"""
agent/graph/nodes.py

LangGraph 그래프를 구성하는 모든 노드 및 조건부 엣지 함수를 정의합니다.

노드 구조:
  [Planner] → [Master Router] → [Vision / General Worker] ↔ [ToolNode]
                                                         ↓
                                                    [Aggregator] → END

사용자 승인 흐름:
  Worker가 위험 도구를 감지하면 interrupt()로 그래프를 일시정지합니다.
  /approve API에서 Command(resume=True/False)로 재개하면 Worker가 이어서 실행됩니다.
"""

import json
import logging
import base64 as b64lib
from io import BytesIO
from typing import Literal

from PIL import Image
from pydantic import BaseModel
from langchain_core.runnables import Runnable
from langchain_core.messages import SystemMessage, ToolMessage, HumanMessage
from langgraph.types import interrupt

from .state import AgentState
from prompts.agents_prompts import (
    PLANNER_PROMPT,
    ROUTER_PROMPT,
    VISION_WORKER_PROMPT,
    GENERAL_WORKER_PROMPT,
    AGGREGATOR_PROMPT,
)

logger = logging.getLogger(__name__)

# ==========================================
# 상수
# ==========================================

# Structured Output 모델: Master Router가 반환할 worker 이름
class WorkerDecision(BaseModel):
    # worker: Literal["vision_worker", "general_worker"]
    worker: Literal["windows_mcp_worker"]

# 실행 전 사용자 승인이 필요한 위험 도구 목록
DANGEROUS_TOOLS = ["write_file_tool", "delete_file_tool"]

# Worker 1회 태스크당 최대 도구 호출 횟수 (무한 루프 방지)
MAX_TOOL_CALLS = 5

# ==========================================
# 1. Planner Node
# ==========================================

def make_planner_node(llm: Runnable):
    """
    사용자의 요청을 분석해 단계별 실행 계획(Plan)을 수립합니다.
    단순 대화의 경우 빈 plan을 반환하여 Aggregator로 바로 우회합니다.
    """
    def planner_node(state: AgentState):
        # 가장 마지막 HumanMessage를 원본 요청으로 저장 (Aggregator에서 정확하게 참조)
        original_request = next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            ""
        )

        response = llm.invoke([SystemMessage(content=PLANNER_PROMPT)] + state["messages"])

        plan = []
        try:
            content = response.content
            if "{" in content and "}" in content:
                start, end = content.find("{"), content.rfind("}") + 1
                raw = content[start:end]
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    # LLM이 Windows 경로(D:\foo)를 JSON 이스케이프 없이 출력한 경우
                    # 비이스케이프된 백슬래시만 골라서 \\로 치환 후 재시도
                    import re
                    fixed = re.sub(
                        r'\\(?!["\\bfnrtu])',  # 유효한 JSON 이스케이프가 아닌 \ 만 치환
                        r'\\\\',
                        raw,
                    )
                    data = json.loads(fixed)
                if "plan" in data and isinstance(data["plan"], list):
                    plan = data["plan"]
        except (json.JSONDecodeError, ValueError) as e:
            # 두 번 시도 모두 실패 → 단순 대화로 처리
            logger.warning(f"[Planner] JSON 파싱 실패, 단순 대화로 처리합니다. 원인: {e!r}")

        return {
            "plan": plan,
            "past_results": [],
            "tool_call_count": 0,
            "original_request": original_request,
        }
    return planner_node


# ==========================================
# 2. Master Router Node (LLM Structured Output 기반)
# ==========================================

def make_master_router_node(llm: Runnable):
    """
    Plan에서 다음 태스크를 꺼내고, LLM이 어느 Worker가 적합한지 판단합니다.
    """
    router_llm = llm.with_structured_output(WorkerDecision)

    def master_router_node(state: AgentState):
        plan = state.get("plan", [])
        if not plan:
            # 모든 계획 완료 → Aggregator로
            return {"current_task": "", "active_worker": ""}

        current_task = plan[0]
        remaining_plan = plan[1:]

        decision: WorkerDecision = router_llm.invoke([
            SystemMessage(content=ROUTER_PROMPT),
            HumanMessage(content=current_task),
        ])

        logger.info(f"[Router] '{current_task[:40]}' → {decision.worker}")
        return {
            "plan": remaining_plan,
            "current_task": current_task,
            "active_worker": decision.worker,
            "tool_call_count": 0,  # 새 태스크 시작 시 카운터 초기화
        }
    return master_router_node


