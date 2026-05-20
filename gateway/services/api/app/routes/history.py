import uuid
import logging
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.database import get_db
from app.db.models import Message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/history", tags=["history"])

@router.get("/{session_id}")
async def get_session_history(session_id: str, db: AsyncSession = Depends(get_db)):
    """
    특정 세션의 대화 이력을 반환합니다.
    에이전트가 초기 컨텍스트를 구성할 때 호출됩니다.
    """
    try:
        session_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    stmt = select(Message).where(Message.session_id == session_uuid).order_by(Message.created_at.asc())
    result = await db.execute(stmt)
    
    history = []
    for m in result.scalars().all():
        history.append({
            "role": m.role,
            "message": m.content,
            "message_id": str(m.message_id),
            "created_at": m.created_at.isoformat()
        })
        
    return {"session_id": session_id, "history": history}
