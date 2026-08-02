# Kickoff prompt — consolidate Documents/Upload/Search into "SOW Review"

Self-contained kickoff for a fresh session (target model: Sonnet 5).
Paste everything below the line.

---

Consolidate the ScopeWise web app's document navigation. Frontend-only
UI restructure — no backend changes expected.

## Read first (before any edit; state your plan before touching code)

Root `CLAUDE.md` (testing gates, git rules, deploy), then the actual
files: `apps/web/components/AppShell.tsx` (the side nav),
`apps/web/app/dashboard/page.tsx` (the current "Documents" page),
`apps/web/app/search/page.tsx` (note WHICH API endpoint it calls and
what its results UI shows), `apps/web/app/upload/page.tsx`. The repo may
have drifted since this prompt was written — trust the code you read,
not this prompt's description of it.

## Goal

Today the side nav is: Documents (`/dashboard`), Upload (`/upload`),
Search (`/search`), MITRE Assessment (`/mitre`), Admin (`/admin`).
After this change it must be exactly: **SOW Review** (`/dashboard`),
**MITRE Assessment**, **Admin**. Upload and Search stop being nav
destinations; their capabilities live on (or launch from) the SOW
Review page.

## Exact changes

1. **Rename Documents → SOW Review.** Nav label + icon-title in
   `AppShell.tsx`, and the page's own `<h1>`/title on
   `/dashboard`. Keep the `/dashboard` URL (bookmarks, redirects, and
   internal `href="/dashboard"` links stay valid — do NOT rename the
   route). Grep the whole of `apps/web` for other user-facing
   "Documents" labels pointing at this page (mobile nav, tooltips, empty
   states) and rename those too. Do NOT rename API fields, types, or
   anything backend.
2. **Global search moves ONTO the SOW Review page.** Add a search
   input on `/dashboard` that searches ANY uploaded document (the same
   scope the `/search` page covers today) — reuse the exact API
   endpoint(s) `/search/page.tsx` calls; do not invent a new one. The
   existing dashboard table likely has a client-side filter — the new
   search must be the SERVER-backed global search, and the two should
   not be confusingly duplicated: replace the client-side filter with
   the global search if the result shapes allow rendering in the same
   table, otherwise render search results as a clearly-labeled section
   above/instead-of the table while a query is active (pick whichever
   reads cleaner after you've seen both pages; say which you chose and
   why in one line). Debounce input; empty query restores the normal
   list; keep the house UI taste (tight, data-dense, shadcn, no layout
   jank).
3. **Upload becomes a button, not a nav item.** On the SOW Review page
   header, an "Upload document" button navigates to the SAME `/upload`
   page (do not rebuild or inline the upload flow — its logic is
   untouched). Remove Upload from the side nav. On the upload page, add
   a small "Back to SOW Review" link so it isn't a dead end, and after a
   successful upload keep whatever redirect it does today (verify where
   it goes — if it goes to `/dashboard` already, nothing to change).
4. **Retire the `/search` nav route gracefully.** Remove it from the
   nav; make `/search` redirect to `/dashboard` (client redirect is
   fine) so old bookmarks don't 404. Delete the search page component
   only if nothing else imports from it — if the SOW Review page now
   reuses pieces of it, move those pieces rather than duplicating.

## Do NOT touch

- Anything under `apps/web/app/mitre/` or `apps/api/app/mitre/` (the
  MITRE module has its own reference doc and standing isolation rule).
- Backend routers/endpoints — this is a frontend consolidation; the
  search API is consumed as-is.
- Auth/login flows, Admin page.

## Gates (CLAUDE.md rules apply)

- `cd apps/web && npx tsc --noEmit` must be clean.
- Backend suite untouched-but-verify only if you changed any `apps/api`
  file (you shouldn't); if you must run pytest, run SOLO per the
  `edgp-test-single-runner-rule` memory.
- Manual smoke list to report: nav shows exactly SOW Review / MITRE
  Assessment / Admin; `/dashboard` shows the search input and Upload
  button; a real search query returns server results; `/upload` still
  uploads and links back; `/search` redirects; mobile nav (AppShell has
  one) matches the desktop nav; no page shows the old "Documents"/
  "Search" labels.
- Don't commit/push/deploy unless the user says so. One commit per
  logical unit when asked. Update `docs/IMPLEMENTATION_PROGRESS.md` and
  write a session handoff in `docs/phases/summaries/` at the end.
