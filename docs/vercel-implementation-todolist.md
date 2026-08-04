# Vercel Implementation Todo List

## Purpose

This document tracks the implementation work for the Vercel deployment plan.

Use it as the live execution board while implementing:

- Update statuses as work progresses.
- Keep task sizes visible.
- Record verification evidence before marking a task done.
- Keep open questions separate from implementation tasks.

Related plan:

- [Vercel Deployment Plan](./vercel-deployment-plan.md)

## Status Legend

| Status | Meaning |
| --- | --- |
| `TODO` | Not started |
| `DOING` | Currently in progress |
| `BLOCKED` | Waiting on a decision, credential, tool, or external service |
| `VERIFY` | Implemented, waiting for validation |
| `DONE` | Implemented and verified |

## Size Legend

| Size | Meaning |
| --- | --- |
| `L` | Large milestone or subsystem |
| `M` | Medium implementation slice |
| `S` | Small concrete task |

## Progress Snapshot

| Milestone | Status | Notes |
| --- | --- | --- |
| M1. Deployment Foundation | `DONE` | Vercel Services, local Supabase-ready schema migration, Next public API, Python crawler service shell |
| M2. Operations Admin | `DONE` | Admin auth, source status, crawl runs, manual source execution |
| M3. Dedupe and Data Quality | `DONE` | `jobs` model, cross-source dedupe, duplicate review, audit log |
| M4. Public Map UX | `DONE` | Responsive map/list workspace and accessible public search controls |
| M5. Multi-source Crawling | `DONE` | Public adapters and verified initial ingestion for Our Vancouver, Jinzai Canada, and Vanchosun |
| M6. Data Retention | `DONE` | Scheduled crawl removes records older than 14 days and reconciles representative jobs |
| M7. Crawl Quality | `DONE` | AI-assisted quality gate with business-name location precedence and grounded neighborhood fallback |
| M8. Public Localization | `DONE` | Four-language public UI, localized job titles, and visible posting/first-seen dates |
| M10. Current Multi-source Feed | `DONE` | Refreshed live Jinzai Canada and Vanchosun listings, added conservative duplicate reconciliation with preserved audit history, and published a verified temporary Cloudflare preview |

## M1. Deployment Foundation

Goal: make the project deployable on Vercel with a Next.js web service, Python crawler service, and Supabase/PostGIS database.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M1-01 | S | `DONE` | Add root `vercel.json` with `web` and `crawler` services plus cron path. | `vercel.json` validates and service paths match repo layout. |
| M1-02 | M | `DONE` | Add Supabase-ready migrations for new production schema without breaking local Docker setup. | `003_vercel_foundation.sql` applied on local PostGIS. |
| M1-03 | M | `DONE` | Add server-only DB helper in `frontend` using `pg` and lazy initialization. | `npm run build` passes without DB access during build. |
| M1-04 | M | `DONE` | Implement `GET /api/jobs/viewport` as a Next.js Route Handler. | Route returns compatible `ApiResponse<JobSource[]>`. |
| M1-05 | M | `DONE` | Implement `GET /api/jobs/nearby` as a Next.js Route Handler. | Route returns distance-sorted compatible response. |
| M1-06 | S | `DONE` | Remove frontend dependency on `NEXT_PUBLIC_API_URL` and use relative `/api/...` calls. | Browser loads `http://localhost:3000/` with no backend FastAPI dependency. |
| M1-07 | M | `DONE` | Add `crawler/api.py` FastAPI entrypoint with `/cron/crawl` route. | `/health` returns `200`; invalid cron auth returns `401`; valid auth returns summary JSON. |
| M1-08 | M | `DONE` | Refactor crawler DB writes to use Supabase/Postgres directly instead of old `/internal/ingest`. | Controlled crawler smoke test wrote one `job_sources` row and cleaned it up. |
| M1-09 | S | `DONE` | Document required Vercel env vars and local `.env` parity. | README and plan point to required env setup. |
| M1-10 | S | `DONE` | Run baseline validation. | `npm run lint`, `npm run build`, Python compile/import, route smoke tests, and browser check passed. |

## M2. Operations Admin

