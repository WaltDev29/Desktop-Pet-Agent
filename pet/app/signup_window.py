import os
import re
import requests

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint, Signal, QThread, QByteArray, QSize
from PySide6.QtGui import QColor, QIcon, QPainter
from PySide6.QtSvg import QSvgRenderer

from app.chat_gui import BubbleFrame
from app.chat_style import (
    LOGIN_INPUT_STYLE, LOGIN_BTN_STYLE, LOGIN_ERROR_LABEL_STYLE, FONT_FAMILY
)

AGENT_BASE_URL = "http://localhost:8001"

_ICON_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "icon")


def _make_svg_icon(name: str, color: str, size: int = 18) -> QIcon:
    path = os.path.join(_ICON_DIR, f"{name}.svg")
    with open(path, "r", encoding="utf-8") as f:
        svg = f.read()
    svg = re.sub(r'fill="[^"]*"', f'fill="{color}"', svg)
    svg = re.sub(r'<path(?![^>]*fill=)', f'<path fill="{color}"', svg)
    ba = QByteArray(svg.encode("utf-8"))
    renderer = QSvgRenderer(ba)
    from PySide6.QtGui import QPixmap
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)


class SignupWorker(QThread):
    signup_result = Signal(bool, str)

    def __init__(self, email: str, password: str, name: str):
        super().__init__()
        self.email = email
        self.password = password
        self.name = name

    def run(self):
        try:
            response = requests.post(
                f"{AGENT_BASE_URL}/api/signup",
                json={"email": self.email, "password": self.password, "name": self.name},
                timeout=10
            )
            data = response.json()
            if data.get("status") == "success":
                self.signup_result.emit(True, data.get("message", ""))
            else:
                self.signup_result.emit(False, data.get("message", "회원가입에 실패했습니다."))
        except requests.exceptions.ConnectionError:
            self.signup_result.emit(False, "에이전트 서버에 연결할 수 없습니다.\n(localhost:8001 실행 여부를 확인하세요)")
        except requests.exceptions.Timeout:
            self.signup_result.emit(False, "서버 응답 시간이 초과되었습니다.")
        except Exception as e:
            self.signup_result.emit(False, f"오류가 발생했습니다: {e}")


