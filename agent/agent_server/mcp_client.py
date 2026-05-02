"""
agent/agent_server/mcp_client.py

config.py에서 MCP 설정을 읽어 MultiServerMCPClient를 구성합니다.

보안 민감 항목 관리 분리:
  config.json  경로, 포트, 활성화 여부, Notion OAuth 토큰
  .env         GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET

지원 MCP 서버:
  desktop-pet-tools  기존 자체 MCP 서버 (SSE 또는 stdio, .env로 제어)
  windows-mcp        Windows 자동화 (stdio)
  workspace-mcp      Google Gmail / Calendar / Drive 등 (stdio)
  email-mcp          SMTP/IMAP 범용 이메일 (stdio)
  notion-mcp         Notion 공식 원격 MCP (SSE + OAuth 2.1 + PKCE 자동 처리)
"""

import os
import logging
from pathlib import Path

from dotenv import load_dotenv
from langchain_mcp_adapters.client import MultiServerMCPClient

from . import config as cfg

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

MCP_TRANSPORT  = os.getenv("MCP_TRANSPORT", "stdio").lower()
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8002/sse")

_mcp_client = None


async def get_mcp_tools():
    """모든 MCP 서버들의 Tools를 합쳐서 반환합니다."""
    win, ext = await get_categorized_mcp_tools()
    return win + ext


async def get_categorized_mcp_tools():
    """
    Windows MCP 도구와 외부(External) MCP 도구를 분리하여 반환합니다.
    Returns: (windows_tools, external_tools)
    """
    mcp_config = await _build_config()
    
    # 1. Windows 전용 설정
    win_cfg = {k: v for k, v in mcp_config.items() if k == "windows-mcp"}
    # 2. 그 외 (Workspace, Email, Notion, DesktopPet 등) 설정
    ext_cfg = {k: v for k, v in mcp_config.items() if k != "windows-mcp"}

    win_tools = []
    if win_cfg:
        win_client = MultiServerMCPClient(win_cfg)
        win_tools = await win_client.get_tools()

    ext_tools = []
    if ext_cfg:
        ext_client = MultiServerMCPClient(ext_cfg)
        ext_tools = await ext_client.get_tools()

    return win_tools, ext_tools


def get_mcp_client():
    return _mcp_client


# ==========================================
# Config Builder
# ==========================================

async def _build_config() -> dict:
    """notion-mcp는 토큰 발급이 async라 전체를 async로 처리합니다."""
    config: dict = {}
    _register_desktop_pet_tools(config)
    _register_windows_mcp(config)
    _register_workspace_mcp(config)
    _register_email_mcp(config)
    await _register_notion_mcp(config)
    return config


def _register_desktop_pet_tools(config: dict) -> None:
    if MCP_TRANSPORT == "sse":
        config["desktop-pet-tools"] = {
            "url": MCP_SERVER_URL,
            "transport": "sse",
        }
        logger.info(f"[MCP] desktop-pet-tools 등록 (SSE: {MCP_SERVER_URL})")


def _register_windows_mcp(config: dict) -> None:
    enabled     = cfg.get("mcp.windows_mcp.enabled", True)
    python_path = cfg.get("mcp.windows_mcp.python_path", "")

    if not enabled:
        return
    if not python_path:
        logger.warning("[MCP] windows-mcp: python_path 미설정")
        return

    config["windows-mcp"] = {
        "command": python_path,
        "args": ["-m", "windows_mcp"],
        "transport": "stdio",
        "env": {"ANONYMIZED_TELEMETRY": "false"},
    }
    logger.info("[MCP] windows-mcp 등록")


