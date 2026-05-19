"""
agent/agent_server/notion_oauth.py

Notion MCP 서버 연결을 위한 OAuth 2.1 + PKCE 플로우 처리 모듈입니다.
공식 문서: https://developers.notion.com/guides/mcp/build-mcp-client

흐름:
  1. OAuth Discovery (RFC 9470 → RFC 8414)
  2. PKCE code_verifier / code_challenge 생성
  3. Dynamic Client Registration (RFC 7591)
  4. 브라우저 열어서 사용자 로그인 유도
  5. 로컬 콜백 서버로 authorization code 수신
  6. code → access_token / refresh_token 교환
  7. 토큰을 config.json에 저장
  8. 만료 시 refresh_token으로 자동 갱신

토큰 특성 (Notion MCP):
  - access_token: 1시간 만료
  - refresh_token: rotation 방식 (사용 시 새 토큰 발급, 기존 무효화)
"""

import os
import time
import base64
import hashlib
import secrets
import webbrowser
import logging
import asyncio
from urllib.parse import urlencode, urlparse, parse_qs
from http.server import HTTPServer, BaseHTTPRequestHandler

import httpx

logger = logging.getLogger(__name__)

# OAuth 콜백 수신용 로컬 서버 포트
CALLBACK_PORT = 9999
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"

# config.json 저장 키
NOTION_TOKEN_KEY = "notion_oauth"
TOKEN_REFRESH_SKEW_SECONDS = 10 * 60


# ==========================================
# Step 1: OAuth Discovery
# ==========================================

async def discover_oauth_metadata(mcp_server_url: str) -> dict:
    """
    RFC 9470 → RFC 8414 순서로 OAuth 메타데이터를 탐색합니다.
    authorization_endpoint, token_endpoint, registration_endpoint 등을 반환합니다.
    """
    parsed = urlparse(mcp_server_url)
    base = f"{parsed.scheme}://{parsed.netloc}"

    async with httpx.AsyncClient() as client:
        # Step 1: RFC 9470 - Protected Resource Metadata
        pr_url = f"{base}/.well-known/oauth-protected-resource"
        pr_resp = await client.get(pr_url)
        pr_resp.raise_for_status()
        auth_servers = pr_resp.json().get("authorization_servers", [])

        if not auth_servers:
            raise ValueError("OAuth 인증 서버를 찾을 수 없습니다.")

        auth_server_url = auth_servers[0]

        # Step 2: RFC 8414 - Authorization Server Metadata
        as_url = f"{auth_server_url}/.well-known/oauth-authorization-server"
        as_resp = await client.get(as_url)
        as_resp.raise_for_status()
        metadata = as_resp.json()

    if not metadata.get("authorization_endpoint") or not metadata.get("token_endpoint"):
        raise ValueError("OAuth 메타데이터에 필수 엔드포인트가 없습니다.")

    logger.info(f"[Notion OAuth] 메타데이터 탐색 완료: {auth_server_url}")
    return metadata


# ==========================================
# Step 2: PKCE 생성
# ==========================================

def generate_pkce() -> tuple[str, str]:
    """
    code_verifier와 code_challenge(S256)를 생성합니다.
    Returns: (code_verifier, code_challenge)
    """
    code_verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return code_verifier, code_challenge


# ==========================================
# Step 3: Dynamic Client Registration
# ==========================================

