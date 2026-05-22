"""중앙 설정: .env 로드 + 경로/상수."""
from __future__ import annotations

import os
import re
import uuid
from datetime import date, datetime
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
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
CLAUDE_PROMPT_CACHE = os.getenv("CLAUDE_PROMPT_CACHE", "1").lower() in {"1", "true", "yes", "on"}

# --- TTS ---
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "ko-KR-SunHiNeural")
DEFAULT_TONE = os.getenv("DEFAULT_TONE", "흥미로운_사실")

# --- 템플릿 (영상 디자인) ---
TEMPLATE = os.getenv("TEMPLATE", "documentary")  # documentary | pop

# --- 자막 (TTS 단어경계 기반 구문 그룹핑) ---
# 어절을 "한 호흡 = 한 줄"로 묶는 기준. 아래 중 하나라도 충족하면 줄을 끊는다.
CAPTION_MAX_CHARS = int(os.getenv("CAPTION_MAX_CHARS", "16"))   # 한 줄 최대 글자수(공백 제외)
CAPTION_MAX_WORDS = int(os.getenv("CAPTION_MAX_WORDS", "4"))    # 한 줄 최대 어절수
CAPTION_MAX_MS = int(os.getenv("CAPTION_MAX_MS", "2500"))       # 한 줄 최대 표시시간
CAPTION_PAUSE_MS = int(os.getenv("CAPTION_PAUSE_MS", "400"))    # 이만큼 멈추면 끊기

# --- 비주얼 ---
NUM_VISUALS = int(os.getenv("NUM_VISUALS", "5"))
# Grok 이미지(xAI). 키 없으면 Pollinations 폴백.
# 모델: grok-imagine-image(표준) | grok-imagine-image-quality(고품질).
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_IMAGE_MODEL = os.getenv("XAI_IMAGE_MODEL", "grok-imagine-image")

JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def new_job_id() -> str:
    """로컬 파일 시스템에서 쓰기 쉬운 짧은 작업 ID."""
    return f"{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}"


def validate_job_id(job_id: str) -> str:
    """경로 탈출을 막기 위해 안전한 job_id만 허용."""
    if not JOB_ID_RE.fullmatch(job_id):
        raise ValueError("job_id는 영문/숫자로 시작하고 영문·숫자·_·-·.만 사용할 수 있습니다.")
    return job_id


def run_dir(d: date | None = None, job_id: str | None = None) -> Path:
    """runs/YYYY-MM-DD/<job_id>/ 경로 반환 (없으면 생성)."""
    d = d or date.today()
    job_id = validate_job_id(job_id or new_job_id())
    p = ROOT / "runs" / d.isoformat() / job_id
    (p / "assets").mkdir(parents=True, exist_ok=True)
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p
