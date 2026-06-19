import os
import requests

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGraphicsDropShadowEffect, QMessageBox
)
from PySide6.QtCore import Qt, QPoint, Signal, QThread
from PySide6.QtGui import QColor

from app.chat_gui import BubbleFrame
from app.chat_style import (
    LOGIN_INPUT_STYLE, LOGIN_BTN_STYLE, LOGIN_ERROR_LABEL_STYLE, FONT_FAMILY
)

AGENT_BASE_URL = "http://localhost:8001"


class LoginWorker(QThread):
    login_result = Signal(bool, str)

    def __init__(self, email: str, password: str):
        super().__init__()
        self.email = email
        self.password = password

    def run(self):
        try:
            response = requests.post(
                f"{AGENT_BASE_URL}/api/login",
                json={"email": self.email, "password": self.password},
                timeout=10
            )
            data = response.json()
            if data.get("status") == "success":
                self.login_result.emit(True, data.get("message", ""))
            else:
                self.login_result.emit(False, data.get("message", "로그인에 실패했습니다."))
        except requests.exceptions.ConnectionError:
            self.login_result.emit(False, "에이전트 서버에 연결할 수 없습니다.\n(localhost:8001 실행 여부를 확인하세요)")
        except requests.exceptions.Timeout:
            self.login_result.emit(False, "서버 응답 시간이 초과되었습니다.")
        except Exception as e:
            self.login_result.emit(False, f"오류가 발생했습니다: {e}")


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
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.login_btn = QPushButton("로그인")
        self.login_btn.setStyleSheet(LOGIN_BTN_STYLE)
        self.login_btn.clicked.connect(self._try_login)

        signup_link = QLabel('<a href="#" style="color:#5B9BD5; text-decoration:none;">계정이 없으신가요? 회원가입</a>')
        signup_link.setAlignment(Qt.AlignCenter)
        signup_link.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 11px;")
        signup_link.setOpenExternalLinks(False)
        signup_link.linkActivated.connect(self._open_signup)

        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addSpacing(4)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addWidget(self.error_label)
        form_layout.addSpacing(8)
        form_layout.addWidget(self.login_btn)
        form_layout.addSpacing(6)
        form_layout.addWidget(signup_link)

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

    def _open_signup(self):
        from app.signup_window import SignupWindow
        self._signup_window = SignupWindow(self.pet_window)
        if hasattr(self, 'pet_window') and self.pet_window:
            self.pet_window.signup_win = self._signup_window
            self._signup_window.adjustSize()
            pet = self.pet_window
            pet_center_x = pet.x() + (pet.width() // 2)
            signup_x = pet_center_x - (self._signup_window.width() // 2)
            signup_y = pet.y() - self._signup_window.height() - 15
            self._signup_window.move(signup_x, signup_y)
        else:
            self._signup_window.move(self.pos())
            
        self._signup_window.go_to_login.connect(self._on_signup_success)
        self._signup_window.show()
        self.hide()

    def _on_signup_success(self, success_status: bool = False):
        self.show()
        self.error_label.hide()
        if success_status:
            QMessageBox.information(self, "알림", "회원가입이 완료되었습니다!")

    def _try_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            self.error_label.setText("이메일과 비밀번호를 입력해주세요.")
            self.error_label.show()
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("로그인 중...")
        self.error_label.hide()

        self._worker = LoginWorker(email, password)
        self._worker.login_result.connect(self._on_login_result)
        self._worker.start()

    def _on_login_result(self, success: bool, message: str):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("로그인")

        if success:
            self.error_label.hide()
            self.login_success.emit()
        else:
            self.error_label.setText(message)
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
