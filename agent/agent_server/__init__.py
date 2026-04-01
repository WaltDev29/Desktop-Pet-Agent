from fastapi import FastAPI
from .router import router

# ==========================================
# Agent Server (port 8001)
# LangGraph 에이전트를 실행하는 서버입니다.
# Web UI의 채팅 요청을 받아 에이전트를 구동하고,
# Tool 실행이 필요할 때 Tool Server(8002)에 HTTP 요청을 보냅니다.
# ==========================================

def create_app():
    app = FastAPI(
        title="Desktop Pet - Agent Server",
        description="LangGraph 에이전트 서버. Tool 실행은 Tool Server(8002)에 위임합니다.",
        version="1.0.0",
    )

    app.include_router(router)

    return app