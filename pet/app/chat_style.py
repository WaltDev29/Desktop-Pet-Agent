MAIN_CONTAINER_STYLE = """
QFrame#main_container {
    background-color: #FFFFFF;
    border: 1px solid #D1D1D1;
    border-radius: 20px;
}
"""

import html

FONT_FAMILY = "'Pretendard', 'Apple SD Gothic Neo', 'Malgun Gothic', '맑은 고딕', sans-serif"

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
        return f'<div style="font-family: {FONT_FAMILY}; font-size: 13px; line-height: 1.5; color: #111; word-wrap: break-word; word-break: break-word;">{safe_text}</div>'
    
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

    return f'<div style="font-family: {FONT_FAMILY}; font-size: 13px; line-height: 1.5; color: #111; word-wrap: break-word; word-break: break-word;">{html_content.strip()}</div>'


CHAT_HISTORY_STYLE = f"""
QTextEdit {{
    background-color: transparent;
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
QLineEdit {
    background-color: #F2F2F2;
    color: black;
    border-radius: 15px;
    border: 1px solid #E0E0E0;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus {
    border: 1px solid #A0A0A0;
}
"""

CLOSE_BTN_STYLE = "background-color: #FF5F56; color: white; border-radius: 10px; font-weight: bold; font-size: 11px;"

ATTACH_BTN_STYLE = """
QPushButton {
    background-color: transparent;
    color: #888888;
    border: none;
    font-size: 18px;
    padding: 2px 4px;
}
QPushButton:hover {
    color: #555555;
}
QPushButton:disabled {
    color: #CCCCCC;
}
"""

IMAGE_PREVIEW_AREA_STYLE = """
QWidget#image_preview_area {
    background-color: #F7F7F7;
    border: 1px dashed #D0D0D0;
    border-radius: 10px;
}
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

WINDOW_WIDTH = 300
WINDOW_HEIGHT = 400

USER_MSG_FORMAT = f"""
<div style="display: flex; justify-content: flex-end; margin-bottom: 12px;">
    <div style="width: 65%; max-width: 70%; text-align: right;">
        <div style="color: #888; font-size: 10px; margin-bottom: 4px; margin-right: 4px;">나</div>
        <div style="background-color: #FEE500; border-radius: 16px; padding: 12px 14px; color: #111; font-family: {FONT_FAMILY}; font-size: 13px; line-height: 1.5; word-wrap: break-word; word-break: break-word; overflow-wrap: break-word; max-height: 260px; overflow-y: auto; overflow-x: hidden; width: 100%; display: inline-block;">{{text}}</div>
    </div>
</div>
"""

PET_MSG_FORMAT = f"""
<div style="display: flex; justify-content: flex-start; margin-bottom: 12px;">
    <div style="width: 65%; max-width: 70%; text-align: left;">
        <div style="color: #888; font-size: 10px; margin-bottom: 4px; margin-left: 4px;">🐾 펫</div>
        <div style="background-color: #E3F2FD; border-radius: 16px; padding: 12px 14px; color: #111; font-family: {FONT_FAMILY}; font-size: 13px; line-height: 1.5; word-wrap: break-word; word-break: break-word; overflow-wrap: break-word; max-height: 260px; overflow-y: auto; overflow-x: hidden; width: 100%; display: inline-block;">{{text}}</div>
    </div>
</div>
"""

ERROR_MSG_FORMAT = f"""
<div style="margin: 10px 0; text-align: center;">
    <div style="display: inline-block; background-color: #FFEBEB; border-radius: 8px; padding: 8px 12px; color: #FF0000; font-family: {FONT_FAMILY}; font-size: 12px; max-width: 70%; max-height: 250px; overflow-y: auto; overflow-x: hidden; word-wrap: break-word; word-break: break-word;">⚠️ {{text}}</div>
</div>
"""

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