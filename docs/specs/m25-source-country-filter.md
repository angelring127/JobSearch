# M25 Source Country Filter and Advanced Location Search

## Purpose

Let users filter Canadian jobs by the country/community of the originating job
site while moving location navigation into the existing progressive-disclosure
filter panel.

## Scope

- Replace the always-visible location-search position with a source-country
  select: all sources, Korean sources, Japanese sources, or Chinese sources.
- On mobile, replace the compact header region select with the same synchronized
  source-country select.
- Move the major-city selector and free-form Canadian location search into the
  detailed filter panel without removing autocomplete, counts, keyboard support,
  or map navigation behavior.
- Map sources conservatively by adapter key:
  - Korea: `ourvancouver`, `casmo`, `vanchosun`
  - Japan: `jpcanada`, `jinzaicanada`
  - China: `sinojobs`
- Filter viewport, nearby, and city-count APIs using parameterized source keys.
- For representative jobs with multiple raw sources, match against every
  `job_sources` row and return a source belonging to the selected country.
- Keep all four UI locales synchronized and accessible.

## Exclusions

- Do not infer employer nationality, worker nationality, visa eligibility, or
  workplace country from a source-country selection.
- Do not split or delete representative jobs or raw source records.
- Do not change crawler source classification or duplicate thresholds.
- Do not deploy or push this UI checkpoint unless the user asks separately.

## Completion Criteria

- The country select is visible where the location controls were previously
  prominent, with a compact synchronized version in the mobile header.
- Location controls are reachable inside detailed filters at 320px through
  desktop widths and retain labels, autocomplete, error feedback, and 44px touch
  targets.
- Selecting Korea, Japan, or China refreshes map jobs and city counts and never
  relies only on a representative job's primary source.
- Invalid `sourceCountry` API values return `400`.
- A merged representative is returned under every matching source-country
  selection with the selected country's source metadata.
- Frontend lint/build, route behavior checks, responsive browser checks, and
  independent checkpoint review pass.

## Test Method

- Exercise route handlers with valid/invalid `sourceCountry` parameters and
  inspect parameterized SQL construction.
- Run `npm run lint` and `npm run build`.
- Use Playwright at 320, 375, 768, 1024, and 1440px to verify the compact header,
  detailed-filter location controls, synchronized country selection, keyboard
  focus, no horizontal overflow, filtered requests, and zero console errors.
- Validate the checkpoint range and dispatch a read-only independent review.
