# Session handoff — MITRE accuracy plan, Phases A10 + A11 (2026-08-03)

Device-level truth (A10) + report/template visual polish (A11). Read
`docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md` (Ground rules + the
A10/A11 phase blocks) before touching this area again.

## What shipped

**Commits (master), A10:** `93fee49` (piece 1: platform synonyms),
`875bbe9` (piece 2: one-row-per-log-stream guidance), `a3462a6` (piece 3:
coverage by log source, incl. the piece 4 UI hook), `689ee7d` (piece 4:
unmonitored-capability check backend), `0222924` (docs).

**Commits (master), A11:** `ea6687e` (piece 1: uniform XLSX header
fills), `35bd7a0` (piece 2: template regeneration + new generator
script), plus a piece 3 (PDF flow) + docs commit landing right after this
handoff (see the plan doc's §15 history table for final SHAs once
committed).

### A10 piece 1 — platform synonyms (`ingest.py`)

`_PLATFORM_RULES` gains `photon os`/`photon` → Linux, `rubrik` → Linux,
`infoblox`/`dns appliance(s)` → Network Devices. Deliberately **no bare
`"dns"` rule** (precision over recall — a bare "DNS servers" entry could
be Windows or Linux). IoT/mainframe z/OS entries stay unmapped on
purpose — ATT&CK v19.1 has no such platform, and mapping them would be
dishonest — pinned by a regression test so a future session doesn't "fix"
it. New tests in `test_mitre_ingest.py`.

### A10 piece 2 — one-row-per-log-stream guidance

The environment template's Read Me sheet (`apps/web/public/templates/
scopewise-mitre-environment.xlsx`) gained one plain line via a one-off
openpyxl edit (values-only addition, sheet names/headers stayed
byte-identical); a matching line was added under the wizard's environment
drop-zone (`apps/web/app/mitre/new/page.tsx`).

### A10 piece 3 — coverage by log source

New `report_common.compute_log_source_coverage(use_cases,
technique_results, index)`: groups detection rules by their `log_source`,
normalized through `ranking._norm` (reused, no second normalizer). Two
surfaces share this ONE function so they can't drift apart:
- `GET /assessments/{id}` gains a `log_source_coverage` field (computed
  only once the assessment is `completed` — the extra `use_cases` query
  is gated on that, since 5s polling stops once a run finishes).
- New "Coverage by Log Source" XLSX sheet, excluded from scoped downloads
  the same way "Use-Case Mappings" already is (not listed in any
  `_SCOPE_SHEETS` entry — no code change needed there).

Frontend: `UploadSummaryCard`'s log-source count became a clickable
toggle expanding per-source chips ("Sysmon: 12 rules → 9 techniques"),
each opening the existing `RuleListPanel` with a "What X gives you: N
rules alerting on M techniques" title, filtered by the group's
`row_refs`.

### A10 piece 4 — unmonitored-capability check (the "Infoblox problem")

New curated `data/device_classes.json` (8 classes: DNS appliance, EDR,
email gateway, firewall, IdP, backup, proxy, WAF → expected primary
telemetry category + plain capability). `quality.unmonitored_capability_
check()`: for each class matched by an Assets or Security Tooling entry,
if none of the customer's own Log Sources map to the expected category,
emits ONE aggregated finding (N = count of ranked gaps in that category;
a class with zero such gaps stays silent — no "0 gaps" claim). Wired into
`service.py`'s pipeline as "Stage 6.5" (needs `ranked["gaps"]`, so it runs
after ranking), gated on a Log Sources sheet having actually been
uploaded. The finding's message flows into the existing `assumptions`
list — same slot the UI tab / PDF appendix / XLSX Assumptions sheet
already render generically — plus a highlighted amber line in
`UploadSummaryCard` (filtered by the message's stable prefix).

### A10 wrap-up

Suite 863→876 passed / 7 skipped (+13 new tests across
`test_mitre_ingest.py`, `test_mitre_quality.py`, `test_mitre_report.py`,
`test_mitre_api.py`); `tsc --noEmit` clean. Docs: `MITRE_MODULE_REFERENCE.md`
§§5/6/11/12/13/15, `IMPLEMENTATION_PROGRESS.md`, plan status table (A10
ticked, A11 row added).

---

### A11 piece 1 — uniform XLSX header fills

`report_xlsx.py`'s shared `sheet()` helper (used by every sheet except
the hand-built Summary) now applies ONE branded fill (`0057B8`) + white
bold font to every header row, replacing the previous bold-only styling.
Summary's own two mini-table headers ("Metric/Value/What it means",
"Gap/Effort/Recommendation") got the same upgrade — previously only its
section-title bars ("EXECUTIVE SUMMARY" etc.) were brand-filled. Data-row
fills (state/tier/feasibility colors) untouched. New test:
`test_xlsx_a11_uniform_header_fill`.

### A11 piece 2 — templates regenerated with styling

New committed `scripts/build_mitre_templates.py` (prefer re-running this
over hand-editing the `.xlsx` files). Regenerates both downloadable
templates: same branded header fill/font as the XLSX report, thin
all-borders on header + example rows, ~100 pre-formatted blank data rows
per sheet (so pasted/typed content lands in a visible grid), sized column
widths (kept the existing, already-reasonable values). Every cell VALUE
verified **byte-identical** to what shipped before, via a cell-by-cell
diff against the prior git-tracked files (ignoring the newly-appended
blank rows, which are all literally blank) — the existing round-trip
tests (`test_real_use_case_template_round_trips` /
`test_real_environment_template_round_trips`) pass unchanged. Side fix:
the environment template's prose Read Me sheet had two swapped row
heights and one row with no explicit height at all — a bug left over
from A10 piece 2's ad hoc `insert_rows()` edit — the generator now sets
every row height explicitly and correctly. New test:
`test_real_templates_have_branded_header_fill_and_bordered_grid`.

### A11 piece 3 — executive PDF flow

Removed `class="page-break"` from `<h2 id="roadmap">` in `detail.html` —
it's a sub-section WITHIN the "detailed" part (tactics is the true entry
point), not a genuine PART boundary, so it no longer forces a break;
`#exec`/`#tactics`/`#register` (the real cover→executive→detailed→
appendix boundaries) keep theirs unchanged — `appendix.html` and
`executive.html` needed no edits, they were already compliant (only
their true part-boundary heading carried the class).

