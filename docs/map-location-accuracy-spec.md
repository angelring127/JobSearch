# Map Location Accuracy Remediation Spec

## Purpose

Stop unrelated job postings from sharing a broad Downtown Vancouver centroid and
repair the affected production records with source-grounded, AI-assisted location
extraction.

## Scope

- Re-evaluate the nine representative jobs shown at `49.283393, -123.1174563`
  and every raw source row attached to those representatives.
- Keep Codex Bridge analysis for ambiguous Our Vancouver job/location text.
- Prefer an exact source address or a narrowly verified named-business address.
- Prevent AI-selected North Vancouver or other location evidence from being
  overwritten by an unrelated `downtown` word elsewhere in the post.
- Treat city-only and neighborhood-only locations as list context, not exact map
  points, by keeping them below the public `confidence >= 0.6` threshold.
- Do not fall back to a city or neighborhood centroid when exact business
  geocoding fails.
- Make crawler database transactions explicitly read-write when using a pooled
  Supabase connection.
- Reprocess the affected production rows, update the installed six-hour macOS
  crawler runtime, and deploy the verified code to Vercel production.

## Exclusions

- Do not invent addresses from model knowledge.
- Do not persist job descriptions, contact details, or personal data.
- Do not add a general web-search crawler or follow arbitrary outbound links.
- Do not show broad neighborhood centroids as workplace addresses.
- Do not change frontend API response shapes, public confidence threshold, map
  layout, dedupe policy, or retention window.
- Do not modify unrelated dirty or untracked workspace files.

## Required Scenarios

1. K-Well Downtown resolves to its verified 889 W Pender Street location, while
   a K-Well Langley post cannot reuse that Downtown address without Downtown
   context.
2. Akihana Sushi postings resolve to 1205 Davie Street.
3. the VANMAK Downtown posting resolves to 82 Keefer Place, including when the
   business name appears as Korean `밴막`.
4. the source-grounded `808 Bute Street` result remains a precise visible pin.
5. NinNin Ramen resolves from its named business to 660 Abbott Street even when
   the source's location field only says Downtown.
6. the North Vancouver/Lonsdale post retains the AI-selected North Vancouver
   context but has no public pin without a precise workplace.
7. deleted source posts have no public pin.
8. an unknown named business that fails geocoding receives no city-center
   fallback.
9. the original nine-job Downtown centroid cluster returns zero public jobs after
   remediation; legitimate same-address jobs may still cluster at the verified
   employer address.

## Edge Cases

- AI analysis is unavailable or returns malformed data: fail closed unless a
  deterministic, source-grounded precise location exists.
- A named business has multiple locations: require narrow location context before
  applying a verified address.
- A pooled database backend has a stale read-only session default: crawler writes
  must start as read-write transactions.
- A source has been deleted since ingestion: lower its coordinates/confidence
  rather than manufacturing an address.

## Completion Criteria

- Crawler unit suite, Python compile, frontend lint/build, and `git diff --check`
  pass.
- Production DB has no visible representative at the old Downtown centroid and
  the repaired target rows match the decisions above.
- Public viewport/nearby APIs remain compatible and expose the corrected visible
  coordinates only.
- A real production browser shows no nine-job centroid cluster and no console or
  page errors.
- The installed macOS runtime contains the location-resolution fix and its next
  scheduler transaction is read-write.
- Independent read-only review returns PASS, or every valid finding is remediated
  and revalidated before production deployment.

## Test Method

- `PYTHONPATH=crawler:crawler/src crawler/.venv/bin/python -m unittest discover -s crawler/tests -p 'test_*.py'`
- `crawler/.venv/bin/python -m compileall -q crawler/api.py crawler/src crawler/tests`
- `cd frontend && npm run lint && npm run build`
- Read-only SQL checks for target source rows, representative coordinates,
  confidence, geometry, and duplicate-coordinate groups.
- Public production API requests for Vancouver viewport/nearby data.
- Playwright CLI snapshot/screenshot and console-error check on the production map.
