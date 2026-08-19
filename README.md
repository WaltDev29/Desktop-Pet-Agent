# Desktop Pet Agent

Desktop Pet Agent는 데스크톱 화면 위에서 동작하는 캐릭터 기반 인터페이스와 고성능 AI Agent 기능을 결합한 프로그램입니다. LangGraph 기반의 멀티 에이전트 아키텍처를 사용하여 복잡한 작업을 계획하고 실행하며, 사용자와의 자연스러운 상호작용을 지원합니다.

<br>

## ✨ 주요 기능
- **캐릭터 기반 GUI**: 화면 위를 자유롭게 이동하며 상호작용하는 펫 캐릭터.
- **동적 MCP 확장**: `config.json` 수정만으로 새로운 기능을 가진 MCP 서버를 즉시 추가하고 실행 가능.
- **OS & 서비스 제어**: 마우스/키보드 직접 입력, 시각적 인식, 쉘(Shell) 조작뿐만 아니라 이메일, 클라우드 서비스 등 다양한 외부 기능 연동.
- **지능형 작업 실행**: 복잡한 명령을 언어 모델이 인지하고 단계별 분할 실행.
- **Human-in-the-Loop**: 위험한 명령어 작동 등 파괴적 행동 수행 전 Agent UI를 통한 사전 승인 체계.

<br>

## 프로그램 작동 예시
| Pet UI 채팅 | 모바일 앱 | 모바일 앱 채팅 |
|:---:|:---:|:---:|
|<img width="300" alt="파일탐색" src="https://github.com/user-attachments/assets/4c7225f8-e232-4432-9762-51677d389e49" />|<img width="300" alt="모바일 파일탐색" src="https://github.com/user-attachments/assets/8f3bfb07-1436-463e-8625-6c0c26204318" />|<img width="300" alt="모바일 앱 화면" src="https://github.com/user-attachments/assets/3913af12-6c87-4a20-87ae-5706ed47bfc0" />|

---
<br>

## 🛠️ 기술 스택
- **Backend (Agent)**: FastAPI, LangChain, LangGraph
- **Backend (MCP)**: windows-mcp (Model Context Protocol 표준)
- **Frontend (UI)**: PySide6 (Python Qt)
- **Database**: MemorySaver (MVP), PostgresSaver (Production ready)

<br>

## 🏗️ 시스템 아키텍처

이 프로젝트는 **Plan-and-Execute** 모델을 기반으로 하는 멀티 에이전트 구조를 채택하고 있습니다.

- **Planner**: 사용자 요청을 분석하여 단계별 실행 계획을 수립합니다.
- **Master Router**: 현재 작업을 처리할 워커로 적절하게 태스크를 라우팅합니다.
- **General MCP Worker**: `config.json`에 정의된 모든 MCP 서버(Windows 제어, 이메일, 외부 서비스 등)를 통합 관리하고 도구를 실행하는 범용 워커 노드입니다.
- **Vision Worker**: 사용자가 업로드한 이미지를 분석하여 시각적 정보를 텍스트로 변환합니다.
- **Aggregator**: 모든 작업 결과를 취합하여 사용자에게 친절한 답변을 생성합니다.
- **MemorySaver**: 대화 내용 및 에이전트의 상태를 스레드별로 유지하여 멀티 턴 대화를 지원합니다.

<br>

## 🚀 시작하기

### 1. 환경 요구 사양
- **OS**: Windows 10/11 (필수, Windows 기반 MCP 사용)
- **Python**: 3.11 이상
- **Conda**: 다중 시스템 환경 관리를 위해 필수

<br>

### 2. 설치 방법

프로젝트는 Agent 서버와 Pet UI를 위해 각각 분리된 Conda 환경을 사용합니다. MCP 서버는 `config.json` 설정을 통해 동적으로 실행됩니다.

```bash
# 1. Agent 서버 환경 설정 (LangGraph 기반 AI 모델 서버)
cd agent
conda env create -f environment.yml
conda activate desktop-pet-agent

# 2. Pet UI 환경 설정 (사용자 인터페이스)
cd pet
conda env create -f environment.yml
conda activate pet-ui
```

<br>

### 3. 환경 변수 및 MCP 설정

1.  **`.env` 설정**: `agent/` 디렉토리에 있는 `.env.example` 파일을 복사하여 `.env`를 생성하고 LLM API 키 등을 입력합니다.
2.  **`config.json` 설정**: `agent/agent_server/` 디렉토리의 `config.default.json`을 복사하여 `config.json`을 생성합니다. 여기에 사용할 MCP 서버들의 실행 명령과 환경 변수를 정의합니다.

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
