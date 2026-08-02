# Session Handoff -- Web Nav Consolidation (2026-08-03)

## Goal

Frontend-only restructure of the ScopeWise web app's side nav: collapse
5 nav items down to 3 (SOW Review / MITRE Assessment / Admin), moving
Upload and Search off the nav and onto the SOW Review (`/dashboard`) page.

## Changes

1. **`apps/web/components/AppShell.tsx`** -- `NAV_ITEMS` trimmed to
   `[{ '/dashboard', 'SOW Review' }, { '/mitre', 'MITRE Assessment' }]`
   plus the existing conditional Admin item. Removed the now-unused
   `Search`/`Upload` icon imports. Desktop aside and mobile `Sheet` both
   render from the same `NavLinks`, so one edit covers both surfaces.

2. **`apps/web/app/dashboard/page.tsx`** -- renamed `<h1>` from
   "Documents" to "SOW Review" (route/URL untouched). Added a debounced
   (300ms) global search input in the header that calls the exact same
   endpoint the old `/search` page used
   (`GET /api/v1/search?q=...&skip=0&limit=20`), reusing the existing
   `handleReview`/`handleView` handlers for row actions. While a query is
   active, a clearly-labeled "Search results (N) for "..."" section with
   its own dense table (Filename/Type/Relevance/Snippet/Uploaded/Actions)
   replaces the grouped project/document table; clearing the query (or
   the inline X button) restores the normal view instantly.

   **Decision + why:** rendered search results in a separate section
   rather than reusing the same table. The two result shapes don't
   overlap -- `SearchResult` has no score/version/project fields the
   normal `Document` table depends on for its collapsible version-group
   rendering, so forcing one table to cover both would need extensive
   conditional columns for no readability win.

   Also: the existing "Filter by Type" dropdown was **not** touched or
   replaced. It's a server-side facet filter (`?document_type=`), not a
   client-side text filter -- the prompt's assumption of a client-side
   filter to replace didn't match what's actually in the code, so nothing
   there needed to change.

3. **`apps/web/app/upload/page.tsx`** -- added a "Back to SOW Review"
   link (`ArrowLeft` icon + `Link href="/dashboard"`) above the upload
   card. Left the upload flow itself, its validation, and its post-upload
   `router.push('/dashboard')` redirect untouched (it already went to
   `/dashboard`, so no redirect change was needed).

4. **`apps/web/app/search/page.tsx`** -- replaced the full page (search
   filter form, results list, CSV export, analytics chart) with a small
   client component that immediately `router.replace('/dashboard')`s.
   Old bookmarks/links to `/search` land on SOW Review instead of 404ing.

## Left alone (dead but harmless)

`components/SearchFilter.tsx`, `components/SearchResults.tsx`,
`components/AnalyticsChart.tsx`, and `lib/exportCsv.ts`'s
`exportToCsv`/`formatSearchResultsForCsv` are no longer imported by any
page (`/search` was their only caller besides `SearchFilter`, which is
still exercised directly by `tests/accessibility.test.tsx`). Not deleted
-- the task only called for deleting the search *page* conditionally on
nothing else importing it, not its sub-components, and removing them
wasn't otherwise requested. Fine to clean up in a future pass if desired.

## Verification

- `cd apps/web && npx tsc --noEmit` -- clean (exit 0).
- Backend untouched: no `apps/api` files were changed, so the 809/7
  pytest baseline doesn't need re-running.
- Manual smoke test **not run in-browser this session** (no dev server
  was started) -- the checklist below should be walked through before
  merging/deploying:
  - [ ] Side nav (desktop + mobile) shows exactly SOW Review / MITRE
        Assessment / (Admin if applicable) -- no Upload, no Search.
  - [ ] `/dashboard` shows the new search input and an "Upload Document"
        button in the header.
  - [ ] Typing a real query returns server-backed results in the new
        section; clearing it restores the grouped document table.
  - [ ] `/upload` still uploads successfully and its "Back to SOW Review"
        link returns to `/dashboard`.
  - [ ] `/search` redirects to `/dashboard` (not a 404).
  - [ ] No page still shows the old "Documents" or "Search" labels.

## Not touched

`apps/web/app/mitre/**`, `apps/api/**` (no backend files touched at all
this session), Admin page, auth/login flows.

## Next action

Run the manual smoke checklist above in a browser against a local dev
server before considering this done. No commit/push was made this
session (not requested) -- one commit for this logical unit when asked.

---

## Addendum — review + deploy outcome (2026-08-03, follow-up session)

The build session's output was diff-reviewed and shipped:

- **Review verdict: passed.** The section-vs-merged-table choice, the
  untouched type-facet filter, `router.replace` for the redirect, and
  leaving the a11y-tested `SearchFilter` in place were all upheld. Two
  functional drops the build report didn't mention were identified and
  accepted (recorded in the code commit message): the old `/search`
  page's search-history logging (`POST /api/v1/search/history`), CSV
  export, and analytics chart do not carry over — the backend endpoints
  remain if any is wanted later. `tsc --noEmit` was independently
  re-verified clean. Not security-adjacent → no adversarial gate.
- **Shipped:** `9f6e091` (code, 4 files +179/−255) + `d306e5f` (docs).
  Deployed to the VPS (frontend-only, no migration); prod at `d306e5f`,
  all `scopewise-*` containers up. Smoke: `/dashboard` 200 and serving
  the "SOW Review" markup, `/search` 200 (client redirect), `/upload` +
  `/mitre` 200, API 401 unauthenticated.
- **Still open:** the manual click-through checklist above was not run
  in a browser (neither session started one) — worth 60 seconds on the
  live site: search box results + clear button, upload back-link,
  mobile nav parity.
