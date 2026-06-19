MAIN_CONTAINER_STYLE = """
QFrame#main_container {
    background-color: #FFFFFF;
    border: 1px solid #D1D1D1;
    border-radius: 20px;
}
"""

import html

FONT_FAMILY = "'Inter', 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕'"

# ── QTextDocument 전용 마크다운 스타일시트 ──
# setDefaultStyleSheet()로 주입되어 HTML 뼈대에 스타일을 입힘
MARKDOWN_CSS = f"""
    body {{
        font-family: {FONT_FAMILY};
        font-size: 13px;
        line-height: 1.6;
        color: #111111;
        margin: 0;
        padding: 0;
    }}
    p {{ margin: 2px 0; }}
    strong {{ font-weight: bold; }}
    em {{ font-style: italic; }}
    a {{ color: #1a73e8; text-decoration: underline; }}
    code {{
        font-family: 'Courier New', Courier, monospace;
        font-size: 12px;
        background-color: #f0f0f0;
        color: #c0392b;
        padding: 1px 4px;
    }}
    pre {{
        font-family: 'Courier New', Courier, monospace;
        font-size: 12px;
        background-color: #2b2b2b;
        color: #f8f8f2;
        padding: 8px;
        margin: 4px 0;
    }}
    ul {{ margin: 4px 0; padding-left: 18px; }}
    ol {{ margin: 4px 0; padding-left: 18px; }}
    li {{ margin: 2px 0; }}
    table {{ border-collapse: collapse; margin: 6px 0; }}
    th {{ border: 1px solid #cccccc; padding: 4px 8px; background-color: #eeeeee; font-weight: bold; }}
    td {{ border: 1px solid #cccccc; padding: 4px 8px; }}
    h1, h2 {{ font-size: 14px; font-weight: bold; margin: 4px 0; }}
    h3, h4 {{ font-size: 13px; font-weight: bold; margin: 4px 0; }}
"""

try:
    import markdown
    _HAS_MARKDOWN = True
except ImportError:
    _HAS_MARKDOWN = False

def convert_markdown_to_html(md_text: str) -> str:
    """마크다운 텍스트를 순수 HTML 구조로 변환합니다. (스타일은 MARKDOWN_CSS가 담당)"""
    if not _HAS_MARKDOWN:
        safe_text = html.escape(md_text).replace('\n', '<br>')
        return safe_text

    html_content = markdown.markdown(
        md_text,
        extensions=['nl2br', 'extra', 'tables', 'fenced_code']
    )
    return html_content.strip()


CHAT_HISTORY_STYLE = f"""
QTextEdit {{
    background-color: #222222;
    border: none;
    color: #333333;
    font-family: {FONT_FAMILY};
    line-height: 150%;
}}
"""

BTN_BASE_STYLE = "color: white; border-radius: 8px; font-weight: bold; padding: 6px; font-size: 12px;"
APPROVE_BTN_STYLE = f"background-color: #5cb85c; {BTN_BASE_STYLE}"
REJECT_BTN_STYLE = f"background-color: #d9534f; {BTN_BASE_STYLE}"

INPUT_FIELD_STYLE = """
QTextEdit {
    background-color: #1E2A38;
    color: #E0E0E0;
    border-radius: 15px;
    border: 1px solid #2C3E50;
    padding: 8px 12px;
    font-size: 13px;
}
QTextEdit:focus {
    border: 1px solid #3498DB;
}
"""

CLOSE_BTN_STYLE = """
QPushButton {
    background-color: #FF5F56;
    color: white;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 16px;
}
QPushButton:hover {
    background-color: #E0483E;
}
"""

ATTACH_BTN_STYLE = """
QPushButton {
    background-color: #E0E0E0;
    color: #333333;
    border-radius: 8px;
    font-weight: bold;
    font-size: 12px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #D0D0D0;
}
QPushButton:disabled {
    background-color: #F0F0F0;
    color: #AAAAAA;
}
"""

NEW_CHAT_BTN_STYLE = """
QPushButton {
    background-color: #2979B0;
    color: white;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 16px;
}
QPushButton:hover {
    background-color: #1A5F8F;
}
"""

IMAGE_PREVIEW_AREA_STYLE = """
QWidget#image_preview_area {
    background-color: #F7F7F7;
    border: 1px dashed #D0D0D0;
    border-radius: 10px;
}
"""

