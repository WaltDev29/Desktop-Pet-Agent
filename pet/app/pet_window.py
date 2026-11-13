import json
import os
import random
from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint, QRect
from PySide6.QtGui import QMovie, QPainter, QPixmap

from app.chat_window import ChatWindow
from app.login_window import LoginWindow
from app.pet_style import (
    PET_WIDTH, 
    PET_HEIGHT, 
    PET_MOVIE_PATH, 
    CHAT_WIN_OFFSET_X, 
    CHAT_WIN_OFFSET_Y,
    MOVEMENT_X_MIN_RATIO,
    MOVEMENT_X_MAX_RATIO,
    MOVEMENT_Y_MIN_RATIO,
    MOVEMENT_Y_MAX_RATIO
)

PET_SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "pet_settings.json"
)

class DirectionalPetLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.movie = None
        self.pixmap_image = None
        self.h_flip = False
        self.base_flip_h = False
        self.offset_x_ratio = 0.0
        self.offset_y_ratio = 0.0

    def setMovie(self, movie):
        if self.movie:
            try:
                self.movie.frameChanged.disconnect(self.update)
            except Exception:
                pass
        self.movie = movie
        self.pixmap_image = None
        if self.movie:
            self.movie.frameChanged.connect(self.update)
        self.update()

    def setStaticPixmap(self, pixmap):
        if self.movie:
            try:
                self.movie.frameChanged.disconnect(self.update)
            except Exception:
                pass
            self.movie.stop()
            self.movie = None
        self.pixmap_image = pixmap
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        pix = None
        if self.movie:
            pix = self.movie.currentPixmap()
        elif self.pixmap_image and not self.pixmap_image.isNull():
            pix = self.pixmap_image

        if pix and not pix.isNull():
            painter.save()
            # 픽셀 아트 / GIF 도트의 선명한 화질을 유지하기 위해 SmoothPixmapTransform 렌더 힌트는 사용하지 않음
            if self.h_flip:
                # 가로축 기준 반전
                painter.scale(-1, 1)
                painter.translate(-self.width(), 0)

            pw = pix.width()
            ph = pix.height()
            if pw > 0 and ph > 0:
                # 원본 종횡비 유지 (강제 왜곡 방지)
                ratio = min(self.width() / pw, self.height() / ph)
                target_w = max(1, int(pw * ratio))
                target_h = max(1, int(ph * ratio))

                center_x = self.width() / 2.0 + self.offset_x_ratio * self.width()
                center_y = self.height() / 2.0 + self.offset_y_ratio * self.height()

                draw_x = int(center_x - target_w / 2.0)
                draw_y = int(center_y - target_h / 2.0)

                painter.drawPixmap(QRect(draw_x, draw_y, target_w, target_h), pix)
            painter.restore()
            return
        super().paintEvent(event)

