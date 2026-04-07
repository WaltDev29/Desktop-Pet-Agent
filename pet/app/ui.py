# 아래 코드를 pet/ui.py에 붙여넣기.
import sys
import random
import requests
import threading
from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QMovie, QTextCursor

class ChatSignaler(QObject):
    response_received = Signal(str)
    error_occurred = Signal(str)

class ChatWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.ToolTip | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background:transparent; border:none;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; border-radius: 10px; border: none;")
        
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("무엇을 도와드릴까요?")
        self.input_field.setStyleSheet("background-color: white; color: black; border-radius: 5px; border: none;")
        self.input_field.returnPressed.connect(self.send_message)
        
        bottom_layout = QHBoxLayout()
        self.close_btn = QPushButton("종료")
        self.close_btn.setStyleSheet("background-color: #ff5555; color: white; border-radius: 5px; font-weight: bold; border: none;")
        self.close_btn.clicked.connect(QApplication.instance().quit)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.input_field)
        layout.addLayout(bottom_layout)
        self.resize(200, 200)
        
        self.signaler = ChatSignaler()
        self.signaler.response_received.connect(self.on_response_received)
        self.signaler.error_occurred.connect(self.on_error_occurred)
        
        self.web_ui_url = "http://localhost:8000"
        # 통신 최적화를 위해 세션 객체 생성
        self.session = requests.Session()

    def send_message(self):
        text = self.input_field.text()
        if text:
            self.chat_history.append(f"나: {text}")
            self.chat_history.append("펫: 생각 중...") # 상태 피드백 추가
            self.input_field.clear()
            self.input_field.setEnabled(False)
            
            thread = threading.Thread(target=self.send_to_api, args=(text,))
            thread.daemon = True
            thread.start()
    
    def send_to_api(self, message: str):
        try:
            # 서버(8000)의 타임아웃 120.0초에 맞춰 UI 타임아웃도 확장
            response = self.session.post(
                f"{self.web_ui_url}/chat",
                json={"message": message},
                timeout=120.0 
            )
            
            if response.status_code == 200:
                data = response.json()
                reply = data.get("response") or data.get("message") or str(data)
                self.signaler.response_received.emit(reply)
            else:
                error_msg = f"서버 오류 ({response.status_code})"
                self.signaler.error_occurred.emit(error_msg)
                
        except requests.exceptions.Timeout:
            self.signaler.error_occurred.emit("응답 시간이 너무 길어 중단되었습니다.")
        except Exception as e:
            self.signaler.error_occurred.emit(f"연결 오류 발생")
    
    def on_response_received(self, reply: str):
        """API 응답을 채팅창에 표시 (생각 중... 메시지 삭제 후 교체)"""
        cursor = self.chat_history.textCursor()
        
        # cursor.End가 아니라 클래스명인 QTextCursor.End를 사용해야 합니다.
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar() # 줄바꿈 문자 삭제
        
        self.chat_history.append(f"펫: {reply}")
        print(f"펫: {reply}")
        self.input_field.setEnabled(True)
        self.input_field.setFocus()
    
    def on_error_occurred(self, error: str):
        self.chat_history.append(f"시스템: {error}")
        self.input_field.setEnabled(True)
        self.input_field.setFocus()

# 생성자에서 기본 설정을 정의함.(펫 이미지, 이동속도, 이동 간격 등)
class PetWindow(QWidget):
    def __init__(self):
        super().__init__()
        
        # Qt.Tool 플래그 추가
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.NoDropShadowWindowHint) 
        
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent; border: 0px; outline: none;")
        self.setContentsMargins(0, 0, 0, 0)
        self.resize(50, 50) 

        # --- PetWindow의 __init__ 내부 ---
        self.setAttribute(Qt.WA_OpaquePaintEvent, False) # 불투명한 덧칠 방지

        # --- PetWindow의 __init__ 내부 ---
        self.setWindowOpacity(0.99) # 펫 윈도우에도 동일한 투명도 꼼수 적용
        self.setStyleSheet("""
            QWidget {
                background: transparent;
                border: 1px solid rgba(0, 0, 0, 0);
                outline: none;
            }
        """)
        
        self.pet_label = QLabel(self)
        self.pet_label.setAttribute(Qt.WA_TransparentForMouseEvents) 
        self.pet_label.setStyleSheet("background: transparent; border: 0px; outline: none;")
        
        self.pet_label.setGeometry(0, 0, 50, 50) 
        self.pet_label.setAlignment(Qt.AlignCenter)  
        self.pet_label.setScaledContents(True) 
        
        self.movie = QMovie("assets/pet.gif") 
        self.pet_label.setMovie(self.movie)
        self.movie.start()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_logic) # 16ms(60 FPS)마다 다음 위치로 이동.
        self.timer.start(16) 
        
        self.x_speed = 0.5
        self.y_speed = 0.5
        self.change_dir_timer = 0 # 방향 바꾸는 타이머
        
        screen_geo = self.screen().availableGeometry()
        self.curr_x = random.randint(0, screen_geo.width() - self.width())
        self.curr_y = screen_geo.height() // 2 + random.randint(0, screen_geo.height() // 2 - self.height())
        self.move(int(self.curr_x), int(self.curr_y))

        self.is_interacting = False 
        self.chat_win = ChatWindow() # 채팅창 객체 생성

    # 펫 랜덤 이동 로직
    def update_logic(self):
        if self.is_interacting:
            return 

        self.change_dir_timer += 1
        if self.change_dir_timer > 100: 
            self.x_speed = random.uniform(-1.0, 1.0)
            self.y_speed = random.uniform(-1.0, 1.0)
            self.change_dir_timer = 0

        screen_geo = self.screen().availableGeometry()
        
        self.curr_x += self.x_speed
        self.curr_y += self.y_speed

        if self.curr_x <= 0 or self.curr_x + self.width() >= screen_geo.width():
            self.x_speed *= -1
        if self.curr_y <= screen_geo.height() // 2 or self.curr_y + self.height() >= screen_geo.height():
            self.y_speed *= -1

        self.move(int(self.curr_x), int(self.curr_y))

    # 펫 클릭 이벤트
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.interact_with_pet()

    # 펫과 상호작용(정지 및 UI 표시 등) 이벤트
    def interact_with_pet(self):
        self.is_interacting = not self.is_interacting
        
        if self.is_interacting:
            self.chat_win.move(self.x() - 75, self.y() - 210)
            self.chat_win.show()
            self.chat_win.input_field.setFocus()
        else:
            self.chat_win.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    pet = PetWindow()
    pet.show()
    
    sys.exit(app.exec())