SETTINGS_BTN_STYLE = """
QPushButton {
    background-color: #333333;
    color: white;
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 16px;
}
QPushButton:hover {
    background-color: #444444;
}
"""

SETTINGS_WINDOW_STYLE = f"""
QFrame#settings_container {{
    background-color: rgba(255, 255, 255, 245);
    border: 2px solid #E0E0E0;
    border-radius: 15px;
}}
QLabel {{
    color: #333333;
    font-family: {FONT_FAMILY};
    font-size: 13px;
    font-weight: bold;
}}
"""

IMAGE_REMOVE_BTN_STYLE = """
QPushButton {
    background-color: rgba(0, 0, 0, 160);
    color: white;
    border-radius: 8px;
    font-size: 10px;
    font-weight: bold;
    padding: 0px;
    min-width: 16px;
    max-width: 16px;
    min-height: 16px;
    max-height: 16px;
}
QPushButton:hover {
    background-color: rgba(220, 50, 50, 200);
}
"""

WINDOW_WIDTH = 450
WINDOW_HEIGHT = 700
SIDEBAR_WIDTH = 180
SIDEBAR_EXPANDED_WINDOW_WIDTH = WINDOW_WIDTH + SIDEBAR_WIDTH

BUBBLE_MAX_HEIGHT = 200

# ── 메시지 포맷 상수 (스타일은 MARKDOWN_CSS + QSS가 담당) ──
USER_MSG_FORMAT = "{text}"
PET_MSG_FORMAT = "{text}"
ERROR_MSG_FORMAT = "{text}"
FONT_FAMILY = "'Inter', 'Pretendard', 'Apple SD Gothic Neo', '-apple-system', 'BlinkMacSystemFont', 'Malgun Gothic', sans-serif"

# ── QTextDocument 전용 마크다운 스타일시트 ──
# setDefaultStyleSheet()로 주입되어 HTML 뼈대에 스타일을 입힘
MARKDOWN_CSS = f"""
    body {{
        font-family: {FONT_FAMILY};
        font-size: 13.5px;
        font-weight: 400;
        line-height: 1.6;
        color: #2C3E50;
        margin: 0;
        padding: 0;
    }}
    p {{ margin: 2px 0; }}
    strong {{ font-weight: 600; color: #1A252F; }}
    em {{ font-style: italic; color: #5C6D7E; }}
    a {{ color: #2980B9; text-decoration: none; border-bottom: 1px solid #2980B9; }}
    code {{
        font-family: 'Courier New', Courier, monospace;
        font-size: 12.5px;
        background-color: #F4F6F8;
        color: #E74C3C;
        padding: 2px 5px;
        border-radius: 4px;
        border: 1px solid #E1E8ED;
    }}
    pre {{
        font-family: 'Courier New', Courier, monospace;
        font-size: 12.5px;
        background-color: #282C34;
        color: #ABB2BF;
        padding: 12px;
        border-radius: 8px;
        line-height: 1.4;
    }}
    pre code {{
        background-color: transparent;
        color: inherit;
        padding: 0;
        border: none;
    }}
    blockquote {{
        margin: 4px 0;
        padding-left: 12px;
        border-left: 4px solid #BDC3C7;
        color: #7F8C8D;
        background-color: #F8F9F9;
    }}
    ul, ol {{ margin-top: 4px; margin-bottom: 4px; padding-left: 24px; }}
    li {{ margin-bottom: 2px; }}
    h1, h2, h3, h4, h5, h6 {{
        color: #2C3E50;
        margin-top: 10px;
        margin-bottom: 6px;
        font-weight: 600;
    }}
    h1 {{ font-size: 18px; border-bottom: 1px solid #ECF0F1; padding-bottom: 4px; }}
    h2 {{ font-size: 16px; }}
    h3 {{ font-size: 14.5px; }}
    hr {{ border: none; border-top: 1px solid #ECF0F1; margin: 10px 0; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 6px; margin-bottom: 6px; }}
    th, td {{ border: 1px solid #BDC3C7; padding: 6px 10px; }}
    th {{ background-color: #ECF0F1; font-weight: bold; text-align: left; }}
"""

