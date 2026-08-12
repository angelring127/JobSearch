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
| M11. Our Vancouver Completeness | `DONE` | Daum pagination, bounded 14-day backlog processing, and seen-item tracking independently revalidated |
| M12. Mobile Map-First Header | `DONE` | Mobile map default, synchronized top-bar region selection, and compact language control verified |
| M13. Mobile Map Loading Context | `DONE` | Vancouver-first map, localized mobile region counts, and request-safe viewport loading feedback verified and independently revalidated |
| M14. Vercel Deployment | `DONE` | Supabase secured and production deployment verified end to end with the pooled database connection |
| M15. Production Crawl Recovery | `DONE` | Current Our Vancouver markup is accepted and the verified production replay exposes 15 deduplicated map jobs |
| M16. Local Production Crawl | `DONE` | Keychain-backed Library runtime completed a real production crawl and focused independent revalidation passed |
| M18. Map Location Accuracy | `DONE` | AI-assisted re-resolution, fail-closed location handling, production data repair, deployment, and public map/API validation complete |
| M19. Vercel Web Analytics | `DONE` | Privacy-friendly pageview analytics enabled, independently reviewed, deployed, and verified on the production domain |
| M20. Compact Language Selector | `DONE` | The compact selector now uses polished circular SVG flags and an accessible menu that shows each flag with its country and language name. |
| M21. Compact Mobile Search | `DONE` | Mobile density work passed independent review and local/preview/production validation, then shipped to the production domain. |
| M22. Mobile List Detail Visibility | `DONE` | Mobile list view now keeps the selected card context without displaying the job-detail panel; map and desktop details remain available. |

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
| M8-02 | S | `DONE` | Default the public UI to the device/browser language on first visit, fall back to English for unsupported languages, and keep an explicit language selection across visits. | Frontend lint/build and diff check passed; request checks verified KO/EN/JA/ZH HTML, metadata, fallback, quality ordering, and saved-cookie priority. Independent review found one Medium cookie/local-storage divergence and one Low cookie-hardening gap; both were fixed and focused revalidation passed. Production deployment `dpl_GQLFRD57GHaJrM1viazgcA2Djtto` is `READY` on `jobmap.narulabs.ca`; production request checks verified all four locales, English fallback, cookie priority, public API `200`, and crawler auth rejection `401`. Playwright verified device-default Korean plus persisted Japanese UI/title/HTML language/local storage/Secure cookie after reload with 0 console errors. |

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

## M11. Our Vancouver Completeness

Goal: discover Our Vancouver postings beyond page 1 while limiting ingestion and
public retention to the current two-week window.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M11-01 | M | `DONE` | Paginate the Daum mobile listing, process unseen recent posts in bounded new-first batches, and retain public records for 14 days. | 49 crawler tests and compile pass; live discovery found the bounded recent window, controlled batches preserved public data quality, migration ordering was remediated, and independent revalidation passed. |

## M12. Mobile Map-First Header

Goal: prioritize map browsing on phones and keep region/language controls usable
without crowding the top bar.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M12-01 | S | `DONE` | Open mobile on the map, add a synchronized region selector to the top bar, and compact the mobile language selector. | Frontend lint/build passed; Playwright at 320, 375, 414, 768, and 1280px found map-first loading, no overflow/overlay/console errors, synchronized region state, and a correctly bounded desktop detail panel; independent review passed. |

## M13. Mobile Map Loading Context

Goal: start mobile users in Vancouver with useful region counts and make map
viewport loading visible without showing stale results.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M13-01 | S | `DONE` | Show localized counts in the mobile region selector, open on Vancouver, and display a request-safe loading status while map pins refresh. | Frontend lint/build and diff check passed; Playwright verified Vancouver zoom 10, localized counts at 320–1280px with no overflow, visible non-blocking loading with existing pins retained, latest-response-wins for delayed/overlapping requests, loader settlement after fetch and map errors, and independent remediation revalidation passed. |

## M14. Vercel Deployment

