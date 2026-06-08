import random
from PySide6.QtWidgets import QWidget, QLabel, QApplication
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QMovie, QPainter

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

class DirectionalPetLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.movie = None
        self.h_flip = False

    def setMovie(self, movie):
        self.movie = movie
        if self.movie:
            self.movie.frameChanged.connect(self.update)

    def paintEvent(self, event):
        painter = QPainter(self)
        if self.movie:
            pixmap = self.movie.currentPixmap()
            if not pixmap.isNull():
                painter.save()
                if self.h_flip:
                    # 가로축 기준 반전 (오른쪽 이동 시 반전)
                    painter.scale(-1, 1)
                    painter.translate(-self.width(), 0)
                # 라벨 위젯의 사각형 영역 크기에 픽스맵을 맞추어 그림
                painter.drawPixmap(self.rect(), pixmap)
                painter.restore()
                return
        super().paintEvent(event)

class PetWindow(QWidget):
    def __init__(self, already_logged_in: bool = False):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen) 
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.resize(PET_WIDTH, PET_HEIGHT) 

        self.pet_label = DirectionalPetLabel(self)
        self.pet_label.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.pet_label.setGeometry(0, 0, PET_WIDTH, PET_HEIGHT) 
        self.pet_label.setAlignment(Qt.AlignCenter)  
        self.pet_label.setScaledContents(True) 
        
        self.movie = QMovie(PET_MOVIE_PATH) 
        self.pet_label.setMovie(self.movie)
        self.movie.start()

        screen_geo = self.screen().availableGeometry()
        width, height = screen_geo.width(), screen_geo.height()
        
        self.min_x = width * MOVEMENT_X_MIN_RATIO
        self.max_x = width * MOVEMENT_X_MAX_RATIO - self.width()
        self.min_y = height * MOVEMENT_Y_MIN_RATIO
        self.max_y = height * MOVEMENT_Y_MAX_RATIO - self.height()

        self.curr_x = random.uniform(self.min_x, self.max_x)
        self.curr_y = random.uniform(self.min_y, self.max_y)
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

        if already_logged_in:
            QTimer.singleShot(100, self._on_login_success)

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

        # 이동 방향에 맞춰 좌우 반전 상태 설정
        if self.x_speed > 0:
            self.pet_label.h_flip = True
        elif self.x_speed < 0:
            self.pet_label.h_flip = False

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

    def end_drag(self):
        """드래그 종료: 상태 초기화 후 자동이동 재개."""
        self._drag_active = False
        self._drag_start_cursor = None
        self._drag_start_pet = None
        self._drag_start_chat = None
        self._drag_start_login = None
        self.timer.start(16)

    def interact_with_pet(self):
        if not self._logged_in:
            self.is_interacting = True
            pet_center_x = self.x() + (self.width() // 2)
            login_x = pet_center_x - (self.login_win.width() // 2)
            login_y = self.y() - self.login_win.height() - 15
            self.login_win.move(login_x, login_y)
            self.login_win.show()
            self.login_win.email_input.setFocus()
            return

        self.is_interacting = not self.is_interacting
        if self.is_interacting:
            pet_center_x = self.x() + (self.width() // 2)
            chat_x = pet_center_x - (self.chat_win.width() // 2)
            chat_y = self.y() - self.chat_win.height() - 15
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
        chat_y = self.y() - self.chat_win.height() - 15
        self.chat_win.move(chat_x, chat_y)
        self.chat_win.show()
        self.chat_win.input_field.setFocus()