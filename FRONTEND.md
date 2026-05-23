# FRONTEND.md — 프론트엔드 구현 명세

> 목적: **Claude(또는 v0/Cursor 류)가 이 문서만 보고 프론트엔드를 바로 구현**할 수 있도록 하는 단일 명세.
> 상위 기획은 [PRD.md](PRD.md), 백엔드/파이프라인은 [AGENTS.md](AGENTS.md).
> 대상 사용자: 비개발자(브라우저만 사용). 언어: 한국어.

---

## 0. 한 줄 요약

주제 한 줄 입력 → 9:16 정보형 YouTube 쇼츠를 **고정 템플릿("형") 기반**으로 자동 생성·검수·공개하는 구독형 웹앱. 프론트는 **Wanted Design System(비주얼) + shadcn/ui(코드) + Next.js**로 구현한다.

---

## 1. 디자인 시스템 전략 (가장 중요)

**두 레이어를 분리한다.**

| 레이어 | 선택 | 역할 |
|---|---|---|
| 디자인 소스 | **Wanted Design System** (Figma 오픈소스) | 색·타이포·그리드·아이콘·**Design Token**·폰트의 단일 진실원천 |
| 폰트 | **Pretendard / Wanted Sans** (오픈소스) | 한국어 본문/제목 |
| 구현(코드) | **shadcn/ui + Tailwind CSS** | Wanted 토큰을 Tailwind 테마로 매핑해 컴포넌트 구현. Claude가 바로 생성 가능한 표준 |
| 프레임워크 | **Next.js (App Router) + React + TypeScript** | PRD §12 |

- **원칙**: Wanted DS = "어떻게 보일지"(토큰), shadcn/ui = "코드로 어떻게 만들지". 디자이너는 Figma에서 토큰을 정하고, 그 값이 `tailwind.config`의 테마로 들어간다. 컴포넌트 자체는 shadcn/ui로.
- Figma: Wanted Design System (Community). Foundation(color/typography/grid/icons) + Element + Variants + Design Tokens 제공.
- ⚠️ Wanted DS는 **디자인 자산**이지 코드 라이브러리가 아니다. 코드 컴포넌트는 shadcn/ui로 만들고, Wanted의 토큰/폰트로 "입힌다".

### 1.1 디자인 토큰 (Figma에서 채워 넣을 자리)

> 아래는 구조 placeholder. 실제 값은 Wanted DS Figma의 Design Token에서 추출해 채운다.

- **Color**: `primary`, `secondary`, `bg`, `surface`, `text`, `muted`, `line`, `success`, `warning`, `danger` (light/dark)
- **Typography**: 폰트 = Pretendard(본문)/Wanted Sans(헤드). 스케일 = display / h1~h4 / body / caption
- **Spacing**: 4px 베이스 스케일
- **Radius**: sm/md/lg/full
- **Elevation**: shadow 토큰

---

## 1.5 UX 원칙 — 편안한 사용 (최우선, 화면설계보다 앞선다)

> 페르소나: 비개발자, 브라우저만 사용(PRD §3). 이탈 요인 = 복잡한 온보딩·깨진 영상·느린 생성·YouTube 연동 실패. 아래 원칙을 모든 화면에 우선 적용한다.

