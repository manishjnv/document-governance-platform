# Phase 3 Accessibility Audit (trimmed scope)

Scope: T-3076, T-3077, T-3078, T-3079, T-3080, T-3082, T-3083, T-3084, T-3085, T-3096.
Dropped by user: i18n, T-3081 (manual screen-reader testing).

| Task | Area | Status | Notes |
|---|---|---|---|
| T-3076 | Semantic HTML / headings / alt text | FIXED | Added `scope="col"` to all `<th>` in `dashboard/page.tsx` and `OrgMemberManagement.tsx`; `aria-hidden="true"` on decorative upload SVG icon. Heading hierarchy already sequential (h1→h2→h3→h4) with no skips across all 6 pages — no change needed there. |
| T-3077 | Keyboard navigation | FIXED | Two custom clickable `<div>`s with `onClick` and no keyboard path: the upload drag-and-drop zone (`app/upload/page.tsx`) and the knowledge-base result card (`components/KnowledgeBaseSearch.tsx`). Both now have `role="button"`, `tabIndex={0}`, and an `onKeyDown` handler firing on Enter/Space. |
| T-3078 | Focus indicators | PASS | All buttons go through the shadcn `Button` (`focus-visible:ring-2`) or raw inputs with `focus:ring-2` Tailwind classes already present; nothing removed a default outline. No change needed. |
| T-3079 | Color contrast 4.5:1 | FIXED (1 token) | Computed sRGB contrast for every CSS variable in `globals.css` against `--background`: `--muted-foreground` 4.70:1 (pass), `--secondary`+white text 4.84:1 (pass), `--primary`+white text 5.57:1 (pass), `--destructive`+white text **4.47:1 (fail)**. Changed `--destructive` lightness `54%`→`53%` → now 4.60:1 (pass). No other token changed. |
| T-3080 | ARIA labels / landmarks | FIXED | Added `role="alert"` to every inline error banner (login, dashboard, search, results, upload, OrgMemberManagement, MultiCriteriaFilter); `role="status"` to the upload success banner, the install-prompt banner, and the SW-update banner; `aria-label` on the upload file input, KB search input, per-row role `<select>` in OrgMemberManagement, and the AnalyticsChart canvas wrapper (`role="img"`); `aria-expanded`/`aria-controls` on the results-page finding toggle buttons; `role="progressbar"` + `aria-valuenow/min/max` on the overall-score bar. `<main id="main-content">` landmark added in layout. |
| T-3082 | Form accessibility | FIXED | `<label>` elements without `htmlFor`/`id` pairing fixed: login (email, password), dashboard (type filter select), upload (Organization ID). `SearchFilter.tsx` and `MultiCriteriaFilter.tsx` already had correct `htmlFor`/`id` pairs — no change needed there. |
| T-3083 | Modal dialogs: focus trap | N/A | `Dialog`/`Sheet` (Radix-based, `components/ui/dialog.tsx` / `sheet.tsx`) are installed but not imported by any page or component yet (`grep` confirms zero usage). Both wrap `@radix-ui/react-dialog` directly with no custom `onOpenAutoFocus`/`onCloseAutoFocus` override, so Radix's built-in focus trap and restore-on-close are intact and will work correctly whenever a caller adopts them. Nothing to fix now. |
| T-3084 | Skip links | FIXED | Added a visually-hidden-until-focused "Skip to main content" link plus `<main id="main-content">` wrapper in `app/layout.tsx`. |
| T-3085 | Lighthouse/axe written audit | FIXED | This document. |
| T-3096 | jest-axe unit tests | PARTIAL | `jest-axe` added to devDependencies (only new dependency, as instructed) and `apps/web/tests/accessibility.test.tsx` written against `LoginPage`, `SearchFilter`, `OrgMemberManagement`. **jest itself is not configured in this repo** — no `test` script, no jest config, no `@testing-library/react`. Confirmed by running `npx jest tests/accessibility.test.tsx`: fails at TSX parse time (no babel/ts-jest transform), not a real pass/fail. Did not add a parallel test runner/config — that's a separate infra decision outside this trimmed task. Since the test file references `@testing-library/react`/`jest-axe` types and jest globals that don't resolve without that infra, `tests/` was added to `tsconfig.json`'s `exclude` so it doesn't break `tsc --noEmit` for the rest of the app; remove that exclude once jest is wired in. |

## Color contrast detail

All ratios computed via WCAG relative-luminance formula against `--background: 0 0% 100%` (white):

| Token | Before | Ratio | After | Ratio |
|---|---|---|---|---|
| `--muted-foreground` | `215 16% 47%` | 4.70:1 | unchanged | 4.70:1 |
| `--secondary` (white text on it) | `210 9% 45%` | 4.84:1 | unchanged | 4.84:1 |
| `--primary` (white text on it) | `210 100% 40%` | 5.57:1 | unchanged | 5.57:1 |
| `--destructive` (white text on it) | `354 70% 54%` | 4.47:1 (fail) | `354 70% 53%` | 4.60:1 |

Note: most page body copy uses raw Tailwind utility colors (`text-gray-500`, etc.) rather than these CSS variables — that's a larger, separate palette audit outside this task's scope, which was explicitly limited to the `globals.css` design tokens.
