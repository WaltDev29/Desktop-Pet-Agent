import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Session, Message, MessageLog
from app.core.connection import manager

logger = logging.getLogger(__name__)

router = APIRouter()

async def create_or_get_session(db: AsyncSession, session_id: str, user_id: str):
    stmt = select(Session).where(Session.session_id == uuid.UUID(session_id))
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        session = Session(session_id=uuid.UUID(session_id), user_id=uuid.UUID(user_id))
        db.add(session)
        await db.commit()
    return session

@router.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    user_id: str,
    db: AsyncSession = Depends(get_db)
):
    # Wait for the first register message
    await websocket.accept()
    
    client_id = None
    role = None
    
    try:
        data = await websocket.receive_json()
        if data.get("type") == "register":
            payload = data.get("payload", {})
            role = payload.get("role")
            client_id = payload.get("client_id")
            
            if not role or not client_id:
                await websocket.close(code=1008)
                return
                
            # Officially connect via manager
            # Since websocket is already accepted, we just register it
            manager.active_connections[user_id][role][client_id] = websocket
            logger.info(f"Registered: user_id={user_id}, role={role}, client_id={client_id}")
            
        else:
            await websocket.close(code=1008)
            return

        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")
            payload = data.get("payload", {})
            session_id = payload.get("session_id")
            message_id = payload.get("message_id")
            
            # 시스템 메시지(Ping) 처리 - session_id 불필요
            if msg_type == "ping":
                await websocket.send_json({"type": "pong", "payload": {}})
                continue

            # 대화 관련 메시지인데 session_id나 message_id가 없는 경우 무시
            if not session_id or not message_id:
                logger.warning(f"Missing identifiers: session_id={session_id}, message_id={message_id}")
                continue

            # Ensure session exists in DB
            try:
                await create_or_get_session(db, session_id, user_id)
            except Exception as e:
                logger.error(f"Session creation failed: {e}")
                continue

            # Route messages based on sender role
            target_role = "agent" if role == "app" else "app"
            
            if msg_type == "chat":
                # User (App or Agent UI) sends a chat
                content = payload.get("message", "")
                images = payload.get("images", [])
                processed_images = []
                
                # Base64 이미지 처리
                import base64
                import os
                from app.core.config import settings
                import jwt
                import time

                for img_data in images:
                    if img_data.startswith("data:image"):
                        try:
                            header, encoded = img_data.split(",", 1)
                            ext = "." + header.split("/")[1].split(";")[0]
                            image_uuid = str(uuid.uuid4())
                            
                            session_dir = os.path.join(settings.UPLOAD_DIR, user_id, session_id)
                            os.makedirs(session_dir, exist_ok=True)
                            
                            file_path = os.path.join(session_dir, f"{image_uuid}{ext}")
                            with open(file_path, "wb") as f:
                                f.write(base64.b64decode(encoded))
                            
                            # Signed URL 생성 (WebSocket에서는 Request 객체가 없으므로 설정 기반 URL 사용 권장하나 우선 상대경로/더미 도메인으로 구성)
                            # 실제 환경에서는 settings.BASE_URL 등을 사용해야 함.
                            expire = time.time() + (settings.TOKEN_EXPIRE_HOURS * 3600)
                            token_payload = {"user_id": user_id, "session_id": session_id, "image_uuid": image_uuid, "exp": expire}
                            token = jwt.encode(token_payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
                            
                            # 포트 80이 호스트에 매핑되어 있으므로 localhost:80 (또는 실제 도메인) 사용
                            image_url = f"http://localhost/view/{user_id}/{session_id}/{image_uuid}?token={token}"
                            processed_images.append(image_url)
                        except Exception as e:
                            logger.error(f"Image processing failed: {e}")
                            processed_images.append(img_data) # 실패 시 원본 유지
                    else:
                        processed_images.append(img_data)
                
                # 페이로드 업데이트
                payload["images"] = processed_images
                # message_id가 누락되었을 경우를 대비하여 DB에 저장되는 ID를 명시적으로 주입 (App과 Agent의 동기화 보장)
                generated_id = uuid.UUID(message_id) if message_id else uuid.uuid4()
                payload["message_id"] = str(generated_id)
                data["payload"] = payload
                
                new_msg = Message(
                    message_id=generated_id,
                    session_id=uuid.UUID(session_id),
                    role="user",
                    status="done",
                    content=content
                )
                db.add(new_msg)
                await db.commit()
                
                # 모든 역할(Agent, App)에게 브로드캐스트 (에이전트가 수신하여 실행하기 위함)
                await manager.send_to_role(user_id, "agent", data)
                await manager.send_to_role(user_id, "app", data)

            elif msg_type == "log":
                status = payload.get("status")
                node = payload.get("node")
                tool_name = payload.get("tool_name")
                
                # Create empty message if node_start or tool_start
                if status in ("node_start", "tool_start"):
                    new_msg = Message(
                        message_id=uuid.UUID(message_id),
                        session_id=uuid.UUID(session_id),
                        role="agent",
                        status="streaming",
                        content=""
                    )
                    db.add(new_msg)
                
                # Save log
                new_log = MessageLog(
                    message_id=uuid.UUID(message_id),
                    step=node or tool_name,
                    detail=payload.get("message") or status
                )
                db.add(new_log)
                await db.commit()
                
                await manager.send_to_role(user_id, target_role, data)
                
            elif msg_type == "token":
                chunk = payload.get("chunk", "")
                await manager.buffer_token(message_id, chunk)
                await manager.send_to_role(user_id, target_role, data)
                
            elif msg_type == "done":
                # Finalize message in DB
                stmt = select(Message).where(Message.message_id == uuid.UUID(message_id))
                result = await db.execute(stmt)
                msg = result.scalar_one_or_none()
                if msg:
                    msg.status = "done"
                    msg.content = payload.get("final_message", msg.content)
                    await db.commit()
                
                await manager.flush_tokens_to_db() # Force flush
                await manager.send_to_role(user_id, target_role, data)

            elif msg_type in ["approval_request", "approval_response"]:
                await manager.send_to_role(user_id, target_role, data)

    except WebSocketDisconnect:
        if role and client_id:
            manager.disconnect(user_id, role, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if role and client_id:
            manager.disconnect(user_id, role, client_id)
