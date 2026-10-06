"""
pet/app/chat_session.py

채팅 세션 데이터 모델 - 각 대화 세션의 상태를 메모리에 보존합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BubbleSnapshot:
    """말풍선 하나의 스냅샷 - 복원 시 _add_bubble()에 전달됩니다."""
    html: str
    msg_type: str
    # 사고 과정 토글을 위한 프로퍼티 (None이면 일반 말풍선)
    answer_html_content: str | None = None
    thinking_html_content: str | None = None
    thinking_expanded: bool = False


@dataclass
class StreamState:
    """채팅 스트리밍 상태 스냅샷"""
    streaming: bool = False
    current_stream_text: str = ""
    current_node_name: str | None = None
    current_response_index: int | None = None
    thinking_logs: list[str] = field(default_factory=list)
    thinking_stream_buffer: str = ""


@dataclass
class ChatSession:
    """
    단일 채팅 세션의 전체 상태를 보존하는 데이터 클래스.

    - session_id: 서버로부터 발급된 세션 ID (첫 메시지 전까지는 None)
    - title: 사이드바에 표시될 이름 (첫 메시지 앞 20자)
    - created_at: 세션 생성 시각
    - bubbles: 말풍선 스냅샷 목록 (순서 보존)
    - stream_state: 스트리밍 관련 상태 (세션 전환 후 복원용)
    - pending_tool_call_id: 승인 대기 중인 도구 호출 ID
    """
    session_id: str | None = None
    title: str = "새 채팅"
    created_at: datetime = field(default_factory=datetime.now)
    bubbles: list[BubbleSnapshot] = field(default_factory=list)
    stream_state: StreamState = field(default_factory=StreamState)
    pending_tool_call_id: Any = None

    def update_title_from_message(self, message: str, max_len: int = 20):
        """첫 메시지 내용으로 세션 제목을 자동 업데이트합니다."""
        if self.title == "새 채팅" and message.strip():
            text = message.strip().replace("\n", " ")
            self.title = text[:max_len] + ("..." if len(text) > max_len else "")
