# Public Localization SPEC

## Purpose

Make the public JobMap experience readable in Korean, English, Japanese, and Simplified Chinese, including arbitrary job-posting titles, and make each listing's posting date visible.

## Scope

- Add a public language selector for `ko`, `en`, `ja`, and `zh`.
- Persist the selected language in the browser and update the document language.
- Translate all public map/search/filter/list/detail interface copy.
- Display an exact localized posting date on every job card. If a source does not expose its posting date, display the database's first-seen date with a distinct localized label; use an unavailable label only when neither date exists.
- Store crawler-generated title translations in PostgreSQL and return them through the existing public job APIs.
- Use the configured server-only Codex Bridge in bounded batches; never expose its credentials to the browser.
- Fall back to the original title when a translation has not been generated or translation is unavailable.

## Exclusions

- Admin UI localization.
- Translation of source-page body content.
- Translation of employer names, addresses, or source URLs.
- A new client-visible translation service or browser-exposed credential.

## User Scenarios

1. A user changes the language and immediately sees all public interface labels and available job-title translations in that language.
2. Refreshing the page keeps the user's selected language.
3. Every job card shows a localized posting date, a clearly labeled first-seen fallback, or an explicit date-unavailable label.
4. A title that has not been translated still appears using its original source text.
5. Map markers and the selected-job detail use the same localized title as the list.

## Completion Criteria

- The four language choices are keyboard accessible and usable at 375px and desktop widths.
- `html[lang]`, document title, visible labels, accessible names, errors, categories, numbers, and dates follow the selected language.
- `GET /api/jobs/viewport` and `GET /api/jobs/nearby` preserve their existing shape and add `title_translations` as an optional object.
- Missing or failed translations do not block crawling, hide a job, or produce an empty title.
- Translation credentials stay server-only.
- Frontend lint/build, Python tests/compile, database migration, API checks, and browser checks pass.

## Edge Cases

- Null, invalid, or timezone-less posting dates.
- Missing title, partial translation objects, and malformed model output.
- Codex Bridge absent, slow, or unavailable.
- Long CJK titles and narrow screens.
- Existing rows created before the localization migration.

## Test Method

- Unit-test translation response validation and failure fallback.
- Apply the migration to local PostGIS and inspect the new JSONB column.
- Run `npm run lint`, `npm run build`, Python tests, and Python compile/import checks.
- Check both public APIs for backward-compatible fields and `title_translations`.
- Exercise language selection, persistence, list dates, translated titles, map marker labels, and detail content in a real browser at desktop and 375px widths.
