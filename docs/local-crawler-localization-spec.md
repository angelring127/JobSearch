# Local Production Crawler and Source Localization Spec

## Purpose

Run the production crawler from the owner's Mac every six hours so the local
Codex Bridge can classify jobs and generate Korean, English, Japanese, and
Simplified Chinese titles before records are served from Supabase. Localize the
fixed source-site labels in the public list and detail views as well.

## Scope

- Add a non-interactive Python entrypoint for one complete enabled-source crawl.
- Add an idempotent macOS LaunchAgent installer with a six-hour interval and
  `RunAtLoad` behavior.
- Read the production `DATABASE_URL` from the owner's unlocked macOS login
  Keychain instead of copying it into the repository or a plaintext config file.
- Prevent overlapping local runs and keep logs under the user's Library logs.
- Remove the Vercel-hosted daily cron configuration to avoid duplicate runs that
  cannot reach the Mac-only Codex Bridge.
- Return `source_key` from both public job APIs and localize known source labels
  in Korean, English, Japanese, and Simplified Chinese.
- Keep the original job title and source hostname as fallbacks when translated
  data or a known source key is unavailable.

## Exclusions

- Starting or supervising the separate Codex Bridge process.
- Running while the Mac is powered off or disconnected from the network.
- Translating arbitrary source descriptions or job bodies in the browser.
- Exposing database or Bridge credentials through browser-visible variables.

## Scenarios

1. Installing the LaunchAgent starts one crawl and schedules subsequent runs at
   six-hour intervals.
2. A second invocation exits without crawling while another run holds the lock.
3. The crawler receives the production database URL from Keychain without
   writing its value to the repository or its logs.
4. Selecting English, Japanese, Chinese, or Korean changes both the job title
   (when the stored translation exists) and the fixed source-site label.
5. Unknown sources retain their supplied display name or hostname.

## Completion Criteria

- Installer validation and a real locally initiated production crawl pass.
- The production crawl writes to Supabase and completes a four-language title
  backfill through the local Bridge.
- Frontend lint and build pass.
- Public viewport and nearby APIs include `source_key` without removing existing
  fields.
- Browser verification confirms localized titles and source labels in all four
  languages on the public production UI.
- An unauthenticated crawler HTTP request remains rejected.

## Test Method

- Python compile and the full crawler test suite.
- Installer dry-run/validation plus `launchctl print` evidence.
- Frontend `npm run lint` and `npm run build`.
- Public API response inspection and Playwright language-switch checks.
- Supabase query for crawl runs and complete title-translation counts.
