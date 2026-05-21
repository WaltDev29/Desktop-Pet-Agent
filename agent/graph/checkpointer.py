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

