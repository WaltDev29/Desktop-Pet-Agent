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
            
            if not session_id or session_id == "system":
                # Handle system messages (ping/pong)
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "payload": {"session_id": "system"}})
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
                
                new_msg = Message(
                    message_id=uuid.UUID(message_id) if message_id else uuid.uuid4(),
                    session_id=uuid.UUID(session_id),
                    role="user",
                    status="done",
                    content=content
                )
                db.add(new_msg)
                await db.commit()
                
                # Forward to target
                await manager.send_to_role(user_id, target_role, data)

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
