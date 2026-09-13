# UI design references

Reference material for any ScopeWise UI work (see the `ui-design-workflow` skill and
`docs/planning/UI_REDESIGN_BUILD_PLAN.md`). Screenshots of third-party products are kept
**local only** (`*.png` here is gitignored: this repo is public). Capture them from a logged-in
session or with `python apps/web/tests/ui_sweep.py --capture-references` (public pages only).

## What to copy from whom

| Product | URL | Copy this | Ignore this |
|---|---|---|---|
| Linear | https://linear.app | list density (13px rows, 36px height), inline status chips with dots, keyboard-first sheets, sidebar at 220-240px with soft active tint | dark theme, custom fonts |
| Stripe Dashboard | https://dashboard.stripe.com (needs login) / https://stripe.com/docs | KPI tiles (label above, big tabular number, delta below), table header type (11px uppercase), filter bar layout | purple accent |
| Attio | https://attio.com | record tables that become cards on phone, hairline borders, no shadows, 8-10px radii | marketing gradients |
| Vercel Dashboard | https://vercel.com/home | page header with meta line and right-aligned actions, empty states with one primary action, skeleton loading | monochrome palette |

## Our own baselines

`docs/design/complete-app-2026-09-12/*.dc.html` are the approved artboards (render with
`harness.py`). Screenshots of the live app with real data belong next to them locally
(`shots-<date>/`), not in git.

## Review checklist (run per screen, real data on screen)

1. Density: does the row height, cell padding and type size match the reference table?
2. Contrast: every number and value full ink, muted only on labels.
3. Hierarchy: one h1, one primary action, everything else outline or ghost.
4. Phone: no horizontal scroll at 390px (`ui_sweep.py` fails on it), tables become card rows.
5. States: loading, empty, error and gated all designed, none a bare sentence.
