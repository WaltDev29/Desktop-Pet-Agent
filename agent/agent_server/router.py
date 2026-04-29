"""
agent/agent_server/router.py

FastAPI 라우터 - 에이전트와 Web UI 간의 인터페이스를 제공합니다.

세션 관리:
  - session_id: HttpOnly 쿠키로 자동 발급/관리 (Web UI 코드 변경 불필요)
  - thread_id: f"{user_id}:{session_id}" 형태로 구성
      - 지금(MVP): user_id = "default" 고정
      - 나중(멀티유저): JWT 토큰에서 user_id를 추출하여 교체

사용자 승인 흐름 (LangGraph interrupt 방식):
  [Worker 내부] interrupt() 발동
    → ainvoke가 즉시 반환, result에 "__interrupt__" 키 포함
    → API가 프론트엔드에 approval_required 반환
  [사용자 승인/거절]
    → /approve API에서 Command(resume=True/False) 전달
    → 그래프가 interrupt() 바로 다음부터 재개
"""

import uuid
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from langgraph.types import Command

logger = logging.getLogger(__name__)

router = APIRouter()

class ChatPayload(BaseModel):
    message: str
    images: list[str] = []         # base64 인코딩된 이미지 문자열 리스트 (최대 3개 제한)
    session_id: str | None = None

class ApprovePayload(BaseModel):
    approve: bool                  # True: 허용 / False: 거절
    session_id: str | None = None

# ==========================================
# 에이전트 지연 초기화 (순환 임포트 방지)
# ==========================================
_agent = None

async def _get_or_create_agent():
    global _agent
    if _agent is None:
        from graph import create_agent
        _agent = await create_agent()
    return _agent


def _make_config(session_id: str) -> dict:
    user_id = "default"  # MVP: 단일 사용자 고정
    return {"configurable": {"thread_id": f"{user_id}:{session_id}"}}


async def _initial_state(payload: ChatPayload, session_id: str, existing_images: list = None) -> dict:
    from utils.storage import upload_image
    
    if existing_images is None:
        existing_images = []
        
    new_uploaded_urls = []
    if payload.images:
        for img in payload.images[:3]:
            # 업로드 수행 후 반환된 식별용 URL 저장
            url_data = await upload_image(img, "default", session_id)
            new_uploaded_urls.append(url_data)
            
    # LLM 메인 프롬프트에는 이미지 본문을 넣지 않음 (순수 텍스트만)
    content = payload.message
    total_image_count = len(existing_images) + len(new_uploaded_urls)
    
    if total_image_count > 0:
        content += f"\n\n[첨부된 이미지: {total_image_count}장]"

    return {
        "messages":        [HumanMessage(content=content)],
        "original_request": payload.message,
        "plan":            [],
        "current_task":    "",
        "past_results":    [],
        "active_worker":   "",
        "tool_call_count": 0,
        "uploaded_images": new_uploaded_urls, # operator.add에 의해 기존 이미지와 합쳐짐
        "active_image_uuids": [img["uuid"] for img in new_uploaded_urls], # 이번 턴에 올라온 것들만 마킹
    }


