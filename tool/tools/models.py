from pydantic import BaseModel, Field


# ==========================================
# Monitor Tool 스키마
# ==========================================

class ScreenshotModel(BaseModel):
    save_path: str = Field(
        default="",
        description="저장할 파일 절대 경로. 비워두면 base64 문자열로 반환 (예: 'C:/tmp/shot.png')"
    )


class ScreenInfoModel(BaseModel):
    pass  # 파라미터 없음


# ==========================================
# OCR Tool 스키마
# ==========================================

class OcrModel(BaseModel):
    x: int = Field(..., description="캡처 영역 좌측 상단 X 좌표 (픽셀)")
    y: int = Field(..., description="캡처 영역 좌측 상단 Y 좌표 (픽셀)")
    width: int = Field(..., description="캡처 영역 너비 (픽셀)")
    height: int = Field(..., description="캡처 영역 높이 (픽셀)")
