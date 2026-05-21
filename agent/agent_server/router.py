"""
agent/agent_server/router.py

FastAPI 라우터 - 로컬 데스크탑 UI와 통신하며 게이트웨이 서버와 동기화합니다.
"""
import uuid
import logging
import json
import asyncio
from contextlib import asynccontextmanager

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import HumanMessage
from langgraph.types import Command

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    from entity import (
        WsMessage, TokenPayload, LogPayload, ApprovalRequestPayload, DonePayload,
        ChatPayload, ApprovalResponsePayload
    )
except ImportError:
    pass

from .gateway_client import gateway_client

logger = logging.getLogger(__name__)

# ==========================================
# Router Lifespan: Start GatewayClient
# ==========================================
@asynccontextmanager
async def router_lifespan(app: APIRouter):
    logger.info("Starting gateway client in Router Lifespan...")
    
    # 게이트웨이에서 수신한 명령을 처리할 핸들러 등록
    gateway_client.set_handlers(
        chat_handler=handle_gateway_chat,
        approve_handler=handle_gateway_approve,
        sync_handler=handle_gateway_sync
    )
    
    # 백그라운드 연결 시작 (자동 재시도 루프 포함)
    await gateway_client.connect()
    yield
    logger.info("Shutting down gateway client...")
    await gateway_client.disconnect()

router = APIRouter(lifespan=router_lifespan)

# ==========================================
# 에이전트 인스턴스 관리
# ==========================================
_agent = None

async def _get_or_create_agent():
    global _agent
    if _agent is None:
        from graph import create_agent
        _agent = await create_agent()
    return _agent

# 세션별 실행 락 (순차 처리를 보장)
session_locks = {}

def get_session_lock(session_id: str) -> asyncio.Lock:
    if session_id not in session_locks:
        session_locks[session_id] = asyncio.Lock()
    return session_locks[session_id]

# 중복 실행 방지 메모리: 게이트웨이와 로컬 파이프라인 혼합 시 중복 방지
executed_message_ids = set()

# DB의 UUID 필드와 호환되도록 기본값으로 UUID 형식을 사용함
DEFAULT_UUID = "00000000-0000-0000-0000-000000000000"

def _make_config(session_id: str) -> dict:
    user_id = DEFAULT_UUID
    return {"configurable": {"thread_id": f"{user_id}:{session_id}"}, "recursion_limit": 50}

async def _initial_state(payload: ChatPayload, session_id: str, existing_images: list = None, is_new_session: bool = False) -> dict:
    from utils.storage import upload_image
    
    if existing_images is None:
        existing_images = []
        
    new_uploaded_urls = []
    if payload.images:
        for img in payload.images[:3]:
            # 이미지 데이터가 이미 URL(http/https) 형식이면 업로드 생략
            if img.startswith("http"):
                # 게이트웨이가 생성한 URL (사용자ID/세션ID/UUID.png 조합)
                # 파일명 부분에서 UUID 추출 시도 (실패 시 랜덤 생성)
                image_uuid = img.split("/")[-1].split(".")[0] if "/" in img else str(uuid.uuid4())
                new_uploaded_urls.append({
                    "url": img,
                    "uuid": image_uuid,
                    "session_id": session_id
                })
            else:
                # Base64 데이터면 기존처럼 업로드 (로컬 모드 대응용)
                url_data = await upload_image(img, DEFAULT_UUID, session_id)
                new_uploaded_urls.append(url_data)
            
    content = payload.message
    total_image_count = len(existing_images) + len(new_uploaded_urls)
    if total_image_count > 0:
        content += f"\n\n[첨부된 이미지: {total_image_count}장]"

    messages = []
    if is_new_session:
        import httpx
        from langchain_core.messages import AIMessage
        api_server = os.getenv("API_SERVER", "http://localhost").rstrip("/")
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{api_server}/api/history/{session_id}", timeout=5.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data.get("history", []):
                        msg_text = item.get("message", "").strip()
                        if not msg_text or msg_text.startswith('{"plan"'):
                            continue
                            
                        if item["role"] == "user":
                            messages.append(HumanMessage(content=msg_text))
                        elif item["role"] == "agent":
                            messages.append(AIMessage(content=msg_text))
                    logger.info(f"[InitialState] 게이트웨이에서 {len(messages)}개의 대화 기록을 불러와 초기 상태에 주입했습니다.")
        except Exception as e:
            logger.error(f"[InitialState] 게이트웨이 히스토리 로드 실패: {e}")

    # 현재 들어온 메시지를 마지막에 추가
    messages.append(HumanMessage(content=content))

    return {
        "messages": messages,
        "original_request": payload.message,
        "plan": [],
        "current_task": "",
        "past_results": [],
        "active_worker": "",
        "tool_call_count": 0,
        "uploaded_images": new_uploaded_urls,
        "active_image_uuids": [img["uuid"] for img in new_uploaded_urls],
    }

