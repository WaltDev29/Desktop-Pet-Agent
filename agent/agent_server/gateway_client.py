import asyncio
import os
import socket
import logging
import json
from dotenv import load_dotenv

try:
    import websockets
except ImportError:
    pass

import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from entity import (
        WsMessage, 
        AgentRegisterPayload, 
        ChatPayload,
        ApprovalResponsePayload,
        PingPongPayload
    )
except ImportError:
    logger = logging.getLogger(__name__)
    logger.error("entity.py not found. Please ensure it is in the agent directory.")

logger = logging.getLogger(__name__)
load_dotenv()

class GatewayClient:
    def __init__(self):
        self.ws = None
        self.is_local_mode = False
        
        # 동적 Client ID 할당: {PC이름}-1
        self.hostname = socket.gethostname()
        self.client_id = f"{self.hostname}-1"
        self._listen_task = None

        api_server = os.getenv("API_SERVER", "")
        # DB의 UUID 필드와 호환되도록 기본값으로 UUID 형식을 사용함
        user_id = os.getenv("USER_ID", "00000000-0000-0000-0000-000000000000")
        if api_server.startswith("http://"):
            self.gateway_url = f"{api_server.replace('http://', 'ws://', 1)}/ws/{user_id}"
        elif api_server.startswith("https://"):
            self.gateway_url = f"{api_server.replace('https://', 'wss://', 1)}/ws/{user_id}"
        else:
            self.gateway_url = f"ws://localhost:8080/ws/{user_id}"
            
        self.chat_handler = None
        self.approve_handler = None

    def set_handlers(self, chat_handler, approve_handler, sync_handler=None):
        self.chat_handler = chat_handler
        self.approve_handler = approve_handler
        self.sync_handler = sync_handler

    async def connect(self):
        """정확히 3회 연결을 시도하고 실패 시 로컬 모드로 전환합니다."""
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                logger.info(f"[GatewayClient] 연결 시도 중: {self.gateway_url} ({retry_count + 1}/{max_retries})...")
                self.ws = await websockets.connect(self.gateway_url)
                logger.info(f"[GatewayClient] 게이트웨이 서버 연결 성공! (Client ID: {self.client_id})")
                self.is_local_mode = False
                
                # Register 메시지 전송
                reg_payload = AgentRegisterPayload(client_id=self.client_id)
                msg = WsMessage(type="register", payload=reg_payload)
                await self.ws.send(msg.model_dump_json())
                
                # 수신 루프 시작
                self._listen_task = asyncio.create_task(self._listen_loop())
                return
                
            except Exception as e:
                logger.error(f"[GatewayClient] 연결 실패: {e}")
                retry_count += 1
                if retry_count < max_retries:
                    await asyncio.sleep(2)
                    
        logger.warning("[GatewayClient] 3회 연결 실패. 로컬(Local) 모드로 전환합니다.")
        self.is_local_mode = True
        self.ws = None

    async def disconnect(self):
        if self._listen_task:
            self._listen_task.cancel()
        if self.ws:
            await self.ws.close()
            self.ws = None
            logger.info("[GatewayClient] 연결이 안전하게 종료되었습니다.")

    async def _listen_loop(self):
        try:
            async for message in self.ws:
                try:
                    data = json.loads(message)
                    msg_type = data.get("type")
                    raw_payload = data.get("payload", {})
                    
                    if msg_type == "chat" and self.chat_handler:
                        payload = ChatPayload.model_validate(raw_payload)
                        asyncio.create_task(self.chat_handler(payload))
                        
                    elif msg_type == "approval_response" and self.approve_handler:
                        payload = ApprovalResponsePayload.model_validate(raw_payload)
                        asyncio.create_task(self.approve_handler(payload))
                        
                    elif msg_type in ("session_sync", "session_created", "session_deleted") and getattr(self, "sync_handler", None):
                        # Pydantic을 거치지 않고 raw data 통과 (단순 포워딩)
                        asyncio.create_task(self.sync_handler(msg_type, raw_payload))
                        
                    elif msg_type == "ping":
                        pong_msg = WsMessage(type="pong", payload=PingPongPayload())
                        await self.ws.send(pong_msg.model_dump_json())
                        
                except Exception as e:
                    logger.error(f"[GatewayClient] 메시지 파싱/처리 에러: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.info("[GatewayClient] 서버에 의해 연결이 종료되었습니다.")
            self.ws = None
            logger.warning("[GatewayClient] 통신 단절. 로컬(Local) 모드로 전환합니다.")
            self.is_local_mode = True

    async def send_message(self, ws_message: WsMessage):
        """게이트웨이 서버로 메시지를 전송합니다 (로컬 모드가 아닐 때만)."""
        if not self.is_local_mode and self.ws:
            try:
                await self.ws.send(ws_message.model_dump_json())
            except Exception as e:
                logger.error(f"[GatewayClient] 전송 실패: {e}")

# 싱글톤 인스턴스
gateway_client = GatewayClient()
