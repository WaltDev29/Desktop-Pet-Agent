import html
import json
import base64
import os
import re
import uuid

from PySide6.QtWidgets import (
    QWidget, QTextEdit, QTextBrowser, QVBoxLayout, QPushButton, QHBoxLayout,
    QApplication, QGraphicsDropShadowEffect, QLabel, QFrame,
    QFileDialog, QScrollArea, QSlider, QMessageBox
)
from PySide6.QtCore import Qt, Signal, QPoint, QTimer, QEvent, QRect, QUrl, QSettings, QByteArray, QSize
from PySide6.QtGui import QColor, QPixmap, QCursor, QDesktopServices, QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer

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
    PET_BUBBLE_STYLE_WITH_THINKING,
    PET_BUBBLE_INNER_TEXT_STYLE,
    ERROR_BUBBLE_STYLE,
    CHAT_SCROLL_AREA_STYLE,
    DARK_THEME,
    LIGHT_THEME,
    get_chat_scroll_area_style,
    get_input_field_style,
    get_sidebar_style,
    get_session_item_style,
    get_session_item_active_style,
    get_sidebar_new_chat_btn_style,
    get_settings_btn_style,
    get_sidebar_toggle_btn_style,
    get_sidebar_scroll_style,
)

from app.chat_network import ChatClient
from app.chat_handler import ChatResponseHandler
from app.chat_session import ChatSession, BubbleSnapshot, StreamState
from app.chat_gui import (
    BubbleFrame, ChatInputField, ImagePreviewItem,
    RESIZE_MARGIN, DIR_NONE, DIR_LEFT, DIR_RIGHT, DIR_TOP, DIR_BOTTOM, RESIZE_CURSOR_MAP,
    fit_bubble_size, ThinkingWidget, apply_markdown_css, scroll_to_bottom,
    get_resize_dir, sync_pet_with_bubble
)

MAX_IMAGES = 3
SIDEBAR_ANIM_DURATION = 180  # 사이드바 애니메이션 시간(ms)

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon")


