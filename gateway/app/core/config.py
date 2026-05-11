import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    TOKEN_EXPIRE_HOURS: int = int(os.getenv("TOKEN_EXPIRE_HOURS", "1"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://petagent:petpassword@localhost:5432/petagent_db")

    class Config:
        env_file = ".env"

settings = Settings()