# ==========================================
# Worker 공통 유틸리티
# ==========================================

def _build_worker_messages(state: AgentState, system_prompt: str) -> list:
    """Worker LLM에 전달할 메시지 목록을 구성합니다."""
    msgs = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=(
            f"Sub-task: {state.get('current_task', '')}\n"
            f"Past Results: {state.get('past_results', [])}"
        )),
    ]
    # 최근 도구 호출 / 결과 메시지 덧붙이기 (Worker가 이전 도구 결과를 볼 수 있도록)
    recent = []
    for msg in reversed(state["messages"]):
        if isinstance(msg, ToolMessage):
            recent.insert(0, msg)
        elif getattr(msg, "tool_calls", None):
            recent.insert(0, msg)
            break
    return msgs + recent


def _compress_screenshot(b64_png: str) -> str:
    """PNG Base64 → JPEG 1280×800 이하 압축 Base64로 변환합니다. (토큰 절약)"""
    raw = b64lib.b64decode(b64_png)
    img = Image.open(BytesIO(raw))
    img.thumbnail((1280, 800), Image.LANCZOS)
    buf = BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=60)
    return b64lib.b64encode(buf.getvalue()).decode("utf-8")


def _apply_vision_postprocess(msgs: list) -> list:
    """ToolMessage의 base64_png를 멀티모달(image_url) 포맷으로 변환합니다."""
    result = []
    for msg in msgs:
        if isinstance(msg, ToolMessage) and isinstance(msg.content, str):
            try:
                data = json.loads(msg.content)
                if isinstance(data, dict) and "base64_png" in data:
                    compressed = _compress_screenshot(data["base64_png"])
                    msg = ToolMessage(
                        content=[
                            {"type": "text", "text": "Screenshot captured. Analyze the image carefully."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{compressed}"}},
                        ],
                        name=msg.name,
                        tool_call_id=msg.tool_call_id,
                    )
            except Exception as e:
                logger.warning(f"[Vision] 이미지 변환 실패: {e!r}")
        result.append(msg)
    return result


# ==========================================
# 3. 공통 Worker 팩토리
#    Vision/General이 동일한 구조를 공유합니다.
#    Vision만 postprocess(이미지 압축 변환)를 추가로 적용합니다.
# ==========================================

def _make_base_worker(llm_with_tools: Runnable, system_prompt: str, worker_label: str, postprocess=None):
    def worker_node(state: AgentState):
        msgs = _build_worker_messages(state, system_prompt)
        if postprocess:
            msgs = postprocess(msgs)

        # ---- 무한 루프 방지 ----
        count = state.get("tool_call_count", 0)
        if count >= MAX_TOOL_CALLS:
            logger.warning(f"[{worker_label}] 최대 도구 호출 횟수({MAX_TOOL_CALLS}) 초과. 강제 종료.")
            return {
                "past_results": state.get("past_results", []) + [
                    f"[{worker_label}] 최대 도구 호출 횟수를 초과하여 작업이 중단되었습니다."
                ],
                "tool_call_count": 0,
            }

        response = llm_with_tools.invoke(msgs)

        if response.tool_calls:
            # ---- 위험 도구 전수 스캔 ----
            # LLM이 한 번에 여러 tool_call을 반환할 수 있으므로 [0]만 보면 안 됩니다.
            dangerous_calls = [
                tc for tc in response.tool_calls if tc["name"] in DANGEROUS_TOOLS
            ]

            if dangerous_calls:
                logger.info(
                    f"[{worker_label}] 위험 도구 감지 {len(dangerous_calls)}개 → interrupt() 발동"
                )
                # 위험 도구 전체 목록을 한 번에 사용자에게 표시
                approved = interrupt({
                    "tool_name":  dangerous_calls[0]["name"],          # UI 표시용 대표 이름
                    "tool_args":  [tc["args"] for tc in dangerous_calls],  # 전체 인자 목록
                    "tool_call_id": dangerous_calls[0]["id"],
                    "total_count": len(dangerous_calls),               # 총 개수 표시
                })
                if not approved:
                    # 거절: 위험 도구 전체에 대해 ToolMessage 생성 후 router 복귀
                    rejections = [
                        ToolMessage(
                            content="사용자가 명령 실행을 거절하였습니다.",
                            name=tc["name"],
                            tool_call_id=tc["id"],
                        )
                        for tc in dangerous_calls
                    ]
                    return {
                        "messages": [response] + rejections,
                        "past_results": state.get("past_results", []) + [
                            f"[{worker_label}] '{dangerous_calls[0]['name']}' 외 "
                            f"{len(dangerous_calls)}건 실행이 거절되었습니다."
                        ],
                        "tool_call_count": 0,
                    }
                # 승인 → Tools 노드로 이동 (route_worker가 tool_calls 유무로 판단)

            # 일반 도구 (또는 승인된 위험 도구) → ToolNode로 전달
            return {"messages": [response], "tool_call_count": count + 1}


        # 도구 호출 없음 → 태스크 완료, Master Router로 복귀
        return {
            "messages": [response],
            "past_results": state.get("past_results", []) + [
                f"[{worker_label}] {response.content}"
            ],
            "tool_call_count": 0,
        }
    return worker_node


# ==========================================
# 3-1. Vision Worker Node
# ==========================================

def make_vision_worker(llm_with_tools: Runnable):
    """화면 캡처, OCR, 이미지 분석 전담 Worker."""
    return _make_base_worker(
        llm_with_tools,
        system_prompt=VISION_WORKER_PROMPT,
        worker_label="vision_worker",
        postprocess=_apply_vision_postprocess,
    )


# ==========================================
# 3-2. General Worker Node
# ==========================================

def make_general_worker(llm_with_tools: Runnable):
    """파일 시스템, 시스템 모니터링, 웹 검색 전담 Worker."""
    return _make_base_worker(
        llm_with_tools,
        system_prompt=GENERAL_WORKER_PROMPT,
        worker_label="general_worker",
    )


# ==========================================
# 3-3. Windows MCP Worker Node (Test)
# ==========================================

def make_windows_mcp_worker(llm_with_tools: Runnable):
    """windows-mcp의 모든 도구를 담당하는 단일 Worker."""
    return _make_base_worker(
        llm_with_tools,
        system_prompt=GENERAL_WORKER_PROMPT,  # 임시로 general 프롬프트 재사용
        worker_label="windows_mcp_worker",
    )


# ==========================================
# 5. Aggregator Node
# ==========================================

def make_aggregator_node(llm: Runnable):
    """모든 Worker 결과를 취합해 사용자에게 최종 답변을 생성합니다.

    [대화 기억 구현 방식]
    state["messages"]에서 순수 대화 메시지(HumanMessage + Aggregator의 AIMessage)만 추출해
    LLM에 히스토리로 제공합니다. 이를 통해 이전 대화 내용을 기억하면서 현재 요청에 답변합니다.

    Worker 내부 메시지(ToolMessage, tool_calls 포함 AIMessage)는 대화 맥락과 무관하므로 제외합니다.
    """
    def aggregator_node(state: AgentState):
        from langchain_core.messages import AIMessage

        current_request = state.get("original_request") or next(
            (msg.content for msg in reversed(state["messages"]) if isinstance(msg, HumanMessage)),
            ""
        )
        past = state.get("past_results", [])

        # ---- 순수 대화 히스토리 추출 ----
        # HumanMessage: 사용자의 원본 발화
        # Tool call이 없는 AIMessage: Aggregator가 이전 턴에 사용자에게 보낸 답변
        # (Worker나 Planner의 중간 AIMessage는 tool_calls 혹은 내용으로 구분해 제외)
        chat_history = []
        for msg in state["messages"]:
            if isinstance(msg, HumanMessage):
                chat_history.append(msg)
            elif isinstance(msg, AIMessage) and not getattr(msg, "tool_calls", None):
                # Planner/Router의 JSON 출력은 Aggregator 답변과 혼동될 수 있으므로
                # content가 JSON처럼 보이는 메시지는 히스토리에서 제외합니다.
                content = msg.content.strip()
                if not (content.startswith("{") and content.endswith("}")):
                    chat_history.append(msg)

        # ---- 현재 요청 제거 ----
        # 마지막 HumanMessage는 current_request와 동일하므로 중복 방지를 위해 히스토리에서 뺍니다.
        # (current_request를 별도의 마지막 메시지로 명시적으로 추가할 예정)
        if chat_history and isinstance(chat_history[-1], HumanMessage):
            chat_history = chat_history[:-1]

        # ---- 메시지 목록 구성 ----
        msgs = [SystemMessage(content=AGGREGATOR_PROMPT)]

        # 과거 대화 이력을 그대로 주입 (멀티턴 기억)
        if chat_history:
            msgs.extend(chat_history)

        # 현재 사용자 요청 + Worker 작업 결과를 마지막 메시지로 추가
        if past:
            final_prompt = (
                f"Current user request: {current_request}\n"
                f"Worker Results:\n" + "\n".join(f"- {r}" for r in past)
            )
        else:
            final_prompt = (
                f"Current user request: {current_request}\n"
                f"(No tool results — direct conversation)"
            )
        msgs.append(HumanMessage(content=final_prompt))

        response = llm.invoke(msgs)
        return {"messages": [response]}
    return aggregator_node


# ==========================================
# Conditional Edge Parsers
# ==========================================

def route_planner(state: AgentState) -> Literal["master_router", "aggregator"]:
    """Plan이 있으면 Router로, 없으면 단순 대화이므로 Aggregator로."""
    return "master_router" if state.get("plan") else "aggregator"


def route_master_router(state: AgentState) -> Literal["vision_worker", "general_worker", "windows_mcp_worker", "aggregator"]:
    """Router가 선택한 worker로 이동. active_worker가 없으면 모든 계획 완료."""
    worker = state.get("active_worker", "")
    if worker in ("vision_worker", "general_worker", "windows_mcp_worker"):
        return worker
    return "aggregator"


def route_worker(state: AgentState) -> Literal["tools", "master_router"]:
    """
    마지막 메시지에 tool_calls가 있으면 ToolNode로, 없으면 Master Router로 복귀.
    next_step 필드 없이 메시지 타입만으로 분기하므로 human_approval 경로가 불필요합니다.
    (위험 도구는 Worker 내부에서 interrupt()로 처리)
    """
    last_msg = state["messages"][-1] if state["messages"] else None
    if last_msg and getattr(last_msg, "tool_calls", None):
        return "tools"
    return "master_router"


def route_tools(state: AgentState) -> Literal["vision_worker", "general_worker", "windows_mcp_worker"]:
    """도구 실행 완료 후 original_request한 Worker로 정확히 복귀."""
    return state.get("active_worker", "windows_mcp_worker")


def route_entry(state: AgentState) -> Literal["planner", "master_router", "vision_worker", "general_worker", "windows_mcp_worker"]:

    """
    진입점 라우터.
    MemorySaver가 이전 상태를 복원하므로, 현재 상태를 보고 어느 노드부터 재개할지 결정합니다.

    우선순위:
    1. 마지막 메시지가 ToolMessage + active_worker 있음 → Worker로 복귀 (도구 실행 후)
    2. 진행 중인 plan/active_worker 있음 → master_router로 (계획 진행 중)
    3. 그 외 → planner (새 대화 시작)
    """
    last_msg = state["messages"][-1] if state.get("messages") else None
    if isinstance(last_msg, ToolMessage) and state.get("active_worker"):
        return state["active_worker"]
    if state.get("plan") or state.get("active_worker"):
        return "master_router"
    return "planner"
