"""④ 비주얼 수집: 현재는 이미지 기반, 영상 provider는 manifest에 자리만 만든다.

XAI_API_KEY가 있으면 Grok 이미지 API, 없으면 Pollinations.ai 폴백(키 불필요).
9:16 프레이밍은 렌더 단계(Remotion objectFit:cover)에서 처리한다.
"""
from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from urllib.parse import quote

import aiohttp

from pipeline import config

POLLINATIONS = "https://image.pollinations.ai/prompt/"
XAI_IMAGES = "https://api.x.ai/v1/images/generations"


async def _fetch_grok(session: aiohttp.ClientSession, prompt: str, out: Path, retries: int = 3) -> Path:
    headers = {"Authorization": f"Bearer {config.XAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": config.XAI_IMAGE_MODEL,
        "prompt": prompt,
        "n": 1,
        "response_format": "b64_json",
    }
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            async with session.post(
                XAI_IMAGES, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=120),
            ) as resp:
                resp.raise_for_status()
                body = await resp.json()
            data = base64.b64decode(body["data"][0]["b64_json"])
            if len(data) < 1000:
                raise RuntimeError(f"이미지가 너무 작음({len(data)}B)")
            out.write_bytes(data)
            return out
        except Exception as e:  # noqa: BLE001 - 단계별로 잡아 재시도
            if attempt == retries:
                raise
            print(f"  [visuals/grok] {out.name} 시도 {attempt} 실패({e!r}), {delay:.0f}s 후 재시도")
            await asyncio.sleep(delay)
            delay *= 2
    return out


async def _fetch_pollinations(session: aiohttp.ClientSession, prompt: str, out: Path, seed: int, retries: int = 3) -> Path:
    url = (
        POLLINATIONS
        + quote(prompt)
        + f"?width={config.VIDEO_WIDTH}&height={config.VIDEO_HEIGHT}&nologo=true&seed={seed}"
    )
    delay = 2.0
    for attempt in range(1, retries + 1):
        try:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=120)) as resp:
                resp.raise_for_status()
                data = await resp.read()
            if len(data) < 1000:
                raise RuntimeError(f"이미지가 너무 작음({len(data)}B)")
            out.write_bytes(data)
            return out
        except Exception as e:  # noqa: BLE001 - 단계별로 잡아 재시도
            if attempt == retries:
                raise
            print(f"  [visuals/pollinations] {out.name} 시도 {attempt} 실패({e!r}), {delay:.0f}s 후 재시도")
            await asyncio.sleep(delay)
            delay *= 2
    return out


def _resolve_image_provider() -> str:
    return "xai" if config.XAI_API_KEY else "pollinations"


def _fallback_reason(mode: str, provider: str) -> str | None:
    if mode in {"stock_video", "ai_video"}:
        return f"{mode}/{provider} provider는 아직 실험 전이라 motion_image로 대체했습니다."
    if provider not in {"auto", "xai", "local"}:
        return f"{provider} provider는 아직 실험 전이라 기본 이미지 provider로 대체했습니다."
    if provider == "xai" and not config.XAI_API_KEY:
        return "XAI_API_KEY가 없어 Pollinations 이미지 provider로 대체했습니다."
    return None


async def _gather(prompts: list[str], assets_dir: Path, image_provider: str) -> list[Path]:
    use_grok = image_provider == "xai"
    results: list[Path] = []
    async with aiohttp.ClientSession() as session:
        for i, p in enumerate(prompts):
            out = assets_dir / f"{i:03d}.jpg"
            if out.exists() and out.stat().st_size > 0:  # 멱등: 캐시 재사용
                results.append(out)
                continue
            if use_grok:
                results.append(await _fetch_grok(session, p, out))
            else:
                if i > 0:
                    await asyncio.sleep(1.0)  # Pollinations 익명 티어 rate limit 회피
                results.append(await _fetch_pollinations(session, p, out, seed=i))
    return results


def collect(
    prompts: list[str],
    out_dir: Path,
    visual_mode: str | None = None,
    visual_provider: str | None = None,
) -> list[Path]:
    """비주얼 프롬프트 목록 → assets/*.jpg. 이미 있으면 재사용(멱등)."""
    requested_mode = config.validate_visual_mode(visual_mode)
    requested_provider = config.validate_visual_provider(visual_provider)
    image_provider = _resolve_image_provider()
    assets_dir = out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets = asyncio.run(_gather(prompts, assets_dir, image_provider))
    manifest = {
        "requested_mode": requested_mode,
        "requested_provider": requested_provider,
        "effective_mode": "motion_image",
        "effective_provider": image_provider,
        "fallback_reason": _fallback_reason(requested_mode, requested_provider),
        "items": [
            {
                "type": "image",
                "path": f"assets/{asset.name}",
                "prompt": prompts[i] if i < len(prompts) else "",
                "source": image_provider,
            }
            for i, asset in enumerate(assets)
        ],
    }
    (out_dir / "visuals.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return assets
