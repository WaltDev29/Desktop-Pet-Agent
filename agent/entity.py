from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
import uuid

# ==========================================
# 1. 공통 웹소켓 메시지 규격 (WebSocket Base)
# ==========================================

class BasePayload(BaseModel):
    """모든 웹소켓 메시지 payload의 공통 필드"""
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="메시지 고유 식별자")
    session_id: Optional[str] = Field(None, description="대화 세션 ID (LangGraph thread_id 매핑용)")
    timestamp: datetime = Field(default_factory=datetime.now, description="메시지 발생 시간")

MessageType = Literal[
    "register", "status", "token", "log", "approval_request", 
    "approval_response", "done", "chat", "ping", "pong", "error",
    "session_sync", "session_created", "session_deleted"
]

class WsMessage(BaseModel):
    """웹소켓으로 주고받는 최상위 메시지 래퍼"""
    type: MessageType = Field(..., description="메시지 타입")
    payload: Any = Field(..., description="실제 데이터 (BasePayload를 상속받은 모델들)")

# ==========================================
# 2. 페이로드 상세 규격 (Payload Models)
# ==========================================

class AgentRegisterPayload(BasePayload):
    role: Literal["agent"] = "agent"
    client_id: str = Field(..., description="에이전트 고유 ID (예: agent_pc_01)")

class AppRegisterPayload(BasePayload):
    role: Literal["app"] = "app"
    target_agent_id: str = Field(..., description="제어/모니터링할 대상 에이전트 ID")

class StatusPayload(BasePayload):
    agent_id: str
    status: Literal["online", "offline"]

class TokenPayload(BasePayload):
    chunk: str = Field(..., description="스트리밍되는 텍스트 조각 (현재 에이전트의 chunk 속성에 맞춤)")

class LogPayload(BasePayload):
    status: Literal["node_start", "tool_start", "error", "info"] = Field(..., description="현재 에이전트 스트리밍 상태에 맞춤")
    node: Optional[str] = Field(None, description="실행 중인 노드명 (node_start 시)")
    tool_name: Optional[str] = Field(None, description="도구 이름 (tool_start 시)")
    tool_input: Optional[Any] = Field(None, description="도구 입력값 (tool_start 시)")
    message: Optional[str] = Field(None, description="완성된 에러 또는 부가 메시지")

class ApprovalRequestPayload(BasePayload):
    tool_name: str
    tool_args: Dict[str, Any] = Field(..., description="도구 실행에 필요한 파라미터")
    tool_call_id: str = Field(..., description="현재 에이전트의 tool_call_id (인터럽트 식별용)")
    message: str = Field(..., description="사용자에게 보여질 승인 요청 메시지")

class ApprovalResponsePayload(BasePayload):
    approve: bool = Field(..., description="승인 여부 (true/false)")

class SessionItem(BaseModel):
    session_id: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class SessionSyncPayload(BasePayload):
    sessions: List[SessionItem] = Field(..., description="유저의 전체 세션 목록")

class SessionCreatedPayload(BasePayload):
    session_id: str = Field(..., description="새로 생성된 세션 ID")
    title: Optional[str] = Field(None, description="세션 제목")

class SessionDeletedPayload(BasePayload):
    session_id: str = Field(..., description="삭제된 세션 ID")

class DonePayload(BasePayload):
    final_message: str = Field(..., description="최종 완료 메시지")

class ChatPayload(BasePayload):
    message: str = Field(..., description="사용자 질문 또는 텍스트 메시지")
    images: List[str] = Field(default_factory=list, description="이미지 base64 문자열 또는 URL 리스트")

class PingPongPayload(BasePayload):
    """하트비트용 페이로드 (추가 필드 없음)"""
    pass


# ==========================================
# 3. DB Entity 규격 (Database Models)
# ==========================================

class UserEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = Field(..., description="사용자 이름")
    created_at: datetime = Field(default_factory=datetime.now)

class DeviceEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Device (Agent) 고유 ID")
    user_id: str = Field(..., description="소유자 User ID")
    name: str = Field(..., description="기기 이름 (예: 내 데스크탑, 회사 PC)")
    status: Literal["online", "offline"] = "offline"
    last_connected_at: datetime = Field(default_factory=datetime.now)

class SessionEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="대화/작업 단위의 Session ID")
    device_id: str = Field(..., description="연결된 Device ID")
    title: Optional[str] = Field(None, description="세션 제목")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

class MessageEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(..., description="속한 Session ID")
    role: Literal["user", "agent", "system"] = Field(..., description="메시지 발신자 역할")
    content: str = Field(..., description="메시지 텍스트 내용")
    image_urls: Optional[List[str]] = Field(None, description="DB에 저장된 이미지 URL 목록")
    created_at: datetime = Field(default_factory=datetime.now)

class LogEntity(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_id: str = Field(..., description="어떤 답변(Message)을 생성하는 과정에서 나온 로그인지 매핑")
    step: str = Field(..., description="작업 단계명")
    detail: str = Field(..., description="작업 상세 내용")
    input_data: Optional[str] = Field(None, description="도구 입력 파라미터 등")
    created_at: datetime = Field(default_factory=datetime.now)
