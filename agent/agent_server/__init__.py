import logging
import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 환경변수 로드
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
logger = logging.getLogger(__name__)
logger.info(f"[Server] 환경 변수 로드 완료. API_SERVER: {os.getenv('API_SERVER')}")
from .router import router

# 기본적인 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)

# 에이전트 동작 및 MCP 서버 통신 로그 확인을 위한 상세 설정
logging.getLogger("graph.nodes").setLevel(logging.INFO)
logging.getLogger("agent_server.router").setLevel(logging.INFO)
logging.getLogger("langchain_mcp_adapters").setLevel(logging.DEBUG)
logging.getLogger("mcp").setLevel(logging.DEBUG)

# ==========================================
# Agent Server (port 8001)
# ==========================================

def create_app():
    app = FastAPI(
        title="Desktop Pet - Agent Server",
        description="LangGraph 에이전트 서버. Tool 실행은 Tool Server(8002)에 위임합니다.",
        version="1.0.0",
    )

    # CORS 설정 추가 (Web UI 브라우저 통신 허용 - 405 에러 해결)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router)

    return app