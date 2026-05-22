"""⑤ 자막 그룹핑: boundaries.json → captions.json (구문 단위).

어절(띄어쓰기)마다 단발로 표시되던 문제를 해결한다. "한 호흡 = 한 줄" 원칙.

타이밍 소스는 TTS 경계(boundaries.json). edge-tts 한국어 보이스는 보통
**문장경계(SentenceBoundary)**를 주므로, 각 문장을 구문으로 쪼개고 시간을
글자수에 비례해 분배한다. (단어경계가 오는 보이스면 어절을 묶는다.)

줄 끊기 기준(하나라도 충족 시): 절 부호(. ! ? … ,) / 글자수≥CAPTION_MAX_CHARS /
어절수≥CAPTION_MAX_WORDS. 빈 자막은 만들지 않는다(불변식).
"""
from __future__ import annotations

import json
from pathlib import Path

from pipeline import config

_BREAK_PUNCT = (".", "!", "?", "…", ",", "。", "！", "？", "，")


def _ends_clause(text: str) -> bool:
    return text.rstrip().endswith(_BREAK_PUNCT)


def _chunk_eojeols(text: str) -> list[str]:
    """문장 텍스트를 구문(한 줄) 단위 어절 묶음으로 분할."""
    chunks: list[str] = []
    cur: list[str] = []
    eojeols = text.split()
    for j, e in enumerate(eojeols):
        cur.append(e)
        chars = sum(len(x) for x in cur)
        is_last = j + 1 == len(eojeols)
        if (
            is_last
            or _ends_clause(e)
            or chars >= config.CAPTION_MAX_CHARS
            or len(cur) >= config.CAPTION_MAX_WORDS
        ):
            chunks.append(" ".join(cur).strip())
            cur = []
    return [c for c in chunks if c]


def _split_sentence(item: dict) -> list[dict]:
    """문장경계 1개 → 구문들. 시간은 글자수 비례 분배."""
    chunks = _chunk_eojeols(item["text"])
    if not chunks:
        return []
    start, end = item["startMs"], item["endMs"]
    span = max(end - start, 1)
    weights = [len(c.replace(" ", "")) or 1 for c in chunks]
    total = sum(weights)
    phrases: list[dict] = []
    t = start
    for c, w in zip(chunks, weights):
        dur = round(span * w / total)
        phrases.append({"text": c, "startMs": t, "endMs": t + dur})
        t += dur
    phrases[-1]["endMs"] = end  # 마지막은 문장 끝에 정확히 맞춤
    return phrases


def _group_words(words: list[dict]) -> list[dict]:
    """단어경계 → 구문 묶음(어절 누적)."""
    phrases: list[dict] = []
    cur: list[dict] = []
    for i, w in enumerate(words):
        cur.append(w)
        chars = sum(len(x["text"]) for x in cur)
        dur = w["endMs"] - cur[0]["startMs"]
        is_last = i + 1 == len(words)
        gap = None if is_last else words[i + 1]["startMs"] - w["endMs"]
        if (
            is_last
            or _ends_clause(w["text"])
            or chars >= config.CAPTION_MAX_CHARS
            or len(cur) >= config.CAPTION_MAX_WORDS
            or dur >= config.CAPTION_MAX_MS
            or (gap is not None and gap >= config.CAPTION_PAUSE_MS)
        ):
            text = " ".join(x["text"] for x in cur).strip()
            if text:
                phrases.append({"text": text, "startMs": cur[0]["startMs"], "endMs": w["endMs"]})
            cur = []
    return phrases


def _group(items: list[dict]) -> list[dict]:
    words = [i for i in items if i.get("kind") == "word"]
    if words:
        phrases = _group_words(words)
    else:
        phrases = []
        for sent in items:
            phrases.extend(_split_sentence(sent))

    # 표시 연속성: 각 구문을 다음 구문 시작까지 유지(짧은 간격 깜빡임 방지)
    for j in range(len(phrases) - 1):
        phrases[j]["endMs"] = max(phrases[j]["endMs"], phrases[j + 1]["startMs"])
    return phrases


def build(out_dir: Path) -> list[dict]:
    """boundaries.json → captions.json (구문 단위). 이미 있으면 재사용(멱등)."""
    out = out_dir / "captions.json"
    if out.exists():
        return json.loads(out.read_text(encoding="utf-8"))

    items = json.loads((out_dir / "boundaries.json").read_text(encoding="utf-8"))
    phrases = _group(items)
    out.write_text(json.dumps(phrases, ensure_ascii=False, indent=2), encoding="utf-8")
    return phrases
