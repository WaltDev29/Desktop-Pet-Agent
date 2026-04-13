import logging
from fastapi import FastAPI
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