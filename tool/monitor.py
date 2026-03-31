import json
import base64
from io import BytesIO

import pyautogui
import pygetwindow as gw

from langchain_core.tools import tool
from tool.models import ScreenshotModel, ScreenInfoModel


# ==========================================
# 실제 구현 함수
# ==========================================

def capture_screenshot(save_path: str = "") -> str:
    """
    현재 화면 전체를 캡처합니다.
    - save_path 지정 시: 파일로 저장 후 경로 반환
    - save_path 미지정 시: PNG를 base64 인코딩하여 반환 (LLM이 이미지를 직접 읽을 수 있음)
    """
    screenshot = pyautogui.screenshot()

    if save_path:
        screenshot.save(save_path)
        return f"저장 완료: {save_path}"

    buffer = BytesIO()
    screenshot.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return encoded


def get_screen_info() -> str:
    """
    현재 화면 해상도와 활성 창 제목을 반환합니다.
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
# Tool 등록 (팀장 지정 방식: tool() + BaseModel + args_schema)
# ==========================================

def _screenshot_func(save_path: str = "") -> str:
    return capture_screenshot(save_path)

def _screen_info_func() -> str:
    return get_screen_info()


screenshot_tool = tool(
    func=_screenshot_func,
    name="screenshot_tool",
    description=(
        "현재 화면 전체를 캡처합니다. "
        "save_path를 지정하면 파일로 저장하고 경로를 반환합니다. "
        "비워두면 PNG 이미지를 base64로 인코딩하여 반환하며, LLM이 화면 내용을 직접 분석할 수 있습니다."
    ),
    args_schema=ScreenshotModel,
)

screen_info_tool = tool(
    func=_screen_info_func,
    name="screen_info_tool",
    description=(
        "현재 화면 해상도(width, height)와 활성 창 제목을 JSON 형식으로 반환합니다. "
        "OCR이나 캡처 좌표 계산 전에 화면 상태를 파악할 때 사용합니다."
    ),
    args_schema=ScreenInfoModel,
)


tools = [screenshot_tool, screen_info_tool]