def _bubble_style(bg_color: str, text_color: str = "#2C3E50", border_color: str = "none") -> str:
    border_prop = f"border: 1px solid {border_color};" if border_color != "none" else "border: none;"
    return f"""
    QTextBrowser {{
        background-color: {bg_color};
        {border_prop}
        color: {text_color};
        border-radius: 14px;
        padding: 10px 16px 10px 12px;
    }}
    QScrollBar:vertical {{
        border: none;
        width: 6px;
        background: {bg_color};
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(150, 150, 150, 0.5);
        min-height: 20px;
        border-radius: 3px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(150, 150, 150, 0.8);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        border: none;
        background: {bg_color};
    }}
    """

# ── 메시지 포맷 상수 (스타일은 MARKDOWN_CSS + QSS가 담당) ──
USER_MSG_FORMAT = "{text}"
PET_MSG_FORMAT = "{text}"
ERROR_MSG_FORMAT = "{text}"

# 유저 챗 버블 (카카오톡 느낌의 노란색 + 은은한 테두리)
USER_BUBBLE_STYLE = _bubble_style("#FEF01B", "#383100", "#E5CD00")

# 기본 펫 버블 (회색조/파란조 + 은은한 테두리)
PET_BUBBLE_STYLE = _bubble_style("#F0F4F8", "#2C3E50", "#D9E2EC")

# 사고 과정(Thinking)과 답변을 하나의 말풍선 안에 담기 위한 QFrame 컨테이너 스타일
PET_BUBBLE_STYLE_WITH_THINKING = """
QFrame#thinking_bubble_frame {
    background-color: #F0F4F8;
    border-radius: 14px;
    border: 1px solid #D9E2EC;
}
"""

PET_BUBBLE_INNER_TEXT_STYLE = _bubble_style("transparent", "#2C3E50", "none")
ERROR_BUBBLE_STYLE = _bubble_style("#FDEDED", "#E74C3C", "#F5C6CB")

OPACITY_SLIDER_STYLE = """
QSlider::groove:horizontal {
    background: #ddd;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #5cb85c;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}
QSlider::handle:horizontal:hover {
    background: #4cae4c;
}
"""

OPACITY_LABEL_STYLE = f"""
QLabel {{
    color: #333333;
    font-family: {FONT_FAMILY};
    font-size: 11px;
    font-weight: bold;
}}
"""