# ==========================================
# 로컬 WebSocket 관리 (데스크탑 UI 브로드캐스트)
# ==========================================
class LocalConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: WsMessage):
        data = message.model_dump_json()
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                pass

local_manager = LocalConnectionManager()

async def broadcast_event(message: WsMessage):
    """로컬 UI와 게이트웨이 양쪽으로 메시지를 전송합니다."""
    # 1. 로컬 UI 브로드캐스트
    await local_manager.broadcast(message)
    # 2. 게이트웨이 전송 (연결된 경우에만)
    if not gateway_client.is_local_mode:
        await gateway_client.send_message(message)

# ==========================================
# LangGraph 실행 (공통)
# ==========================================
async def execute_agent(session_id: str, state=None, command=None):
    agent = await _get_or_create_agent()
    config = _make_config(session_id)
    
    # 노드별로 메시지를 그룹화하기 위한 추적용 ID
    current_msg_id = str(uuid.uuid4())
    
    try:
        stream_input = command if command else state
        async for event in agent.astream_events(stream_input, config=config, version="v2"):
            kind = event["event"]
            
            if kind == "on_chain_start":
                node_name = event.get("name", "")
                metadata = event.get("metadata", {})
                langgraph_node = metadata.get("langgraph_node", "")
                
                if langgraph_node and langgraph_node == node_name and not node_name.startswith("__") and node_name != "tools":
                    # 새로운 노드(단계) 시작 시 새로운 message_id 생성
                    current_msg_id = str(uuid.uuid4())
                    log_payload = LogPayload(status="node_start", node=node_name, message_id=current_msg_id, session_id=session_id)
                    await broadcast_event(WsMessage(type="log", payload=log_payload))
                    
            elif kind == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and chunk.content and isinstance(chunk.content, str):
                    # 현재 노드의 흐름에 속한 토큰들은 동일한 message_id 공유
                    token_payload = TokenPayload(chunk=chunk.content, message_id=current_msg_id, session_id=session_id)
                    await broadcast_event(WsMessage(type="token", payload=token_payload))

            elif kind == "on_tool_start":
                # 도구 실행은 별도의 로그 블록으로 취급하여 새로운 ID 부여
                tool_msg_id = str(uuid.uuid4())
                tool_name = event.get("name", "")
                tool_input = event["data"].get("input", "")
                log_payload = LogPayload(status="tool_start", tool_name=tool_name, tool_input=tool_input, message_id=tool_msg_id, session_id=session_id)
                await broadcast_event(WsMessage(type="log", payload=log_payload))

        final_state = await agent.aget_state(config)
        if final_state.tasks and len(final_state.tasks) > 0 and final_state.tasks[0].interrupts:
            interrupt_data = final_state.tasks[0].interrupts[0].value
            logger.info(f"[Agent] interrupt 발동: {interrupt_data['tool_name']}")
            app_payload = ApprovalRequestPayload(
                tool_call_id=interrupt_data["tool_call_id"],
                tool_name=interrupt_data["tool_name"],
                tool_args=interrupt_data["tool_args"],
                message=f"⚠️ 위험한 작업 감지\n도구: {interrupt_data['tool_name']}\n실행을 허용하시겠습니까?",
                session_id=session_id
            )
            await broadcast_event(WsMessage(type="approval_request", payload=app_payload))
        else:
            final_text = ""
            if final_state.values and "messages" in final_state.values:
                messages = final_state.values["messages"]
                if messages and messages[-1].type == "ai":
                    final_text = messages[-1].content
                    
            done_payload = DonePayload(final_message=final_text, message_id=current_msg_id, session_id=session_id)
            await broadcast_event(WsMessage(type="done", payload=done_payload))

    except Exception as e:
        import traceback
        trace = traceback.format_exc()
        logger.error(f"[Agent] 에이전트 실행 오류:\n{trace}")
        error_payload = LogPayload(status="error", message=f"에이전트 실행 실패: {e}", session_id=session_id)
        await broadcast_event(WsMessage(type="log", payload=error_payload))

