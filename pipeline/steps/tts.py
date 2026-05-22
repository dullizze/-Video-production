"""③ TTS: edge-tts → voice.mp3 + boundaries.json (단어경계, 지수 백오프 재시도).

스트리밍으로 받아 오디오와 WordBoundary(단어 시작/길이)를 동시에 추출한다.
이 단어경계가 ⑤ 자막 그룹핑의 타이밍 소스가 된다(faster-whisper 불필요).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import edge_tts

from pipeline import config


async def _stream(text: str, voice: str, mp3: Path, boundaries: Path, retries: int = 3) -> None:
    delay = 2.0
    for attempt in range(1, retries + 1):
        items: list[dict] = []
        try:
            communicate = edge_tts.Communicate(text, voice)
            with mp3.open("wb") as f:
                async for chunk in communicate.stream():
                    t = chunk["type"]
                    if t == "audio":
                        f.write(chunk["data"])
                    elif t in ("WordBoundary", "SentenceBoundary"):
                        # offset/duration 단위는 100ns → ms 변환
                        start = chunk["offset"] // 10_000
                        dur = chunk["duration"] // 10_000
                        items.append(
                            {
                                "text": chunk["text"],
                                "startMs": start,
                                "endMs": start + dur,
                                "kind": "word" if t == "WordBoundary" else "sentence",
                            }
                        )
            if mp3.stat().st_size == 0:
                raise RuntimeError("빈 mp3 생성됨")
            if not items:
                raise RuntimeError("경계(Word/Sentence Boundary)가 비어 있음")
            boundaries.write_text(
                json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            return
        except Exception as e:  # noqa: BLE001 - 단계별로 잡아 재시도
            if attempt == retries:
                raise
            print(f"  [tts] 시도 {attempt} 실패({e!r}), {delay:.0f}s 후 재시도")
            await asyncio.sleep(delay)
            delay *= 2


def synthesize(text: str, out_dir: Path, voice: str | None = None) -> Path:
    """나레이션 → voice.mp3 (+ boundaries.json). 둘 다 있으면 재사용(멱등)."""
    mp3 = out_dir / "voice.mp3"
    boundaries = out_dir / "boundaries.json"
    if mp3.exists() and mp3.stat().st_size > 0 and boundaries.exists():
        return mp3
    voice = voice or config.DEFAULT_VOICE
    asyncio.run(_stream(text, voice, mp3, boundaries))
    return mp3