class SignupWindow(QWidget):
    go_to_login = Signal(bool)

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
        x_btn = QPushButton()
        x_btn.setFixedSize(28, 28)
        x_btn.setIconSize(QSize(14, 14))
        x_btn.setIcon(_make_svg_icon("ic_x_1", "#AAAAAA", 14))
        x_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: rgba(220, 50, 50, 180);
            }
        """)
        x_btn.clicked.connect(self._close_app)
        top_bar.addStretch()
        top_bar.addWidget(x_btn)
        layout.addLayout(top_bar)

        layout.addSpacing(8)

        # 폼 수평 중앙 정렬
        form_widget = QWidget()
        form_widget.setFixedWidth(300)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(12)

        title = QLabel("회원가입")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"color: #E0E0E0; font-family: {FONT_FAMILY}; font-size: 18px; font-weight: bold;")
        form_layout.addWidget(title)
        
        info_label = QLabel("한 기기에 하나의 사용자만 회원 가입 가능합니다.")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 10px;")
        form_layout.addWidget(info_label)
        
        form_layout.addSpacing(10)

        name_label = QLabel("이름")
        name_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: bold;")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("이름을 입력하세요")
        self.name_input.setStyleSheet(LOGIN_INPUT_STYLE)
        self.name_input.returnPressed.connect(self._try_signup)

        email_label = QLabel("이메일")
        email_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: bold;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("이메일을 입력하세요")
        self.email_input.setStyleSheet(LOGIN_INPUT_STYLE)
        self.email_input.returnPressed.connect(self._try_signup)

        password_label = QLabel("비밀번호")
        password_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("비밀번호를 입력하세요 (6자 이상)")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(LOGIN_INPUT_STYLE)
        self.password_input.returnPressed.connect(self._try_signup)

        confirm_label = QLabel("비밀번호 확인")
        confirm_label.setStyleSheet(f"color: #AAAAAA; font-family: {FONT_FAMILY}; font-size: 12px; font-weight: bold;")
        self.confirm_input = QLineEdit()
        self.confirm_input.setPlaceholderText("비밀번호를 다시 입력하세요")
        self.confirm_input.setEchoMode(QLineEdit.Password)
        self.confirm_input.setStyleSheet(LOGIN_INPUT_STYLE)
        self.confirm_input.returnPressed.connect(self._try_signup)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet(LOGIN_ERROR_LABEL_STYLE)
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.signup_btn = QPushButton("회원가입")
        self.signup_btn.setStyleSheet(LOGIN_BTN_STYLE)
        self.signup_btn.clicked.connect(self._try_signup)

        # 로그인으로 돌아가기 링크
        login_link = QLabel('<a href="#" style="color:#5B9BD5; text-decoration:none;">이미 계정이 있으신가요? 로그인</a>')
        login_link.setAlignment(Qt.AlignCenter)
        login_link.setStyleSheet(f"font-family: {FONT_FAMILY}; font-size: 11px;")
        login_link.setOpenExternalLinks(False)
        login_link.linkActivated.connect(self._go_back_to_login)

        form_layout.addWidget(name_label)
        form_layout.addWidget(self.name_input)
        form_layout.addSpacing(4)
        form_layout.addWidget(email_label)
        form_layout.addWidget(self.email_input)
        form_layout.addSpacing(4)
        form_layout.addWidget(password_label)
        form_layout.addWidget(self.password_input)
        form_layout.addSpacing(4)
        form_layout.addWidget(confirm_label)
        form_layout.addWidget(self.confirm_input)
        form_layout.addWidget(self.error_label)
        form_layout.addSpacing(8)
        form_layout.addWidget(self.signup_btn)
        form_layout.addSpacing(6)
        form_layout.addWidget(login_link)

        form_wrapper = QHBoxLayout()
        form_wrapper.addStretch()
        form_wrapper.addWidget(form_widget)
        form_wrapper.addStretch()
        layout.addLayout(form_wrapper)

        layout.addSpacing(8)

        main_layout.addWidget(self.container)
        self.setMinimumSize(220, 300)
        self.setMouseTracking(True)
        self.container.setMouseTracking(True)
        self.adjustSize()

    def _close_app(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance().quit()
        os._exit(0)

    def _go_back_to_login(self):
        self.go_to_login.emit(False)
        self.close()

    def _validate(self) -> str | None:
        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm = self.confirm_input.text()

        if not name:
            return "이름을 입력해주세요."
        if not email:
            return "이메일을 입력해주세요."
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            return "올바른 이메일 형식을 입력해주세요."
        if not password:
            return "비밀번호를 입력해주세요."
        if len(password) < 6:
            return "비밀번호는 6자 이상이어야 합니다."
        if password != confirm:
            return "비밀번호가 일치하지 않습니다."
        return None

    def _try_signup(self):
        error = self._validate()
        if error:
            self.error_label.setText(error)
            self.error_label.show()
            self.adjustSize()
            return

        self.signup_btn.setEnabled(False)
        self.signup_btn.setText("가입 중...")
        self.error_label.hide()

        name = self.name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()

        self._worker = SignupWorker(email, password, name)
        self._worker.signup_result.connect(self._on_signup_result)
        self._worker.start()

    def _on_signup_result(self, success: bool, message: str):
        self.signup_btn.setEnabled(True)
        self.signup_btn.setText("회원가입")

        if success:
            self.go_to_login.emit(True)
            self.close()
        else:
            if "signup" in message.lower() or "device" in message.lower() or "exist" in message.lower() or "이미" in message:
                message = "한 기기에 하나의 사용자만 회원 가입 가능합니다."
            self.error_label.setText(message)
            self.error_label.show()
            self.adjustSize()
            self.password_input.clear()
            self.confirm_input.clear()
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
