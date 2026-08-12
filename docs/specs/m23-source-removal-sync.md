# M23 Source Removal Sync

## Purpose

Remove recently crawled Our Vancouver postings from the public JobMap when the
source has definitively deleted them, without re-fetching every stored posting
or treating temporary source failures as deletion.

## Scope

- Compare the completed 14-day Our Vancouver listing scan with recent stored
  `job_sources` IDs.
- Recheck only stored IDs missing from the current listing.
- Treat HTTP 404/410 and explicit Daum missing/deleted-post pages as removed.
- Preserve records for 403, 429, other unexpected HTTP responses, empty
  responses, timeouts, and request failures.
- Use the existing transactional source deletion/reconciliation path after a
  removal is confirmed.
- Record bounded removal-check counts in the crawl summary.
- Stop removal checks for a run when more than ten recent stored IDs are absent
  from the listing, preventing a malformed or incomplete listing from causing
  a mass deletion.

## Exclusions

- No AI classification or translation calls.
- No full re-fetch of every stored posting on each scheduled crawl.
- No database schema, RLS, retention-window, scheduler, or frontend changes.
- No deletion synchronization for sources other than Our Vancouver.
- No production deployment or production crawl in this checkpoint.

## Scenarios

1. A stored recent ID remains in the current listing: no availability request
   is made.
2. A stored recent ID is absent and its detail endpoint returns 404 or 410: its
   source row is removed and the representative job is deleted or reconciled.
3. A missing ID returns a normal current article: preserve it.
4. A missing ID returns 403, 429, 5xx, an empty response, or a request error:
   preserve it and report an unknown check.
5. More than ten recent stored IDs are missing: make no detail checks or
   deletions and report that the safety guard deferred the candidates.
6. An unseen current listing ID is still processed normally after the removal
   check.

## Completion Criteria

- Removal checks run only for adapters that explicitly opt in.
- Existing seen-item selection and 14-day retention behavior remain intact.
- Confirmed removals call the existing transactional deletion/reconciliation
  method exactly once per source item.
- Transient or ambiguous responses never delete data.
- Crawl summaries expose candidate, checked, removed, active, unknown, and
  deferred counts.
- Focused crawler tests, the full crawler test suite, and Python compilation
  pass.

## Test Method

- Unit-test Daum availability classification for active, explicit removed,
  404/410, transient HTTP, and empty-response cases.
- Unit-test crawl integration for confirmed removal, unknown preservation, the
  mass-removal guard, and unchanged new-item processing.
- Run `python -m unittest discover -s tests` from `crawler/` with its virtual
  environment.
- Run Python compilation for `crawler/api.py` and `crawler/src/`.
- Run `git diff --check` and inspect the checkpoint diff before independent
  review.
