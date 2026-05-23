"""파일 기반 job manifest 유틸리티."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pipeline import accounts
from pipeline import config
from pipeline import presets


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def rel(out_dir: Path, path: Path) -> str:
    return path.relative_to(out_dir).as_posix()


def write_job(out_dir: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = now_iso()
    (out_dir / "job.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def create_manifest(
    topic: str,
    tone: str | None = None,
    template: str | None = None,
    job_id: str | None = None,
    user_id: str | None = None,
    plan: str | None = None,
    status: str = "pending",
    step: str = "created",
    overwrite: bool = True,
    visual_mode: str | None = None,
    visual_provider: str | None = None,
    preset_id: str | None = None,
    voice: str | None = None,
    model: str | None = None,
    channel_name: str | None = None,
    footer_main: str | None = None,
    footer_accent: str | None = None,
    accent_color: str | None = None,
    headline_main: str | None = None,
    headline_accent: str | None = None,
) -> dict[str, Any]:
    job_id = config.validate_job_id(job_id) if job_id else config.new_job_id()
    user_id = accounts.normalize_user_id(user_id)
    plan = accounts.normalize_plan(plan)
    # 프리셋(있으면)을 base로 깔고, 명시값이 우선(명시 > 프리셋 > 시스템 기본).
    resolved = presets.resolve(user_id, preset_id)
    template = config.validate_template(template or resolved.get("template"))
    tone = (tone or resolved.get("tone") or config.DEFAULT_TONE).strip()
    visual_mode = config.validate_visual_mode(visual_mode or resolved.get("visual_mode"))
    visual_provider = config.validate_visual_provider(
        visual_provider or resolved.get("visual_provider")
    )
    voice = config.normalize_voice(voice or resolved.get("voice"))
    model = config.normalize_model(model or resolved.get("model"))
    channel_name = (channel_name or resolved.get("channel_name") or "").strip()
    footer_main = (footer_main or resolved.get("footer_main") or "").strip()
    footer_accent = (footer_accent or resolved.get("footer_accent") or "").strip()
    accent_color = config.normalize_accent_color(accent_color or resolved.get("accent_color"))
    # 헤드라인은 주제별 콘텐츠 → 프리셋 상속 없이 명시값만(비우면 AI 대본값을 렌더 단계에서 사용).
    headline_main = (headline_main or "").strip()
    headline_accent = (headline_accent or "").strip()
    out_dir = config.run_dir(job_id=job_id)
    if not overwrite and (out_dir / "job.json").exists():
        raise FileExistsError(f"이미 존재하는 job_id입니다: {job_id}")
    job = {
        "job_id": job_id,
        "topic": topic,
        "tone": tone,
        "template": template,
        "user_id": user_id,
        "plan": plan,
        "preset_id": preset_id,
        "voice": voice,
        "model": model,
        "channel_name": channel_name,
        "footer_main": footer_main,
        "footer_accent": footer_accent,
        "accent_color": accent_color,
        "headline_main": headline_main,
        "headline_accent": headline_accent,
        "visual_mode": visual_mode,
        "visual_provider": visual_provider,
        "quota": accounts.quota_snapshot(user_id, plan, exclude_job_id=job_id),
        "status": status,
        "step": step,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "run_dir": str(out_dir.relative_to(config.ROOT)),
        "artifacts": {},
        "error": None,
    }
    write_job(out_dir, job)
    return job


def read_job_path(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def find_job_dir(job_id: str, run_date: date | str | None = None) -> Path:
    job_id = config.validate_job_id(job_id)
    runs_root = config.ROOT / "runs"
    if run_date is not None:
        date_text = run_date.isoformat() if isinstance(run_date, date) else run_date
        candidate = runs_root / date_text / job_id
        if (candidate / "job.json").exists():
            return candidate
        raise FileNotFoundError(f"job을 찾을 수 없습니다: {date_text}/{job_id}")

    matches = sorted(
        (p.parent for p in runs_root.glob(f"*/{job_id}/job.json")),
        key=lambda p: p.as_posix(),
        reverse=True,
    )
    if not matches:
        raise FileNotFoundError(f"job을 찾을 수 없습니다: {job_id}")
    return matches[0]


def read_job(job_id: str, run_date: date | str | None = None) -> dict[str, Any]:
    return read_job_path(find_job_dir(job_id, run_date) / "job.json")