def _make_svg_icon(name: str, color: str, size: int = 18) -> QIcon:
    path = os.path.join(_ICON_DIR, f"{name}.svg")
    with open(path, "r", encoding="utf-8") as f:
        svg = f.read()
    svg = re.sub(r'fill="[^"]*"', f'fill="{color}"', svg)
    svg = re.sub(r'<path(?![^>]*fill=)', f'<path fill="{color}"', svg)
    ba = QByteArray(svg.encode("utf-8"))
    renderer = QSvgRenderer(ba)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class ChatWindow(QWidget):
    def __init__(self, pet_window=None):
        super().__init__(pet_window)
        self.pet_window = pet_window
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
        
        # ── 로컬 세션 상태 로드 (낙관적 UI) ────────────────────────
        self.settings = QSettings("PetAgent", "ChatApp")
        self._current_theme = DARK_THEME
        saved_session_ids = self.settings.value("agent_sessions_list", [])
        saved_session_titles_json = self.settings.value("agent_session_titles", "{}")
        try:
            saved_session_titles = json.loads(saved_session_titles_json)
        except Exception:
            saved_session_titles = {}
        saved_current_id = self.settings.value("agent_session_id", None)
        
        # ── 세션 관리 상태 ──────────────────────────────────
        self._sidebar_expanded = False
        self._session_item_btns: list[tuple] = []  # (ChatSession, QPushButton, QWidget)
        self.sessions: list[ChatSession] = []
        self._is_first_sync = True
        
        if saved_session_ids:
            for sid in saved_session_ids:
                title = saved_session_titles.get(sid) or f"세션: {sid[:6]}..."
                self.sessions.append(ChatSession(session_id=sid, title=title))
            current_found = next((s for s in self.sessions if s.session_id == saved_current_id), None)
            self.current_session = current_found if current_found else self.sessions[0]
        else:
            self.current_session = ChatSession()
            self.sessions.append(self.current_session)

        self.sent_message_ids = set()

        # ── 채팅 스크롤 영역 (개별 말풍선 위젯 방식) ──
        self.chat_scroll_area = QScrollArea()
        self.chat_scroll_area.setWidgetResizable(True)
        self.chat_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.chat_scroll_area.setStyleSheet(get_chat_scroll_area_style(self._current_theme))

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

        self.sidebar_toggle_btn = QPushButton()
        self.sidebar_toggle_btn.setStyleSheet(get_sidebar_toggle_btn_style(self._current_theme))
        self.sidebar_toggle_btn.setToolTip("채팅 목록 열기/닫기")
        self.sidebar_toggle_btn.setIconSize(QSize(18, 18))
        self.sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        
        self.new_chat_btn = QPushButton("신규 채팅")
        self.new_chat_btn.setStyleSheet(NEW_CHAT_BTN_STYLE)
        self.new_chat_btn.clicked.connect(self.prepare_new_chat)
        
        self.settings_btn = QPushButton("설정")
        self.settings_btn.setStyleSheet(get_settings_btn_style(self._current_theme))
        self.settings_btn.clicked.connect(self.open_settings)
        
        self.top_close_btn = QPushButton()
        self.top_close_btn.setFixedSize(28, 28)
        self.top_close_btn.setIconSize(QSize(14, 14))
        self.top_close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(220, 50, 50, 180);
            }
        """)
        self.top_close_btn.clicked.connect(self.close_program)
        self.top_close_btn.setToolTip("프로그램 종료")

        top_btn_layout.addWidget(self.sidebar_toggle_btn)
        top_btn_layout.addStretch()
        top_btn_layout.addWidget(self.top_close_btn)

        self.input_field = ChatInputField()
        self.input_field.setPlaceholderText("무엇을 도와드릴까요?")
        self.input_field.setStyleSheet(get_input_field_style(self._current_theme))
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
        
        self.attach_btn = QPushButton(self.input_field)
        self.attach_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover { background-color: rgba(255,255,255,15); border-radius: 6px; }
            QPushButton:disabled { opacity: 0.4; }
        """)
        self.attach_btn.setToolTip("이미지 첨부 (최대 3개)")
        self.attach_btn.setFixedSize(36, 36)
        self.attach_btn.setIconSize(QSize(20, 20))
        self.attach_btn.move(8, 7)
        self.attach_btn.clicked.connect(self.attach_image)

        self._is_agent_busy = False
        self.send_btn = QPushButton()
        self.send_btn.setFixedSize(50, 50)
        self.send_btn.setIconSize(QSize(22, 22))
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #2979B0;
                border-radius: 12px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #1A5F8F;
            }
            QPushButton:disabled {
                background-color: #7AA9C8;
            }
        """)
        self.send_btn.setToolTip("메시지 전송")
        self.send_btn.clicked.connect(self.send_message)

        input_layout.addWidget(self.input_field)
        input_layout.addWidget(self.send_btn, 0, Qt.AlignBottom)

        # ── 하단 버튼 행 (로그아웃 버튼) ──────────────────────────────────
        self.logout_btn = QPushButton("로그아웃")
        self.logout_btn.setStyleSheet("background-color: #D32F2F; color: white; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 8px 16px;")
        self.logout_btn.clicked.connect(self._handle_logout)


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

        # ── 수평 분할: 사이드바(좌) + 채팅 영역(우) ──────────
        inner_h_layout = QHBoxLayout()
        inner_h_layout.setContentsMargins(0, 0, 0, 0)
        inner_h_layout.setSpacing(12)

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
        self.chat_client.session_id = self.current_session.session_id
        self.chat_client.signaler.response_received.connect(self.on_response_received)
        self.chat_client.signaler.error_occurred.connect(self.on_error_occurred)
        self.chat_client.signaler.connected.connect(self._on_ws_connected)

        # Race condition 방지: 이미 연결된 상태라면 수동으로 트리거
        with self.chat_client._ws_lock:
            if self.chat_client.ws_conn:
                QTimer.singleShot(0, self._on_ws_connected)

        # 시작 시 사이드바를 기본으로 열어두어 변경사항을 바로 확인할 수 있도록 함
        self._toggle_sidebar()

        # 스트림 관련 변수
        self._streaming = False
        self._current_stream_text = ""
        self._current_node_name = None
        self._current_response_index: int | None = None

        # 사고 과정 로그 누적
        self._thinking_logs: list[str] = []
        self._thinking_stream_buffer = ""


        

        self.handler = ChatResponseHandler(self)
        self.apply_theme("dark")

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

    def prepare_new_chat(self):
        """신규 채팅을 입력할 수 있도록 UI를 초기화하고 임시 세션 상태로 전환합니다."""
        if self.current_session and not self.current_session.session_id:
            return  # 이미 임시 세션 상태인 경우 무시
            
        # 임시 세션 생성
        new_session = ChatSession(session_id=None, title="새 대화")
        self.sessions.insert(0, new_session)
        self.current_session = new_session
        self.chat_client.session_id = None
        
        # 사이드바에 임시 항목 추가
        self._add_session_item(new_session, index=0)
        self._update_session_highlight()
        
        # 화면 초기화
        self._clear_bubble_widgets()
        self._reset_stream_state()
        self.input_field.clear()
        self._clear_attached_images()
        self.input_field.setEnabled(True)
        self._update_attach_btn_state()
        self._add_bubble(PET_MSG_FORMAT.format(text="새로운 대화 세션이 시작되었습니다."), "pet", add_to_session=False)

    def create_new_session(self):
        """메시지를 처음 전송할 때 임시 세션을 실제 세션으로 확정합니다."""
        new_sid = str(uuid.uuid4())
        
        # 현재 임시 세션에 ID 부여
        if self.current_session and not self.current_session.session_id:
            self.current_session.session_id = new_sid
            self.current_session.title = "새 채팅"
        else:
            new_session = ChatSession(session_id=new_sid, title="새 채팅")
            self.sessions.insert(0, new_session)
            self.current_session = new_session
            
        self.chat_client.session_id = new_sid
        
        # 사이드바 업데이트 (sync_session_list 사용)
        self.sync_session_list([s.session_id for s in self.sessions if s.session_id])
        
        # 서버로 알림
        payload = {"type": "session_created", "payload": {"session_id": new_sid}}
        self.chat_client.send_message(payload)

    # ── 사이드바 구성 ────────────────────────────────────────────

    def _build_sidebar(self) -> QWidget:
        """좌측 세션 목록 사이드바 위젯을 생성합니다."""
        from PySide6.QtWidgets import QSizePolicy

        panel = QWidget()
        panel.setObjectName("sidebar_panel")
        panel.setStyleSheet(get_sidebar_style(self._current_theme))
        panel.setFixedWidth(SIDEBAR_WIDTH)
        panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(8, 12, 8, 12)
        panel_layout.setSpacing(8)

        # 상단 신규 채팅 버튼
        panel_layout.addWidget(self.new_chat_btn)

        # 헤더
        header = QLabel("채팅 목록")
        header.setObjectName("sidebar_header")
        panel_layout.addWidget(header)

        # 세션 목록 스크롤 영역
        self.session_list_scroll = QScrollArea()
        self.session_list_scroll.setWidgetResizable(True)
        self.session_list_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.session_list_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.session_list_scroll.setStyleSheet(get_sidebar_scroll_style(self._current_theme))

        self.session_list_content = QWidget()
        self.session_list_content.setStyleSheet("background: transparent;")
        self.session_list_layout = QVBoxLayout(self.session_list_content)
        self.session_list_layout.setContentsMargins(0, 0, 0, 0)
        self.session_list_layout.setSpacing(0)
        self.session_list_layout.addStretch()

        self.session_list_scroll.setWidget(self.session_list_content)
        panel_layout.addWidget(self.session_list_scroll, 1)

        # 초기 세션 목록 렌더링
        for s in self.sessions:
            self._add_session_item(s)
        self._update_session_highlight()
        
        # 하단 설정 / 종료 버튼 영역
        panel_bottom_layout = QVBoxLayout()
        panel_bottom_layout.setSpacing(6)
        panel_bottom_layout.addWidget(self.settings_btn)
        panel_bottom_layout.addWidget(self.logout_btn)
        
        panel_layout.addLayout(panel_bottom_layout)

        return panel

    def _toggle_sidebar(self):
        """사이드바를 접거나 펼칩니다. 창 너비도 함께 조정합니다."""
        self._sidebar_expanded = not self._sidebar_expanded

        icon_color = self._current_theme.get("icon_color", "#AAAAAA")
        if self._sidebar_expanded:
            self.sidebar_panel.show()
            self.resize(SIDEBAR_EXPANDED_WINDOW_WIDTH, self.height())
            self.sidebar_toggle_btn.setIcon(_make_svg_icon("ic_menu_close", icon_color))
            self.sidebar_toggle_btn.setToolTip("채팅 목록 닫기")
        else:
            self.sidebar_panel.hide()
            self.resize(WINDOW_WIDTH, self.height())
            self.sidebar_toggle_btn.setIcon(_make_svg_icon("ic_menu", icon_color))
            self.sidebar_toggle_btn.setToolTip("채팅 목록 열기/닫기")

        sync_pet_with_bubble(self, self.pet_window)

    # ── 세션 저장/복원 ────────────────────────────────────────────

    def _save_local_sessions(self):
        session_ids = [s.session_id for s in self.sessions if s.session_id]
        session_titles = {s.session_id: s.title for s in self.sessions if s.session_id}
        self.settings.setValue("agent_sessions_list", session_ids)
        self.settings.setValue("agent_session_titles", json.dumps(session_titles))
        if self.current_session and self.current_session.session_id:
            self.settings.setValue("agent_session_id", self.current_session.session_id)
        else:
            self.settings.remove("agent_session_id")

    def _on_ws_connected(self):
        # 웹소켓 연결 성공 시, 로컬에 저장된 세션이 있다면 즉시 히스토리 로드
        if self.current_session.session_id:
            self._load_session(self.current_session)

    def _load_session(self, session: ChatSession):
        self._clear_bubble_widgets()
        self._reset_stream_state()
        self.current_session = session
        self.chat_client.session_id = session.session_id
        self._save_local_sessions()
        
        # 만약 로컬에 이미 보존된 대화 이력이 있다면 즉시 복원 (사용자 경험/반응성 극대화)
        if session.bubbles:
            for snap in session.bubbles:
                thinking_widget = None
                if snap.thinking_html_content:
                    from app.chat_gui import ThinkingWidget
                    thinking_widget = ThinkingWidget(snap.thinking_html_content)
                    if snap.thinking_expanded:
                        thinking_widget.set_expanded(True)
                bubble = self._add_bubble(snap.html, snap.msg_type, add_to_session=False, thinking_widget=thinking_widget)
                bubble.setProperty("thinking_expanded", snap.thinking_expanded)
            self.scrollToBottom()
        else:
            if session.session_id:
                self._add_bubble(f"세션({session.session_id[:6]}...)의 대화를 불러오는 중...", "pet", add_to_session=False)
                
        # 서버에 최신 대화 이력 동기화 요청
        if session.session_id:
            payload = {"type": "get_history", "payload": {"session_id": session.session_id}}
            self.chat_client.send_message(payload)
            
        self._update_session_highlight()

    # ── 사이드바 항목 관리 ─────────────────────────────────────────

    def _add_session_item(self, session: ChatSession, index: int = -1):
        """사이드바 목록에 세션 항목 버튼(+삭제 버튼)을 행 위젯으로 추가합니다."""
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(2)

        btn = QPushButton(f"{session.title}")
        btn.setStyleSheet(get_session_item_style(self._current_theme))
        btn.setToolTip(session.title)
        btn.clicked.connect(lambda checked=False, s=session: self._on_session_clicked(s))

        del_btn = QPushButton("X")
        del_btn.setFixedSize(28, 28)
        del_btn.setToolTip("이 세션 삭제")
        del_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #888888;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: rgba(220,50,50,180);
                color: white;
            }
        """)
        del_btn.clicked.connect(lambda checked=False, s=session: self._delete_session(s))

        row_layout.addWidget(btn, 1)
        row_layout.addWidget(del_btn)

        if index == -1:
            idx = self.session_list_layout.count() - 1
            self.session_list_layout.insertWidget(idx, row)
        else:
            self.session_list_layout.insertWidget(index, row)

        self._session_item_btns.append((session, btn, row))

    def _refresh_sidebar_item(self, session: ChatSession):
        """사이드바에서 해당 세션의 버튼 텍스트를 업데이트합니다."""
        for item in self._session_item_btns:
            s, btn = item[0], item[1]
            if s is session:
                btn.setText(f"{session.title}")
                btn.setToolTip(session.title)
                self._save_local_sessions()
                break

    def _update_session_highlight(self):
        """현재 활성 세션 항목만 강조 스타일로 표시합니다."""
        for item in self._session_item_btns:
            s, btn = item[0], item[1]
            if s is self.current_session:
                btn.setStyleSheet(get_session_item_active_style(self._current_theme))
            else:
                btn.setStyleSheet(get_session_item_style(self._current_theme))

    def _on_session_clicked(self, session: ChatSession):
        """사이드바 세션 항목 클릭 시 해당 세션으로 전환합니다."""
        if session is self.current_session:
            return
        self._load_session(session)

    def sync_session_list(self, session_ids: list[str], session_titles: dict | None = None):
        """게이트웨이로부터 받은 세션 리스트 동기화"""
        if session_titles is None:
            session_titles = {}

        # 1. 기존 버튼 위젯 제거
        for item in self._session_item_btns:
            row = item[2] if len(item) > 2 else item[1]
            self.session_list_layout.removeWidget(row)
            row.deleteLater()
        self._session_item_btns.clear()

        # 2. 기존 ChatSession 객체 매핑 저장 (id -> session)
        existing_sessions = {s.session_id: s for s in self.sessions if s.session_id}
        
        # 임시 세션 보존
        temp_session = next((s for s in self.sessions if not s.session_id), None)
        
        # 3. 새로운 세션 리스트 재구성
        new_sessions = []
        if temp_session:
            new_sessions.append(temp_session)
            
        for sid in session_ids:
            title = session_titles.get(sid) or f"세션: {sid[:6]}..."
            if sid in existing_sessions:
                s = existing_sessions[sid]
                # 타이틀이 업데이트되었을 수 있으므로 업데이트
                if title and not title.startswith("세션:"):
                    s.title = title
            else:
                s = ChatSession(session_id=sid, title=title)
            new_sessions.append(s)
            
        self.sessions = new_sessions

        # 4. 사이드바 아이템 다시 추가
        for s in self.sessions:
            self._add_session_item(s)

        # 5. 활성 세션 업데이트
        if self.current_session.session_id not in session_ids and self.current_session.session_id is not None and self.sessions:
            self.current_session = self.sessions[0]
            self.chat_client.session_id = self.current_session.session_id
            
        self._update_session_highlight()
        self._save_local_sessions()

    def add_session_to_list(self, sid: str):
        if not any(s.session_id == sid for s in self.sessions):
            s = ChatSession(session_id=sid, title=f"세션: {sid[:6]}...")
            self.sessions.insert(0, s)
            self._add_session_item(s, index=0)
            self._update_session_highlight()
            self._save_local_sessions()

    def remove_session_from_list(self, sid: str):
        was_current = (self.current_session.session_id == sid)
        # 기존 title 정보 보존
        existing_titles = {s.session_id: s.title for s in self.sessions if s.session_id != sid}
        self.sessions = [s for s in self.sessions if s.session_id != sid]
        self.sync_session_list(
            [s.session_id for s in self.sessions if s.session_id],
            existing_titles
        )
        if was_current:
            self._clear_bubble_widgets()
            if self.sessions:
                self.current_session = self.sessions[0]
                self.chat_client.session_id = self.current_session.session_id
                self._load_session(self.current_session)
            else:
                self._add_bubble(PET_MSG_FORMAT.format(text="모든 세션이 삭제되었습니다. 새 대화를 시작해주세요."), "pet")

    def _delete_session(self, session: ChatSession):
        """세션 삭제 확인 후 서버에 삭제 요청을 전송합니다."""
        sid = session.session_id
        if not sid:
            return

        reply = QMessageBox.question(
            self,
            "세션 삭제",
            f"'{session.title}' 세션을 삭제하시겠습니까?\n이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        # 낙관적 UI 업데이트 후 서버 전송
        self.remove_session_from_list(sid)
        payload = {"type": "session_deleted", "payload": {"session_id": sid}}
        self.chat_client.send_message(payload)
                
    def render_history(self, history: list[dict]):
        local_bubbles = self.current_session.bubbles[:]
        
        # 로컬 버퍼가 서버 히스토리보다 최신(또는 동기화됨)이라면 화면 덮어쓰기를 생략합니다.
        # (사고 과정 위젯 등의 로컬 전용 UI 상태를 보존하기 위함)
        if len(local_bubbles) >= len(history) and len(history) > 0:
            return

        self._clear_bubble_widgets()
        self.current_session.bubbles.clear()
        
        if not history:
            self._add_bubble("이전 대화가 없습니다.", "pet")
            return

        from app.chat_session import BubbleSnapshot

        for i, m in enumerate(history):
            role = m.get("role", "pet")
            if role == "assistant":
                role = "pet"
                
            text = m.get("message") or m.get("content", "")
            images = m.get("images", [])
            formatted_text = text
            for img in images:
                formatted_text += f"\n\n![\uc774\ubbf8\uc9c0]({img})"
                
            html_content = convert_markdown_to_html(formatted_text)
            
            thinking_widget = None
            snap_thinking_html = ""
            snap_thinking_expanded = False
            
            # 서버 히스토리와 로컬 스냅샷을 순서대로 매칭하여 사고 과정(Thinking) 정보 복구
            if i < len(local_bubbles) and local_bubbles[i].msg_type == role:
                snap = local_bubbles[i]
                if snap.thinking_html_content:
                    from app.chat_gui import ThinkingWidget
                    thinking_widget = ThinkingWidget(snap.thinking_html_content)
                    if snap.thinking_expanded:
                        thinking_widget.set_expanded(True)
                    snap_thinking_html = snap.thinking_html_content
                    snap_thinking_expanded = snap.thinking_expanded
                    
            bubble = self._add_bubble(html_content, role, add_to_session=False, thinking_widget=thinking_widget)
            if thinking_widget:
                bubble.setProperty("thinking_expanded", snap_thinking_expanded)
                
            new_snap = BubbleSnapshot(html=html_content, msg_type=role)
            new_snap.thinking_html_content = snap_thinking_html
            new_snap.thinking_expanded = snap_thinking_expanded
            self.current_session.bubbles.append(new_snap)

        self.scrollToBottom()
        
    def set_agent_busy(self, is_busy: bool):
        self._is_agent_busy = is_busy
        self.input_field.setEnabled(not is_busy)
        self.attach_btn.setEnabled(not is_busy)
        if is_busy:
            self.send_btn.setText("중지 🚫")
            self.send_btn.setEnabled(True)
            self.send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #C0392B;
                    color: white;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background-color: #A93226; }
            """)
        else:
            self.send_btn.setText("전송")
            self.send_btn.setEnabled(True)
            self.send_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2979B0;
                    color: white;
                    border-radius: 12px;
                    font-weight: bold;
                    font-size: 13px;
                    padding: 8px 16px;
                }
                QPushButton:hover { background-color: #1A5F8F; }
                QPushButton:disabled { background-color: #7AA9C8; color: #DDDDDD; }
            """)
            self.input_field.setFocus()

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
        if self._is_agent_busy:
            payload = {
                "type": "stop",
                "payload": {"session_id": self.current_session.session_id}
            }
            self.chat_client.send_message(payload)
            return

        text = self.input_field.toPlainText().strip()
        images = self._encode_images()
        if not text and not images:
            return

        if not self.current_session or not self.current_session.session_id:
            self.create_new_session()

        self.set_agent_busy(True)

        # 채팅 히스토리에 사용자 메시지 표시
        display_text = text if text else "(이미지 전송)"
        formatted_text = display_text
        if images:
            for image_uri in images:
                formatted_text += f"\n\n![이미지]({image_uri})"

        html_content = convert_markdown_to_html(formatted_text)
        self._add_bubble(html_content, "user")

        self._reset_stream_state()
        self._current_response_index = len(self.bubble_widgets)
        self._add_bubble("요청을 확인하고 있습니다...", "pet", add_to_session=False)

        self.scrollToBottom()
        self.input_field.clear()
        self._clear_attached_images()

        msg_id = str(uuid.uuid4())
        self.sent_message_ids.add(msg_id)

        payload = {
            "type": "chat",
            "payload": {
                "message_id": msg_id,
                "message": text,
                "images": images,
                "session_id": self.current_session.session_id
            }
        }
        self.chat_client.send_message(payload)

    # ── 말풍선 위젯 헬퍼 ─────────────────────────────────────────
    def _add_bubble(self, html_content: str, msg_type: str = "pet", add_to_session: bool = True, thinking_widget: 'ThinkingWidget | None' = None) -> QTextBrowser:
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

        def apply_shadow(widget):
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(12)
            shadow.setXOffset(0)
            shadow.setYOffset(3)
            shadow.setColor(QColor(0, 0, 0, 18))
            widget.setGraphicsEffect(shadow)

        if msg_type == "pet":
            bubble_frame = QFrame()
            bubble_frame.setObjectName("thinking_bubble_frame")
            bubble_frame.setAttribute(Qt.WA_StyledBackground, True)
            bubble_frame.setStyleSheet(PET_BUBBLE_STYLE_WITH_THINKING)
            frame_vbox = QVBoxLayout(bubble_frame)
            frame_vbox.setContentsMargins(0, 0, 0, 0)
            frame_vbox.setSpacing(0)

            if thinking_widget is not None:
                thinking_widget.make_transparent()
                frame_vbox.addWidget(thinking_widget)

            bubble = QTextBrowser()
            bubble.setOpenExternalLinks(False)
            bubble.anchorClicked.connect(self._on_bubble_link_clicked)
            bubble.setHtml(html_content)
            apply_markdown_css(bubble)
            bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            bubble.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            bubble.setProperty("msg_type", msg_type)
            bubble.document().setDocumentMargin(0)
            bubble.setStyleSheet(PET_BUBBLE_INNER_TEXT_STYLE)
            bubble.setProperty("bubble_frame", bubble_frame)
            fit_bubble_size(bubble, self.chat_scroll_area.viewport())
            
            frame_vbox.addWidget(bubble)
            vbox.addWidget(bubble_frame)
            apply_shadow(bubble_frame)
        else:
            # ── 일반 버블 (user, error) ──
            bubble = QTextBrowser()
            bubble.setOpenExternalLinks(False)
            bubble.anchorClicked.connect(self._on_bubble_link_clicked)
            bubble.setHtml(html_content)
            apply_markdown_css(bubble)
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

            fit_bubble_size(bubble, self.chat_scroll_area.viewport())
            vbox.addWidget(bubble)
            apply_shadow(bubble)

        if msg_type == "user":
            alignment = Qt.AlignRight
        elif msg_type == "error":
            alignment = Qt.AlignHCenter
        else:
            alignment = Qt.AlignLeft

        idx = self.chat_scroll_layout.count() - 1
        self.chat_scroll_layout.insertWidget(idx, container, 0, alignment)
        self.bubble_widgets.append(bubble)

        bubble.setProperty("container_widget", container)
        bubble.setProperty("thinking_widget", thinking_widget)

        if add_to_session:
            self.current_session.bubbles.append(BubbleSnapshot(html=html_content, msg_type=msg_type))

        return bubble


    def _update_bubble(self, index: int, html_content: str, msg_type: str = "pet"):
        """기존 말풍선 위젯의 HTML 내용을 업데이트합니다."""
        if 0 <= index < len(self.bubble_widgets):
            bubble = self.bubble_widgets[index]
            bubble.setHtml(html_content)
            apply_markdown_css(bubble)
            fit_bubble_size(bubble, self.chat_scroll_area.viewport())

            
            # 세션 스냅샷 업데이트
            if 0 <= index < len(self.current_session.bubbles):
                self.current_session.bubbles[index].html = html_content
                self.current_session.bubbles[index].msg_type = msg_type

    def _update_bubble_thinking_properties(self, index: int, answer_html: str, thinking_html: str, expanded: bool):
        """특정 말풍선 스냅샷의 사고과정 프로퍼티를 업데이트합니다."""
        if 0 <= index < len(self.current_session.bubbles):
            snap = self.current_session.bubbles[index]
            snap.answer_html_content = answer_html
            snap.thinking_html_content = thinking_html
            snap.thinking_expanded = expanded

    def _flush_thinking_buffer(self):
        """스트림 버퍼에 쌓인 텍스트를 사고 과정 로그에 추가합니다."""
        if self._thinking_stream_buffer.strip():
            self._thinking_logs.append(self._thinking_stream_buffer.strip())
        self._thinking_stream_buffer = ""


    def _on_bubble_link_clicked(self, url: QUrl):
        """말풍선 내 링크 클릭 처리. 외부 링크 열기."""
        url_str = url.toString()
        if not url_str.startswith("action:"):
            QDesktopServices.openUrl(url)

    def scrollToBottom(self):
        scroll_to_bottom(self.chat_scroll_area)
    
    def on_response_received(self, data: dict):
        self.handler.handle(data)


    def process_btn(self, choice: str):
        self.btn_area.hide()
        is_approved = (choice == "approved")
        
        text = "위험 작업 승인 확인" if is_approved else "위험 작업 거절 확인"
        self._add_bubble(convert_markdown_to_html(text), "pet")

        self.set_agent_busy(True)
        self.scrollToBottom()

        payload = {
            "type": "approval_response",
            "payload": {
                "approve": is_approved,
                "session_id": self.current_session.session_id,
                "tool_call_id": self.pending_tool_call_id
            }
        }
        self.chat_client.send_message(payload)

    def on_error_occurred(self, error: str):
        safe_error = html.escape(error)
        self._add_bubble(f"⚠️ {safe_error}", "error")
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

    def apply_theme(self, theme_name: str):
        """다크/화이트 테마를 채팅창 전체에 즉시 적용합니다."""
        self._current_theme = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        theme = self._current_theme
        is_dark = theme["name"] == "dark"

        self.chat_scroll_area.setStyleSheet(get_chat_scroll_area_style(theme))
        self.chat_scroll_content.setStyleSheet(f"background-color: {theme['scroll_bg']};")
        self.input_field.setStyleSheet(get_input_field_style(theme))
        self.sidebar_toggle_btn.setStyleSheet(get_sidebar_toggle_btn_style(theme))
        self.settings_btn.setStyleSheet(get_settings_btn_style(theme))
        self.new_chat_btn.setStyleSheet(get_sidebar_new_chat_btn_style(theme))
        self.sidebar_panel.setStyleSheet(get_sidebar_style(theme))
        self.session_list_scroll.setStyleSheet(get_sidebar_scroll_style(theme))

        self.container.set_theme(theme)
        self._update_session_highlight()

        icon_color = theme.get("icon_color", "#AAAAAA")
        self.top_close_btn.setIcon(_make_svg_icon("ic_x_1", icon_color, 14))
        self.attach_btn.setIcon(_make_svg_icon("ic_file", icon_color, 20))
        self.send_btn.setIcon(_make_svg_icon("ic_send", "#FFFFFF", 22))
        if self._sidebar_expanded:
            self.sidebar_toggle_btn.setIcon(_make_svg_icon("ic_menu_close", icon_color))
        else:
            self.sidebar_toggle_btn.setIcon(_make_svg_icon("ic_menu", icon_color))

        if hasattr(self, "settings_window") and self.settings_window.isVisible():
            self.settings_window.update_theme(theme)

        self.update()

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

    def _handle_logout(self):
        import requests
        from PySide6.QtWidgets import QMessageBox
        try:
            response = requests.post("http://localhost:8001/api/logout", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    QMessageBox.information(self, "로그아웃", "성공적으로 로그아웃 되었습니다.")
                    if self.pet_window:
                        self.pet_window._logged_in = False
                    self.hide()
                    if hasattr(self, 'settings_win') and self.settings_win:
                        self.settings_win.close()
                else:
                    QMessageBox.warning(self, "로그아웃 실패", data.get("message", "알 수 없는 오류가 발생했습니다."))
            else:
                QMessageBox.warning(self, "로그아웃 실패", f"서버 오류: {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "로그아웃 오류", f"로그아웃 요청 중 오류가 발생했습니다:\n{str(e)}")
