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
    IMAGE_PREVIEW_AREA_STYLE,
    IMAGE_REMOVE_BTN_STYLE,
    WINDOW_WIDTH,
    WINDOW_HEIGHT,
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
from app.chat_gui import (
    BubbleFrame, ChatInputField, ImagePreviewItem,
    RESIZE_MARGIN, DIR_NONE, DIR_LEFT, DIR_RIGHT, DIR_TOP, DIR_BOTTOM, RESIZE_CURSOR_MAP,
    fit_bubble_size, render_thinking_html, scroll_to_bottom,
    get_resize_dir, sync_pet_with_bubble
)

MAX_IMAGES = 3


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

        # ── 투명도 조절 영역 ──────────────────────────────
        opacity_layout = QHBoxLayout()
        chat_opacity_label = QLabel("채팅창 투명도:")
        chat_opacity_label.setStyleSheet(OPACITY_LABEL_STYLE)
        self.chat_opacity_slider = QSlider(Qt.Horizontal)
        self.chat_opacity_slider.setRange(0, 100)
        self.chat_opacity_slider.setValue(100)
        self.chat_opacity_slider.setStyleSheet(OPACITY_SLIDER_STYLE)
        self.chat_opacity_slider.valueChanged.connect(self.set_chat_opacity)

        pet_opacity_label = QLabel("펫 투명도:")
        pet_opacity_label.setStyleSheet(OPACITY_LABEL_STYLE)
        self.pet_opacity_slider = QSlider(Qt.Horizontal)
        self.pet_opacity_slider.setRange(0, 100)
        self.pet_opacity_slider.setValue(100)
        self.pet_opacity_slider.setStyleSheet(OPACITY_SLIDER_STYLE)
        self.pet_opacity_slider.valueChanged.connect(self.set_pet_opacity)

        opacity_layout.addWidget(chat_opacity_label)
        opacity_layout.addWidget(self.chat_opacity_slider)
        opacity_layout.addWidget(pet_opacity_label)
        opacity_layout.addWidget(self.pet_opacity_slider)

        # ── 입력 하단 버튼 행 ─────────────────────────────────
        bottom_layout = QHBoxLayout()
        self.attach_btn = QPushButton("📎")
        self.attach_btn.setStyleSheet(ATTACH_BTN_STYLE)
        self.attach_btn.setToolTip("이미지 첨부 (최대 3개)")
        self.attach_btn.setFixedSize(30, 30)
        self.attach_btn.clicked.connect(self.attach_image)

        self.close_btn = QPushButton("종료")
        self.close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        self.close_btn.clicked.connect(self.close_program)

        bottom_layout.addWidget(self.attach_btn)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(self.chat_scroll_area, 1)
        layout.addWidget(self.btn_area)
        layout.addWidget(self.image_preview_area)
        layout.addWidget(self.input_field)
        layout.addLayout(opacity_layout)
        layout.addLayout(bottom_layout)
        
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
        if images:
            for image_uri in images:
                formatted_text += f"\n\n![이미지]({image_uri})"

        # 마크다운을 HTML로 변환
        html_content = convert_markdown_to_html(formatted_text)
        user_html = USER_MSG_FORMAT.format(text=html_content)
        self._add_bubble(user_html, "user")

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

    def set_chat_opacity(self, value):
        opacity = value / 100.0
        self.setWindowOpacity(opacity)

    def set_pet_opacity(self, value):
        if self.pet_window:
            opacity = value / 100.0
            self.pet_window.setWindowOpacity(opacity)

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
