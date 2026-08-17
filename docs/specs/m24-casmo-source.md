# M24 Casmo Community Source

## Purpose

Add the public Casmo (`[캐스모] 캐나다 한국인 스토리 모임`) job-board
listing as a conservative Korean Canadian source without creating duplicate map
jobs when the same employer also posts on Our Vancouver or another source.

## Scope

- Register a new `casmo` crawler source and localized public source label.
- Read only the anonymous public listing and Daum public pagination API for
  board `8cBB` in cafe `skc67` (`grpid=7rX`).
- Scan a bounded newest window every six hours with the existing Daum request
  interval and seen-item retry model.
- Store only public listing metadata needed by JobMap: item ID, source URL,
  title, source-derived posting time, category, grounded location fields, and
  wages present in the title.
- Accept only employer-side hiring titles with an explicit Canadian city or
  municipality. Reject job-seeker posts, volunteer recruiting, service ads,
  contact-bearing titles, and titles whose geography is ambiguous.
- Use the existing fail-closed local Codex Bridge analysis only to classify the
  public title and resolve a title-grounded business or location query. A bridge
  failure must remain retryable rather than becoming a permanent skip.
- Reuse the existing representative-job duplicate scoring. Preserve separate
  `job_sources` rows while automatically merging only high-confidence matches;
  keep lower-confidence overlaps as admin duplicate candidates.
- Keep the source on the macOS six-hour crawler. Do not add Vercel Cron.

## Exclusions

- Do not log in to Daum, reuse browser cookies, bypass the cafe membership
  requirement, or crawl member-only article bodies.
- Do not persist descriptions, phone numbers, email addresses, writer names, or
  other contact/profile data.
- Do not infer a city from a generic term such as `다운타운`, `미드타운`, or a
  business name alone when the public title does not identify Canadian
  geography.
- Do not run a production crawl, apply the production migration, deploy Vercel,
  or update the installed macOS runtime in this implementation checkpoint.
- Do not weaken the existing duplicate auto-merge threshold.

## Scenarios

1. A public listing title marked `구인` (or with explicit hiring intent) and
   naming `노스욕` is eligible for title-only analysis.
2. A `구직` title, volunteer post, dental/immigration/service advertisement, or
   title containing a phone/email address is rejected before AI analysis.
3. A hiring title with no explicit Canadian municipality is rejected even when
   it contains a recognizable employer name.
4. If the Codex Bridge is unavailable or returns an invalid result, the item is
   recorded as a crawl failure and remains unseen so a later run retries it.
5. Two substantive titles from Casmo and Our Vancouver at the same precise
   location may auto-merge; generic or different-role titles must remain
   separate.
6. Pagination is bounded. An empty or malformed public page fails closed without
   advancing seen-item state for unprocessed jobs.

## Completion Criteria

- `CasmoAdapter` is registered and uses only anonymous public listing requests.
- The adapter never requests a member-only article-detail URL while ingesting.
- The newest-window page and per-run item bounds are explicit and tested.
- Location/title filtering and transient-analysis retry behavior are tested.
- Source registration is an idempotent migration created through Supabase CLI.
- Korean, English, Japanese, and Simplified Chinese source labels are present.
- Cross-source duplicate tests cover both a high-confidence merge and a
  non-merge for generic/different-role posts.
- Crawler tests, Python compilation, frontend lint/build, and `git diff --check`
  pass.
- A bounded live read confirms the public listing/API shape without writing to
  Supabase or crawling member-only content.
- Independent checkpoint review passes before the task is marked `DONE`.

## Test Method

- Mock the Daum listing and pagination API with `httpx.MockTransport`.
- Unit-test listing parsing, eligibility, posting-time parsing, page bounds,
  no-detail-fetch behavior, and analyzer failure retry semantics.
- Run the full crawler unit-test suite and Python compilation.
- Run frontend lint and production build for localized source labels.
- Perform a read-only live listing/API sample and a read-only database check.
- Validate the checkpoint range and dispatch a read-only Claude review through
  the repository implementation-review workflow.
