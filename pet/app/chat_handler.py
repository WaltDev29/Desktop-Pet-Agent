import json
from PySide6.QtWidgets import QApplication
from app.chat_style import convert_markdown_to_html
from app.chat_gui import fit_bubble_size, ThinkingWidget


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
            message_text = payload.get("message", "승인이 필요합니다.")
            self.window._add_bubble(f"⚠️ 승인 필요: {message_text}", "pet")
            self.window.scrollToBottom()

        elif msg_type == "log":
            status = payload.get("status")
            if not status:
                return
            if status == "error":
                self.window.on_error_occurred(payload.get("message", "알 수 없는 오류가 발생했습니다."))
            elif status == "info":
                msg = payload.get("message", "")
                self.window._add_bubble(f"ℹ️ 안내: {msg}", "pet")
                self.window.scrollToBottom()
            elif status == "node_start":
                node_name = payload.get("node", "")
                self.window._current_node_name = node_name
                self.window._flush_thinking_buffer()

                if self.window._current_response_index is None:
                    self.window._current_response_index = len(self.window.bubble_widgets)
                    self.window._add_bubble("생각 중...", "pet")

                if node_name == "aggregator":
                    thinking_content = "\n".join(self.window._thinking_logs)
                    thinking_html = convert_markdown_to_html(thinking_content) if thinking_content else ""
                    self._ensure_thinking_widget(thinking_html)
                    self.window._update_bubble(self.window._current_response_index, "")
                else:
                    self.window._thinking_logs.append(f"[⚙️ {node_name} 동작 중...]")
                    thinking_content = "\n".join(self.window._thinking_logs)
                    thinking_html = convert_markdown_to_html(thinking_content)
                    self._ensure_thinking_widget(thinking_html)
                    self.window._update_bubble(self.window._current_response_index, "생각 중...")
                self.window.scrollToBottom()

            elif status == "tool_start":
                self.window._flush_thinking_buffer()
                tool_name = payload.get("tool_name", "unknown")
                tool_input = payload.get("tool_input", "")
                tool_input_str = json.dumps(tool_input, ensure_ascii=False) if isinstance(tool_input, dict) else str(tool_input) if tool_input else ""
                log_entry = f"[🛠️ 도구 호출: {tool_name}]"
                if tool_input_str:
                    log_entry += f" 파라미터: {tool_input_str}"

                if self.window._current_response_index is None:
                    self.window._current_response_index = len(self.window.bubble_widgets)
                    self.window._add_bubble("도구 실행 중...", "pet")

                self.window._thinking_logs.append(log_entry)
                thinking_content = "\n".join(self.window._thinking_logs)
                thinking_html = convert_markdown_to_html(thinking_content)
                self._ensure_thinking_widget(thinking_html)
                self.window._update_bubble(self.window._current_response_index, "생각 중...")
                self.window.scrollToBottom()

        elif msg_type == "token":
            chunk = payload.get("chunk", "")
            if self.window._current_response_index is None:
                self.window._current_response_index = len(self.window.bubble_widgets)
                self.window._add_bubble("...", "pet")

            if self.window._current_node_name == "aggregator":
                if not self.window._streaming:
                    self.window._streaming = True
                    self.window._current_stream_text = ""
                self.window._current_stream_text += chunk
                self.window._update_bubble(
                    self.window._current_response_index,
                    convert_markdown_to_html(self.window._current_stream_text)
                )
            else:
                self.window._thinking_stream_buffer += chunk
                thinking_content = "\n".join(self.window._thinking_logs) + self.window._thinking_stream_buffer
                thinking_html = convert_markdown_to_html(thinking_content)
                self._ensure_thinking_widget(thinking_html)
                
                idx = self.window._current_response_index
                if idx is not None and idx < len(self.window.bubble_widgets):
                    tw = self.window.bubble_widgets[idx].property("thinking_widget")
                    if tw and not tw.is_expanded():
                        tw.set_expanded(True)

            self.window.scrollToBottom()

        elif msg_type == "done":
            self.window._flush_thinking_buffer()
            if self.window._current_node_name == "aggregator" and self.window._streaming:
                formatted_reply = self.window._current_stream_text
            else:
                formatted_reply = payload.get("message") or "처리 완료."

            html_reply = convert_markdown_to_html(formatted_reply)

            if self.window._current_response_index is not None:
                bubble = self.window.bubble_widgets[self.window._current_response_index]
                bubble.setHtml(html_reply)
                fit_bubble_size(bubble, self.window.chat_scroll_area.viewport())

                if self.window._thinking_logs:
                    thinking_content = "\n".join(self.window._thinking_logs)
                    thinking_html = convert_markdown_to_html(thinking_content)
                    self._ensure_thinking_widget(thinking_html)
                    
                    tw = bubble.property("thinking_widget")
                    if tw:
                        tw.set_expanded(False)

                    self.window._update_bubble_thinking_properties(
                        self.window._current_response_index, html_reply, thinking_html, False
                    )
            else:
                self.window._add_bubble(html_reply, "pet")

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
            self.window._add_bubble(html_content, "user" if role == "user" else "pet")
            self.window.scrollToBottom()

        elif msg_type == "approval_response":
            approve = payload.get("approve", False)
            text = "✅ 승인합니다. (서버/앱 연동)" if approve else "❌ 거절합니다. (서버/앱 연동)"
            self.window._add_bubble(convert_markdown_to_html(text), "user")
            self.window.scrollToBottom()

        elif msg_type == "session_sync":
            raw_sessions = payload.get("sessions", [])
            session_ids = []
            session_titles = {}
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
            for m in history:
                role = m.get("role", "")
                text = m.get("message") or m.get("content", "")
                if role == "user" and text:
                    self.window.current_session.update_title_from_message(text)
                    self.window._refresh_sidebar_item(self.window.current_session)
                    break

        elif msg_type == "status":
            is_busy = payload.get("status") == "busy"
            self.window.set_agent_busy(is_busy)

    def _ensure_thinking_widget(self, thinking_html: str):
        """현재 스트리밍 버블에 ThinkingWidget이 없으면 새로 추가하고, 있으면 업데이트합니다."""
        idx = self.window._current_response_index
        if idx is None or idx >= len(self.window.bubble_widgets):
            return
        bubble = self.window.bubble_widgets[idx]
        tw = bubble.property("thinking_widget")
        if tw is None and thinking_html:
            tw = ThinkingWidget(thinking_html)
            tw.make_transparent()

            bubble_frame = bubble.property("bubble_frame")
            if bubble_frame:
                layout = bubble_frame.layout()
                layout.insertWidget(0, tw)
            else:
                container = bubble.property("container_widget")
                if container:
                    layout = container.layout()
                    layout.insertWidget(layout.count() - 1, tw)

            bubble.setProperty("thinking_widget", tw)
            fit_bubble_size(bubble, self.window.chat_scroll_area.viewport())
        elif tw is not None and thinking_html:
            tw.update_thinking(thinking_html)
            fit_bubble_size(bubble, self.window.chat_scroll_area.viewport())
