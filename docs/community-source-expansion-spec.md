# Community Source Expansion SPEC

## Goal

Expand JobMap's Canadian community-job coverage without bypassing source rules
or weakening the map's location-quality threshold.

The repository already supports two Korean community sources (Our Vancouver and
Vancouver Chosun) and two Japanese sources (JPCanada and Jinzai Canada). This
checkpoint adds one Chinese-community source: Sinojobs Canada.

## Source Decision

| Source | Language/community | Decision | Reason |
| --- | --- | --- | --- |
| Our Vancouver | Korean | Existing adapter | Active community job board. |
| Vancouver Chosun | Korean | Existing adapter | Active community job board. |
| JPCanada | Japanese | Existing adapter | Active Canadian Japanese job board. |
| Jinzai Canada | Japanese | Existing adapter | Active Canadian Japanese recruitment board. |
| Sinojobs Canada | Chinese/Asian | Add adapter | Official public RSS feed and public JobPosting metadata are available; robots.txt requires a 20-second crawl delay. |
| 51.ca | Chinese | Exclude | Its legal notice explicitly prohibits crawlers, scraping, automated access, and building aggregators without prior written permission. |
| Vansky | Chinese | Exclude | Its recruitment form warns other sites not to copy postings; do not ingest without written permission. |

## Scope and Completion Criteria

1. Register `sinojobs` as a crawler source and expose a source label in Korean,
   English, Japanese, and Simplified Chinese.
2. Discover current listings only through Sinojobs' official public RSS feed.
3. Fetch public job-detail pages only to read the published `JobPosting`
   metadata needed by JobMap: title, source URL, publication date, expiry date,
   location, wage, and category.
4. Enforce at least 20 seconds between requests to the Sinojobs host, including
   the RSS-to-first-detail transition.
5. Reject expired listings, listings outside Canada, and listings without a
   recognized Canadian city or region. Do not fall back to a Canada-wide map
   point.
6. Do not persist or return descriptions, phone numbers, email addresses,
   social handles, application data, or other contact details. Description text
   may be inspected transiently only to classify the role and parse an hourly
   wage.
7. Preserve source isolation: a Sinojobs failure must not stop other sources.
   Current-list refreshes remain idempotent through the existing source URL and
   external ID upsert behavior.
8. Keep the existing public `confidence >= 0.6` visibility threshold unchanged.

## Test Method

- Unit-test RSS ID extraction, duplicate handling, monotonic cursor behavior,
  JobPosting parsing, Canadian-location acceptance, outside-Canada rejection,
  expiry rejection, and the adapter request interval.
- Run all crawler unit tests and a Python compile/import check.
- Perform a bounded live check against the official RSS feed and one current
  detail page; do not run an unbounded or production database crawl as part of
  validation.
- Run frontend lint and build after adding the localized source label.
- Run `git diff --check` and validate the checkpoint base/head range before
  independent review.

## Source References

- Sinojobs English jobs: <https://en.sinojobs.ca/jobs/>
- Sinojobs job RSS: <https://en.sinojobs.ca/feed/?post_type=job_listing>
- Sinojobs robots policy: <https://en.sinojobs.ca/robots.txt>
- 51.ca legal notice: <https://about.51.ca/legal.html>
- Vansky recruitment form: <https://www.vansky.com/info/ba_job.php>