def _register_workspace_mcp(config: dict) -> None:
    if not cfg.get("mcp.workspace_mcp.enabled", False):
        return

    exe_path      = cfg.get("mcp.workspace_mcp.exe_path", "")
    client_id     = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")

    missing = [k for k, v in [
        ("exe_path (config.json)", exe_path),
        ("GOOGLE_OAUTH_CLIENT_ID (.env)", client_id),
        ("GOOGLE_OAUTH_CLIENT_SECRET (.env)", client_secret),
    ] if not v]

    if missing:
        logger.warning(f"[MCP] workspace-mcp: 필수 설정 누락 {missing}")
        return

    tools = cfg.get("mcp.workspace_mcp.tools", ["gmail", "calendar"])
    port  = str(cfg.get("mcp.workspace_mcp.oauth_callback_port", "8003"))
    google_email = cfg.get("mcp.workspace_mcp.user_google_email", "")

    config["workspace-mcp"] = {
        "command": exe_path,
        "args": ["--tools"] + tools,
        "transport": "stdio",
        "env": {
            "GOOGLE_OAUTH_CLIENT_ID":      client_id,
            "GOOGLE_OAUTH_CLIENT_SECRET":  client_secret,
            "USER_GOOGLE_EMAIL":           google_email,
            "OAUTHLIB_INSECURE_TRANSPORT": "1",
            "PORT":                        port,
            "WORKSPACE_MCP_PORT":          port,
            "GOOGLE_OAUTH_REDIRECT_URI":   f"http://localhost:{port}/oauth2callback"
        },
    }
    logger.info(f"[MCP] workspace-mcp 등록 (tools={tools})")


def _register_email_mcp(config: dict) -> None:
    if not cfg.get("mcp.email_mcp.enabled", False):
        return

    exe_path  = cfg.get("mcp.email_mcp.exe_path", "")
    email     = cfg.get("mcp.email_mcp.email_address", "")
    password  = cfg.get("mcp.email_mcp.password", "")
    imap_host = cfg.get("mcp.email_mcp.imap_host", "")
    smtp_host = cfg.get("mcp.email_mcp.smtp_host", "")

    missing = [k for k, v in [
        ("exe_path", exe_path),
        ("email_address", email),
        ("password", password),
        ("imap_host", imap_host),
        ("smtp_host", smtp_host),
    ] if not v]

    if missing:
        logger.warning(f"[MCP] email-mcp: 필수 설정 누락 {missing}")
        return

    config["email-mcp"] = {
        "command": exe_path,
        "args": ["stdio"],
        "transport": "stdio",
        "env": {
            "MCP_EMAIL_SERVER_ACCOUNT_NAME":               cfg.get("mcp.email_mcp.account_name", "default"),
            "MCP_EMAIL_SERVER_FULL_NAME":                  cfg.get("mcp.email_mcp.full_name", ""),
            "MCP_EMAIL_SERVER_EMAIL_ADDRESS":              email,
            "MCP_EMAIL_SERVER_PASSWORD":                   password,
            "MCP_EMAIL_SERVER_IMAP_HOST":                  imap_host,
            "MCP_EMAIL_SERVER_IMAP_PORT":                  str(cfg.get("mcp.email_mcp.imap_port", "993")),
            "MCP_EMAIL_SERVER_SMTP_HOST":                  smtp_host,
            "MCP_EMAIL_SERVER_SMTP_PORT":                  str(cfg.get("mcp.email_mcp.smtp_port", "465")),
            "MCP_EMAIL_SERVER_ENABLE_ATTACHMENT_DOWNLOAD": str(cfg.get("mcp.email_mcp.enable_attachment_download", "false")),
        },
    }
    logger.info(f"[MCP] email-mcp 등록 ({email})")


async def _register_notion_mcp(config: dict) -> None:
    """
    Notion 공식 원격 MCP (SSE + OAuth 2.1 + PKCE)
    - 최초 실행: 브라우저 열려서 로그인 → 토큰 config.json 저장
    - 이후 실행: 저장된 토큰 재사용, 만료 시 자동 갱신
    """
    if not cfg.get("mcp.notion_mcp.enabled", False):
        return

    try:
        from agent_server.notion_oauth import get_valid_token
        access_token = await get_valid_token(cfg)
    except Exception as e:
        logger.error(f"[MCP] notion-mcp: 토큰 발급 실패 — {e}")
        return

    config["notion-mcp"] = {
        "url": "https://mcp.notion.com/sse",
        "transport": "sse",
        "headers": {
            "Authorization": f"Bearer {access_token}",
        },
    }
    logger.info("[MCP] notion-mcp 등록 (SSE + OAuth 토큰)")