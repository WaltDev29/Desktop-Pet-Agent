import base64
from io import BytesIO

import pyautogui

from langchain_core.tools import tool
from tool.models import OcrModel


# ==========================================
# 실제 구현 함수
# ==========================================

def capture_region(x: int, y: int, width: int, height: int) -> str:
    """
    마우스 좌표 기반으로 지정한 화면 영역을 캡처하여 base64 PNG로 반환합니다.

    별도 OCR 바이너리(Tesseract 등) 없이 pillow만 사용합니다.
    반환된 base64 이미지는 OpenAI Vision 모델이 직접 읽어 텍스트를 인식합니다.

    좌표 계산 팁:
        - screen_info_tool로 전체 해상도를 먼저 확인하세요.
        - pyautogui.position()으로 마우스 현재 위치를 확인할 수 있습니다.
        - region = (x, y, width, height) 형식입니다. (left-top 기준)
    """
    if width <= 0 or height <= 0:
        return "Error: width와 height는 0보다 커야 합니다."

    try:
        screenshot = pyautogui.screenshot(region=(x, y, width, height))
        buffer = BytesIO()
        screenshot.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return encoded
    except Exception as e:
        return f"Error: {str(e)}"


# ==========================================
# Tool 등록 (팀장 지정 방식: tool() + BaseModel + args_schema)
# ==========================================

def _ocr_func(x: int, y: int, width: int, height: int) -> str:
    return capture_region(x, y, width, height)


ocr_tool = tool(
    func=_ocr_func,
    name="ocr_tool",
    description=(
        "지정한 화면 영역을 캡처하여 base64 PNG 이미지로 반환합니다. "
        "x, y는 캡처 영역의 좌측 상단 좌표이며, width와 height는 영역의 크기입니다. "
        "반환된 이미지를 LLM(Vision 모델)이 읽어 텍스트를 인식합니다. "
        "Tesseract 등 외부 바이너리 없이 동작하며 pillow만 사용합니다."
    ),
    args_schema=OcrModel,
)


tools = [ocr_tool]