1. **최소 입력으로 첫 성공(TTFV 최소화)**: 주제 한 줄 + "생성"만으로 영상이 나와야 한다. 형·보이스·브랜딩·provider 등은 스마트 기본값 + "고급 설정" 토글 뒤로 숨김(progressive disclosure). 헤드라인은 비우면 AI가 채움.
2. **대기 경험 설계**: 생성 1~2분 → spinner만 두지 말고 **단계별 진행 + 친근한 한국어 카피**("대본 쓰는 중… → 목소리 입히는 중… → 영상 만드는 중…") + 예상 시간 + 자리 비워도 됨(완료 시 알림).
3. **검수 = 안심**: "비공개로 올라갔어요, 확인 후 공개하세요" 프레이밍. 미리보기·재생성·간단 편집을 한 화면에서. 팩트 확인 리마인더(PRD §10).
4. **에러는 평이한 한국어 + 원클릭 복구**: 스택트레이스 금지. "이미지 생성이 잠시 실패했어요 → [다시 시도]" 식. 기술 디테일은 접기.
5. **온보딩 이탈 방지(특히 YouTube OAuth)**: 연결을 **뒤로 미룰 수 있게**(영상 먼저 만들고 mp4 다운로드 가능), 권한 이유 설명, 실패 시 재시도 + FAQ.
6. **빈 화면 해소**: 첫 진입·주제 막힘 시 샘플 주제·추천("이런 주제 어때요?") 제공.
7. **반응형/모바일**: 비개발자는 폰 사용이 많다 → 모바일에서도 생성·검수 가능해야 한다.
8. **즉각 피드백**: 모든 버튼에 로딩/비활성 상태, 액션마다 토스트(Sonner), 폼/프리셋 자동저장.
9. **놀라지 않게**: 쿼터 잔여 항상 노출("이번 달 N편 남음"), 크레딧 차감 행동(이미지 재생성·최종 렌더) 전 명확히 고지.
10. **접근성·한글 가독성**: shadcn/Radix 기본 a11y 유지, 충분한 대비·폰트 크기, 키보드 내비게이션.

---

## 2. 정보구조(IA) / 라우트 맵

```
/                      랜딩(제품 소개·가격·CTA)
/login                 로그인/가입 (이메일 + OAuth)
/onboarding            온보딩 위저드
  ├ plan               플랜 선택/결제
  ├ youtube            YouTube 채널 연결 (Google OAuth) — 이탈 1순위, 가장 친절하게
  └ channel            채널 기본설정(카테고리·톤·기본 형·보이스)
/app                   (인증 영역)
  ├ /app/dashboard     생성 이력·쿼터·실패/재시도
  ├ /app/create        생성 플로우(주제 → 형 선택 → 브랜딩/헤드라인 → 생성)
  ├ /app/jobs/[id]     job 상세: 진행상태 폴링 + 미리보기 + 메타데이터
  ├ /app/jobs/[id]/edit  ★영상 에디터(컷/자막/TTS/브금) — §6, Phase 2
  ├ /app/presets       프리셋 관리(스타일 레시피 저장/적용)
  └ /app/settings      계정·결제·채널·쿼터
```

- 현재 내부용 단일 페이지 대시보드(`web/dashboard.html`)가 `/app/create`+`/app/jobs/[id]`의 프로토타입. 이걸 위 구조로 분해·재구현한다.

---

## 3. 핵심 화면 명세

### 3.1 생성 플로우 (`/app/create`)
> 원칙(§1.5-1): **주제 입력 + 생성**만으로 완성되게. 2·3번은 스마트 기본값이 채워져 있고, 상세 입력은 "고급 설정" 토글 뒤로.
1. **주제 입력** (textarea, ≤200자)
2. **"형" 선택** — `GET /templates`로 받은 목록(기본형/팝형/배너형)을 카드/세그먼트로. 각 형은 미리보기 썸네일 + 한 줄 설명.
3. **콘텐츠 입력**(선택한 형에 따라 노출):
   - 배너형: 상단 헤드라인 1·2줄(`headline_main`/`headline_accent`, 비우면 AI 생성), 채널명, 하단 footer 1·2줄, 강조색
   - 공통: 톤, 보이스, 비주얼 방식/Provider, (선택) 프리셋 적용
4. **생성** → `POST /jobs` (`auto_start: true`) → 즉시 `queued` job 반환 → `/app/jobs/[id]`로 이동
5. 쿼터 초과 시 402 → 업그레이드 안내 모달

