# YouTube 쇼츠 자동 생성 파이프라인

주제 한 줄 → 정보/지식형 9:16 YouTube 쇼츠 자동 생성. 자세한 기획은 [PRD.md](PRD.md) 참고.

실행 환경(ffmpeg·Python·Node·Remotion·한글폰트)은 **Docker로 박제**되어 있어, 어느 PC에서든 동일하게 돌아갑니다.

## 다른 PC에서 시작하기

전제: 그 PC에 **Docker Desktop**(또는 Docker Engine)만 설치돼 있으면 됩니다.

```bash
# 1) 코드 받기
git clone <레포 주소>
cd dullizze

# 2) 키 설정 (레포에 .env는 없음)
cp .env.example .env
#   .env 를 열어 ANTHROPIC_API_KEY 등 값을 채운다

# 3) 이미지 빌드 (최초 1회, 몇 분 소요)
docker compose build

# 4) 영상 1편 생성
docker compose run --rm shorts "클레오파트라는 이집트인이 아니었다" --no-upload
```

생성물은 호스트의 `runs/<날짜>/<job_id>/final.mp4` 에 나옵니다 (compose 볼륨으로 연결됨).
`job_id`는 자동 생성되며, 재현 가능한 실행이 필요하면 `--job-id my-job`처럼 지정할 수 있습니다.

## API 스켈레톤

초기 웹 연동용 파일 기반 API를 로컬에서 띄울 수 있습니다.

```bash
docker compose up api
```

- `GET /` — 내부용 대시보드
- `GET /health`
- `POST /jobs` — `job.json` 생성 후 기본값으로 백그라운드 실행 예약 (`auto_start=false`면 생성만)
- `GET /jobs/{job_id}?date=YYYY-MM-DD` — job 상태 조회
- `POST /jobs/{job_id}/run?date=YYYY-MM-DD` — 기존 job 실행/재실행 예약
- `GET /jobs/{job_id}/video?date=YYYY-MM-DD` — 렌더 완료된 mp4 반환

## 구조

```
pipeline/        # 파이썬 파이프라인 (config + steps + main)
remotion/        # Remotion 영상 합성 (src/ 컴포넌트, tsconfig)
data/            # 주제 큐(topics.json) 등
Dockerfile       # 실행 환경 정의
docker-compose.yml
.env.example     # 키 템플릿 (실제 .env 는 커밋 금지)
runs/            # job 단위 산출물: runs/<날짜>/<job_id>/job.json + final.mp4
```

## 참고
- `.env`, `runs/`, `node_modules/`, `*.mp4` 등은 `.gitignore`로 커밋에서 제외됩니다.
- 자세한 단계·로드맵은 [PRD.md](PRD.md).
