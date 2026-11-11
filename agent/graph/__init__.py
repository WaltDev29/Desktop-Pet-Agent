import os
import logging
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from .state import AgentState
from .checkpointer import get_checkpointer
from .nodes import (
    make_planner_node,
    make_master_router_node,
    make_general_mcp_worker,
    make_vision_worker,
    make_aggregator_node,
    route_planner,
    route_master_router,
    route_worker,
    route_tools,
    route_entry,
)


logger = logging.getLogger(__name__)

# ==========================================
# 환경변수 Load
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# 기본값 추가: .env에 USE_OPENAI가 없어도 NoneType 에러 방지
USE_OPENAI = os.getenv("USE_OPENAI", "false")
MODEL     = os.getenv("OPENAI_MODEL") if USE_OPENAI.lower() == "true" else os.getenv("API_MODEL")
API_KEY   = os.getenv("API_KEY", "")  if USE_OPENAI.lower() == "true" else os.getenv("LOCAL_API_KEY")
BASE_URL  = os.getenv("API_BASE_URL", "")

# ==========================================
# 그래프 싱글톤
# 서버 시작 후 최초 1회만 생성하고 이후 재사용합니다.
# MemorySaver가 thread_id 별로 상태를 내부적으로 관리합니다.
# ==========================================
_agent = None


async def create_agent():
    global _agent
    if _agent is not None:
        return _agent

    # ==========================================
    # 도구 가져오기 (MCP 클라이언트)
    # ==========================================
    from agent_server.mcp_client import get_mcp_tools
    tools = await get_mcp_tools()

    # ==========================================
    # LLM 초기화 및 도구 분리 바인딩
    # ==========================================
    if USE_OPENAI.lower() == "true":
        llm = ChatOpenAI(model=MODEL, api_key=API_KEY)
    else:
        llm = ChatOpenAI(
            model=MODEL,
            base_url=BASE_URL,
            api_key=API_KEY or "x",  # 로컬 서버는 API_KEY가 빈 문자열이면 에러 나는 경우 대비
            default_headers={"User-Agent": "Mozilla/5.0"},
            reasoning_effort="none"
        )
    
    # OpenAI 호환 규격 API는 tools 배열 길이가 최대 128개로 제한됩니다.
    MAX_TOOLS = 128
    if len(tools) > MAX_TOOLS:
        logger.warning(
            f"[Agent] 등록된 도구 수({len(tools)}개)가 모델 한도({MAX_TOOLS}개)를 초과하여 상위 {MAX_TOOLS}개로 제한합니다."
        )
        safe_tools = tools[:MAX_TOOLS]
    else:
        safe_tools = tools

    general_mcp_llm = llm.bind_tools(safe_tools)
    logger.info(f"[Agent] Loaded MCP tools: {[t.name for t in safe_tools]}")


    # ==========================================
    # 노드 초기화
    # ==========================================
    planner_node    = make_planner_node(llm, tools)
    router_node     = make_master_router_node(llm)
    general_mcp_node = make_general_mcp_worker(general_mcp_llm)
    vision_worker_node = make_vision_worker(llm)
    aggregator_node = make_aggregator_node(llm)

    tool_node       = ToolNode(tools, handle_tool_errors=True)

    # ==========================================
    # 그래프 조립
    # ==========================================
    workflow = StateGraph(AgentState)

    workflow.add_node("planner",        planner_node)
    workflow.add_node("master_router",  router_node)
    workflow.add_node("general_mcp_worker", general_mcp_node)
    workflow.add_node("vision_worker",      vision_worker_node)
    workflow.add_node("aggregator",     aggregator_node)
    workflow.add_node("tools",          tool_node)

    # ---- 진입점 ----
    workflow.set_conditional_entry_point(route_entry, {
        "planner":        "planner",
        "master_router":  "master_router",
        "general_mcp_worker": "general_mcp_worker",
        "vision_worker":      "vision_worker",
    })

    # ---- 노드간 엣지 ----
    workflow.add_conditional_edges("planner", route_planner, {"master_router": "master_router", "aggregator": "aggregator"})
    workflow.add_conditional_edges("master_router", route_master_router, {"general_mcp_worker": "general_mcp_worker", "vision_worker": "vision_worker", "aggregator": "aggregator"})
    workflow.add_conditional_edges("general_mcp_worker", route_worker, {"tools": "tools", "master_router": "master_router"})
    workflow.add_conditional_edges("vision_worker", route_worker, {"tools": "tools", "master_router": "master_router"})
    workflow.add_conditional_edges("tools",  route_tools,  {"general_mcp_worker": "general_mcp_worker", "vision_worker": "vision_worker"})
    workflow.add_edge("aggregator", "__end__")

    # ---- 컴파일: 체크포인터 주입 ----
    # MemorySaver → thread_id별 상태를 메모리에 보존
    # 나중에 .env에 DATABASE_URL 추가만 하면 PostgresSaver로 자동 전환됩니다.
    _agent = workflow.compile(checkpointer=await get_checkpointer())
    logger.info("[Agent] 그래프 컴파일 완료")
    return _agent