### 3.2 Job 상세/검수 (`/app/jobs/[id]`)
- 상태 배지: `pending|queued|running|done|failed`
- **진행 폴링**: `running|queued`이면 2.5초 간격 `GET /jobs/{id}` 폴링, step 표시(스크립트 생성→TTS→비주얼 수집→자막 그룹핑→영상 합성)
- `done`이면 `GET /jobs/{id}/video`로 9:16 플레이어 미리보기 + 메타데이터(제목/태그/설명)
- `failed`이면 error.step/message + 재시도 버튼(`POST /jobs/{id}/run`)
- **공개는 항상 비공개 업로드 후 사용자 확인**(PRD §10)

### 3.3 대시보드 (`/app/dashboard`)
- 쿼터 카드(`GET /users/{id}/quota`: used/limit/remaining)
- job 리스트(상태·썸네일·생성일), 실패 필터, 재시도

### 3.4 프리셋 (`/app/presets`)
- 프리셋 = 주제 제외 스타일 레시피. CRUD API(§5) 사용. 적용 시 생성 폼 프리필.

---

## 4. 상태/엣지케이스 (반드시 처리)

- **로딩**: skeleton(목록/플레이어)
- **빈 상태**: job 없음 → "첫 쇼츠 만들기" CTA
- **에러**: API detail 메시지 노출. 402(쿼터)=업그레이드 유도, 409(이미 실행 중), 404(job 없음)
- **장시간 작업**: 생성은 1~2분. 폴링 + 진행 step 표시로 체감 대기 완화
- **YouTube 연결 실패**: 온보딩에서 재시도 흐름 + FAQ 링크

---

## 5. API 계약 (백엔드 — 현재 구현됨)

> Base: 현재 FastAPI(`pipeline/api.py`). 인증/멀티테넌시는 PRD Phase B에서 추가 예정 — 지금은 `user_id` 쿼리/바디로 식별.

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | `{status:"ok"}` |
| GET | `/templates` | `[{value, label}]` — 형 목록(기본형/팝형/배너형) |
| POST | `/jobs` | job 생성+백그라운드 실행. 201. 400/402(쿼터)/409 |
| GET | `/jobs/{id}?date=YYYY-MM-DD` | job manifest 조회 |
| POST | `/jobs/{id}/run?date=` | 기존 job 실행/재실행(quota 체크) |
| GET | `/jobs/{id}/video?date=` | 완료된 mp4(Range 지원) |
| GET | `/users/{id}/quota?plan=` | `{used, limit, remaining, plan, month}` |
| GET | `/users/{id}/presets` | 프리셋 목록 |
| POST | `/users/{id}/presets` | 프리셋 생성 |
| GET/PUT/DELETE | `/users/{id}/presets/{pid}` | 프리셋 조회/수정/삭제(204) |

### 5.1 `POST /jobs` body (JobCreate)
```jsonc
{
  "topic": "string(1~200)",        // 필수
  "template": "documentary|pop|banner",
  "tone": "string?",
  "voice": "string?",              // 예: ko-KR-SunHiNeural
  "model": "string?",              // 예: claude-haiku-4-5-20251001
  "user_id": "string?", "plan": "free|basic|pro",
  "visual_mode": "auto|motion_image|stock_video|ai_video",
  "visual_provider": "auto|xai|kie|pexels|pixabay|local",
  "preset_id": "string?",
  "channel_name": "string?", "footer_main": "string?",
  "footer_accent": "string?", "accent_color": "#hex?",
  "headline_main": "string?",      // 배너 상단 1줄(비우면 AI)
  "headline_accent": "string?",    // 배너 상단 2줄(비우면 AI)
  "auto_start": true
}
```

### 5.2 job manifest (응답) 주요 필드
`job_id, topic, tone, template, user_id, plan, preset_id, voice, model, channel_name, footer_main, footer_accent, accent_color, headline_main, headline_accent, visual_mode, visual_provider, quota{used,limit,remaining}, status, step, created_at, updated_at, run_dir, artifacts{script,audio,assets[],captions,props,video}, error{step,message}`

