# Tool 설계 문서 — Monitor / OCR / MCP 연동

---

## 목차

1. [Monitor Tool](#1-monitor-tool)
2. [OCR Tool](#2-ocr-tool)
3. [공통 미구현 사항 — DPI 스케일링](#3-공통-미구현-사항--dpi-스케일링)
4. [MCP 연동 가이드](#4-mcp-연동-가이드)
5. [추후 확장 방향](#5-추후-확장-방향)

---

## 1. Monitor Tool

### 개요

현재 화면 상태를 에이전트가 인식할 수 있도록 정보를 제공하는 툴입니다.
에이전트가 어떤 액션을 취하기 전 "지금 화면이 어떤 상태인가"를 파악하는 역할을 담당합니다.

### 구현된 툴

#### `screen_info_tool`

현재 화면 해상도(논리 픽셀)와 활성 창 제목을 반환합니다.

**반환 예시**
```json
{
  "resolution": { "width": 1920, "height": 1080 },
  "active_window": "Visual Studio Code"
}
```

**사용 목적**
- 마우스 이동 전 화면 크기 파악
- 현재 어떤 창이 활성화되어 있는지 확인
- OCR 좌표 계산의 기준점 확보

**사용 라이브러리**
- `pyautogui.size()` — 전체 해상도 조회
- `pygetwindow.getActiveWindow()` — 활성 창 제목 조회

> ⚠️ **[미구현] DPI 스케일링**: 현재 논리 픽셀만 반환합니다. 자세한 내용은 [3장](#3-공통-미구현-사항--dpi-스케일링)을 참고하세요.

---

#### `screenshot_tool`

전체 화면을 캡처하여 base64 PNG 이미지로 반환합니다.

**파라미터**

| 파라미터 | 타입 | 기본값 | 설명 |
|---|---|---|---|
| `save_path` | str | `""` | 비워두면 base64 반환, 경로 지정 시 파일 저장 |

**반환**
- `save_path` 미지정: base64 인코딩된 PNG 문자열 → LLM(Vision 모델)이 직접 분석
- `save_path` 지정: 파일 저장 후 경로 반환

**사용 라이브러리**
- `pyautogui.screenshot()` — 화면 캡처
- `Pillow(BytesIO)` — PNG 인코딩 및 base64 변환

### 설계 시 고려한 옵션들

**옵션 A — 이미지 파일로 저장 후 경로 반환**

화면을 캡처해 로컬 파일로 저장하고 경로만 반환하는 방식입니다.
- 장점: 구현이 단순하고 파일을 나중에 재사용 가능
- 단점: 파일 시스템 의존, 임시 파일 정리 필요, LLM이 직접 읽을 수 없음
- **미채택 이유**: 에이전트가 이미지를 직접 분석하려면 추가 처리가 필요하고 배포 환경에서 경로 관리가 복잡해짐

**옵션 B — base64 인코딩 반환 (채택)**

캡처한 이미지를 메모리에서 직접 base64로 변환하여 반환하는 방식입니다.
- 장점: 파일 저장 불필요, OpenAI Vision 모델이 즉시 분석 가능, 라이브러리 추가 없음
- 단점: 전체 화면 캡처 시 base64 문자열이 길어짐
- **채택 이유**: 배포 시 가볍고, 에이전트가 이미지를 즉시 활용 가능

**옵션 C — 해상도·창 정보 + 스크린샷 통합 (단일 툴)**

두 기능을 하나의 툴로 합치는 방식입니다.
- 장점: 툴 개수 감소
- 단점: 에이전트가 필요 없는 스크린샷까지 항상 찍어야 하는 비효율 발생, 툴 호출 목적이 불명확해짐
- **미채택 이유**: 역할을 분리해야 에이전트가 상황에 맞게 선택적으로 호출 가능

### 마우스 이동에서 Monitor 툴 활용 방법

```
[1] screen_info_tool 호출
        ↓
    해상도 확인 (예: 1920x1080)
    활성 창 확인 (예: "Chrome")
        ↓
[2] screenshot_tool 호출
        ↓
    전체 화면 이미지(base64) 반환
        ↓
[3] LLM(Vision 모델)이 이미지 분석
        ↓
    "버튼이 화면 중앙 우측, 약 (1400, 540) 부근에 있음"
        ↓
[4] 마우스 이동 툴 호출 (추후 구현)
    pyautogui.moveTo(1400, 540)
```

**구체적인 좌표 계산 예시**

해상도가 1920x1080일 때 화면을 구역으로 나누면:

| 구역 | X 범위 | Y 범위 |
|---|---|---|
| 좌측 상단 | 0 ~ 960 | 0 ~ 540 |
| 우측 상단 | 960 ~ 1920 | 0 ~ 540 |
| 좌측 하단 | 0 ~ 960 | 540 ~ 1080 |
| 우측 하단 | 960 ~ 1920 | 540 ~ 1080 |

---

## 2. OCR Tool

### 개요

화면의 특정 영역을 좌표 기반으로 캡처하여 에이전트가 텍스트를 인식할 수 있도록 이미지를 제공하는 툴입니다.
"화면에서 이 부분의 텍스트를 읽어줘"라는 요청을 처리하기 위한 기반 기능을 담당합니다.

### 구현된 툴

#### `ocr_tool`

지정한 화면 영역을 캡처하여 base64 PNG 이미지로 반환합니다.
반환된 이미지를 OpenAI Vision 모델이 읽어 텍스트를 인식합니다.

**파라미터**

| 파라미터 | 타입 | 설명 |
|---|---|---|
| `x` | int | 캡처 영역 좌측 상단 X 좌표 (논리 픽셀) |
| `y` | int | 캡처 영역 좌측 상단 Y 좌표 (논리 픽셀) |
| `width` | int | 캡처 영역 너비 (픽셀) |
| `height` | int | 캡처 영역 높이 (픽셀) |

**반환**
- base64 인코딩된 PNG 문자열
- LLM(Vision 모델)이 이미지를 직접 분석하여 텍스트 추출

**사용 라이브러리**
- `pyautogui.screenshot(region=(x, y, w, h))` — 좌표 기반 영역 캡처
- `Pillow(BytesIO)` — PNG 인코딩 및 base64 변환

> 외부 바이너리 불필요: Tesseract 등 별도 OCR 엔진 설치 없이 동작합니다.

> ⚠️ **[미구현] DPI 스케일링**: 좌표는 논리 픽셀 기준으로 입력해야 합니다. 자세한 내용은 [3장](#3-공통-미구현-사항--dpi-스케일링)을 참고하세요.

### 설계 시 고려한 옵션들

**옵션 A — Tesseract + pytesseract (전통적 OCR)**

로컬에서 Tesseract 엔진이 직접 텍스트를 추출하는 방식입니다.
- 장점: 인터넷 없이 동작, 텍스트를 문자열로 직접 반환
- 단점: Tesseract 바이너리 별도 설치 필요, 한국어 언어팩 추가 필요, 폰트·배경에 따라 인식률 불안정, 배포 시 환경 설정 복잡
- **미채택 이유**: 배포 시 최대한 가볍게 유지해야 한다는 요구사항에 맞지 않음

**옵션 B — EasyOCR**

딥러닝 기반 OCR 라이브러리로 한국어 인식률이 높습니다.
- 장점: 한국어 포함 다국어 지원, 인식률 우수
- 단점: 모델 파일 다운로드 필요(수백 MB), GPU 없으면 느림, 패키지 크기 대형
- **미채택 이유**: 배포 경량화 요구사항에 정면으로 위배됨

**옵션 C — base64 이미지 반환 후 LLM 분석 (채택)**

캡처 이미지를 그대로 LLM(Vision 모델)에게 넘기는 방식입니다.
- 장점: 추가 패키지 없음, pillow만으로 구현, OpenAI Vision 모델의 높은 인식률, 한국어 포함 자연어 문맥 이해 가능
- 단점: OpenAI API 호출 필요 (인터넷 연결 필수), API 비용 발생
- **채택 이유**: 배포 경량화 조건 충족, 기존 OpenAI 사용 환경과 일치, 별도 모델 설치 불필요

**옵션 D — Windows OCR API (WinRT)**

Windows 내장 OCR 엔진을 사용하는 방식입니다.
- 장점: OS 내장 기능이라 별도 설치 없음
- 단점: Windows 전용, Python에서 WinRT 호출이 복잡, 한국어 언어팩 설치 여부에 따라 동작 달라짐
- **미채택 이유**: 크로스플랫폼 고려 및 구현 복잡도 문제

### 마우스 이동에서 OCR 툴 활용 방법

OCR 툴은 마우스를 이동시킬 **목표 위치를 텍스트로 찾아내는** 역할을 합니다.

```
[1] screen_info_tool 호출
        ↓
    전체 해상도 파악 (예: 1920x1080)
        ↓
[2] screenshot_tool 호출
        ↓
    전체 화면 이미지 분석
    → LLM: "확인 버튼이 화면 하단 중앙부, 약 (900~1020, 700~740) 영역 추정"
        ↓
[3] ocr_tool 호출 — 추정 영역만 정밀 캡처
    ocr_tool(x=900, y=700, width=120, height=40)
        ↓
    해당 영역 이미지 반환
    → LLM: "이미지에 '확인' 텍스트 확인, 중심 좌표 (960, 720)"
        ↓
[4] 마우스 이동 툴 호출 (추후 구현)
    pyautogui.moveTo(960, 720)
    pyautogui.click()
```

**좌표 계산 전략**

전체 화면을 한 번에 OCR하면 이미지가 크고 분석 비용이 높아집니다.
아래 전략으로 영역을 좁히면 정확도와 효율이 올라갑니다.

- **전략 1 — 구역 분할**: 전체 화면을 4등분하여 목표가 있을 법한 구역만 OCR
- **전략 2 — 스크린샷 후 정밀 캡처 (권장)**: `screenshot_tool`로 전체 화면 먼저 확인 → LLM이 위치 추정 → 해당 구역만 `ocr_tool`로 정밀 캡처
- **전략 3 — 슬라이딩 윈도우**: 목표 위치를 전혀 모를 때 일정 크기의 윈도우를 이동하며 순차 스캔

---

## 3. 공통 미구현 사항 — DPI 스케일링

### 문제 정의

Windows에서 화면 배율(125%, 150%, 200% 등)을 설정하면 두 가지 좌표계가 존재합니다.

| 좌표계 | 설명 | 예시 (150% 배율) |
|---|---|---|
| **논리 픽셀** | OS가 앱에게 알려주는 해상도 | 1920 x 1080 |
| **물리 픽셀** | 실제 모니터 해상도 | 2880 x 1620 |

`pyautogui.size()`는 논리 픽셀을 반환하지만 `pyautogui.screenshot()`은 환경에 따라 물리 픽셀로 캡처합니다.
결과적으로 LLM이 스크린샷 이미지에서 읽은 좌표를 그대로 마우스 이동에 쓰면 위치가 어긋납니다.

```
screen_info_tool 반환 → 1920 x 1080 (논리 픽셀)
screenshot 실제 크기  → 2880 x 1620 (물리 픽셀, 150% 배율)

LLM: "버튼이 (960, 540)에 있음"  ← 물리 픽셀 기준
→ pyautogui.moveTo(960, 540)
→ 실제 클릭 위치: (720, 405)   ← 논리 픽셀 기준으로 어긋남
```

### 배율별 오차 정리

| 배율 | 논리 픽셀 | 물리 픽셀 | 오차 배율 |
|---|---|---|---|
| 100% | 1920x1080 | 1920x1080 | 없음 |
| 125% | 1920x1080 | 2400x1350 | 1.25배 |
| 150% | 1920x1080 | 2880x1620 | 1.5배 |
| 200% | 1920x1080 | 3840x2160 | 2.0배 |

### 개선 방향 (추후 마우스 이동 툴 개발 시 반영 예정)

`screen_info_tool`에 `ctypes`(Windows 내장)를 추가하여 물리 픽셀과 배율 정보를 함께 반환합니다.

```python
import ctypes

physical_w = ctypes.windll.user32.GetSystemMetrics(0)
physical_h = ctypes.windll.user32.GetSystemMetrics(1)
scale_x = physical_w / logical_w
scale_y = physical_h / logical_h
```

**개선 후 반환 예시 (150% 배율)**
```json
{
  "resolution": {
    "logical":  { "width": 1920, "height": 1080 },
    "physical": { "width": 2880, "height": 1620 },
    "scale":    { "x": 1.5, "y": 1.5 }
  },
  "active_window": "Chrome"
}
```

에이전트가 배율 정보를 받으면 물리 픽셀 좌표를 논리 픽셀로 변환하여 정확한 마우스 이동이 가능합니다.

```
물리 픽셀 (960, 540) → 논리 픽셀 = (960 / 1.5, 540 / 1.5) = (640, 360)
pyautogui.moveTo(640, 360)  ← 올바른 위치
```

> `ctypes.windll`은 Windows 전용입니다. 크로스플랫폼 지원이 필요할 경우 `screeninfo` 라이브러리 사용을 검토할 수 있으나 배포 경량화 요구사항과 상충될 수 있어 추후 논의가 필요합니다.

---

## 4. MCP 연동 가이드

### 개요

`tool/main.py`는 FastMCP 기반 MCP 서버입니다.
`@mcp.tool()` 데코레이터 방식으로 구현되어 있으며 stdio 방식으로 동작합니다.

| 툴 이름 | 설명 | 반환 |
|---|---|---|
| `screenshot_tool` | 전체 화면 캡처 | base64 PNG 또는 파일 경로 |
| `screen_info_tool` | 해상도 + 활성 창 제목 | JSON 문자열 |
| `ocr_tool` | 좌표 기반 영역 캡처 | base64 PNG |

### 구현 방식 — `@mcp.tool()` vs `add_tool()`

`@mcp.tool()` 데코레이터 방식을 채택한 이유는 다음과 같습니다.

`fastmcp`의 `add_tool()`은 LangChain `StructuredTool` 객체를 받을 때 버전에 따라 스키마 파싱 오류가 발생할 수 있습니다. 반면 `@mcp.tool()` 데코레이터는 함수 시그니처와 타입 힌트를 직접 읽어 MCP 스키마를 자동 생성하므로 버전 의존성 없이 안정적으로 동작합니다.

LangChain 에이전트 바인딩용 `tool() + BaseModel + args_schema` 방식은 `monitor.py` / `ocr.py`에서 별도로 유지합니다. 두 방식은 각자의 역할이 다르며 함께 공존합니다.

### 필요 패키지 설치

```bash
pip install fastmcp pyautogui pygetwindow pillow
```

> `pytesseract`, Tesseract 바이너리 **설치 불필요**
> OCR은 반환된 base64 이미지를 OpenAI Vision 모델이 직접 읽습니다.

### MCP 서버 실행

```bash
python -m tool.main
```

### agent_server 연동 방법

`agent_server/tool_client.py`의 기존 HTTP Proxy Tool 방식과 병행하여 아래처럼 MCP 클라이언트를 추가할 수 있습니다.

**패키지 설치**
```bash
pip install langchain-mcp-adapters
```

**연동 코드**
```python
from langchain_mcp_adapters.client import MultiServerMCPClient

async def get_mcp_tools():
    async with MultiServerMCPClient({
        "desktop-pet": {
            "command": "python",
            "args": ["-m", "tool.main"],
            "transport": "stdio",
        }
    }) as client:
        return client.get_tools()
```

반환된 `tools` 리스트를 기존 `tool_client.py`의 `tools`에 추가하면 에이전트가 MCP 툴을 함께 사용할 수 있습니다.

```python
mcp_tools = await get_mcp_tools()
all_tools = tools + mcp_tools
llm_with_tools = llm.bind_tools(all_tools)
```

### tool_choice 사용 예시

```python
# 자동 선택 (기본)
llm_with_tools = llm.bind_tools(tools, tool_choice="auto")

# 특정 툴 강제 호출
llm_with_tools = llm.bind_tools(
    tools,
    tool_choice={"type": "function", "function": {"name": "ocr_tool"}}
)
```

### 툴 파라미터 참고

**screenshot_tool**
```json
{ "save_path": "" }
```

**screen_info_tool**
```json
{}
```

**ocr_tool**
```json
{
  "x": 100,
  "y": 200,
  "width": 400,
  "height": 300
}
```

> ⚠️ **DPI 주의**: 좌표는 논리 픽셀 기준으로 입력하세요. 배율 환경에서 물리 픽셀 기준으로 입력하면 엉뚱한 영역이 캡처됩니다. `screen_info_tool`로 해상도를 먼저 확인하세요. DPI 보정은 추후 반영 예정입니다.

### 추후 툴 추가 방법

1. `tool/main.py`에 `@mcp.tool()` 데코레이터로 함수 추가
2. `tool/models.py`에 `BaseModel` 스키마 추가 (LangChain 바인딩용)
3. `tool/tools/` 아래 구현 파일 추가
4. `tool/__init__.py` 수정은 **별도 브랜치** `feature/tool/init`에서 PR

```python
# tool/main.py — 툴 추가 예시
@mcp.tool()
def new_tool(param: str) -> str:
    """새로운 툴 설명"""
    return some_function(param)
```

---

## 5. 추후 확장 방향

**Monitor**
- DPI 보정 적용: `screen_info_tool`에 논리/물리 픽셀 및 배율 정보 추가 (마우스 이동 툴 개발 시)
- 특정 창 스크린샷: 활성 창만 캡처하는 기능 (`pygetwindow` + 창 좌표 기반 region 캡처)
- 변화 감지: 이전/현재 스크린샷 비교로 화면 변화 여부 반환

**OCR**
- DPI 보정 자동화: 배율 정보를 받아 좌표 변환을 툴 내부에서 처리
- 텍스트 위치 반환: 현재 이미지 반환에서 좌표 + 텍스트 함께 반환하는 구조로 발전
- 클릭 타겟 자동화: OCR → 좌표 확보 → 마우스 이동 파이프라인 연결
- 다중 영역 동시 캡처: 배치 방식으로 API 비용 절감

**공통**
- 멀티 모니터 지원: 모니터별 region 분리 처리
- 마우스 이동 툴 추가: `feature/tool/mouse` 브랜치에서 별도 개발 예정
