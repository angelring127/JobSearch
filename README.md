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
- **크롤러**: Python 3.11, Requests, BeautifulSoup
- **데이터베이스**: Supabase (PostgreSQL + PostGIS)

## 시작하기

### 사전 요구사항

- Python 3.11+
- Node.js 18+
- PostgreSQL (Supabase 사용 시 자동 제공)

### 환경 변수 설정

각 서비스의 `.env.example` 파일을 참고하여 `.env` 파일을 생성하세요.

### 백엔드 실행

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
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
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

## 문서

- [PRD (Product Requirements Document)](docs/prd.md)
- [TRD (Technical Requirements Document)](docs/trd.md)

## 라이선스

MIT


