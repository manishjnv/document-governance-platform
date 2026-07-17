# EDGP UI Build — Prompt for New Session

Run this after Phase 3 is complete. Paste as the opening message in a fresh session.

---

Build the enterprise UI for `apps/web` (Next.js 14 + Tailwind + shadcn/ui). This continues work already done — read this whole prompt before touching code, then check current file state before assuming anything below is still accurate.

## Design taste — apply to every screen/component

- **Spacing:** tight, intentional. Padding scale 4/8/12/16/24px. Card/panel gutters max 16-24px. Avoid the typical AI-generated look of huge margins/whitespace between content and borders.
- **Icons:** outline style (`lucide-react`), 16-20px, used sparingly — only where they aid scanning, never decorative filler.
- **Corners/shadows:** subtle radius (6-8px). No oversized rounded corners, no glassmorphism, no gradient-blob backgrounds.
- **Layout:** one sidebar OR one top nav, not both — simple, predictable hierarchy. Prefer data-dense tables/lists over card grids for admin/review screens (this is enterprise software, not a marketing site).
- **Responsive:** must work at 375px / 768px / 1440px. Sidebar collapses to a `sheet` drawer below `md`. Tables stack below `sm`. Mobile is not an afterthought.
- **Motion:** short and smooth everywhere — 150-200ms ease-out via `tailwindcss-animate` / Radix primitives. Never longer, never bouncy.
- **Charts/tooltips:** smooth-transition tooltips on graphs using the charting library's built-in tooltip/transition config — don't hand-roll popovers.
- **Data-rich components:** sortable/filterable tables, stat tiles, status badges — prioritize information density and scannability over decoration.
- Overall goal: looks human-designed, clean, professional — not AI-generated slop.

## What's already done (verify still true, don't redo)

- Foundation bugs fixed: `app/layout.tsx` added (was missing), `tailwind.config.ts` + `tsconfig.json` path globs fixed (pointed at nonexistent `src/`), broken `@radix-ui/react-slot` version pin fixed, `app/globals.css` + `lib/utils.ts` (`cn()`) + `components.json` added.
- shadcn/ui components installed in `components/ui/`: `button`, `table`, `tooltip`, `badge`, `card`, `dialog`, `dropdown-menu`, `sheet`.
- Stack already available: `@tanstack/react-query`, `zustand`, `react-hook-form` + `zod`, `chart.js` + `react-chartjs-2`, `react-pdf`.

## Build order

1. **Install `@tanstack/react-table`** and confirm it's not already present.
2. **Shared layout shell** — one component wrapping all authenticated pages: responsive nav (sidebar collapsing to `sheet` drawer below `md`), consistent header, content area with the tight-gutter spacing rules above. Build once, reuse everywhere.
3. **Retrofit existing 5 pages** onto the shared shell + shadcn components: `app/login/page.tsx`, `app/dashboard/page.tsx`, `app/upload/page.tsx`, `app/results/[reviewId]/page.tsx`, `app/(search)/page.tsx`.
4. **Data table**: wire `@tanstack/react-table` + the `table` shadcn component into the dashboard's document list (currently custom-built — check whether it's reinventing sort/filter logic the library already provides).
5. **Chart tooltips**: standardize `AnalyticsChart.tsx` and any other chart component on one consistent tooltip style using Chart.js's built-in config.

## Known pre-existing bugs (fix opportunistically while touching these files, not required upfront)

- `app/login/page.tsx` — TS2345, an object is passed where a string is expected.
- `components/AnalyticsChart.tsx` — multiple Chart.js generic-type errors around scriptable options (`ScriptableContext<keyof ChartTypeRegistry>` vs a specific chart type).

## Testing

Per project convention: minimal, targeted tests only — cover base functionality (renders, responsive breakpoint doesn't crash, no false passes). No exhaustive test suites for UI polish work.

## Verify before claiming done

`npx tsc --noEmit` in `apps/web` should show no new errors beyond the 2 pre-existing ones above. Run the dev server and manually check each retrofitted page at 375px/768px/1440px.
