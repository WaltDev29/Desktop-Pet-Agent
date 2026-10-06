import json
import logging
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
logger = logging.getLogger(__name__)

_process: subprocess.Popen | None = None
_port: int | None = None


def start_workspace_mcp_server() -> None:
    """Run Google workspace-mcp as one long-lived streamable-http process."""
    global _process, _port

    cfg = _load_workspace_config()
    if not cfg:
        return

    env = {**os.environ, **{k: str(v) for k, v in (cfg.get("env") or {}).items()}}
    workspace_dir = Path(__file__).resolve().parents[2]
    env.setdefault("UV_CACHE_DIR", str(workspace_dir / ".uv-cache"))
    env.setdefault("UV_TOOL_DIR", str(workspace_dir / ".uv-tools"))
    port = _workspace_port(cfg)
    _port = port

    if _process and _process.poll() is None:
        return

    command = cfg.get("command")
    args = list(cfg.get("args") or [])
    if not command or not args:
        logger.warning("[workspace-mcp] command/args setting is missing.")
        return
    command, args = _prefer_installed_workspace_mcp(command, args)

    _kill_listeners_on_port(port)

    if "--transport" not in args:
        args.extend(["--transport", "streamable-http"])

    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    logger.info("[workspace-mcp] starting streamable-http server on port %s", port)
    try:
        _process = subprocess.Popen(
            [command, *args],
            env=env,
            cwd=str(Path(__file__).resolve().parents[2]),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    except OSError as exc:
        logger.warning("[workspace-mcp] failed to start process: %s", exc)
        return

    timeout = float(env.get("WORKSPACE_MCP_STARTUP_TIMEOUT", "120"))
    _wait_for_port(port, timeout=timeout)


def stop_workspace_mcp_server() -> None:
    global _process, _port

    if not _process:
        return

    if _process.poll() is None:
        logger.info("[workspace-mcp] stopping streamable-http server")
        _process.terminate()
        try:
            _process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _process.kill()
            _process.wait(timeout=5)

    _process = None
    if _port is not None:
        _kill_listeners_on_port(_port)
    _port = None


def _load_workspace_config() -> dict | None:
    if not CONFIG_PATH.exists():
        return None

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        logger.warning("[workspace-mcp] failed to read config.json: %s", exc)
        return None

    cfg = (data.get("mcpServers") or {}).get("workspace-mcp")
    if not isinstance(cfg, dict) or cfg.get("enabled", True) is False:
        return None
    if cfg.get("transport", "stdio") != "stdio":
        return None

    return cfg


def _workspace_port(cfg: dict) -> int:
    env = cfg.get("env") or {}
    return int(env.get("PORT") or env.get("WORKSPACE_MCP_PORT") or 8003)


def _prefer_installed_workspace_mcp(command: str, args: list[str]) -> tuple[str, list[str]]:
    if command != "uvx" or not args or args[0] != "workspace-mcp":
        return command, args

    installed = shutil.which("workspace-mcp")
    if not installed:
        return command, args

    logger.info("[workspace-mcp] using installed executable: %s", installed)
    return installed, args[1:]


def _wait_for_port(port: int, timeout: float = 120.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _process and _process.poll() is not None:
            logger.warning("[workspace-mcp] process exited before port %s opened", port)
            return
        if _is_port_open(port):
            logger.info("[workspace-mcp] port %s is ready", port)
            return
        time.sleep(0.2)

    logger.warning("[workspace-mcp] port %s did not open within %ss", port, timeout)


def _is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _kill_listeners_on_port(port: int) -> None:
    if sys.platform != "win32":
        return

    for pid in _listening_pids(port):
        if pid == os.getpid():
            continue
        logger.info("[workspace-mcp] killing existing listener on port %s: PID %s", port, pid)
        subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def _listening_pids(port: int) -> set[int]:
    result = subprocess.run(
        ["netstat", "-ano", "-p", "tcp"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )

    pids: set[int] = set()
    marker = f":{port}"
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) < 5:
            continue
        local_address, state, pid_text = parts[1], parts[3], parts[4]
        if marker in local_address and state.upper() == "LISTENING":
            try:
                pids.add(int(pid_text))
            except ValueError:
                pass
    return pids
