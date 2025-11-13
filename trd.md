# JobMap – Technical Requirements Document (TRD)

## 1. 시스템 개요

**JobMap**은 캐나다 구인정보 포럼(JPCanada 등)에서 게시된 데이터를 수집, 정제, 시각화하여 지도 기반으로 탐색할 수 있는 플랫폼입니다. 본 문서는 기술 스택, 아키텍처, API 명세, 데이터 모델, 크롤러 로직, 배포 구조를 정의합니다.

---

## 2. 기술 스택

| 계층      | 기술                                                | 설명                                 |
| --------- | --------------------------------------------------- | ------------------------------------ |
| Frontend  | Next.js 15, TypeScript, TailwindCSS, MapLibre GL JS | 지도 렌더링 및 반응형 UI             |
| Backend   | FastAPI (Python 3.11)                               | REST API 서버, 데이터 검색 및 필터링 |
| Database  | PostgreSQL + PostGIS (Supabase)                     | 공간 데이터 인덱싱, 위치 기반 쿼리   |
| Crawler   | Python + Requests + BeautifulSoup                   | msgid 커서 기반 크롤링               |
| Hosting   | Supabase (DB), EC2 (API), Vercel (프론트)           | 분리형 클라우드 구성                 |
| Scheduler | cron + systemd                                      | 도시별 주기적 크롤링 실행            |

---

## 3. 시스템 아키텍처

```
┌───────────────────────────────────────────┐
│                 User Client (Web)         │
│  Next.js + MapLibre + Tailwind            │
└────────────────────┬──────────────────────┘
                     │ REST API (HTTPS)
┌────────────────────┴──────────────────────┐
│              FastAPI Backend              │
│  - /api/jobs/viewport                     │
│  - /api/jobs/nearby                       │
│  - /api/jobs/clusters                     │
│  - /internal/ingest                       │
└────────────────────┬──────────────────────┘
                     │ SQLAlchemy + PostGIS
┌────────────────────┴──────────────────────┐
│           PostgreSQL (Supabase)           │
│  job_sources, regions, crawl_log          │
└────────────────────┬──────────────────────┘
                     │ Batch ingest (cron)
┌────────────────────┴──────────────────────┐
│         Python Crawler (EC2/Local)        │
│  - JPCanada BBS별 msgid 기반 수집         │
│  - 데이터 정제 후 /internal/ingest 호출  │
└───────────────────────────────────────────┘
```

---

## 4. 데이터 모델

### 4.1 `regions`

```sql
CREATE TABLE regions (
  id SERIAL PRIMARY KEY,
  city TEXT NOT NULL,
  bbs INTEGER NOT NULL,
  listing_url TEXT NOT NULL,
  center GEOGRAPHY(Point, 4326) NOT NULL
);
```

### 4.2 `job_sources`

```sql
CREATE TABLE job_sources (
  id BIGSERIAL PRIMARY KEY,
  msgid BIGINT NOT NULL,
  source_url TEXT UNIQUE NOT NULL,
  region_hint TEXT,
  title TEXT,
  wage_min INTEGER,
  wage_max INTEGER,
  lat DOUBLE PRECISION,
  lng DOUBLE PRECISION,
  geom GEOGRAPHY(Point,4326),
  category TEXT,
  confidence FLOAT DEFAULT 0.8,
  posted_at TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX job_sources_geom_idx ON job_sources USING GIST(geom);
```

### 4.3 `crawl_log`

```sql
CREATE TABLE crawl_log (
  id SERIAL PRIMARY KEY,
  bbs INTEGER NOT NULL,
  last_seen_msgid BIGINT,
  updated_at TIMESTAMP DEFAULT NOW()
);
```

---

## 5. API 명세

### 5.1 `GET /api/jobs/viewport`