Goal: publish the verified application through the linked Vercel project and
record any external configuration still required for a functional production release.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M14-01 | S | `DONE` | Link the Vercel project, update the Services configuration, deploy production, and verify its public health. | Production deployment `dpl_7XD5mpS3wos2JDZG2fKFuY2tku4g` is READY at `jobsearch-lake.vercel.app`; home, crawler health, city counts, viewport, and nearby endpoints return 200 through the Supabase Transaction Pooler, while an unauthenticated cron request returns 401. |
| M14-02 | S | `DONE` | Apply and secure the production Supabase schema for server-only JobMap access. | All 13 migrations applied; RLS and effective Data API denial verified for both API roles, FK advisor findings cleared, frontend/crawler checks passed, and independent review returned PASS at `d1f9e7b`. |

## M15. Production Crawl Recovery

Goal: recover production ingestion after source-side markup and network behavior
prevented the initial scheduled crawl from producing public map jobs.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M15-01 | S | `DONE` | Accept current top-level Our Vancouver title markup and JavaScript-injected body fallback without weakening quality checks. | All 52 crawler tests and compile check pass; a representative live detail parses with its original publication time; independent review and remediation revalidation passed. Production deployment `dpl_Aj38GP1QPQFYNyKZDDhGT6a3X5GG` replayed after removing 100 false skip markers: the 14-day store contains 17 raw sources and 16 representatives, one verified repost pair was merged, all 16 representatives have four-language titles, and the public Vancouver APIs expose 15 map-eligible jobs with actual source dates. JPCanada was re-enabled after its upstream listing continued to time out. |

## M16. Local Production Crawl and Source Localization

Goal: run production ingestion from the owner's Mac every six hours so the
local Codex Bridge can curate and translate new jobs, while showing source-site
names in the selected public language.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M16-01 | M | `DONE` | Add and install a six-hour macOS production crawler, disable the duplicate Vercel cron, backfill missing titles locally, and localize public source labels. | SearchingJob DB password was reset and synchronized to Keychain plus Vercel Production/Preview without committing it. Production deployment `dpl_EAP9ndujEVCiMU6kG7NW5LAAQJBH` serves the custom domain; home, city counts, viewport, and nearby return 200 while unauthenticated crawler access returns 401. The Library LaunchAgent reports a 21600-second interval and its first completed replay exited 0: Our Vancouver, Vanchosun, and Jinzai Canada succeeded, JPCanada was isolated as a remote-source failure, 8 new source rows were stored, 40 jobs are publicly visible, and all 41 titled representatives have four-language translations. The 56 crawler tests, Python compile check, installer dry run and active-run guard, frontend lint/build, shell syntax, and diff checks pass. Independent review found no Critical/High/Medium defects; two actionable Low findings were fixed and focused revalidation passed. |

## M17. Canadian Community Source Expansion

Goal: extend Korean, Japanese, and Chinese community-job coverage using only
sources whose public delivery and access rules support responsible ingestion.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M17-01 | M | `DONE` | Research Canadian Korean, Japanese, and Chinese job sources; add a rate-limited Sinojobs RSS/JobPosting adapter; and document sources excluded by anti-crawling terms. | 61 crawler tests and Python compile pass; frontend lint/build and diff checks pass; the idempotent local migration registers Sinojobs enabled; a bounded live run discovered IDs 2812/2810/2808 and parsed current Vancouver metadata. The adapter enforces the published 20-second delay after successful and failed responses, retries unseen recent failures, rejects expired/outside-Canada/ambiguous `CA` locations, and does not persist description/contact data. Independent review findings were remediated and final focused revalidation passed. |

## M18. Map Location Accuracy

Goal: prevent broad city or neighborhood fallback points from appearing as exact
workplace markers and revalidate clustered production rows against current source
content plus AI-assisted extraction.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M18-01 | M | `DONE` | Fix AI location precedence, require a geocodable precise address or business for public map confidence, and reprocess the nine-job Downtown Vancouver cluster. | 75 crawler tests, Python compile, frontend lint/build, and independent revalidation pass. Vercel production `dpl_5NMXdKDmhcUgEydVSu1NenD5uVpC` is READY; home/crawler health return 200 and unauthenticated cron returns 401. Production DB/API report zero jobs at both invalid centroids; Playwright finds no 9- or 6-job cluster and zero console errors. The six-hour LaunchAgent runtime matches source, writes with `transaction_read_only=off`, and completed runs 35-38 with exit code 0. |

