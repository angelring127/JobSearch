# Production Crawl Recovery SPEC

## Purpose

Restore production ingestion for current Our Vancouver detail pages after the
source moved `span.article_title` outside the legacy `bbs_read_tit` wrapper and
started injecting the body with JavaScript while retaining it in Open Graph
metadata.

## Scope

- Accept the current top-level `span.article_title` detail-page markup.
- Fall back to `og:description` when the content container is present but empty
  before client-side JavaScript runs.
- Preserve the existing legacy title selectors and content requirement.
- Add a regression test using the current title/content structure.
- Deploy the verified parser and replay only Our Vancouver items incorrectly
  recorded as skipped by the broken parser.
- Re-run bounded production crawling and verify stored and visible job counts.

## Exclusions

- Do not weaken the job-intent, location, retention, or duplicate quality gates.
- Do not fabricate locations or publication dates.
- Do not delete job rows or reset seen records for other sources.
- Do not treat the upstream JPCanada timeout as a parser defect.

## Scenarios

1. A legacy detail page with `article_title` inside `bbs_read_tit` still parses.
2. A current detail page with a top-level `span.article_title`, an empty
   `tx-content-container`, and `og:description` parses the title, content, and
   source publication time.
3. A page missing either title or content is still rejected.
4. Replayed current posts still pass the existing quality and map-location gates
   before they become visible.

## Completion Criteria

- The parser regression test passes with both legacy and current markup.
- A representative live Our Vancouver page parses locally.
- The crawler unit suite and Python compile check pass.
- Independent review returns PASS or all valid findings are remediated.
- Only Our Vancouver skipped seen markers from the failed production run are
  removed before replay.
- Production crawl runs finish with auditable source summaries and public APIs
  return the resulting eligible jobs.

## Edge Cases

- The broad `.article_title` selector and metadata fallback must remain scoped
  to a detail document that also contains the required content container.
- Source posts without grounded map locations remain stored or rejected
  according to the existing quality policy; no city-center coordinates are added.
- Client or Vercel timeouts must not be interpreted as a rollback of already
  committed database rows.

## Test Method

- Run `python -m unittest tests.test_source_parsers` and the full crawler suite.
- Run a live read-only parse against one current Our Vancouver detail page.
- Run `python -m compileall -q api.py src tests` and `git diff --check`.
- Validate the checkpoint range and dispatch a read-only Claude review.
- Query Supabase before and after the targeted seen-item replay and crawl.
- Verify `/api/jobs/city-counts` and a Vancouver viewport response in production.
