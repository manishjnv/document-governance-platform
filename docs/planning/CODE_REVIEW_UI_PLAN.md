# Code Security Review — UI plan (professional pass before the kit session)

**Written:** 2026-09-11. **Status:** built 2026-09-11 (same day, next session) — sections 2–6 implemented as specified; results page split into `[reviewId]/components/`. Kept as the design record. The v1 pages under
`apps/web/app/codereview/` work (list / upload / results + drawer, `tsc`
clean) but were built in one pass by a subagent from a functional spec.
This plan raises them to the standard of the MITRE results page before the
scan-kit session adds the "Get the scanner" panel. Design taste per the
project memory: tight spacing, data-dense, sparse outline icons, no
"AI-generated look", responsive, smooth transitions. Reuse
`components/ui/*` (badge, button, card, dialog, dropdown-menu, sheet,
table, tooltip) and the MITRE components where they fit
(`ExecutiveBand`, `StateBadge`, `DrillDownPanel`, `useSheetResize`) —
copy, don't import across modules if a prop change would be needed.

## 1. Information architecture (3 pages, one drawer)

```
/codereview                 list of reviews (cards)  ── [New review]
/codereview/new             two-column: "Get the scanner" | "Upload results"
/codereview/[id]            results: header band → severity strip → table + drawer
                            └ tabs: Findings · Exploit chains · Scan details
```

## 2. `/codereview` — list page

```
┌ Code Security Reviews                      [Get scanner ▾] [+ New review] ┐
│ ⌕ search name / repo        ▾ sort: newest                                │
├──────────────────┬──────────────────┬──────────────────┐                  │
│ acme-payments-api│ portal-web       │ …                │  ← 1→3 columns   │
│ 3f9c2a1 · 11 Sep │ a8b1c02 · 9 Sep  │                  │                  │
│ ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮  │ ▮▮▮▮▮▮▮▮▮▮▮▮▮▮▮  │  severity bar    │                  │
│ 2 crit 3 high 4… │ 0 crit 1 high …  │  (stacked, 6px)  │                  │
│ 12 findings · 2 chains          ⋯   │                  │                  │
└──────────────────┴──────────────────┴──────────────────┘                  │
```

- Card body: name (truncate), repo label + short sha chip, date; a stacked
  horizontal severity bar (critical→info, proportional widths, the same
  colours as the tiles) with the counts as a one-line legend under it;
  footer: total findings, chain count, source-format chip
  (`findings.json` / `SARIF`).
- Kebab menu (dropdown-menu) → Rename, Delete (dialog confirm, not
  `window.confirm`).
- Empty state: one sentence + the two CTAs (Get scanner, New review).
- Loading: 3 skeleton cards; error: inline alert like MITRE.

## 3. `/codereview/new` — upload page

```
┌ New code security review                                                   ┐
│ ┌ 1 · Get the scanner ───────────────┐ ┌ 2 · Upload the results ─────────┐ │
│ │ [⬇ Download scan kit]  v1.3.0     │ │ Name (optional)  [________]     │ │
│ │ ① pip install …                    │ │ ┌ drop findings.json / .sarif / │ │
│ │ ② put your API key in .env         │ │ │   scan zip here  (≤10 MB)     │ │
│ │ ③ scopewise-scan --repo <path>     │ │ └───────────────────────────────┘ │
│ │ ── or run VVAH directly: ──        │ │ + run_manifest (optional)        │ │
│ │ `vvaharness scan … --stop-after s9`│ │ ✓ acme_findings.json · 84 KB    │ │
│ │ [copy]                             │ │            [Import and review →] │ │
│ └────────────────────────────────────┘ └──────────────────────────────────┘ │
│ ⓘ Findings are AI triage candidates from your scan; nothing runs here.     │
└─────────────────────────────────────────────────────────────────────────────┘
```

