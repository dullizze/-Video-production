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
- 산출물: 호스트 `runs/<날짜>/<job_id>/final.mp4` (compose 볼륨).
- 단계별 산출물·로그: `runs/<날짜>/<job_id>/` (job.json, script.json, voice.mp3, assets/, captions.json, logs/).

## 2. 현재 상태 (완료)
- **Phase 0 — 환경**: Dockerfile에 박제(ffmpeg 4.4.2, Python 3.11, Node 20, Remotion 4.x, fonts-nanum). 컨테이너 내 Remotion/Chromium/Python 검증 완료.
- **Phase 1 — 단일 영상**: `pipeline/`(config, main, steps: script_gen·tts·visuals·captions·render) + `remotion/`. end-to-end 동작 확인("클레오파트라…" 45초, 9:16 1080×1920, 자막 동기화, 한글 정상).
- 파이프라인 흐름: ① 주제 → ② 대본(Claude) → ③ TTS(edge-tts, 경계 추출) → ④ 이미지(Pollinations, A3서 Grok으로 교체 예정) → ⑤ 자막 구문 그룹핑(boundaries→captions, faster-whisper 제거됨) → ⑥ 렌더(Remotion).
- **A1 완료**: 자막이 어절 단발 → 구문 단위. `tts.py`가 `boundaries.json`(문장경계) 생성, `captions.py`가 구문으로 분할. `faster-whisper` 의존성 제거됨.
- **A2 완료**: 템플릿 시스템(`remotion/src/templates/` Documentary·Pop) + 렌더 전 품질 게이트. **사용자 선택: 기본 템플릿 = documentary**(config 기본값도 documentary).
- **운영 메모**: 테스트 렌더 영상은 `test mp4/` 폴더에 둘 것(사용자 확인용). 로컬 실행엔 Docker Desktop 필요, `.env`에 `XAI_API_KEY` 있음(ANTHROPIC 미설정 → 대본 자동생성 쓰려면 키 필요, 아니면 `--job-id <id>` 지정 후 `runs/<date>/<id>/script.json` 더미 시드).
- **A3(이미지) 완료**: Grok `grok-imagine-image`로 비주얼 생성(폴백 Pollinations). TTS는 edge-tts 유지(유료 TTS 미적용).
- **A4 완료**: 대본 기본 모델을 Claude Haiku 4.5(`claude-haiku-4-5-20251001`)로 전환. `script_gen.py`는 정적 시스템 프롬프트에 `cache_control: {"type": "ephemeral"}`을 적용하고, Anthropic usage 기반 토큰/예상 비용을 `runs/<date>/<job_id>/logs/script_usage.json`에 기록. 단, Haiku 4.5는 4096토큰 이상 프롬프트만 실제 캐시되므로 현재 짧은 시스템 프롬프트는 cache write/read가 0일 수 있음.
- **B0 완료**: 산출물 구조를 job 단위로 변경. 기본 실행은 자동 `job_id`를 만들어 `runs/<date>/<job_id>/`에 저장하고, `--job-id`로 재현 가능한 작업 ID를 지정 가능. `job.json`에 topic/tone/template/status/step/artifacts/error를 기록.
- **B1 완료**: FastAPI 파일 기반 job API 스켈레톤 추가. `docker compose up api`로 실행, `POST /jobs`, `GET /jobs/{job_id}`, `GET /jobs/{job_id}/video` 기본 엔드포인트 제공.
- **B2 완료**: API 백그라운드 실행 분리. `POST /jobs`는 기본 `auto_start=true`로 즉시 `queued` job을 반환하고 뒤에서 파이프라인 실행, `auto_start=false`면 manifest만 생성. `POST /jobs/{job_id}/run`으로 기존 job 실행/재실행 가능. 현재는 단일 API 프로세스 안의 background task + lock 기반이라 동시 렌더는 1개씩 처리.
- **B3 완료**: FastAPI 루트(`/`)에 내부용 웹 대시보드 추가. 주제/톤/템플릿 입력, 자동 시작 토글, job 조회/실행, 상태 폴링, 완료 mp4 미리보기를 한 화면에서 처리.
- **B4 완료**: 인증/결제 전 임시 사용자·쿼터 구조 추가. `user_id`/`plan`/`quota`가 `job.json`에 기록되고, `GET /users/{user_id}/quota`로 월간 사용량 조회, `auto_start`/재실행 시 플랜 quota 초과는 402로 차단. 대시보드에서 사용자/플랜 입력과 quota 표시 가능.
- **A5 완료**: 비주얼 품질 전략을 사용자 선택형으로 전환하기 위한 최소 구조 추가. `visual_mode`(`auto`·`motion_image`·`stock_video`·`ai_video`)와 `visual_provider`(`auto`·`xai`·`kie`·`pexels`·`pixabay`·`local`)가 CLI/API/dashboard/job.json에 기록된다. 아직 스톡/AI 영상 provider는 실험 전이라 기존 이미지 모션 파이프라인으로 fallback하고, `visuals.json`에 requested/effective/fallback_reason을 남긴다.

## 3. 다음 작업 (우선순위, PRD §14)
- [x] **A1 — 자막 구문 그룹핑 + faster-whisper 제거** (PRD §7, 완료 2026-05-22). 타이밍을 TTS 경계로 바꾸고 어절을 "한 호흡=한 줄"로 묶음. edge-tts 한국어는 **SentenceBoundary**만 주므로(WordBoundary 아님) 문장을 구문으로 쪼개고 글자수 비례로 시간 분배. 검증: 문장 3개→구문 6개(어절 단발 0건).
- [x] **A3 — 이미지: Grok 연동 검증 완료**(2026-05-22). 모델 `grok-imagine-image`(주의: `grok-2-image`는 폐기됨). `XAI_API_KEY` 없으면 Pollinations 폴백. 3장 ~13초(Pollinations 6분 대비 대폭 개선). **TTS는 edge-tts 무료 유지**(유료 TTS는 나중에). 9:16은 Remotion objectFit:cover로 처리.
- [x] **A2 — 카테고리별 고정 템플릿 완료**(2026-05-22). `remotion/src/templates/`에 `Documentary`(다큐)·`Pop`(잡지식) 2종, `shared.tsx` 공통요소, `Main`이 `template` prop으로 분기. `render.py`에 렌더 전 품질 게이트(이미지·자막·길이·템플릿 검증). 선택: `--template` / `TEMPLATE` env. 두 템플릿 렌더 검증 완료.
- [x] **A4 — 대본 모델 Haiku 4.5 전환 + 프롬프트 캐싱** (PRD §8, 완료 2026-05-22). 기본 모델 `claude-haiku-4-5-20251001`, 캐시 breakpoint 적용, 토큰/예상 비용 로깅. 검증: Docker build, ruff, 더미 script.json 기반 documentary 렌더(1080×1920, 29.06초) 완료.
- [x] **B0 — job_id 기반 실행 디렉토리 + job manifest** (완료 2026-05-22). `runs/<date>/<job_id>/` 구조, `--job-id` 옵션, `job.json` 상태/아티팩트 기록. 검증: Docker build, ruff, 더미 script.json 기반 documentary 렌더(1080×1920, 30.91초) 완료.
- [x] **B1 — 파일 기반 job 조회 API 스켈레톤** (완료 2026-05-22). FastAPI 최소 엔드포인트(`GET /health`, `POST /jobs`, `GET /jobs/{job_id}`, `GET /jobs/{job_id}/video`) 추가, DB/큐 없이 `job.json` 재사용. 검증: Docker build, ruff, TestClient 한글 생성/조회, HTTP health/create/get/video range.
- [x] **B2 — 백그라운드 실행 분리** (완료 2026-05-22). API 요청은 즉시 queued/pending job을 반환하고 실제 렌더는 FastAPI background task에서 실행. 단일 서버용 lock으로 동시 렌더 1개 제한. 검증: Docker build, ruff, TestClient create/run, HTTP create/run.
- [x] **B3 — 최소 웹 대시보드** (완료 2026-05-22). 로그인/결제 없이 주제 입력, 템플릿 선택, 생성 요청, job 상태 폴링, mp4 미리보기까지 가능한 내부용 첫 화면. 검증: Docker build, ruff, TestClient root/API, HTTP root/create.
- [x] **B4 — 사용자/쿼터 최소 구조** (완료 2026-05-22). 인증/결제 전 단계로 `user_id`, plan, monthly quota, usage count를 manifest/API/대시보드에 얇게 추가. `auto_start`/재실행은 quota 초과 시 402로 차단. 검증: Docker build, ruff, TestClient 생성/쿼터/402/root smoke.
- [x] **A5 — 비주얼 모드/provider 선택 구조** (완료 2026-05-22). `motion_image`·`stock_video`·`ai_video` 선택값과 `xai`·`kie`·`pexels`·`pixabay` provider 후보를 job/API/대시보드에 기록. 미구현 provider는 기존 이미지 생성으로 안전 fallback하며 `visuals.json`에 기록. 검증: Docker build, ruff, TestClient 생성/필드/root smoke.
- [ ] **A6 — BGM 믹싱**. 템플릿별 기본 BGM, 음성 우선 볼륨(-20~-26dB), fade in/out, 길이 자동 loop/trim.
- [ ] **A7 — Stock video provider 실험**. Pexels/Pixabay 검색→다운로드→`visuals.json` video item→Remotion `<Video>` 렌더까지 최소 경로 검증.
- [ ] **A8 — AI video provider 실험**. xAI 공식 Grok video와 Kie.ai 경유 Grok/Kling/Seedance 샘플을 5~6초 단위로 비교하고 원가/속도/품질 기록.
- [ ] **B5 — job/user 저장소 경계 만들기**. 지금의 `job.json` 직접 접근을 얇은 storage/repository 계층으로 감싸고, 다음 단계의 SQLite/Postgres 전환과 사용자별 job 목록 API를 준비.
- 이후 **B**(멀티테넌트 백엔드) · **C**(웹 프론트/온보딩) · **D**(YouTube 업로드/쿼터/과금) · **E**(운영/스케일). PRD §14.

