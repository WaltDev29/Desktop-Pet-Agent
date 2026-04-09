# Desktop Pet Agent

<img width="1536" height="1024" alt="프로젝트logo" src="https://github.com/user-attachments/assets/485706df-908c-4873-96da-6db80db1f082" />

Desktop Pet Agent는 데스크톱 화면 위에서 동작하는 캐릭터 기반 인터페이스와 고성능 AI Agent 기능을 결합한 프로그램입니다. LangGraph 기반의 멀티 에이전트 아키텍처를 사용하여 복잡한 작업을 계획하고 실행하며, 사용자와의 자연스러운 상호작용을 지원합니다.

<br>

# 프로그램 작동 예시
|항목|사진|
|--|--|
|Text 명령 입력|<img width="553" height="311" alt="예시1" src="https://github.com/user-attachments/assets/a8f52a12-718e-4a8a-86c8-9069198c666f" />|
|클릭 시 표시 메뉴|<img width="334" height="189" alt="예시2" src="https://github.com/user-attachments/assets/bca6ee3b-73cb-416b-9d43-a4b89a054970" />|

---
<br>

## 🚀 시작하기

### 1. 환경 요구 사양
- **OS**: Windows (권장)
- **Python**: 3.11 이상
- **Conda**: 환경 관리를 위해 설치 권장

<br>

### 2. 설치 방법

프로젝트는 `agent`와 `pet` 두 개의 주요 패키지로 구성되어 있습니다. 각각의 환경을 설정해야 합니다.

```bash
# Agent 환경 설정
cd agent
conda env create -f environment.yml
conda activate desktop-pet-agent

# Pet UI 환경 설정
cd pet
conda env create -f environment.yml
conda activate pet-ui
```

<br>

### 3. 환경 변수 설정 (`.env`)

`agent/` 디렉토리에 `.env.example` 파일 이름을 `env`로 수정하고, 사용자 환경에 맞게 수정합니다.

<br>

## 🖥️ 실행 방법

프로그램을 실행하려면 **Agent 서버**를 먼저 실행한 후, **Pet UI**를 실행해야 합니다.

### Step 1: Agent 서버 실행
```bash
cd agent
conda activate desktop-pet-agent
python main.py
```
- Agent 서버는 `localhost:8001`에서 대기하며 요청을 처리합니다.

### Step 2: Pet UI & App 서버 실행
```bash
cd pet
conda activate pet-ui
python main.py
```
- UI가 별도 스레드에서 실행되며, App 서버는 `localhost:8000`에서 실행되어 UI와 Agent 사이의 중계 역할을 합니다.

<br>

## 🏗️ 시스템 아키텍처

이 프로젝트는 **Plan-and-Execute** 모델을 기반으로 하는 멀티 에이전트 구조를 채택하고 있습니다.

- **Planner**: 사용자 요청을 분석하여 단계별 실행 계획을 수립합니다.
- **Master Router**: 현재 단계에서 가장 적합한 전문가 에이전트(Vision/General)를 선택합니다.
- **Vision Worker**: 화면 스크린샷 캡처, OCR 및 시각적 분석을 담당합니다.
- **General Worker**: 파일 조작, 시스템 제어, 웹 검색 등을 수행합니다.
- **Aggregator**: 모든 작업 결과를 취합하여 사용자에게 친절한 답변을 생성합니다.
- **MemorySaver**: 대화 내용 및 에이전트의 상태를 스레드별로 유지하여 멀티 턴 대화를 지원합니다.

<br>

## ✨ 주요 기능
- **캐릭터 기반 GUI**: 화면 위를 자유롭게 이동하며 상호작용하는 펫 캐릭터.
- **지능형 작업 실행**: 복잡한 명령(예: "D드라이브 파일 모두 삭제해줘")을 이해하고 분할 실행.
- **Human-in-the-Loop**: 위험한 작업(파일 삭제 등) 수행 전 사용자 승인 인터페이스 제공.
- **쿠키 기반 세션 관리**: 멀티 유저 환경을 고려한 안정적인 대화 맥락 유지.
- **시각적 이해**: 화면의 내용을 캡처하고 분석하여 피드백 제공.

<br>

## 🛠️ 기술 스택
- **Backend**: FastAPI, LangChain, LangGraph
- **Frontend**: PySide6 (Python Qt)
- **Database**: MemorySaver (MVP), PostgresSaver (Production ready)
- **Tools**: PyAutoGUI, httpx, PIL
