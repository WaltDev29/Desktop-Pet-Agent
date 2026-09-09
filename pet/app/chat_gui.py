from PySide6.QtWidgets import QFrame, QWidget, QTextEdit, QLabel, QPushButton, QHBoxLayout, QTextBrowser, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QTimer, QUrl, QByteArray
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QCursor, QDesktopServices, QTextCursor, QTextFormat, QImage, QTextDocument

from app.chat_style import (
    IMAGE_REMOVE_BTN_STYLE,
    FONT_FAMILY,
    MARKDOWN_CSS,
    BUBBLE_MAX_HEIGHT,
)

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
            self.thumb.setText("X")
            self.thumb.setAlignment(Qt.AlignCenter)

        # 제거 버튼 (우상단 오버레이)
        self.remove_btn = QPushButton("✕", self)
        self.remove_btn.setStyleSheet(IMAGE_REMOVE_BTN_STYLE)
        self.remove_btn.setFixedSize(16, 16)
        self.remove_btn.move(44, 2)
        self.remove_btn.clicked.connect(lambda: self.remove_requested.emit(self))
        self.remove_btn.raise_()

class BubbleFrame(QFrame):
    # 드래그 시작을 알리는 시그널 (글로벌 마우스 위치)
    drag_started = Signal(QPoint)
    drag_moved = Signal(QPoint)
    drag_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_active = False
        self._press_pos = None
        self._bg_color = QColor(34, 34, 34, 245)
        self._border_color = QColor("#444444")

    def set_theme(self, theme: dict):
        self._bg_color = QColor(
            theme["bubble_frame_bg_r"],
            theme["bubble_frame_bg_g"],
            theme["bubble_frame_bg_b"],
            theme["bubble_frame_bg_a"],
        )
        self._border_color = QColor(theme["bubble_frame_border"])
        self.update()

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
        """말풍선 배경을 그리고 마우스 이벤트를 받기 위한 투명 레이어를 생성합니다."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 투명 영역 클릭을 감지하기 위해 아주 미세한 알파값(1)을 가진 배경을 채움
        painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        
        rect = self.rect()
        tail_height = 15
        tail_width = 20
        radius = 15
        
        # 실제 말풍선 본체 영역 (상하좌우 1px씩 여백)
        body_rect = QRectF(1, 1, rect.width() - 2, rect.height() - tail_height - 2)
        
        path = QPainterPath()
        # 말풍선 상단 및 측면 그리기
        path.moveTo(body_rect.left() + radius, body_rect.top())
        path.lineTo(body_rect.right() - radius, body_rect.top())
        path.arcTo(body_rect.right() - 2*radius, body_rect.top(), 2*radius, 2*radius, 90, -90)
        
        path.lineTo(body_rect.right(), body_rect.bottom() - radius)
        path.arcTo(body_rect.right() - 2*radius, body_rect.bottom() - 2*radius, 2*radius, 2*radius, 0, -90)
        
        # 하단 중앙 꼬리 부분 그리기
        center_x = body_rect.center().x()
        path.lineTo(center_x + tail_width/2, body_rect.bottom())
        path.lineTo(center_x, body_rect.bottom() + tail_height) 
        path.lineTo(center_x - tail_width/2, body_rect.bottom())
        
        # 왼쪽 하단 및 측면 마무리
        path.lineTo(body_rect.left() + radius, body_rect.bottom())
        path.arcTo(body_rect.left(), body_rect.bottom() - 2*radius, 2*radius, 2*radius, -90, -90)
        
        path.lineTo(body_rect.left(), body_rect.top() + radius)
        path.arcTo(body_rect.left(), body_rect.top(), 2*radius, 2*radius, 180, -90)
        
        path.closeSubpath()
        
        # 말풍선 내부 채우기 (약간의 투명도 포함)
        painter.fillPath(path, self._bg_color)

        # 테두리 그리기
        pen = QPen(self._border_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawPath(path)

# ── 리사이즈 상수 ──────────────────────────────────────────────────
RESIZE_MARGIN = 20
DIR_NONE   = 0
DIR_LEFT   = 1
DIR_RIGHT  = 2
DIR_TOP    = 4
DIR_BOTTOM = 8

RESIZE_CURSOR_MAP = {
    DIR_NONE                : Qt.CursorShape.ArrowCursor,
    DIR_LEFT                : Qt.CursorShape.SizeHorCursor,
    DIR_RIGHT               : Qt.CursorShape.SizeHorCursor,
    DIR_TOP                 : Qt.CursorShape.SizeVerCursor,
    DIR_BOTTOM              : Qt.CursorShape.SizeVerCursor,
    DIR_LEFT  | DIR_TOP    : Qt.CursorShape.SizeFDiagCursor,
    DIR_RIGHT | DIR_BOTTOM : Qt.CursorShape.SizeFDiagCursor,
    DIR_RIGHT | DIR_TOP    : Qt.CursorShape.SizeBDiagCursor,
    DIR_LEFT  | DIR_BOTTOM : Qt.CursorShape.SizeBDiagCursor,
}

def get_bubble_corners(container, window_geometry):
    """말풍선의 상하좌우 꼭짓점(코너) 위치를 ChatWindow 로컬 좌표로 반환합니다."""
    container_pos = container.pos()
    rect = container.rect()
    tail_height = 15
    radius = 15
    body_width = rect.width() - 2
    body_height = rect.height() - tail_height - 2
    
    top_left = QPoint(container_pos.x() + 1 + radius, container_pos.y() + 1)
    top_right = QPoint(container_pos.x() + 1 + body_width - radius, container_pos.y() + 1)
    bottom_left = QPoint(container_pos.x() + 1 + radius, container_pos.y() + 1 + body_height)
    bottom_right = QPoint(container_pos.x() + 1 + body_width - radius, container_pos.y() + 1 + body_height)
    
    return top_left, top_right, bottom_left, bottom_right

def get_resize_dir(window, cursor_global: QPoint) -> int:
    """커서 위치가 말풍선의 꼭짓점 근처인지 확인하고 리사이즈 방향을 반환합니다."""
    cursor_local = window.mapFromGlobal(cursor_global)
    corners = get_bubble_corners(window.container, window.geometry())
    m = RESIZE_MARGIN
    
    corner_dirs = [
        DIR_LEFT | DIR_TOP,
        DIR_RIGHT | DIR_TOP,
        DIR_LEFT | DIR_BOTTOM,
        DIR_RIGHT | DIR_BOTTOM
    ]
    
    for corner, d in zip(corners, corner_dirs):
        if (corner - cursor_local).manhattanLength() <= m:
            return d
    
    return DIR_NONE

def sync_pet_with_bubble(window, pet_window):
    """말풍선 하단 중앙(꼬리 부분)에 펫이 오도록 위치를 조정합니다."""
    if not pet_window:
        return

    geom = window.geometry()
    center_x = geom.x() + (geom.width() // 2)
    pet_new_x = center_x - (pet_window.width() // 2)
    pet_new_y = geom.y() + geom.height() - 35
    
    pet_window.move(pet_new_x, pet_new_y)

def fit_bubble_size(bubble: QTextBrowser, scroll_area_viewport, max_height: int = None):
    """말풍선 너비를 내용에 맞추되 최대 70%, 높이도 내용에 맞추되 최대 max_height."""
    if max_height is None:
        max_height = BUBBLE_MAX_HEIGHT
    
    # 최대 너비 = 채팅 스크롤 영역 폭의 75%
    scroll_w = scroll_area_viewport.width()
    if scroll_w < 50:
        scroll_w = scroll_area_viewport.parent().width() - 20
    max_w = max(int(scroll_w * 0.75), 200)

    # === 동적 이미지 크기 조절 ===
    doc = bubble.document()
    ORIG_W_PROP = QTextFormat.UserProperty + 1
    ORIG_H_PROP = QTextFormat.UserProperty + 2

    block = doc.begin()
    while block.isValid():
        iterator = block.begin()
        while not iterator.atEnd():
            fragment = iterator.fragment()
            if fragment.isValid():
                fmt = fragment.charFormat()
                if fmt.isImageFormat():
                    img_fmt = fmt.toImageFormat()
                    img_name = img_fmt.name()
                    
                    orig_w = img_fmt.property(ORIG_W_PROP)
                    orig_h = img_fmt.property(ORIG_H_PROP)
                    
                    if orig_w is None or orig_h is None:
                        orig_w = 0
                        orig_h = 0
                        
                        img_resource = doc.resource(QTextDocument.ImageResource, QUrl(img_name))
                        if img_resource is not None:
                            if hasattr(img_resource, 'width') and hasattr(img_resource, 'height'):
                                orig_w = img_resource.width()
                                orig_h = img_resource.height()
                        
                        if (orig_w == 0 or orig_h == 0) and img_name.startswith("data:image"):
                            try:
                                base64_data = img_name.split(",", 1)[1]
                                temp_img = QImage()
                                temp_img.loadFromData(QByteArray.fromBase64(base64_data.encode()))
                                orig_w = temp_img.width()
                                orig_h = temp_img.height()
                            except Exception:
                                pass
                                
                        if orig_w > 0 and orig_h > 0:
                            img_fmt.setProperty(ORIG_W_PROP, orig_w)
                            img_fmt.setProperty(ORIG_H_PROP, orig_h)
                            
                    if orig_w and orig_h and orig_w > 0 and orig_h > 0:
                        target_w = max_w - 40
                        if orig_w > target_w:
                            new_w = target_w
                            new_h = int(orig_h * (new_w / orig_w))
                            img_fmt.setWidth(new_w)
                            img_fmt.setHeight(new_h)
                        else:
                            img_fmt.setWidth(orig_w)
                            img_fmt.setHeight(orig_h)
                            
                        cur = QTextCursor(doc)
                        cur.setPosition(fragment.position())
                        cur.setPosition(fragment.position() + fragment.length(), QTextCursor.KeepAnchor)
                        cur.setCharFormat(img_fmt)
            iterator += 1
        block = block.next()
    # ====================================

    # 문서의 이상적인 너비 계산 (내용에 맞는 최소 너비)
    bubble.document().setTextWidth(-1)  # 제한 없이 자연 너비 계산
    ideal_w = int(bubble.document().idealWidth()) + 30  # 여백 보정 넉넉히

    bubble_frame = bubble.property("bubble_frame")
    if bubble_frame:
        tw = bubble.property("thinking_widget")
        if tw:
            if tw.is_expanded():
                ideal_w = max_w  # 사고과정 보기 시 로그/코드가 많으므로 최대 너비 부여
            else:
                ideal_w = max(ideal_w, 220) # 사고과정 토글 버튼의 기본 너비 보장

    # 너비 결정: min(ideal, max_w), 최소 60px
    final_w = max(min(ideal_w, max_w), 60)
    
    if bubble_frame:
        # 겉 컨테이너(bubble_frame)를 고정시키고 내부(bubble)는 꽉 차도록 확장 허용
        bubble_frame.setFixedWidth(final_w)
        bubble.setMinimumWidth(10)
        bubble.setMaximumWidth(final_w)
        tw = bubble.property("thinking_widget")
        if tw:
            tw.force_update_height(final_w)
    else:
        bubble.setFixedWidth(final_w)

    # 높이 계산: 결정된 너비로 문서 재배치 후 높이 측정
    # 내부 padding(좌우 각 12px)을 제외한 실제 텍스트 영역에 맞게 텍스트 너비를 세팅해야 조기 줄바꿈을 막을 수 있음
    bubble.document().setTextWidth(final_w - 24)
    doc_height = int(bubble.document().size().height())
    
    # QTextBrowser 내부에 padding: 10px 12px; 가 적용되어 있으므로
    # 위아래 여백 총 20px을 높이에 더해주어야 내용물이 잘리지 않고 불필요한 스크롤바가 안 생깁니다.
    # 안전 여백으로 2px 추가
    needed_height = doc_height + 22

    if needed_height > max_height:
        bubble.setFixedHeight(max_height)
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
    else:
        bubble.setFixedHeight(max(needed_height, 30))
        bubble.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

def render_thinking_html(answer_html_content: str, thinking_html_content: str, expanded: bool) -> str:
    """[DEPRECATED] ThinkingWidget 도입으로 대체 예정. 하위 호환성 유지용."""
    combined = thinking_html_content + "<br>" + answer_html_content if thinking_html_content else answer_html_content
    return combined


class ThinkingWidget(QWidget):
    """사고 과정 접기/폴기 토글을 제공하는 Qt 네이티브 위젯.
    HTML 테이블 구조 대신 QPushButton과 QTextBrowser를 VBox으로 조립합니다.
    """
    toggled = Signal()

    def __init__(self, thinking_html: str, parent=None):
        super().__init__(parent)
        self._thinking_html = thinking_html
        self._expanded = False
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._toggle_btn = QPushButton("\U0001f9e0  사고 과정 보기  ▶")
        self._toggle_btn.setCursor(Qt.PointingHandCursor)
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #DCF0FD;
                color: #1A4F9A;
                border: none;
                border-bottom: 1px solid #B8D5E8;
                font-size: 11px;
                font-weight: bold;
                padding: 7px 12px;
                text-align: left;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QPushButton:hover { background-color: #C8E4F7; }
        """)
        self._toggle_btn.clicked.connect(self._on_toggle)
        layout.addWidget(self._toggle_btn)

        self._content_browser = QTextBrowser()
        self._content_browser.setOpenExternalLinks(False)
        self._content_browser.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._content_browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._content_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #D4EBFA;
                border: none;
                border-bottom: 1px solid #B8D5E8;
                color: #1E3A6E;
                font-size: 11.5px;
                padding: 8px 12px;
            }
            QScrollBar:vertical {
                border: none;
                width: 6px;
                background: #D4EBFA;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(30, 58, 110, 0.3);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(30, 58, 110, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                border: none;
                background: #D4EBFA;
            }
        """)
        self._content_browser.document().setDefaultStyleSheet(
            "body { font-family: 'Courier New', monospace; font-size: 11.5px; color: #1E3A6E; }"
        )
        self._content_browser.setHtml(thinking_html)
        self._content_browser.setFixedHeight(0)
        self._content_browser.hide()
        layout.addWidget(self._content_browser)

    def force_update_height(self, width: int):
        if self._expanded and width > 24:
            self._content_browser.document().setTextWidth(width - 24)
            self._content_browser.document().adjustSize()
            doc_h = int(self._content_browser.document().size().height())
            self._content_browser.setFixedHeight(min(doc_h + 12, 300))

    def _on_toggle(self):
        self._expanded = not self._expanded
        if self._expanded:
            self._toggle_btn.setText("\U0001f9e0  사고 과정 닫기  ▼")
            self._content_browser.show()
            self.force_update_height(self.width())
        else:
            self._toggle_btn.setText("\U0001f9e0  사고 과정 보기  ▶")
            self._content_browser.hide()
            self._content_browser.setFixedHeight(0)
        self.toggled.emit()

    def update_thinking(self, thinking_html: str):
        self._thinking_html = thinking_html
        
        vbar = self._content_browser.verticalScrollBar()
        is_at_bottom = vbar.value() >= vbar.maximum() - 5
        saved_value = vbar.value()
        
        self._content_browser.setHtml(thinking_html)
        
        if self._expanded:
            self.force_update_height(self.width())
            
            def restore_scroll():
                if is_at_bottom:
                    vbar.setValue(vbar.maximum())
                else:
                    vbar.setValue(saved_value)
                
            QTimer.singleShot(0, restore_scroll)

    def is_expanded(self) -> bool:
        return self._expanded

    def set_expanded(self, expanded: bool):
        if expanded != self._expanded:
            self._on_toggle()

    def make_transparent(self):
        """QFrame 래퍼와 통합될 때 호출. bubble_frame 배경과 어울리는 단색 스타일로 전환합니다."""
        self._toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #E4EEF8;
                color: #1A4F9A;
                border: none;
                border-bottom: 1px solid #C5D8ED;
                font-size: 11px;
                font-weight: bold;
                padding: 7px 12px;
                text-align: left;
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
                border-bottom-left-radius: 0px;
                border-bottom-right-radius: 0px;
            }
            QPushButton:hover { background-color: #D5E6F5; }
        """)
        self._content_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #D8EBF8;
                border: none;
                border-bottom: 1px solid #C5D8ED;
                color: #0F3A7A;
                font-size: 11.5px;
                padding: 8px 12px;
            }
            QScrollBar:vertical {
                border: none;
                width: 6px;
                background: #D8EBF8;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background: rgba(26, 79, 154, 0.3);
                min-height: 20px;
                border-radius: 3px;
            }
            QScrollBar::handle:vertical:hover {
                background: rgba(26, 79, 154, 0.5);
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                border: none;
                background: #D8EBF8;
            }
        """)


def apply_markdown_css(browser: QTextBrowser):
    """QTextBrowser의 기본 스타일시트에 MARKDOWN_CSS를 주입합니다."""
    browser.document().setDefaultStyleSheet(MARKDOWN_CSS)

def scroll_to_bottom(scroll_area):
    QTimer.singleShot(50, lambda: scroll_area.verticalScrollBar().setValue(
        scroll_area.verticalScrollBar().maximum()
    ))
