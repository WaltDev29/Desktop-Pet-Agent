import threading
import json

from PySide6.QtCore import QObject, Signal

class ChatSignaler(QObject):
    response_received = Signal(dict)
    error_occurred = Signal(str)

class ChatClient(QObject):
    def __init__(self, ws_url="ws://localhost:8000/ws", parent=None):
        super().__init__(parent)
        self.ws_url = ws_url
        self.signaler = ChatSignaler()
        self.session_id = None
        self.ws_conn = None
        self._ws_lock = threading.Lock()
        self._is_running = True
        self._start_websocket_thread()

    def _start_websocket_thread(self):
        thread = threading.Thread(target=self._websocket_worker, daemon=True)
        thread.start()

    def _websocket_worker(self):
        from websockets.sync.client import connect
        try:
            with connect(self.ws_url) as websocket:
                with self._ws_lock:
                    self.ws_conn = websocket
                
                # Listen continuously
                while self._is_running:
                    try:
                        message = websocket.recv()
                        data = json.loads(message)
                        self.signaler.response_received.emit(data)
                    except Exception as e:
                        if self._is_running:
                            print(f"WebSocket 닫힘 또는 수신 에러: {e}")
                        break
        except Exception as e:
            if self._is_running:
                self.signaler.error_occurred.emit(f"WebSocket 서버 연결 실패: {e}")
        finally:
            with self._ws_lock:
                self.ws_conn = None

    def send_message(self, payload: dict):
        if self.session_id:
            payload["session_id"] = self.session_id
        
        def _do_send():
            with self._ws_lock:
                if self.ws_conn:
                    try:
                        self.ws_conn.send(json.dumps(payload))
                    except Exception as e:
                        self.signaler.error_occurred.emit(f"메시지 전송 실패: {e}")
                else:
                    self.signaler.error_occurred.emit("서버와 연결되어 있지 않습니다. 다시 실행해주세요.")

        threading.Thread(target=_do_send, daemon=True).start()

    def close(self):
        self._is_running = False
        with self._ws_lock:
            if self.ws_conn:
                try:
                    self.ws_conn.close()
                except Exception:
                    pass
