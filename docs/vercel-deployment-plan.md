# Vercel Deployment Plan

## Summary

JobSearch will be deployed as a single Vercel project with two services:

- `web`: the existing Next.js frontend and user-facing API routes.
- `crawler`: the existing Python crawler, wrapped as a FastAPI service.

The production database will be Supabase PostgreSQL with PostGIS enabled. Local development will keep using the Docker PostGIS database.

Execution tracker:

- [Vercel Implementation Todo List](./vercel-implementation-todolist.md)

## Target Architecture

```text
Browser
  -> Vercel Next.js web service
      -> /api/jobs/viewport
      -> /api/jobs/nearby
      -> Supabase PostGIS

macOS LaunchAgent (owner's Mac, every 6 hours)
  -> production DATABASE_URL from macOS login Keychain
  -> local Python crawler + local Codex Bridge
  -> JPCanada, Our Vancouver, Jinzai Canada, and Vanchosun crawls
  -> Supabase PostGIS

Authenticated manual operations
  -> /crawler/cron/crawl or /crawler/admin/run
  -> Vercel Python crawler service
```

## Vercel Services

Use Vercel Services so the frontend and Python crawler can live in one Vercel project.

Planned root `vercel.json`:

```json
{
  "services": {
    "web": {
      "root": "frontend/",
      "framework": "nextjs"
    },
    "crawler": {
      "root": "crawler/",
      "framework": "fastapi",
      "entrypoint": "api:app"
    }
  },
  "rewrites": [
    { "source": "/crawler/(.*)", "destination": { "service": "crawler" } },
    { "source": "/(.*)", "destination": { "service": "web" } }
  ]
}
```

In Vercel Project Settings, set the Framework Preset to `Services`.

## Frontend and Public API

Move the public job search API from the current FastAPI backend into the Next.js app.

Required Next.js routes:

```text
GET /api/jobs/viewport
GET /api/jobs/nearby
```

The response shape should stay compatible with the current frontend:

```ts
{
  success: boolean
  data?: T
  meta?: object
  error?: {
    code: string
    message: string
    details?: unknown
  }
}
```

Frontend changes:

- Remove `NEXT_PUBLIC_API_URL`.
- Use relative API calls such as `/api/jobs/viewport`.
- Keep the existing map, filter, and job list behavior.

## Python Crawler Service

Keep the crawler in Python.

Add a FastAPI entrypoint at:

```text
crawler/api.py
```

Required route:

```text
GET /cron/crawl
```

External URL after Vercel routing:

```text
/crawler/cron/crawl
```

Expected behavior:

- Verify `Authorization: Bearer ${CRON_SECRET}`.
- Load `regions` from Supabase.
- Read `crawl_log` to avoid re-processing old posts.
- Crawl enabled public listing sources through registered adapters.
- Crawl new job detail pages.
- Reuse the existing Python parsing logic from `crawler/src/crawler.py`.
- For Our Vancouver, reject obvious advertisements and locationless posts before
  geocoding; use Codex Bridge only for ambiguous job/location text when configured.
- Geocode grounded addresses, businesses, or neighborhoods. If a reviewed precise
  location cannot be resolved, keep it off the public map instead of falling back
  to a city-center marker.
- Upsert records into `job_sources`.
- Update `crawl_log`.
- After all enabled sources finish, delete source records older than 14 days using
  `posted_at` with `created_at` as the fallback, then reconcile or remove their
  representative `jobs` rows.
- Return a JSON summary with counts for processed, created, updated, skipped, and failed items.

The crawler should write to Supabase directly instead of calling the old `/internal/ingest` backend API.

## Database

Production database:

```text
Supabase PostgreSQL + PostGIS
```

Local database:

```text
Docker PostGIS on localhost:5432
```

Required schema files:

```text
database/migrations/001_initial_schema.sql
database/migrations/002_update_regions_urls.sql
database/migrations/003_vercel_foundation.sql
database/migrations/004_operations_admin.sql
database/migrations/005_dedupe_data_quality.sql
database/migrations/006_multi_source_adapters.sql
database/migrations/007_job_retention.sql
database/migrations/008_job_title_translations.sql
database/migrations/009_preserve_merge_history_previous_job.sql
database/migrations/010_crawl_seen_items.sql
database/migrations/20260804075445_jobmap_data_api_lockdown.sql
database/migrations/20260804075725_jobmap_revoke_public_schema_access.sql
database/migrations/20260804075814_jobmap_foreign_key_indexes.sql
```