# ==========================================
# /ws
# ==========================================

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("[WebSocket] 클라이언트 연결됨")

    try:
        while True:
            data = await websocket.receive_json()
            action = data.get("action")

            if action == "chat":
                payload = ChatPayload(**data)
                session_id = payload.session_id or str(uuid.uuid4())
                logger.info(f"[WebSocket-Chat] thread_id=default:{session_id[:8]}...")

                agent = await _get_or_create_agent()
                config = _make_config(session_id)
                
                # 기존 상태 확인 (이전 대화에서 올린 이미지가 있는지 파악)
                current_state = agent.get_state(config)
                existing_images = current_state.values.get("uploaded_images", []) if current_state.values else []
                
                state = await _initial_state(payload, session_id, existing_images)

                try:
                    async for event in agent.astream_events(state, config={**config, "recursion_limit": 50}, version="v2"):
                        kind = event["event"]
                        
                        if kind == "on_chain_start":
                            node_name = event.get("name", "")
                            metadata = event.get("metadata", {})
                            langgraph_node = metadata.get("langgraph_node", "")
                            
                            # langgraph_node 메타데이터가 존재하고 이벤트 이름과 일치할 때(최상위 노드)만
                            if langgraph_node and langgraph_node == node_name and not node_name.startswith("__") and node_name != "tools":
                                await websocket.send_json({"status": "node_start", "node": node_name})
                                
                        elif kind == "on_chat_model_stream":
                            chunk = event["data"].get("chunk")
                            if chunk:
                                content = chunk.content
                                if isinstance(content, str) and content:
                                    await websocket.send_json({"status": "stream_chunk", "chunk": content})

                        elif kind == "on_tool_start":
                            tool_name = event.get("name", "")
                            tool_input = event["data"].get("input", "")
                            await websocket.send_json({
                                "status": "tool_start",
                                "tool_name": tool_name,
                                "tool_input": tool_input
                            })

                    final_state = agent.get_state(config)
                    if final_state.tasks and len(final_state.tasks) > 0 and final_state.tasks[0].interrupts:
                        interrupt_data = final_state.tasks[0].interrupts[0].value
                        logger.info(f"[WebSocket-Chat] interrupt 발동: {interrupt_data['tool_name']}")
                        await websocket.send_json({
                            "status":       "approval_required",
                            "message":      (
                                f"⚠️ 위험한 작업 감지\n"
                                f"도구: {interrupt_data['tool_name']}\n"
                                f"내용: {interrupt_data['tool_args']}\n\n"
                                f"실행을 허용하시겠습니까?"
                            ),
                            "tool_call_id": interrupt_data["tool_call_id"],
                            "session_id": session_id,
                        })
                    else:
                        await websocket.send_json({
                            "status": "stream_end", 
                            "session_id": session_id
                        })
                except Exception as e:
                    import traceback
                    trace = traceback.format_exc()
                    logger.error(f"[WebSocket-Chat] 에이전트 실행 오류:\n{trace}")
                    await websocket.send_json({"status": "error", "message": f"에이전트 실행 실패: {e}"})

            elif action == "approve":
                payload = ApprovePayload(**data)
                session_id = payload.session_id
                
                if not session_id:
                    await websocket.send_json({"status": "error", "message": "세션이 없습니다. 새로 대화를 시작해주세요."})
                    continue
                    
                logger.info(f"[WebSocket-Approve] thread_id=default:{session_id[:8]}...")
                
                agent = await _get_or_create_agent()
                config = _make_config(session_id)

                try:
                    async for event in agent.astream_events(Command(resume=payload.approve), config={**config, "recursion_limit": 50}, version="v2"):
                        kind = event["event"]
                        
                        if kind == "on_chain_start":
                            node_name = event.get("name", "")
                            metadata = event.get("metadata", {})
                            langgraph_node = metadata.get("langgraph_node", "")
                            
                            # langgraph_node 메타데이터가 존재하고 이벤트 이름과 일치할 때(최상위 노드)만
                            if langgraph_node and langgraph_node == node_name and not node_name.startswith("__") and node_name != "tools":
                                await websocket.send_json({"status": "node_start", "node": node_name})
                                
                        elif kind == "on_chat_model_stream":
                            chunk = event["data"].get("chunk")
                            if chunk:
                                content = chunk.content
                                if isinstance(content, str) and content:
                                    await websocket.send_json({"status": "stream_chunk", "chunk": content})

                        elif kind == "on_tool_start":
                            tool_name = event.get("name", "")
                            tool_input = event["data"].get("input", "")
                            await websocket.send_json({
                                "status": "tool_start",
                                "tool_name": tool_name,
                                "tool_input": tool_input
                            })

                    final_state = agent.get_state(config)
                    if final_state.tasks and len(final_state.tasks) > 0 and final_state.tasks[0].interrupts:
                        interrupt_data = final_state.tasks[0].interrupts[0].value
                        await websocket.send_json({
                            "status":       "approval_required",
                            "message":      (
                                f"⚠️ 또 다른 위험 작업이 감지되었습니다.\n"
                                f"도구: {interrupt_data['tool_name']}\n"
                                f"내용: {interrupt_data['tool_args']}"
                            ),
                            "tool_call_id": interrupt_data["tool_call_id"],
                            "session_id": session_id,
                        })
                    else:
                        await websocket.send_json({
                            "status": "stream_end", 
                            "session_id": session_id
                        })
                except Exception as e:
                    import traceback
                    trace = traceback.format_exc()
                    logger.error(f"[WebSocket-Approve] 재개 오류:\n{trace}")
                    await websocket.send_json({"status": "error", "message": f"재개 중 오류 발생: {e}"})
                    
            elif action == "delete_session":
                payload = data.get("session_id")
                if payload:
                    from utils.storage import delete_session_images
                    await delete_session_images("default", payload)
                    await websocket.send_json({"status": "success", "message": f"세션 {payload} 이미지 기록 삭제 완료."})
                else:
                    await websocket.send_json({"status": "error", "message": "session_id가 없습니다."})
                    
            else:
                await websocket.send_json({"status": "error", "message": "알 수 없는 action 타입입니다."})

    except WebSocketDisconnect:
        logger.info("[WebSocket] 클라이언트 연결 종료")
    except Exception as e:
        logger.error(f"[WebSocket] 예기치 않은 오류 발생: {e}")
