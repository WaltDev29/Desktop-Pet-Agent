import sys # 윈도우 위에서 움직이게 하기 위함.
import random # 랜덤한 위치로 이동시키기 위함.

# PySide6 - CLI 상으로 결과 나오는게 아닌 UI 형태로 결과가 나오게 하기 위함.
from PySide6.QtWidgets import QApplication, QWidget, QLabel, QLineEdit, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QMovie # GIF 사용을 위해 추가

# 채팅창 인터페이스 클래스
class ChatWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # 채팅창 설정(기존 채팅도 보이게 설정)
        layout = QVBoxLayout(self)
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; border-radius: 10px;")
        
        # 채팅 입력창 설정
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("무엇을 도와드릴까요?")
        self.input_field.setStyleSheet("background-color: white; border-radius: 5px;")
        self.input_field.returnPressed.connect(self.send_message)
        
        # 하단 종료 버튼 레이아웃 추가
        bottom_layout = QHBoxLayout()
        self.close_btn = QPushButton("종료")
        self.close_btn.setStyleSheet("background-color: #ff5555; color: white; border-radius: 5px; font-weight: bold;")
        self.close_btn.clicked.connect(QApplication.instance().quit)
        
        bottom_layout.addStretch() # 입력창과 종료 버튼 사이 간격 조절용
        bottom_layout.addWidget(self.close_btn)

        layout.addWidget(self.chat_history)
        layout.addWidget(self.input_field)
        layout.addLayout(bottom_layout)
        self.resize(200, 200)

    def send_message(self):
        text = self.input_field.text()
        if text:
            # 입력된 텍스트를 터미널에 출력
            print(f"[사용자 입력]: {text}")
            
            self.chat_history.append(f"나: {text}")
            self.input_field.clear()
            self.chat_history.append(f"펫: 명령을 접수했습니다!") 

# 생성자에서 기본 설정을 정의함.(펫 이미지, 이동속도, 이동 간격 등)
class PetWindow(QWidget):
    # QWidget을 자료형?으로 하는 클래스가 생성되고, 이 클래스에 대한 속성은 self.~ 식으로 정의함.
    def __init__(self):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint) # 테두리 제거(투명화)
        
        self.setAttribute(Qt.WA_TranslucentBackground) # 배경색 투명화
        self.resize(50, 50) # 펫이 차지하는 영역의 크기 설정
        
        # QtWidget의 QLabel 활용하여 펫의 모습 정의
        self.pet_label = QLabel(self)
        self.pet_label.setAttribute(Qt.WA_TransparentForMouseEvents) 
        
        self.pet_label.setGeometry(0, 0, 50, 50) # 이미지 크기 조정(정확히는 geometry 자체가 (x,y,w,h) 순으로 배치하는 것인데, 이걸 통해 크기 조정)
        self.pet_label.setAlignment(Qt.AlignCenter)  # 이미지를 상자 안에 어디 배치할 지(우리는 당연히 정중앙)
        self.pet_label.setScaledContents(True) # gif 크기를 영역에 맞춤
        
        # GIF 설정
        self.movie = QMovie("assets/pet.gif") # 움직이는 이미지/영상을 지정하기 위해 QMovie 형태로 설정. gif도 이걸로 붙여야함.
        self.pet_label.setMovie(self.movie) # QMovie 형태로 입힐 movie를 gif로 지정한다.
        self.movie.start() # 그 gif를 재생 상태로 함. 지금은 상관없지만, 나중에 혹시나 영상 기반으로 붙이게 되면 필요할 때만 start하는게 좋음.

        # 임시 텍스트 (GIF가 없을 때를 대비) # 여길 나중에 if문 등을 써서 gif 파일을 찾을 수 없을 때 알아서 나오게끔
        # self.pet_label.setText("움직이는 펫")
        # self.pet_label.setStyleSheet("color: white; font-weight: bold;")

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_logic) # 16ms마다 다음 위치로 이동.
        self.timer.start(16) # 16ms면 약 60 FPS라는 의미.
        
        # x축/y축 이동속도
        self.x_speed = 0.5
        self.y_speed = 0.5
        self.change_dir_timer = 0 # 방향 바꾸는 타이머
        
        # 소수점 위치를 기억하기 위한 변수(이동하기 전 위치를 기억한다는 의미인가? 그걸 토대로 다음 이동 지점을 랜덤값 기반으로 정하는거고.)
        self.curr_x = float(self.x()) 
        self.curr_y = float(self.y()) 

        self.is_interacting = False 
        self.chat_win = ChatWindow() # 채팅창 객체 생성

    def update_logic(self):
        if self.is_interacting:
            return 

        # 일정 시간마다 무작위로 방향 전환
        self.change_dir_timer += 1
        if self.change_dir_timer > 100: 
            # 속도를 너무 크게 잡지 않도록 수정 (0.5 ~ 1.5 사이)
            # 이동방향 바꾸는 타이머가 100틱(=16ms * 100이므로 1.6초)을 넘어가면, 속도를 초기화함
            self.x_speed = random.uniform(-1.0, 1.0)
            self.y_speed = random.uniform(-1.0, 1.0)
            self.change_dir_timer = 0

        # 전체 화면 크기 파악
        screen_geo = self.screen().availableGeometry()
        
        # 현재 위치에 speed(사실상 이동 거리)만큼 이동함
        self.curr_x += self.x_speed
        self.curr_y += self.y_speed

        # 현재 위치가 윈도우 범위 넘어가지 않게 함.
        if self.curr_x <= 0 or self.curr_x + self.width() >= screen_geo.width():
            self.x_speed *= -1
        if self.curr_y <= 0 or self.curr_y + self.height() >= screen_geo.height():
            self.y_speed *= -1

        # 최종 이동은 정수로 변환하여 수행(계산 자체는 소수점으로 하되, 최종 이동 거리는 정수로 변환해 넣어준다는거 같음)
        self.move(int(self.curr_x), int(self.curr_y))

    # 펫 클릭 이벤트
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.interact_with_pet()

    # 펫을 선택하면, 상호작용 모드로 전환해 이동을 잠시 멈춤.
    def interact_with_pet(self):
        self.is_interacting = not self.is_interacting
        
        if self.is_interacting:
            # 펫 머리 위에 채팅창 배치
            self.chat_win.move(self.x() - 75, self.y() - 210)
            self.chat_win.show()
            self.chat_win.input_field.setFocus()
        else:
            self.chat_win.hide()

if __name__ == "__main__":
    # 여기서 app/pet 선언해두는게 무슨 의미이지?
    app = QApplication(sys.argv) # 대충 프로젝트가 시작된다는 의미.
    pet = PetWindow() # 우리가 위에서 만든 pet을 화면 위에 배치
    pet.show() # 하고 보여지게 함
    
    sys.exit(app.exec())