- Left column is a static card now (command + copy button, kit download
  button disabled with "coming soon" tooltip until the kit session lands
  it). Right column is the existing form, restyled: single dropzone that
  accepts `.json/.sarif/.zip`, selected-file row with size + remove ✕,
  manifest as a secondary dashed row, primary button full-width on mobile.
- Validation inline under the dropzone (type, size), server `detail`
  shown in the same slot. Submit shows a spinner + "Parsing…" label.
- Columns stack on < 768 px; step numbers become a vertical stepper.

## 4. `/codereview/[id]` — results page

```
┌ ← Reviews   acme-payments-api  ✎        findings.json · 3f9c2a1 · 11 Sep  ┐
│                                            [⬇ XLSX] [⬇ PPTX] [⋯]          │
├─ Executive band (copy MITRE ExecutiveBand layout) ────────────────────────┤
│  12 findings │ 2 critical │ 3 high │ 2 exploit chains │ 1 verifier FP     │
│  "Confirm the 2 criticals first — both are reachable from the login form" │
├─ Severity strip: [All 12] [Critical 2] [High 3] [Medium 4] [Low 2] [Info 1]┤
│  (toggle chips, active = filled colour; counts update with search)        │
├─ Tabs: Findings · Exploit chains (2) · Scan details ──────────────────────┤
│ ⌕ search title / file / CWE      ▾ class: all   ▾ verdict: all   ▾ sort   │
│ ┌──┬────────┬────────────────────────────┬──────────┬──────┬─────┬───────┐ │
│ │# │ Sev    │ Title                      │ Class    │ CWE  │CVSS │ File  │ │
│ │1 │●Crit   │ SQL injection in /login    │ injection│ 89   │ 9.8 │ db.py:42 │
│ …  sticky header, zebra rows, row hover, keyboard ↑↓ + Enter opens drawer │
│ └──┴────────┴────────────────────────────┴──────────┴──────┴─────┴───────┘ │
│  showing 12 of 12                                                          │
└────────────────────────────────────────────────────────────────────────────┘
```

- **Executive band**: 5 stat tiles + one derived plain-English line
  (deterministic: highest-severity count + top file), same visual as the
  MITRE `ExecutiveBand` (thin border, no gradients).
- **Findings tab**: table via `components/ui/table`; columns #, severity
  (StateBadge-style dot + label), title (2-line clamp), class, CWE (link),
  CVSS (mono, right-aligned), confidence (mini bar 0–1 with `n votes`
  tooltip), file:lines (mono, truncated start), verdict chip (FP = muted).
  Header sort on every column; filters: severity strip, class dropdown,
  verdict dropdown, text search. Row density 36 px. Mobile: card rows
  (title, sev, file) instead of the table.
- **Exploit chains tab**: one card per chain — title, severity chip,
  narrative, step pills "#2 → #4" that open the drawer.
- **Scan details tab**: two definition lists — scan metrics (files in
  scope, analyzed, duration, tokens, TP/FP counts, degraded reason) and
  run manifest (git sha, VVAH version, models per role, cost). Plus the
  `assumptions[]` list under "Ingest notes".
- **Drawer** (Sheet, resizable via `useSheetResize`, 560 px default):
  header = #, severity chip, title; meta grid (CWE link, CVSS score +
  vector in mono, confidence/votes, verdict + reason, file + lines,
  source → sink); sections in a fixed order with small caps headings:
  Description · Impact · Exploit scenario · Preconditions · Code
  (`<pre>` with line-start numbering) · How to fix · Exploitability ·
  Verifier reasoning · Also at. Prev/Next finding buttons in the footer
  (respect current filter/sort). Copy-link button (`?finding=N` deep link).
- **Footer**: attribution line in muted text.
- States: loading skeleton for band + 6 table rows; degraded banner
  (amber, dismissible per session); empty filtered state.

## 5. Visual system — match the live ScopeWise theme (verified 2026-09-11)

Source of truth: `apps/web/app/globals.css` + `tailwind.config.ts` +
`apps/web/app/mitre/lib.ts` chip classes. Do not invent tokens.