class PetWindow(QWidget):
    def __init__(self, already_logged_in: bool = False):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen) 
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.resize(PET_WIDTH, PET_HEIGHT) 

        self.current_character_path = PET_MOVIE_PATH
        self.scale_percent = 100
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.base_flip_h = False
        self.movie = None

        self.pet_label = DirectionalPetLabel(self)
        self.pet_label.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.pet_label.setGeometry(0, 0, PET_WIDTH, PET_HEIGHT) 
        self.pet_label.setAlignment(Qt.AlignCenter)  
        self.pet_label.setScaledContents(False) 
        
        # 저장된 펫 설정 불러오기 및 초기화
        self._load_pet_settings()
        self.apply_character(self.current_character_path, self.scale_percent, self.offset_x, self.offset_y, self.base_flip_h)

        screen_geo = self.screen().availableGeometry()
        width, height = screen_geo.width(), screen_geo.height()
        
        self.min_x = width * MOVEMENT_X_MIN_RATIO
        self.max_x = width * MOVEMENT_X_MAX_RATIO - self.width()
        self.min_y = height * MOVEMENT_Y_MIN_RATIO
        self.max_y = height * MOVEMENT_Y_MAX_RATIO - self.height()

        self.curr_x = (width - self.width()) / 2
        self.curr_y = (height - self.height()) * 0.75
        self.move(int(self.curr_x), int(self.curr_y))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(16)

        self.x_speed, self.y_speed = 0.5, 0.5
        # 초기 방향 설정 (오른쪽으로 이동하므로 우로 반전)
        self.pet_label.h_flip = True
        self.change_dir_timer = 0
        self.is_interacting = False
        self.is_paused = False          # 우클릭으로 멈춤 여부
        self.chat_win = ChatWindow(self)
        self._logged_in = already_logged_in
        self.login_win = LoginWindow(self)
        self.login_win.login_success.connect(self._on_login_success)

        # ── 드래그 상태 ──────────────────────────────────────
        self._drag_active = False
        self._drag_start_cursor: QPoint | None = None
        self._drag_start_pet: QPoint | None = None
        self._drag_start_chat: QPoint | None = None
        self._drag_start_login: QPoint | None = None
        self._drag_start_signup: QPoint | None = None

        if already_logged_in:
            QTimer.singleShot(100, self._on_login_success)

    def _load_pet_settings(self):
        norm_path = os.path.normpath(PET_SETTINGS_PATH)
        if os.path.exists(norm_path):
            try:
                with open(norm_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    p = data.get("character_path")
                    if p and os.path.exists(p):
                        self.current_character_path = p
                    self.scale_percent = int(data.get("scale_percent", 100))
                    self.offset_x = float(data.get("offset_x", 0))
                    self.offset_y = float(data.get("offset_y", 0))
                    self.base_flip_h = bool(data.get("flip_h", False))
            except Exception:
                pass

    def apply_character(self, path: str, scale_percent: int = 100, offset_x: float = 0.0, offset_y: float = 0.0, flip_h: bool = False):
        self.scale_percent = max(30, min(300, scale_percent))
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.base_flip_h = flip_h
        self.pet_label.base_flip_h = flip_h
        self.pet_label.offset_x_ratio = offset_x / 180.0
        self.pet_label.offset_y_ratio = offset_y / 180.0
        has_speed = hasattr(self, "x_speed")
        moving_right = (self.x_speed > 0) if has_speed else True
        self.pet_label.h_flip = moving_right ^ self.base_flip_h
        self.pet_label.update()

        scale = self.scale_percent / 100.0
        new_w = max(30, int(PET_WIDTH * scale))
        new_h = max(30, int(PET_HEIGHT * scale))

        has_pos = hasattr(self, "curr_x") and hasattr(self, "curr_y")
        if has_pos:
            old_center_x = self.curr_x + self.width() / 2.0
            old_center_y = self.curr_y + self.height() / 2.0

        self.resize(new_w, new_h)
        self.pet_label.setGeometry(0, 0, new_w, new_h)
        self._update_movement_bounds()

        if has_pos:
            new_x = old_center_x - new_w / 2.0
            new_y = old_center_y - new_h / 2.0
            if hasattr(self, "min_x") and hasattr(self, "max_x"):
                new_x = max(self.min_x, min(new_x, self.max_x))
                new_y = max(self.min_y, min(new_y, self.max_y))
            self.curr_x = new_x
            self.curr_y = new_y
            self.move(int(new_x), int(new_y))

        if not path or not os.path.exists(path):
            path = PET_MOVIE_PATH

        self.current_character_path = path
        if path.lower().endswith(".gif"):
            if self.movie:
                self.movie.stop()
            self.movie = QMovie(path)
            self.pet_label.setMovie(self.movie)
            self.movie.start()
        else:
            if self.movie:
                self.movie.stop()
                self.movie = None
            pix = QPixmap(path)
            self.pet_label.setStaticPixmap(pix)

    def set_offset(self, offset_x: float, offset_y: float):
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.pet_label.offset_x_ratio = offset_x / 180.0
        self.pet_label.offset_y_ratio = offset_y / 180.0
        self.pet_label.update()

    def set_base_flip(self, flip_h: bool):
        self.base_flip_h = flip_h
        self.pet_label.base_flip_h = flip_h
        has_speed = hasattr(self, "x_speed")
        moving_right = (self.x_speed > 0) if has_speed else True
        self.pet_label.h_flip = moving_right ^ self.base_flip_h
        self.pet_label.update()

    def set_scale_percent(self, scale_percent: int):
        self.scale_percent = max(30, min(300, scale_percent))
        scale = self.scale_percent / 100.0
        new_w = max(30, int(PET_WIDTH * scale))
        new_h = max(30, int(PET_HEIGHT * scale))

        has_pos = hasattr(self, "curr_x") and hasattr(self, "curr_y")
        if has_pos:
            old_center_x = self.curr_x + self.width() / 2.0
            old_center_y = self.curr_y + self.height() / 2.0

        self.resize(new_w, new_h)
        self.pet_label.setGeometry(0, 0, new_w, new_h)
        self._update_movement_bounds()

        if has_pos:
            new_x = old_center_x - new_w / 2.0
            new_y = old_center_y - new_h / 2.0
            if hasattr(self, "min_x") and hasattr(self, "max_x"):
                new_x = max(self.min_x, min(new_x, self.max_x))
                new_y = max(self.min_y, min(new_y, self.max_y))
            self.curr_x = new_x
            self.curr_y = new_y
            self.move(int(new_x), int(new_y))

    def _update_movement_bounds(self):
        screen = self.screen()
        if not screen:
            return
        screen_geo = screen.availableGeometry()
        width, height = screen_geo.width(), screen_geo.height()
        self.min_x = width * MOVEMENT_X_MIN_RATIO
        self.max_x = width * MOVEMENT_X_MAX_RATIO - self.width()
        self.min_y = height * MOVEMENT_Y_MIN_RATIO
        self.max_y = height * MOVEMENT_Y_MAX_RATIO - self.height()

    def update_logic(self):
        if self.is_interacting or self.is_paused:
            return
        
        self.change_dir_timer += 1
        if self.change_dir_timer > 100: 
            self.x_speed = random.uniform(-1.0, 1.0)
            self.y_speed = random.uniform(-1.0, 1.0)
            self.change_dir_timer = 0

        self.curr_x += self.x_speed
        self.curr_y += self.y_speed

        if self.curr_x <= self.min_x or self.curr_x >= self.max_x:
            self.x_speed *= -1
        if self.curr_y <= self.min_y or self.curr_y >= self.max_y:
            self.y_speed *= -1
            
        self.curr_x = max(self.min_x, min(self.curr_x, self.max_x))
        self.curr_y = max(self.min_y, min(self.curr_y, self.max_y))
        self.move(int(self.curr_x), int(self.curr_y))

        # 이동 방향 및 기본 반전 설정에 맞춰 좌우 반전 상태 설정
        if self.x_speed > 0:
            self.pet_label.h_flip = True ^ self.base_flip_h
        elif self.x_speed < 0:
            self.pet_label.h_flip = False ^ self.base_flip_h

    # ── 마우스 이벤트 (클릭 vs 드래그 구분) ────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_drag(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton and self._drag_start_cursor is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_cursor
            if not self._drag_active and delta.manhattanLength() > 5:
                self._drag_active = True
                # 드래그 중 자동이동 타이머 일시 정지
                self.timer.stop()
            if self._drag_active:
                self.do_drag(event.globalPosition().toPoint())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self._drag_active:
                # 드래그 종료 → 자동이동 재개
                self.end_drag()
            else:
                # 단순 클릭 → 채팅창 토글
                self.interact_with_pet()
        elif event.button() == Qt.RightButton and not self._drag_active:
            # 우클릭 → 자동이동 멈춤/재개 토글
            self.is_paused = not self.is_paused

    # ── 드래그 공개 메서드 (ChatWindow에서도 호출) ────────────────
    def start_drag(self, cursor_global: QPoint):
        """드래그 시작: 시작 위치를 기억합니다."""
        self._drag_active = False
        self._drag_start_cursor = cursor_global
        self._drag_start_pet = self.pos()
        self._drag_start_chat = self.chat_win.pos() if self.chat_win.isVisible() else None
        self._drag_start_login = self.login_win.pos() if self.login_win.isVisible() else None
        if hasattr(self, 'signup_win') and self.signup_win.isVisible():
            self._drag_start_signup = self.signup_win.pos()
        else:
            self._drag_start_signup = None

    def do_drag(self, cursor_global: QPoint):
        """드래그 중: 커서 delta만큼 펫·채팅창을 함께 이동합니다."""
        if self._drag_start_cursor is None:
            return
        delta = cursor_global - self._drag_start_cursor
        new_pet = self._drag_start_pet + delta
        self.curr_x = float(new_pet.x())
        self.curr_y = float(new_pet.y())
        self.move(new_pet)
        if self._drag_start_chat is not None:
            self.chat_win.move(self._drag_start_chat + delta)
        if self._drag_start_login is not None:
            self.login_win.move(self._drag_start_login + delta)
        if hasattr(self, '_drag_start_signup') and self._drag_start_signup is not None:
            if hasattr(self, 'signup_win'):
                self.signup_win.move(self._drag_start_signup + delta)

    def end_drag(self):
        """드래그 종료: 상태 초기화 후 자동이동 재개."""
        self._drag_active = False
        self._drag_start_cursor = None
        self._drag_start_pet = None
        self._drag_start_chat = None
        self._drag_start_login = None
        self._drag_start_signup = None
        self.timer.start(16)

    def interact_with_pet(self):
        if not self._logged_in:
            if self.login_win.isVisible():
                self.is_interacting = False
                self.login_win.hide()
            else:
                self.is_interacting = True
                pet_center_x = self.x() + (self.width() // 2)
                login_x = pet_center_x - (self.login_win.width() // 2)
                login_y = self.y() - self.login_win.height()
                self.login_win.move(login_x, login_y)
                self.login_win.show()
                self.login_win.email_input.setFocus()
            return

        self.is_interacting = not self.is_interacting
        if self.is_interacting:
            pet_center_x = self.x() + (self.width() // 2)
            chat_x = pet_center_x - (self.chat_win.width() // 2)
            chat_y = self.y() - self.chat_win.height()
            self.chat_win.move(chat_x, chat_y)
            self.chat_win.show()
            self.chat_win.input_field.setFocus()
        else:
            self.chat_win.hide()

    def _on_login_success(self):
        self._logged_in = True
        self.login_win.hide()
        self.is_interacting = True
        pet_center_x = self.x() + (self.width() // 2)
        chat_x = pet_center_x - (self.chat_win.width() // 2)
        chat_y = self.y() - self.chat_win.height()
        self.chat_win.move(chat_x, chat_y)
        self.chat_win.show()
        self.chat_win.input_field.setFocus()