import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from .db.database import engine, Base
from .core.config import settings
from .core.connection import start_flush_worker, stop_flush_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("DEBUG: Gateway lifespan starting...")
    # DB 스키마 생성 (로컬 테스트용)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # 기본 테스트 유저 생성 (00000000-0000-0000-0000-000000000000)
    from .db.database import AsyncSessionLocal
    from .db.models import User
    import uuid
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        default_user_id = uuid.UUID("00000000-0000-0000-0000-000000000000")
        result = await session.execute(select(User).where(User.user_id == default_user_id))
        if not result.scalar_one_or_none():
            default_user = User(
                user_id=default_user_id,
                email="default@example.com",
                password="dummy_password",
                name="Default User"
            )
            session.add(default_user)
            await session.commit()
            
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    
    # 주기적 Flush 워커 시작
    start_flush_worker()
    
    yield
    
    # 주기적 Flush 워커 종료
    await stop_flush_worker()

def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)

    # 라우터 등록
    from .routes import images, ws, history
    app.include_router(images.router)
    app.include_router(ws.router)
    app.include_router(history.router)

    return app