## 4. 코딩 규칙
- Python: type hint 사용, `ruff` 통과. 비동기 다운로드는 `asyncio`.
- **모든 단계 멱등**: 중간 산출물 있으면 스킵(재시작 가능). 같은 `runs/<date>/<job_id>/`에 이전 결과 있으면 재사용되니, 재실행하려면 같은 `--job-id`를 쓰고 새 실행은 자동 job_id에 맡길 것.
- 에러는 던지지 말고 **단계별로 잡아 로그·기록**(파이프라인 중단 방지).
- **키 하드코딩 금지** (`.env` + `python-dotenv`). 로그는 `runs/<date>/<job_id>/logs/`.
- 영상 규격: 9:16 **1080×1920**, **30~60초**.
- 변경은 최소·외과적으로. 무관한 리팩터 금지.

## 5. 함정 / 실무 메모 (꼭 읽을 것)
- **이미지(A3)**: 기본 **Grok `grok-imagine-image`**(xAI, `POST https://api.x.ai/v1/images/generations`, b64_json). ⚠️ `grok-2-image`는 폐기됨(404). 다른 모델은 `GET /v1/models`로 확인. `XAI_API_KEY` 없으면 **Pollinations 폴백**(익명 티어 402 → 순차+1초, 느림). Grok은 종횡비 고정이라 9:16은 렌더 objectFit:cover로 크롭.
- **비주얼 전략(A5~A8)**: 기본은 `DEFAULT_VISUAL_MODE=motion_image`, `DEFAULT_VISUAL_PROVIDER=auto`. `stock_video`/`ai_video`는 현재 선택값만 저장하고 이미지 모션으로 fallback. Kie.ai는 저가 후보지만 중간 플랫폼이므로 가격·속도·실패율을 샘플로 검증하기 전 기본값으로 박지 말 것. Free/Basic은 `stock_video + motion_image`, Pro/크레딧은 일부 장면만 `ai_video`로 섞는 방향.
- **템플릿(A2)**: `remotion/src/templates/`(Documentary·Pop) + `shared.tsx`. 새 템플릿 추가 시: 컴포넌트 작성 → `Composition.tsx`의 `TEMPLATES` 레지스트리 + `render.py`의 `KNOWN_TEMPLATES`에 등록. 자막 한글 폰트는 NanumGothic.
- **ffmpeg 4.4.2**: Ubuntu 22.04 기본. PRD 표의 6.0+ 아님. `libx264 -crf 23` 인코딩엔 충분.
- **대본 모델(A4)**: 기본 `claude-haiku-4-5-20251001` (`.env` `CLAUDE_MODEL`로 변경). `CLAUDE_PROMPT_CACHE=1`이면 시스템 프롬프트에 ephemeral cache breakpoint 적용. Haiku 4.5 캐시 최소 길이는 4096토큰이라 현재 짧은 프롬프트는 실제 캐시 write/read가 0일 수 있음. 대본이 길어지면 60초 초과 가능 → `script_gen.py` 프롬프트에 길이 하드캡(현재 380자). ANTHROPIC 없이 더미 대본으로 테스트하려면 `--job-id <id>`를 정하고 `runs/<date>/<id>/script.json`을 시드.
- **API/대시보드(B1~B4)**: `docker compose up api` 후 `http://localhost:8000/`에서 대시보드, `/docs`에서 API 확인. `POST /jobs`는 기본적으로 background 실행을 예약하고, `auto_start=false`로 manifest만 생성 가능. `user_id`/`plan`을 받아 `job.json`에 기록하고, `GET /users/{user_id}/quota?plan=free`로 월간 사용량 확인. `auto_start`/`POST /jobs/{job_id}/run`은 quota 초과 시 402. 아직 Redis/Celery/DB 없음, API 프로세스가 내려가면 실행 중 작업도 중단될 수 있음.
- **자막(A1 해결됨)**: edge-tts 한국어 보이스는 **SentenceBoundary**만 줌(WordBoundary 미제공). `captions.py`가 문장→구문 분할 + 글자수 비례 시간 분배. 문장 내 타이밍은 근사(문장 경계는 정확). 그룹핑 기준은 `config.py` `CAPTION_MAX_CHARS/WORDS/MS/PAUSE_MS`.
- **한글 폰트**: Docker에 `fonts-nanum` 설치, Remotion 자막은 `NanumGothic` 사용(미설치 시 □□□ 깨짐).
- **⚠️ 보안**: 초기 `ANTHROPIC_API_KEY`가 채팅에 평문 노출된 적 있음 → **반드시 폐기·재발급** 후 `.env`에 새 키 입력.

