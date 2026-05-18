import html
import json
import base64
import os

from PySide6.QtWidgets import (
    QWidget, QTextEdit, QTextBrowser, QVBoxLayout, QPushButton, QHBoxLayout,
    QApplication, QGraphicsDropShadowEffect, QLabel,
    QFileDialog, QScrollArea, QSlider
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QEvent, QRect, QUrl
from PySide6.QtGui import QColor, QPixmap, QCursor, QDesktopServices

from app.chat_style import (
    CHAT_HISTORY_STYLE,
    APPROVE_BTN_STYLE,
    REJECT_BTN_STYLE,
    INPUT_FIELD_STYLE,
    CLOSE_BTN_STYLE,
    ATTACH_BTN_STYLE,
    NEW_CHAT_BTN_STYLE,
    SETTINGS_BTN_STYLE,
    IMAGE_PREVIEW_AREA_STYLE,
    IMAGE_REMOVE_BTN_STYLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
    SIDEBAR_WIDTH,
    SIDEBAR_EXPANDED_WINDOW_WIDTH,
    SIDEBAR_TOGGLE_BTN_STYLE,
    SIDEBAR_STYLE,
    SESSION_ITEM_STYLE,
    SESSION_ITEM_ACTIVE_STYLE,
    SIDEBAR_NEW_CHAT_BTN_STYLE,
    USER_MSG_FORMAT,
    PET_MSG_FORMAT,
    ERROR_MSG_FORMAT,
    OPACITY_SLIDER_STYLE,
    OPACITY_LABEL_STYLE,
    convert_markdown_to_html,
    BUBBLE_MAX_HEIGHT,
    USER_BUBBLE_STYLE,
    PET_BUBBLE_STYLE,
    ERROR_BUBBLE_STYLE,
    CHAT_SCROLL_AREA_STYLE,
    THINKING_LINK_COLLAPSED,
    THINKING_LINK_EXPANDED,
    THINKING_CONTENT_DIV,
)

from app.chat_network import ChatClient
from app.chat_handler import ChatResponseHandler
from app.chat_session import ChatSession, BubbleSnapshot, StreamState
from app.chat_gui import (
    BubbleFrame, ChatInputField, ImagePreviewItem,
    RESIZE_MARGIN, DIR_NONE, DIR_LEFT, DIR_RIGHT, DIR_TOP, DIR_BOTTOM, RESIZE_CURSOR_MAP,
    fit_bubble_size, render_thinking_html, scroll_to_bottom,
    get_resize_dir, sync_pet_with_bubble
)

MAX_IMAGES = 3
SIDEBAR_ANIM_DURATION = 180  # 사이드바 애니메이션 시간(ms)


class ChatWindow(QWidget):
    def __init__(self, pet_window=None):
        super().__init__(pet_window)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        # 드래그 상태
        self._drag_start_window_pos = None   # 드래그 시작 시 chat 창의 글로벌 위치
        self._drag_start_pet_pos = None      # 드래그 시작 시 pet 창의 글로벌 위치
        self._drag_start_cursor_pos = None   # 드래그 시작 시 커서의 글로벌 위치

        # 리사이즈 상태
        self._resize_active = False
        self._resize_dir = DIR_NONE
        self._resize_start_global: QPoint | None = None
        self._resize_start_geom: QRect | None = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.container = BubbleFrame(self)
        self.container.setObjectName("main_container")

        # BubbleFrame 드래그 → pet_window 위임
        self.container.drag_started.connect(self._on_drag_started)
        self.container.drag_moved.connect(self._on_drag_moved)
        self.container.drag_finished.connect(self._on_drag_finished)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
        
        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 30)

        self.is_shutting_down = False

        self.message_history = []
        
        # ── 세션 관리 상태 ──────────────────────────────────
        self._sidebar_expanded = False
        self._session_item_btns: list[tuple] = []  # (ChatSession, QPushButton)
        self.sessions: list[ChatSession] = []
        self.current_session: ChatSession = ChatSession()
        self.sessions.append(self.current_session)

        # ── 채팅 스크롤 영역 (개별 말풍선 위젯 방식) ──
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll_area.setStyleSheet(CHAT_SCROLL_AREA_STYLE)

        self.chat_scroll_content = QWidget()
        self.chat_scroll_content.setObjectName("chat_scroll_content")
        self.chat_scroll_layout = QVBoxLayout(self.chat_scroll_content)
        self.chat_scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.chat_scroll_layout.setSpacing(2)
        self.chat_scroll_layout.addStretch()

        self.chat_scroll_area.setWidget(self.chat_scroll_content)
        self.bubble_widgets: list[QTextBrowser] = []
        
        self.btn_area = QWidget()
        self.btn_layout = QHBoxLayout(self.btn_area)
        self.btn_layout.setContentsMargins(5, 2, 5, 2)
        
        self.approve_btn = QPushButton("승인")
        self.reject_btn = QPushButton("거절")
        
        self.approve_btn.setStyleSheet(APPROVE_BTN_STYLE)
        self.reject_btn.setStyleSheet(REJECT_BTN_STYLE)
        
        self.approve_btn.clicked.connect(lambda: self.process_btn("approved"))
        self.reject_btn.clicked.connect(lambda: self.process_btn("rejected"))
        
        self.btn_layout.addWidget(self.approve_btn)
        self.btn_layout.addWidget(self.reject_btn)
        self.btn_area.hide()

        # ── 상단 버튼 영역 (토글 + 신규 채팅 / 설정) ─────────────────
        top_btn_layout = QHBoxLayout()
        top_btn_layout.setContentsMargins(0, 0, 0, 5)

        self.sidebar_toggle_btn = QPushButton("☰")
        self.sidebar_toggle_btn.setStyleSheet(SIDEBAR_TOGGLE_BTN_STYLE)
        self.sidebar_toggle_btn.setToolTip("채팅 목록 열기/닫기")
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        
        self.new_chat_btn = QPushButton("신규 채팅")
        self.new_chat_btn.setStyleSheet(NEW_CHAT_BTN_STYLE)
        self.new_chat_btn.clicked.connect(self.start_new_chat)
        
        self.settings_btn = QPushButton("⚙️ 설정")
        self.settings_btn.setStyleSheet(SETTINGS_BTN_STYLE)
        self.settings_btn.clicked.connect(self.open_settings)
        
        top_btn_layout.addWidget(self.sidebar_toggle_btn)
        top_btn_layout.addWidget(self.new_chat_btn)
        top_btn_layout.addStretch()
        top_btn_layout.addWidget(self.settings_btn)

        self.input_field = ChatInputField()
        self.input_field.setPlaceholderText("무엇을 도와드릴까요?")
        self.input_field.setStyleSheet(INPUT_FIELD_STYLE)
        self.input_field.returnPressed.connect(self.send_message)

        # ── 이미지 미리보기 영역 ──────────────────────────────
        self.image_preview_area = QWidget()
        self.image_preview_area.setObjectName("image_preview_area")
        self.image_preview_area.setStyleSheet(IMAGE_PREVIEW_AREA_STYLE)
        self.image_preview_area.setFixedHeight(74)

        self.image_preview_layout = QHBoxLayout(self.image_preview_area)
        self.image_preview_layout.setContentsMargins(6, 6, 6, 6)
        self.image_preview_layout.setSpacing(6)
        self.image_preview_layout.addStretch()
        self.image_preview_area.hide()  # 이미지 없으면 숨김

        self.attached_images: list[ImagePreviewItem] = []

        # ── 입력 영역 ──────────────────────────────────────
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        
        self.attach_btn = QPushButton("파일 업로드")
        self.attach_btn.setStyleSheet(ATTACH_BTN_STYLE)
        self.attach_btn.setToolTip("이미지 첨부 (최대 3개)")
        self.attach_btn.clicked.connect(self.attach_image)

        input_layout.addWidget(self.attach_btn)
        input_layout.addWidget(self.input_field)

        # ── 하단 버튼 행 ──────────────────────────────────
        bottom_layout = QHBoxLayout()
        self.close_btn = QPushButton("종료")
        self.close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        self.close_btn.clicked.connect(self.close_program)

        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)


        # ── 채팅 영역 위젯 (우측) ────────────────────────────
        chat_area = QWidget()
        chat_area_layout = QVBoxLayout(chat_area)
        chat_area_layout.setContentsMargins(0, 0, 0, 0)
        chat_area_layout.setSpacing(4)
        chat_area_layout.addLayout(top_btn_layout)
        chat_area_layout.addWidget(self.chat_scroll_area, 1)
        chat_area_layout.addWidget(self.btn_area)
        chat_area_layout.addWidget(self.image_preview_area)
        chat_area_layout.addLayout(input_layout)
        chat_area_layout.addLayout(bottom_layout)

        # ── 수평 분할: 사이드바(좌) + 채팅 영역(우) ──────────
        inner_h_layout = QHBoxLayout()
        inner_h_layout.setContentsMargins(0, 0, 0, 0)
        inner_h_layout.setSpacing(0)

        self.sidebar_panel = self._build_sidebar()
        self.sidebar_panel.hide()  # 기본: 접혀 있음

        inner_h_layout.addWidget(self.sidebar_panel)
        inner_h_layout.addWidget(chat_area, 1)

        layout.addLayout(inner_h_layout)

        main_layout.addWidget(self.container)
        self.setMinimumSize(220, 300)
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        self.container.installEventFilter(self)
        self.resize(WINDOW_WIDTH, WINDOW_HEIGHT)

        
        self.pending_tool_call_id = None
        
        self.chat_client = ChatClient(ws_url="ws://localhost:8000/ws")
        self.chat_client.signaler.response_received.connect(self.on_response_received)
        self.chat_client.signaler.error_occurred.connect(self.on_error_occurred)

        # 스트림 관련 변수
        self._streaming = False
        self._current_stream_text = ""
        self._current_node_name = None
        self._current_response_index: int | None = None

        # 사고 과정 로그 누적
        self._thinking_logs: list[str] = []
        self._thinking_stream_buffer = ""

        self.pet_window = pet_window
        self.handler = ChatResponseHandler(self)

    def attach_image(self):
        """파일 선택 다이얼로그로 이미지를 첨부합니다."""
        remaining = MAX_IMAGES - len(self.attached_images)
        if remaining <= 0:
            return

        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "이미지 선택 (최대 3개)",
            "",
            "이미지 파일 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )

        for path in paths[:remaining]:
            self._add_image_preview(path)

    def _add_image_preview(self, file_path: str):
        """이미지 미리보기 아이템을 추가합니다."""
        if len(self.attached_images) >= MAX_IMAGES:
            return

        item = ImagePreviewItem(file_path, self)
        item.remove_requested.connect(self._remove_image_preview)

        # stretch 앞에 삽입
        insert_index = self.image_preview_layout.count() - 1
        self.image_preview_layout.insertWidget(insert_index, item)
        self.attached_images.append(item)

        self.image_preview_area.show()
        self._update_attach_btn_state()

    def _remove_image_preview(self, item: ImagePreviewItem):
        """이미지 미리보기 아이템을 제거합니다."""
        if item in self.attached_images:
            self.attached_images.remove(item)
            self.image_preview_layout.removeWidget(item)
            item.deleteLater()

        if not self.attached_images:
            self.image_preview_area.hide()
        self._update_attach_btn_state()

    def _update_attach_btn_state(self):
        """최대 첨부 수에 따라 첨부 버튼 활성화 여부를 업데이트합니다."""
        self.attach_btn.setEnabled(len(self.attached_images) < MAX_IMAGES)
        count = len(self.attached_images)
        tooltip = f"이미지 첨부 ({count}/{MAX_IMAGES}개)" if count > 0 else "이미지 첨부 (최대 3개)"
        self.attach_btn.setToolTip(tooltip)

    def _encode_images(self) -> list[str]:
        """첨부된 이미지를 data URI 문자열 리스트로 반환합니다.
        형식: 'data:image/{mime};base64,{data}'
        """
        encoded = []
        for item in self.attached_images:
            try:
                ext = os.path.splitext(item.file_path)[1].lower().lstrip(".")
                mime = "jpeg" if ext in ("jpg", "jpeg") else ext
                with open(item.file_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                encoded.append(f"data:image/{mime};base64,{data}")
            except Exception:
                pass
        return encoded

    def _clear_attached_images(self):
        """전송 후 첨부 이미지를 모두 제거합니다."""
        for item in list(self.attached_images):
            self.image_preview_layout.removeWidget(item)
            item.deleteLater()
        self.attached_images.clear()
        self.image_preview_area.hide()
        self._update_attach_btn_state()

    def start_new_chat(self):
        """현재 세션을 저장하고 새 채팅 세션을 시작합니다."""
        # 1. 현재 세션 저장 (말풍선이 하나라도 있을 때만)
        if self.bubble_widgets:
            self._save_current_session()
            self._refresh_sidebar_item(self.current_session)

        # 2. 새 세션 생성
        new_session = ChatSession()
        self.sessions.append(new_session)
        self.current_session = new_session

        # 3. 사이드바에 새 항목 추가
        self._add_session_item(new_session)

        # 4. 화면 초기화
        self._clear_bubble_widgets()
        self._reset_stream_state()

        # 5. 입력창 및 첨부 초기화
        self.input_field.clear()
        self._clear_attached_images()
        self.input_field.setEnabled(True)
        self._update_attach_btn_state()

        # 6. chat_client session_id 초기화
        self.chat_client.session_id = None

        # 7. 사이드바 항목 강조 업데이트
        self._update_session_highlight()

    # ── 사이드바 구성 ────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        """좌측 세션 목록 사이드바 위젯을 생성합니다."""
        from PySide6.QtWidgets import QSizePolicy

        panel = QWidget()
        panel.setObjectName("sidebar_panel")
        panel.setStyleSheet(SIDEBAR_STYLE)
        panel.setFixedWidth(SIDEBAR_WIDTH)
        panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(0, 8, 0, 8)
        panel_layout.setSpacing(2)

        # 헤더
        header = QLabel("채팅 목록")
        header.setObjectName("sidebar_header")
        panel_layout.addWidget(header)

        # 세션 목록 스크롤 영역
        self.session_list_scroll = QScrollArea()
        self.session_list_scroll.setWidgetResizable(True)
        self.session_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.session_list_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.session_list_scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
            "QScrollBar:vertical { width: 4px; background: rgba(255,255,255,10); }"
            "QScrollBar::handle:vertical { background: rgba(255,255,255,80); border-radius: 2px; }"
        )

        self.session_list_content = QWidget()
        self.session_list_content.setStyleSheet("background: transparent;")
        self.session_list_layout = QVBoxLayout(self.session_list_content)
        self.session_list_layout.setContentsMargins(0, 0, 0, 0)
        self.session_list_layout.setSpacing(0)
        self.session_list_layout.addStretch()

        self.session_list_scroll.setWidget(self.session_list_content)
        panel_layout.addWidget(self.session_list_scroll, 1)

        # 현재 세션 항목 추가 (초기 세션)
        self._add_session_item(self.current_session)
        self._update_session_highlight()

        return panel

    def _toggle_sidebar(self):
        """사이드바를 접거나 펼칩니다. 창 너비도 함께 조정합니다."""
        self._sidebar_expanded = not self._sidebar_expanded

        if self._sidebar_expanded:
            self.sidebar_panel.show()
            self.resize(SIDEBAR_EXPANDED_WINDOW_WIDTH, self.height())
            self.sidebar_toggle_btn.setText("✕")
            self.sidebar_toggle_btn.setToolTip("채팅 목록 닫기")
        else:
            self.sidebar_panel.hide()
            self.resize(WINDOW_WIDTH, self.height())
            self.sidebar_toggle_btn.setText("☰")
            self.sidebar_toggle_btn.setToolTip("채팅 목록 열기/닫기")

        sync_pet_with_bubble(self, self.pet_window)

    # ── 세션 저장/복원 ────────────────────────────────────────────

    def _save_current_session(self):
        """현재 화면의 말풍선들을 현재 세션에 스냅샷으로 저장합니다."""
        snapshots = []
        for bubble in self.bubble_widgets:
            snap = BubbleSnapshot(
                html=bubble.toHtml(),
                msg_type=bubble.property("msg_type") or "pet",
                answer_html_content=bubble.property("answer_html_content"),
                thinking_html_content=bubble.property("thinking_html_content"),
                thinking_expanded=bubble.property("thinking_expanded") or False,
            )
            snapshots.append(snap)
        self.current_session.bubbles = snapshots

        # 스트림 상태도 저장
        self.current_session.stream_state = StreamState(
            streaming=self._streaming,
            current_stream_text=self._current_stream_text,
            current_node_name=self._current_node_name,
            current_response_index=self._current_response_index,
            thinking_logs=list(self._thinking_logs),
            thinking_stream_buffer=self._thinking_stream_buffer,
        )
        self.current_session.pending_tool_call_id = self.pending_tool_call_id

    def _load_session(self, session: ChatSession):
        """선택된 세션의 말풍선을 화면에 복원합니다."""
        # 현재 세션 저장
        if self.bubble_widgets:
            self._save_current_session()

        # 화면 초기화
        self._clear_bubble_widgets()

        # 세션 전환
        self.current_session = session
        self.chat_client.session_id = session.session_id

        # 스트림 상태 복원
        ss = session.stream_state
        self._streaming = ss.streaming
        self._current_stream_text = ss.current_stream_text
        self._current_node_name = ss.current_node_name
        self._current_response_index = ss.current_response_index
        self._thinking_logs = list(ss.thinking_logs)
        self._thinking_stream_buffer = ss.thinking_stream_buffer
        self.pending_tool_call_id = session.pending_tool_call_id

        # 말풍선 복원
        for snap in session.bubbles:
            bubble = self._add_bubble(snap.html, snap.msg_type)
            if snap.answer_html_content is not None:
                bubble.setProperty("answer_html_content", snap.answer_html_content)
                bubble.setProperty("thinking_html_content", snap.thinking_html_content)
                bubble.setProperty("thinking_expanded", snap.thinking_expanded)

        self.scrollToBottom()
        self._update_session_highlight()

    # ── 사이드바 항목 관리 ─────────────────────────────────────────

    def _add_session_item(self, session: ChatSession):
        """사이드바 목록에 세션 항목 버튼을 추가합니다."""
        btn = QPushButton(f"💬 {session.title}")
        btn.setStyleSheet(SESSION_ITEM_STYLE)
        btn.setToolTip(session.title)
        btn.clicked.connect(lambda checked=False, s=session: self._on_session_clicked(s))

        # stretch 앞에 삽입
        idx = self.session_list_layout.count() - 1
        self.session_list_layout.insertWidget(idx, btn)

        self._session_item_btns.append((session, btn))

    def _refresh_sidebar_item(self, session: ChatSession):
        """사이드바에서 해당 세션의 버튼 텍스트를 업데이트합니다."""
        for s, btn in self._session_item_btns:
            if s is session:
                btn.setText(f"💬 {session.title}")
                btn.setToolTip(session.title)
                break

    def _update_session_highlight(self):
        """현재 활성 세션 항목만 강조 스타일로 표시합니다."""
        for s, btn in self._session_item_btns:
            if s is self.current_session:
                btn.setStyleSheet(SESSION_ITEM_ACTIVE_STYLE)
            else:
                btn.setStyleSheet(SESSION_ITEM_STYLE)

    def _on_session_clicked(self, session: ChatSession):
        """사이드바 세션 항목 클릭 시 해당 세션으로 전환합니다."""
        if session is self.current_session:
            return
        self._load_session(session)

    # ── 내부 헬퍼 ─────────────────────────────────────────────────

    def _clear_bubble_widgets(self):
        """현재 화면의 말풍선 위젯을 모두 제거합니다."""
        for bubble in self.bubble_widgets:
            container = bubble.property("container_widget")
            if container:
                self.chat_scroll_layout.removeWidget(container)
                container.deleteLater()
            else:
                self.chat_scroll_layout.removeWidget(bubble)
                bubble.deleteLater()
        self.bubble_widgets.clear()

    def _reset_stream_state(self):
        """스트림 관련 상태를 초기화합니다."""
        self._streaming = False
        self._current_stream_text = ""
        self._current_node_name = None
        self._current_response_index = None
        self._thinking_logs.clear()
        self._thinking_stream_buffer = ""



    def send_message(self):
        text = self.input_field.toPlainText().strip()
        images = self._encode_images()
        if not text and not images:
            return

        # router.py ChatRequest.message: str 은 필수 필드이므로
        # 이미지만 전송할 때도 빈 문자열 대신 기본 지시문을 채워 전달
        api_message = text if text else "이미지를 분석해줘."

        # 채팅 히스토리에 사용자 메시지 표시
        display_text = text if text else "(이미지 전송)"
        formatted_text = display_text
        formatted_text = display_text
        if images:
            for image_uri in images:
                formatted_text += f"\n\n![이미지]({image_uri})"

        # 마크다운을 HTML로 변환
        html_content = convert_markdown_to_html(formatted_text)
        user_html = USER_MSG_FORMAT.format(text=html_content)
        self._add_bubble(user_html, "user")

        # 첫 메시지로 세션 제목 업데이트
        self.current_session.update_title_from_message(display_text)
        self._refresh_sidebar_item(self.current_session)
        self._update_session_highlight()


        thinking_html = PET_MSG_FORMAT.format(text="생각 중...")
        self._current_response_index = len(self.bubble_widgets)
        self._add_bubble(thinking_html, "pet")
        self._current_node_name = None
        self._streaming = False
        self._current_stream_text = ""
        self._thinking_logs = []
        self._thinking_stream_buffer = ""

        self.scrollToBottom()

        self.input_field.clear()
        self._clear_attached_images()
        self.input_field.setEnabled(False)
        self.attach_btn.setEnabled(False)

        payload = {"action": "chat", "message": api_message, "images": images}
        self.chat_client.send_message(payload)

    # ── 말풍선 위젯 헬퍼 ─────────────────────────────────────────
    def _add_bubble(self, html_content: str, msg_type: str = "pet") -> QTextBrowser:
        """개별 말풍선 QTextBrowser 위젯을 컨테이너에 담아 추가합니다."""
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        vbox.setSizeConstraint(QVBoxLayout.SetFixedSize)

        if msg_type != "error":
            label = QLabel()
            label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; margin-bottom: 2px;")
            if msg_type == "user":
                label.setText("나")
                label.setAlignment(Qt.AlignRight)
            else:
                label.setText("🐾 펫")
                label.setAlignment(Qt.AlignLeft)
            vbox.addWidget(label)

        bubble = QTextBrowser()
        bubble.setOpenExternalLinks(False)
        bubble.anchorClicked.connect(self._on_bubble_link_clicked)
        bubble.setHtml(html_content)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        bubble.setProperty("msg_type", msg_type)
        bubble.document().setDocumentMargin(0)

        if msg_type == "user":
            bubble.setStyleSheet(USER_BUBBLE_STYLE)
        elif msg_type == "error":
            bubble.setStyleSheet(ERROR_BUBBLE_STYLE)
        else:
            bubble.setStyleSheet(PET_BUBBLE_STYLE)

        # 크기 조절 (너비: 내용 기반, 최대 70% / 높이: 내용 기반, 최대 BUBBLE_MAX_HEIGHT)
        fit_bubble_size(bubble, self.chat_scroll_area.viewport())
        vbox.addWidget(bubble)

        # 정렬: 사용자=오른쪽, 펫=왼쪽, 에러=중앙
        if msg_type == "user":
            alignment = Qt.AlignRight
        elif msg_type == "error":
            alignment = Qt.AlignHCenter
        else:
            alignment = Qt.AlignLeft

        # stretch 앞에 컨테이너를 삽입
        idx = self.chat_scroll_layout.count() - 1
        self.chat_scroll_layout.insertWidget(idx, container, 0, alignment)
        self.bubble_widgets.append(bubble)
        
        # 삭제 등의 처리를 위해 컨테이너 참조 저장
        bubble.setProperty("container_widget", container)
        
        return bubble


    def _update_bubble(self, index: int, html_content: str, msg_type: str = "pet"):
        """기존 말풍선 위젯의 HTML 내용을 업데이트합니다."""
        if 0 <= index < len(self.bubble_widgets):
            bubble = self.bubble_widgets[index]
            bubble.setHtml(html_content)
            fit_bubble_size(bubble, self.chat_scroll_area.viewport())

    def _flush_thinking_buffer(self):
        """스트림 버퍼에 쌓인 텍스트를 사고 과정 로그에 추가합니다."""
        if self._thinking_stream_buffer.strip():
            self._thinking_logs.append(self._thinking_stream_buffer.strip())
        self._thinking_stream_buffer = ""


    def _on_bubble_link_clicked(self, url: QUrl):
        """말풍선 내 링크 클릭 처리. 사고과정 토글 또는 외부 링크."""
        url_str = url.toString()
        if url_str == "action:toggle_thinking":
            bubble = self.sender()
            if bubble is None:
                return
            expanded = bubble.property("thinking_expanded") or False
            expanded = not expanded
            bubble.setProperty("thinking_expanded", expanded)

            answer_html = bubble.property("answer_html_content") or ""
            thinking_html = bubble.property("thinking_html_content") or ""
            new_html = render_thinking_html(answer_html, thinking_html, expanded)
            bubble.setHtml(new_html)

            # 펼친 상태에서는 높이 제한을 해제 (매우 큰 값으로 설정)
            max_h = 10000 if expanded else BUBBLE_MAX_HEIGHT
            fit_bubble_size(bubble, self.chat_scroll_area.viewport(), max_height=max_h)
            self.scrollToBottom()
        else:
            QDesktopServices.openUrl(url)

    def scrollToBottom(self):
        scroll_to_bottom(self.chat_scroll_area)
    
    def on_response_received(self, data: dict):
        self.handler.handle(data)


    def process_btn(self, choice: str):
        self.btn_area.hide()
        is_approved = (choice == "approved")
        choice_text = "승인" if is_approved else "거절"
        
        # 마크다운을 HTML로 변환
        user_text = f"[{choice_text}] 하겠어."
        html_user_text = convert_markdown_to_html(user_text)
        user_msg = USER_MSG_FORMAT.format(text=html_user_text)
        self._add_bubble(user_msg, "user")

        thinking_html = PET_MSG_FORMAT.format(text="결과를 서버에 전달하는 중...")
        self._current_response_index = len(self.bubble_widgets)
        self._add_bubble(thinking_html, "pet")
        self._current_node_name = None
        self._streaming = False
        self._current_stream_text = ""
        self._thinking_logs = []
        self._thinking_stream_buffer = ""

        self.scrollToBottom()

        payload = {
            "action": "approve",
            "approve": is_approved,
            "tool_call_id": self.pending_tool_call_id
        }
        self.chat_client.send_message(payload)

    def on_error_occurred(self, error: str):
        safe_error = html.escape(error)
        
        # 마크다운 변환 (일관성 유지)
        html_error = convert_markdown_to_html(safe_error)
        error_msg = ERROR_MSG_FORMAT.format(text=html_error)
        self._add_bubble(error_msg, "error")
        self.scrollToBottom()
        
        self.input_field.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.input_field.setFocus()

    # ── 반응형 리사이즈 ──────────────────────────────────────────
    def resizeEvent(self, event):
        """창 크기 변경 시 내부 말풍선 및 사고 과정 위젯 크기를 재계산합니다."""
        super().resizeEvent(event)
        scroll_w = self.chat_scroll_area.viewport().width()
        if scroll_w < 50:
            scroll_w = self.chat_scroll_area.width() - 20
        max_w = max(int(scroll_w * 0.7), 100)

        # 일반 말풍선 크기 재계산
        for bubble in self.bubble_widgets:
            expanded = bubble.property("thinking_expanded") or False
            max_h = BUBBLE_MAX_HEIGHT * 2 if expanded else BUBBLE_MAX_HEIGHT
            fit_bubble_size(bubble, self.chat_scroll_area.viewport(), max_height=max_h)

    # ── 드래그 이동 ───────────────────────────────────────────
    def _on_drag_started(self, cursor_global: QPoint):
        if self.pet_window:
            self.pet_window.start_drag(cursor_global)
        else:
            self._drag_start_cursor_pos = cursor_global
            self._drag_start_window_pos = self.pos()

    def _on_drag_moved(self, cursor_global: QPoint):
        if self.pet_window:
            if not self.pet_window._drag_active:
                delta = cursor_global - self.pet_window._drag_start_cursor
                if delta.manhattanLength() > 5:
                    self.pet_window._drag_active = True
                    self.pet_window.timer.stop()
            if self.pet_window._drag_active:
                self.pet_window.do_drag(cursor_global)
        else:
            if self._drag_start_cursor_pos is None: return
            delta = cursor_global - self._drag_start_cursor_pos
            self.move(self._drag_start_window_pos + delta)

    def _on_drag_finished(self):
        if self.pet_window: self.pet_window.end_drag()
        else:
            self._drag_start_cursor_pos = None
            self._drag_start_window_pos = None

    def open_settings(self):
        if not hasattr(self, 'settings_window') or not self.settings_window.isVisible():
            from app.settings_window import SettingsWindow
            self.settings_window = SettingsWindow(self, self.pet_window)
            self.settings_window.show()
        else:
            self.settings_window.raise_()
            self.settings_window.activateWindow()

    def close_program(self):
        self.is_shutting_down = True
        self.chat_client.close()
            
        QApplication.instance().quit()
        
        import os
        os._exit(0)

    def eventFilter(self, obj, event):
        if obj is not self.container: return super().eventFilter(obj, event)
        etype = event.type()
        if etype == QEvent.Type.MouseMove:
            gpos = event.globalPosition().toPoint()
            if self._resize_active:
                self._do_resize(gpos)
                return True
            self._update_resize_cursor(get_resize_dir(self, gpos))
        elif etype == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                gpos = event.globalPosition().toPoint()
                d = get_resize_dir(self, gpos)
                if d != DIR_NONE:
                    self._start_resize(gpos, d)
                    return True
        elif etype == QEvent.Type.MouseButtonRelease:
            if self._resize_active and event.button() == Qt.LeftButton:
                self._end_resize()
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            d = get_resize_dir(self, event.globalPosition().toPoint())
            if d != DIR_NONE:
                self._start_resize(event.globalPosition().toPoint(), d)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        gpos = event.globalPosition().toPoint()
        if self._resize_active:
            self._do_resize(gpos)
            event.accept()
            return
        self._update_resize_cursor(get_resize_dir(self, gpos))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_active and event.button() == Qt.LeftButton:
            self._end_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _update_resize_cursor(self, d: int):
        self.setCursor(QCursor(RESIZE_CURSOR_MAP.get(d, Qt.CursorShape.ArrowCursor)))

    def _start_resize(self, cursor_global: QPoint, d: int):
        self._resize_active = True
        self._resize_dir = d
        self._resize_start_global = cursor_global
        self._resize_start_geom = self.geometry()

    def _do_resize(self, cursor_global: QPoint):
        if self._resize_start_global is None: return
        delta = cursor_global - self._resize_start_global
        g = QRect(self._resize_start_geom)
        if self._resize_dir & DIR_RIGHT: g.setRight(g.right() + delta.x())
        if self._resize_dir & DIR_BOTTOM: g.setBottom(g.bottom() + delta.y())
        if self._resize_dir & DIR_LEFT: g.setLeft(g.left() + delta.x())
        if self._resize_dir & DIR_TOP: g.setTop(g.top() + delta.y())

        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        if g.width() < min_w:
            if self._resize_dir & DIR_LEFT: g.setLeft(g.right() - min_w)
            else: g.setRight(g.left() + min_w)
        if g.height() < min_h:
            if self._resize_dir & DIR_TOP: g.setTop(g.bottom() - min_h)
            else: g.setBottom(g.top() + min_h)

        self.setGeometry(g)
        sync_pet_with_bubble(self, self.pet_window)
    
    def _end_resize(self):
        self._resize_active = False
        self._resize_dir = DIR_NONE
        self._resize_start_global = None
        self._resize_start_geom = None
        self.unsetCursor()
