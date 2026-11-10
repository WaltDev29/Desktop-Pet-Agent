"""앱 테마에 맞춘 알림/확인 다이얼로그 (QMessageBox 대체).

별도 아이콘 파일 없이 색상 원 + 글리프로 종류를 표시합니다.
사용법은 QMessageBox 정적 메서드와 동일합니다.
    show_info(parent, title, text)
    show_warning(parent, title, text)
    show_error(parent, title, text)
    ask_yes_no(parent, title, text) -> bool
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QGraphicsDropShadowEffect,
)
from PySide6.QtGui import QColor

_FONT = "'Pretendard', 'Malgun Gothic', '맑은 고딕'"

# kind -> (글리프, 색상)
_KINDS = {
    "info": ("i", "#3498DB"),
    "warning": ("!", "#F0AD4E"),
    "error": ("×", "#D9534F"),
    "question": ("?", "#3498DB"),
}

_STYLE = f"""
QFrame#dlg_container {{
    background-color: #FFFFFF;
    border: 1px solid #D1D1D1;
    border-radius: 16px;
}}
QLabel#dlg_title {{
    color: #222222; font-size: 15px; font-weight: bold; font-family: {_FONT};
}}
QLabel#dlg_text {{
    color: #444444; font-size: 13px; font-family: {_FONT};
}}
QPushButton {{
    border-radius: 10px; padding: 7px 22px; font-size: 13px;
    font-family: {_FONT}; min-width: 60px;
}}
QPushButton#dlg_primary {{ background-color: #3498DB; color: white; border: none; }}
QPushButton#dlg_primary:hover {{ background-color: #2e86c1; }}
QPushButton#dlg_danger {{ background-color: #D9534F; color: white; border: none; }}
QPushButton#dlg_danger:hover {{ background-color: #c9302c; }}
QPushButton#dlg_secondary {{
    background-color: #F1F1F1; color: #444444; border: 1px solid #D1D1D1;
}}
QPushButton#dlg_secondary:hover {{ background-color: #E6E6E6; }}
"""


class StyledMessageDialog(QDialog):
    def __init__(self, parent, kind: str, title: str, text: str, confirm: bool = False,
                 ok_text: str = "확인", cancel_text: str = "취소", danger: bool = False):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setModal(True)
        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self.setStyleSheet(_STYLE)
        self._drag_pos = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)  # 그림자 여백

        container = QFrame()
        container.setObjectName("dlg_container")
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 70))
        container.setGraphicsEffect(shadow)
        outer.addWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(22, 20, 22, 18)
        root.setSpacing(16)

        glyph, color = _KINDS.get(kind, _KINDS["info"])
        head = QHBoxLayout()
        head.setSpacing(12)
        badge = QLabel(glyph)
        badge.setFixedSize(30, 30)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(
            f"background-color: {color}; color: white; border-radius: 15px;"
            f"font-size: 16px; font-weight: bold; font-family: {_FONT};"
        )
        title_label = QLabel(title)
        title_label.setObjectName("dlg_title")
        head.addWidget(badge)
        head.addWidget(title_label, 1)
        root.addLayout(head)

        text_label = QLabel(text)
        text_label.setObjectName("dlg_text")
        text_label.setWordWrap(True)
        text_label.setTextInteractionFlags(Qt.NoTextInteraction)
        root.addWidget(text_label)

        btns = QHBoxLayout()
        btns.addStretch(1)
        if confirm:
            cancel = QPushButton(cancel_text)
            cancel.setObjectName("dlg_secondary")
            cancel.setCursor(Qt.PointingHandCursor)
            cancel.clicked.connect(self.reject)
            btns.addWidget(cancel)
        ok = QPushButton(ok_text)
        ok.setObjectName("dlg_danger" if danger else "dlg_primary")
        ok.setCursor(Qt.PointingHandCursor)
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        btns.addWidget(ok)
        root.addLayout(btns)

    # 프레임리스 창 드래그 이동
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos is not None and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None


def show_info(parent, title: str, text: str):
    StyledMessageDialog(parent, "info", title, text).exec()


def show_warning(parent, title: str, text: str):
    StyledMessageDialog(parent, "warning", title, text).exec()


def show_error(parent, title: str, text: str):
    StyledMessageDialog(parent, "error", title, text).exec()


def ask_yes_no(parent, title: str, text: str, ok_text: str = "예",
               cancel_text: str = "아니오", danger: bool = False) -> bool:
    dlg = StyledMessageDialog(parent, "question", title, text, confirm=True,
                              ok_text=ok_text, cancel_text=cancel_text, danger=danger)
    return dlg.exec() == QDialog.Accepted
