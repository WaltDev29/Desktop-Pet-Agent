MAIN_CONTAINER_STYLE = """
QFrame#main_container {
    background-color: #FFFFFF;
    border: 1px solid #D1D1D1;
    border-radius: 20px;
}
"""

import html

FONT_FAMILY = "'Inter', 'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕'"

try:
    import markdown
    _HAS_MARKDOWN = True
except ImportError:
    _HAS_MARKDOWN = False

def convert_markdown_to_html(md_text: str) -> str:
    """마크다운 텍스트를 HTML로 변환하고 스타일을 적용합니다."""
    if not _HAS_MARKDOWN:
        # markdown 라이브러리가 없으면 평문 반환
        safe_text = html.escape(md_text).replace('\n', '<br>')
        return f'<div style="margin: 0; font-family: {FONT_FAMILY}; font-size: 13px; line-height: 1.5; color: #111; word-wrap: break-word; word-break: break-word;">{safe_text}</div>'
    
    html_content = markdown.markdown(md_text, extensions=['nl2br', 'extra', 'tables', 'fenced_code'])
    
    # 마크다운 요소별 스타일 적용
    # 코드 블록 <pre><code> 스타일
    html_content = html_content.replace('<pre><code>', f'<pre><code style="background-color: #2d2d2d; color: #f8f8f2; padding: 10px; border-radius: 6px; font-family: \'Courier New\', monospace; font-size: 12px; line-height: 1.5; overflow-x: auto; display: block;">')
    html_content = html_content.replace('</code></pre>', '</code></pre>')
    
    # 인라인 코드 <code> 스타일 (pre 태그 내부가 아닌 경우)
    html_content = html_content.replace('<code>', f'<code style="background-color: #f5f5f5; color: #d63384; padding: 2px 6px; border-radius: 3px; font-family: \'Courier New\', monospace; font-size: 12px;">')
    
    # 강조 <strong> 스타일
    html_content = html_content.replace('<strong>', '<strong style="color: #1a73e8; font-weight: bold;">')
    
    # 이탤릭 <em> 스타일
    html_content = html_content.replace('<em>', '<em style="color: #666; font-style: italic;">')
    
    # 링크 <a> 스타일
    html_content = html_content.replace('<a ', f'<a style="color: #1a73e8; text-decoration: none; cursor: pointer;" ')
    
    # 리스트 스타일
    html_content = html_content.replace('<ul>', f'<ul style="margin: 8px 0; padding-left: 20px;">')
    html_content = html_content.replace('<ol>', f'<ol style="margin: 8px 0; padding-left: 20px;">')
    html_content = html_content.replace('<li>', f'<li style="margin: 4px 0;">')
    
    # 테이블 스타일
    html_content = html_content.replace('<table>', f'<table style="border-collapse: collapse; margin: 8px 0; font-size: 12px; width: 100%;">')
    html_content = html_content.replace('<th>', f'<th style="border: 1px solid #ddd; padding: 8px; background-color: #f5f5f5; text-align: left;">')
    html_content = html_content.replace('<td>', f'<td style="border: 1px solid #ddd; padding: 8px;">')
    
    # 문단(<p>) 태그를 제거하고 줄바꿈(<br>)으로 대체
    html_content = html_content.replace('<p>', '').replace('</p>', '<br>')
    if html_content.endswith('<br>'):
        html_content = html_content[:-4]

    # 중첩 div를 제거하고 순수 HTML만 반환 (말풍선 포맷에서 처리하도록)
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
SIDEBAR_WIDTH = 180  # 사이드바 열림 시 너비 (px)
SIDEBAR_EXPANDED_WINDOW_WIDTH = WINDOW_WIDTH + SIDEBAR_WIDTH  # 사이드바 열림 시 전체 창 너비

# ── 개별 말풍선(QTextBrowser) 위젯 최대 높이 임계값 (px) ──
# 이 높이를 초과하면 말풍선 내부에 스크롤바가 생김
BUBBLE_MAX_HEIGHT = 200

# ── 사용자 메시지 HTML 템플릿 ──
USER_MSG_FORMAT = f"""
<body style="margin: 0; padding: 0; font-family: {FONT_FAMILY};">
    <div style="padding: 12px 16px; font-size: 13px; line-height: 1.5; text-align: left;">
        {{text}}
    </div>
</body>
"""

# ── 펫 메시지 HTML 템플릿 ──
PET_MSG_FORMAT = f"""
<body style="margin: 0; padding: 0; font-family: {FONT_FAMILY};">
    <div style="padding: 12px 16px; font-size: 13px; line-height: 1.5;">
        {{text}}
    </div>
</body>
"""

# ── 에러 메시지 HTML 템플릿 ──
ERROR_MSG_FORMAT = f"""
<body style="margin: 0; padding: 0; font-family: {FONT_FAMILY};">
    <div style="padding: 10px 14px; font-size: 12px; word-wrap: break-word; word-break: break-word;">
        ⚠️ {{text}}
    </div>
</body>
"""


# ── 개별 말풍선 QTextBrowser 기본 스타일시트 ──
def _bubble_style(bg_color: str, text_color: str = "#111111") -> str:
    return f"""
    QTextBrowser {{
        background-color: {bg_color};
        border: none;
        font-family: {FONT_FAMILY};
        font-size: 13px;
        color: {text_color};
        border-radius: 8px;
    }}
    QScrollBar:vertical {{
        width: 8px;
        background: rgba(0,0,0,30);
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(120,120,120,180);
        border-radius: 4px;
        min-height: 20px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(150,150,150,220);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    """

USER_BUBBLE_STYLE = _bubble_style("#FEE500", "#111111")
PET_BUBBLE_STYLE = _bubble_style("#E3F2FD", "#111111")
ERROR_BUBBLE_STYLE = _bubble_style("#FFEBEB", "#FF0000")

# ── 사고 과정 HTML 템플릿 (말풍선 내부 인라인) ──
THINKING_BLOCK_COLLAPSED = f'''
<div style="margin: 0 10px 8px 10px; border: 1px solid #9BBDDA; border-radius: 10px; padding: 8px 12px;">
<table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="22" style="color: #2A62A8; font-size: 13px;">🧠</td>
    <td><a href="action:toggle_thinking" style="color: #1A4F9A; font-family: {FONT_FAMILY}; font-size: 11.5px; font-weight: bold; text-decoration: none;">사고 과정 보기</a></td>
    <td align="right"><a href="action:toggle_thinking" style="color: #2A62A8; text-decoration: none; font-size: 11px;">▶</a></td>
</tr></table>
</div>
'''

THINKING_BLOCK_EXPANDED = f'''
<div style="margin: 0 10px 8px 10px; border: 1px solid #9BBDDA; border-radius: 10px; padding: 8px 12px;">
<table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td width="22" style="color: #2A62A8; font-size: 13px;">🧠</td>
    <td><a href="action:toggle_thinking" style="color: #1A4F9A; font-family: {FONT_FAMILY}; font-size: 11.5px; font-weight: bold; text-decoration: none;">사고 과정 닫기</a></td>
    <td align="right"><a href="action:toggle_thinking" style="color: #2A62A8; text-decoration: none; font-size: 11px;">▼</a></td>
</tr></table>
<div style="border-top: 1px solid #9BBDDA; margin-top: 8px; padding-top: 8px; font-family: 'Courier New', monospace; font-size: 11.5px; color: #1E3A6E; line-height: 1.6; white-space: pre-wrap;">{{content}}</div>
</div>
'''

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