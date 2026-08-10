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
- Install the executable crawler runtime under
  `~/Library/Application Support/JobMap/runtime` so a background LaunchAgent does
  not require Full Disk Access to the source checkout under `Documents`.
- Read the local Codex Bridge base URL and API key from the owner's login
  Keychain at runtime; the installer may seed those Keychain items from the
  existing server-only local environment without logging their values.
- Prevent overlapping local runs and keep logs under the user's Library logs.
- Refuse to replace or unload the installed runtime while a production crawl
  owns the scheduler lock, preventing interrupted runs from being left open.
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
4. The installer tests the stored database URL before loading the LaunchAgent
   and, when its Pooler credentials are stale, requests the current database
   password as hidden input and safely URL-encodes it before updating Keychain.
5. The LaunchAgent runs from the installed Library runtime even when macOS
   denies background access to the source checkout under `Documents`.
6. Rerunning the installer during an active crawl exits without unloading the
   LaunchAgent or replacing its runtime.
7. Selecting English, Japanese, Chinese, or Korean changes both the job title
   (when the stored translation exists) and the fixed source-site label.
8. Unknown sources retain their supplied display name or hostname.

## Completion Criteria

- Installer validation and a real locally initiated production crawl pass.
- `launchctl print` reports a 21600-second interval and the installed runtime
  path, with no `Operation not permitted` error from the source checkout.
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
