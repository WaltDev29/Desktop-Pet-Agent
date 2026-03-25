from typing import TypedDict, Annotated, List, Literal
from langchain_core.messages import AnyMessage
import operator


class AgentState(TypedDict):
    """LangGraph 에이전트의 상태를 정의합니다."""
    
    # ============ messages ============
    """사용자와 AI 간의 모든 대화 내용이 기록되는 리스트입니다."""
    messages: Annotated[List[AnyMessage], operator.add]
    

    # ============ pending_tool_call ============
    """
    AI가 '파일 삭제' 등 위험한 도구를 사용하려 할 때, 
    바로 실행하지 않고 사용자 승인을 받기 위해 
    도구의 정보(이름, 매개변수)를 임시로 저장해두는 공간입니다.
    """
    pending_tool_call: dict | None
    
    
    # ============ next_step ============
    """
    현재 에이전트가 다음에 어떤 행동을 취해야 하는지 방향을 알려줍니다.
    - "agent": LLM이 생각하고 답변을 생성할 차례입니다.
    - "tools": LLM이 도구를 써야 한다고 판단했을 때 실행할 차례입니다.
    - "human_approval": 위험한 작업을 실행하기 전 사용자 승인을 기다리는 멈춤 상태입니다.
    - "end": 더 이상 할 일이 없어 대화를 종료하고 사용자에게 답변을 보냅니다.
    """
    next_step: Literal["agent", "tools", "human_approval", "end"]
