import json
import base64
from io import BytesIO

import pyautogui
import pygetwindow as gw
from mcp.server.fastmcp import FastMCP

# ==========================================
# MCP 서버 초기화
# ==========================================
mcp = FastMCP("desktop-pet-tools")


# ==========================================
# @mcp.tool() 데코레이터 방식을 사용하는 이유
#
# fastmcp는 LangChain의 StructuredTool 객체를 add_tool()로 받을 때
# 버전에 따라 스키마 파싱 오류가 발생할 수 있습니다.
# @mcp.tool() 데코레이터는 함수 시그니처와 타입 힌트를 직접 읽어
# MCP 스키마를 생성하므로 가장 안정적입니다.
#
# LangChain 에이전트 바인딩용 tool() + BaseModel + args_schema 방식은
# monitor.py / ocr.py 에서 별도로 유지합니다.
# (두 방식은 각자의 역할이 다르며 함께 공존합니다)
# ==========================================


# ==========================================
# Monitor 툴
# ==========================================

@mcp.tool()
def screenshot_tool(save_path: str = "") -> str:
    """
    현재 화면 전체를 캡처합니다.
    save_path를 지정하면 파일로 저장하고 경로를 반환합니다.
    비워두면 PNG 이미지를 base64로 인코딩하여 반환하며,
    LLM(Vision 모델)이 화면 내용을 직접 분석할 수 있습니다.
    """
    screenshot = pyautogui.screenshot()

    if save_path:
        screenshot.save(save_path)
        return f"저장 완료: {save_path}"

    buffer = BytesIO()
    screenshot.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


@mcp.tool()
def screen_info_tool() -> str:
    """
    현재 화면 해상도(논리 픽셀)와 활성 창 제목을 JSON 형식으로 반환합니다.
    OCR이나 캡처 좌표 계산 전에 화면 상태를 파악할 때 사용합니다.

    [주의 - 미구현] DPI 스케일링 미적용
    현재 pyautogui.size()는 논리 픽셀만 반환합니다.
    화면 배율(125%, 150% 등)이 설정된 환경에서는 스크린샷의 실제 크기(물리 픽셀)와
    여기서 반환하는 해상도가 다를 수 있어 좌표 계산 시 오차가 발생할 수 있습니다.
    DPI 보정은 추후 마우스 이동 툴 개발 시 함께 반영할 예정입니다.
    """
    width, height = pyautogui.size()

    try:
        active = gw.getActiveWindow()
        window_title = active.title if active else "활성 창 없음"
    except Exception:
        window_title = "조회 불가"

    info = {
        "resolution": {
            "width": width,
            "height": height
        },
        "active_window": window_title
    }
    return json.dumps(info, ensure_ascii=False)


# ==========================================
# OCR 툴
# ==========================================

@mcp.tool()
def ocr_tool(x: int, y: int, width: int, height: int) -> str:
    """
    지정한 화면 영역을 캡처하여 base64 PNG 이미지로 반환합니다.
    x, y는 캡처 영역의 좌측 상단 좌표(논리 픽셀 기준)이며,
    width와 height는 영역의 크기입니다.
    반환된 이미지를 LLM(Vision 모델)이 읽어 텍스트를 인식합니다.
    Tesseract 등 외부 바이너리 없이 pillow만 사용합니다.

    [주의 - 미구현] DPI 스케일링 미적용
    x, y, width, height는 논리 픽셀 기준으로 입력해야 합니다.
    화면 배율이 설정된 환경에서 스크린샷 이미지(물리 픽셀) 기준으로 좌표를 입력하면
    엉뚱한 영역이 캡처될 수 있습니다.
    screen_info_tool로 해상도를 먼저 확인 후 좌표를 계산하세요.
    DPI 보정은 추후 마우스 이동 툴 개발 시 함께 반영할 예정입니다.
    """
    if width <= 0 or height <= 0:
        return "Error: width와 height는 0보다 커야 합니다."

    try:
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode("utf-8")
    except Exception as e:
        return f"Error: {str(e)}"


# ==========================================
# 실행
# 터미널에서: python -m tool.main
# ==========================================
if __name__ == "__main__":
    mcp.run(transport="stdio")
