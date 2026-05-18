import json
import html
from PySide6.QtWidgets import QApplication
from app.chat_style import PET_MSG_FORMAT, convert_markdown_to_html
from app.chat_gui import fit_bubble_size, render_thinking_html

class ChatResponseHandler:
    def __init__(self, window):
        self.window = window

    def handle(self, data: dict):
        if self.window.is_shutting_down:
            QApplication.instance().quit()
            return
            

        status = data.get("status")

        if status == "error":
            self.window.on_error_occurred(data.get("message", "알 수 없는 오류가 발생했습니다."))
            return

        elif status == "approval_required":
            self.window._streaming = False
            self.window._current_stream_text = ""
            self.window._current_node_name = None
            if data.get("session_id"):
                self.window.chat_client.session_id = data["session_id"]
            self.window.pending_tool_call_id = data.get("tool_call_id")
            self.window.btn_area.setVisible(True)
            self.window.input_field.setEnabled(False)
            self.window.attach_btn.setEnabled(False)
            return

        elif status == "node_start":
            node_name = data.get("node", "")
            self.window._current_node_name = node_name
            self.window._flush_thinking_buffer()
            if self.window._current_response_index is not None:
                if node_name == "aggregator":
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text="답변 생성 중..."))
                else:
                    self.window._thinking_logs.append(f"[⚙️ {node_name} 동작 중...]")
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text="생각 중..."))
                self.window.scrollToBottom()
            return

        elif status == "tool_start":
            self.window._flush_thinking_buffer()
            tool_name = data.get("tool_name", "unknown")
            tool_input = data.get("tool_input", "")
            tool_input_str = json.dumps(tool_input, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input) if tool_input else ""
            log_entry = f"[🛠️ 도구 호출: {tool_name}]"
            if tool_input_str: log_entry += f" 파라미터: {tool_input_str}"
            self.window._thinking_logs.append(log_entry)
            if self.window._current_response_index is not None:
                self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text="도구 실행 중..."))
                self.window.scrollToBottom()
            return

        elif status == "stream_chunk":
            chunk = data.get("chunk", "")
            if self.window._current_node_name == "aggregator":
                if not self.window._streaming:
                    self.window._streaming = True
                    self.window._current_stream_text = ""
                self.window._current_stream_text += chunk
                if self.window._current_response_index is not None:
                    html_reply = convert_markdown_to_html(self.window._current_stream_text)
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_reply))
                    self.window.scrollToBottom()
            else:
                self.window._thinking_stream_buffer += chunk
                if self.window._current_response_index is not None:
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text="생각 중..."))
                    self.window.scrollToBottom()
            return

        elif status in ("stream_end", "success"):
            if self.window._current_node_name == "aggregator":
                self.window._flush_thinking_buffer()
                if self.window._streaming:
                    self.window._streaming = False
                    formatted_reply = self.window._current_stream_text
                else:
                    reply = data.get("response") or data.get("message") or ""
                    formatted_reply = reply if reply else "생각 중..."

                html_reply = convert_markdown_to_html(formatted_reply)

                if self.window._thinking_logs and self.window._current_response_index is not None:
                    thinking_content = "\n".join(self.window._thinking_logs)
                    thinking_html = convert_markdown_to_html(thinking_content)
                    full_html = render_thinking_html(html_reply, thinking_html, expanded=False)
                    bubble = self.window.bubble_widgets[self.window._current_response_index]
                    bubble.setProperty("answer_html_content", html_reply)
                    bubble.setProperty("thinking_html_content", thinking_html)
                    bubble.setProperty("thinking_expanded", False)
                    bubble.setHtml(full_html)
                    fit_bubble_size(bubble, self.window.chat_scroll_area.viewport())
                elif self.window._current_response_index is not None:
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_reply))
                else:
                    self.window._add_bubble(PET_MSG_FORMAT.format(text=html_reply), "pet")
                self.window.scrollToBottom()
                self.window._current_stream_text = ""
                self.window._thinking_logs = []
                self.window._thinking_stream_buffer = ""
            else:
                self.window._streaming = False
                self.window._current_stream_text = ""
                self.window._flush_thinking_buffer()
            
            if data.get("session_id"):
                self.window.chat_client.session_id = data["session_id"]
            self.window._current_node_name = None
            self.window.input_field.setEnabled(True)
            self.window.attach_btn.setEnabled(True)
            self.window.input_field.setFocus()

        else:
            reply = data.get("response") or data.get("message") or str(data)
            html_reply = convert_markdown_to_html(reply)
            self.window._add_bubble(PET_MSG_FORMAT.format(text=html_reply), "pet")
            self.window.scrollToBottom()

        if data.get("session_id"):
            self.window.chat_client.session_id = data["session_id"]
        self.window.pending_tool_call_id = data.get("tool_call_id")
        
        is_waiting = (status == "approval_required")
        self.window.btn_area.setVisible(is_waiting)
        self.window.input_field.setEnabled(not is_waiting)
        self.window.attach_btn.setEnabled(not is_waiting)
        if not is_waiting: self.window.input_field.setFocus()
