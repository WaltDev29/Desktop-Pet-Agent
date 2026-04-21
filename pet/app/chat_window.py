import threading
import html
import json
import base64
import os

from PySide6.QtWidgets import (
    QWidget, QTextEdit, QVBoxLayout, QPushButton, QHBoxLayout,
    QApplication, QFrame, QGraphicsDropShadowEffect, QLabel,
    QFileDialog, QScrollArea, QSizePolicy, QSlider
)
from PySide6.QtCore import Qt, Signal, QObject, QRectF, QPoint, QTimer, QEvent, QRect
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QCursor

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
    OPACITY_LABEL_STYLE
)

class ChatSignaler(QObject):
    response_received = Signal(dict)
    error_occurred = Signal(str)

class ChatInputField(QTextEdit):
    returnPressed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(50)
        self.setAcceptRichText(False)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
            self.returnPressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

class BubbleFrame(QFrame):
    # 드래그 시작을 알리는 시그널 (글로벌 마우스 위치)
    drag_started = Signal(QPoint)
    drag_moved = Signal(QPoint)
    drag_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_active = False
        self._press_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._press_pos = event.globalPosition().toPoint()
            self._drag_active = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and event.buttons() & Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_pos
            if not self._drag_active and delta.manhattanLength() > 5:
                self._drag_active = True
                self.drag_started.emit(self._press_pos)
            if self._drag_active:
                self.drag_moved.emit(event.globalPosition().toPoint())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._drag_active:
            self.drag_finished.emit()
        self._drag_active = False
        self._press_pos = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        tail_height = 15
        tail_width = 20
        radius = 15
        
        body_rect = QRectF(1, 1, rect.width() - 2, rect.height() - tail_height - 2)
        
        path = QPainterPath()
        path.moveTo(body_rect.left() + radius, body_rect.top())
        path.lineTo(body_rect.right() - radius, body_rect.top())
        path.arcTo(body_rect.right() - 2*radius, body_rect.top(), 2*radius, 2*radius, 90, -90)
        
        path.lineTo(body_rect.right(), body_rect.bottom() - radius)
        path.arcTo(body_rect.right() - 2*radius, body_rect.bottom() - 2*radius, 2*radius, 2*radius, 0, -90)
        
        center_x = body_rect.center().x()
        path.lineTo(center_x + tail_width/2, body_rect.bottom())
        path.lineTo(center_x, body_rect.bottom() + tail_height) 
        path.lineTo(center_x - tail_width/2, body_rect.bottom())
        
        path.lineTo(body_rect.left() + radius, body_rect.bottom())
        path.arcTo(body_rect.left(), body_rect.bottom() - 2*radius, 2*radius, 2*radius, -90, -90)
        
        path.lineTo(body_rect.left(), body_rect.top() + radius)
        path.arcTo(body_rect.left(), body_rect.top(), 2*radius, 2*radius, 180, -90)
        
        path.closeSubpath()
        
        painter.fillPath(path, QColor(255, 255, 255, 245))

        pen = QPen(QColor("#e0e0e0"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)

MAX_IMAGES = 3

# ── 리사이즈 상수 ──────────────────────────────────────────────────
_RESIZE_MARGIN = 8
_DIR_NONE   = 0
_DIR_LEFT   = 1
_DIR_RIGHT  = 2
_DIR_TOP    = 4
_DIR_BOTTOM = 8
_RESIZE_CURSOR_MAP = {
    _DIR_NONE                : Qt.CursorShape.ArrowCursor,
    _DIR_LEFT                : Qt.CursorShape.SizeHorCursor,
    _DIR_RIGHT               : Qt.CursorShape.SizeHorCursor,
    _DIR_TOP                 : Qt.CursorShape.SizeVerCursor,
    _DIR_BOTTOM              : Qt.CursorShape.SizeVerCursor,
    _DIR_LEFT  | _DIR_TOP    : Qt.CursorShape.SizeFDiagCursor,
    _DIR_RIGHT | _DIR_BOTTOM : Qt.CursorShape.SizeFDiagCursor,
    _DIR_RIGHT | _DIR_TOP    : Qt.CursorShape.SizeBDiagCursor,
    _DIR_LEFT  | _DIR_BOTTOM : Qt.CursorShape.SizeBDiagCursor,
}

class ImagePreviewItem(QWidget):
    """이미지 미리보기 아이템 (썸네일 + 제거 버튼)"""
    remove_requested = Signal(object)  # self

    def __init__(self, file_path: str, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.setFixedSize(62, 62)

        # 썸네일
        self.thumb = QLabel(self)
        self.thumb.setFixedSize(60, 60)
        self.thumb.setScaledContents(True)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet("border: 1px solid #D0D0D0; border-radius: 8px; background-color: #EFEFEF;")

        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.thumb.setPixmap(pixmap.scaled(60, 60, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.thumb.setText("❌")
            self.thumb.setAlignment(Qt.AlignCenter)

        # 제거 버튼 (우상단 오버레이)
        self.remove_btn = QPushButton("✕", self)
        self.remove_btn.setStyleSheet(IMAGE_REMOVE_BTN_STYLE)
        self.remove_btn.setFixedSize(16, 16)
        self.remove_btn.move(44, 2)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_btn.raise_()


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
        self._resize_dir = _DIR_NONE
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
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet(CHAT_HISTORY_STYLE)
        
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

        layout.addWidget(self.chat_history)
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
        
        self.signaler = ChatSignaler()
        self.signaler.response_received.connect(self.on_response_received)
        self.signaler.error_occurred.connect(self.on_error_occurred)

        self.pending_tool_call_id = None
        self.session_id = None
        self.ws_url = "ws://localhost:8000/ws"
        self.ws_conn = None
        self._ws_lock = threading.Lock()

        self.pet_window = pet_window
        self._start_websocket_thread()

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
        formatted_text = display_text.replace('\n', '<br>')
        if images:
            img_count = len(images)
            formatted_text += f"<br><span style='color:#888888; font-size:11px;'>📎 이미지 {img_count}장 첨부</span>"

        user_html = USER_MSG_FORMAT.format(text=formatted_text)
        self.message_history.append(user_html)

        thinking_html = PET_MSG_FORMAT.format(text="생각 중...")
        full_html = "".join(self.message_history) + thinking_html
        self.chat_history.setHtml(full_html)
        self.scrollToBottom()

        self.input_field.clear()
        self._clear_attached_images()
        self.input_field.setEnabled(False)
        self.attach_btn.setEnabled(False)

        payload = {"action": "chat", "message": api_message, "images": images}
        self._send_ws_message(payload)
            
    def scrollToBottom(self):
        scrollbar = self.chat_history.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _start_websocket_thread(self):
        thread = threading.Thread(target=self._websocket_worker, daemon=True)
        thread.start()

    def _websocket_worker(self):
        from websockets.sync.client import connect
        try:
            with connect(self.ws_url) as websocket:
                with self._ws_lock:
                    self.ws_conn = websocket
                
                # Listen continuously
                while True:
                    try:
                        message = websocket.recv()
                        data = json.loads(message)
                        self.signaler.response_received.emit(data)
                    except Exception as e:
                        print(f"WebSocket 닫힘 또는 수신 에러: {e}")
                        break
        except Exception as e:
            self.signaler.error_occurred.emit(f"WebSocket 서버 연결 실패: {e}")
        finally:
            with self._ws_lock:
                self.ws_conn = None

    def _send_ws_message(self, payload: dict):
        if self.session_id:
            payload["session_id"] = self.session_id
        
        def _do_send():
            with self._ws_lock:
                if self.ws_conn:
                    try:
                        self.ws_conn.send(json.dumps(payload))
                    except Exception as e:
                        self.signaler.error_occurred.emit(f"메시지 전송 실패: {e}")
                else:
                    self.signaler.error_occurred.emit("서버와 연결되어 있지 않습니다. 다시 실행해주세요.")

        threading.Thread(target=_do_send, daemon=True).start()

    
    def on_response_received(self, data: dict):
        if self.is_shutting_down:
            QApplication.instance().quit()
            return

        # 에이전트가 오류 응답을 반환한 경우 에러로 처리
        if data.get("status") == "error":
            self.on_error_occurred(data.get("message", "알 수 없는 오류가 발생했습니다."))
            return

        reply = data.get("response") or data.get("message") or str(data)
        formatted_reply = reply.replace('\n', '<br>')
        
        pet_html = PET_MSG_FORMAT.format(text=formatted_reply)
        self.message_history.append(pet_html)
        
        self.chat_history.setHtml("".join(self.message_history))
        self.scrollToBottom()
        
        if data.get("session_id"): self.session_id = data["session_id"]
        self.pending_tool_call_id = data.get("tool_call_id")
        
        is_waiting = (data.get("status") == "approval_required")
        self.btn_area.setVisible(is_waiting)
        self.input_field.setEnabled(not is_waiting)
        self.attach_btn.setEnabled(not is_waiting)
        if not is_waiting: self.input_field.setFocus()


    def process_btn(self, choice: str):
        self.btn_area.hide()
        is_approved = (choice == "approved")
        choice_text = "승인" if is_approved else "거절"
        
        user_msg = USER_MSG_FORMAT.format(text=f"[{choice_text}] 하겠어.")
        self.message_history.append(user_msg)
        
        thinking_html = PET_MSG_FORMAT.format(text="결과를 서버에 전달하는 중...")
        full_html = "".join(self.message_history) + thinking_html
        self.chat_history.setHtml(full_html)
        self.scrollToBottom()

        payload = {
            "action": "approve",
            "approve": is_approved,
            "tool_call_id": self.pending_tool_call_id
        }
        self._send_ws_message(payload)

    def on_error_occurred(self, error: str):
        safe_error = html.escape(error)
        
        error_msg = ERROR_MSG_FORMAT.format(text=safe_error)
        self.message_history.append(error_msg)
        self.chat_history.setHtml("".join(self.message_history))
        self.scrollToBottom()
        
        self.input_field.setEnabled(True)
        self.attach_btn.setEnabled(True)
        self.input_field.setFocus()

    # ── 드래그 이동 ───────────────────────────────────────────
    def _on_drag_started(self, cursor_global: QPoint):
        """BubbleFrame 드래그 시작 → pet_window에 위임합니다."""
        if self.pet_window:
            self.pet_window.start_drag(cursor_global)
        else:
            # pet_window가 없을 때 채팅창만 단독 이동
            self._drag_start_cursor_pos = cursor_global
            self._drag_start_window_pos = self.pos()

    def _on_drag_moved(self, cursor_global: QPoint):
        """BubbleFrame 드래그 중 → pet_window에 위임합니다."""
        if self.pet_window:
            if not self.pet_window._drag_active:
                delta = cursor_global - self.pet_window._drag_start_cursor
                if delta.manhattanLength() > 5:
                    self.pet_window._drag_active = True
                    self.pet_window.timer.stop()
            if self.pet_window._drag_active:
                self.pet_window.do_drag(cursor_global)
        else:
            if self._drag_start_cursor_pos is None:
                return
            delta = cursor_global - self._drag_start_cursor_pos
            self.move(self._drag_start_window_pos + delta)

    def _on_drag_finished(self):
        """BubbleFrame 드래그 종료 → pet_window에 위임합니다."""
        if self.pet_window:
            self.pet_window.end_drag()
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
        
        with self._ws_lock:
            if hasattr(self, 'ws_conn') and self.ws_conn:
                try:
                    self.ws_conn.close()
                except Exception:
                    pass
            
        QApplication.instance().quit()
        
        import os
        os._exit(0)

    # ── 리사이즈: 이벤트 필터 (BubbleFrame 위에서도 동작) ─────────────
    def eventFilter(self, obj, event):
        if obj is not self.container:
            return super().eventFilter(obj, event)

        etype = event.type()

        if etype == QEvent.Type.MouseMove:
            gpos = event.globalPosition().toPoint()
            if self._resize_active:
                self._do_resize(gpos)
                return True                       # 드래그 이동 차단
            self._update_resize_cursor(self._get_resize_dir(gpos))
            return False

        elif etype == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.LeftButton:
                gpos = event.globalPosition().toPoint()
                d = self._get_resize_dir(gpos)
                if d != _DIR_NONE:
                    self._start_resize(gpos, d)
                    return True                   # 드래그 시작 차단
            return False

        elif etype == QEvent.Type.MouseButtonRelease:
            if self._resize_active and event.button() == Qt.LeftButton:
                self._end_resize()
                return True
            return False

        return super().eventFilter(obj, event)

    # ChatWindow 마진 영역(BubbleFrame 밖)도 리사이즈 처리
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            d = self._get_resize_dir(event.globalPosition().toPoint())
            if d != _DIR_NONE:
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
        self._update_resize_cursor(self._get_resize_dir(gpos))
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resize_active and event.button() == Qt.LeftButton:
            self._end_resize()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    # ── 리사이즈 헬퍼 ────────────────────────────────────────────────
    def _get_resize_dir(self, cursor_global: QPoint) -> int:
        """커서가 창 가장자리 어느 방향에 있는지 비트마스크로 반환합니다."""
        m = _RESIZE_MARGIN
        x, y = cursor_global.x(), cursor_global.y()
        wx, wy = self.x(), self.y()
        ww, wh = self.width(), self.height()

        d = _DIR_NONE
        if x <= wx + m:
            d |= _DIR_LEFT
        elif x >= wx + ww - m:
            d |= _DIR_RIGHT
        if y <= wy + m:
            d |= _DIR_TOP
        elif y >= wy + wh - m:
            d |= _DIR_BOTTOM
        return d

    def _update_resize_cursor(self, d: int):
        self.setCursor(QCursor(_RESIZE_CURSOR_MAP.get(d, Qt.CursorShape.ArrowCursor)))

    def _start_resize(self, cursor_global: QPoint, d: int):
        self._resize_active = True
        self._resize_dir = d
        self._resize_start_global = cursor_global
        self._resize_start_geom = self.geometry()

    def _do_resize(self, cursor_global: QPoint):
        if self._resize_start_global is None:
            return
        delta = cursor_global - self._resize_start_global
        g = QRect(self._resize_start_geom)

        if self._resize_dir & _DIR_RIGHT:
            g.setRight(g.right() + delta.x())
        if self._resize_dir & _DIR_BOTTOM:
            g.setBottom(g.bottom() + delta.y())
        if self._resize_dir & _DIR_LEFT:
            g.setLeft(g.left() + delta.x())
        if self._resize_dir & _DIR_TOP:
            g.setTop(g.top() + delta.y())

        # 최소 크기 강제
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        if g.width() < min_w:
            if self._resize_dir & _DIR_LEFT:
                g.setLeft(g.right() - min_w)
            else:
                g.setRight(g.left() + min_w)
        if g.height() < min_h:
            if self._resize_dir & _DIR_TOP:
                g.setTop(g.bottom() - min_h)
            else:
                g.setBottom(g.top() + min_h)

        self.setGeometry(g)

    def _end_resize(self):
        self._resize_active = False
        self._resize_dir = _DIR_NONE
        self._resize_start_global = None
        self._resize_start_geom = None
        self.unsetCursor()