# ==========================================
# Gateway로부터의 핸들러 (App -> Gateway -> Agent)
# ==========================================
async def handle_gateway_chat(payload: ChatPayload):
    session_id = payload.session_id
    
    # 중복 실행 방지 검사 (텍스트 전용 메시지의 경우 이미 로컬에서 실행됨)
    if payload.message_id in executed_message_ids:
        logger.info(f"[GatewayHandler] Already executed locally, skipping: {payload.message_id}")
        return

    # 게이트웨이(앱)에서 온 채팅 메시지를 로컬 UI에도 표시 (동기화)
    await local_manager.broadcast(WsMessage(type="chat", payload=payload))

    async def process_locked_chat():
        lock = get_session_lock(session_id)
        async with lock:
            # 상태 동기화: 시작
            status_msg = WsMessage(type="status", payload={"status": "busy", "session_id": session_id})
            await local_manager.broadcast(status_msg)
            await gateway_client.send_message(status_msg)

            try:
                logger.info(f"[GatewayHandler] Received chat. session_id={session_id}")
                agent = await _get_or_create_agent()
                config = _make_config(session_id)
                current_state = await agent.aget_state(config)
                is_new_session = not bool(current_state.values)
                existing_images = current_state.values.get("uploaded_images", []) if current_state.values else []
                
                state = await _initial_state(payload, session_id, existing_images, is_new_session=is_new_session)
                await execute_agent(session_id, state=state)
            finally:
                # 상태 동기화: 종료
                ready_msg = WsMessage(type="status", payload={"status": "ready", "session_id": session_id})
                await local_manager.broadcast(ready_msg)
                await gateway_client.send_message(ready_msg)

    asyncio.create_task(process_locked_chat())

async def handle_gateway_approve(payload: ApprovalResponsePayload):
    session_id = payload.session_id
    logger.info(f"[GatewayHandler] Received approve={payload.approve} for session={session_id}")
    
    # 게이트웨이(앱)에서 온 승인 여부를 로컬 UI에도 표시 (동기화)
    await local_manager.broadcast(WsMessage(type="approval_response", payload=payload))
    
    await execute_agent(session_id, command=Command(resume=payload.approve))

async def handle_gateway_sync(msg_type: str, payload: dict):
    """게이트웨이로부터 받은 세션 동기화 이벤트를 로컬 UI로 전달합니다."""
    logger.info(f"[GatewayHandler] Received sync event: {msg_type}")
    

    # WsMessage(type=msg_type, payload=payload)를 생성하여 브로드캐스트
    # entity.py의 WsMessage 규격을 따르되 payload는 raw dict를 허용함
    await local_manager.broadcast(WsMessage(type=msg_type, payload=payload))


