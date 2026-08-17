# JobMap

캐나다 구인정보 게시판(JPCanada 등)의 일자리 정보를 크롤링·정제하여 지도 기반으로 시각화하는 웹 서비스입니다.

## 프로젝트 구조

```
JobSearch/
├── backend/          # FastAPI 백엔드
├── frontend/         # Next.js 프론트엔드
├── crawler/          # Python 크롤러
├── database/         # 데이터베이스 마이그레이션 파일
└── docs/             # 문서 (PRD, TRD)
```

## 기술 스택

- **프론트엔드**: Next.js 15, TypeScript, TailwindCSS, MapLibre GL JS
- **백엔드**: FastAPI, SQLAlchemy, PostgreSQL + PostGIS
- **크롤러**: Python 3.9+ (3.11 권장), Requests, BeautifulSoup
- **데이터베이스**: Supabase (PostgreSQL + PostGIS)

## 시작하기

### 사전 요구사항

- Python 3.9+ (3.11 권장)
- Node.js 18+
- Docker Desktop (로컬 PostgreSQL + PostGIS 실행 시)
- PostgreSQL (Supabase 사용 시 자동 제공)

### 환경 변수 설정

초기 로컬 개발용 환경 변수는 이미 생성되어 있습니다.

- 백엔드: `backend/.env`
- 프론트엔드: `frontend/.env.local`
- 크롤러: `crawler/.env`
- 선택 AI 품질 판정 및 구인 제목 번역: 프로젝트 루트 `.env.local`의 `CODEX_BRIDGE_*`

값을 다시 만들 때는 각 서비스의 `.env.example` 파일을 복사하세요.

### 데이터베이스 실행

```bash
docker compose up -d db
```

처음 실행할 때 `database/migrations/001_initial_schema.sql`이 자동으로 적용됩니다.

### 백엔드 실행

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 프론트엔드 실행

```bash
cd frontend
npm install
npm run dev
```

### 크롤러 실행

```bash
cd crawler
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

### Vercel 배포 구조

Vercel 배포는 루트 `vercel.json`의 Services 구성을 기준으로 합니다.

- `web`: `frontend/` Next.js 앱. 공개 지도 화면과 `/api/jobs/*`를 담당합니다.
- `crawler`: `crawler/api.py` FastAPI 서비스. 운영 정기 크롤링은 이 Mac의 LaunchAgent가 6시간마다 직접 실행하며, HTTP 경로는 인증된 수동 실행용으로 유지합니다.
- 데이터베이스: 프로덕션은 Supabase PostgreSQL + PostGIS, 로컬은 Docker PostGIS를 사용합니다.

Vercel Project Settings의 Framework Preset은 `Services`로 설정하세요. 필요한 환경 변수는 `DATABASE_URL`, `CRON_SECRET`, `CRAWLER_MAX_POSTS_PER_REGION`, `OURVANCOUVER_MAX_POSTS_PER_REGION`, `CASMO_MAX_POSTS_PER_REGION`, `ADMIN_PASSWORD`, `SESSION_SECRET`, `CRAWLER_SERVICE_URL`입니다. `OURVANCOUVER_MAX_POSTS_PER_REGION`은 14일 분량의 우벤유 누락 공고를 새 글 우선의 제한된 배치로 보충할 때 사용하며 기본값은 100입니다. `CASMO_MAX_POSTS_PER_REGION`은 캐스모 공개 목록의 매우 높은 게시량을 제한하는 배치 크기로, 기본값은 25입니다. 우벤유와 캐스모의 애매한 게시글 판정과 한국어·영어·일본어·중국어 구인 제목 번역에는 서버 전용 `CODEX_BRIDGE_BASE_URL`, `CODEX_BRIDGE_API_KEY`, `CODEX_BRIDGE_MODEL`을 사용합니다. 캐스모는 회원 전용 본문을 요청하지 않고 공개 목록 제목만 분석하며, Bridge 실패 항목은 다음 실행에서 재시도합니다.

이 Mac에서 운영 크롤러를 6시간마다 실행하려면 다음 설치기를 실행합니다. 설치기는 운영 `DATABASE_URL`과 로컬 Codex Bridge 연결 정보를 macOS 로그인 키체인에서 읽으므로 비밀값을 저장소나 평문 설정 파일에 복사하지 않습니다. 또한 macOS가 백그라운드 프로세스의 `Documents` 접근을 막아도 실행되도록 필요한 런타임만 `~/Library/Application Support/JobMap/runtime`에 설치합니다. 소스나 의존성을 변경한 뒤에는 설치기를 다시 실행해 런타임을 갱신해야 합니다. Mac이 켜져 있고 네트워크와 로컬 Codex Bridge를 사용할 수 있어야 합니다.

```bash
./crawler/install_macos_schedule.command
```

로그는 `~/Library/Logs/JobMap/crawler.log`과 `crawler-error.log`에 기록됩니다.

로컬에서 Vercel용 크롤러 서비스를 확인하려면 다음을 실행합니다.

```bash
cd crawler
source .venv/bin/activate
uvicorn api:app --reload --port 8001
```

자세한 전환 계획과 진행 상태는 [Vercel Deployment Plan](docs/vercel-deployment-plan.md)과 [Vercel Implementation Todo List](docs/vercel-implementation-todolist.md)를 기준으로 관리합니다.

관리자 페이지는 `http://localhost:3000/admin`에서 확인합니다. 로컬 기본 비밀번호는 `frontend/.env.local`의 `ADMIN_PASSWORD` 값입니다.

## 문서

- [PRD (Product Requirements Document)](docs/prd.md)
- [TRD (Technical Requirements Document)](docs/trd.md)

## 라이선스

MIT
