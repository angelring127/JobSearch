# Vercel Web Analytics Spec

## Purpose

Enable privacy-friendly traffic analytics for the production JobMap site so the
owner can inspect pageviews, visitors, referrers, countries, devices, and browsers
from the linked Vercel project.

## Scope

- Enable Web Analytics for the linked Vercel `jobsearch` project.
- Install the official `@vercel/analytics` package in `frontend`.
- Mount the Next.js App Router `Analytics` component once in the root layout.
- Collect pageviews on the production custom domain and route transitions supported
  by the official Next.js integration.
- Deploy through a verified preview before promoting the same artifact to production.

## Exclusions

- Do not add GA4, advertising pixels, third-party session replay, or user profiling.
- Do not add custom events, user identifiers, job descriptions, contact data, or
  database/internal API values to analytics payloads.
- Do not add browser-exposed credentials or new environment variables.
- Do not change the map, localization, public API response shapes, crawler, database,
  or admin behavior.
- Do not combine unrelated dependency security upgrades with this analytics change.

## Required Scenarios

1. The Vercel project reports Web Analytics enabled.
2. Every localized public rendering mounts one analytics component through the root
   layout without changing the resolved HTML language or metadata.
3. Production serves the Vercel Analytics script from `/_vercel/insights/script.js`.
4. A real production browser loads the public map with no console or page errors and
   issues the analytics script request.
5. Existing public APIs and the protected crawler route keep their existing behavior.

## Edge Cases

- Local development may log or suppress analytics depending on the official package;
  only the Vercel production collection path is completion evidence.
- Analytics dashboard data can take time to appear after the first pageview; script
  delivery and a browser request are the immediate verification signals.
- Ad blockers may suppress analytics for individual visitors and are not an app error.

## Completion Criteria

- `npm run lint`, `npm run build`, and `git diff --check` pass.
- Independent read-only review finds no unremediated material issue.
- Preview and production deployments reach `READY`.
- The production homepage, public API, crawler health, and unauthenticated crawler
  authorization check return their expected status codes.
- The custom production domain serves the analytics script and Playwright observes
  its request with zero console errors.
- The implementation board records the Vercel enablement and deployment evidence.

## Test Method

- `cd frontend && npm run lint`
- `cd frontend && npm run build`
- `git diff --check`
- `vercel project web-analytics jobsearch --json`
- Preview deployment inspection and HTTP checks.
- Production promotion followed by homepage, API, crawler health, and auth checks.
- Playwright snapshot, request inspection, and console-error check on
  `https://jobmap.narulabs.ca`.
