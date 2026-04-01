from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict

from . import filesystem_tool, system_monitor_tool, web_search_tool

router = APIRouter()

# ==========================================
# Tool 레지스트리: 이름 → Tool 객체 매핑
# ==========================================
TOOLS: Dict[str, Any] = {}
for t in [
    *filesystem_tool.tools,
    *system_monitor_tool.tools,
    *web_search_tool.tools,
]:
    TOOLS[t.name] = t

# ==========================================
# 위험 Tool 목록: 사용자 승인 없이는 실행 불가
# ==========================================
DANGEROUS_TOOLS = {"write_file_tool", "delete_file_tool"}


class ExecuteRequest(BaseModel):
    tool_name: str
    args: Dict[str, Any] = {}
    # Agent 서버에서 사용자 승인을 받은 경우에만 True가 됩니다.
    approved: bool = False


@router.get("/tools")
async def list_tools():
    """등록된 Tool 목록과 스키마를 반환합니다. (디버깅/확인용)"""
    return {
        "tools": [
            {
                "name": name,
                "description": tool.description,
                "dangerous": name in DANGEROUS_TOOLS,
            }
            for name, tool in TOOLS.items()
        ]
    }


@router.post("/execute")
async def execute_tool(request: ExecuteRequest):
    """
    Agent 서버의 요청을 받아 실제 Tool 함수를 실행합니다.

    - 일반 Tool: 즉시 실행 → 결과 반환 (Agent가 LLM 응답 생성에 활용)
    - 위험 Tool: approved=True일 때만 실행 (파일 삭제·쓰기 등 파괴적 작업)
    """
    tool = TOOLS.get(request.tool_name)
    if not tool:
        return {"status": "error", "message": f"Tool '{request.tool_name}'을 찾을 수 없습니다."}

    # 위험 Tool 승인 체크
    if request.tool_name in DANGEROUS_TOOLS and not request.approved:
        return {
            "status": "error",
            "message": f"'{request.tool_name}'은 위험 Tool입니다. 사용자 승인이 필요합니다.",
        }

    try:
        result = tool.invoke(request.args)
        return {"status": "success", "result": str(result)}
    except Exception as e:
        return {"status": "error", "message": f"Tool 실행 오류: {str(e)}"}