Goal: make crawling operable through a protected admin UI.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M2-01 | M | `DONE` | Add single-admin login using `ADMIN_PASSWORD` and signed session cookie. | `/admin` redirects to `/admin/login`; login with local admin password reaches dashboard. |
| M2-02 | S | `DONE` | Add logout flow. | Logout clears session and returns to `/admin/login`. |
| M2-03 | M | `DONE` | Add source registry model. | `crawler_sources` exists and JPCanada appears as an active source. |
| M2-04 | M | `DONE` | Define Python `CrawlerAdapter` interface and register JPCanada as the first adapter. | `CrawlerAdapter` and `JPCanadaAdapter` are registered through the adapter registry. |
| M2-05 | M | `DONE` | Add crawl run summary table. | `crawl_runs` records cron/manual summaries with source, status, counts, timestamps, and representative error. |
| M2-06 | M | `DONE` | Add limited crawl failure item table. | Controlled failure persisted one failed msgid/error item in `crawl_failures`. |
| M2-07 | M | `DONE` | Build admin source dashboard. | Admin dashboard shows source enabled state, last status, recent runs, and failures. |
| M2-08 | M | `DONE` | Add source enable/disable action. | Browser check toggled JPCanada off/on and run button disabled while off. |
| M2-09 | M | `DONE` | Add source-level manual run action. | Crawler admin route recorded manual JPCanada runs; admin dashboard exposes source-level run action. |
| M2-10 | S | `DONE` | Add internal failure emphasis in admin. | Browser check showed failed run and failure item after controlled failure. |

## M3. Dedupe and Data Quality

Goal: support multi-source normalized jobs with conservative automatic merging and admin duplicate controls.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M3-01 | M | `DONE` | Add `jobs` representative table separate from raw `job_sources`. | Public API reads from `jobs`; raw source records remain preserved. |
| M3-02 | M | `DONE` | Update crawler write flow to attach each `job_sources` row to a representative `jobs` row. | Controlled upserts linked `job_sources.job_id` to representative `jobs`. |
| M3-03 | M | `DONE` | Enforce public visibility threshold `confidence >= 0.6`. | Low-confidence records are stored but not returned by public map APIs. |
| M3-04 | M | `DONE` | Implement conservative cross-source duplicate scoring. | Similar title + same city/region + similar wage created duplicate candidates. |
| M3-05 | M | `DONE` | Add duplicate candidate table. | `duplicate_candidates` stores ambiguous pending/approved/rejected candidates. |
| M3-06 | M | `DONE` | Add automatic merge history table. | `job_merge_history` records merge and rollback actions. |
| M3-07 | M | `DONE` | Add admin duplicate review screen. | Browser check showed candidate pairs and comparison fields in admin. |
| M3-08 | M | `DONE` | Add approve/reject duplicate candidate actions. | Browser check approved one candidate and rejected another. |
| M3-09 | M | `DONE` | Add merge rollback action. | Browser check rolled back an approved merge and created a new representative job. |
| M3-10 | M | `DONE` | Add admin audit log. | Manual crawl, duplicate approve/reject, and rollback actions are recorded in `admin_audit_log`. |

## M4. Public Map UX

Goal: make the public map search usable and visually coherent across desktop and mobile without changing API behavior.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M4-01 | M | `DONE` | Redesign the public JobMap workspace with shared design tokens, accessible controls, and a mobile list/map switcher. | `npm run lint`, `npm run build`, and browser checks at 320, 375, 414, 768, and desktop widths pass. |
| M4-02 | S | `DONE` | Stop the selected-job map focus effect from retriggering viewport searches after every jobs response. | Selecting a job produces a bounded viewport request count and the loading indicator settles. |
| M4-03 | S | `DONE` | Add a major-city quick selector that moves the map without geocoding. | Each preset moves to the expected city and remains usable at mobile widths. |
| M4-04 | S | `DONE` | Show the number of visible jobs beside every major-city selector option. | One aggregate request returned confidence-filtered counts; lint, build, and mobile browser checks passed. |

## M5. Multi-source Crawling

Goal: expand public job ingestion beyond JPCanada while preserving source isolation, conservative request rates, and existing dedupe behavior.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M5-01 | M | `DONE` | Add public-page adapters and source registry entries for Our Vancouver, Jinzai Canada, and Vanchosun. | Nine crawler tests, Python compile, local migration, live batches, frontend lint/build, and public API checks passed. |

## M6. Data Retention

Goal: keep public job data current by removing stale source records and their orphaned representative jobs.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M6-01 | S | `DONE` | Delete job source records older than 14 days during the authenticated scheduled crawl and reconcile representative jobs. | Removed 18 expired local source rows and 18 representatives plus one old orphan; index/FKs valid, 11 crawler tests and compile pass, frontend lint/build pass, and public APIs return 200. |

## M7. Crawl Quality

