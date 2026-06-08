import sys
import threading
import time
import requests
import uvicorn

from app import create_app
from app.pet_window import PetWindow, QApplication
from app.chat_window import ChatWindow
from app.chat_network import ChatSignaler # Not directly used but good for reference if needed elsewhere or to avoid import errors if main expects it.

AGENT_BASE_URL = "http://localhost:8001"

def check_auth_status() -> bool:
    try:
        response = requests.get(f"{AGENT_BASE_URL}/api/status", timeout=3)
        return response.json().get("is_logged_in", False)
    except Exception:
        return False

def run_ui(already_logged_in: bool = False):
    """별도 스레드에서 UI 실행"""
    app = QApplication(sys.argv)
    pet = PetWindow(already_logged_in=already_logged_in)
    pet.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # UI 시작 전 인증 상태 확인
    already_logged_in = check_auth_status()

    # UI를 별도 스레드에서 실행 (인증 상태 전달)
    print("[1/2] Starting Pet UI in thread...")
    ui_thread = threading.Thread(target=run_ui, args=(already_logged_in,), daemon=False)
    ui_thread.start()
    
    # UI가 시작될 때까지 대기
    time.sleep(2)
    
    # 이후 서버를 메인 스레드에서 실행
    print("[2/2] Starting Pet App Server...")
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)