- **Base**: white background, Inter, foreground `222 47% 11%`, borders
  `border` (`214 32% 91%`), radius `0.5rem` (`rounded-md` on cards/inputs,
  `rounded-full` on chips). No shadows, no gradients.
- **Primary blue** `hsl(210 100% 40%)` (`text-primary` / `bg-primary`) is
  the only action colour: primary buttons, active nav, active severity
  chip outline, headline numbers in the executive band (`text-primary`,
  as `ExecutiveBand` does), links (CWE, deep link), focus rings
  (`ring-ring`), row hover `hover:bg-primary/5`.
- **Muted** (`bg-muted`, `text-muted-foreground`) for labels, empty
  states, footers, secondary chips (source format, sha).
- **Severity colours — use them wherever severity appears** (tiles,
  strip, table dot + chip, stacked bar, drawer header, chain cards),
  always in the MITRE tinted-chip pattern `bg-{c}-100 text-{c}-800
  border-{c}-200` and a solid `bg-{c}-600` dot / bar segment:

  | Severity | c | Chip | Dot/bar |
  |---|---|---|---|
  | critical | rose | `bg-rose-100 text-rose-800 border-rose-200` | `bg-rose-600` |
  | high | orange | `bg-orange-100 text-orange-800 border-orange-200` | `bg-orange-500` |
  | medium | amber | `bg-amber-100 text-amber-800 border-amber-200` | `bg-amber-500` |
  | low | emerald | `bg-emerald-100 text-emerald-800 border-emerald-200` | `bg-emerald-600` |
  | info | sky | `bg-sky-100 text-sky-800 border-sky-200` | `bg-sky-500` |

  Verdict chips: TRUE_POSITIVE `emerald` tint, FALSE_POSITIVE `bg-muted
  text-muted-foreground` with strikethrough-free "Verifier: false
  positive" tooltip. Degraded banner: `amber` tint. Destructive actions:
  `text-destructive`. Every chip gets a tooltip (locked MITRE rule).
- **Colour in numbers**: executive-band tiles show the count in the
  severity colour (`text-rose-700`, `text-orange-600`, …) with muted
  labels; the stacked bar on list cards uses the dot colours in the
  severity order left→right; confidence mini-bar uses `bg-primary`.
- **Type scale** (same as MITRE): page title `text-lg font-semibold`,
  tile number `text-2xl font-bold`, tile label `text-[11px]`, table
  `text-sm`, chips `text-[11px] font-medium`, mono for sha / CVSS vector /
  file paths (`font-mono text-xs`).
- **Spacing**: `p-3.5` cards, `gap-2`/`gap-3` grids, 36 px table rows,
  `mb-4` between page blocks. **Motion**: `transition-colors` 150 ms only;
  Sheet slide for the drawer. **Icons**: lucide outline 14–16 px, muted
  unless it is a severity dot; the module icon is `Bug`.
- Dark mode is `class`-based but not shipped; keep tokens semantic so it
  works if enabled.

## 6. Build plan (one Sonnet agent per page, parallel; Opus critique)

1. `lib.ts`: add `SEVERITY_META.bar` classes, `deriveHeadline(report)`,
   `filterFindings(findings, {severity, klass, verdict, query})` — pure,
   unit-testable in Vitest if present, else typed only.
2. List page → section 2. Upload page → section 3 (kit button disabled).
   Results page → section 4 (split into `components/`:
   `ReviewBand.tsx`, `SeverityStrip.tsx`, `FindingsTable.tsx`,
   `FindingDrawer.tsx`, `ChainsTab.tsx`, `ScanDetailsTab.tsx`).
3. Gates: `npx tsc --noEmit`; manual pass at 400 / 768 / 1280 px with the
   synthetic sample; keyboard-only walk of table → drawer → prev/next.
4. Screenshot review by the user before the kit session starts.

Effort: ~1 day of agent time. Nothing in this plan touches the API.
