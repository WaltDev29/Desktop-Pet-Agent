import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QGraphicsDropShadowEffect, QFrame, QMessageBox, QDialog,
    QTextEdit, QDialogButtonBox, QCheckBox, QLineEdit, QTabWidget,
    QFileDialog
)
from PySide6.QtCore import Qt, QPoint, QRect
from PySide6.QtGui import QColor, QFont, QMovie, QPixmap, QPainter, QPen, QPainterPath
from app.chat_style import (
    CLOSE_BTN_STYLE,
    get_settings_window_style,
    get_settings_label_style,
    get_settings_slider_style,
    DARK_THEME,
)
import requests

from app.pet_style import PET_WIDTH, PET_HEIGHT

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "agent", "agent_server", "config.json"
)
ENV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "agent", ".env"
)
PET_SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "pet_settings.json"
)

def get_default_pet_path():
    candidate = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Assets", "bee", "bee_fly_2.gif"))
    if os.path.exists(candidate):
        return candidate
    return "Assets/bee/bee_fly_2.gif"

DEFAULT_PET_PATH = get_default_pet_path()


class PetPreviewWidget(QWidget):
    """
    펫 캐릭터 미리보기 위젯:
    - 바깥 영역 없는 단일 정사각형 캔버스 (220x220)
    - 선명하고 명확한 2px 테두리 및 중심 가이드 십자선
    - 실제 화면에 표시되는 크기(PET_WIDTH=90 기준)와 1:1로 일치하는 실제 크기 반영
    - 도트 화질 저하 방지 (SmoothPixmapTransform 비활성화로 선명한 픽셀 보존)
    - 좌우 반전 시각화 지원
    - 마우스 드래그를 통한 이미지 중심 위치(오프셋) 조절
    - 중앙 정렬 기능 지원
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(220, 220)
        self.setCursor(Qt.OpenHandCursor)
        self.movie = None
        self.pixmap = None
        self.current_path = ""
        self.scale_percent = 100
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.flip_h = False
        self._is_dragging = False
        self._drag_start_pos = None
        self._drag_start_offset = (0.0, 0.0)
        self.on_offset_changed = None
        self.is_dark = True

    def set_theme(self, is_dark: bool):
        self.is_dark = is_dark
        self.update()

    def set_flip_h(self, flip_h: bool):
        self.flip_h = flip_h
        self.update()

    def load_file(self, path: str, scale_percent: int = 100, offset_x: float = 0.0, offset_y: float = 0.0, flip_h: bool = False):
        self.current_path = path
        self.scale_percent = scale_percent
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.flip_h = flip_h

        if self.movie:
            try:
                self.movie.frameChanged.disconnect(self.update)
            except Exception:
                pass
            self.movie.stop()
            self.movie = None
        self.pixmap = None

        if path and os.path.exists(path):
            if path.lower().endswith(".gif"):
                self.movie = QMovie(path)
                self.movie.frameChanged.connect(self.update)
                self.movie.start()
            else:
                self.pixmap = QPixmap(path)
        self.update()

    def set_scale(self, scale_percent: int):
        self.scale_percent = scale_percent
        self.update()

    def set_offset(self, offset_x: float, offset_y: float):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.update()

    def reset_offset(self):
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._is_dragging = True
            self._drag_start_pos = event.pos()
            self._drag_start_offset = (self.offset_x, self.offset_y)
            self.setCursor(Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if self._is_dragging and self._drag_start_pos:
            delta = event.pos() - self._drag_start_pos
            # 좌우 반전 상태이면 마우스 이동 방향도 자연스럽게 맞춰줌
            dx = -delta.x() if self.flip_h else delta.x()
            dy = delta.y()
            self.offset_x = self._drag_start_offset[0] + dx
            self.offset_y = self._drag_start_offset[1] + dy
            self.update()
            if callable(self.on_offset_changed):
                self.on_offset_changed(self.offset_x, self.offset_y)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._is_dragging:
            self._is_dragging = False
            self.setCursor(Qt.OpenHandCursor)

    def paintEvent(self, event):
        painter = QPainter(self)

        # 1. 배경 & 선명한 테두리 (안티앨리어싱 활성화)
        painter.setRenderHint(QPainter.Antialiasing, True)
        bg_color = QColor("#16191F") if self.is_dark else QColor("#F4F6F9")
        border_color = QColor("#4A90E2") if self.is_dark else QColor("#2979B0")

        path = QPainterPath()
        path.addRoundedRect(1, 1, self.width() - 2, self.height() - 2, 10, 10)

        painter.fillPath(path, bg_color)
        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.drawPath(path)

        # 2. 중심 십자 가이드선 및 실제 펫 크기 영역 가이드 박스
        center_x = self.width() / 2.0
        center_y = self.height() / 2.0
        guide_color = QColor(255, 255, 255, 45) if self.is_dark else QColor(0, 0, 0, 35)
        guide_pen = QPen(guide_color, 1, Qt.DashLine)
        painter.setPen(guide_pen)
        painter.drawLine(int(center_x), 8, int(center_x), self.height() - 8)
        painter.drawLine(8, int(center_y), self.width() - 8, int(center_y))

        # 실제 화면에 표시되는 펫 윈도우 크기 (PET_WIDTH * scale)
        actual_box_w = PET_WIDTH * (self.scale_percent / 100.0)
        actual_box_h = PET_HEIGHT * (self.scale_percent / 100.0)
        box_guide_color = QColor(74, 144, 226, 60) if self.is_dark else QColor(41, 121, 176, 50)
        painter.setPen(QPen(box_guide_color, 1, Qt.DotLine))
        box_x = int(center_x - actual_box_w / 2.0)
        box_y = int(center_y - actual_box_h / 2.0)
        painter.drawRect(QRect(box_x, box_y, int(actual_box_w), int(actual_box_h)))

        # 3. 이미지 / GIF 그리기 (정사각형 영역 내부로 클리핑)
        painter.setClipPath(path)

        # 도트 / 픽셀 아트의 화질이 뭉개지지 않고 선명하도록 안티앨리어싱 해제
        painter.setRenderHint(QPainter.Antialiasing, False)

        pix = None
        if self.movie:
            pix = self.movie.currentPixmap()
        elif self.pixmap and not self.pixmap.isNull():
            pix = self.pixmap

        if pix and not pix.isNull():
            pw = pix.width()
            ph = pix.height()
            if pw > 0 and ph > 0:
                # 실제 화면(PetWindow)과 정확히 1:1로 일치하는 실제 픽셀 크기 계산!
                ratio = min(actual_box_w / pw, actual_box_h / ph)
                target_w = max(1, int(pw * ratio))
                target_h = max(1, int(ph * ratio))

                painter.save()
                if self.flip_h:
                    painter.scale(-1, 1)
                    painter.translate(-self.width(), 0)

                draw_x = int(center_x - target_w / 2.0 + self.offset_x)
                draw_y = int(center_y - target_h / 2.0 + self.offset_y)

                painter.drawPixmap(QRect(draw_x, draw_y, target_w, target_h), pix)
                painter.restore()
        else:
            empty_text = "이미지 없음"
            text_color = QColor("#888888") if self.is_dark else QColor("#999999")
            painter.setPen(QPen(text_color))
            painter.drawText(self.rect(), Qt.AlignCenter, empty_text)

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
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        self.title_label = QLabel("설정")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        # 펫 설정 캐시 변수
        self.current_pet_path = DEFAULT_PET_PATH
        self.current_pet_scale = 100
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        self.current_flip_h = False
        self._saved_pet_path = DEFAULT_PET_PATH
        self._saved_pet_scale = 100
        self._saved_offset_x = 0.0
        self._saved_offset_y = 0.0
        self._saved_flip_h = False
        self._pet_dirty = False
        self._pet_preview_movie = None
        self._load_pet_settings()

        # 모델 설정 캐시 변수
        self.local_model = ""
        self.local_base_url = ""
        self.local_api_key = ""
        self.openai_model = ""
        self.openai_api_key = ""
        self.is_local = False

        # 상단 탭 위젯 (Pet, UI, 모델, MCP)
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._init_pet_tab(), "Pet")
        self.tab_widget.addTab(self._init_ui_tab(), "UI")
        self.tab_widget.addTab(self._init_model_tab(), "모델")
        self.tab_widget.addTab(self._init_mcp_tab(), "MCP")
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        layout.addWidget(self.tab_widget, 1)

        # 하단 버튼 영역: [상태 레이블]  --- stretch ---  [저장(변경 시만 노출)] [닫기(우측)]
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.setSpacing(10)

        self.footer_status_label = QLabel("")
        self.footer_status_label.setStyleSheet("font-size: 11px; padding: 2px 4px;")
        btn_layout.addWidget(self.footer_status_label)

        btn_layout.addStretch()

        self.common_save_btn = QPushButton("저장")
        self.common_save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2979B0;
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 7px 22px;
            }
            QPushButton:hover { background-color: #1A5F8F; }
        """)
        self.common_save_btn.clicked.connect(self._on_common_save_clicked)
        self.common_save_btn.setVisible(False)
        btn_layout.addWidget(self.common_save_btn)

        self.close_btn = QPushButton("닫기")
        self.close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        self.close_btn.clicked.connect(self.close)
        btn_layout.addWidget(self.close_btn)

        layout.addLayout(btn_layout)

        main_layout.addWidget(self.container)

        self.resize(500, 570)

        # 더티 상태 및 저장값 추적
        self._saved_model_state = {}
        self._saved_mcp_text = ""
        self._model_dirty = False
        self._mcp_dirty = False

        current_theme = getattr(self.chat_window, "_current_theme", DARK_THEME)
        self.update_theme(current_theme)

        geom = self.chat_window.geometry()
        self.move(geom.x() + geom.width() + 10, geom.y())

    def showEvent(self, event):
        super().showEvent(event)
        self.footer_status_label.setText("")
        self._load_pet_settings()
        self._load_model_settings()
        self._load_mcp_settings()
        self._on_tab_changed(self.tab_widget.currentIndex())

    # ==========================
    # 0. Pet 탭
    # ==========================
    def _init_pet_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(14, 8, 14, 8)
        l.setSpacing(8)

        # 1. 파일 선택 및 초기화 버튼 행
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self.pet_choose_btn = QPushButton("📁 Image / GIF 불러오기")
        self.pet_choose_btn.setCursor(Qt.PointingHandCursor)
        self.pet_choose_btn.clicked.connect(self._choose_pet_file)
        btn_row.addWidget(self.pet_choose_btn, 1)

        self.pet_reset_btn = QPushButton("기본값 복원")
        self.pet_reset_btn.setCursor(Qt.PointingHandCursor)
        self.pet_reset_btn.clicked.connect(self._reset_to_default_pet)
        btn_row.addWidget(self.pet_reset_btn)

        l.addLayout(btn_row)

        # 2. 이미지/GIF 단일 정사각형 미리보기 영역 (실제 화면 90px 기준 1:1 실시간 렌더링, 220x220)
        preview_container = QHBoxLayout()
        preview_container.setAlignment(Qt.AlignCenter)

        self.pet_preview_widget = PetPreviewWidget(self)
        self.pet_preview_widget.on_offset_changed = self._on_preview_offset_changed
        preview_container.addWidget(self.pet_preview_widget)
        l.addLayout(preview_container)

        # 위치 조절 가이드, 중앙 정렬 버튼, 좌우 반전 버튼 행
        pos_ctrl_row = QHBoxLayout()
        pos_ctrl_row.setSpacing(8)

        self.pet_guide_label = QLabel("💡 드래그하여 위치 조절")
        self.pet_guide_label.setStyleSheet("font-size: 11px;")
        pos_ctrl_row.addWidget(self.pet_guide_label)

        pos_ctrl_row.addStretch()

        self.pet_center_btn = QPushButton("🎯 중앙 정렬")
        self.pet_center_btn.setCursor(Qt.PointingHandCursor)
        self.pet_center_btn.clicked.connect(self._center_pet_image)
        pos_ctrl_row.addWidget(self.pet_center_btn)

        self.pet_flip_btn = QPushButton("↔ 좌우 반전")
        self.pet_flip_btn.setCursor(Qt.PointingHandCursor)
        self.pet_flip_btn.clicked.connect(self._toggle_flip_h)
        pos_ctrl_row.addWidget(self.pet_flip_btn)

        l.addLayout(pos_ctrl_row)

        # 파일 경로 표시 라벨
        self.pet_path_label = QLabel("")
        self.pet_path_label.setAlignment(Qt.AlignCenter)
        self.pet_path_label.setStyleSheet("font-size: 11px;")
        l.addWidget(self.pet_path_label)

        # 3. 크기 조절 (30% ~ 300%까지 확장)
        scale_header = QHBoxLayout()
        self.pet_scale_title = QLabel("크기 조절:")
        self.pet_scale_value_label = QLabel(f"{self.current_pet_scale}%")
        self.pet_scale_value_label.setStyleSheet("font-weight: bold;")
        scale_header.addWidget(self.pet_scale_title)
        scale_header.addStretch()
        scale_header.addWidget(self.pet_scale_value_label)
        l.addLayout(scale_header)

        self.pet_scale_slider = QSlider(Qt.Horizontal)
        self.pet_scale_slider.setRange(30, 300)
        self.pet_scale_slider.setSingleStep(5)
        self.pet_scale_slider.setValue(self.current_pet_scale)
        self.pet_scale_slider.valueChanged.connect(self._on_scale_slider_changed)
        l.addWidget(self.pet_scale_slider)

        l.addStretch()

        self._update_flip_btn_style()
        self._update_pet_preview()
        return w

    def _on_preview_offset_changed(self, offset_x: float, offset_y: float):
        self.current_offset_x = offset_x
        self.current_offset_y = offset_y
        if self.pet_window:
            self.pet_window.set_offset(offset_x, offset_y)
        self._check_pet_dirty()

    def _center_pet_image(self):
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        if hasattr(self, "pet_preview_widget"):
            self.pet_preview_widget.reset_offset()
        if self.pet_window:
            self.pet_window.set_offset(0.0, 0.0)
        self._check_pet_dirty()

    def _toggle_flip_h(self):
        self.current_flip_h = not self.current_flip_h
        if hasattr(self, "pet_preview_widget"):
            self.pet_preview_widget.set_flip_h(self.current_flip_h)
        if self.pet_window:
            self.pet_window.set_base_flip(self.current_flip_h)
        self._update_flip_btn_style()
        self._check_pet_dirty()

    def _update_flip_btn_style(self):
        if not hasattr(self, "pet_flip_btn"):
            return
        is_dark = getattr(self.chat_window, "_current_theme", DARK_THEME).get("name", "dark") == "dark"
        if self.current_flip_h:
            self.pet_flip_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2979B0;
                    color: white;
                    border: 1px solid #3498DB;
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 5px 12px;
                }
                QPushButton:hover {
                    background-color: #1A5F8F;
                }
            """)
        else:
            center_bg = "#2C3E50" if is_dark else "#E8EEF5"
            center_color = "#64B5F6" if is_dark else "#1976D2"
            center_hover = "#34495E" if is_dark else "#D5E2F0"
            border_c = "#3D566E" if is_dark else "#B8D2EC"
            self.pet_flip_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {center_bg};
                    color: {center_color};
                    border: 1px solid {border_c};
                    border-radius: 6px;
                    font-size: 11px;
                    font-weight: bold;
                    padding: 5px 12px;
                }}
                QPushButton:hover {{
                    background-color: {center_hover};
                }}
            """)

    def _choose_pet_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "캐릭터 이미지 또는 GIF 선택",
            "",
            "Image / GIF (*.gif *.png *.jpg *.jpeg *.webp *.bmp);;모든 파일 (*)"
        )
        if file_path:
            self.current_pet_path = os.path.normpath(file_path)
            self._update_pet_preview()
            self._check_pet_dirty()

    def _reset_to_default_pet(self):
        self.current_pet_path = DEFAULT_PET_PATH
        self.current_pet_scale = 100
        self.current_offset_x = 0.0
        self.current_offset_y = 0.0
        self.current_flip_h = False
        self.pet_scale_slider.blockSignals(True)
        self.pet_scale_slider.setValue(100)
        self.pet_scale_slider.blockSignals(False)
        self.pet_scale_value_label.setText("100%")
        if hasattr(self, "pet_preview_widget"):
            self.pet_preview_widget.reset_offset()
            self.pet_preview_widget.set_scale(100)
            self.pet_preview_widget.set_flip_h(False)
        self._update_flip_btn_style()
        self._update_pet_preview()
        if self.pet_window:
            self.pet_window.apply_character(DEFAULT_PET_PATH, 100, 0.0, 0.0, False)
        self._check_pet_dirty()

    def _on_scale_slider_changed(self, value: int):
        self.current_pet_scale = value
        self.pet_scale_value_label.setText(f"{value}%")
        if hasattr(self, "pet_preview_widget"):
            self.pet_preview_widget.set_scale(value)
        if self.pet_window:
            self.pet_window.set_scale_percent(value)
        self._check_pet_dirty()

    def _check_pet_dirty(self):
        self._pet_dirty = (
            self.current_pet_path != self._saved_pet_path
            or self.current_pet_scale != self._saved_pet_scale
            or abs(self.current_offset_x - self._saved_offset_x) > 0.5
            or abs(self.current_offset_y - self._saved_offset_y) > 0.5
            or self.current_flip_h != self._saved_flip_h
        )
        if hasattr(self, "tab_widget") and self.tab_widget.currentIndex() == 0:
            self.common_save_btn.setVisible(self._pet_dirty)

    def _update_pet_preview(self):
        if not hasattr(self, "pet_preview_widget"):
            return

        path = self.current_pet_path
        if not path or not os.path.exists(path):
            path = DEFAULT_PET_PATH

        filename = os.path.basename(path)
        self.pet_path_label.setText(f"선택된 파일: {filename}")
        self.pet_path_label.setToolTip(path)

        self.pet_preview_widget.load_file(
            path,
            self.current_pet_scale,
            self.current_offset_x,
            self.current_offset_y,
            self.current_flip_h
        )

    def _load_pet_settings(self):
        norm_path = os.path.normpath(PET_SETTINGS_PATH)
        loaded_path = DEFAULT_PET_PATH
        loaded_scale = 100
        loaded_offset_x = 0.0
        loaded_offset_y = 0.0
        loaded_flip_h = False
        if os.path.exists(norm_path):
            try:
                with open(norm_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    p = data.get("character_path")
                    if p and os.path.exists(p):
                        loaded_path = p
                    loaded_scale = int(data.get("scale_percent", 100))
                    loaded_offset_x = float(data.get("offset_x", 0.0))
                    loaded_offset_y = float(data.get("offset_y", 0.0))
                    loaded_flip_h = bool(data.get("flip_h", False))
            except Exception:
                pass

        self.current_pet_path = loaded_path
        self.current_pet_scale = loaded_scale
        self.current_offset_x = loaded_offset_x
        self.current_offset_y = loaded_offset_y
        self.current_flip_h = loaded_flip_h
        self._saved_pet_path = loaded_path
        self._saved_pet_scale = loaded_scale
        self._saved_offset_x = loaded_offset_x
        self._saved_offset_y = loaded_offset_y
        self._saved_flip_h = loaded_flip_h
        self._pet_dirty = False

        self._update_flip_btn_style()

        if hasattr(self, "pet_scale_slider"):
            self.pet_scale_slider.blockSignals(True)
            self.pet_scale_slider.setValue(self.current_pet_scale)
            self.pet_scale_slider.blockSignals(False)
            self.pet_scale_value_label.setText(f"{self.current_pet_scale}%")
            self._update_pet_preview()

        if hasattr(self, "tab_widget") and self.tab_widget.currentIndex() == 0:
            self.common_save_btn.setVisible(False)

    def _save_pet_settings(self):
        norm_path = os.path.normpath(PET_SETTINGS_PATH)
        try:
            data = {
                "character_path": self.current_pet_path,
                "scale_percent": self.current_pet_scale,
                "offset_x": int(round(self.current_offset_x)),
                "offset_y": int(round(self.current_offset_y)),
                "flip_h": self.current_flip_h
            }
            with open(norm_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            self._saved_pet_path = self.current_pet_path
            self._saved_pet_scale = self.current_pet_scale
            self._saved_offset_x = self.current_offset_x
            self._saved_offset_y = self.current_offset_y
            self._saved_flip_h = self.current_flip_h
            self._pet_dirty = False
            self.common_save_btn.setVisible(False)

            if self.pet_window:
                self.pet_window.apply_character(
                    self.current_pet_path,
                    self.current_pet_scale,
                    self.current_offset_x,
                    self.current_offset_y,
                    self.current_flip_h
                )

            self.footer_status_label.setStyleSheet("font-size: 11px; color: #4CAF50; padding: 2px 4px;")
            self.footer_status_label.setText("✅ 펫 설정 저장 완료!")
        except Exception as e:
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #FF6B6B; padding: 2px 4px;")
            self.footer_status_label.setText(f"❌ 펫 설정 저장 실패: {e}")

    # ==========================
    # 1. UI 탭
    # ==========================
    def _init_ui_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 16, 12, 16)
        l.setSpacing(16)

        self.theme_label = QLabel("채팅창 테마:")
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(8)

        self.dark_theme_btn = QPushButton("다크")
        self.light_theme_btn = QPushButton("화이트")
        self.dark_theme_btn.clicked.connect(lambda: self._apply_theme("dark"))
        self.light_theme_btn.clicked.connect(lambda: self._apply_theme("light"))
        theme_btn_layout.addWidget(self.dark_theme_btn)
        theme_btn_layout.addWidget(self.light_theme_btn)

        self.chat_opacity_label = QLabel("채팅창 투명도:")
        self.chat_opacity_slider = QSlider(Qt.Horizontal)
        self.chat_opacity_slider.setRange(20, 100)
        self.chat_opacity_slider.setValue(int(self.chat_window.windowOpacity() * 100))
        self.chat_opacity_slider.valueChanged.connect(self.set_chat_opacity)

        self.pet_opacity_label = QLabel("펫 투명도:")
        self.pet_opacity_slider = QSlider(Qt.Horizontal)
        self.pet_opacity_slider.setRange(20, 100)
        pet_val = int(self.pet_window.windowOpacity() * 100) if self.pet_window else 100
        self.pet_opacity_slider.setValue(pet_val)
        self.pet_opacity_slider.valueChanged.connect(self.set_pet_opacity)

        l.addWidget(self.theme_label)
        l.addLayout(theme_btn_layout)
        l.addWidget(self.chat_opacity_label)
        l.addWidget(self.chat_opacity_slider)
        l.addWidget(self.pet_opacity_label)
        l.addWidget(self.pet_opacity_slider)
        l.addStretch()

        return w

    # ==========================
    # 2. 모델 탭
    # ==========================
    def _init_model_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 12, 12, 12)
        l.setSpacing(8)

        self._local_checkbox = QCheckBox("로컬 모델")
        self._local_checkbox.toggled.connect(self._on_local_toggled)
        l.addWidget(self._local_checkbox)

        self._model_label = QLabel("모델명:")
        self._model_edit = QLineEdit()
        self._model_edit.textChanged.connect(self._check_model_dirty)
        l.addWidget(self._model_label)
        l.addWidget(self._model_edit)

        self._base_url_container = QWidget()
        base_url_layout = QVBoxLayout(self._base_url_container)
        base_url_layout.setContentsMargins(0, 0, 0, 0)
        base_url_layout.setSpacing(4)

        self._base_url_label = QLabel("Base URL:")
        self._base_url_edit = QLineEdit()
        self._base_url_edit.textChanged.connect(self._check_model_dirty)
        base_url_layout.addWidget(self._base_url_label)
        base_url_layout.addWidget(self._base_url_edit)
        l.addWidget(self._base_url_container)

        self._api_key_label = QLabel("API Key:")
        self._api_key_edit = QLineEdit()
        self._api_key_edit.textChanged.connect(self._check_model_dirty)
        l.addWidget(self._api_key_label)
        l.addWidget(self._api_key_edit)

        l.addStretch()

        self._load_model_settings()
        return w

    # ==========================
    # 3. MCP 탭
    # ==========================
    def _init_mcp_tab(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(12, 10, 12, 10)
        l.setSpacing(6)

        self._mcp_hint = QLabel("JSON 형식으로 직접 편집할 수 있습니다. 저장 시 유효성 검사가 실행됩니다.")
        self._mcp_hint.setWordWrap(True)
        l.addWidget(self._mcp_hint)

        self._mcp_editor = QTextEdit()
        font = QFont("Courier New")
        font.setPointSize(10)
        self._mcp_editor.setFont(font)
        self._mcp_editor.setAcceptRichText(False)
        self._mcp_editor.textChanged.connect(self._check_mcp_dirty)
        l.addWidget(self._mcp_editor, 1)

        self._load_mcp_settings()
        return w

    # ==========================
    # 공통 더티 체크 및 탭 변경 처리
    # ==========================
    def _check_model_dirty(self):
        if not hasattr(self, "_local_checkbox") or not self._saved_model_state:
            return
        current = {
            "is_local": self._local_checkbox.isChecked(),
            "model": self._model_edit.text().strip(),
            "base_url": self._base_url_edit.text().strip(),
            "api_key": self._api_key_edit.text().strip(),
        }
        self._model_dirty = (current != self._saved_model_state)
        if self.tab_widget.currentIndex() == 2:
            self.common_save_btn.setVisible(self._model_dirty)

    def _check_mcp_dirty(self):
        if not hasattr(self, "_mcp_editor"):
            return
        current_text = self._mcp_editor.toPlainText().strip()
        self._mcp_dirty = (current_text != self._saved_mcp_text)
        if self.tab_widget.currentIndex() == 3:
            self.common_save_btn.setVisible(self._mcp_dirty)

    def _on_tab_changed(self, index: int):
        self.footer_status_label.setText("")
        if index == 0:
            self.common_save_btn.setVisible(self._pet_dirty)
        elif index == 2:
            self.common_save_btn.setVisible(self._model_dirty)
        elif index == 3:
            self.common_save_btn.setVisible(self._mcp_dirty)
        else:
            self.common_save_btn.setVisible(False)

    def _on_common_save_clicked(self):
        idx = self.tab_widget.currentIndex()
        if idx == 0:
            self._save_pet_settings()
        elif idx == 2:
            self._save_model_settings()
        elif idx == 3:
            self._save_mcp_settings()

    # ==========================
    # 모델 탭 데이터 처리
    # ==========================
    def _read_env_dict(self) -> dict:
        env_vars = {}
        path = os.path.normpath(ENV_PATH)
        if not os.path.exists(path):
            return env_vars
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                v_clean = v.split("#")[0].strip()
                env_vars[k.strip()] = v_clean
        return env_vars

    def _load_model_settings(self):
        if not hasattr(self, "_local_checkbox"):
            return
        env = self._read_env_dict()
        use_openai = env.get("USE_OPENAI", "false").lower() == "true"
        self.is_local = not use_openai

        self.local_model = env.get("API_MODEL", "")
        self.local_base_url = env.get("API_BASE_URL", "")
        self.local_api_key = env.get("LOCAL_API_KEY", "")

        self.openai_model = env.get("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_api_key = env.get("API_KEY", "")

        self._local_checkbox.blockSignals(True)
        self._local_checkbox.setChecked(self.is_local)
        self._local_checkbox.blockSignals(False)

        self._model_edit.blockSignals(True)
        self._base_url_edit.blockSignals(True)
        self._api_key_edit.blockSignals(True)

        self._update_model_fields()

        self._model_edit.blockSignals(False)
        self._base_url_edit.blockSignals(False)
        self._api_key_edit.blockSignals(False)

        self._saved_model_state = {
            "is_local": self._local_checkbox.isChecked(),
            "model": self._model_edit.text().strip(),
            "base_url": self._base_url_edit.text().strip(),
            "api_key": self._api_key_edit.text().strip(),
        }
        self._model_dirty = False
        if self.tab_widget.currentIndex() == 2:
            self.common_save_btn.setVisible(False)

    def _on_local_toggled(self, checked: bool):
        if self.is_local:
            self.local_model = self._model_edit.text().strip()
            self.local_base_url = self._base_url_edit.text().strip()
            self.local_api_key = self._api_key_edit.text().strip()
        else:
            self.openai_model = self._model_edit.text().strip()
            self.openai_api_key = self._api_key_edit.text().strip()

        self.is_local = checked

        self._model_edit.blockSignals(True)
        self._base_url_edit.blockSignals(True)
        self._api_key_edit.blockSignals(True)

        self._update_model_fields()

        self._model_edit.blockSignals(False)
        self._base_url_edit.blockSignals(False)
        self._api_key_edit.blockSignals(False)

        self._check_model_dirty()

    def _update_model_fields(self):
        if self.is_local:
            self._model_edit.setText(self.local_model)
            self._base_url_edit.setText(self.local_base_url)
            self._api_key_edit.setText(self.local_api_key)
            self._base_url_container.setVisible(True)
        else:
            self._model_edit.setText(self.openai_model)
            self._api_key_edit.setText(self.openai_api_key)
            self._base_url_container.setVisible(False)

    def _save_model_settings(self):
        path = os.path.normpath(ENV_PATH)
        if self.is_local:
            self.local_model = self._model_edit.text().strip()
            self.local_base_url = self._base_url_edit.text().strip()
            self.local_api_key = self._api_key_edit.text().strip()
            updates = {
                "USE_OPENAI": "False",
                "API_MODEL": self.local_model,
                "API_BASE_URL": self.local_base_url,
                "LOCAL_API_KEY": self.local_api_key,
            }
        else:
            self.openai_model = self._model_edit.text().strip()
            self.openai_api_key = self._api_key_edit.text().strip()
            updates = {
                "USE_OPENAI": "True",
                "OPENAI_MODEL": self.openai_model,
                "API_KEY": self.openai_api_key,
            }

        try:
            lines = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            updated_keys = set()
            new_lines = []
            for line in lines:
                s = line.strip()
                matched_key = None
                if s and not s.startswith("#") and "=" in s:
                    k = s.split("=", 1)[0].strip()
                    if k in updates:
                        matched_key = k

                if matched_key:
                    comment = ""
                    if "#" in line:
                        parts = line.split("#", 1)
                        if len(parts) > 1 and "=" in parts[0]:
                            comment = " #" + parts[1].rstrip("\r\n")
                    new_lines.append(f"{matched_key}={updates[matched_key]}{comment}\n")
                    updated_keys.add(matched_key)
                else:
                    new_lines.append(line)

            for k, v in updates.items():
                if k not in updated_keys:
                    new_lines.append(f"{k}={v}\n")

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            for k, v in updates.items():
                os.environ[k] = v

            self._saved_model_state = {
                "is_local": self._local_checkbox.isChecked(),
                "model": self._model_edit.text().strip(),
                "base_url": self._base_url_edit.text().strip(),
                "api_key": self._api_key_edit.text().strip(),
            }
            self._model_dirty = False
            self.common_save_btn.setVisible(False)

            self.footer_status_label.setStyleSheet("font-size: 11px; color: #4CAF50; padding: 2px 4px;")
            self.footer_status_label.setText("✅ .env에 저장 완료!")
        except Exception as e:
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #FF6B6B; padding: 2px 4px;")
            self.footer_status_label.setText(f"❌ 저장 실패: {e}")

    # ==========================
    # MCP 탭 데이터 처리
    # ==========================
    def _load_mcp_settings(self):
        if not hasattr(self, "_mcp_editor"):
            return
        path = os.path.normpath(CONFIG_PATH)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            parsed = json.loads(raw)
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            self._mcp_editor.blockSignals(True)
            self._mcp_editor.setPlainText(formatted)
            self._mcp_editor.blockSignals(False)
            self._saved_mcp_text = formatted.strip()
            self._mcp_dirty = False
            if self.tab_widget.currentIndex() == 3:
                self.common_save_btn.setVisible(False)
        except FileNotFoundError:
            self._mcp_editor.setPlainText("{}")
            self._saved_mcp_text = "{}"
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #FF6B6B; padding: 2px 4px;")
            self.footer_status_label.setText(f"파일을 찾을 수 없습니다: {path}")
        except json.JSONDecodeError as e:
            self._mcp_editor.setPlainText(raw)
            self._saved_mcp_text = raw.strip()
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #FF6B6B; padding: 2px 4px;")
            self.footer_status_label.setText(f"기존 파일이 올바른 JSON이 아닙니다: {e}")

    def _save_mcp_settings(self):
        text = self._mcp_editor.toPlainText().strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #FF6B6B; padding: 2px 4px;")
            self.footer_status_label.setText(f"❌ JSON 오류: {e}")
            return

        path = os.path.normpath(CONFIG_PATH)
        try:
            formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
            with open(path, "w", encoding="utf-8") as f:
                f.write(formatted)
            self._saved_mcp_text = formatted.strip()
            self._mcp_dirty = False
            self.common_save_btn.setVisible(False)
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #4CAF50; padding: 2px 4px;")
            self.footer_status_label.setText("✅ config.json 저장 완료!")
        except Exception as e:
            self.footer_status_label.setStyleSheet("font-size: 11px; color: #FF6B6B; padding: 2px 4px;")
            self.footer_status_label.setText(f"❌ 저장 실패: {e}")

    # ==========================
    # 테마 업데이트 (다크 / 화이트 완벽 지원)
    # ==========================
    def update_theme(self, theme: dict):
        is_dark = theme["name"] == "dark"

        self.container.setStyleSheet(get_settings_window_style(theme))

        label_style = get_settings_label_style(theme)
        slider_style = get_settings_slider_style(theme)

        title_color = "#E0E0E0" if is_dark else "#1A1A1A"
        self.title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; margin-bottom: 4px; color: {title_color};"
        )

        self.theme_label.setStyleSheet(label_style)
        self.chat_opacity_label.setStyleSheet(label_style)
        self.pet_opacity_label.setStyleSheet(label_style)
        self.chat_opacity_slider.setStyleSheet(slider_style)
        self.pet_opacity_slider.setStyleSheet(slider_style)

        if hasattr(self, "pet_scale_title"):
            self.pet_scale_title.setStyleSheet(label_style)
            self.pet_scale_value_label.setStyleSheet(label_style)
            self.pet_scale_slider.setStyleSheet(slider_style)

            if hasattr(self, "pet_preview_widget"):
                self.pet_preview_widget.set_theme(is_dark)

            if hasattr(self, "pet_guide_label"):
                guide_color = "#888888" if is_dark else "#666666"
                self.pet_guide_label.setStyleSheet(f"font-size: 11px; color: {guide_color};")

            path_color = "#AAAAAA" if is_dark else "#555555"
            self.pet_path_label.setStyleSheet(f"font-size: 11px; color: {path_color};")

            reset_bg = "#3A3A3A" if is_dark else "#E0E0E0"
            reset_color = "#CCCCCC" if is_dark else "#333333"
            self.pet_choose_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2979B0;
                    color: white;
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 7px 14px;
                }
                QPushButton:hover { background-color: #1A5F8F; }
            """)
            self.pet_reset_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {reset_bg};
                    color: {reset_color};
                    border-radius: 8px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 7px 14px;
                }}
                QPushButton:hover {{
                    background-color: {'#4A4A4A' if is_dark else '#D0D0D0'};
                }}
            """)

            if hasattr(self, "pet_center_btn"):
                center_bg = "#2C3E50" if is_dark else "#E8EEF5"
                center_color = "#64B5F6" if is_dark else "#1976D2"
                center_hover = "#34495E" if is_dark else "#D5E2F0"
                self.pet_center_btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {center_bg};
                        color: {center_color};
                        border: 1px solid {'#3D566E' if is_dark else '#B8D2EC'};
                        border-radius: 6px;
                        font-size: 11px;
                        font-weight: bold;
                        padding: 5px 12px;
                    }}
                    QPushButton:hover {{
                        background-color: {center_hover};
                    }}
                """)

            self._update_flip_btn_style()

        self._update_theme_buttons(theme)
        self._update_tab_style(is_dark)
        self._update_model_and_mcp_theme(is_dark)

    def _update_tab_style(self, is_dark: bool):
        pane_border = "#3A3F4B" if is_dark else "#D0D0D0"
        tab_bg = "#1A1D23" if is_dark else "#EAEAEA"
        tab_color = "#888888" if is_dark else "#555555"
        tab_hover = "#2A2E39" if is_dark else "#DFDFDF"

        self.tab_widget.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {pane_border};
                border-radius: 8px;
                background-color: transparent;
                padding: 6px;
            }}
            QTabBar::tab {{
                background-color: {tab_bg};
                color: {tab_color};
                border: 1px solid {pane_border};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 6px 18px;
                font-size: 12px;
                font-weight: bold;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: #2979B0;
                color: white;
                border-color: #2979B0;
            }}
            QTabBar::tab:hover:!selected {{
                background-color: {tab_hover};
                color: {'#CCCCCC' if is_dark else '#222222'};
            }}
        """)

    def _update_model_and_mcp_theme(self, is_dark: bool):
        """화이트/다크 모드에 맞춰 모델 탭과 MCP 탭 텍스트 및 입력창 색상을 선명하게 전환합니다."""
        chk_text_color = "#E0E0E0" if is_dark else "#1A1A1A"
        chk_bg = "#1A1D23" if is_dark else "#FFFFFF"
        chk_border = "#3A3F4B" if is_dark else "#B0B4BC"

        sublabel_color = "#CCCCCC" if is_dark else "#222222"
        input_bg = "#1A1D23" if is_dark else "#FFFFFF"
        input_border = "#3A3F4B" if is_dark else "#C0C4CC"
        input_text = "#E0E0E0" if is_dark else "#1A1A1A"

        hint_color = "#888888" if is_dark else "#555555"
        editor_bg = "#1A1D23" if is_dark else "#FAFAFA"
        editor_text = "#ABB2BF" if is_dark else "#1A1A1A"
        editor_border = "#3A3F4B" if is_dark else "#C0C4CC"

        if hasattr(self, "_local_checkbox"):
            self._local_checkbox.setStyleSheet(f"""
                QCheckBox {{
                    color: {chk_text_color};
                    font-size: 13px;
                    font-weight: bold;
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border-radius: 4px;
                    border: 1px solid {chk_border};
                    background-color: {chk_bg};
                }}
                QCheckBox::indicator:hover {{ border-color: #2979B0; }}
                QCheckBox::indicator:checked {{ background-color: #2979B0; border-color: #2979B0; }}
            """)

        field_label_style = f"color: {sublabel_color}; font-size: 12px; font-weight: bold;"
        line_edit_style = f"""
            QLineEdit {{
                background-color: {input_bg};
                color: {input_text};
                border: 1px solid {input_border};
                border-radius: 8px;
                font-size: 12px;
                padding: 6px 10px;
            }}
            QLineEdit:focus {{ border-color: #2979B0; }}
        """

        if hasattr(self, "_model_label"):
            self._model_label.setStyleSheet(field_label_style)
            self._base_url_label.setStyleSheet(field_label_style)
            self._api_key_label.setStyleSheet(field_label_style)
            self._model_edit.setStyleSheet(line_edit_style)
            self._base_url_edit.setStyleSheet(line_edit_style)
            self._api_key_edit.setStyleSheet(line_edit_style)

        if hasattr(self, "_mcp_hint"):
            self._mcp_hint.setStyleSheet(f"color: {hint_color}; font-size: 11px;")
        if hasattr(self, "_mcp_editor"):
            self._mcp_editor.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {editor_bg};
                    color: {editor_text};
                    border: 1px solid {editor_border};
                    border-radius: 8px;
                    font-family: 'Courier New', monospace;
                    font-size: 12px;
                    padding: 8px;
                    line-height: 1.4;
                }}
            """)

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


class MCPConfigEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MCP 설정 관리")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(540, 440)

        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._container = QFrame(self)
        self._container.setObjectName("mcp_editor_container")
        self._container.setStyleSheet("""
            QFrame#mcp_editor_container {
                background-color: #23272E;
                border-radius: 14px;
                border: 1px solid #3A3F4B;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 6)
        self._container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("⚙️  MCP 설정 (config.json)")
        title.setStyleSheet("color: #E0E0E0; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("JSON 형식으로 직접 편집할 수 있습니다. 저장 시 유효성 검사가 실행됩니다.")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._editor = QTextEdit()
        self._editor.setStyleSheet("""
            QTextEdit {
                background-color: #1A1D23;
                color: #ABB2BF;
                border: 1px solid #3A3F4B;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12.5px;
                padding: 10px;
                line-height: 1.5;
            }
        """)
        font = QFont("Courier New")
        font.setPointSize(11)
        self._editor.setFont(font)
        self._editor.setAcceptRichText(False)
        layout.addWidget(self._editor, 1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px; padding: 2px 0;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._save_btn = QPushButton("저장")
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2979B0;
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1A5F8F; }
        """)
        self._save_btn.clicked.connect(self._save)

        self._cancel_btn = QPushButton("닫기")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3F4B;
                color: #CCCCCC;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #4A505E; }
        """)
        self._cancel_btn.clicked.connect(self.close)

        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        outer.addWidget(self._container)

        self._load()

    def _config_path(self) -> str:
        return os.path.normpath(CONFIG_PATH)

    def _load(self):
        path = self._config_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            parsed = json.loads(raw)
            self._editor.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
            self._set_status("", ok=True)
        except FileNotFoundError:
            self._editor.setPlainText("{}")
            self._set_status(f"파일을 찾을 수 없습니다: {path}", ok=False)
        except json.JSONDecodeError as e:
            self._editor.setPlainText(raw)
            self._set_status(f"기존 파일이 올바른 JSON이 아닙니다: {e}", ok=False)

    def _save(self):
        text = self._editor.toPlainText().strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            self._set_status(f"❌ JSON 오류: {e}", ok=False)
            return

        path = self._config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            self._set_status("✅ 저장 완료!", ok=True)
        except Exception as e:
            self._set_status(f"❌ 저장 실패: {e}", ok=False)

    def _set_status(self, msg: str, ok: bool = True):
        color = "#4CAF50" if ok else "#FF6B6B"
        self._status_label.setStyleSheet(f"font-size: 11px; color: {color}; padding: 2px 0;")
        self._status_label.setText(msg)

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


class ModelConfigEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("모델 설정 관리")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(440, 390)

        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        self.local_model = ""
        self.local_base_url = ""
        self.local_api_key = ""
        self.openai_model = ""
        self.openai_api_key = ""
        self.is_local = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._container = QFrame(self)
        self._container.setObjectName("model_editor_container")
        self._container.setStyleSheet("""
            QFrame#model_editor_container {
                background-color: #23272E;
                border-radius: 14px;
                border: 1px solid #3A3F4B;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 6)
        self._container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("🤖  모델 설정 (.env)")
        title.setStyleSheet("color: #E0E0E0; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self._local_checkbox = QCheckBox("로컬 모델")
        self._local_checkbox.setStyleSheet("""
            QCheckBox {
                color: #E0E0E0;
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3A3F4B;
                background-color: #1A1D23;
            }
            QCheckBox::indicator:hover {
                border-color: #2979B0;
            }
            QCheckBox::indicator:checked {
                background-color: #2979B0;
                border-color: #2979B0;
            }
        """)
        self._local_checkbox.toggled.connect(self._on_local_toggled)
        layout.addWidget(self._local_checkbox)

        line_edit_style = """
            QLineEdit {
                background-color: #1A1D23;
                color: #E0E0E0;
                border: 1px solid #3A3F4B;
                border-radius: 8px;
                font-size: 12px;
                padding: 7px 10px;
            }
            QLineEdit:focus {
                border-color: #2979B0;
            }
        """
        label_style = "color: #CCCCCC; font-size: 12px; font-weight: bold;"

        self._model_label = QLabel("모델명:")
        self._model_label.setStyleSheet(label_style)
        self._model_edit = QLineEdit()
        self._model_edit.setStyleSheet(line_edit_style)
        layout.addWidget(self._model_label)
        layout.addWidget(self._model_edit)

        self._base_url_container = QWidget()
        base_url_layout = QVBoxLayout(self._base_url_container)
        base_url_layout.setContentsMargins(0, 0, 0, 0)
        base_url_layout.setSpacing(4)

        self._base_url_label = QLabel("Base URL:")
        self._base_url_label.setStyleSheet(label_style)
        self._base_url_edit = QLineEdit()
        self._base_url_edit.setStyleSheet(line_edit_style)
        base_url_layout.addWidget(self._base_url_label)
        base_url_layout.addWidget(self._base_url_edit)
        layout.addWidget(self._base_url_container)

        self._api_key_label = QLabel("API Key:")
        self._api_key_label.setStyleSheet(label_style)
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setStyleSheet(line_edit_style)
        layout.addWidget(self._api_key_label)
        layout.addWidget(self._api_key_edit)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px; padding: 2px 0;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._save_btn = QPushButton("저장")
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2979B0;
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1A5F8F; }
        """)
        self._save_btn.clicked.connect(self._save)

        self._cancel_btn = QPushButton("닫기")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3F4B;
                color: #CCCCCC;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #4A505E; }
        """)
        self._cancel_btn.clicked.connect(self.close)

        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        outer.addWidget(self._container)

        self._load()

    def _env_path(self) -> str:
        return os.path.normpath(ENV_PATH)

    def _read_env_dict(self) -> dict:
        env_vars = {}
        path = self._env_path()
        if not os.path.exists(path):
            return env_vars
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                v_clean = v.split("#")[0].strip()
                env_vars[k.strip()] = v_clean
        return env_vars

    def _load(self):
        env = self._read_env_dict()
        use_openai = env.get("USE_OPENAI", "false").lower() == "true"
        self.is_local = not use_openai

        self.local_model = env.get("API_MODEL", "")
        self.local_base_url = env.get("API_BASE_URL", "")
        self.local_api_key = env.get("LOCAL_API_KEY", "")

        self.openai_model = env.get("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_api_key = env.get("API_KEY", "")

        self._local_checkbox.blockSignals(True)
        self._local_checkbox.setChecked(self.is_local)
        self._local_checkbox.blockSignals(False)

        self._update_fields()

    def _on_local_toggled(self, checked: bool):
        if self.is_local:
            self.local_model = self._model_edit.text().strip()
            self.local_base_url = self._base_url_edit.text().strip()
            self.local_api_key = self._api_key_edit.text().strip()
        else:
            self.openai_model = self._model_edit.text().strip()
            self.openai_api_key = self._api_key_edit.text().strip()

        self.is_local = checked
        self._update_fields()

    def _update_fields(self):
        if self.is_local:
            self._model_edit.setText(self.local_model)
            self._base_url_edit.setText(self.local_base_url)
            self._api_key_edit.setText(self.local_api_key)
            self._base_url_container.setVisible(True)
        else:
            self._model_edit.setText(self.openai_model)
            self._api_key_edit.setText(self.openai_api_key)
            self._base_url_container.setVisible(False)
        self._set_status("", ok=True)

    def _save(self):
        path = self._env_path()
        if self.is_local:
            self.local_model = self._model_edit.text().strip()
            self.local_base_url = self._base_url_edit.text().strip()
            self.local_api_key = self._api_key_edit.text().strip()
            updates = {
                "USE_OPENAI": "False",
                "API_MODEL": self.local_model,
                "API_BASE_URL": self.local_base_url,
                "LOCAL_API_KEY": self.local_api_key,
            }
        else:
            self.openai_model = self._model_edit.text().strip()
            self.openai_api_key = self._api_key_edit.text().strip()
            updates = {
                "USE_OPENAI": "True",
                "OPENAI_MODEL": self.openai_model,
                "API_KEY": self.openai_api_key,
            }

        try:
            lines = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            updated_keys = set()
            new_lines = []
            for line in lines:
                s = line.strip()
                matched_key = None
                if s and not s.startswith("#") and "=" in s:
                    k = s.split("=", 1)[0].strip()
                    if k in updates:
                        matched_key = k

                if matched_key:
                    comment = ""
                    if "#" in line:
                        parts = line.split("#", 1)
                        if len(parts) > 1 and "=" in parts[0]:
                            comment = " #" + parts[1].rstrip("\r\n")
                    new_lines.append(f"{matched_key}={updates[matched_key]}{comment}\n")
                    updated_keys.add(matched_key)
                else:
                    new_lines.append(line)

            for k, v in updates.items():
                if k not in updated_keys:
                    new_lines.append(f"{k}={v}\n")

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            for k, v in updates.items():
                os.environ[k] = v

            self._set_status("✅ .env에 저장 완료!", ok=True)
        except Exception as e:
            self._set_status(f"❌ 저장 실패: {e}", ok=False)

    def _set_status(self, msg: str, ok: bool = True):
        color = "#4CAF50" if ok else "#FF6B6B"
        self._status_label.setStyleSheet(f"font-size: 11px; color: {color}; padding: 2px 0;")
        self._status_label.setText(msg)

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
