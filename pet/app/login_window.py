import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, Signal
from PySide6.QtGui import QColor

from app.chat_gui import BubbleFrame
from app.chat_style import (
    LOGIN_INPUT_STYLE, LOGIN_BTN_STYLE, LOGIN_ERROR_LABEL_STYLE, FONT_FAMILY
)

VALID_EMAIL = "1234"
VALID_PASSWORD = "1234"


class LoginWindow(QWidget):
    login_success = Signal()

    def __init__(self, pet_window=None):
        super().__init__(pet_window)
        self.pet_window = pet_window

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.container = BubbleFrame(self)
        self.container.setObjectName("login_container")

        self.container.drag_started.connect(self._on_drag_started)
        self.container.drag_moved.connect(self._on_drag_moved)
        self.container.drag_finished.connect(self._on_drag_finished)
        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(15, 15, 15, 30)
        layout.setSpacing(0)

        # 상단: X 종료 버튼
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        x_btn = QPushButton("✕")
        x_btn.setFixedSize(28, 28)
        x_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #AAAAAA;
                border: none;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(220, 50, 50, 180);
                color: white;
            }
        """)
        x_btn.clicked.connect(self._close_login)
        top_bar.addStretch()
        top_bar.addWidget(x_btn)
        layout.addLayout(top_bar)

        # 수직 중앙 정렬 (위)
        layout.addSpacing(8)

        # 폼 수평 중앙 정렬
        form_widget = QWidget()
        form_widget.setFixedWidth(300)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        title = QLabel("로그인")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: #E0E0E0; font-family: {FONT_FAMILY}; font-size: 18px; font-weight: bold;")
        form_layout.addWidget(title)
        form_layout.addSpacing(10)

        email_label = QLabel("이메일")
        email_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: bold;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("이메일을 입력하세요")
        self.email_input.setStyleSheet(LOGIN_INPUT_STYLE)
        self.email_input.returnPressed.connect(self._try_login)

        password_label = QLabel("비밀번호")
        password_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("비밀번호를 입력하세요")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(LOGIN_INPUT_STYLE)
        self.password_input.returnPressed.connect(self._try_login)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(LOGIN_ERROR_LABEL_STYLE)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.hide()

        login_btn = QPushButton("로그인")
        login_btn.setStyleSheet(LOGIN_BTN_STYLE)
        login_btn.clicked.connect(self._try_login)

        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addSpacing(4)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.error_label)
        form_layout.addSpacing(8)
        form_layout.addWidget(login_btn)

        form_wrapper = QHBoxLayout()
        form_wrapper.addStretch()
        form_wrapper.addWidget(form_widget)
        form_wrapper.addStretch()
        layout.addLayout(form_wrapper)

        # 수직 중앙 정렬 (아래)
        layout.addSpacing(8)

        main_layout.addWidget(self.container)
        self.setMinimumSize(220, 300)
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        self.adjustSize()

    def _close_login(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
        os._exit(0)

    def _try_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if email == VALID_EMAIL and password == VALID_PASSWORD:
            self.error_label.hide()
            self.login_success.emit()
        else:
            self.error_label.setText("이메일 또는 비밀번호가 올바르지 않습니다.")
            self.error_label.show()
            self.password_input.clear()
            self.password_input.setFocus()

    def _on_drag_started(self, cursor_global: QPoint):
        self._drag_start_cursor_pos = cursor_global
        self._drag_start_window_pos = self.pos()

    def _on_drag_moved(self, cursor_global: QPoint):
        if self._drag_start_cursor_pos is None:
            return
        delta = cursor_global - self._drag_start_cursor_pos
        self.move(self._drag_start_window_pos + delta)

    def _on_drag_finished(self):
        self._drag_start_cursor_pos = None
        self._drag_start_window_pos = None