## M19. Vercel Web Analytics

Goal: collect privacy-friendly production pageviews in the linked Vercel project
without adding advertising cookies or exposing application secrets.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M19-01 | S | `DONE` | Enable Vercel Web Analytics for the linked project and mount the Next.js App Router analytics component in the root layout. | Frontend lint/build and independent review passed. Preview `dpl_HdwcyhnvsxnT9b4dHcCtZuGvGYAF` and production `dpl_JGzBSxChFJ8u9EfwC6EfVNiNjZh7` are READY. Vercel reports analytics enabled; the production analytics script, home, crawler health, and viewport API return 200 while unauthenticated cron returns 401. Playwright observed the `@vercel/analytics/next` 2.0.1 script loading with status 200, a queued pageview, and zero console errors; Vercel reported no runtime errors in the post-deploy window. |

## M20. Compact Language Selector

Goal: reduce header width while keeping all four locales discoverable and accessible.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M20-01 | S | `DONE` | Show the active locale as a circular vector flag and expose country plus language names in the native dropdown. | Frontend lint/build passed. Playwright verified a 44×44px selector, all four country/language option names, keyboard focus and type-to-select, saved locale/cookie behavior, no horizontal overflow at 375/768/1440px, and zero browser console errors. |
| M20-02 | S | `DONE` | Replace the provisional flag drawings with production flag assets and show a flag beside every dropdown option. | Frontend lint/build passed. Playwright verified four in-menu flag icons, a 44×44px trigger, arrow/Enter/Escape keyboard behavior with focus restoration, locale cookie/localStorage persistence after reload, reduced-motion handling, no overflow at 375/768/1440px, and zero console errors. |

## M21. Compact Mobile Search

Goal: expose more job results above the fold on mobile without shrinking search touch targets.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M21-01 | S | `DONE` | Reduce mobile-only intro/search spacing and remove the empty reserved error row while retaining accessible labels and feedback. | Frontend lint/build passed. Playwright verified the combined mobile intro/search height fell from about 294px to 160px at 375px, input and button stayed 44px high, error feedback remained visible when populated, no overflow at 320/375/667-landscape/768px or enlarged text, and zero browser console errors. |
| M21-02 | S | `DONE` | Independently review the compact mobile search checkpoint, deploy it to preview, verify the public surface, and promote the validated artifact to production. | Independent review found no Critical/High/Medium issues (one non-blocking Low note; reviewer sandbox could not rerun commands), while Codex lint/build passed. Preview `dpl_CGtfuokhYWwXmoNwZVWYcjzL7f4Z` reached Ready and returned 200 for the home, crawler health, city counts, viewport, and nearby routes while unauthenticated crawl returned 401. Production `dpl_CmNd9jdsoBthRSeGD6Z2pVfbUEcn` reached Ready at `https://jobmap.narulabs.ca`; the same HTTP checks passed, Web Analytics returned 200, 375×812 Playwright measured 68px intro + 92px search sections with 44px controls and no horizontal overflow, verified all four country/language flags, and reported zero console or post-deployment runtime errors. |

## M22. Mobile List Detail Visibility

Goal: keep the mobile list focused on scanning job cards without covering it with the selected-job detail panel.

| ID | Size | Status | Task | Verification |
| --- | --- | --- | --- | --- |
| M22-01 | S | `DONE` | Render the selected-job detail only in map view while preserving desktop detail behavior and selected-job map context. | Frontend lint/build passed. Playwright verified that a selected job remains highlighted while its detail is hidden from the visual and accessibility trees at 375×812 and 667×375, detail returns in map view, desktop detail remains visible at 1024×768, no horizontal overflow occurs, and browser console errors remain at zero. |

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
