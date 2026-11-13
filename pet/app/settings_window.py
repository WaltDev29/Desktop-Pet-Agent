import json
import os

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QPushButton,
    QGraphicsDropShadowEffect, QFrame, QMessageBox, QDialog,
    QTextEdit, QDialogButtonBox, QCheckBox, QLineEdit
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QColor, QFont
from app.chat_style import (
    CLOSE_BTN_STYLE,
    get_settings_window_style,
    get_settings_label_style,
    get_settings_slider_style,
    DARK_THEME,
)
import requests

CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "agent", "agent_server", "config.json"
)
ENV_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "agent", ".env"
)

class SettingsWindow(QWidget):
    def __init__(self, chat_window, pet_window=None):
        super().__init__(chat_window)
        self.chat_window = chat_window
        self.pet_window = pet_window

        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)

        self.container = QFrame(self)
        self.container.setObjectName("settings_container")
        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self.container)
        layout.setContentsMargins(20, 20, 20, 30)
        layout.setSpacing(15)

        self.title_label = QLabel("설정")
        self.title_label.setAlignment(Qt.AlignCenter)

        self.theme_label = QLabel("채팅창 테마:")
        theme_btn_layout = QHBoxLayout()
        theme_btn_layout.setSpacing(8)

        self.dark_theme_btn = QPushButton("다크")
        self.light_theme_btn = QPushButton("화이트")
        self.dark_theme_btn.clicked.connect(lambda: self._apply_theme("dark"))
        self.light_theme_btn.clicked.connect(lambda: self._apply_theme("light"))
        theme_btn_layout.addWidget(self.dark_theme_btn)
        theme_btn_layout.addWidget(self.light_theme_btn)

        self.chat_opacity_label = QLabel("채팅창 투명도:")
        self.chat_opacity_slider = QSlider(Qt.Horizontal)
        self.chat_opacity_slider.setRange(20, 100)
        self.chat_opacity_slider.setValue(int(self.chat_window.windowOpacity() * 100))
        self.chat_opacity_slider.valueChanged.connect(self.set_chat_opacity)

        self.pet_opacity_label = QLabel("펫 투명도:")
        self.pet_opacity_slider = QSlider(Qt.Horizontal)
        self.pet_opacity_slider.setRange(20, 100)
        pet_val = int(self.pet_window.windowOpacity() * 100) if self.pet_window else 100
        self.pet_opacity_slider.setValue(pet_val)
        self.pet_opacity_slider.valueChanged.connect(self.set_pet_opacity)

        self.close_btn = QPushButton("닫기")
        self.close_btn.setStyleSheet(CLOSE_BTN_STYLE)
        self.close_btn.clicked.connect(self.close)

        layout.addWidget(self.title_label)
        layout.addWidget(self.theme_label)
        layout.addLayout(theme_btn_layout)
        layout.addWidget(self.chat_opacity_label)
        layout.addWidget(self.chat_opacity_slider)
        layout.addWidget(self.pet_opacity_label)
        layout.addWidget(self.pet_opacity_slider)


        self.mcp_btn = QPushButton("mcp 설정 관리")
        self.mcp_btn.setStyleSheet("background-color: #2979B0; color: white; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 8px 16px;")
        self.mcp_btn.clicked.connect(self._manage_mcp_settings)
        layout.addWidget(self.mcp_btn)

        self.model_btn = QPushButton("모델 설정 관리")
        self.model_btn.setStyleSheet("background-color: #2979B0; color: white; border-radius: 8px; font-size: 13px; font-weight: bold; padding: 8px 16px;")
        self.model_btn.clicked.connect(self._manage_model_settings)
        layout.addWidget(self.model_btn)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        main_layout.addWidget(self.container)

        self.resize(260, 430)

        current_theme = getattr(self.chat_window, "_current_theme", DARK_THEME)
        self.update_theme(current_theme)

        geom = self.chat_window.geometry()
        self.move(geom.x() + geom.width() + 10, geom.y())

    def update_theme(self, theme: dict):
        is_dark = theme["name"] == "dark"

        self.container.setStyleSheet(get_settings_window_style(theme))

        label_style = get_settings_label_style(theme)
        slider_style = get_settings_slider_style(theme)

        title_color = "#E0E0E0" if is_dark else "#1A1A1A"
        self.title_label.setStyleSheet(
            f"font-size: 16px; font-weight: bold; margin-bottom: 10px; color: {title_color};"
        )

        self.theme_label.setStyleSheet(label_style)
        self.chat_opacity_label.setStyleSheet(label_style)
        self.pet_opacity_label.setStyleSheet(label_style)
        self.chat_opacity_slider.setStyleSheet(slider_style)
        self.pet_opacity_slider.setStyleSheet(slider_style)

        self._update_theme_buttons(theme)

    def _update_theme_buttons(self, theme: dict | None = None):
        if theme is None:
            theme = getattr(self.chat_window, "_current_theme", DARK_THEME)
        current = theme.get("name", "dark")
        is_dark = theme["name"] == "dark"

        _base = "border-radius: 8px; font-size: 12px; font-weight: bold; padding: 6px 14px;"
        active_style = f"background-color: #2979B0; color: white; {_base}"
        inactive_bg = "#3A3A3A" if is_dark else "#E0E0E0"
        inactive_color = "#CCCCCC" if is_dark else "#333333"
        inactive_style = f"background-color: {inactive_bg}; color: {inactive_color}; {_base}"

        self.dark_theme_btn.setStyleSheet(
            active_style if current == "dark" else inactive_style
        )
        self.light_theme_btn.setStyleSheet(
            active_style if current == "light" else inactive_style
        )

    def _apply_theme(self, theme_name: str):
        self.chat_window.apply_theme(theme_name)

    def set_chat_opacity(self, value):
        self.chat_window.setWindowOpacity(value / 100.0)

    def set_pet_opacity(self, value):
        if self.pet_window:
            self.pet_window.setWindowOpacity(value / 100.0)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_cursor_pos = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_start_cursor_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_cursor_pos
            self.move(self._drag_start_window_pos + delta)

    def mouseReleaseEvent(self, event):
        self._drag_start_cursor_pos = None
        self._drag_start_window_pos = None

    def _manage_mcp_settings(self):
        self.chat_window.setEnabled(False)
        self.setEnabled(False)

        editor = MCPConfigEditor(self)
        editor.finished.connect(self._on_mcp_editor_closed)
        editor.show()

    def _on_mcp_editor_closed(self):
        self.setEnabled(True)
        self.chat_window.setEnabled(True)
        self.raise_()
        self.activateWindow()

    def _manage_model_settings(self):
        self.chat_window.setEnabled(False)
        self.setEnabled(False)

        editor = ModelConfigEditor(self)
        editor.finished.connect(self._on_model_editor_closed)
        editor.show()

    def _on_model_editor_closed(self):
        self.setEnabled(True)
        self.chat_window.setEnabled(True)
        self.raise_()
        self.activateWindow()


class MCPConfigEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("MCP 설정 관리")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(540, 440)

        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._container = QFrame(self)
        self._container.setObjectName("mcp_editor_container")
        self._container.setStyleSheet("""
            QFrame#mcp_editor_container {
                background-color: #23272E;
                border-radius: 14px;
                border: 1px solid #3A3F4B;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 6)
        self._container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("⚙️  MCP 설정 (config.json)")
        title.setStyleSheet("color: #E0E0E0; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        hint = QLabel("JSON 형식으로 직접 편집할 수 있습니다. 저장 시 유효성 검사가 실행됩니다.")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._editor = QTextEdit()
        self._editor.setStyleSheet("""
            QTextEdit {
                background-color: #1A1D23;
                color: #ABB2BF;
                border: 1px solid #3A3F4B;
                border-radius: 8px;
                font-family: 'Courier New', monospace;
                font-size: 12.5px;
                padding: 10px;
                line-height: 1.5;
            }
        """)
        font = QFont("Courier New")
        font.setPointSize(11)
        self._editor.setFont(font)
        self._editor.setAcceptRichText(False)
        layout.addWidget(self._editor, 1)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px; padding: 2px 0;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._save_btn = QPushButton("저장")
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2979B0;
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1A5F8F; }
        """)
        self._save_btn.clicked.connect(self._save)

        self._cancel_btn = QPushButton("닫기")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3F4B;
                color: #CCCCCC;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #4A505E; }
        """)
        self._cancel_btn.clicked.connect(self.close)

        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        outer.addWidget(self._container)

        self._load()

    def _config_path(self) -> str:
        return os.path.normpath(CONFIG_PATH)

    def _load(self):
        path = self._config_path()
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = f.read()
            parsed = json.loads(raw)
            self._editor.setPlainText(json.dumps(parsed, indent=2, ensure_ascii=False))
            self._set_status("", ok=True)
        except FileNotFoundError:
            self._editor.setPlainText("{}")
            self._set_status(f"파일을 찾을 수 없습니다: {path}", ok=False)
        except json.JSONDecodeError as e:
            self._editor.setPlainText(raw)
            self._set_status(f"기존 파일이 올바른 JSON이 아닙니다: {e}", ok=False)

    def _save(self):
        text = self._editor.toPlainText().strip()
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            self._set_status(f"❌ JSON 오류: {e}", ok=False)
            return

        path = self._config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(parsed, f, indent=2, ensure_ascii=False)
            self._set_status("✅ 저장 완료!", ok=True)
        except Exception as e:
            self._set_status(f"❌ 저장 실패: {e}", ok=False)

    def _set_status(self, msg: str, ok: bool = True):
        color = "#4CAF50" if ok else "#FF6B6B"
        self._status_label.setStyleSheet(f"font-size: 11px; color: {color}; padding: 2px 0;")
        self._status_label.setText(msg)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_cursor_pos = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_start_cursor_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_cursor_pos
            self.move(self._drag_start_window_pos + delta)

    def mouseReleaseEvent(self, event):
        self._drag_start_cursor_pos = None
        self._drag_start_window_pos = None


class ModelConfigEditor(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("모델 설정 관리")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(440, 390)

        self._drag_start_window_pos = None
        self._drag_start_cursor_pos = None

        self.local_model = ""
        self.local_base_url = ""
        self.local_api_key = ""
        self.openai_model = ""
        self.openai_api_key = ""
        self.is_local = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)

        self._container = QFrame(self)
        self._container.setObjectName("model_editor_container")
        self._container.setStyleSheet("""
            QFrame#model_editor_container {
                background-color: #23272E;
                border-radius: 14px;
                border: 1px solid #3A3F4B;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(18)
        shadow.setColor(QColor(0, 0, 0, 120))
        shadow.setOffset(0, 6)
        self._container.setGraphicsEffect(shadow)

        layout = QVBoxLayout(self._container)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("🤖  모델 설정 (.env)")
        title.setStyleSheet("color: #E0E0E0; font-size: 14px; font-weight: bold;")
        layout.addWidget(title)

        self._local_checkbox = QCheckBox("로컬 모델")
        self._local_checkbox.setStyleSheet("""
            QCheckBox {
                color: #E0E0E0;
                font-size: 13px;
                font-weight: bold;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid #3A3F4B;
                background-color: #1A1D23;
            }
            QCheckBox::indicator:hover {
                border-color: #2979B0;
            }
            QCheckBox::indicator:checked {
                background-color: #2979B0;
                border-color: #2979B0;
            }
        """)
        self._local_checkbox.toggled.connect(self._on_local_toggled)
        layout.addWidget(self._local_checkbox)

        line_edit_style = """
            QLineEdit {
                background-color: #1A1D23;
                color: #E0E0E0;
                border: 1px solid #3A3F4B;
                border-radius: 8px;
                font-size: 12px;
                padding: 7px 10px;
            }
            QLineEdit:focus {
                border-color: #2979B0;
            }
        """
        label_style = "color: #CCCCCC; font-size: 12px; font-weight: bold;"

        self._model_label = QLabel("모델명:")
        self._model_label.setStyleSheet(label_style)
        self._model_edit = QLineEdit()
        self._model_edit.setStyleSheet(line_edit_style)
        layout.addWidget(self._model_label)
        layout.addWidget(self._model_edit)

        self._base_url_container = QWidget()
        base_url_layout = QVBoxLayout(self._base_url_container)
        base_url_layout.setContentsMargins(0, 0, 0, 0)
        base_url_layout.setSpacing(4)

        self._base_url_label = QLabel("Base URL:")
        self._base_url_label.setStyleSheet(label_style)
        self._base_url_edit = QLineEdit()
        self._base_url_edit.setStyleSheet(line_edit_style)
        base_url_layout.addWidget(self._base_url_label)
        base_url_layout.addWidget(self._base_url_edit)
        layout.addWidget(self._base_url_container)

        self._api_key_label = QLabel("API Key:")
        self._api_key_label.setStyleSheet(label_style)
        self._api_key_edit = QLineEdit()
        self._api_key_edit.setStyleSheet(line_edit_style)
        layout.addWidget(self._api_key_label)
        layout.addWidget(self._api_key_edit)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 11px; padding: 2px 0;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._save_btn = QPushButton("저장")
        self._save_btn.setStyleSheet("""
            QPushButton {
                background-color: #2979B0;
                color: white;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #1A5F8F; }
        """)
        self._save_btn.clicked.connect(self._save)

        self._cancel_btn = QPushButton("닫기")
        self._cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3F4B;
                color: #CCCCCC;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 24px;
            }
            QPushButton:hover { background-color: #4A505E; }
        """)
        self._cancel_btn.clicked.connect(self.close)

        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        outer.addWidget(self._container)

        self._load()

    def _env_path(self) -> str:
        return os.path.normpath(ENV_PATH)

    def _read_env_dict(self) -> dict:
        env_vars = {}
        path = self._env_path()
        if not os.path.exists(path):
            return env_vars
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, v = s.split("=", 1)
                v_clean = v.split("#")[0].strip()
                env_vars[k.strip()] = v_clean
        return env_vars

    def _load(self):
        env = self._read_env_dict()
        use_openai = env.get("USE_OPENAI", "false").lower() == "true"
        self.is_local = not use_openai

        self.local_model = env.get("API_MODEL", "")
        self.local_base_url = env.get("API_BASE_URL", "")
        self.local_api_key = env.get("LOCAL_API_KEY", "")

        self.openai_model = env.get("OPENAI_MODEL", "gpt-4o-mini")
        self.openai_api_key = env.get("API_KEY", "")

        self._local_checkbox.blockSignals(True)
        self._local_checkbox.setChecked(self.is_local)
        self._local_checkbox.blockSignals(False)

        self._update_fields()

    def _on_local_toggled(self, checked: bool):
        if self.is_local:
            self.local_model = self._model_edit.text().strip()
            self.local_base_url = self._base_url_edit.text().strip()
            self.local_api_key = self._api_key_edit.text().strip()
        else:
            self.openai_model = self._model_edit.text().strip()
            self.openai_api_key = self._api_key_edit.text().strip()

        self.is_local = checked
        self._update_fields()

    def _update_fields(self):
        if self.is_local:
            self._model_edit.setText(self.local_model)
            self._base_url_edit.setText(self.local_base_url)
            self._api_key_edit.setText(self.local_api_key)
            self._base_url_container.setVisible(True)
        else:
            self._model_edit.setText(self.openai_model)
            self._api_key_edit.setText(self.openai_api_key)
            self._base_url_container.setVisible(False)
        self._set_status("", ok=True)

    def _save(self):
        path = self._env_path()
        if self.is_local:
            self.local_model = self._model_edit.text().strip()
            self.local_base_url = self._base_url_edit.text().strip()
            self.local_api_key = self._api_key_edit.text().strip()
            updates = {
                "USE_OPENAI": "False",
                "API_MODEL": self.local_model,
                "API_BASE_URL": self.local_base_url,
                "LOCAL_API_KEY": self.local_api_key,
            }
        else:
            self.openai_model = self._model_edit.text().strip()
            self.openai_api_key = self._api_key_edit.text().strip()
            updates = {
                "USE_OPENAI": "True",
                "OPENAI_MODEL": self.openai_model,
                "API_KEY": self.openai_api_key,
            }

        try:
            lines = []
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            updated_keys = set()
            new_lines = []
            for line in lines:
                s = line.strip()
                matched_key = None
                if s and not s.startswith("#") and "=" in s:
                    k = s.split("=", 1)[0].strip()
                    if k in updates:
                        matched_key = k

                if matched_key:
                    comment = ""
                    if "#" in line:
                        parts = line.split("#", 1)
                        if len(parts) > 1 and "=" in parts[0]:
                            comment = " #" + parts[1].rstrip("\r\n")
                    new_lines.append(f"{matched_key}={updates[matched_key]}{comment}\n")
                    updated_keys.add(matched_key)
                else:
                    new_lines.append(line)

            for k, v in updates.items():
                if k not in updated_keys:
                    new_lines.append(f"{k}={v}\n")

            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)

            for k, v in updates.items():
                os.environ[k] = v

            self._set_status("✅ .env에 저장 완료!", ok=True)
        except Exception as e:
            self._set_status(f"❌ 저장 실패: {e}", ok=False)

    def _set_status(self, msg: str, ok: bool = True):
        color = "#4CAF50" if ok else "#FF6B6B"
        self._status_label.setStyleSheet(f"font-size: 11px; color: {color}; padding: 2px 0;")
        self._status_label.setText(msg)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_cursor_pos = event.globalPosition().toPoint()
            self._drag_start_window_pos = self.pos()

    def mouseMoveEvent(self, event):
        if self._drag_start_cursor_pos is not None:
            delta = event.globalPosition().toPoint() - self._drag_start_cursor_pos
            self.move(self._drag_start_window_pos + delta)

    def mouseReleaseEvent(self, event):
        self._drag_start_cursor_pos = None
        self._drag_start_window_pos = None