# ==========================================
# 로컬 Desktop UI 웹소켓
# ==========================================
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await local_manager.connect(websocket)
    logger.info("[WebSocket] 데스크탑 UI 클라이언트 연결됨")

    if gateway_client.is_local_mode:
        log_payload = LogPayload(status="info", message="서버와 연결되지 않아 로컬 모드로 전환합니다. 대화 내용이 앱과 동기화되지 않습니다.", session_id="system")
        await websocket.send_text(WsMessage(type="log", payload=log_payload).model_dump_json())

    try:
        while True:
            raw_msg = await websocket.receive_text()
            try:
                msg = WsMessage.model_validate_json(raw_msg)
                
                if msg.type == "chat":
                    raw_data = json.loads(raw_msg)
                    chat_payload = ChatPayload.model_validate(raw_data.get("payload", {}))
                    session_id = chat_payload.session_id
                    
                    # msg 객체에 새로 생성된 message_id를 포함한 payload로 교체하여 일관성 유지
                    msg.payload = chat_payload
                    
                    async def process_chat_sequentially(sid, msg_obj, payload_obj):
                        lock = get_session_lock(sid)
                        async with lock:
                            # 실행 시작 알림 (모든 기기 버튼 비활성화용)
                            status_msg = WsMessage(type="status", payload={"status": "busy", "session_id": sid})
                            await local_manager.broadcast(status_msg)
                            if not gateway_client.is_local_mode:
                                await gateway_client.send_message(status_msg)
                            
                            try:
                                if not gateway_client.is_local_mode:
                                    if not payload_obj.images:
                                        executed_message_ids.add(payload_obj.message_id)
                                        await gateway_client.send_message(msg_obj)
                                        agent = await _get_or_create_agent()
                                        config = _make_config(sid)
                                        agent_state = await agent.aget_state(config)
                                        is_new_session = not bool(agent_state.values)
                                        state = await _initial_state(payload_obj, sid, 
                                                                   agent_state.values.get("uploaded_images", []) if agent_state.values else [], is_new_session=is_new_session)
                                        await execute_agent(sid, state=state)
                                    else:
                                        await gateway_client.send_message(msg_obj)
                                else:
                                    # 로컬 모드 처리
                                    if payload_obj.images:
                                        err_msg = WsMessage(type="log", payload=LogPayload(status="error", message="❌ 로컬 모드 이미지 불가", session_id=sid))
                                        await local_manager.broadcast(err_msg)
                                    else:
                                         agent = await _get_or_create_agent()
                                         config = _make_config(sid)
                                         agent_state = await agent.aget_state(config)
                                         is_new_session = not bool(agent_state.values)
                                         state = await _initial_state(payload_obj, sid, 
                                                                    agent_state.values.get("uploaded_images", []) if agent_state.values else [], is_new_session=is_new_session)
                                         await execute_agent(sid, state=state)
                            finally:
                                # 실행 종료 알림 (모든 기기 버튼 활성화용)
                                ready_msg = WsMessage(type="status", payload={"status": "ready", "session_id": sid})
                                await local_manager.broadcast(ready_msg)
                                if not gateway_client.is_local_mode:
                                    await gateway_client.send_message(ready_msg)

                    # 백그라운드 태스크로 실행하여 다른 메시지(세션 삭제 등) 처리를 방해하지 않음
                    asyncio.create_task(process_chat_sequentially(session_id, msg, chat_payload))
                    
                elif msg.type == "approval_response":
                    raw_data = json.loads(raw_msg)
                    app_payload = ApprovalResponsePayload.model_validate(raw_data.get("payload", {}))
                    session_id = app_payload.session_id
                    
                    if not gateway_client.is_local_mode:
                        # [온라인 모드] 게이트웨이로 전달
                        await gateway_client.send_message(msg)
                    else:
                        # [로컬 모드] 직접 처리
                        await execute_agent(session_id, command=Command(resume=app_payload.approve))
                
                elif msg.type in ["session_created", "session_deleted", "get_history"]:
                    if not gateway_client.is_local_mode:
                        logger.info(f"[WebSocket] Forwarding {msg.type} to Gateway: {msg.payload}")
                        await gateway_client.send_message(msg)
                    else:
                        logger.warning(f"[WebSocket] Cannot forward {msg.type}: Local mode active")
                
                elif msg.type == "register":
                    # 데스크탑 UI가 세션 정보를 보내며 등록하는 경우 (필요 시 처리)
                    pass
                    
            except Exception as e:
                logger.error(f"[WebSocket] 메시지 처리 오류: {e}")

                
    except WebSocketDisconnect:
        local_manager.disconnect(websocket)
        logger.info("[WebSocket] 데스크탑 UI 연결 종료")
