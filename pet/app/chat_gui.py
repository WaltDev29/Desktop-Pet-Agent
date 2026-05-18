from PySide6.QtWidgets import QFrame, QWidget, QTextEdit, QLabel, QPushButton, QHBoxLayout, QTextBrowser
from PySide6.QtCore import Qt, Signal, QPoint, QRectF, QTimer, QUrl
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap, QCursor, QDesktopServices

from app.chat_style import (
    IMAGE_REMOVE_BTN_STYLE,
    FONT_FAMILY,
    PET_MSG_FORMAT,
    THINKING_LINK_EXPANDED,
    THINKING_LINK_COLLAPSED,
    THINKING_CONTENT_DIV,
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
            self.thumb.setText("❌")
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
        painter.fillPath(path, QColor(255, 255, 255, 245))

        # 테두리 그리기
        pen = QPen(QColor("#e0e0e0"))
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
    
    # 최대 너비 = 채팅 스크롤 영역 폭의 70%
    scroll_w = scroll_area_viewport.width()
    if scroll_w < 50:
        scroll_w = scroll_area_viewport.parent().width() - 20
    max_w = max(int(scroll_w * 0.7), 100)

    # 문서의 이상적인 너비 계산 (내용에 맞는 최소 너비)
    bubble.document().setTextWidth(-1)  # 제한 없이 자연 너비 계산
    ideal_w = int(bubble.document().idealWidth()) + 20  # 여백 보정

    # 너비 결정: min(ideal, max_w), 최소 60px
    final_w = max(min(ideal_w, max_w), 60)
    bubble.setFixedWidth(final_w)

    # 높이 계산: 결정된 너비로 문서 재배치 후 높이 측정
    bubble.document().setTextWidth(final_w)
    doc_height = int(bubble.document().size().height())
    if doc_height > max_height:
        bubble.setFixedHeight(max_height)
    else:
        bubble.setFixedHeight(max(doc_height, 30))

def render_thinking_html(answer_html_content: str, thinking_html_content: str, expanded: bool) -> str:
    """사고 과정 토글 + 최종 답변을 하나의 말풍선 HTML로 조합합니다."""
    link = THINKING_LINK_EXPANDED if expanded else THINKING_LINK_COLLAPSED
    thinking_section = THINKING_CONTENT_DIV.format(content=thinking_html_content) if expanded else ""
    combined_text = f"{link}{thinking_section}{answer_html_content}"
    return PET_MSG_FORMAT.format(text=combined_text)

def scroll_to_bottom(scroll_area):
    QTimer.singleShot(50, lambda: scroll_area.verticalScrollBar().setValue(
        scroll_area.verticalScrollBar().maximum()
    ))
