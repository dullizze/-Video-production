"""마스터 파이프라인 엔트리 포인트 (Phase 1: 단일 영상 수동 생성)."""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pipeline import config
from pipeline.steps import captions, render, script_gen, tts, visuals


def _setup_logging(out_dir: Path) -> logging.Logger:
    log = logging.getLogger("pipeline")
    log.setLevel(logging.INFO)
    log.handlers.clear()
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s", "%H:%M:%S")
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    fh = logging.FileHandler(out_dir / "logs" / "pipeline.log", encoding="utf-8")
    fh.setFormatter(fmt)
    log.addHandler(sh)
    log.addHandler(fh)
    return log


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_job(out_dir: Path, data: dict[str, Any]) -> None:
    data["updated_at"] = _now_iso()
    (out_dir / "job.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _rel(out_dir: Path, path: Path) -> str:
    return path.relative_to(out_dir).as_posix()


def run(
    topic: str,
    tone: str | None = None,
    no_upload: bool = True,
    template: str | None = None,
    job_id: str | None = None,
) -> Path:
    job_id = config.validate_job_id(job_id) if job_id else config.new_job_id()
    out = config.run_dir(job_id=job_id)
    log = _setup_logging(out)
    selected_template = template or config.TEMPLATE
    selected_tone = tone or config.DEFAULT_TONE
    job = {
        "job_id": job_id,
        "topic": topic,
        "tone": selected_tone,
        "template": selected_template,
        "status": "running",
        "step": "start",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
        "run_dir": str(out.relative_to(config.ROOT)),
        "artifacts": {},
        "error": None,
    }
    _write_job(out, job)
    log.info("=== 파이프라인 시작: %r → %s ===", topic, out)

    def step(num: int, name: str, fn):
        t0 = time.time()
        job["status"] = "running"
        job["step"] = name
        _write_job(out, job)
        log.info("[%d] %s ...", num, name)
        try:
            result = fn()
        except Exception as e:
            job["status"] = "failed"
            job["error"] = {"step": name, "message": str(e)}
            _write_job(out, job)
            log.exception("[%d] %s 실패", num, name)
            raise
        log.info("[%d] %s 완료 (%.1fs)", num, name, time.time() - t0)
        return result

    script = step(2, "스크립트 생성", lambda: script_gen.generate(topic, out, selected_tone))
    job["artifacts"]["script"] = "script.json"
    mp3 = step(3, "TTS", lambda: tts.synthesize(script["narration"], out))
    job["artifacts"]["audio"] = _rel(out, mp3)
    job["artifacts"]["boundaries"] = "boundaries.json"
    assets = step(4, "비주얼 수집", lambda: visuals.collect(script["visual_prompts"], out))
    job["artifacts"]["assets"] = [_rel(out, asset) for asset in assets]
    caps = step(5, "자막 그룹핑", lambda: captions.build(out))
    job["artifacts"]["captions"] = "captions.json"
    title = script.get("title") or script.get("hook") or topic
    final = step(6, "영상 합성", lambda: render.render(mp3, caps, assets, out, selected_template, title))
    job["artifacts"]["props"] = "props.json"
    job["artifacts"]["video"] = _rel(out, final)
    job["status"] = "done"
    job["step"] = "done"
    job["error"] = None
    _write_job(out, job)

    log.info("=== 완료: %s ===", final)
    if not no_upload:
        log.info("(업로드는 Phase 4에서 구현 — 지금은 --no-upload 동작)")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 쇼츠 자동 생성 (Phase 1)")
    parser.add_argument("topic", help="영상 주제 (한 줄)")
    parser.add_argument("--no-upload", action="store_true", help="업로드 생략 (Phase 1 기본)")
    parser.add_argument("--tone", default=None, help="톤 (기본: .env DEFAULT_TONE)")
    parser.add_argument("--template", default=None, help="템플릿: documentary | pop (기본: .env TEMPLATE)")
    parser.add_argument("--job-id", default=None, help="작업 ID (기본: 자동 생성)")
    args = parser.parse_args()
    run(
        args.topic,
        tone=args.tone,
        no_upload=args.no_upload or True,
        template=args.template,
        job_id=args.job_id,
    )


if __name__ == "__main__":
    main()