# ── 채팅 스크롤 영역 스타일 ──
CHAT_SCROLL_AREA_STYLE = f"""
QScrollArea {{
    background-color: #222222;
    border: none;
}}
QWidget#chat_scroll_content {{
    background-color: #222222;
}}
QScrollBar:vertical {{
    width: 8px;
    background: rgba(255,255,255,15);
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,150);
    border-radius: 4px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255,255,255,200);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""

# ── 사이드바 토글 버튼 ──
SIDEBAR_TOGGLE_BTN_STYLE = """
QPushButton {
    background-color: transparent;
    color: #888888;
    border: none;
    font-size: 18px;
    font-weight: bold;
    padding: 4px 6px;
    border-radius: 8px;
    min-width: 28px;
    max-width: 28px;
}
QPushButton:hover {
    background-color: rgba(0,0,0,60);
    color: #FFFFFF;
}
"""

# ── 사이드바 패널 전체 배경 ──
SIDEBAR_STYLE = f"""
QWidget#sidebar_panel {{
    background-color: #1A1A1A;
    border-right: 1px solid #333333;
    border-radius: 0px;
}}
QLabel#sidebar_header {{
    color: #AAAAAA;
    font-family: {FONT_FAMILY};
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
    letter-spacing: 1px;
}}
"""

# ── 사이드바 개별 세션 항목 버튼 ──
SESSION_ITEM_STYLE = f"""
QPushButton {{
    background-color: transparent;
    color: #CCCCCC;
    border: none;
    border-radius: 8px;
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: normal;
    text-align: left;
    padding: 8px 10px;
    margin: 1px 4px;
}}
QPushButton:hover {{
    background-color: rgba(255,255,255,12);
    color: #FFFFFF;
}}
"""

# ── 현재 선택된 세션 항목 강조 ──
SESSION_ITEM_ACTIVE_STYLE = f"""
QPushButton {{
    background-color: rgba(41,121,176,180);
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: bold;
    text-align: left;
    padding: 8px 10px;
    margin: 1px 4px;
}}
QPushButton:hover {{
    background-color: rgba(41,121,176,220);
}}
"""

# ── 사이드바 내 신규 채팅 버튼 ──
SIDEBAR_NEW_CHAT_BTN_STYLE = f"""
QPushButton {{
    background-color: rgba(41,121,176,150);
    color: #FFFFFF;
    border: 1px solid rgba(41,121,176,200);
    border-radius: 10px;
    font-family: {FONT_FAMILY};
    font-weight: bold;
    font-size: 12px;
    padding: 7px 10px;
    margin: 4px 6px;
}}
QPushButton:hover {{
    background-color: rgba(41,121,176,220);
}}
"""

# ── 로그인 창 스타일 ──
LOGIN_INPUT_STYLE = f"""
QLineEdit {{
    background-color: #1E2A38;
    color: #E0E0E0;
    border: 1px solid #2C3E50;
    border-radius: 10px;
    padding: 8px 12px;
    font-family: {FONT_FAMILY};
    font-size: 13px;
}}
QLineEdit:focus {{
    border: 1px solid #3498DB;
}}
"""

LOGIN_BTN_STYLE = f"""
QPushButton {{
    background-color: #2979B0;
    color: white;
    border-radius: 10px;
    border: none;
    font-family: {FONT_FAMILY};
    font-weight: bold;
    font-size: 13px;
    padding: 10px 0px;
}}
QPushButton:hover {{
    background-color: #1A5F8F;
}}
QPushButton:pressed {{
    background-color: #144D78;
}}
"""

LOGIN_ERROR_LABEL_STYLE = f"""
QLabel {{
    color: #FF6B6B;
    font-family: {FONT_FAMILY};
    font-size: 11px;
}}
"""

LOGIN_WINDOW_STYLE = f"""
QFrame#login_container {{
    background-color: rgba(255, 255, 255, 245);
    border: 2px solid #E0E0E0;
    border-radius: 15px;
}}
QLabel#login_title {{
    color: #1A1A2E;
    font-family: {FONT_FAMILY};
    font-size: 16px;
    font-weight: bold;
}}
QLabel#login_field_label {{
    color: #555555;
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: bold;
}}
"""

# ── 테마 팔레트 ──────────────────────────────────────────────────
# QColor 호환을 위해 bubble_frame 배경은 r,g,b,a 정수 키로 분리 관리

DARK_THEME = {
    "name": "dark",
    "scroll_bg": "#1C1C1C",
    "scroll_border": "#2A2A2A",
    "scroll_bar_track": "rgba(255,255,255,15)",
    "scroll_bar_handle": "rgba(255,255,255,150)",
    "scroll_bar_handle_hover": "rgba(255,255,255,200)",
    "input_bg": "#1E2A38",
    "input_color": "#E0E0E0",
    "input_border": "#2C3E50",
    "input_focus_border": "#3498DB",
    "sidebar_bg": "#1A1A1A",
    "sidebar_border": "#333333",
    "sidebar_header_color": "#AAAAAA",
    "session_color": "#CCCCCC",
    "session_hover_bg": "rgba(255,255,255,12)",
    "session_hover_color": "#FFFFFF",
    "session_active_bg": "rgba(41,121,176,180)",
    "session_active_hover_bg": "rgba(41,121,176,220)",
    "sidebar_new_chat_bg": "rgba(41,121,176,150)",
    "sidebar_new_chat_border": "rgba(41,121,176,200)",
    "sidebar_new_chat_hover_bg": "rgba(41,121,176,220)",
    "sidebar_scroll_bg": "rgba(255,255,255,10)",
    "sidebar_scroll_handle": "rgba(255,255,255,80)",
    "settings_btn_bg": "#3A3A3A",
    "settings_btn_hover_bg": "#505050",
    "settings_btn_color": "#FFFFFF",
    "toggle_btn_color": "#888888",
    "toggle_btn_hover_bg": "rgba(255,255,255,15)",
    "toggle_btn_hover_color": "#FFFFFF",
    # BubbleFrame paintEvent용 — QColor(r,g,b,a)로 직접 사용
    "bubble_frame_bg_r": 34,
    "bubble_frame_bg_g": 34,
    "bubble_frame_bg_b": 34,
    "bubble_frame_bg_a": 245,
    "bubble_frame_border": "#555555",
    "new_chat_btn_bg": "#2979B0",
    "new_chat_btn_hover_bg": "#1A5F8F",
}

LIGHT_THEME = {
    "name": "light",
    "scroll_bg": "#FAFAFA",
    "scroll_border": "#EAEAEA",
    "scroll_bar_track": "rgba(0,0,0,10)",
    "scroll_bar_handle": "rgba(0,0,0,100)",
    "scroll_bar_handle_hover": "rgba(0,0,0,160)",
    "input_bg": "#FFFFFF",
    "input_color": "#1A1A1A",
    "input_border": "#C8C8C8",
    "input_focus_border": "#2979B0",
    "sidebar_bg": "#E4E4E4",
    "sidebar_border": "#D0D0D0",
    "sidebar_header_color": "#666666",
    "session_color": "#333333",
    "session_hover_bg": "rgba(0,0,0,8)",
    "session_hover_color": "#111111",
    "session_active_bg": "rgba(41,121,176,200)",
    "session_active_hover_bg": "rgba(41,121,176,240)",
    "sidebar_new_chat_bg": "rgba(41,121,176,220)",
    "sidebar_new_chat_border": "rgba(41,121,176,240)",
    "sidebar_new_chat_hover_bg": "rgba(29,95,143,255)",
    "sidebar_scroll_bg": "rgba(0,0,0,8)",
    "sidebar_scroll_handle": "rgba(0,0,0,70)",
    "settings_btn_bg": "#D0D0D0",
    "settings_btn_hover_bg": "#BBBBBB",
    "settings_btn_color": "#222222",
    "toggle_btn_color": "#555555",
    "toggle_btn_hover_bg": "rgba(0,0,0,12)",
    "toggle_btn_hover_color": "#111111",
    # BubbleFrame paintEvent용 — QColor(r,g,b,a)로 직접 사용
    "bubble_frame_bg_r": 248,
    "bubble_frame_bg_g": 248,
    "bubble_frame_bg_b": 248,
    "bubble_frame_bg_a": 250,
    "bubble_frame_border": "#C8C8C8",
    "new_chat_btn_bg": "#2979B0",
    "new_chat_btn_hover_bg": "#1A5F8F",
}


# ── 테마 기반 스타일 생성 함수 ────────────────────────────────────

def get_chat_scroll_area_style(theme: dict) -> str:
    bg = theme["scroll_bg"]
    border = theme.get("scroll_border", "transparent")
    handle = theme["scroll_bar_handle"]
    handle_hover = theme["scroll_bar_handle_hover"]
    return f"""
