import json
from typing import Literal
from pydantic import BaseModel
from langchain_core.runnables import Runnable
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage, AIMessage
from .state import AgentState

# Structured Output 모델: Master Router가 반환할 worker 이름
class WorkerDecision(BaseModel):
    worker: Literal["vision_worker", "general_worker"]

# ============ 위험 도구 목록============
DANGEROUS_TOOLS = ["write_file_tool", "delete_file_tool"]

def human_approval_node(state: AgentState):
    """위험 작업 실행 흐름 대기용 더미 노드"""
    return {}

# ==========================================
# 1. Planner Node
# ==========================================
def make_planner_node(llm: Runnable):
    def planner_node(state: AgentState):
        from prompts.agents_prompts import PLANNER_PROMPT
        messages = [SystemMessage(content=PLANNER_PROMPT)] + state["messages"]
        response = llm.invoke(messages)
        
        plan = []
        try:
            content = response.content
            if "{" in content and "}" in content:
                start = content.find("{")
                end = content.rfind("}") + 1
                data = json.loads(content[start:end])
                if "plan" in data and isinstance(data["plan"], list):
                    plan = data["plan"]
        except:
            pass
            
        return {"plan": plan, "past_results": []}
    return planner_node

# ==========================================
# 2. Master Router Node (LLM Structured Output 기반)
# ==========================================
def make_master_router_node(llm: Runnable):
    # 라우터 전용 LLM: 단순 분기만 하므로 tools 없이 사용
    router_llm = llm.with_structured_output(WorkerDecision)

    def master_router_node(state: AgentState):
        from prompts.agents_prompts import ROUTER_PROMPT

        plan = state.get("plan", [])
        if not plan:
            return {"current_task": "", "next_step": "aggregator"}

        current_task = plan[0]
        remaining_plan = plan[1:]

        # LLM이 current_task를 보고 어떤 worker가 적합한지 판단
        decision: WorkerDecision = router_llm.invoke([
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=current_task)
        ])

        return {
            "plan": remaining_plan,
            "current_task": current_task,
            "active_worker": decision.worker,
            "next_step": decision.worker
        }
    return master_router_node

# Worker Helper
def format_worker_messages(state: AgentState, system_prompt: str):
    msgs = [SystemMessage(content=system_prompt)]
    msgs.append(HumanMessage(content=f"Sub-task: {state['current_task']}\nPast Results: {state.get('past_results', [])}"))
    
    # 툴 실행 결과를 Worker가 읽을 수 있도록 최근 ToolMessage 덧붙이기
    recent_interaction = []
    if len(state["messages"]) > 0:
        for msg in reversed(state["messages"]):
            if isinstance(msg, ToolMessage):
                recent_interaction.insert(0, msg)
            elif getattr(msg, "tool_calls", None):
                recent_interaction.insert(0, msg)
                break
    return msgs + recent_interaction

# ==========================================
# 3-1. Vision Worker Node
# ==========================================
def make_vision_worker(llm_with_tools: Runnable):
    def vision_worker_node(state: AgentState):
        from prompts.agents_prompts import VISION_WORKER_PROMPT
        recent = format_worker_messages(state, VISION_WORKER_PROMPT)
        
        # Base64 이미지 멀티모달 변환 + 압축 (토큰 절약)
        formatted_recent = []
        for msg in recent:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
                try:
                    data = json.loads(msg.content)
                    if isinstance(data, dict) and "base64_png" in data:
                        import base64 as b64lib
                        from PIL import Image
                        from io import BytesIO

                        # 원본 PNG 디코딩 후 JPEG 1280x800 이하로 압축
                        raw = b64lib.b64decode(data["base64_png"])
                        img = Image.open(BytesIO(raw))
                        img.thumbnail((1280, 800), Image.LANCZOS)
                        buf = BytesIO()
                        img.convert("RGB").save(buf, format="JPEG", quality=60)
                        compressed_b64 = b64lib.b64encode(buf.getvalue()).decode("utf-8")

                        new_content = [
                            {"type": "text", "text": "Screenshot captured successfully. Analyze the image carefully."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{compressed_b64}"}}
                        ]
                        msg = ToolMessage(content=new_content, name=msg.name, tool_call_id=msg.tool_call_id)
                except Exception:
                    pass
            formatted_recent.append(msg)

        response = llm_with_tools.invoke(formatted_recent)
        
        if response.tool_calls:
            tc = response.tool_calls[0]
            if tc["name"] in DANGEROUS_TOOLS:
                return {"messages": [response], "pending_tool_call": tc, "next_step": "human_approval"}
            return {"messages": [response], "pending_tool_call": None, "next_step": "tools"}
            
        return {"messages": [response], "past_results": [f"Vision output: {response.content}"], "next_step": "router"}
    return vision_worker_node

# ==========================================
# 3-2. General Worker Node
# ==========================================
def make_general_worker(llm_with_tools: Runnable):
    def general_worker_node(state: AgentState):
        from prompts.agents_prompts import GENERAL_WORKER_PROMPT
        recent = format_worker_messages(state, GENERAL_WORKER_PROMPT)
        response = llm_with_tools.invoke(recent)
        
        if response.tool_calls:
            tc = response.tool_calls[0]
            if tc["name"] in DANGEROUS_TOOLS:
                return {"messages": [response], "pending_tool_call": tc, "next_step": "human_approval"}
            return {"messages": [response], "pending_tool_call": None, "next_step": "tools"}
            
        return {"messages": [response], "past_results": [f"General output: {response.content}"], "next_step": "router"}
    return general_worker_node

# ==========================================
# 5. Aggregator Node
# ==========================================
def make_aggregator_node(llm: Runnable):
    def aggregator_node(state: AgentState):
        from prompts.agents_prompts import AGGREGATOR_PROMPT
        original_msg = state['messages'][0].content if state['messages'] else ""
        prompt = f"Original user request: {original_msg}\nPast Results: {state.get('past_results', [])}"
        msgs = [SystemMessage(content=AGGREGATOR_PROMPT), HumanMessage(content=prompt)]
        
        response = llm.invoke(msgs)
        return {"messages": [response], "next_step": "end"}
    return aggregator_node

# ==========================================
# Conditional Edge Parsers
# ==========================================
def route_planner(state: AgentState) -> Literal["master_router", "aggregator"]:
    return "master_router" if len(state.get("plan", [])) > 0 else "aggregator"

def route_master_router(state: AgentState) -> Literal["vision_worker", "general_worker", "aggregator"]:
    if not state.get("current_task"):
        return "aggregator"
    return state["active_worker"]

def route_worker(state: AgentState) -> Literal["tools", "human_approval", "master_router"]:
    step = state.get("next_step")
    if step == "human_approval": return "human_approval"
    if step == "tools": return "tools"
    return "master_router"

def route_entry(state: AgentState) -> Literal["planner", "master_router", "vision_worker", "general_worker"]:
    """프론트엔드 통신(API)으로 인해 매번 그래프가 재시작 되는 것을 보정하는 진입점 라우터"""
    if state.get("active_worker"):
        # 도구가 실행된 후 복귀한 경우
        last_msg = state["messages"][-1]
        if isinstance(last_msg, ToolMessage):
            return state["active_worker"]
    
    # plan이 비어있으면 아예 쌩초기 상태
    if not state.get("plan") and not state.get("past_results"):
        return "planner"
    
    return "master_router"
