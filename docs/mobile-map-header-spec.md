# Mobile Map-First Header SPEC

## Purpose

Make the public JobMap immediately useful on a phone by opening on the map and
keeping the two highest-frequency navigation controls in the fixed top bar.

## Scope

- Open the mobile workspace with the map active by default.
- Add a localized major-region selector to the mobile top bar.
- Keep the top-bar region selector and the discovery-panel city selector in sync.
- Fetch city job counts once and reuse them in the discovery-panel selector.
- Use a compact mobile language selector while preserving full language names on desktop.
- Keep the existing mobile list/map switcher and desktop split workspace.

## Completion Criteria

- At 320, 375, 414, and 768 CSS pixels, the map is visible on first load.
- The top bar does not overflow or overlap at any required mobile width.
- Selecting a region moves the map and keeps map view active.
- The mobile language selector shows short, unambiguous labels and does not
  produce the narrow, clipped popup shown in the reported screenshot.
- At desktop width, the full wordmark, status, full language labels, city selector,
  discovery panel, and map remain available.
- Keyboard focus remains visible and every select keeps a 44px touch target.
- Frontend lint and production build pass, with no browser error overlay or
  horizontal scrolling in the required viewports.