- **설명:** 현재 지도 경계(Bounding Box) 내의 구인정보를 조회
- **파라미터:**

  - `minLng` (float, required): 경계 박스 최소 경도
  - `minLat` (float, required): 경계 박스 최소 위도
  - `maxLng` (float, required): 경계 박스 최대 경도
  - `maxLat` (float, required): 경계 박스 최대 위도
  - `zoom` (int, optional): 현재 줌 레벨
  - `wageMin` (int, optional): 최소 시급 필터
  - `wageMax` (int, optional): 최대 시급 필터
  - `category` (string, optional): 직종 카테고리 필터
  - `limit` (int, optional): 반환 개수 제한 (기본값: 100, 최대: 500)

- **쿼리 예시:**

```sql
SELECT id, title, wage_min, wage_max, confidence, source_url,
       ST_X(geom) AS lng, ST_Y(geom) AS lat
FROM job_sources
WHERE geom && ST_MakeEnvelope(:minLng, :minLat, :maxLng, :maxLat, 4326)
ORDER BY posted_at DESC
LIMIT 100;
```

- **응답 스키마:**

```json
{
  "success": true,
  "data": [
    {
      "id": 12345,
      "msgid": 67890,
      "title": "Cafe Staff Needed",
      "wage_min": 17,
      "wage_max": 20,
      "lat": 49.2827,
      "lng": -123.1207,
      "source_url": "https://jpcanada.com/topics.php?...",
      "confidence": 0.85,
      "category": "cafe",
      "region_hint": "Vancouver",
      "posted_at": "2024-01-15T10:30:00Z"
    }
  ],
  "meta": {
    "count": 42,
    "total": 42
  }
}
```

### 5.2 `GET /api/jobs/nearby`

- **설명:** 특정 좌표 중심 반경 N km 내 구인정보 조회
- **파라미터:**

  - `lat` (float, required): 중심 위도
  - `lng` (float, required): 중심 경도
  - `radius` (float, required): 반경 (km 단위, 최대 50km)
  - `wageMin` (int, optional): 최소 시급 필터
  - `wageMax` (int, optional): 최대 시급 필터
  - `category` (string, optional): 직종 카테고리 필터
  - `limit` (int, optional): 반환 개수 제한 (기본값: 100)

- **쿼리 예시:**

```sql
SELECT *, ST_DistanceSphere(geom, ST_MakePoint(:lng, :lat)) AS dist
FROM job_sources
WHERE ST_DWithin(geom::geography, ST_MakePoint(:lng,:lat)::geography, :radius_m)
ORDER BY dist ASC
LIMIT 100;
```

- **응답 스키마:**

```json
{
  "success": true,
  "data": [
    {
      "id": 12345,
      "title": "Cafe Staff Needed",
      "wage_min": 17,
      "wage_max": 20,
      "lat": 49.2827,
      "lng": -123.1207,
      "source_url": "https://jpcanada.com/topics.php?...",
      "confidence": 0.85,
      "category": "cafe",
      "region_hint": "Vancouver",
      "posted_at": "2024-01-15T10:30:00Z",
      "distance_km": 1.2
    }
  ],
  "meta": {
    "count": 15,
    "total": 15,
    "center": {
      "lat": 49.2827,
      "lng": -123.1207
    },
    "radius_km": 5.0
  }
}
```

### 5.3 `POST /internal/ingest`

- **설명:** 크롤러가 신규 데이터 삽입 요청
- **인증:** API Key 헤더 필요 (`X-API-Key: <API_KEY>`)
- **Request Body:**

```json
{
  "source_url": "https://jpcanada.com/topics.php?msgid=12345",
  "msgid": 12345,
  "region_hint": "Vancouver",
  "title": "Cafe Staff Needed",
  "wage_min": 17,
  "wage_max": 20,
  "location_text": "123 Main St, Vancouver, BC",
  "category": "cafe",
  "posted_at": "2024-01-15T10:30:00Z"
}
```

- **처리 로직:**

  1. API Key 검증
  2. URL 중복 검사 (`source_url` 기준)
  3. 주소 텍스트 → 지오코딩(OpenStreetMap Nominatim)
  4. 지오코딩 실패 시 fallback 처리 (region_hint 기반 중심 좌표 사용, confidence 낮춤)
  5. `geom` 생성 및 confidence 계산
  6. UPSERT 실행 (중복 시 업데이트)

