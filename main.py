"""
Desktop Pet Agent - 실행 가이드
================================

이 프로젝트는 3개의 독립 서버로 구성됩니다.
아래 순서대로 터미널 3개를 열어 각각 실행하세요.

[터미널 1] Tool Server (port 8002) - 사용자 컴퓨터의 Tool 실행
    uvicorn tool_server.main:app --host 0.0.0.0 --port 8002 --reload

[터미널 2] Agent Server (port 8001) - LangGraph 에이전트 실행
    uvicorn agent_server.main:app --host 0.0.0.0 --port 8001 --reload

[터미널 3] Web UI (port 8000) - 사용자 채팅 인터페이스
    uvicorn web_ui.main:app --host 0.0.0.0 --port 8000 --reload

접속 주소: http://localhost:8000

통신 흐름:
    Web UI (8000) ──HTTP──> Agent Server (8001) ──HTTP──> Tool Server (8002)
"""

# 이 파일은 직접 실행하지 않습니다.
# 위 가이드를 참고하여 각 서버를 개별 터미널에서 실행하세요.