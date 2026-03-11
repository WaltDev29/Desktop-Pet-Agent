# Desktop Pet Agent
Desktop Pet Agent는 데스크톱 화면 위에서 동작하는 캐릭터 기반 인터페이스와 AI Agent 기능을 결합한 프로그램이다. 화면 위에 표시되는 캐릭터가 사용자와 상호작용하며 다양한 작업을 수행하는 AI 기반 데스크톱 보조 시스템을 목표로 한다.

이 프로젝트는 GUI 인터페이스, AI Agent, 시스템 제어 Tool, AI Agent 제어 App 구조를 결합하여 사용자의 자연어 명령을 기반으로 다양한 작업을 수행할 수 있도록 설계되었다.

<br>

# 주요 기능
- Desktop 화면 위 캐릭터 UI 제공
- 자연어 기반 사용자 명령 처리
- AI Agent 기반 작업 계획 및 실행
- 애플리케이션을 이용한 AI Agent 제어

<br>

# 프로그램 작동 예시
|항목|사진|
|--|--|
|Text 명령 입력||
|클릭 시 표시 메뉴||

<br>

# 시스템 구조
프로젝트는 다음과 같은 모듈 구조로 구성된다.

Desktop Pet Agent  
│  
├─ GUI  
│   └ Desktop Pet 인터페이스  
│  
├─ AI Agent  
│   └ 사용자 명령 분석 및 작업 계획  
│  
├─ Tool API  
│   ├ 시스템 자동화  
│   ├ 애플리케이션 제어  
│   └ OCR 기능  
│  
└ App  
&nbsp;&nbsp;&nbsp;&nbsp;└ AI Agent 제어

<br>

# 사용 기술
### GUI
- PySide

### AI Agent
- LangChain

### Tool API
- PyAutoGUI
- pywinauto

### App
- Kotlin