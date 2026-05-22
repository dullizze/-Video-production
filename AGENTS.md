# AGENTS.md — 에이전트 인수인계 문서

> 이 레포의 작업을 맡는 AI 에이전트(Codex, Claude Code 등)를 위한 **단일 출발점**이다.
> 상세 기획은 [PRD.md](PRD.md). 실행/구조 요약은 [README.md](README.md).
>
> **규칙: 의미 있는 작업을 끝낼 때마다 이 파일의 §2(현재 상태)·§3(다음 작업)·§7(이력)을 갱신할 것.**

---

## 0. 1분 요약
- **제품**: 주제 한 줄 → 정보/지식형 9:16 YouTube 쇼츠 자동 생성.
- **방향 전환**: 개인용 로컬 CLI(v1, 동작함) → **판매형 웹 SaaS(v2, 구현 예정)**. 상세는 PRD.md §0.
- **실행**: Docker (§1).
- **언어/대상**: 한국어 콘텐츠.

## 1. 실행 방법 (Docker)
전제: Docker Desktop/Engine.
```bash
git clone https://github.com/gyeongwonKR/dullizze.git
cd dullizze
cp .env.example .env          # ANTHROPIC_API_KEY 등 입력 (레포에 .env 없음)
docker compose build          # 최초 1회 (몇 분)
docker compose run --rm shorts "클레오파트라는 이집트인이 아니었다" --no-upload
```
- 산출물: 호스트 `runs/<날짜>/final.mp4` (compose 볼륨).
- 단계별 산출물·로그: `runs/<날짜>/` (script.json, voice.mp3, assets/, captions.json, logs/).

## 2. 현재 상태 (완료)
- **Phase 0 — 환경**: Dockerfile에 박제(ffmpeg 4.4.2, Python 3.11, Node 20, Remotion 4.x, fonts-nanum). 컨테이너 내 Remotion/Chromium/Python 검증 완료.
- **Phase 1 — 단일 영상**: `pipeline/`(config, main, steps: script_gen·tts·visuals·captions·render) + `remotion/`. end-to-end 동작 확인("클레오파트라…" 45초, 9:16 1080×1920, 자막 동기화, 한글 정상).
- 파이프라인 흐름: ① 주제 → ② 대본(Claude) → ③ TTS(edge-tts, 경계 추출) → ④ 이미지(Pollinations, A3서 Grok으로 교체 예정) → ⑤ 자막 구문 그룹핑(boundaries→captions, faster-whisper 제거됨) → ⑥ 렌더(Remotion).
- **A1 완료**: 자막이 어절 단발 → 구문 단위. `tts.py`가 `boundaries.json`(문장경계) 생성, `captions.py`가 구문으로 분할. `faster-whisper` 의존성 제거됨.

## 3. 다음 작업 (우선순위, PRD §14)
- [x] **A1 — 자막 구문 그룹핑 + faster-whisper 제거** (PRD §7, 완료 2026-05-22). 타이밍을 TTS 경계로 바꾸고 어절을 "한 호흡=한 줄"로 묶음. edge-tts 한국어는 **SentenceBoundary**만 주므로(WordBoundary 아님) 문장을 구문으로 쪼개고 글자수 비례로 시간 분배. 검증: 문장 3개→구문 6개(어절 단발 0건).
- [ ] **A3 — 유료 이미지(Flux)·유료 TTS 연동 + 폴백.** 완료기준: 안정적 5장 < 30초, 보이스 교체 가능.
- [ ] **A2 — 카테고리별 고정 템플릿** (PRD §6). AI는 내용만, 디자인은 템플릿. props 스키마 검증.
- [ ] **A4 — 대본 모델 Haiku 4.5 전환 + 프롬프트 캐싱** (PRD §8).
- 이후 **B**(멀티테넌트 백엔드) · **C**(웹 프론트/온보딩) · **D**(YouTube 업로드/쿼터/과금) · **E**(운영/스케일). PRD §14.

## 4. 코딩 규칙
- Python: type hint 사용, `ruff` 통과. 비동기 다운로드는 `asyncio`.
- **모든 단계 멱등**: 중간 산출물 있으면 스킵(재시작 가능). 같은 날짜 `runs/<date>/`에 이전 결과 있으면 재사용되니, 새 실행 전 정리 필요.
- 에러는 던지지 말고 **단계별로 잡아 로그·기록**(파이프라인 중단 방지).
- **키 하드코딩 금지** (`.env` + `python-dotenv`). 로그는 `runs/<date>/logs/`.
- 영상 규격: 9:16 **1080×1920**, **30~60초**.
- 변경은 최소·외과적으로. 무관한 리팩터 금지.

## 5. 함정 / 실무 메모 (꼭 읽을 것)
- **Pollinations.ai**: 익명 티어가 동시 요청을 `402 Payment Required`(rate limit)로 막음 → `pipeline/steps/visuals.py`는 **순차+1초 간격**으로 처리. 신규 5장 다운로드가 느림(최대 ~6분). → v2에서 **유료 Flux로 대체** 예정.
- **ffmpeg 4.4.2**: Ubuntu 22.04 기본. PRD 표의 6.0+ 아님. `libx264 -crf 23` 인코딩엔 충분.
- **대본 모델**: 기본 `claude-sonnet-4-6` (`.env` `CLAUDE_MODEL`로 변경). 대본이 길어지면 60초 초과 가능 → `script_gen.py` 프롬프트에 길이 하드캡(현재 380자).
- **자막(A1 해결됨)**: edge-tts 한국어 보이스는 **SentenceBoundary**만 줌(WordBoundary 미제공). `captions.py`가 문장→구문 분할 + 글자수 비례 시간 분배. 문장 내 타이밍은 근사(문장 경계는 정확). 그룹핑 기준은 `config.py` `CAPTION_MAX_CHARS/WORDS/MS/PAUSE_MS`.
- **한글 폰트**: Docker에 `fonts-nanum` 설치, Remotion 자막은 `NanumGothic` 사용(미설치 시 □□□ 깨짐).
- **⚠️ 보안**: 초기 `ANTHROPIC_API_KEY`가 채팅에 평문 노출된 적 있음 → **반드시 폐기·재발급** 후 `.env`에 새 키 입력.

## 6. 위치 / 환경
- **정규 위치**: 이 레포(`github.com/gyeongwonKR/dullizze`). 편집·실행 모두 여기서 Docker로.
- 옛 WSL 작업본(`Ubuntu-22.04:/root/shorts-pipeline`)은 삭제됨. Docker용 `docker-desktop` 배포판은 건드리지 말 것.
- `.env`, `runs/`, `node_modules/`, `*.mp4` 등은 `.gitignore`로 커밋 제외.

## 7. 상태 변경 이력 (작업 끝나면 한 줄씩 추가)
- 2026-05-22: Phase 0·1 완료, PRD v2.0(웹 SaaS) 작성, Docker화, GitHub 초기 푸시, AGENTS.md 생성.
- 2026-05-22: **A1 완료** — 자막 구문 그룹핑(`tts.py`+`captions.py`), faster-whisper 제거, Docker 재빌드 검증. 다음: A3(Grok 이미지 + API TTS).