- **응답 스키마:**

```json
{
  "success": true,
  "data": {
    "id": 12345,
    "msgid": 12345,
    "source_url": "https://jpcanada.com/topics.php?msgid=12345",
    "lat": 49.2827,
    "lng": -123.1207,
    "confidence": 0.85,
    "created": true
  }
}
```

- **에러 응답:**

```json
{
  "success": false,
  "error": {
    "code": "GEOCODING_FAILED",
    "message": "Failed to geocode location",
    "details": {
      "location_text": "123 Main St, Vancouver, BC"
    }
  }
}
```

### 5.4 `GET /api/jobs/clusters`

- **설명:** 줌 레벨별 클러스터링 데이터 반환
- **파라미터:**

  - `minLng`, `minLat`, `maxLng`, `maxLat` (float, required): 경계 박스
  - `zoom` (int, required): 현재 줌 레벨 (클러스터 크기 결정)
  - `wageMin`, `wageMax` (int, optional): 시급 필터
  - `category` (string, optional): 직종 필터

- **방식:** PostGIS `ST_ClusterWithin()` 사용
- **응답 스키마:**

```json
{
  "success": true,
  "data": [
    {
      "id": "cluster_1",
      "center": {
        "lat": 49.2827,
        "lng": -123.1207
      },
      "count": 15,
      "bounds": {
        "minLng": -123.13,
        "minLat": 49.27,
        "maxLng": -123.11,
        "maxLat": 49.29
      }
    }
  ],
  "meta": {
    "zoom": 12,
    "cluster_count": 5
  }
}
```

---

## 6. 크롤러 로직

### 6.1 기본 크롤링 흐름

1️⃣ `listing.php?bbs={ID}` 요청 → 최신 목록 수집  
2️⃣ HTML에서 `topics.php?...msgid=XXXX` 정규식 추출  
3️⃣ `msgid` 커서 기반 페이지 순회 (`min_msgid - 1`)  
4️⃣ 신규 URL 감지 (`msgid > last_seen_max_msgid`) 시 `/internal/ingest` 호출  
5️⃣ 2.5초 간격 sleep + 예외시 백오프 처리

### 6.2 상세 구현 로직

**초기화:**

- `crawl_log` 테이블에서 해당 BBS의 `last_seen_msgid` 조회
- 없으면 0으로 시작

**페이지 크롤링:**

```python
# 의사코드
last_msgid = get_last_seen_msgid(bbs_id)
current_msgid = fetch_latest_msgid(bbs_id)

while current_msgid > last_msgid:
    page_url = f"listing.php?bbs={bbs_id}&min_msgid={current_msgid}"
    html = fetch_with_retry(page_url)
    msgids = extract_msgids(html)

    for msgid in msgids:
        if msgid > last_msgid:
            job_data = scrape_job_detail(msgid)
            ingest_to_api(job_data)
            sleep(2.5)

    current_msgid = min(msgids) - 1
    update_crawl_log(bbs_id, max(msgids))
```

**에러 처리 및 재시도:**

- 네트워크 오류: 지수 백오프 (2초 → 4초 → 8초), 최대 3회 재시도
- HTTP 429 (Rate Limit): 60초 대기 후 재시도
- 파싱 오류: 로그 기록 후 다음 항목으로 진행
- API ingest 실패: 로그 기록, 재시도 큐에 추가 (별도 프로세스)

**로깅:**

- 각 크롤링 세션 시작/종료 시간 기록
- 처리된 게시글 수, 실패 수 기록
- 에러 상세 정보 기록 (에러 타입, 메시지, URL)

**데이터 정제:**

- HTML 태그 제거
- 시급 정보 정규식 추출 (`$XX/hour`, `$XX-XX/hour` 등)
- 위치 텍스트 정규화 (도시명, 주소 형식 통일)
- 중복 검사: `source_url` 기준, 전화번호/이메일 해시 기반 (선택)

