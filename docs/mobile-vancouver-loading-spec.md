# Mobile Vancouver Loading SPEC

## Purpose

Make the mobile map useful immediately by opening on Vancouver, showing the
available job count in the compact region selector, and making asynchronous map
updates visible while the user waits for pins.

## Scope

- Show the localized city job count beside every option in the mobile header
  region selector once the existing aggregate count request completes.
- Open the public page with Vancouver selected and the map centered at the
  existing Vancouver preset and zoom level.
- Show a localized, non-blocking loading status from the start of a map move
  until the newest viewport request settles.
- Keep existing pins visible while the next viewport is loading, then replace
  them with the newest successful response.
- Prevent an older or cancelled viewport request from replacing newer jobs or
  dismissing the newest loading state.
- Preserve existing search, filter, current-location, localization, and public
  API response behavior.

## Exclusions

- No crawler, database, dedupe, or retention changes.
- No redesign of the map, header, desktop selector, or job detail panel.
- No new external loading or animation dependency.

## User Scenarios

1. A phone user opens JobMap and sees Vancouver selected with the map centered
   on Vancouver.
2. After city counts load, the phone user opens the region selector and sees a
   localized count beside each region.
3. The user pans, zooms, selects a preset, chooses a search result, or requests
   current location. A loading status appears while the destination viewport is
   moving or its jobs are loading and disappears when the newest request ends.
4. Slow or overlapping viewport requests do not show stale pins and do not
   leave the loading status stuck.

## Completion Criteria

- The initial selected region is `vancouver` and the initial viewport request
  bounds contain the Vancouver preset center at zoom 10.
- Mobile region options use the same localized count format as the desktop
  quick selector.
- A visible `role="status"` loading indicator appears during delayed viewport
  loading, and settles after success, failure, or cancellation.
- Only the newest viewport response updates jobs and markers.
- The page has no horizontal overflow at 320, 375, 414, or 768 CSS pixels.
- `npm run lint`, `npm run build`, `git diff --check`, and the relevant browser
  scenarios pass without page errors or console errors.

## Test Method

- Run frontend lint and production build.
- Verify the initial region, option text, map request bounds, and marker results
  in a real browser.
- Delay `/api/jobs/viewport` in the browser, move the map, and verify loading
  appears before the response and disappears after it.
- Trigger overlapping viewport requests and verify the latest result wins and
  the loader settles.
- Check 320, 375, 414, 768, and desktop widths for overflow and control layout.
