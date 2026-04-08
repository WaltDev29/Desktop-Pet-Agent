import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from .state import AgentState
from .nodes import (
    make_planner_node,
    make_master_router_node,
    make_vision_worker,
    make_general_worker,
    make_aggregator_node,
    human_approval_node,
    route_planner,
    route_master_router,
    route_worker,
    route_entry
)

# ==========================================
# 환경변수 Load
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR/".env")

USE_OPENAI = os.getenv("USE_OPENAI")

if USE_OPENAI.lower() == 'true':
    MODEL = os.getenv("OPENAI_MODEL")
    API_KEY = os.getenv("API_KEY")
else:
    API_KEY = ""
    MODEL = os.getenv("API_MODEL")
    BASE_URL = os.getenv("API_BASE_URL")


async def create_agent():
    # ==========================================
    # 도구 가져오기 (MCP 클라이언트)
    # ==========================================
    from agent_server.mcp_client import get_mcp_tools
    tools = await get_mcp_tools()

    # ==========================================
    # 도구 분리 및 LLM 바인딩
    # ==========================================
    if USE_OPENAI.lower() == 'true':
        llm = ChatOpenAI(model=MODEL, api_key=API_KEY)
    else: 
        llm = ChatOpenAI(
            model=MODEL,
            base_url=BASE_URL,
            api_key=API_KEY,
            default_headers={"User-Agent": "Mozilla/5.0"}
        )
        
    vision_tools = [t for t in tools if "screen" in t.name or "ocr" in t.name or "image" in t.name]
    general_tools = [t for t in tools if t.name not in [v.name for v in vision_tools]]

    vision_llm = llm.bind_tools(vision_tools)
    general_llm = llm.bind_tools(general_tools)

    # ==========================================
    # 그래프 노드 초기화
    # ==========================================
    planner_node = make_planner_node(llm)
    master_router_node = make_master_router_node(llm)
    vision_worker_node = make_vision_worker(vision_llm)
    general_worker_node = make_general_worker(general_llm)
    aggregator_node = make_aggregator_node(llm)
    tool_node = ToolNode(tools)

    # ==========================================
    # 그래프 조립 
    # ==========================================
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("master_router", master_router_node)
    workflow.add_node("vision_worker", vision_worker_node)
    workflow.add_node("general_worker", general_worker_node)
    workflow.add_node("aggregator", aggregator_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("human_approval", human_approval_node)

    # ============ 라우팅 엣지 연결 ============
    workflow.set_conditional_entry_point(route_entry, {
        "planner": "planner",
        "master_router": "master_router",
        "vision_worker": "vision_worker",
        "general_worker": "general_worker"
    })

    workflow.add_conditional_edges("planner", route_planner, {"master_router": "master_router", "aggregator": "aggregator"})
    workflow.add_conditional_edges("master_router", route_master_router, {"vision_worker": "vision_worker", "general_worker": "general_worker", "aggregator": "aggregator"})
    
    workflow.add_conditional_edges("vision_worker", route_worker, {"tools": "tools", "human_approval": "human_approval", "master_router": "master_router"})
    workflow.add_conditional_edges("general_worker", route_worker, {"tools": "tools", "human_approval": "human_approval", "master_router": "master_router"})
    
    # 도구 완료 시 어떤 워커가 요청했는지 복귀
    def route_tools(state: AgentState):
        return state["active_worker"]
        
    workflow.add_conditional_edges("tools", route_tools, {"vision_worker": "vision_worker", "general_worker": "general_worker"})
    
    # 대기, 종료 처리
    workflow.add_edge("human_approval", "__end__")
    workflow.add_edge("aggregator", "__end__")

    app_graph = workflow.compile()
    return app_graph