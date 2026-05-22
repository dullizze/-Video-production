"""파일 기반 job manifest 유틸리티."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from pipeline import accounts
from pipeline import config


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
) -> dict[str, Any]:
    job_id = config.validate_job_id(job_id) if job_id else config.new_job_id()
    user_id = accounts.normalize_user_id(user_id)
    plan = accounts.normalize_plan(plan)
    visual_mode = config.validate_visual_mode(visual_mode)
    visual_provider = config.validate_visual_provider(visual_provider)
    out_dir = config.run_dir(job_id=job_id)
    if not overwrite and (out_dir / "job.json").exists():
        raise FileExistsError(f"이미 존재하는 job_id입니다: {job_id}")
    job = {
        "job_id": job_id,
        "topic": topic,
        "tone": tone or config.DEFAULT_TONE,
        "template": template or config.TEMPLATE,
        "user_id": user_id,
        "plan": plan,
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
