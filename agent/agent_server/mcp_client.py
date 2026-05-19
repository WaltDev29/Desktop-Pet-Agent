"""
agent/agent_server/mcp_client.py

config.json의 mcpServers 설정을 읽어 MultiServerMCPClient를 구성합니다.
사용자가 config.json에 MCP 서버를 추가하면 별도 코드 수정 없이 동일한 MCP
worker에서 통합 관리합니다.
"""

import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

logger = logging.getLogger(__name__)

_mcp_client = None


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
    global _mcp_client

    if _mcp_client is not None:
        return await _mcp_client.get_tools()

    mcp_config = _load_mcp_servers()
    final_config = await _normalize_mcp_config(mcp_config)

    if not final_config:
        logger.warning("[MCP] 등록된 MCP 서버가 없습니다.")
        return []

    _mcp_client = MultiServerMCPClient(final_config)
    return await _mcp_client.get_tools()


def get_mcp_client():
    """현재 유지되고 있는 클라이언트를 반환합니다."""
    return _mcp_client


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
    logger.info("[MCP] config.json에서 %d개의 MCP 서버 설정을 로드했습니다.", len(servers))
    return servers


async def _normalize_mcp_config(mcp_config: dict) -> dict:
    final_config = {}

    for name, raw_cfg in mcp_config.items():
        transport = raw_cfg.get("transport", "stdio")
        normalized = {
            "transport": transport,
        }

        if transport == "sse":
            url = raw_cfg.get("url")
            if not url:
                logger.warning("[MCP] %s: SSE transport에는 url이 필요합니다.", name)
                continue
            normalized["url"] = url
            if raw_cfg.get("headers"):
                normalized["headers"] = raw_cfg["headers"]
            if raw_cfg.get("oauth") == "notion" or raw_cfg.get("oauth") is True:
                try:
                    from agent_server.notion_oauth import get_valid_token

                    token = await get_valid_token(_JsonConfigStore(CONFIG_PATH))
                    headers = dict(normalized.get("headers", {}))
                    headers["Authorization"] = f"Bearer {token}"
                    normalized["headers"] = headers
                except Exception as e:
                    logger.error("[MCP] %s: Notion OAuth 토큰 발급 실패: %s", name, e)
                    continue
        else:
            command = raw_cfg.get("command")
            if not command:
                logger.warning("[MCP] %s: stdio transport에는 command가 필요합니다.", name)
                continue
            normalized["command"] = sys.executable if command == "python" else command
            normalized["args"] = raw_cfg.get("args", [])
            normalized["env"] = raw_cfg.get("env", {})

        final_config[name] = normalized

    return final_config
