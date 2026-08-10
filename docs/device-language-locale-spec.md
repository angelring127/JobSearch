# Device Language Locale Selection

## Purpose

Show the public JobMap UI in the visitor's supported device or browser language on first visit while preserving an explicit language choice across later visits.

## Scope

- Support Korean (`ko`), English (`en`), Japanese (`ja`), and Simplified Chinese (`zh`).
- Resolve the initial locale from the request `Accept-Language` header.
- Respect quality weights in `Accept-Language`.
- Use English when no requested language is supported.
- Prefer a previously saved explicit locale over automatic detection.
- Apply the resolved locale to visible UI copy, dynamic job titles, `<html lang>`, page title, and metadata description.
- Preserve the existing language selector and store explicit choices in local storage and a same-site locale cookie.

## Exclusions

- Adding new supported languages.
- Translating source content beyond the existing stored title translations and fallbacks.
- Changing public API response shapes, crawler behavior, database schema, or admin localization.
- Deploying a duplicate crawler schedule.

## User Scenarios

1. A first-time Korean, English, Japanese, or Chinese visitor sees the matching supported locale on the first server-rendered response.
2. A first-time visitor using an unsupported language sees English.
3. A visitor manually selects a supported language and continues to see it after reload.
4. A saved explicit language overrides a different current device language.

## Edge Cases

- Region-specific tags such as `en-US`, `ko-KR`, `ja-JP`, and `zh-TW` map to their supported base language.
- Multiple languages honor quality weights and original order for equal weights.
- Wildcards, zero-quality entries, malformed quality values, and empty headers do not produce an unsupported locale.
- Invalid locale cookie values are ignored.

## Completion Criteria

- The first rendered HTML, visible heading, metadata title, and `<html lang>` agree for all four supported languages.
- Unsupported languages fall back to English.
- A valid saved locale takes priority over the request language.
- Manual selection updates the current UI and survives a full reload.
- Frontend lint and production build pass.
- Real-browser validation reports no console errors in the selection and reload flow.

## Test Method

- Run `npm run lint` and `npm run build` in `frontend/`.
- Send requests with representative `Accept-Language` headers and inspect `<html lang>`, `<title>`, and the first heading.
- Test an unsupported language, weighted language order, and a saved locale cookie.
- Use a real browser to change the language, reload, and verify visible copy, document language, title, local storage, cookie, and console errors.
