"""
OAuth helper for Notion's hosted MCP server.

The hosted Notion MCP endpoint requires user OAuth with PKCE. This module keeps
the project on the SSE transport without depending on Node-based mcp-remote.
Tokens are stored in config.json under the top-level "notion_oauth" key.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlencode, urlparse

import httpx

logger = logging.getLogger(__name__)

CALLBACK_PORT = 9999
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}/callback"
NOTION_BASE_URL = "https://mcp.notion.com"
NOTION_SSE_URL = f"{NOTION_BASE_URL}/sse"
NOTION_TOKEN_KEY = "notion_oauth"
TOKEN_REFRESH_SKEW_SECONDS = 10 * 60


async def discover_oauth_metadata() -> dict:
    """Discover Notion OAuth endpoints and protected resource metadata."""
    async with httpx.AsyncClient(timeout=30) as client:
        protected_resp = await client.get(f"{NOTION_BASE_URL}/.well-known/oauth-protected-resource")
        protected_resp.raise_for_status()
        protected_resource = protected_resp.json()

        auth_servers = protected_resource.get("authorization_servers") or []
        if not auth_servers:
            raise ValueError("No Notion OAuth authorization server was advertised.")

        auth_server_url = auth_servers[0].rstrip("/")
        metadata_resp = await client.get(f"{auth_server_url}/.well-known/oauth-authorization-server")
        metadata_resp.raise_for_status()
        metadata = metadata_resp.json()

    if not metadata.get("authorization_endpoint") or not metadata.get("token_endpoint"):
        raise ValueError("Notion OAuth metadata is missing required endpoints.")

    metadata["_protected_resource"] = protected_resource
    return metadata


def generate_pkce() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(32)).decode("utf-8").rstrip("=")
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    return verifier, challenge


async def register_client(metadata: dict) -> dict:
    registration_endpoint = metadata.get("registration_endpoint")
    if not registration_endpoint:
        raise ValueError("Notion OAuth server does not support dynamic client registration.")

    payload = {
        "client_name": "Desktop Pet Agent",
        "redirect_uris": [REDIRECT_URI],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            registration_endpoint,
            json=payload,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()


def _resource_from_metadata(metadata: dict) -> str:
    protected = metadata.get("_protected_resource") or {}
    return protected.get("resource") or NOTION_BASE_URL


def _build_auth_url(metadata: dict, client_id: str, code_challenge: str, state: str) -> str:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": "openid email profile",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "prompt": "consent",
        "resource": _resource_from_metadata(metadata),
    }
    return f"{metadata['authorization_endpoint']}?{urlencode(params)}"


def _wait_for_callback() -> tuple[str, str]:
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            result["code"] = params.get("code", [""])[0]
            result["state"] = params.get("state", [""])[0]
            result["error"] = params.get("error", [""])[0]
            result["error_description"] = params.get("error_description", [""])[0]

            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()

            if result.get("error"):
                body = "<h2>Notion OAuth failed</h2><p>You can close this window.</p>"
            else:
                body = "<h2>Notion OAuth complete</h2><p>You can return to Desktop Pet Agent.</p>"
            self.wfile.write(body.encode("utf-8"))

        def log_message(self, format, *args):
            return

    server = HTTPServer(("localhost", CALLBACK_PORT), CallbackHandler)
    try:
        server.handle_request()
    finally:
        server.server_close()

    if result.get("error"):
        desc = result.get("error_description") or result["error"]
        raise ValueError(f"Notion OAuth failed: {desc}")
    if not result.get("code"):
        raise ValueError("Notion OAuth callback did not contain an authorization code.")
    return result["code"], result["state"]


async def exchange_code_for_token(metadata: dict, client_id: str, code: str, code_verifier: str) -> dict:
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": client_id,
        "code_verifier": code_verifier,
        "resource": _resource_from_metadata(metadata),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            metadata["token_endpoint"],
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def refresh_access_token(metadata: dict, client_id: str, refresh_token: str) -> dict:
    payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": client_id,
        "resource": _resource_from_metadata(metadata),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            metadata["token_endpoint"],
            data=payload,
            headers={"Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def get_valid_token(config_store, *, force_refresh: bool = False) -> str:
    saved = config_store.get(NOTION_TOKEN_KEY) or {}
    access_token = saved.get("access_token", "")
    refresh_token = saved.get("refresh_token", "")
    expires_at = float(saved.get("expires_at", 0) or 0)
    client_id = saved.get("client_id", "")
    metadata = saved.get("metadata")

    if not metadata:
        metadata = await discover_oauth_metadata()

    ttl = expires_at - time.time()
    if access_token and not force_refresh and ttl > TOKEN_REFRESH_SKEW_SECONDS:
        logger.info("[Notion OAuth] Reusing stored access token (TTL: %ss)", int(ttl))
        return access_token

    if refresh_token and client_id:
        try:
            token = await refresh_access_token(metadata, client_id, refresh_token)
            _save_token(config_store, token, client_id, metadata)
            return token["access_token"]
        except Exception as exc:
            logger.warning("[Notion OAuth] Refresh failed, starting re-auth: %s", exc)

    credentials = await register_client(metadata)
    client_id = credentials["client_id"]
    verifier, challenge = generate_pkce()
    state = secrets.token_hex(16)
    auth_url = _build_auth_url(metadata, client_id, challenge, state)

    print("\n[Notion OAuth] Complete Notion authorization in the browser.")
    print(f"If the browser does not open, paste this URL:\n{auth_url}\n")
    webbrowser.open(auth_url)

    loop = asyncio.get_running_loop()
    code, returned_state = await loop.run_in_executor(None, _wait_for_callback)
    if returned_state != state:
        raise ValueError("Notion OAuth state mismatch.")

    token = await exchange_code_for_token(metadata, client_id, code, verifier)
    _save_token(config_store, token, client_id, metadata)
    return token["access_token"]


def invalidate_token(config_store, *, reason: str = "") -> None:
    saved = config_store.get(NOTION_TOKEN_KEY) or {}
    if not saved:
        return
    saved["access_token"] = ""
    saved["expires_at"] = 0
    config_store.save({NOTION_TOKEN_KEY: saved})
    logger.warning("[Notion OAuth] Invalidated access token%s", f": {reason}" if reason else "")


def _save_token(config_store, token: dict, client_id: str, metadata: dict) -> None:
    expires_in = int(token.get("expires_in", 3600) or 3600)
    refresh_token = token.get("refresh_token")
    previous = config_store.get(NOTION_TOKEN_KEY) or {}
    config_store.save(
        {
            NOTION_TOKEN_KEY: {
                "access_token": token["access_token"],
                "refresh_token": refresh_token or previous.get("refresh_token", ""),
                "expires_at": time.time() + expires_in,
                "client_id": client_id,
                "metadata": metadata,
            }
        }
    )
    logger.info("[Notion OAuth] Saved token (expires in %ss)", expires_in)