## 6. 위치 / 환경
- **정규 위치**: 이 레포(`github.com/gyeongwonKR/dullizze`). 편집·실행 모두 여기서 Docker로.
- 옛 WSL 작업본(`Ubuntu-22.04:/root/shorts-pipeline`)은 삭제됨. Docker용 `docker-desktop` 배포판은 건드리지 말 것.
- `.env`, `runs/`, `node_modules/`, `*.mp4` 등은 `.gitignore`로 커밋 제외.

## 7. 상태 변경 이력 (작업 끝나면 한 줄씩 추가)
- 2026-05-22: Phase 0·1 완료, PRD v2.0(웹 SaaS) 작성, Docker화, GitHub 초기 푸시, AGENTS.md 생성.
- 2026-05-22: **A1 완료** — 자막 구문 그룹핑(`tts.py`+`captions.py`), faster-whisper 제거, Docker 재빌드 검증.
- 2026-05-22: **A3 이미지 — Grok 연동 구현**(`visuals.py`, XAI_API_KEY 없으면 Pollinations 폴백). TTS는 edge-tts 유지.
- 2026-05-22: **A3 검증 + 모델 수정** — `grok-2-image`(폐기) → `grok-imagine-image`. 3장 13초 확인.
- 2026-05-22: **A2 완료** — 템플릿 시스템(Documentary/Pop) + 품질 게이트. 두 템플릿 렌더 검증.
- 2026-05-22: **A4 완료** — 기본 대본 모델을 Claude Haiku 4.5로 전환, 시스템 프롬프트 `cache_control` 적용, 토큰/예상 비용 로그(`logs/script_usage.json`) 추가. Docker build/ruff/더미 대본 렌더 검증, 결과를 `test mp4/a4-haiku-cache-documentary-2026-05-22.mp4`에 복사.
- 2026-05-22: **B0 완료** — `runs/<date>/<job_id>/` 구조와 `--job-id` 옵션 도입, `job.json` 상태/아티팩트 manifest 기록 추가. Docker build/ruff/더미 대본 렌더 검증, 결과를 `test mp4/b0-job-smoke-documentary-2026-05-22.mp4`에 복사.
- 2026-05-22: **B1 완료** — FastAPI 파일 기반 job API 추가(`pipeline/api.py`, `pipeline/jobs.py`), compose `api` 서비스와 `/health`·`/jobs`·`/jobs/{job_id}`·`/jobs/{job_id}/video` 엔드포인트 구현. Docker build/ruff/TestClient/HTTP smoke 검증.
- 2026-05-22: **B2 완료** — API background task 실행 추가(`auto_start`, `/jobs/{job_id}/run`), 기존 manifest를 보존하며 파이프라인 재실행 가능하도록 `main.run(out_dir=...)` 지원. Docker build/ruff/TestClient/HTTP smoke 검증.
- 2026-05-22: **B3 완료** — `web/dashboard.html` 내부용 대시보드 추가, FastAPI `/`에서 서빙. 생성/조회/실행/상태 폴링/mp4 미리보기 UI 구현. Docker build/ruff/TestClient/HTTP smoke 검증.
- 2026-05-22: **B4 완료** — 임시 사용자/플랜/quota 구조 추가(`accounts.py`, `job.json` quota snapshot, `/users/{user_id}/quota`, 대시보드 표시). `auto_start`/재실행 quota 초과는 402로 차단. Docker build/ruff/TestClient smoke 검증.
- 2026-05-22: **A5 완료** — 비주얼 품질 전략 기록 및 `visual_mode`/`visual_provider` 선택 구조 추가(API/CLI/dashboard/job.json/`visuals.json`). 스톡/AI 영상 provider는 기존 이미지 생성으로 fallback. Docker build/ruff/TestClient smoke 검증.
