from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor

from app.chat_gui import BubbleFrame
from app.chat_style import (
    OPACITY_SLIDER_STYLE, OPACITY_LABEL_STYLE, CLOSE_BTN_STYLE, SETTINGS_WINDOW_STYLE
)

class SettingsWindow(QWidget):
    def __init__(self, chat_window, pet_window=None):
        super().__init__(chat_window)
        self.chat_window = chat_window
        self.pet_window = pet_window
        
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        self.container = BubbleFrame(self)
        self.container.setObjectName("settings_container")
        self.container.setStyleSheet(SETTINGS_WINDOW_STYLE)
        
        # 드래그 처리
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
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(15)
        
        title = QLabel("설정")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        
        # 채팅창 투명도
        chat_opacity_label = QLabel("채팅창 투명도:")
        chat_opacity_label.setStyleSheet(OPACITY_LABEL_STYLE)
        self.chat_opacity_slider = QSlider(Qt.Horizontal)
        self.chat_opacity_slider.setRange(20, 100) # 최소 투명도 제한
        self.chat_opacity_slider.setValue(int(self.chat_window.windowOpacity() * 100))
        self.chat_opacity_slider.setStyleSheet(OPACITY_SLIDER_STYLE)
        self.chat_opacity_slider.valueChanged.connect(self.set_chat_opacity)
        
        # 펫 투명도
        pet_opacity_label = QLabel("펫 투명도:")
        pet_opacity_label.setStyleSheet(OPACITY_LABEL_STYLE)
        self.pet_opacity_slider = QSlider(Qt.Horizontal)
        self.pet_opacity_slider.setRange(20, 100)
        pet_val = int(self.pet_window.windowOpacity() * 100) if self.pet_window else 100
        self.pet_opacity_slider.setValue(pet_val)
        self.pet_opacity_slider.setStyleSheet(OPACITY_SLIDER_STYLE)
        self.pet_opacity_slider.valueChanged.connect(self.set_pet_opacity)
        
        close_btn = QPushButton("닫기")
        close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        close_btn.clicked.connect(self.close)
        
        layout.addWidget(title)
        layout.addWidget(chat_opacity_label)
        layout.addWidget(self.chat_opacity_slider)
        layout.addWidget(pet_opacity_label)
        layout.addWidget(self.pet_opacity_slider)
        layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
        
        main_layout.addWidget(self.container)
        
        self.resize(250, 300)
        
        # 채팅창 옆에 위치시키기
        geom = self.chat_window.geometry()
        self.move(geom.x() + geom.width() + 10, geom.y())

    def set_chat_opacity(self, value):
        opacity = value / 100.0
        self.chat_window.setWindowOpacity(opacity)

    def set_pet_opacity(self, value):
        if self.pet_window:
            opacity = value / 100.0
            self.pet_window.setWindowOpacity(opacity)

    def _on_drag_started(self, cursor_global: QPoint):
        self._drag_start_cursor_pos = cursor_global
        self._drag_start_window_pos = self.pos()

    def _on_drag_moved(self, cursor_global: QPoint):
        if self._drag_start_cursor_pos is None: return
        delta = cursor_global - self._drag_start_cursor_pos
        self.move(self._drag_start_window_pos + delta)

    def _on_drag_finished(self):
        self._drag_start_cursor_pos = None
        self._drag_start_window_pos = None
