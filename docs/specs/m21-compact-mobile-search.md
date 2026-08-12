# M21 Compact Mobile Search

## Purpose

Expose more job results above the fold on phone-sized screens by reducing the
vertical space used by the public introduction and location-search area.

## Scope

- Apply compact spacing only below the existing 48rem responsive breakpoint.
- Keep the eyebrow and primary heading visible.
- Hide the supporting hero description on phone-sized screens.
- Remove the empty search-error row while preserving populated error feedback.
- Keep the search input and submit button at least 44px high.
- Preserve tablet/desktop presentation and all search behavior.

## Exclusions

- No changes to search requests, autocomplete, geocoding, filters, job data, or map behavior.
- No redesign of job cards, the mobile view switcher, or the desktop discovery panel.
- No database, crawler, environment-variable, or Vercel architecture changes.

## User Scenarios

1. A phone user opens list view and sees job results sooner without scrolling past a large search header.
2. A phone user can still tap, type, and submit the location search comfortably.
3. A search with no matching Canadian location displays its localized error message beneath the controls.
4. A tablet or desktop user keeps the existing descriptive introduction and spacing.

## Completion Criteria

- At 375px width, the combined introduction and empty search area is no more than 170px high.
- Search input and submit button remain at least 44px high.
- The visible `label` remains associated with the location input.
- The empty error element consumes no layout space; populated errors remain visible and announced.
- No horizontal overflow at 320px, 375px, 667px landscape, or 768px.
- Enlarged root text does not introduce horizontal overflow.
- Frontend lint and production build pass with zero browser console errors.

## Edge Cases

- Long localized headings may wrap vertically but must not be truncated.
- Disabled and loading search-button states must remain legible and touch-sized.
- Error feedback may increase the section height only while an error is present.

## Test Method

- Run `npm run lint` and `npm run build` in `frontend/`.
- Use Playwright at 320x700, 375x812, 667x375, and 768x700.
- Measure introduction, search, input, and button bounding boxes.
- Submit a guaranteed-missing location and verify the localized error remains visible.
- Repeat at 375px with a 20px root font and check horizontal overflow.
- Check browser console errors and inspect a 375px screenshot.
