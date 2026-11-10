"""
agent/agent_server/mcp_client.py

config.json의 mcpServers 설정을 읽어 MultiServerMCPClient를 구성합니다.
사용자가 config.json에 MCP 서버를 추가하면 별도 코드 수정 없이 동일한 MCP
worker에서 통합 관리합니다.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

logger = logging.getLogger(__name__)

_mcp_client = None
_mcp_client_config = None
_mcp_source_config = None


class _JsonConfigStore:
    def __init__(self, path: Path):
        self.path = path

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def get(self, key: str, default=None):
        return self._read().get(key, default)

    def save(self, updates: dict) -> None:
        data = self._read()
        data.update(updates)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


async def get_mcp_tools():
    """config.json의 mcpServers 설정을 동적으로 읽어 Tools를 반환합니다."""
    global _mcp_client, _mcp_client_config, _mcp_source_config

    if _mcp_client is not None and not _should_rebuild_client():
        return await _mcp_client.get_tools()

    if _mcp_client is not None:
        reset_mcp_client("MCP 설정 또는 OAuth 토큰 상태 변경")

    mcp_config = _load_mcp_servers()
    final_config = await _normalize_mcp_config(mcp_config)

    if not final_config:
        logger.warning("[MCP] 등록된 MCP 서버가 없습니다.")
        return []

    try:
        # 1차 시도: 모든 서버를 일괄 등록하여 도구를 로드합니다.
        candidate_client = MultiServerMCPClient(final_config)
        raw_tools = await candidate_client.get_tools()
        _mcp_client = candidate_client
        _mcp_client_config = final_config
    except Exception as batch_error:
        # 단일 서버 오류(예: stdio 즉시 종료, HTTP 401/404 등)로 전체가 실패한 경우 개별 서버 격리 모드로 전환합니다.
        logger.warning(
            "[MCP] 전체 서버 일괄 연결 중 오류 발생 (%s). 서버별 장애 격리(Fault Tolerance) 모드로 재시도합니다.",
            batch_error,
        )
        healthy_config = {}
        for server_name, server_cfg in final_config.items():
            try:
                single_client = MultiServerMCPClient({server_name: server_cfg})
                await single_client.get_tools()
                healthy_config[server_name] = server_cfg
                logger.info("[MCP] 서버 '%s' 연결 성공", server_name)
            except Exception as single_error:
                logger.error(
                    "[MCP] 서버 '%s' 초기화 실패 (도구 목록에서 제외됨): %s",
                    server_name,
                    single_error,
                )

        if not healthy_config:
            logger.error("[MCP] 정상 동작하는 MCP 서버가 하나도 없습니다.")
            return []

        _mcp_client = MultiServerMCPClient(healthy_config)
        _mcp_client_config = healthy_config
        raw_tools = await _mcp_client.get_tools()

    _mcp_source_config = mcp_config

    # 제외할 도구 목록 수집 (서버별 disabled_tools / exclude_tools)
    excluded = set()
    for cfg in mcp_config.values():
        if isinstance(cfg, dict):
            excluded.update(cfg.get("disabled_tools") or cfg.get("exclude_tools") or [])

    if excluded:
        filtered_tools = [t for t in raw_tools if t.name not in excluded]
        logger.info(
            "[MCP] 제외된 도구 (%d개): %s (전체 %d개 중 %d개 활성화)",
            len(raw_tools) - len(filtered_tools),
            list(excluded),
            len(raw_tools),
            len(filtered_tools),
        )
        return filtered_tools

    return raw_tools


def get_mcp_client():
    """현재 유지하고 있는 클라이언트를 반환합니다."""
    return _mcp_client


def should_rebuild_mcp_client() -> bool:
    """Return whether the cached MCP client should be recreated before use."""
    if _mcp_client is None:
        return True
    return _should_rebuild_client()


def reset_mcp_client(reason: str = "") -> None:
    """Drop the cached MCP client so the next get_mcp_tools call reconnects."""
    global _mcp_client, _mcp_client_config, _mcp_source_config

    _mcp_client = None
    _mcp_client_config = None
    _mcp_source_config = None
    logger.info("[MCP] MCP 클라이언트 캐시를 초기화했습니다%s", f": {reason}" if reason else "")


def _load_mcp_servers() -> dict:
    if not CONFIG_PATH.exists():
        logger.warning("[MCP] %s 파일이 없습니다.", CONFIG_PATH)
        return {}

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error("[MCP] config.json 로드 실패: %s", e)
        return {}

    servers = data.get("mcpServers", {})
    enabled_servers = {
        name: cfg
        for name, cfg in servers.items()
        if not isinstance(cfg, dict) or cfg.get("enabled", True) is not False
    }
    disabled_count = len(servers) - len(enabled_servers)
    logger.info(
        "[MCP] config.json에서 %d개의 MCP 서버 설정을 로드했습니다. 비활성 제외: %d개",
        len(enabled_servers),
        disabled_count,
    )
    return enabled_servers


def _should_rebuild_client() -> bool:
    current_config = _load_mcp_servers()
    if _mcp_client_config is None:
        return True

    if current_config != _mcp_source_config:
        return True

    if not _has_notion_oauth_server(current_config):
        return False

    saved = _JsonConfigStore(CONFIG_PATH).get("notion_oauth") or {}
    expires_at = float(saved.get("expires_at", 0) or 0)
    if not expires_at:
        return True

    try:
        from agent_server.notion_oauth import TOKEN_REFRESH_SKEW_SECONDS
    except Exception:
        token_refresh_skew_seconds = 10 * 60
    else:
        token_refresh_skew_seconds = TOKEN_REFRESH_SKEW_SECONDS

    # Rebuild before expiry so the cached SSE Authorization header is refreshed.
    return expires_at - time.time() <= token_refresh_skew_seconds


def _has_notion_oauth_server(mcp_config: dict) -> bool:
    return any(
        isinstance(cfg, dict)
        and cfg.get("transport", "stdio") == "sse"
        and (cfg.get("oauth") == "notion" or cfg.get("oauth") is True)
        for cfg in mcp_config.values()
    )


async def _normalize_mcp_config(mcp_config: dict) -> dict:
    final_config = {}

    for name, raw_cfg in mcp_config.items():
        transport = raw_cfg.get("transport", "stdio")
        normalized = {
            "transport": transport,
        }

        if name == "workspace-mcp" and transport == "stdio":
            env = raw_cfg.get("env") or {}
            port = env.get("PORT") or env.get("WORKSPACE_MCP_PORT") or "8003"
            normalized["transport"] = "streamable_http"
            normalized["url"] = raw_cfg.get("url") or f"http://localhost:{port}/mcp"
        elif transport in {"sse", "streamable_http", "streamable-http", "http"}:
            url = raw_cfg.get("url")
            if not url:
                logger.warning("[MCP] %s: HTTP/SSE transport에는 url이 필요합니다.", name)
                continue
            # 'http' 표기를 langchain-mcp-adapters 규격인 'streamable_http'로 표준화합니다.
            normalized["transport"] = "streamable_http" if transport in {"streamable_http", "streamable-http", "http"} else "sse"
            normalized["url"] = url
            if raw_cfg.get("headers"):
                # 헤더 값에 포함된 ${ENV_VAR} 형태를 시스템 환경변수로 안전하게 치환합니다.
                resolved_headers = {}
                for h_key, h_val in raw_cfg["headers"].items():
                    if isinstance(h_val, str):
                        resolved_val = re.sub(
                            r"\$\{([^}]+)\}|\$([A-Za-z0-9_]+)",
                            lambda m: os.getenv(m.group(1) or m.group(2), ""),
                            h_val,
                        )
                        resolved_headers[h_key] = resolved_val
                    else:
                        resolved_headers[h_key] = h_val
                normalized["headers"] = resolved_headers
            if raw_cfg.get("oauth") == "notion" or raw_cfg.get("oauth") is True:
                try:
                    from agent_server.notion_oauth import get_valid_token

                    token = await get_valid_token(_JsonConfigStore(CONFIG_PATH))
                    headers = dict(normalized.get("headers", {}))
                    headers["Authorization"] = f"Bearer {token}"
                    normalized["headers"] = headers
                except Exception as e:
                    logger.warning("[MCP] %s: Notion OAuth 토큰 발급 실패, 토큰 폐기 후 재시도: %s", name, e)
                    try:
                        from agent_server.notion_oauth import get_valid_token, invalidate_token

                        store = _JsonConfigStore(CONFIG_PATH)
                        invalidate_token(store, reason=str(e))
                        token = await get_valid_token(store, force_refresh=True)
                        headers = dict(normalized.get("headers", {}))
                        headers["Authorization"] = f"Bearer {token}"
                        normalized["headers"] = headers
                    except Exception as retry_error:
                        logger.error("[MCP] %s: Notion OAuth 토큰 발급 최종 실패: %s", name, retry_error)
                        continue
        else:
            command = raw_cfg.get("command")
            if not command:
                logger.warning("[MCP] %s: stdio transport에는 command가 필요합니다.", name)
                continue
            
            args = raw_cfg.get("args", [])
            
            if command == "uvx" and args:
                package_ref = args[0]
                executable_name = package_ref.split('@')[0]
                if not shutil.which(executable_name):
                    logger.info("[MCP] %s: '%s' 실행 파일을 찾을 수 없어 자동 설치를 시도합니다...", name, executable_name)
                    try:
                        process = await asyncio.create_subprocess_exec(
                            "uv", "tool", "install", package_ref,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate()
                        if process.returncode == 0:
                            logger.info("[MCP] %s: '%s' 자동 설치 완료", name, package_ref)
                        else:
                            logger.warning("[MCP] %s: '%s' 자동 설치 실패 (코드 %s): %s", name, package_ref, process.returncode, stderr.decode('utf-8', errors='replace').strip())
                    except Exception as e:
                        logger.error("[MCP] %s: '%s' 자동 설치 중 에러 발생: %s", name, package_ref, e)

            normalized["command"] = sys.executable if command == "python" else command
            normalized["args"] = args
            normalized["env"] = raw_cfg.get("env", {})

        final_config[name] = normalized

    return final_config
