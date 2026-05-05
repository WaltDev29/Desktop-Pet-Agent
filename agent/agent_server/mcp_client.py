import os
import sys
import json
import logging
from pathlib import Path
from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

logger = logging.getLogger(__name__)

# 전역 클라이언트 인스턴스
_mcp_client = None

async def get_mcp_tools():
    """
    config.json의 mcpServers 설정을 동적으로 읽어 Tools를 반환합니다.
    """
    global _mcp_client
    
    if _mcp_client is not None:
        return await _mcp_client.get_tools()

    mcp_config = {}
    
    # 1. config.json에서 서버 설정 로드
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                mcp_config = data.get("mcpServers", {})
                logger.info(f"[MCP] config.json에서 {len(mcp_config)}개의 MCP 서버 설정을 로드했습니다.")
        except Exception as e:
            logger.error(f"[MCP] config.json 로드 실패: {e}")
    else:
        logger.warning(f"[MCP] {CONFIG_PATH} 파일이 없습니다.")

    # 2. 각 서버 설정 보정 (Conda 환경 공유 등)
    final_config = {}
    for name, cfg in mcp_config.items():
        cmd = cfg.get("command")
        args = cfg.get("args", [])
        env = cfg.get("env", {})
        
        # 요구사항 3: python 명령 시 현재 에이전트의 파이썬 인터프리터 사용
        if cmd == "python":
            cmd = sys.executable
        
        final_config[name] = {
            "command": cmd,
            "args": args,
            "transport": cfg.get("transport", "stdio"),
            "env": env
        }

    if not final_config:
        logger.warning("[MCP] 등록된 MCP 서버가 없습니다.")
        return []

    # 3. MultiServerMCPClient 초기화
    _mcp_client = MultiServerMCPClient(final_config)
    
    return await _mcp_client.get_tools()

def get_mcp_client():
    """현재 유지되고 있는 클라이언트를 반환합니다. (직접 호출할 때 필요)"""
    return _mcp_client
