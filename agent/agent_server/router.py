from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage, ToolMessage

from .tool_client import _call_tool_server

# ==========================================
# 전역 대화 상태
# MVP 버전: DB 대신 메모리 딕셔너리로 관리
# ==========================================
current_state: dict = {"messages": []}

router = APIRouter()


class ChatRequest(BaseModel):
    message: str

class ApprovalRequest(BaseModel):
    approve: bool          # True: 허용, False: 거절
    tool_call_id: str      # 승인/거절 대상 Tool의 고유 ID


def get_agent():
    """순환 임포트 방지를 위해 agent를 지연 import합니다."""
    from graph import create_agent
    return create_agent()


# Agent 인스턴스 (서버 시작 시 1회 초기화)
_agent = None

def _get_or_create_agent():
    global _agent
    if _agent is None:
        _agent = get_agent()
    return _agent


@router.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    사용자 메시지를 받아 LangGraph 에이전트를 실행합니다.
    - 일반 Tool(CPU/메모리 등): Tool Server 실행 결과를 받아 LLM이 최종 응답 생성
    - 위험 Tool(파일 삭제 등): human_approval 상태로 반환, Web UI에서 승인 모달 표시
    """
    global current_state
    agent = _get_or_create_agent()

    # [1] 사용자 메시지 상태에 추가
    current_state["messages"].append(HumanMessage(content=request.message))

    try:
        # [2] LangGraph 에이전트 실행
        #     - 일반 Tool: ToolNode → proxy → Tool Server HTTP 호출 → 결과 반환
        #     - 위험 Tool: human_approval_node에서 그래프 정지
        result = agent.invoke(current_state)
        current_state = result

        # [3] 위험 Tool 승인 대기 상태인 경우
        if result.get("next_step") == "human_approval":
            pending = result["pending_tool_call"]
            return JSONResponse(content={
                "status": "approval_required",
                "message": f"위험한 작업({pending['name']})이 감지되었습니다. 승인하시겠습니까?\n내용: {pending['args']}",
                "tool_call_id": pending["id"],
            })

        # [4] 정상 완료: LLM이 Tool 결과를 읽고 생성한 최종 응답
        last_message = result["messages"][-1]
        return JSONResponse(content={
            "status": "success",
            "message": last_message.content,
        })

    except Exception as e:
        return JSONResponse(
            content={"status": "error", "message": str(e)},
            status_code=500,
        )


@router.post("/approve")
async def approve_endpoint(request: ApprovalRequest):
    """
    Web UI의 승인/거절 결과를 받아 처리합니다.
    - 허용: Tool Server에 approved=True로 HTTP 요청 → 결과를 ToolMessage로 상태에 추가 → 에이전트 재개
    - 거절: 거절 메시지를 ToolMessage로 상태에 추가 → 에이전트 재개
    """
    global current_state
    agent = _get_or_create_agent()

    if not current_state.get("pending_tool_call"):
        return JSONResponse(content={"status": "error", "message": "대기 중인 Tool 호출이 없습니다."})

    last_message = current_state["messages"][-1]
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return JSONResponse(content={"status": "error", "message": "마지막 메시지에 tool_calls가 없습니다."})

    # [허용] 클릭: Tool Server에 approved=True로 요청
    if request.approve:
        for tc in last_message.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            # Tool Server에 직접 HTTP 요청 (approved=True 플래그 포함)
            tool_result = _call_tool_server(tool_name, tool_args, approved=True)

            # LLM이 Tool 결과를 읽을 수 있도록 ToolMessage로 상태에 추가
            tool_message = ToolMessage(
                content=str(tool_result),
                name=tool_name,
                tool_call_id=tool_call_id,
            )
            current_state["messages"].append(tool_message)

        current_state["pending_tool_call"] = None

        try:
            result = agent.invoke(current_state)
            current_state = result
            last_msg = result["messages"][-1]
            return JSONResponse(content={"status": "success", "message": last_msg.content})
        except Exception as e:
            return JSONResponse(
                content={"status": "error", "message": f"에이전트 재개 오류: {str(e)}"},
                status_code=500,
            )

    # [거절] 클릭: LLM에게 거절 사실을 ToolMessage로 전달
    else:
        for tc in last_message.tool_calls:
            tool_message = ToolMessage(
                content="사용자가 명령 실행을 거절하였습니다.",
                name=tc["name"],
                tool_call_id=tc["id"],
            )
            current_state["messages"].append(tool_message)

        current_state["pending_tool_call"] = None

        try:
            result = agent.invoke(current_state)
            current_state = result
            last_msg = result["messages"][-1]
            return JSONResponse(content={"status": "rejected", "message": last_msg.content})
        except Exception as e:
            return JSONResponse(
                content={"status": "error", "message": f"거절 후 에이전트 재개 오류: {str(e)}"},
                status_code=500,
            )
