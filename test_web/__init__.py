from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from pathlib import Path

from langchain_core.messages import HumanMessage, ToolMessage

BASE_DIR = Path(__file__).resolve().parent


# ==========================================
# 0. 전역 상태 변수
# MVP(최소 기능) 개발 버전이기 때문에 DB 대신 메모리 딕셔너리에 지난 대화 흐름을 임시로 저장합니다.
# ==========================================
current_state = {"messages": []}

def create_app(agent, tools):
    # ==========================================
    # 1. FastAPI 서버 기본 설정
    # 백엔드를 관장하는 웹 프레임워크입니다.
    # 클라이언트(index.html 챗봇 역할)와 통신하여 LLM의 대답을 전달합니다.
    # ==========================================
    app = FastAPI(title="OS Automation Agent")

    # 'static' 폴더 안에 있는 HTML/CSS/JS 파일들을 '/static' 주소에서 화면에 띄워주기 위한 마운트 작업
    app.mount("/static", StaticFiles(directory=f"{BASE_DIR}/static"), name="static")

    # ==========================================
    # 2. Pydantic 스키마 정의 (클라이언트가 보낼 데이터 그릇)
    # ==========================================
    class ChatRequest(BaseModel):
        message: str  # 채팅창에서 입력한 메시지

    class ApprovalRequest(BaseModel):
        approve: bool # '허용'을 누르면 True, '거절'을 누르면 False
        tool_call_id: str # 거절/허용의 대상이 되는 정확한 위험 도구의 고유 ID


    @app.get("/", response_class=HTMLResponse)
    async def read_root():
        """기본 홈 화면(http://localhost:8000) 접속 시 index.html 파일을 넘겨줍니다."""
        try:
            with open(f"{BASE_DIR}/static/index.html", "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return "static/index.html file not found."

    # ==========================================
    # 4. /chat 통신 (일반 메시지 전달 창구)
    # ==========================================
    @app.post("/chat")
    async def chat_endpoint(request: ChatRequest):
        global current_state
        
        # [1] 클라이언트(사람)가 보낸 메시지를 상태에 추가
        current_state["messages"].append(HumanMessage(content=request.message))
        
        try:
            # [2] LangGraph 에이전트 구동
            result = agent.invoke(current_state)
            current_state = result  # LLM이 쓴 답변을 상태에 저장
            
            # [3] 만약 다음 단계가 "승인(human_approval)"으로 대기 중이라면? (파일 삭제/생성 시)
            if result.get("next_step") == "human_approval":
                pending = result["pending_tool_call"]
                tool_name = pending["name"]
                tool_args = pending["args"]
                
                # 클라이언트에게 "승인이 필요한 위험 도구가 감지되었습니다" 하고 알려줍니다. UI에서 모달창이 뜹니다.
                return JSONResponse(content={
                    "status": "approval_required",
                    "message": f"위험한 작업({tool_name})이 감지되었습니다. 승인하시겠습니까?\n내용: {tool_args}",
                    "tool_call_id": pending["id"]
                })
                
            # [4] 별 문제 없고 안전한 작업이어서 LLM이 일반 답변을 만들어냈을 때
            last_message = result["messages"][-1]
            return JSONResponse(content={
                "status": "success",
                "message": last_message.content
            })
            
        except Exception as e:
            return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)

    # ==========================================
    # 5. /approve 통신 (강력한 보안 및 승인 창구)
    # 도구를 사용하는 허락 버튼을 눌렀을 때 작동하는 곳입니다.
    # ==========================================
    @app.post("/approve")
    async def approve_endpoint(request: ApprovalRequest):
        global current_state
        
        if not current_state.get("pending_tool_call"):
            return JSONResponse(content={"status": "error", "message": "No pending tool call found."})
            
        last_message = current_state["messages"][-1]
        if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
            return JSONResponse(content={"status": "error", "message": "No tool_calls in the last AI message."})
        
        # Case 1: [허용] 클릭!
        if request.approve:
            # LLM이 생성한 '도구 사용 목록'을 순회하며 하나씩 엽니다.
            for tc in last_message.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_call_id = tc["id"]
                
                # 파이썬 내부에서 우리가 구현했던 실제 함수(tool_obj)를 불러들여 직접(invoke) 사용합니다.
                tool_obj = next((t for t in tools if t.name == tool_name), None)
                if tool_obj:
                    try:
                        tool_result = tool_obj.invoke(tool_args)
                    except Exception as e:
                        tool_result = f"Error executing tool: {str(e)}"
                else:
                    tool_result = f"Tool {tool_name} not found."
                
                # ✅ 제일 중요한 부분!
                # OpenAI API에게 "나 너가 말한 거 실행해봤고 그 결과야!" 라고 
                # ToolMessage 구조체로 만들어 상태(state)에 쏙 집어넣어줍니다.
                tool_message = ToolMessage(content=str(tool_result), name=tool_name, tool_call_id=tool_call_id)
                current_state["messages"].append(tool_message)
                
            current_state["pending_tool_call"] = None
            
            # 다시 에이전트를 돌려 "도구를 돌린 결과(결과값)"을 토대로 최종 응답 문장("파일 생성을 완료했어요!")을 얻어냅니다.
            try:
                result = agent.invoke(current_state)
                current_state = result
                last_msg = result["messages"][-1]
                return JSONResponse(content={"status": "success", "message": last_msg.content})
            except Exception as e:
                return JSONResponse(content={"status": "error", "message": f"그래프 재개 오류: {str(e)}"}, status_code=500)
                
        # Case 2: [거절] 로 취소 클릭!
        else:
            # 보안 상 사용자가 거절했다는 메시지를 만들어서 오히려 LLM에게 줍니다. 
            # (LLM이 "아 사용자가 파일 지우는거 거부했구나" 하고 파악합니다)
            for tc in last_message.tool_calls:
                tool_message = ToolMessage(content="사용자가 명령 실행을 거절하였습니다.", name=tc["name"], tool_call_id=tc["id"])
                current_state["messages"].append(tool_message)
                
            current_state["pending_tool_call"] = None
            
            try:
                result = agent.invoke(current_state)
                current_state = result
                last_msg = result["messages"][-1]
                return JSONResponse(content={"status": "rejected", "message": last_msg.content})
            except Exception as e:
                return JSONResponse(content={"status": "error", "message": f"거절 후 그래프 재개 오류: {str(e)}"}, status_code=500)
            

    return app