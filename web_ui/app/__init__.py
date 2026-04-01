import os
import httpx
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8001")


def create_app() -> FastAPI:
    # ==========================================
    # Web UI Server (port 8000)
    # 사용자가 직접 접속하는 인터페이스입니다.
    # Agent Server(8001)에 HTTP 요청을 중계하는 역할만 담당합니다.
    # ==========================================
    app = FastAPI(
        title="Desktop Pet - Web UI",
        description="사용자 인터페이스. 채팅 요청을 Agent Server(8001)에 전달합니다.",
    )

    app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/static"), name="static")

    # ==========================================
    # 요청/응답 스키마
    # ==========================================
    class ChatRequest(BaseModel):
        message: str

    class ApprovalRequest(BaseModel):
        approve: bool
        tool_call_id: str

    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        """메인 채팅 UI(index.html)를 반환합니다."""
        try:
            with open(f"{BASE_DIR}/static/index.html", "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            return "<h1>index.html을 찾을 수 없습니다.</h1>"

    @app.post("/chat")
    async def chat_endpoint(request: ChatRequest):
        """
        사용자 메시지를 Agent Server로 전달하고 응답을 반환합니다.
        Web UI는 Agent 로직에 관여하지 않으며 순수 HTTP 중계만 수행합니다.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{AGENT_SERVER_URL}/chat",
                    json={"message": request.message},
                    timeout=120.0,  # LLM + Tool 실행 시간을 고려한 넉넉한 타임아웃
                )
            return JSONResponse(content=response.json())
        except httpx.ConnectError:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": f"Agent Server({AGENT_SERVER_URL})에 연결할 수 없습니다. Agent Server가 실행 중인지 확인하세요.",
                },
                status_code=503,
            )
        except Exception as e:
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500,
            )

    @app.post("/approve")
    async def approve_endpoint(request: ApprovalRequest):
        """
        사용자의 승인/거절 결과를 Agent Server로 전달합니다.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{AGENT_SERVER_URL}/approve",
                    json=request.model_dump(),
                    timeout=120.0,
                )
            return JSONResponse(content=response.json())
        except httpx.ConnectError:
            return JSONResponse(
                content={
                    "status": "error",
                    "message": "Agent Server에 연결할 수 없습니다.",
                },
                status_code=503,
            )
        except Exception as e:
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500,
            )

    return app
