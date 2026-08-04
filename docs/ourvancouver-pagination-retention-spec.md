# Our Vancouver Pagination and Two-Week Window SPEC

## Purpose

Keep the Our Vancouver feed complete enough for daily operation without crawling
the board's full historical archive. The crawler must discover current postings
through Daum's mobile pagination, process new posts first, and retain public job
records for 14 days.

## Scope

- Read the first Daum mobile listing page and subsequent
  `/api/v1/common-articles` pages.
- Treat the Daum Cafe calendar in `Asia/Seoul` as the listing-date boundary.
- Discover postings published within the inclusive 14-day listing window.
- Continue through the recent listing window even after crossing the current
  high-water mark, then stop after two consecutive fully expired pages. This lets
  an installation repair page-1-era gaps below its existing high-water mark.
- Persist a lightweight seen-item record for successfully stored and intentionally
  skipped posts so a 14-day backlog can be drained across bounded crawl runs
  without repeatedly fetching the same rejected posts.
- Prioritize unseen IDs newer than the high-water mark, then use remaining batch
  capacity for unseen 14-day backlog IDs.
- Keep the existing scheduled cleanup that removes `job_sources` older than 14
  days and reconciles representative `jobs`.
- Use a source-specific default Our Vancouver batch size while preserving an
  explicit manual-run batch override.

## Exclusions

- Do not crawl posts older than the 14-day window.
- Do not expose locationless or low-confidence posts on the public map.
- Do not change frontend API response shapes, dedupe thresholds, or the legacy
  `backend/` service.
- Do not run the entire 14-day backlog in one unbounded request.

## User Scenarios

1. A scheduled crawl finds more than one listing page of new Our Vancouver posts
   and does not miss posts that moved to page 2 before the crawl ran.
2. An existing installation with a page-1-only high-water mark gradually fills
   missing recent posts without hiding newly published posts behind the backlog.
3. A rejected advertisement or locationless post is recorded as seen and is not
   retried on every scheduled run.
4. A transient detail-fetch failure remains eligible for a later retry.
5. Posts older than 14 days are neither added from the listing backlog nor kept
   in the public database.

## Completion Criteria

- Pagination requests use `grpid`, `fldid`, `targetPage`, `afterBbsDepth`, and
  `pageSize` from the observed Daum contract.
- A zero or advanced checkpoint can discover unseen recent backlog items below
  the checkpoint, while two consecutive fully expired pages stop historical
  scanning.
- Stored and intentionally skipped items are excluded from later backlog batches;
  failed items are not marked seen.
- New IDs are selected before backlog IDs and no selected batch exceeds its limit.
- The default public retention remains exactly 14 days.
- Existing adapters and public API response shapes remain compatible.

## Edge Cases

- Duplicate IDs across pages are returned once.
- Missing or malformed pagination metadata fails with a bounded source error
  instead of looping indefinitely.
- Relative time labels such as minutes or `HH:MM` are treated as current; exact
  `YY.MM.DD` labels are compared to the Seoul 14-day cutoff.
- A deleted checkpoint does not prevent recent unseen backlog discovery.
- Pagination has a hard page ceiling and reports an error if neither checkpoint
  nor retention boundary is reached.

## Test Method

- Unit-test first-page parsing, page-2 pagination, checkpoint crossing, 14-day
  cutoff, duplicate IDs, and malformed pagination responses with mocked HTTP.
- Unit-test new-before-backlog selection, seen-item filtering, skipped marking,
  and failure retry behavior in `run_source_crawl`.
- Apply the new migration to local Docker PostGIS and verify constraints/indexes.
- Run all crawler tests and a Python compile/import check.
- Run frontend lint/build and public viewport/nearby response checks because the
  crawler writes feed data consumed by the Next.js routes.
- Run a bounded live Our Vancouver listing discovery and one controlled crawl
  batch, then verify database linkage and the 14-day public boundary.
