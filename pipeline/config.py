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
KNOWN_TEMPLATES = ("documentary", "pop", "banner")
TEMPLATE = os.getenv("TEMPLATE", "documentary")  # documentary | pop | banner
# 사용자에게 보여줄 한국어 "형" 이름(영상 제작 전 선택지). 내부 키는 그대로.
TEMPLATE_LABELS = {
    "documentary": "기본형",
    "pop": "팝형",
    "banner": "배너형",
}
# banner 템플릿(레터박스/밴드형) 강조색 기본값. 프리셋 accent_color로 덮어쓸 수 있음.
DEFAULT_ACCENT_COLOR = os.getenv("DEFAULT_ACCENT_COLOR", "#ff4fa3")

# --- BGM (배경음악) ---
# 음원은 assets/bgm/<파일>에 두고, 없으면 BGM 없이 정상 렌더(안전 fallback).
BGM_ENABLED = os.getenv("BGM_ENABLED", "1").lower() in {"1", "true", "yes", "on"}
BGM_DIR = ROOT / "assets" / "bgm"
TEMPLATE_BGM = {"documentary": "documentary.mp3", "pop": "pop.mp3"}
BGM_VOLUME_DB = float(os.getenv("BGM_VOLUME_DB", "-22"))  # 음성 우선(-20~-26dB 권장)
BGM_FADE_MS = int(os.getenv("BGM_FADE_MS", "800"))        # fade in/out 길이

# --- 자막 (TTS 단어경계 기반 구문 그룹핑) ---
# 어절을 "한 호흡 = 한 줄"로 묶는 기준. 아래 중 하나라도 충족하면 줄을 끊는다.
CAPTION_MAX_CHARS = int(os.getenv("CAPTION_MAX_CHARS", "16"))   # 한 줄 최대 글자수(공백 제외)
CAPTION_MAX_WORDS = int(os.getenv("CAPTION_MAX_WORDS", "4"))    # 한 줄 최대 어절수
CAPTION_MAX_MS = int(os.getenv("CAPTION_MAX_MS", "2500"))       # 한 줄 최대 표시시간
CAPTION_PAUSE_MS = int(os.getenv("CAPTION_PAUSE_MS", "400"))    # 이만큼 멈추면 끊기

# --- 비주얼 ---
NUM_VISUALS = int(os.getenv("NUM_VISUALS", "5"))
VISUAL_MODES = ("auto", "motion_image", "stock_video", "ai_video")
VISUAL_PROVIDERS = ("auto", "xai", "kie", "pexels", "pixabay", "local")
DEFAULT_VISUAL_MODE = os.getenv("DEFAULT_VISUAL_MODE", "motion_image")
DEFAULT_VISUAL_PROVIDER = os.getenv("DEFAULT_VISUAL_PROVIDER", "auto")
# Grok 이미지(xAI). 키 없으면 Pollinations 폴백.
# 모델: grok-imagine-image(표준) | grok-imagine-image-quality(고품질).
XAI_API_KEY = os.getenv("XAI_API_KEY", "")
XAI_IMAGE_MODEL = os.getenv("XAI_IMAGE_MODEL", "grok-imagine-image")
KIE_API_KEY = os.getenv("KIE_API_KEY", "")

JOB_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
USER_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.@-]{0,63}$")
PRESET_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")

# --- 프리셋 (생성 설정 묶음 = 주제 제외한 스타일 레시피) ---
PRESETS_DIR = ROOT / "data" / "presets"

# --- SaaS 준비: 임시 사용자/플랜 ---
DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "local")
DEFAULT_PLAN = os.getenv("DEFAULT_PLAN", "free")
PLAN_MONTHLY_QUOTAS = {
    "free": int(os.getenv("FREE_MONTHLY_QUOTA", "3")),
    "basic": int(os.getenv("BASIC_MONTHLY_QUOTA", "30")),
    "pro": int(os.getenv("PRO_MONTHLY_QUOTA", "100")),
}


