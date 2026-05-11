import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Default URL just in case, but docker-compose injects the correct one
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://petagent:petpassword@localhost:5432/petagent_db")

engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
