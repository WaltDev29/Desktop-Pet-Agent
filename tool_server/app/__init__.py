from fastapi import FastAPI
from .router import router

# ==========================================
# Tool Server (port 8002)
# 사용자 컴퓨터에서 실행되는 서버입니다.
# Agent 서버의 HTTP 요청을 받아 실제 Tool 함수를 실행하고 결과를 반환합니다.
# ==========================================
def create_app():
    app = FastAPI(
        title="Desktop Pet - Tool Server",
        description="Agent 서버의 요청을 받아 사용자 PC의 Tool을 실행합니다.",
        version="1.0.0",
    )

    app.include_router(router)

    return app
