from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QGraphicsDropShadowEffect, QFrame, QMessageBox
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor
from app.chat_style import (
    CLOSE_BTN_STYLE,
    get_settings_window_style,
    get_settings_label_style,
    get_settings_slider_style,
    DARK_THEME,
)
import requests

class SettingsWindow(QWidget):
    def __init__(self, chat_window, pet_window=None):
        super().__init__(chat_window)
        self.chat_window = chat_window
        self.pet_window = pet_window

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.container = QFrame(self)
        self.container.setObjectName("settings_container")
        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(15)

        self.title_label = QLabel("설정")
        self.title_label.setAlignment(Qt.AlignCenter)

        # 테마 선택
        self.theme_label = QLabel("채팅창 테마:")
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(8)

        self.dark_theme_btn = QPushButton("🌙 다크")
        self.light_theme_btn = QPushButton("☀️ 화이트")
        self.dark_theme_btn.clicked.connect(lambda: self._apply_theme("dark"))
        self.light_theme_btn.clicked.connect(lambda: self._apply_theme("light"))
        theme_btn_layout.addWidget(self.dark_theme_btn)
        theme_btn_layout.addWidget(self.light_theme_btn)

        # 채팅창 투명도
        self.chat_opacity_label = QLabel("채팅창 투명도:")
        self.chat_opacity_slider = QSlider(Qt.Horizontal)
        self.chat_opacity_slider.setRange(20, 100)
        self.chat_opacity_slider.setValue(int(self.chat_window.windowOpacity() * 100))
        self.chat_opacity_slider.valueChanged.connect(self.set_chat_opacity)

        # 펫 투명도
        self.pet_opacity_label = QLabel("펫 투명도:")
        self.pet_opacity_slider = QSlider(Qt.Horizontal)
        self.pet_opacity_slider.setRange(20, 100)
        pet_val = int(self.pet_window.windowOpacity() * 100) if self.pet_window else 100
        self.pet_opacity_slider.setValue(pet_val)
        self.pet_opacity_slider.valueChanged.connect(self.set_pet_opacity)

        self.close_btn = QPushButton("닫기")
        self.close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        self.close_btn.clicked.connect(self.close)

        layout.addWidget(self.title_label)
        layout.addWidget(self.theme_label)
        layout.addLayout(theme_btn_layout)
        layout.addWidget(self.chat_opacity_label)
        layout.addWidget(self.chat_opacity_slider)
        layout.addWidget(self.pet_opacity_label)
        layout.addWidget(self.pet_opacity_slider)
        
        # 로그아웃 버튼
        self.logout_btn = QPushButton("로그아웃")
        self.logout_btn.setStyleSheet("background-color: #D32F2F; color: white; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 8px 16px;")
        self.logout_btn.clicked.connect(self._handle_logout)
        layout.addWidget(self.logout_btn)
        
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        layout.addLayout(btn_layout)

        main_layout.addWidget(self.container)

        self.resize(260, 380)

        # 현재 채팅창 테마 적용
        current_theme = getattr(self.chat_window, "_current_theme", DARK_THEME)
        self.update_theme(current_theme)

        # 채팅창 옆에 위치시키기
        geom = self.chat_window.geometry()
        self.move(geom.x() + geom.width() + 10, geom.y())

    def update_theme(self, theme: dict):
        """채팅창 테마에 맞게 설정창 전체 UI를 업데이트합니다."""
        is_dark = theme["name"] == "dark"

        self.container.setStyleSheet(get_settings_window_style(theme))

        label_style = get_settings_label_style(theme)
        slider_style = get_settings_slider_style(theme)

        title_color = "#E0E0E0" if is_dark else "#1A1A1A"
        self.title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; margin-bottom: 10px; color: {title_color};"
        )

        self.theme_label.setStyleSheet(label_style)
        self.chat_opacity_label.setStyleSheet(label_style)
        self.pet_opacity_label.setStyleSheet(label_style)
        self.chat_opacity_slider.setStyleSheet(slider_style)
        self.pet_opacity_slider.setStyleSheet(slider_style)

        self._update_theme_buttons(theme)

    def _update_theme_buttons(self, theme: dict | None = None):
        if theme is None:
            theme = getattr(self.chat_window, "_current_theme", DARK_THEME)
        current = theme.get("name", "dark")
        is_dark = theme["name"] == "dark"

        _base = "border-radius: 8px; font-size: 12px; font-weight: bold; padding: 6px 14px;"
        active_style = f"background-color: #2979B0; color: white; {_base}"
        inactive_bg = "#3A3A3A" if is_dark else "#E0E0E0"
        inactive_color = "#CCCCCC" if is_dark else "#333333"
        inactive_style = f"background-color: {inactive_bg}; color: {inactive_color}; {_base}"

        self.dark_theme_btn.setStyleSheet(
            active_style if current == "dark" else inactive_style
        )
        self.light_theme_btn.setStyleSheet(
            active_style if current == "light" else inactive_style
        )

    def _apply_theme(self, theme_name: str):
        self.chat_window.apply_theme(theme_name)

    def set_chat_opacity(self, value):
        self.chat_window.setWindowOpacity(value / 100.0)

    def set_pet_opacity(self, value):
        if self.pet_window:
            self.pet_window.setWindowOpacity(value / 100.0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_cursor_pos = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_start_cursor_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_cursor_pos
            self.move(self._drag_start_window_pos + delta)

    def mouseReleaseEvent(self, event):
        self._drag_start_cursor_pos = None
        self._drag_start_window_pos = None

    def _handle_logout(self):
        try:
            response = requests.post("http://localhost:8001/api/logout", timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    QMessageBox.information(self, "로그아웃", "성공적으로 로그아웃 되었습니다.")
                    self.close()
                else:
                    QMessageBox.warning(self, "로그아웃 실패", data.get("message", "알 수 없는 오류가 발생했습니다."))
            else:
                QMessageBox.warning(self, "로그아웃 실패", f"서버 오류: {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "로그아웃 오류", f"로그아웃 요청 중 오류가 발생했습니다:\n{str(e)}")