Required extension:

```sql
CREATE EXTENSION IF NOT EXISTS postgis;
```

Required tables:

```text
regions
job_sources
crawl_log
crawler_sources
crawl_runs
crawl_failures
jobs
duplicate_candidates
job_merge_history
admin_audit_log
crawl_seen_items
```

## Environment Variables

Set these in Vercel:

```text
DATABASE_URL
CRON_SECRET
CRAWLER_MAX_POSTS_PER_REGION
OURVANCOUVER_MAX_POSTS_PER_REGION
ADMIN_PASSWORD
SESSION_SECRET
CRAWLER_SERVICE_URL
NOMINATIM_URL
CODEX_BRIDGE_BASE_URL optional
CODEX_BRIDGE_API_KEY optional
CODEX_BRIDGE_MODEL optional
CODEX_BRIDGE_TIMEOUT_SECONDS optional
```

Notes:

- `DATABASE_URL`: Supabase PostgreSQL connection string.
- `CRON_SECRET`: secret used to authorize cron-triggered crawler requests.
- `CRAWLER_MAX_POSTS_PER_REGION`: conservative per-region batch size for crawler runs.
- `OURVANCOUVER_MAX_POSTS_PER_REGION`: source-specific scheduled batch size for the high-volume Our Vancouver backlog; explicit admin-run limits still take precedence.
- `ADMIN_PASSWORD`: single v1 admin password.
- `SESSION_SECRET`: signing secret for the admin session cookie.
- `CRAWLER_SERVICE_URL`: crawler service base URL for admin manual runs. Local default is `http://localhost:8001`; Vercel default can be inferred from `VERCEL_URL` and `/crawler`.
- `NOMINATIM_URL`: optional; default can remain OpenStreetMap Nominatim.
- `CODEX_BRIDGE_*`: server-only settings for ambiguous Our Vancouver post analysis
  and bounded Korean/English/Japanese/Chinese title-translation batches. Without
  them, the quality gate fails closed for unresolved posts and public titles fall
  back to their original source text.

Do not expose database, crawler, or Codex Bridge credentials through `NEXT_PUBLIC_*` variables.

## Local Development

Start the local database:

```bash
docker compose up -d db
```

Run the Next.js web app:

```bash
cd frontend
npm run dev
```

Run the Python crawler service locally:

```bash
cd crawler
source .venv/bin/activate
uvicorn api:app --reload --port 8001
```

Local service map:

```text
frontend: http://localhost:3000
admin:    http://localhost:3000/admin
crawler:  http://localhost:8001
database: localhost:5432
```

The current `backend/` app should remain as reference until the Vercel-oriented API and crawler service are verified.

## Test Plan

Frontend and API:

- `npm run lint`
- `npm run build`
- Verify `/api/jobs/viewport`.
- Verify `/api/jobs/nearby`.
- Verify the map loads without the FastAPI backend running.

Crawler service:

- Python import or compile check.
- FastAPI route test for `/cron/crawl`.
- Missing or invalid `Authorization` returns `401`.
- Valid `Authorization` returns a crawl summary.
- Crawl run inserts or updates `job_sources`.
- Crawl run updates `crawl_log`.

Deployment:

- Apply database migrations to Supabase.
- Configure Vercel environment variables.
- Deploy preview.
- Verify UI, job search APIs, and crawler route.
- Deploy production.
- Install and inspect the macOS LaunchAgent.
- Confirm local crawler logs, four-language title backfill, and Supabase DB changes after a scheduled run.

## Assumptions

- Python crawler logic remains in Python.
- Public job search APIs move into Next.js.
- No separate Render/Fly backend will be used.
- Production scheduled crawling runs from the owner's Mac every six hours so the local Codex Bridge is available; the Vercel HTTP crawler remains an authenticated manual fallback.
- Supabase PostGIS is available for production.
- The old FastAPI backend is retained temporarily as reference, not as a production service.
