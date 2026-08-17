# M25 Source Country Filter and Advanced Location Search

## Purpose

Let users filter Canadian jobs by the country/community of the originating job
site while moving location navigation into the existing progressive-disclosure
filter panel.

## Scope

- Keep the major-city shortcut in its existing desktop and compact mobile
  positions.
- Replace only the free-form location-search position with a source-country
  select: all sources, Korean sources, Japanese sources, or Chinese sources.
- Move the free-form Canadian location search into the detailed filter panel
  without removing autocomplete, keyboard support, or map navigation behavior.
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

- The major-city shortcut remains in its prior desktop and compact mobile
  positions, while the country select occupies the former free-form location
  search position.
- Free-form location search is reachable inside detailed filters at 320px
  through desktop widths and retains labels, autocomplete, error feedback, and
  44px touch targets.
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
