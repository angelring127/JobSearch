# Multi-source crawl and dedupe specification

## Purpose

Populate the public JobMap from active Canadian job boards in addition to Our Vancouver and remove high-confidence duplicate representatives from the public list.

## Scope

- Crawl current listings from Jinzai Canada and Vanchosun through their existing public adapters.
- Keep JPCanada registered, but report source access failures without inventing data when its public host is unavailable.
- Treat Vanchosun as a refresh-style board because older post IDs can be bumped back to the top of the current listing.
- Improve duplicate title comparison for Korean, English, Japanese, and Chinese text.
- Automatically merge only high-confidence duplicates, including same-source reposts, while preserving every raw `job_sources` row and merge history.
- Reconcile high-confidence duplicates after enabled source crawls.
- Expose the verified local frontend through a temporary Cloudflare Quick Tunnel.

## Exclusions

- Do not scrape private, login-only, or blocked pages through circumvention.
- Do not delete raw source records solely because they are duplicates.
- Do not auto-merge ambiguous candidates below the conservative threshold.
- Do not create a permanent Cloudflare DNS record or production deployment.

## User scenarios

1. A user opens JobMap and sees current jobs from Our Vancouver, Jinzai Canada, and Vanchosun with the originating site name.
2. Two sites publish the same job, or one site reposts the same job, and the public list shows one representative job.
3. An inaccessible source fails independently without preventing other enabled sources from completing.
4. A user opens the temporary Cloudflare URL and reaches the same local JobMap UI.

## Completion criteria

- Live Jinzai Canada and Vanchosun crawl runs create or update source rows from their current public listings.
- Vanchosun refresh processing follows current listing order instead of relying only on a monotonically increasing post ID.
- Unicode job titles participate in duplicate scoring.
- High-confidence duplicates merge to one representative while raw source rows and merge history remain intact.
- Ambiguous pairs remain separate or become review candidates.
- Python tests and compile checks pass; frontend lint/build and public API checks pass.
- Database integrity checks show no orphaned source links and correct representative source counts.
- A browser check through the temporary Cloudflare URL loads meaningful content without an error overlay.

## Edge cases

- Bumped Vanchosun posts can have an older ID than newer posts.
- Missing wage or coordinates must not independently make two jobs duplicates.
- Generic recruitment words such as `구인`, `모집`, and `hiring` must not dominate title similarity.
- Cross-source or same-source records with different roles at the same business must remain separate unless the total score reaches the conservative auto-merge threshold.
- A source timeout is recorded as a source failure and does not trigger retries that bypass access controls.

## Test method

- Unit tests for source ordering, Unicode title similarity, conservative duplicate scoring, and reconciliation behavior.
- Full crawler test suite and Python compile check.
- Controlled live crawl batches for Jinzai Canada and Vanchosun.
- SQL checks for source counts, duplicate representatives, merge history, and orphaned rows.
- Frontend lint/build, viewport API response inspection, and real-browser verification.
