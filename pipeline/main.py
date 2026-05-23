"""마스터 파이프라인 엔트리 포인트 (Phase 1: 단일 영상 수동 생성)."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

from pipeline import accounts
from pipeline import config
from pipeline import jobs
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


def run(
    topic: str,
    tone: str | None = None,
    no_upload: bool = True,
    template: str | None = None,
    job_id: str | None = None,
    user_id: str | None = None,
    plan: str | None = None,
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
    out_dir: Path | None = None,
) -> Path:
    job_id = config.validate_job_id(job_id) if job_id else config.new_job_id()
    out = out_dir or config.run_dir(job_id=job_id)
    (out / "assets").mkdir(parents=True, exist_ok=True)
    (out / "logs").mkdir(parents=True, exist_ok=True)
    log = _setup_logging(out)
    selected_template = template or config.TEMPLATE
    selected_tone = tone or config.DEFAULT_TONE
    selected_visual_mode = config.validate_visual_mode(visual_mode)
    selected_visual_provider = config.validate_visual_provider(visual_provider)
    job_path = out / "job.json"
    if job_path.exists():
        job = jobs.read_job_path(job_path)
        job.update(
            {
                "topic": topic,
                "tone": selected_tone,
                "template": selected_template,
                "user_id": job.get("user_id") or user_id or config.DEFAULT_USER_ID,
                "plan": job.get("plan") or plan or config.DEFAULT_PLAN,
                "visual_mode": job.get("visual_mode") or selected_visual_mode,
                "visual_provider": job.get("visual_provider") or selected_visual_provider,
                "preset_id": job.get("preset_id") or preset_id,
                "voice": job.get("voice") or config.normalize_voice(voice),
                "model": job.get("model") or config.normalize_model(model),
                "channel_name": job.get("channel_name") or channel_name or "",
                "footer_main": job.get("footer_main") or footer_main or "",
                "footer_accent": job.get("footer_accent") or footer_accent or "",
                "accent_color": job.get("accent_color") or config.normalize_accent_color(accent_color),
                "headline_main": job.get("headline_main") or (headline_main or "").strip(),
                "headline_accent": job.get("headline_accent") or (headline_accent or "").strip(),
                "status": "running",
                "step": "start",
                "error": None,
            }
        )
        job.setdefault("artifacts", {})
        jobs.write_job(out, job)
    else:
        # 프리셋 해석은 create_manifest가 한다(명시 > 프리셋 > 기본) → 원본 값 그대로 전달.
        job = jobs.create_manifest(
            topic,
            tone,
            template,
            job_id,
            user_id,
            plan,
            "running",
            "start",
            visual_mode=visual_mode,
            visual_provider=visual_provider,
            preset_id=preset_id,
            voice=voice,
            model=model,
            channel_name=channel_name,
            footer_main=footer_main,
            footer_accent=footer_accent,
            accent_color=accent_color,
            headline_main=headline_main,
            headline_accent=headline_accent,
        )
    selected_template = job.get("template") or selected_template
    selected_tone = job.get("tone") or selected_tone
    selected_voice = job.get("voice") or config.normalize_voice(voice)
    selected_model = job.get("model") or config.normalize_model(model)
    selected_visual_mode = job.get("visual_mode") or selected_visual_mode
    selected_visual_provider = job.get("visual_provider") or selected_visual_provider
    log.info(
        "=== 파이프라인 시작: %r → %s (visual=%s/%s) ===",
        topic,
        out,
        selected_visual_mode,
        selected_visual_provider,
    )

    def step(num: int, name: str, fn):
        t0 = time.time()
        job["status"] = "running"
        job["step"] = name
        jobs.write_job(out, job)
        log.info("[%d] %s ...", num, name)
        try:
            result = fn()
        except Exception as e:
            job["status"] = "failed"
            job["error"] = {"step": name, "message": str(e)}
            jobs.write_job(out, job)
            log.exception("[%d] %s 실패", num, name)
            raise
        log.info("[%d] %s 완료 (%.1fs)", num, name, time.time() - t0)
        return result

    script = step(2, "스크립트 생성", lambda: script_gen.generate(topic, out, selected_tone, model=selected_model))
    job["artifacts"]["script"] = "script.json"
    mp3 = step(3, "TTS", lambda: tts.synthesize(script["narration"], out, voice=selected_voice))
    job["artifacts"]["audio"] = jobs.rel(out, mp3)
    job["artifacts"]["boundaries"] = "boundaries.json"
    assets = step(
        4,
        "비주얼 수집",
        lambda: visuals.collect(
            script["visual_prompts"],
            out,
            visual_mode=selected_visual_mode,
            visual_provider=selected_visual_provider,
        ),
    )
    job["artifacts"]["assets"] = [jobs.rel(out, asset) for asset in assets]
    job["artifacts"]["visuals"] = "visuals.json"
    caps = step(5, "자막 그룹핑", lambda: captions.build(out))
    job["artifacts"]["captions"] = "captions.json"
    title = script.get("title") or script.get("hook") or topic
    overlay = {
        # 사용자가 입력한 헤드라인이 있으면 우선, 없으면 AI 대본값.
        "headlineMain": job.get("headline_main") or script.get("headline_main") or script.get("hook") or "",
        "headlineAccent": job.get("headline_accent") or script.get("headline_accent") or "",
        "channelName": job.get("channel_name") or "",
        "footerMain": job.get("footer_main") or "",
        "footerAccent": job.get("footer_accent") or "",
        "accentColor": job.get("accent_color") or config.DEFAULT_ACCENT_COLOR,
    }
    final = step(
        6,
        "영상 합성",
        lambda: render.render(mp3, caps, assets, out, selected_template, title, overlay=overlay),
    )
    job["artifacts"]["props"] = "props.json"
    job["artifacts"]["video"] = jobs.rel(out, final)
    job["status"] = "done"
    job["step"] = "done"
    job["error"] = None
    job["quota"] = accounts.quota_snapshot(job.get("user_id"), job.get("plan"))
    jobs.write_job(out, job)

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
    parser.add_argument("--visual-mode", default=None, help="비주얼 모드: auto | motion_image | stock_video | ai_video")
    parser.add_argument("--visual-provider", default=None, help="비주얼 provider: auto | xai | kie | pexels | pixabay | local")
    parser.add_argument("--preset-id", default=None, help="프리셋 ID (지정 시 저장된 설정을 base로 사용)")
    parser.add_argument("--voice", default=None, help="TTS 보이스 (기본: .env DEFAULT_VOICE)")
    parser.add_argument("--model", default=None, help="대본 모델 (기본: .env CLAUDE_MODEL)")
    parser.add_argument("--channel-name", default=None, help="banner 상단 채널 라인")
    parser.add_argument("--footer-main", default=None, help="banner 하단 흰색 문구")
    parser.add_argument("--footer-accent", default=None, help="banner 하단 강조 문구")
    parser.add_argument("--accent-color", default=None, help="banner 강조색 (기본: .env DEFAULT_ACCENT_COLOR)")
    parser.add_argument("--headline-main", default=None, help="banner 상단 헤드라인 1줄 (비우면 AI 대본값)")
    parser.add_argument("--headline-accent", default=None, help="banner 상단 헤드라인 2줄/강조 (비우면 AI 대본값)")
    parser.add_argument("--job-id", default=None, help="작업 ID (기본: 자동 생성)")
    args = parser.parse_args()
    run(
        args.topic,
        tone=args.tone,
        no_upload=args.no_upload or True,
        template=args.template,
        job_id=args.job_id,
        visual_mode=args.visual_mode,
        visual_provider=args.visual_provider,
        preset_id=args.preset_id,
        voice=args.voice,
        model=args.model,
        channel_name=args.channel_name,
        footer_main=args.footer_main,
        footer_accent=args.footer_accent,
        accent_color=args.accent_color,
        headline_main=args.headline_main,
        headline_accent=args.headline_accent,
    )


if __name__ == "__main__":
    main()
