import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph
from langgraph.prebuilt import ToolNode

from .state import AgentState
from .nodes import make_agent_node, human_approval_node, route_after_agent
from tool import tools

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



def create_agent():
    # ==========================================
    # LLM 초기화 및 도구 바인딩
    # ==========================================
    if USE_OPENAI.lower() == 'true':
        llm = ChatOpenAI(model=MODEL, api_key=API_KEY)
    else: 
        llm = ChatOpenAI(
            model=MODEL,
            base_url=BASE_URL,
            api_key=API_KEY,
            default_headers={
                "User-Agent": "Mozilla/5.0",
            }
        )
        
    llm_with_tools = llm.bind_tools(tools)



    # ==========================================
    # 그래프 노드 초기화
    # ==========================================
    agent_node = make_agent_node(llm_with_tools)
    tool_node = ToolNode(tools)



    # ==========================================
    # 그래프 조립 
    # ==========================================
    workflow = StateGraph(AgentState)

    # ============ 노드 추가 ============
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_node)
    workflow.add_node("human_approval", human_approval_node)

    # ============ 진입점 설정 ============
    workflow.set_entry_point("agent")

    # ============ agent -> router 연결 ============
    '''agent 노드가 끝난 후 route_after_agent 함수의 결과에 따라 갈림길 생성'''
    workflow.add_conditional_edges("agent", route_after_agent)

    # ============ tools -> agent 연결 ============
    '''도구 노드(tools)가 일을 마치면, 그 결과값을 들고 다시 에이전트(agent)에게 돌아가서 다음 답변을 생각하게 합니다.'''
    workflow.add_edge("tools", "agent")

    # ============ 그래프 컴파일 ============
    app_graph = workflow.compile()

    return app_graph