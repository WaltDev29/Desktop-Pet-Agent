"""
agent/config.py

MCP 설정을 JSON 파일로 관리합니다.
.env의 MCP 관련 항목을 대체합니다. LLM/서버 설정은 기존 .env를 유지합니다.

파일 구조:
  config.default.json  기본값 템플릿 + 설정 가이드 (git 추적)
  config.json          사용자 실제 값 (.gitignore 추가)

사용법:
  import config as cfg

  cfg.get("mcp.windows_mcp.python_path")        # 단일 값
  cfg.get("mcp.windows_mcp")                    # 섹션 전체 dict
  cfg.get("mcp.workspace_mcp.enabled", False)   # fallback 지정

  cfg.save({"mcp": {"windows_mcp": {"python_path": "C:/..."}}})
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

BASE_DIR     = Path(__file__).resolve().parent
DEFAULT_PATH = BASE_DIR / "config.default.json"
CONFIG_PATH  = BASE_DIR / "config.json"

_cache: dict | None = None

# config.default.json 최상단의 설명용 키 (실제 설정값이 아님)
_GUIDE_KEYS = {"===== 설정 방법 ====="}


def load() -> dict:
    """
    config.json을 로드합니다. 없으면 config.default.json을 사용합니다.
    한 번 로드하면 메모리에 캐싱됩니다.
    """
    global _cache
    if _cache is not None:
        return _cache

    if not DEFAULT_PATH.exists():
        raise FileNotFoundError(f"config.default.json이 없습니다: {DEFAULT_PATH}")

    with open(DEFAULT_PATH, encoding="utf-8") as f:
        raw = json.load(f)

    # 설명용 키 제거
    result = {k: v for k, v in raw.items() if k not in _GUIDE_KEYS}

    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            try:
                _deep_merge(result, json.load(f))
                logger.info("[Config] config.json 로드 완료")
            except json.JSONDecodeError as e:
                logger.error(f"[Config] config.json 파싱 실패 — 기본값으로 실행합니다: {e}")
    else:
        logger.warning(
            "[Config] config.json 없음. config.default.json 기본값으로 실행합니다.\n"
            f"          → {CONFIG_PATH} 파일을 생성하고 설정값을 입력하세요."
        )

    _cache = result
    return _cache


def get(path: str, fallback=None):
    """
    점(.) 경로로 설정값을 조회합니다.

    Args:
        path:     "mcp.windows_mcp.python_path" 형태의 점 경로
        fallback: 경로가 없을 때 반환할 기본값 (기본: None)

    Examples:
        cfg.get("mcp.windows_mcp.python_path")      # "C:/..."
        cfg.get("mcp.windows_mcp")                  # {"enabled": true, ...}
        cfg.get("mcp.notion_mcp.enabled", False)    # True / False
    """
    node = load()
    for key in path.split("."):
        if not isinstance(node, dict):
            return fallback
        node = node.get(key)
        if node is None:
            return fallback
    return node


def save(values: dict) -> None:
    """
    변경된 값을 config.json에 저장합니다.
    전달한 섹션/키만 업데이트되며 나머지는 유지됩니다. (deep merge)

    Examples:
        cfg.save({"mcp": {"windows_mcp": {"python_path": "C:/..."}}})
        cfg.save({"mcp": {"workspace_mcp": {"enabled": True}}})
    """
    global _cache

    existing: dict = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                logger.warning("[Config] 기존 config.json 파싱 실패 — 덮어씁니다.")

    _deep_merge(existing, values)

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)

    # 캐시 무효화 → 다음 get() 호출 시 재로드
    _cache = None
    logger.info("[Config] config.json 저장 완료")


def _deep_merge(base: dict, override: dict) -> None:
    """override를 base에 재귀 병합합니다. (base 직접 수정)"""
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = v