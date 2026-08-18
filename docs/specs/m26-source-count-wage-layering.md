# M26 Source Counts, Title Wage Parsing, and Header Layering

## Purpose

Expose how many public jobs each source-country filter contains, extract exact
hourly wages when a source puts them in the title, and keep the language selector
usable while a desktop job detail panel is open.

## Scope

- Add one aggregate public API that returns counts for all visible representative
  jobs and for Korean, Japanese, and Chinese source communities.
- Count a representative once per country using every linked `job_sources` row;
  a cross-country merged representative can correctly appear in more than one
  country count.
- Show locale-formatted counts in every source-country select option without
  changing the existing filter placement.
- Search titles as well as structured wage fields and descriptions in every
  source parser.
- Recognize Korean hourly-pay markers such as `시급 24.75불` and preserve cents
  through crawler storage and public API responses.
- Keep the top app bar and its language menu above the non-modal desktop job
  detail panel while retaining the existing keyboard menu behavior.

## User Scenarios

- A visitor opens the source-country select and compares the available job count
  before choosing a source community.
- A crawler encounters an hourly wage only in a post title and stores the exact
  amount so visitors can see and filter on it.
- A desktop visitor opens a job detail, then changes the interface language
  without first closing that detail.

## Edge Cases

- A representative linked to two Korean sources counts once for Korea, while a
  representative linked to Korean and Japanese sources counts once in each.
- Empty countries remain present with a zero count.
- Count-loading failure leaves the filter usable and shows localized feedback.
- Bonus or monthly amounts above the hourly wage range are not mistaken for an
  hourly amount when a valid `시급` value is present.
- Decimal filter values are validated as finite, non-negative numbers.

## Exclusions

- Do not change duplicate thresholds or split representative jobs.
- Do not infer a source country from title language or employer identity.
- Do not rewrite old rows by guessing wages from stored titles in this checkpoint;
  normal local crawler updates will refresh affected posts.
- Do not push or deploy unless requested separately.

## Completion Criteria

- The source selector displays localized counts for all, Korea, Japan, and China.
- Counts use the same public eligibility gate as the map and all linked raw sources.
- The supplied `시급 24.75불` title parses to `24.75` rather than missing or
  rounding the wage.
- Viewport and nearby routes accept decimal wage filters and return numeric wages.
- At desktop widths, opening a job detail and then the language selector leaves
  the complete language menu visible and operable above the detail panel.
- Frontend lint/build, crawler tests/compile, local migration/API checks, responsive
  browser checks, and independent checkpoint review pass.
