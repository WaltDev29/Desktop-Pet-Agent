import os
import logging
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

logger = logging.getLogger(__name__)

# 전역 비동기 커넥션 풀 인스턴스
_pool = None

async def _ensure_pool():
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            logger.info(f"[Checkpointer] AsyncConnectionPool 초기화 중 (URL: {db_url.split('@')[-1]})")
            _pool = AsyncConnectionPool(conninfo=db_url, max_size=10, open=True, kwargs={"autocommit": True})

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
            await _ensure_pool()
            if _pool:
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

async def delete_session_checkpoints(session_id: str, user_id: str = None):
    """
    세션이 삭제될 때 DB에 남아있는 LangGraph 상태(checkpoints)를 정리합니다.
    추후 멀티유저 환경을 고려하여 user_id를 주입받을 수 있도록 설계되었습니다.
    """
    global _pool
    await _ensure_pool()
    if not _pool:
        logger.warning("[Checkpointer] DB 커넥션 풀이 없어 삭제 작업을 수행할 수 없습니다.")
        return

    # 제공된 user_id가 없으면 환경변수나 기본값 사용
    if not user_id:
        user_id = os.getenv("USER_ID", "00000000-0000-0000-0000-000000000000")
        
    thread_id = f"{user_id}:{session_id}"
    
    try:
        async with _pool.connection() as conn:
            # LangGraph에서 생성하는 3개의 상태 테이블의 데이터 일괄 삭제
            await conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))
            await conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
            await conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
            logger.info(f"[Checkpointer] 세션 {session_id}의 에이전트 상태가 DB에서 정리되었습니다 (thread_id: {thread_id}).")
    except Exception as e:
        if "does not exist" in str(e):
            logger.info(f"[Checkpointer] checkpoints 테이블이 아직 생성되지 않아 세션 {session_id} 삭제 처리를 스킵합니다. (첫 대화 시 자동 생성 예정)")
        else:
            logger.error(f"[Checkpointer] 세션 상태 삭제 중 오류 발생: {e}")

async def clean_orphaned_checkpoints(valid_sessions: list, user_id: str = None):
    """
    게이트웨이의 전체 유효 세션 목록과 에이전트 DB의 상태를 비교하여,
    게이트웨이에 없는 찌꺼기 상태(Orphan Checkpoints)를 일괄 청소합니다.
    """
    global _pool
    await _ensure_pool()
    if not _pool:
        return

    if not user_id:
        user_id = os.getenv("USER_ID", "00000000-0000-0000-0000-000000000000")
        
    try:
        async with _pool.connection() as conn:
            # 1. DB에 있는 해당 user_id의 모든 thread_id를 조회
            result = await conn.execute("SELECT DISTINCT thread_id FROM checkpoints WHERE thread_id LIKE %s", (f"{user_id}:%",))
            db_threads = [row[0] for row in await result.fetchall()]
            
            # 2. valid_sessions 리스트를 바탕으로 유지해야 할 thread_id set 생성
            valid_threads = set(f"{user_id}:{sid}" for sid in valid_sessions)
            
            # 3. 고아 thread_id 식별
            orphans = [tid for tid in db_threads if tid not in valid_threads]
            
            if orphans:
                logger.info(f"[Checkpointer] {len(orphans)}개의 찌꺼기 상태(Orphan Checkpoints)를 발견하여 청소합니다.")
                for orphan_tid in orphans:
                    await conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (orphan_tid,))
                    await conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (orphan_tid,))
                    await conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (orphan_tid,))
                logger.info("[Checkpointer] 찌꺼기 상태 청소 완료.")
            else:
                logger.info("[Checkpointer] 찌꺼기 상태가 없습니다. (Clean)")
    except Exception as e:
        if "does not exist" in str(e):
            logger.info("[Checkpointer] checkpoints 테이블이 아직 생성되지 않아 찌꺼기 상태 정리를 스킵합니다. (첫 대화 시 자동 생성 예정)")
        else:
            logger.error(f"[Checkpointer] 찌꺼기 상태 청소 중 오류 발생: {e}")
