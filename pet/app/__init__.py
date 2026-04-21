import os
import uuid
import asyncio
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
AGENT_SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://localhost:8001")


def create_app() -> FastAPI:
    # ==========================================
    # Pet App Server (port 8000)
    # PySide6 UI와 Agent Server(8001) 사이의 중간 계층입니다.
    # HTTP 대신 WebSocket 기반으로 양방향 통신을 중계(Proxy)합니다.
    # ==========================================
    app = FastAPI(
        title="Desktop Pet - App Server",
        description="PySide6 UI와 Agent Server 사이의 중간 계층.",
    )

    @app.websocket("/ws")
    async def websocket_proxy_endpoint(client_ws: WebSocket):
        """
        프론트엔드(또는 PySide6)로부터 연결을 받아, 백엔드 Agent Server로 웹소켓을 연결하고
        서로의 메시지를 양방향으로 중계(Proxy)합니다.
        """
        await client_ws.accept()
        
        agent_ws_url = AGENT_SERVER_URL.replace("http://", "ws://").replace("https://", "wss://") + "/ws"

        try:
            # Agent Server(백엔드)와 웹소켓 연결
            async with websockets.connect(agent_ws_url) as agent_ws:
                
                # Client -> Agent 로 메시지 포워딩
                async def forward_to_agent():
                    try:
                        while True:
                            data = await client_ws.receive_text()
                            await agent_ws.send(data)
                    except WebSocketDisconnect:
                        pass  # 클라이언트 연동 종료
                    except Exception as e:
                        print(f"forward_to_agent error: {e}")

                # Agent -> Client 로 메시지 포워딩
                async def forward_to_client():
                    try:
                        while True:
                            data = await agent_ws.recv()
                            await client_ws.send_text(data)
                    except websockets.exceptions.ConnectionClosed:
                        pass  # 백엔드 연동 종료
                    except Exception as e:
                        print(f"forward_to_client error: {e}")

                # 양방향 포워딩 동시 실행
                await asyncio.gather(
                    forward_to_agent(),
                    forward_to_client(),
                    return_exceptions=True
                )
                
        except Exception as e:
            error_msg = f"Agent Server에 연결할 수 없습니다. ({e})"
            try:
                await client_ws.send_json({"status": "error", "message": error_msg})
                await client_ws.close()
            except Exception:
                pass

    return app