`report.py`'s `scope="executive"` branch now also strips
`class="page-break"` (the same one-liner the `_SECTION_SCOPES` per-tab
branch already used) — in the trimmed 2-page executive-only cut, cover +
executive summary now flow together instead of the cover→executive break
stranding page 1 half-empty.

`style.css`: `h2`/`h3` gained `page-break-after: avoid` (no orphaned
headings), `.tiles` (the scorecard) gained `page-break-inside: avoid`,
new `thead { page-break-after: avoid; }` rule keeps a table's header off
the bottom of a page. `.fix` already had `page-break-inside: avoid`
(unchanged).

**Measured** via a disposable WeasyPrint Docker container (python:3.11-
slim + weasyprint/jinja2/pydantic/pydantic-settings/openpyxl/pypdf, same
recipe as A9's session) — overlaid the OLD `report.py`/`style.css`/
`detail.html` (`git show HEAD:...`) for "before", working tree for
"after", rendered a synthetic ~89-gap assessment through the REAL
`build_html_report` + `generate_pdf`:

| | Executive PDF | Full PDF |
| --- | --- | --- |
| Before | 2 pages (page 1: 1101 chars/20 lines, page 2: 2692 chars/40 lines) | 16 pages |
| After | 2 pages (page 1: 2242 chars/38 lines, page 2: 1533 chars/22 lines) | 15 pages |

Executive page **count** stayed the same, but the distribution improved
materially: before, the forced break stranded page 1 at only ~20 lines
right after the cover (a near-empty page in the middle of a 2-page
document); after, page 1 holds more than double the content (cover +
most of the executive summary flow together), and the natural tail
overflow lands on a shorter page 2 — expected and far less objectionable
than a padded, needlessly-broken page 1. Full PDF got a modest, real
1-page reduction from letting tactics/roadmap/register flow together.
tmp/ measurement artifacts (Dockerfile, measurement script, before/after
overlays and renders) were scratch-only and deleted after use, along with
the disposable `mitre-pdf-measure` Docker image.

New test: `test_html_report_page_break_audit` (asserts `#exec`/`#tactics`/
`#register` keep the class, `#roadmap` doesn't); `test_executive_scope_
report` gained an assertion that no `page-break` class survives the trim.

### A11 wrap-up

Suite 876→879 passed / 7 skipped (+3 new tests); `tsc --noEmit` clean.
Docs: `MITRE_MODULE_REFERENCE.md` §11/§13/§15, `IMPLEMENTATION_PROGRESS.md`,
plan status table (A11 ticked).

## Gotchas hit this session (also logged to persistent memory)

- `ranking._LOG_SOURCE_RULES`'s `"sysmon"` entry maps to `{"endpoint",
  "registry", "network"}` — don't use "Sysmon" as a test's declared Log
  Sources entry when the test needs the "network" category to be
  ABSENT; use "Okta" (identity-only) instead. Bit both an A10 piece 4
  pure-function test and an E2E test before being caught.
- `replace_string_in_file` near an existing test function's tail: reread
  the region right before editing rather than trusting an earlier
  `read_file` call — guessing where a test ends (without re-reading)
  silently split an existing test in half twice this session (dangling
  asserts either mid-new-test or orphaned at EOF, surfacing as a
  `NameError` at collection/run time, not a diff-review-catchable
  mistake).
- PowerShell `-c` with embedded escaped double-quotes breaks
  (`SyntaxError: unterminated string literal`) — write a throwaway `.py`
  script file instead when the one-liner needs literal quotes.

## What's next (not done this session)

- **Deploy**: push to master, standard VPS loop (`docker compose -f
  docker-compose.vps.yml build` + `GIT_SHA=$(git rev-parse --short HEAD)
  docker compose -f docker-compose.vps.yml up -d`, no migration expected),
  smoke-test on `https://scopewise.assessiq.in` per both phases' DEPLOY
  blocks (re-create an Acme-style assessment; Photon/Infoblox/Rubrik rows
  resolve; unmapped line shrinks to IoT + z/OS only; unmonitored-DNS
  insight appears when DNS logs are omitted; log-source list clickable;
  both templates show header fill + bordered grid; full XLSX has uniform
  header fills + the new Coverage by Log Source sheet; executive PDF
  flows continuously with a visibly reduced blank share). Touch ONLY
  `scopewise-*` containers.
