import os
import httpx
from pydantic import BaseModel
from langchain_core.tools import StructuredTool
from typing import Optional
from dotenv import load_dotenv
from pathlib import Path

# ==========================================
# 환경변수 Load
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

TOOL_SERVER_URL = os.getenv("TOOL_SERVER_URL", "http://localhost:8002")


# ==========================================
# Tool Server HTTP 호출 헬퍼
# Agent가 Tool을 직접 실행하지 않고, Tool Server에 HTTP 신호를 보냅니다.
# Tool 실행 결과는 반환값으로 받아 LangGraph의 ToolMessage에 담습니다.
# ==========================================
def _call_tool_server(tool_name: str, args: dict, approved: bool = False) -> str:
    """
    Tool Server에 HTTP POST 요청을 보내 Tool을 실행합니다.
    반환된 result 문자열은 LangGraph ToolNode → agent 노드로 전달되어
    LLM이 사용자 최종 응답을 생성하는 데 사용됩니다.
    """
    try:
        response = httpx.post(
            f"{TOOL_SERVER_URL}/execute",
            json={"tool_name": tool_name, "args": args, "approved": approved},
            timeout=30.0,
        )
        data = response.json()
        if data["status"] == "success":
            return data["result"]
        else:
            return f"Tool 오류: {data.get('message', '알 수 없는 오류')}"
    except httpx.ConnectError:
        return f"[연결 오류] Tool Server({TOOL_SERVER_URL})에 접속할 수 없습니다. Tool Server가 실행 중인지 확인하세요."
    except Exception as e:
        return f"[오류] Tool Server 요청 실패: {str(e)}"


# ==========================================
# Proxy Tool 팩토리
# Tool Server의 각 Tool을 HTTP 호출로 감싼 StructuredTool을 생성합니다.
# LangGraph는 이 Proxy Tool을 통해 Tool을 "실행"하지만,
# 실제 실행은 Tool Server에서 일어납니다.
# ==========================================
def _make_proxy_tool(tool_name: str, description: str, args_schema: type) -> StructuredTool:
    """HTTP 프록시 Tool을 생성합니다."""

    def _run(**kwargs) -> str:
        return _call_tool_server(tool_name, kwargs)

    return StructuredTool(
        name=tool_name,
        description=description,
        args_schema=args_schema,
        func=_run,
    )


# ==========================================
# 각 Tool의 Pydantic 스키마 정의
# LLM이 Tool에 어떤 인수를 전달해야 하는지 알 수 있도록 합니다.
# ==========================================

class ListDirectoryArgs(BaseModel):
    path: str

class ReadFileArgs(BaseModel):
    path: str

class WriteFileArgs(BaseModel):
    path: str
    content: str

class DeleteFileArgs(BaseModel):
    path: str

class GetDiskUsageArgs(BaseModel):
    path: str = "C:\\"

class ListProcessesArgs(BaseModel):
    limit: int = 10

class SearchWebArgs(BaseModel):
    query: str

class EmptyArgs(BaseModel):
    """인수가 없는 Tool용 빈 스키마입니다."""
    pass


# ==========================================
# Proxy Tool 인스턴스 목록
# agent/graph.py에서 이 목록을 import하여 LLM에 바인딩합니다.
# ==========================================
tools = [
    # --- Filesystem Tools ---
    _make_proxy_tool("list_directory_tool", "주어진 경로의 디렉토리 및 파일 목록을 반환합니다.", ListDirectoryArgs),
    _make_proxy_tool("read_file_tool", "주어진 경로의 파일 내용을 읽습니다.", ReadFileArgs),
    _make_proxy_tool("write_file_tool", "파일에 내용을 씁니다. 사용자의 승인이 필요합니다.", WriteFileArgs),
    _make_proxy_tool("delete_file_tool", "파일을 삭제합니다. 사용자의 승인이 필요합니다.", DeleteFileArgs),

    # --- System Monitor Tools ---
    _make_proxy_tool("get_cpu_usage_tool", "CPU 사용률을 퍼센테이지로 반환합니다.", EmptyArgs),
    _make_proxy_tool("get_memory_usage_tool", "메모리 사용 현황을 반환합니다.", EmptyArgs),
    _make_proxy_tool("get_disk_usage_tool", "지정된 경로의 디스크 사용량을 반환합니다.", GetDiskUsageArgs),
    _make_proxy_tool("list_processes_tool", "CPU를 많이 사용하는 상위 N개의 프로세스를 반환합니다.", ListProcessesArgs),

    # --- Web Search Tool ---
    _make_proxy_tool("search_web_tool", "DuckDuckGo를 사용하여 웹에서 정보를 검색합니다.", SearchWebArgs),
]