Goal: prevent advertisements and locationless community posts from appearing as map jobs while preserving grounded neighborhood inference.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M7-01 | M | `DONE` | Add a fail-closed Our Vancouver quality gate with deterministic checks and optional Codex Bridge analysis for ambiguous job/location text. | 21 crawler tests and compile pass; seven invalid, multi-location, or inaccessible duplicate records removed, 405992 maps to Lougheed, DB integrity is clean, frontend lint/build pass, and live APIs exclude all four reported invalid markers. |
| M7-02 | S | `DONE` | Prefer AI-extracted business landmarks over broad neighborhood markers while retaining a grounded neighborhood fallback. | 22 crawler tests and compile pass; live public API and browser details show 405995 at Hongdae Pocha coordinates (49.2898464, -123.133158), 405992 remains at Lougheed, and DB source linkage checks are clean. |

## M8. Public Localization

Goal: let public users browse JobMap in Korean, English, Japanese, or Simplified Chinese while keeping posting dates and job titles understandable in the selected language.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M8-01 | M | `DONE` | Add a persistent four-language selector, localize the public map/search/list/detail UI, show a posting-date row on every job card, and serve crawler-generated title translations with original-title fallback. | Frontend lint/build, 26 Python tests and compile, idempotent local migration, viewport/nearby API checks, 20/20 local title translations, and KO/EN/JA/ZH desktop/mobile browser flows passed; console errors 0. |

## M9. Public Map Context

Goal: make each public result's origin clear and help users orient the job map around their own position without collecting location data server-side.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M9-01 | S | `DONE` | Show the originating site name in public job cards and details, and add an opt-in browser current-location marker with localized permission and failure feedback. | Frontend lint/build and diff check passed; viewport/nearby APIs returned source names for 18/18 jobs; Playwright verified source labels/details, successful and denied geolocation flows, KO/ZH desktop/mobile/landscape layouts, 44px location control, reduced motion, no overflow, no error overlay, and 0 console errors. |
| M9-02 | S | `DONE` | Display only the source site's actual publication date, parse source-specific publication metadata, and backfill missing dates without exposing crawler collection time. | Python tests/compile, frontend lint/build, and diff check passed; all 20 stored source rows were backfilled from source publication metadata, public APIs returned actual dates for 18/18 visible jobs with zero estimated dates, and desktop/mobile browser checks verified localized posted-date labels with no crawl-date fallback, overflow, overlay, or page errors. |

## M10. Current Multi-source Feed

Goal: keep the public feed current across active sources, collapse high-confidence duplicate representatives, and provide a temporary public preview.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M10-01 | M | `DONE` | Refresh live Jinzai Canada and Vanchosun listings and reconcile high-confidence cross-source or same-source duplicate representatives while preserving raw sources. | Live DB contains 40 raw sources and 40 representatives with no high-confidence duplicate pair; public API exposes 29 map-eligible jobs from three sources with complete four-language titles and actual source dates. Python compile, 41 tests, transactional merge-history checks, DB integrity checks, and Claude remediation revalidation passed. |
| M10-02 | S | `DONE` | Expose the verified local frontend through a temporary Cloudflare Quick Tunnel. | Quick Tunnel returned HTTP 200; its viewport API returned the same 29 jobs from three sources, and real-browser checks found meaningful content, no error overlay, and no console errors. |

## Progress Update Rules

During implementation, keep this document current:

1. Move one task to `DOING` before starting it.
2. Move completed code work to `VERIFY` before running checks.
3. Move to `DONE` only after recording verification in the final update or task notes.
4. Use `BLOCKED` with a short note when waiting on Supabase, Vercel, credentials, or a product decision.
5. Do not mark a whole milestone `DONE` until all child tasks are `DONE`.

## Execution Order

Recommended order:

1. Complete M1 before M2.
2. Complete admin auth from M2 before adding manual run actions.
3. Complete the `jobs`/`job_sources` model split before duplicate review UI.
4. Keep the old `backend/` app as reference until M1 and M2 are verified.
5. Remove or archive legacy backend only after production deployment proves the new path works.

## Open Questions

| Question | Default |
| --- | --- |
| Is the Supabase project already created? | Treat as not created until credentials are available. |
| Admin session duration? | 12 hours. |
| Duplicate title similarity method? | Start with normalized token/Jaccard-style string similarity in app code. |
| Batch size for cron crawl? | Source-level run with conservative per-source limits; tune after first real run. |
| External failure alerts? | Excluded from v1; admin internal status only. |
