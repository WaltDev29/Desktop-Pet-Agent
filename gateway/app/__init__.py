import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .db.database import engine, Base
from .core.config import settings
from .core.connection import start_flush_worker, stop_flush_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # DB 스키마 생성 (로컬 테스트용, 실제 프로덕션은 alembic 사용 권장)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 주기적 Flush 워커 시작
    start_flush_worker()
    
    yield
    
    # 주기적 Flush 워커 종료
    await stop_flush_worker()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # 라우터 등록
    from .routes import images, ws
    app.include_router(images.router)
    app.include_router(ws.router)

    return app
