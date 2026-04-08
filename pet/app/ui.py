import sys
import random
import requests
import threading
from typing import Optional

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtGui import QMovie, QTextCursor

class ChatSignaler(QObject):
    response_received = Signal(dict) # 응답 데이터를 dict 형태로 전달
    error_occurred = Signal(str)

class ChatWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        layout = QVBoxLayout(self)
        # layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; border-radius: 10px;")
        
        # --- [추가] 승인/거절 버튼 영역 ---
        self.action_area = QWidget()
        self.action_layout = QHBoxLayout(self.action_area)
        self.action_layout.setContentsMargins(5, 2, 5, 2)
        
        self.approve_btn = QPushButton("승인")
        self.reject_btn = QPushButton("거절")
        
        btn_base_style = "color: white; border-radius: 5px; font-weight: bold; padding: 5px;"
        self.approve_btn.setStyleSheet(f"background-color: #4CAF50; {btn_base_style}")
        self.reject_btn.setStyleSheet(f"background-color: #F44336; {btn_base_style}")
        
        self.approve_btn.clicked.connect(lambda: self.process_action("approved"))
        self.reject_btn.clicked.connect(lambda: self.process_action("rejected"))
        
        self.action_layout.addWidget(self.approve_btn)
        self.action_layout.addWidget(self.reject_btn)
        self.action_area.hide() # 기본적으로 숨김
        # --------------------------------

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("무엇을 도와드릴까요?")
        self.input_field.setStyleSheet("background-color: white; color: black; border-radius: 5px; outline: none;")
        self.input_field.returnPressed.connect(self.send_message)
        
        bottom_layout = QHBoxLayout()
        self.close_btn = QPushButton("종료")
        self.close_btn.setStyleSheet("background-color: #ff5555; color: white; border-radius: 5px; font-weight: bold;")
        self.close_btn.clicked.connect(QApplication.instance().quit)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.action_area) # 레이아웃에 추가
        layout.addWidget(self.input_field)
        layout.addLayout(bottom_layout)
        self.resize(200, 250) # 버튼 영역 고려하여 세로 크기 조정
        
        self.signaler = ChatSignaler()
        self.signaler.response_received.connect(self.on_response_received)
        self.signaler.error_occurred.connect(self.on_error_occurred)

        self.pending_tool_call_id = None
        
        self.web_ui_url = "http://localhost:8000"
        self.session = requests.Session()

    def send_message(self):
        text = self.input_field.text()
        if text:
            self.chat_history.append(f"나: {text}")
            self.chat_history.append("펫: 생각 중...")
            self.input_field.clear()
            self.input_field.setEnabled(False)
            
            thread = threading.Thread(target=self.send_to_api, args=(text,))
            thread.daemon = True
            thread.start()
    
    def send_to_api(self, data_input, endpoint="/chat"):
        try:
            # 입력이 문자열(채팅)이면 dict로 변환, 이미 dict(승인)면 그대로 사용
            json_data = {"message": data_input} if isinstance(data_input, str) else data_input
            
            response = self.session.post(
                f"{self.web_ui_url}{endpoint}",
                json=json_data,
                timeout=120.0 
            )
            
            if response.status_code == 200:
                data = response.json()
                self.signaler.response_received.emit(data)
            else:
                self.signaler.error_occurred.emit(f"서버 오류 ({response.status_code})")
                
        except Exception as e:
            self.signaler.error_occurred.emit(f"연결 오류 발생")
    
    def on_response_received(self, data: dict):
        """서버 응답 처리 및 승인 필요 시 ID 저장"""
        # '생각 중...' 메시지 지우기
        cursor = self.chat_history.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.select(QTextCursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.deletePreviousChar()
        
        reply = data.get("response") or data.get("message") or str(data)
        self.chat_history.append(f"펫: {reply}")
        
        # [중요] 서버가 보낸 tool_call_id를 추출해서 저장해둡니다.
        self.pending_tool_call_id = data.get("tool_call_id")
        
        if data.get("status") == "approval_required":
            self.action_area.show() # 승인/거절 버튼 표시
            self.input_field.setEnabled(False) 
        else:
            self.input_field.setEnabled(True)
            self.input_field.setFocus()

    def process_action(self, choice: str):
        """승인/거절 버튼 클릭 시 ID와 함께 서버로 전송"""
        self.action_area.hide()
        is_approved = (choice == "approved")
        choice_text = "승인" if is_approved else "거절"
        
        self.chat_history.append(f"나: [{choice_text}] 하겠어.")
        self.chat_history.append("펫: 결과를 서버에 전달하는 중...")

        # 서버 ApprovalRequest(BaseModel) 규격에 100% 맞춘 데이터 구성
        payload = {
            "approve": is_approved,
            "tool_call_id": self.pending_tool_call_id
        }

        # /approve 엔드포인트로 비동기 전송
        thread = threading.Thread(target=self.send_to_api, args=(payload, "/approve"))
        thread.daemon = True
        thread.start()

    def on_error_occurred(self, error: str):
            """에러 발생 시 채팅창에 표시하고 입력창을 다시 활성화"""
            # '생각 중...' 혹은 '처리 중...' 메시지 삭제 (필요 시)
            self.chat_history.append(f"시스템: {error}")
            self.input_field.setEnabled(True)
            self.input_field.setFocus()

class PetWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.SplashScreen) 
        self.setAttribute(Qt.WA_TranslucentBackground) 
        self.resize(50, 50) 

        self.pet_label = QLabel(self)
        self.pet_label.setAttribute(Qt.WA_TransparentForMouseEvents) 
        
        self.pet_label.setGeometry(0, 0, 50, 50) 
        self.pet_label.setAlignment(Qt.AlignCenter)  
        self.pet_label.setScaledContents(True) 
        
        self.movie = QMovie("assets/pet.gif") 
        self.pet_label.setMovie(self.movie)
        self.movie.start()

        screen_geo = self.screen().availableGeometry()
        width = screen_geo.width()
        height = screen_geo.height()
        
        self.min_x = width * 0.3
        self.max_x = width * 0.7 - self.width()
        
        self.min_y = height * 0.7
        self.max_y = height * 0.95 - self.height()

        self.curr_x = random.uniform(self.min_x, self.max_x)
        self.curr_y = random.uniform(self.min_y, self.max_y)
        self.move(int(self.curr_x), int(self.curr_y))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_logic)
        self.timer.start(16) 
        
        self.x_speed = 0.5
        self.y_speed = 0.5
        self.change_dir_timer = 0 

        self.is_interacting = False 
        self.chat_win = ChatWindow()

    def update_logic(self):
        if self.is_interacting: return 
        
        self.change_dir_timer += 1
        if self.change_dir_timer > 100: 
            self.x_speed = random.uniform(-1.0, 1.0)
            self.y_speed = random.uniform(-1.0, 1.0)
            self.change_dir_timer = 0

        self.curr_x += self.x_speed
        self.curr_y += self.y_speed

        if self.curr_x <= self.min_x or self.curr_x >= self.max_x:
            self.x_speed *= -1
            self.curr_x = max(self.min_x, min(self.curr_x, self.max_x))
        if self.curr_y <= self.min_y or self.curr_y >= self.max_y:
            self.y_speed *= -1
            self.curr_y = max(self.min_y, min(self.curr_y, self.max_y))

        self.move(int(self.curr_x), int(self.curr_y))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.interact_with_pet()

    def interact_with_pet(self):
        self.is_interacting = not self.is_interacting
        if self.is_interacting:
            self.chat_win.move(self.x() - 75, self.y() - 260)
            self.chat_win.show()
            self.chat_win.input_field.setFocus()
        else:
            self.chat_win.hide()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    app.setStyle("windows")

    pet = PetWindow()
    pet.show()
    sys.exit(app.exec())