QScrollArea {{
    background-color: {bg};
    border: 1px solid {border};
    border-radius: 14px;
}}
QWidget#chat_scroll_content {{
    background-color: {bg};
    border-radius: 14px;
}}
QScrollBar:vertical {{
    border: none;
    width: 6px;
    background: {bg};
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background: {handle};
    border-radius: 3px;
    min-height: 20px;
}}
QScrollBar::handle:vertical:hover {{
    background: {handle_hover};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical,
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    border: none;
    background: {bg};
}}
"""


def get_input_field_style(theme: dict) -> str:
    return f"""
QTextEdit {{
    background-color: {theme["input_bg"]};
    color: {theme["input_color"]};
    border-radius: 15px;
    border: 1px solid {theme["input_border"]};
    padding: 8px 12px 8px 52px;
    font-size: 13px;
}}
QTextEdit:focus {{
    border: 1px solid {theme["input_focus_border"]};
}}
"""


def get_sidebar_style(theme: dict) -> str:
    return f"""
QWidget#sidebar_panel {{
    background-color: {theme["sidebar_bg"]};
    border-right: 1px solid {theme["sidebar_border"]};
    border-radius: 0px;
}}
QLabel#sidebar_header {{
    color: {theme["sidebar_header_color"]};
    font-family: {FONT_FAMILY};
    font-size: 11px;
    font-weight: bold;
    padding: 4px 8px;
    letter-spacing: 1px;
}}
"""


def get_session_item_style(theme: dict) -> str:
    return f"""