def new_job_id() -> str:
    """로컬 파일 시스템에서 쓰기 쉬운 짧은 작업 ID."""
    return f"{datetime.now().strftime('%H%M%S')}-{uuid.uuid4().hex[:8]}"


def validate_job_id(job_id: str) -> str:
    """경로 탈출을 막기 위해 안전한 job_id만 허용."""
    if not JOB_ID_RE.fullmatch(job_id):
        raise ValueError("job_id는 영문/숫자로 시작하고 영문·숫자·_·-·.만 사용할 수 있습니다.")
    return job_id


def validate_user_id(user_id: str) -> str:
    """임시 파일 기반 사용자 ID 검증."""
    if not USER_ID_RE.fullmatch(user_id):
        raise ValueError("user_id는 영문/숫자로 시작하고 영문·숫자·_·-·.·@만 사용할 수 있습니다.")
    return user_id


def validate_visual_mode(mode: str | None) -> str:
    """사용자 선택 비주얼 모드 검증."""
    mode = (mode or DEFAULT_VISUAL_MODE).strip().lower()
    if mode not in VISUAL_MODES:
        raise ValueError(f"visual_mode는 {', '.join(VISUAL_MODES)} 중 하나여야 합니다.")
    return mode


def validate_visual_provider(provider: str | None) -> str:
    """사용자 선택 비주얼 provider 검증."""
    provider = (provider or DEFAULT_VISUAL_PROVIDER).strip().lower()
    if provider not in VISUAL_PROVIDERS:
        raise ValueError(f"visual_provider는 {', '.join(VISUAL_PROVIDERS)} 중 하나여야 합니다.")
    return provider


def validate_template(template: str | None) -> str:
    """영상 디자인 템플릿 검증."""
    template = (template or TEMPLATE).strip().lower()
    if template not in KNOWN_TEMPLATES:
        raise ValueError(f"template은 {', '.join(KNOWN_TEMPLATES)} 중 하나여야 합니다.")
    return template


def template_options() -> list[dict[str, str]]:
    """영상 제작 전 선택지: [{value, label}] (한국어 '형' 이름)."""
    return [{"value": t, "label": TEMPLATE_LABELS.get(t, t)} for t in KNOWN_TEMPLATES]


def normalize_voice(voice: str | None) -> str:
    """TTS 보이스 정규화(빈 값이면 기본 보이스)."""
    return (voice or DEFAULT_VOICE).strip()


def normalize_model(model: str | None) -> str:
    """대본 모델 정규화(빈 값이면 기본 모델). 전체 모델 ID 문자열을 받는다."""
    return (model or CLAUDE_MODEL).strip()


def normalize_accent_color(color: str | None) -> str:
    """banner 강조색 정규화(빈 값이면 기본 강조색)."""
    return (color or DEFAULT_ACCENT_COLOR).strip()


def validate_preset_id(preset_id: str) -> str:
    """경로 탈출을 막기 위해 안전한 preset_id만 허용."""
    if not PRESET_ID_RE.fullmatch(preset_id):
        raise ValueError("preset_id는 영문/숫자로 시작하고 영문·숫자·_·-·.만 사용할 수 있습니다.")
    return preset_id


def new_preset_id() -> str:
    """짧고 안전한 프리셋 ID."""
    return f"preset-{uuid.uuid4().hex[:8]}"


def bgm_linear_volume() -> float:
    """BGM 데시벨(dB)을 Remotion volume용 선형 배율로 변환."""
    return round(10 ** (BGM_VOLUME_DB / 20), 4)


def run_dir(d: date | None = None, job_id: str | None = None) -> Path:
    """runs/YYYY-MM-DD/<job_id>/ 경로 반환 (없으면 생성)."""
    d = d or date.today()
    job_id = validate_job_id(job_id or new_job_id())
    p = ROOT / "runs" / d.isoformat() / job_id
    (p / "assets").mkdir(parents=True, exist_ok=True)
    (p / "logs").mkdir(parents=True, exist_ok=True)
    return p