async def register_client(metadata: dict) -> dict:
    """
    RFC 7591 Dynamic Client Registration으로 client_id를 발급받습니다.
    registration_endpoint가 없으면 에러를 발생시킵니다.
    """
    reg_endpoint = metadata.get("registration_endpoint")
    if not reg_endpoint:
        raise ValueError("서버가 Dynamic Client Registration을 지원하지 않습니다.")

    payload = {
        "client_name": "Desktop Pet Agent",
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            reg_endpoint,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        credentials = resp.json()

    logger.info(f"[Notion OAuth] 클라이언트 등록 완료: client_id={credentials.get('client_id')}")
    return credentials


# ==========================================
# Step 4 + 5: 브라우저 열기 + 콜백 수신
# ==========================================

def _build_auth_url(metadata: dict, client_id: str, code_challenge: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "consent",
    }
    return f"{metadata['authorization_endpoint']}?{urlencode(params)}"


def _wait_for_callback() -> tuple[str, str]:
    """
    로컬 HTTP 서버로 OAuth 콜백을 수신합니다.
    Returns: (code, state)
    """
    result = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            result["code"]  = params.get("code",  [""])[0]
            result["state"] = params.get("state", [""])[0]
            result["error"] = params.get("error", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()

            if result.get("error"):
                body = "<h2>❌ 인증 실패</h2><p>창을 닫고 다시 시도하세요.</p>"
            else:
                body = "<h2>✅ Notion 인증 완료!</h2><p>이 창을 닫아도 됩니다.</p>"
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format, *args):
            pass  # 콘솔 로그 억제

    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    server.handle_request()  # 요청 1개만 처리
    server.server_close()

    if result.get("error"):
        raise ValueError(f"OAuth 인증 실패: {result['error']}")

    return result["code"], result["state"]


# ==========================================
# Step 6: code → token 교환
# ==========================================

async def exchange_code_for_token(
    metadata: dict,
    client_id: str,
    code: str,
    code_verifier: str,
) -> dict:
    """authorization_code를 access_token / refresh_token으로 교환합니다."""
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": code_verifier,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            metadata["token_endpoint"],
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token = resp.json()

    logger.info("[Notion OAuth] 토큰 교환 완료")
    return token


# ==========================================
# Step 8: refresh_token으로 갱신
# ==========================================

async def refresh_access_token(metadata: dict, client_id: str, refresh_token: str) -> dict:
    """refresh_token으로 새 access_token을 발급받습니다."""
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            metadata["token_endpoint"],
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token = resp.json()

    logger.info("[Notion OAuth] 토큰 갱신 완료")
    return token


# ==========================================
# 메인: 토큰 획득 (신규 or 갱신)
# ==========================================

def invalidate_token(cfg, *, reason: str = "") -> None:
    """
    저장된 Notion access_token을 폐기합니다.

    SSE 호출 중 401 Unauthorized가 발생한 경우 호출부에서 이 함수를 실행한 뒤
    get_valid_token(..., force_refresh=True)로 새 토큰을 받아 MCP client를 다시
    생성하면 됩니다. refresh_token과 client_id는 보존해서 브라우저 재인증 없이
    refresh를 우선 시도합니다.
    """
    saved = cfg.get(NOTION_TOKEN_KEY) or {}
    if not saved:
        return

    saved["access_token"] = ""
    saved["expires_at"] = 0
    cfg.save({NOTION_TOKEN_KEY: saved})

    suffix = f" ({reason})" if reason else ""
    logger.warning(f"[Notion OAuth] access_token 무효화{suffix}")


async def get_valid_token(
    cfg,
    *,
    force_refresh: bool = False,
    min_ttl_seconds: int = TOKEN_REFRESH_SKEW_SECONDS,
) -> str:
    """
    config.json의 notion_oauth 섹션에서 유효한 access_token을 반환합니다.
    없거나 만료됐으면 갱신 또는 신규 발급합니다.

    Notion MCP의 SSE 연결은 tool 호출 중 오래 유지될 수 있습니다. 생성 계열
    tool이 1~3분 이상 걸리는 경우 만료 직전 access_token을 재사용하면 호출
    도중 401 Unauthorized가 발생할 수 있으므로, 기본적으로 10분 미만의 TTL이
    남은 토큰은 미리 refresh합니다.

    Args:
        cfg: config 모듈 (cfg.get / cfg.save 사용)
        force_refresh: True면 access_token이 아직 유효해도 refresh_token 갱신을
            우선 시도합니다. 401 Unauthorized 복구 플로우에서 사용합니다.
        min_ttl_seconds: 이 시간보다 적게 남은 토큰은 만료 임박으로 보고 갱신합니다.

    Returns:
        유효한 access_token 문자열
    """
    MCP_URL = "https://mcp.notion.com/sse"
    saved   = cfg.get("notion_oauth") or {}

    access_token  = saved.get("access_token", "")
    refresh_token = saved.get("refresh_token", "")
    expires_at    = saved.get("expires_at", 0)
    client_id     = saved.get("client_id", "")
    metadata      = saved.get("metadata")

    # metadata가 없으면 다시 탐색
    if not metadata:
        metadata = await discover_oauth_metadata(MCP_URL)

    now = time.time()
    ttl = expires_at - now

    # --- 토큰이 있고 충분히 오래 유효한 경우 ---
    if access_token and not force_refresh and ttl > min_ttl_seconds:
        logger.info(f"[Notion OAuth] 저장된 토큰 유효, 재사용 (TTL: {int(ttl)}초)")
        return access_token

    # --- refresh_token으로 갱신 ---
    if refresh_token and client_id:
        try:
            if force_refresh:
                logger.info("[Notion OAuth] force_refresh=True → refresh_token으로 갱신 시도")
            elif access_token:
                logger.info(f"[Notion OAuth] access_token 만료 임박/만료 (TTL: {int(ttl)}초) → refresh_token으로 갱신 시도")
            else:
                logger.info("[Notion OAuth] access_token 없음 → refresh_token으로 갱신 시도")
            token = await refresh_access_token(metadata, client_id, refresh_token)
            _save_token(cfg, token, client_id, metadata)
            return token["access_token"]
        except Exception as e:
            logger.warning(f"[Notion OAuth] 갱신 실패 ({e}) → 재인증 진행")

    # --- 신규 인증 플로우 ---
    logger.info("[Notion OAuth] 신규 인증 시작")

    credentials   = await register_client(metadata)
    client_id     = credentials["client_id"]
    code_verifier, code_challenge = generate_pkce()
    state         = secrets.token_hex(16)
    auth_url      = _build_auth_url(metadata, client_id, code_challenge, state)

    print(f"\n[Notion OAuth] 브라우저에서 Notion 로그인을 완료해주세요.")
    print(f"자동으로 열리지 않으면 아래 URL을 브라우저에 붙여넣으세요:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # 콜백은 동기 서버라 별도 스레드에서 실행
    loop = asyncio.get_event_loop()
    code, returned_state = await loop.run_in_executor(None, _wait_for_callback)

    if returned_state != state:
        raise ValueError("OAuth state 불일치 — CSRF 공격 가능성")

    token = await exchange_code_for_token(metadata, client_id, code, code_verifier)
    _save_token(cfg, token, client_id, metadata)

    return token["access_token"]


def _save_token(cfg, token: dict, client_id: str, metadata: dict) -> None:
    """토큰 정보를 config.json에 저장합니다."""
    expires_in = token.get("expires_in", 3600)
    cfg.save({
        "notion_oauth": {
            "access_token":  token["access_token"],
            "refresh_token": token.get("refresh_token", ""),
            "expires_at":    time.time() + expires_in,
            "client_id":     client_id,
            "metadata":      metadata,
        }
    })
    logger.info(f"[Notion OAuth] 토큰 저장 완료 (만료: {expires_in}초 후)")
