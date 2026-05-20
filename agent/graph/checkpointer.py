import os
import logging
from langgraph.checkpoint.memory import MemorySaver

logger = logging.getLogger(__name__)

async def get_checkpointer():
    """
    게이트웨이에서 대화 기록(Context)을 텍스트로 주입받고,
    상태 관리는 로컬 메모리(MemorySaver)에서 가볍게 처리합니다.
    (재시작 시 초기화되나 데스크톱 환경상 문제 없음)
    """
    logger.info("[Checkpointer] MemorySaver 사용 (무상태 메모리 모드)")
    return MemorySaver()

async def delete_session_checkpoints(session_id: str, user_id: str = None):
    """
    MemorySaver를 사용하므로 DB에서 삭제할 필요가 없습니다.
    """
    logger.info(f"[Checkpointer] 세션 {session_id} 삭제 요청 수신. (MemorySaver 모드이므로 무시됨)")

async def clean_orphaned_checkpoints(valid_sessions: list, user_id: str = None):
    """
    MemorySaver를 사용하므로 찌꺼기 청소 로직이 불필요합니다.
    """
    logger.info("[Checkpointer] MemorySaver 모드이므로 찌꺼기 상태 정리를 생략합니다.")
