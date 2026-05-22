"""중앙 설정: .env 로드 + 경로/상수."""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

# --- 영상 사양 (9:16 쇼츠) ---
VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

# --- API / 모델 ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")

# --- TTS ---
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "ko-KR-SunHiNeural")
DEFAULT_TONE = os.getenv("DEFAULT_TONE", "흥미로운_사실")

# --- 자막 (TTS 단어경계 기반 구문 그룹핑) ---
# 어절을 "한 호흡 = 한 줄"로 묶는 기준. 아래 중 하나라도 충족하면 줄을 끊는다.
CAPTION_MAX_CHARS = int(os.getenv("CAPTION_MAX_CHARS", "16"))   # 한 줄 최대 글자수(공백 제외)
CAPTION_MAX_WORDS = int(os.getenv("CAPTION_MAX_WORDS", "4"))    # 한 줄 최대 어절수
CAPTION_MAX_MS = int(os.getenv("CAPTION_MAX_MS", "2500"))       # 한 줄 최대 표시시간
CAPTION_PAUSE_MS = int(os.getenv("CAPTION_PAUSE_MS", "400"))    # 이만큼 멈추면 끊기

# --- 비주얼 ---
NUM_VISUALS = int(os.getenv("NUM_VISUALS", "5"))


def run_dir(d: date | None = None) -> Path:
    """runs/YYYY-MM-DD/ 경로 반환 (없으면 생성)."""
    d = d or date.today()
    p = ROOT / "runs" / d.isoformat()
    (p / "assets").mkdir(parents=True, exist_ok=True)
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p