### 6.3 지오코딩 실패 처리

**Fallback 전략:**

1. Nominatim API 호출 (1차)
2. 실패 시 `region_hint` 기반 중심 좌표 사용
3. `confidence` 값 설정:
   - 성공: 0.8 ~ 1.0 (주소 정확도에 따라)
   - region_hint 기반: 0.5
   - 완전 실패: 0.3 (수동 검토 필요)

**지오코딩 요청 제한:**

- Nominatim: 1초당 1회 요청 (공식 제한 준수)
- 실패 시 5초 대기 후 재시도 (최대 2회)

---

## 7. 지도 검색 로직

- **Viewport 검색**: PostGIS Envelope 기반 교차 쿼리(`ST_Intersects`)
- **Radius 검색**: `ST_DWithin`
- **클러스터링**: 줌레벨에 따라 서버단 샘플링
- **캐시**: Redis layer (TTL 60초) 사용 가능

---

## 8. 보안 및 정책

### 8.1 크롤링 정책

- robots.txt 준수, User-Agent 명시
- 요청 간격 ≥ 2.5초, 야간 빈도 제한
- 게시글 본문/이미지 저장 금지 (URL, 위치, 시급 메타만)

### 8.2 인증/인가

**API Key 인증 (`/internal/ingest`):**

- 헤더: `X-API-Key: <API_KEY>`
- 검증 방식: 환경 변수 `API_KEY`와 비교
- 실패 시: 401 Unauthorized 응답

**Admin 인증 (향후):**

- IP 화이트리스트 기반 접근 제어
- JWT 토큰 기반 인증 (선택)
- 2단계 인증 권장

**CORS 정책:**

- 프론트엔드 도메인만 허용
- 프로덕션: Vercel 도메인만 허용
- 개발 환경: localhost 허용

---

## 9. 배포 구조

| 서비스     | 호스팅       | 비고                         |
| ---------- | ------------ | ---------------------------- |
| 프론트엔드 | Vercel       | Next.js 15 + Static export   |
| 백엔드     | EC2 / Render | FastAPI + Uvicorn (Gunicorn) |
| DB         | Supabase     | PostGIS 확장 사용            |
| 크롤러     | EC2 크론잡   | Python3 + Requests           |

---

## 10. 향후 기술 확장

- 🧠 Elasticsearch / Typesense 도입 (풀텍스트 + 시급 정렬)
- 🗺️ Mapbox Vector Tile (MVT) API 지원 → 클러스터 성능 향상
- ☁️ Docker Compose 기반 통합 배포
- 🧭 geocoding accuracy 강화 (Google Maps API fallback)

---

## 12. 환경 변수 목록

### 백엔드 환경 변수

| 변수명          | 설명                                  | 필수 | 기본값                                |
| --------------- | ------------------------------------- | ---- | ------------------------------------- |
| `DATABASE_URL`  | Supabase PostgreSQL 연결 문자열       | ✅   | -                                     |
| `API_KEY`       | `/internal/ingest` 엔드포인트 인증 키 | ✅   | -                                     |
| `NOMINATIM_URL` | OpenStreetMap Nominatim API URL       | ❌   | `https://nominatim.openstreetmap.org` |
| `LOG_LEVEL`     | 로깅 레벨                             | ❌   | `INFO`                                |
| `CORS_ORIGINS`  | 허용된 CORS 오리진 (쉼표 구분)        | ❌   | `*` (개발 환경)                       |

### 프론트엔드 환경 변수

| 변수명                       | 설명                        | 필수 | 기본값 |
| ---------------------------- | --------------------------- | ---- | ------ |
| `NEXT_PUBLIC_API_URL`        | 백엔드 API 기본 URL         | ✅   | -      |
| `NEXT_PUBLIC_MAPLIBRE_TOKEN` | MapLibre 스타일 토큰 (선택) | ❌   | -      |

### 크롤러 환경 변수