- status: `pending|queued|running|done|failed`
- 해석 규칙: 명시값 > 프리셋 > 시스템 기본. 헤드라인은 프리셋 상속 없음(주제별 콘텐츠).

---

## 6. ★영상 에디터 — 컷/자막/TTS/브금 사용자 제어 (Phase 2, 예정)

> 사용자가 자동 생성 결과를 받아 **컷 단위로 직접 편집**한 뒤 "병합"으로 최종 렌더하는 기능. MVP 이후 추가. 프론트 IA는 지금부터 이 화면(`/app/jobs/[id]/edit`)을 위해 자리를 비워둔다.

**편집 대상(사용자가 정함):**
- **컷(scene)**: 장면별 이미지/영상 교체·순서·길이
- **자막**: 컷별 자막 텍스트 수정(스타일은 형 고정 — 변형 선택 방식)
- **TTS**: 보이스 교체·구간 재생성
- **브금(BGM)**: 트랙 선택·볼륨

**비용/시간 설계(확정된 합의):**
- 텍스트·순서·길이 편집 = props만 변경 → **크레딧 0**
- **스틸 프레임 미리보기**(단일 프레임 렌더)로 편집 즉시 확인 → 거의 무료·1~2초
- 이미지 재생성·대본 수정 = 크레딧 차감
- **병합(최종 렌더)** = 최대 원가($0.1~0.3) → 신중한 1회 행동(횟수 제한/크레딧 게이트)

**백엔드 의존성(선행 필요):** 현재 파이프라인엔 "컷(scene)" 데이터 모델이 없다(이미지는 시간상 균등 분배, 자막은 독립 타이밍). 에디터를 위해 `scenes.json`(컷=이미지 시간창+해당 자막+나레이션 구간) 모델과 스틸 프레임 렌더 엔드포인트를 백엔드에 먼저 추가해야 한다. 자세한 배경은 대화/AGENTS 참조.

**프론트 형태:** 타임라인/컷 리스트 + 컷별 인스펙터 + 스틸 프레임 프리뷰 패널 + "병합" 버튼.

---

## 7. Claude 구현 가이드

1. **스캐폴드**: `create-next-app`(TS, App Router) → Tailwind → shadcn/ui init.
2. **테마**: Wanted DS Design Token → `tailwind.config` theme + CSS 변수. Pretendard/Wanted Sans 웹폰트 로드.
3. **데이터 레이어**: TanStack Query(또는 SWR)로 §5 API 래핑. job 폴링은 `running|queued`일 때만.
4. **컴포넌트**: shadcn/ui 기반(Button/Card/Input/Select/Badge/Dialog/Tabs/Skeleton/Sonner 등).
5. **화면 순서**: 생성 플로우(§3.1) → job 상세/검수(§3.2) → 대시보드(§3.3) → 프리셋(§3.4) → 온보딩 → 랜딩. 에디터(§6)는 마지막.
6. **목 데이터**: 백엔드 미연동 구간은 §5 스키마로 목킹.

---

## 8. 미정 / 결정 필요

- [ ] 인증 방식(NextAuth? 자체?) — Phase B
- [ ] 결제 UI(Stripe/토스/페이플) — PRD §17
- [ ] 다국어 여부(현재 한국어)
- [ ] Wanted DS 토큰 실제 값 추출 → tailwind 테마 확정
- [ ] 에디터(§6) 백엔드 scene 모델 설계 착수 시점
- [ ] 다크모드 지원 여부

---

## 9. 변경 이력
- 2026-05-23: 초안. 디자인 전략(Wanted DS + shadcn/ui + Next.js), IA/라우트, 화면 명세, API 계약, 영상 에디터(Phase 2) 명세 작성.
