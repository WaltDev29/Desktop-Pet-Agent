import json
import html
from PySide6.QtWidgets import QApplication
from app.chat_style import PET_MSG_FORMAT, USER_MSG_FORMAT, convert_markdown_to_html
from app.chat_gui import fit_bubble_size, render_thinking_html

class ChatResponseHandler:
    def __init__(self, window):
        self.window = window

    def handle(self, data: dict):
        if self.window.is_shutting_down:
            QApplication.instance().quit()
            return
            
        msg_type = data.get("type")
        payload = data.get("payload")
        
        if not payload:
            return
            
        # Session filtering (skip if not current session)
        session_bound_types = ["chat", "approval_request", "approval_response", "log", "token", "done", "status", "history_res"]
        if msg_type in session_bound_types:
            msg_session_id = payload.get("session_id")
            if msg_session_id and self.window.current_session.session_id and msg_session_id.lower() != self.window.current_session.session_id.lower():
                return
                
        if msg_type == "approval_request":
            self.window._streaming = False
            self.window._current_stream_text = ""
            self.window._current_node_name = None
            self.window.pending_tool_call_id = payload.get("tool_call_id")
            self.window.btn_area.setVisible(True)
            self.window.input_field.setEnabled(False)
            self.window.attach_btn.setEnabled(False)
            
            # Show approval message bubble
            message_text = payload.get("message", "승인이 필요합니다.")
            self.window._add_bubble(PET_MSG_FORMAT.format(text=f"⚠️ 승인 필요: {message_text}"), "pet")
            self.window.scrollToBottom()
            
        elif msg_type == "log":
            status = payload.get("status")
            if not status:
                return
                
            if status == "error":
                self.window.on_error_occurred(payload.get("message", "알 수 없는 오류가 발생했습니다."))
                
            elif status == "info":
                msg = payload.get("message", "")
                self.window._add_bubble(PET_MSG_FORMAT.format(text=f"ℹ️ 안내: {msg}"), "pet")
                self.window.scrollToBottom()
                
            elif status == "node_start":
                node_name = payload.get("node", "")
                self.window._current_node_name = node_name
                self.window._flush_thinking_buffer()
                
                if self.window._current_response_index is None:
                    self.window._current_response_index = len(self.window.bubble_widgets)
                    self.window._add_bubble(PET_MSG_FORMAT.format(text="생각 중..."), "pet")
                    
                if node_name == "aggregator":
                    # 최종 답변 생성 단계 진입 시 사고 과정을 박스로 감싸기 준비
                    thinking_content = "\n".join(self.window._thinking_logs)
                    thinking_html = convert_markdown_to_html(thinking_content) if thinking_content else ""
                    # 빈 스트리밍 텍스트와 함께 접혀있는 사고 과정 상자를 미리 렌더링
                    full_html = render_thinking_html("", thinking_html, expanded=False)
                    self.window._update_bubble(self.window._current_response_index, full_html)
                else:
                    self.window._thinking_logs.append(f"[⚙️ {node_name} 동작 중...]")
                    thinking_content = "\n".join(self.window._thinking_logs)
                    html_thinking = convert_markdown_to_html(f"```text\n{thinking_content}\n```")
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_thinking))
                self.window.scrollToBottom()
                
            elif status == "tool_start":
                self.window._flush_thinking_buffer()
                tool_name = payload.get("tool_name", "unknown")
                tool_input = payload.get("tool_input", "")
                tool_input_str = json.dumps(tool_input, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input) if tool_input else ""
                log_entry = f"[🛠️ 도구 호출: {tool_name}]"
                if tool_input_str: log_entry += f" 파라미터: {tool_input_str}"
                
                if self.window._current_response_index is None:
                    self.window._current_response_index = len(self.window.bubble_widgets)
                    self.window._add_bubble(PET_MSG_FORMAT.format(text="도구 실행 중..."), "pet")
                    
                self.window._thinking_logs.append(log_entry)
                thinking_content = "\n".join(self.window._thinking_logs)
                html_thinking = convert_markdown_to_html(f"```text\n{thinking_content}\n```")
                self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_thinking))
                self.window.scrollToBottom()
                
        elif msg_type == "token":
            chunk = payload.get("chunk", "")
            if self.window._current_response_index is None:
                self.window._current_response_index = len(self.window.bubble_widgets)
                self.window._add_bubble(PET_MSG_FORMAT.format(text="..."), "pet")
                
            if self.window._current_node_name == "aggregator":
                if not self.window._streaming:
                    self.window._streaming = True
                    self.window._current_stream_text = ""
                self.window._current_stream_text += chunk
                html_reply = convert_markdown_to_html(self.window._current_stream_text)
                
                # 이미 렌더링된 사고 과정 박스와 결합하여 표시
                thinking_content = "\n".join(self.window._thinking_logs)
                thinking_html = convert_markdown_to_html(thinking_content) if thinking_content else ""
                if thinking_html:
                    full_html = render_thinking_html(html_reply, thinking_html, expanded=False)
                    self.window._update_bubble(self.window._current_response_index, full_html)
                else:
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_reply))
            else:
                self.window._thinking_stream_buffer += chunk
                thinking_content = "\n".join(self.window._thinking_logs) + self.window._thinking_stream_buffer
                html_thinking = convert_markdown_to_html(f"```text\n{thinking_content}\n```")
                self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_thinking))
            self.window.scrollToBottom()
            
        elif msg_type == "done":
            self.window._flush_thinking_buffer()
            if self.window._current_node_name == "aggregator" and self.window._streaming:
                formatted_reply = self.window._current_stream_text
            else:
                formatted_reply = payload.get("message") or "처리 완료."
                
            html_reply = convert_markdown_to_html(formatted_reply)
            
            if self.window._current_response_index is not None:
                if self.window._thinking_logs:
                    thinking_content = "\n".join(self.window._thinking_logs)
                    thinking_html = convert_markdown_to_html(thinking_content)
                    full_html = render_thinking_html(html_reply, thinking_html, expanded=False)
                    
                    bubble = self.window.bubble_widgets[self.window._current_response_index]
                    bubble.setProperty("answer_html_content", html_reply)
                    bubble.setProperty("thinking_html_content", thinking_html)
                    bubble.setProperty("thinking_expanded", False)
                    bubble.setHtml(full_html)
                    fit_bubble_size(bubble, self.window.chat_scroll_area.viewport())
                    
                    # 스냅샷의 사고 과정 속성도 업데이트
                    self.window._update_bubble_thinking_properties(
                        self.window._current_response_index,
                        html_reply,
                        thinking_html,
                        False
                    )
                else:
                    self.window._update_bubble(self.window._current_response_index, PET_MSG_FORMAT.format(text=html_reply))
            else:
                self.window._add_bubble(PET_MSG_FORMAT.format(text=html_reply), "pet")
                
            self.window.scrollToBottom()
            self.window._reset_stream_state()
            self.window.input_field.setEnabled(True)
            self.window.attach_btn.setEnabled(True)
            self.window.input_field.setFocus()
            
        elif msg_type == "chat":
            msg_id = payload.get("message_id")
            if msg_id and msg_id in self.window.sent_message_ids:
                return
            
            role = payload.get("role", "user")
            text = payload.get("message", "")
            images = payload.get("images", [])
            
            formatted_text = text
            if images:
                for img in images:
                    formatted_text += f"\n\n![이미지]({img})"
            
            html_content = convert_markdown_to_html(formatted_text)
            
            if role == "user":
                self.window._add_bubble(USER_MSG_FORMAT.format(text=html_content), "user")
            else:
                self.window._add_bubble(PET_MSG_FORMAT.format(text=html_content), "pet")
            self.window.scrollToBottom()
            
        elif msg_type == "approval_response":
            approve = payload.get("approve", False)
            text = "✅ 승인합니다. (서버/앱 연동)" if approve else "❌ 거절합니다. (서버/앱 연동)"
            html_text = convert_markdown_to_html(text)
            self.window._add_bubble(USER_MSG_FORMAT.format(text=html_text), "user")
            self.window.scrollToBottom()
            
        elif msg_type == "session_sync":
            raw_sessions = payload.get("sessions", [])
            # sessions 필드가 str 리스트 또는 SessionItem 객체 리스트 모두 지원
            session_ids = []
            session_titles = {}  # session_id -> title 매핑
            for item in raw_sessions:
                if isinstance(item, str):
                    session_ids.append(item)
                elif isinstance(item, dict):
                    sid = item.get("session_id") or item.get("id")
                    if sid:
                        session_ids.append(sid)
                        title = item.get("title")
                        if title:
                            session_titles[sid] = title
                            
            old_current_id = self.window.current_session.session_id
            self.window.sync_session_list(session_ids, session_titles)
            
            # 처음 구동(최초 동기화) 시 또는 활성 세션이 변경된 경우 가장 최신(0번째) 세션 자동 로드
            if self.window._is_first_sync:
                self.window._is_first_sync = False
                if self.window.sessions:
                    latest_session = self.window.sessions[0]
                    if self.window.current_session.session_id != latest_session.session_id:
                        self.window._load_session(latest_session)
                    else:
                        if latest_session.session_id:
                            payload = {"type": "get_history", "payload": {"session_id": latest_session.session_id}}
                            self.window.chat_client.send_message(payload)
            else:
                # 서버 동기화 후 활성 세션이 변경되었거나(예: 복원된 세션이 서버에 없음) 이전에 세션이 없었던 경우 자동 로드
                if self.window.current_session.session_id and self.window.current_session.session_id != old_current_id:
                    self.window._load_session(self.window.current_session)
            
        elif msg_type == "session_created":
            sid = payload.get("session_id")
            self.window.add_session_to_list(sid)
            
        elif msg_type == "session_deleted":
            sid = payload.get("session_id")
            self.window.remove_session_from_list(sid)
            
        elif msg_type == "history_res":
            history = payload.get("history", [])
            self.window.render_history(history)
            # 첫 번째 사용자 메시지를 기반으로 현재 세션 제목 업데이트
            for m in history:
                role = m.get("role", "")
                # message 또는 content 키 모두 지원
                text = m.get("message") or m.get("content", "")
                if role == "user" and text:
                    self.window.current_session.update_title_from_message(text)
                    self.window._refresh_sidebar_item(self.window.current_session)
                    break
            
        elif msg_type == "status":
            is_busy = payload.get("status") == "busy"
            self.window.set_agent_busy(is_busy)