| 변수명           | 설명                     | 필수 | 기본값                                |
| ---------------- | ------------------------ | ---- | ------------------------------------- |
| `API_BASE_URL`   | 백엔드 API 기본 URL      | ✅   | -                                     |
| `API_KEY`        | 인증 키                  | ✅   | -                                     |
| `CRAWL_INTERVAL` | 크롤링 간격 (초)         | ❌   | `2.5`                                 |
| `USER_AGENT`     | 크롤러 User-Agent 문자열 | ❌   | `JobMapCrawler/1.0`                   |
| `NOMINATIM_URL`  | Nominatim API URL        | ❌   | `https://nominatim.openstreetmap.org` |

---

## 13. 의존성 패키지 목록

### 백엔드 (requirements.txt)

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
alembic==1.12.1
httpx==0.25.1
```

### 프론트엔드 (package.json)

```json
{
  "dependencies": {
    "next": "^15.0.0",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.2.2",
    "tailwindcss": "^3.3.5",
    "maplibre-gl": "^3.6.2",
    "@types/maplibre-gl": "^3.0.0"
  },
  "devDependencies": {
    "@types/node": "^20.9.0",
    "@types/react": "^18.2.37",
    "@types/react-dom": "^18.2.15",
    "autoprefixer": "^10.4.16",
    "postcss": "^8.4.31"
  }
}
```

### 크롤러 (requirements.txt)

```
requests==2.31.0
beautifulsoup4==4.12.2
lxml==4.9.3
python-dotenv==1.0.0
httpx==0.25.1
```

---

이 문서는 JobMap MVP의 **백엔드 및 인프라 구현 세부사항**을 정의합니다.

---

## 11. Information Architecture (IA)

### 11.1 목적

- 사용자가 **지도 중심으로 빠르게 일자리 탐색** → 최소 클릭, 즉시 피드백.
- 운영자는 **위치추론 결과 품질 관리**와 **삭제/차단 대응**을 신속히 수행.

### 11.2 최상위 내비게이션 구조 (Sitemap)

```
/                          # 홈(지도)
  ├─ /search               # 뷰포트/반경 검색 API 연동형 페이지(동일 UI, 쿼리 파라미터로 상태 유지)
  ├─ /job/:id              # 상세(요약 메타 + 원문 열기 링크)
  ├─ /favorites            # (차후) 즐겨찾기/알림
  ├─ /about                # 서비스 소개/정책
  └─ /admin                # 운영자 영역(보호)
      ├─ /admin/review     # 위치추론 리뷰 큐(confidence 낮은 항목)
      ├─ /admin/logs       # 크롤/지오코딩 로그
      └─ /admin/settings   # 소스/크롤 주기/차단목록
