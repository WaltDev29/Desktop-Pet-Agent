import os
from typing import List
from langchain_core.tools import tool

# ==========================================
# File System Tool: OS의 디렉토리와 파일을 직접 제어하는 도구입니다.
# AI 모델이 로컬 환경의 폴더를 스캔하거나 내용을 읽고 쓰는 역할을 담당합니다.
# ==========================================

def list_directory(path: str) -> List[str]:
    """
    지정된 경로의 파일과 폴더 목록을 반환합니다.
    (예: "D드라이브의 파일들을 보여줘" 
     -> 에이전트가 path="D:\\" 를 전달하여 이 함수를 실행)
    """
    try:
        return os.listdir(path)
    except Exception as e:
        return [f"Error: {str(e)}"]

def read_file(path: str) -> str:
    """
    특정 파일의 내용을 텍스트 형식으로 모두 읽어옵니다.
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"Error: {str(e)}"

# ========================================================
# ⚠️ 경고: 아래 두 함수는 로컬 파일 시스템을 파괴(수정/삭제)할 수 있으므로,
# LangGraph의 DANGEROUS_TOOLS 에 등록되어 자동 실행을 차단하고 있습니다.
# ========================================================

def write_file(path: str, content: str) -> str:
    """
    파일의 내용을 새로 작성합니다. (기존 내용이 있다면 덮어씁니다.)
    """
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Success: {path} 파일이 작성되었습니다."
    except Exception as e:
        return f"Error: {str(e)}"

def delete_file(path: str) -> str:
    """
    파일을 바탕화면이나 휴지통을 거치지 않고 영구적으로 삭제합니다.
    """
    try:
        os.remove(path)
        return f"Success: {path} 파일이 삭제되었습니다."
    except Exception as e:
        return f"Error: {str(e)}"



# ==========================================
# Tool 등록
# ==========================================
@tool
def list_directory_tool(path: str) -> str:
    """주어진 경로의 디렉토리 및 파일 목록을 반환합니다."""
    return str(list_directory(path))

@tool
def read_file_tool(path: str) -> str:
    """주어진 경로의 파일 내용을 읽습니다."""
    return read_file(path)

@tool
def write_file_tool(path: str, content: str) -> str:
    """파일에 내용을 씁니다. 사용자의 승인이 필요합니다."""
    return write_file(path, content)

@tool
def delete_file_tool(path: str) -> str:
    """파일을 삭제합니다. 사용자의 승인이 필요합니다."""
    return delete_file(path)



tools = [list_directory_tool, read_file_tool, write_file_tool, delete_file_tool]