QPushButton {{
    background-color: transparent;
    color: {theme["session_color"]};
    border: none;
    border-radius: 8px;
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: normal;
    text-align: left;
    padding: 8px 10px;
    margin: 1px 4px;
}}
QPushButton:hover {{
    background-color: {theme["session_hover_bg"]};
    color: {theme["session_hover_color"]};
}}
"""


def get_session_item_active_style(theme: dict) -> str:
    return f"""
QPushButton {{
    background-color: {theme["session_active_bg"]};
    color: #FFFFFF;
    border: none;
    border-radius: 8px;
    font-family: {FONT_FAMILY};
    font-size: 12px;
    font-weight: bold;
    text-align: left;
    padding: 8px 10px;
    margin: 1px 4px;
}}
QPushButton:hover {{
    background-color: {theme["session_active_hover_bg"]};
}}
"""


def get_sidebar_new_chat_btn_style(theme: dict) -> str:
    return f"""
QPushButton {{
    background-color: {theme["sidebar_new_chat_bg"]};
    color: #FFFFFF;
    border: 1px solid {theme["sidebar_new_chat_border"]};
    border-radius: 10px;
    font-family: {FONT_FAMILY};
    font-weight: bold;
    font-size: 12px;
    padding: 7px 10px;
    margin: 4px 6px;
}}
QPushButton:hover {{
    background-color: {theme["sidebar_new_chat_hover_bg"]};
}}
"""


def get_settings_btn_style(theme: dict) -> str:
    return f"""
QPushButton {{
    background-color: {theme["settings_btn_bg"]};
    color: {theme["settings_btn_color"]};
    border-radius: 8px;
    font-weight: bold;
    font-size: 13px;
    padding: 10px 16px;
}}
QPushButton:hover {{
    background-color: {theme["settings_btn_hover_bg"]};
}}
"""


def get_sidebar_toggle_btn_style(theme: dict) -> str:
    return f"""
QPushButton {{
    background-color: transparent;
    color: {theme["toggle_btn_color"]};
    border: none;
    font-size: 18px;
    font-weight: bold;
    padding: 4px 6px;
    border-radius: 8px;
    min-width: 28px;
    max-width: 28px;
}}
QPushButton:hover {{
    background-color: {theme["toggle_btn_hover_bg"]};
    color: {theme["toggle_btn_hover_color"]};
}}
"""


def get_sidebar_scroll_style(theme: dict) -> str:
    bg = theme["sidebar_bg"]
    return (
        f"QScrollArea {{ background: transparent; border: none; }}\n"
        f"QScrollBar:vertical {{ border: none; width: 4px; background: {bg}; margin: 0px; }}\n"
        f"QScrollBar::handle:vertical {{ background: {theme['sidebar_scroll_handle']}; border-radius: 2px; min-height: 20px; }}\n"
        f"QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical, \n"
        f"QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical, \n"
        f"QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ border: none; background: {bg}; }}"
    )


def get_settings_window_style(theme: dict) -> str:
    is_dark = theme["name"] == "dark"
    container_bg = "rgba(38, 38, 38, 245)" if is_dark else "rgba(252, 252, 252, 248)"
    border_color = "#555555" if is_dark else "#D8D8D8"
    label_color = "#CCCCCC" if is_dark else "#444444"
    return f"""
QFrame#settings_container {{
    background-color: {container_bg};
    border: 2px solid {border_color};
    border-radius: 15px;
}}
QLabel {{
    color: {label_color};
    font-family: {FONT_FAMILY};
    font-size: 13px;
    font-weight: bold;
}}
"""


def get_settings_label_style(theme: dict) -> str:
    is_dark = theme["name"] == "dark"
    color = "#AAAAAA" if is_dark else "#555555"
    return f"""
QLabel {{
    color: {color};
    font-family: {FONT_FAMILY};
    font-size: 11px;
    font-weight: bold;
}}
"""


def get_settings_slider_style(theme: dict) -> str:
    is_dark = theme["name"] == "dark"
    groove = "#555555" if is_dark else "#D0D0D0"
    handle = "#5cb85c"
    handle_hover = "#4cae4c"
    return f"""
QSlider::groove:horizontal {{
    background: {groove};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {handle};
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
}}
QSlider::handle:horizontal:hover {{
    background: {handle_hover};
}}
"""