```

### 11.3 화면 인벤토리 (Page Inventory)

| ID  | 화면      | 목적                   | 주요 컴포넌트                                                                     |
| --- | --------- | ---------------------- | --------------------------------------------------------------------------------- |
| P1  | 홈/지도   | 지도 중심 탐색(진입점) | 지도(핀/클러스터), 리스트 패널, 필터 바, "이 지역에서 검색" 버튼, 토스트(결과 수) |
| P2  | 상세 팝업 | 선택 공고 요약         | 제목/시급/정확도, 원문 링크, 공유/저장(후순위)                                    |
| P3  | 즐겨찾기  | 저장 목록              | 카드 리스트, 정렬/필터                                                            |
| P4  | 어바웃    | 정책/문의              | 서비스 요약, 크롤링 정책, 연락처                                                  |
| A1  | 리뷰 큐   | 저품질 위치추론 검수   | 테이블(정렬/필터), 지도 미니뷰, 승인/수정/보류                                    |
| A2  | 로그      | 크롤/인입 현황         | 차트(요청 수/실패율), 최근 에러 리스트                                            |
| A3  | 세팅      | 소스/차단/키           | 소스(YAML), 크롤 주기, 블록리스트, API 키 관리                                    |

### 11.4 핵심 사용자 흐름 (User Flows)

**UF-1. 지도 탐색 & 뷰포트 검색**

1. P1 진입 → 기본 뷰(밴쿠버 중심) 로드
2. (선택) 위치권한 허용 → 현재 위치로 이동
3. 사용자가 지도 이동/확대 → 디바운스 400ms 후 `/api/jobs/viewport` 호출
4. 결과 수 토스트 + 핀/클러스터 갱신, 리스트 패널 동기화
5. 항목 클릭 시 P2 팝업 오픈 → "View on JPCanada" 새 탭 이동

**UF-2. 반경 검색(nearby)**

1. 현재 위치 버튼 클릭 → 좌표 획득
2. 반경 슬라이더 조정(예: 3km)
3. `/api/jobs/nearby` 호출 → 거리순 리스트/핀 표시
4. 상세 팝업/원문 이동

**UF-3. 필터 적용(시급/카테고리)**

1. 상단 필터 바에서 범위/체크박스 선택
2. 쿼리파라미터에 상태 반영(공유 가능 URL)
3. 현재 뷰포트 기준 재검색 → 리스트/핀 재렌더
4. 활성 필터 배지 표시, 초기화 버튼 제공

**UF-4.(선택) 즐겨찾기/알림**

1. P2 팝업에서 ‘저장’ 클릭 → 로컬/계정 기반 저장
2. 북마크 목록(P3)에서 관리
3. 알림 구독 지역 설정(후순위)

**UF-5. 운영자 리뷰(품질 관리)**

1. A1 진입 → `confidence < 0.6` 항목 목록
2. 항목 선택 → 미니 지도에서 위치 수정(드래그/검색)
3. 승인 시 DB 업데이트, 실패 시 보류 사유 기록
4. 변동사항 이력 A2에서 확인

### 11.5 정보 구조(도메인 모델 요약)

- **JobSource**: id, msgid, source_url, geom(lat/lng), wage_min/max, category, confidence, posted_at, region_hint
- **ViewportQuery**: bbox, zoom, filters(category, wage, text?), paging
- **Cluster**(옵션): center(lat/lng), count, bounds, childIds
- **ReviewItem**: job_id, reason, suggested_point, status(pending/approved/hold)

### 11.6 컴포넌트 트리 (프론트)

```
<App>
 ├─ <Header/>
 ├─ <Layout>
 │   ├─ <Sidebar>
 │   │   └─ <ResultList> → <ResultItem>
 │   └─ <MapPane>
 │       ├─ <MapView> (핀/클러스터)
 │       ├─ <SearchThisAreaButton/>
 │       └─ <FiltersBar/>
 └─ <JobDetailDrawer/> (또는 <BottomSheet/>)
```

### 11.7 상태 관리 & URL 설계

- 전역: `viewport={bbox,zoom}`, `filters={wageMin,wageMax,category[]}`, `selection=jobId|null`
- URL 쿼리 예:  
  `/?minLng=-123.2&minLat=49.2&maxLng=-123.0&maxLat=49.32&zoom=12&wageMin=17&cat=cafe`
- 히스토리: 지도 이동/필터 변경 시 `replaceState`로 과도한 기록 방지

### 11.8 접근성/모바일 가이드

- 키보드 포커스 링, 핀 aria-label, 리스트-지도 포커스 동기화
- 모바일: 지도 위 하단 **Bottom Sheet**로 리스트 표시, 스와이프 제스처
- 성능: 300ms 디바운스, 스켈레톤 로딩, 가상 리스트(>100 항목)

### 11.9 에러/로딩 UX

- 로딩: 지도 상단 스켈레톤 + 리스트 플레이스홀더
- 에러: 토스트 + 재시도 버튼, 일부 실패 시 부분 결과 유지
- 빈 결과: "이 지역에서 검색 범위를 넓혀보세요" 제안

### 11.10 권한/보안

- 공개: P1, P2, P4
- 인증: P3(선택), Admin(A1~A3)
- Admin 접근: IP 제한 + 로그인(2단계 권장)
