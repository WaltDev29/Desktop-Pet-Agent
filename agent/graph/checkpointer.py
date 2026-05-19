import os
import logging
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

# 전역 비동기 커넥션 풀 인스턴스
_pool = None


async def get_checkpointer():
    """
    환경변수 DATABASE_URL에 따라 적합한 비동기 체크포인터를 반환합니다.

    [지금  MVP] DATABASE_URL 미설정 → MemorySaver (메모리/비동기 지원, 재시작 시 초기화)
    [나중 운영] DATABASE_URL 설정    → AsyncPostgresSaver (DB 영구 저장, psycopg AsyncConnectionPool 기반)
    """
    global _pool
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        try:
            if _pool is None:
                logger.info(f"[Checkpointer] AsyncConnectionPool 초기화 중 (URL: {db_url.split('@')[-1]})")
                # 비동기식 ConnectionPool 생성 및 오픈
                _pool = AsyncConnectionPool(conninfo=db_url, max_size=10, open=True, kwargs={"autocommit": True})
            
            logger.info("[Checkpointer] AsyncPostgresSaver 사용 (DB 영구 저장 모드)")
            saver = AsyncPostgresSaver(_pool)
            # 필요한 DB 테이블(checkpoints 등)이 없다면 자동으로 생성합니다.
            await saver.setup()
            return saver
        except Exception as e:
            logger.error(f"[Checkpointer] AsyncPostgresSaver 초기화 실패: {e}")
            logger.warning("MemorySaver로 대체합니다.")

    from langgraph.checkpoint.memory import MemorySaver
    logger.info("[Checkpointer] MemorySaver 사용 (메모리 기반 MVP 모드)")
    return MemorySaver()
