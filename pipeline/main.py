"""마스터 파이프라인 엔트리 포인트 (Phase 1: 단일 영상 수동 생성)."""
from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

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


def run(topic: str, tone: str | None = None, no_upload: bool = True) -> Path:
    out = config.run_dir()
    log = _setup_logging(out)
    log.info("=== 파이프라인 시작: %r → %s ===", topic, out)

    def step(num: int, name: str, fn):
        t0 = time.time()
        log.info("[%d] %s ...", num, name)
        try:
            result = fn()
        except Exception:
            log.exception("[%d] %s 실패", num, name)
            raise
        log.info("[%d] %s 완료 (%.1fs)", num, name, time.time() - t0)
        return result

    script = step(2, "스크립트 생성", lambda: script_gen.generate(topic, out, tone))
    mp3 = step(3, "TTS", lambda: tts.synthesize(script["narration"], out))
    assets = step(4, "비주얼 수집", lambda: visuals.collect(script["visual_prompts"], out))
    caps = step(5, "자막 그룹핑", lambda: captions.build(out))
    final = step(6, "영상 합성", lambda: render.render(mp3, caps, assets, out))

    log.info("=== 완료: %s ===", final)
    if not no_upload:
        log.info("(업로드는 Phase 4에서 구현 — 지금은 --no-upload 동작)")
    return final


def main() -> None:
    parser = argparse.ArgumentParser(description="YouTube 쇼츠 자동 생성 (Phase 1)")
    parser.add_argument("topic", help="영상 주제 (한 줄)")
    parser.add_argument("--no-upload", action="store_true", help="업로드 생략 (Phase 1 기본)")
    parser.add_argument("--tone", default=None, help="톤 (기본: .env DEFAULT_TONE)")
    args = parser.parse_args()
    run(args.topic, tone=args.tone, no_upload=args.no_upload or True)


if __name__ == "__main__":
    main()
