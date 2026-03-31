from typing import Literal
from langchain_core.runnables import Runnable
from .state import AgentState

# ============ 위험 도구 목록============
'''파일을 만들거나 지우는 작업은 자동으로 실행되지 않도록 막기 위한 리스트입니다.'''
DANGEROUS_TOOLS = ["write_file_tool", "delete_file_tool"]

def make_agent_node(llm_with_tools: Runnable):
    # ============ Agent Node ============
    def agent_node(state: AgentState):
        response = llm_with_tools.invoke(state["messages"])
        
        # ============ Tool 호출 여부 체크 ============
        if response.tool_calls:
            first_tool_call = response.tool_calls[0]
            tool_name = first_tool_call["name"]
            
            # ============ 위험 도구인지 확인 ============
            if tool_name in DANGEROUS_TOOLS:
                return {
                    "messages": [response],
                    "pending_tool_call": first_tool_call,
                    "next_step": "human_approval"
                }
            else:
                # ============ 안전한 도구라면 바로 실행 노드로 ============
                return {
                    "messages": [response],
                    "pending_tool_call": None,
                    "next_step": "tools"
                }
        
        # ============ 툴 호출이 없으면 종료 플래그 설정 ============
        return {
            "messages": [response],
            "pending_tool_call": None,
            "next_step": "end"
        }
        
    return agent_node



# ============ 승인 대기 Node ============
def human_approval_node(state: AgentState):
    """
    위험한 작업에 도달했을 때 에이전트의 흐름을 멈추게 하는 가상의 노드입니다.
    빈 딕셔너리 {} 를 반환하여 기존 state에 불필요한 메시지가 중복 추가되는 파이썬 버그를 방지합니다.
    """
    return {}



# ============ Router Node ============
def route_after_agent(state: AgentState) -> Literal["tools", "human_approval", "__end__"]:
    """agent 노드 실행 후 next_step 값을 읽고 다음 노드로 연결해줍니다."""
    next_step = state.get("next_step")

    # ============ tools로 연결 ============
    if next_step == "tools":
        return "tools"

    # ============ human_approval로 연결 ============
    elif next_step == "human_approval":
        return "human_approval"

    # ============ 종료 ============
    else:
        # 종료 플래그(__end__)를 반환하면 그래프 흐름이 끝납니다.
        return "__end__"
