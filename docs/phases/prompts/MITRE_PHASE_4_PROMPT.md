# Kickoff prompt — MITRE Assessment Phase 4 (reports + trend compare)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session).

---

Implement **Phase 4** of the MITRE ATT&CK coverage-assessment feature for
ScopeWise: PDF/XLSX reports, trend comparison, and the deferred
list-endpoint extension. `docs/planning/MITRE_ASSESSMENT_PLAN.md` (§8
API, §10 reports, §13 Phase 4) is the authoritative design.

## Context

ScopeWise (FastAPI `apps/api`, Next.js `apps/web`). MITRE module Phases
0–3 are COMPLETE, verified, and **live in production** (2026-08-01):
backend pipeline + hardening (adversarial sign-off passed; migration 029
in all 3 DBs) and the `/mitre` frontend (list, wizard, results with
heatmap/gaps/assumptions tabs). Baselines: backend **641 passed / 6
skipped**; `npx tsc --noEmit` clean. ATT&CK pinned v19.1.

Missing (this phase): downloadable executive+detailed **PDF**, detailed
**XLSX** gap register, **compare/trend** between two assessments, and the
list endpoint's per-domain summary (deferred from Phase 3 so the list
page can show per-domain mini-bars without N+1 fetches).

Carried-over pending item: the **AI-tagging quality spot-check** (Phase
2) is blocked on the OpenRouter account daily cap. **At session start,
check whether the key works again** (one cheap call); if yes, run the
mixed 2-tagged/6-untagged smoke from the Phase 0-1 handoff's
instructions and report mapped counts + 5 hand-checked mappings before
starting Phase 4 work.

**Isolation contract for Phase 4:** backend changes confined to
`apps/api/app/mitre/*` + new/extended `test_mitre_*` files; frontend
changes confined to `apps/web/app/mitre/*`. **Zero shared-file edits
this phase** (router is already mounted; nav already exists). No new
dependencies — WeasyPrint and openpyxl are already installed.

## Read first (one parallel burst), then state your plan in a few lines

1. `apps/api/app/scoring/report.py` — the house report pattern to copy:
   `ReportGenerator` HTML-first structure, `_esc()` escaping of ALL
   untrusted strings (stored-XSS was a real past bug), A4 `@page` print
   CSS, **lazy WeasyPrint import** (its Pango/Cairo system libs exist
   only in Dockerfile.prod — local dev must fail soft).
2. `apps/api/app/routers/reviews.py` report endpoint (lines ~581-746) —
   the `format=html|pdf`, PDF-as-base64-in-JSON response shape the
   frontend blob-download already understands, and where the audit
   footer values (git SHA, models) come from.
3. `apps/api/app/mitre/{router,service}.py` — current endpoints, the
   summary JSONB shape (overall/domains/gaps/roadmap/narrative/
   not_applicable/counts), `params.models_used` + `params.thresholds`.
4. `apps/web/app/results/[reviewId]/page.tsx` handleDownloadPdf — the
   base64→blob download pattern; `apps/web/app/versions/diff` — the
   three-column diff layout precedent for the trend view.
5. Plan §10 (report contents + formula-injection rule) and §13 Phase 4.

## Deliverables

### 1. `app/mitre/report.py` — HTML/PDF report

One document, executive first: cover + one-line methodology footnote →
executive summary (headline strict % with weighted % noted, per-domain
bars, top-5 gaps, roadmap-at-a-glance, narrative exec summary) →
detailed sections (per-tactic coverage tables per domain; full gap
register with tier/feasibility/recommendation; roadmap detail
short/mid/long; assumptions; N/A appendix grouped derived-domain /
derived-platform / customer-declared with verbatim reasons; use-case
mapping appendix) → audit footer (attack_version, GIT_SHA env if set,
models_used, thresholds, generated timestamp, narrative generated_by).
Every customer/LLM string through `_esc()`. Numbers come ONLY from the
stored summary/technique_results — never recomputed, never from
narrative text.

### 2. XLSX export (openpyxl, in `report.py`)

Sheets: `Summary`, `Coverage by Tactic`, `Technique Register` (one row
per technique: id, name, domain, tactics, state, N/A reason, mapping
count, mapped rule names), `Use-Case Mappings`, `Gaps &
Recommendations`, `Roadmap`, `Not Applicable`, `Assumptions`.
**Formula-injection guard:** any string cell starting with `=`, `+`,
`-`, or `@` gets an apostrophe prefix — rule names/descriptions are
attacker-controlled. Modest styling only (bold headers, frozen top row,
sane column widths) — it's a working register, not a brochure.

### 3. Endpoints (mitre router only)

| Endpoint | Notes |
| --- | --- |
| `GET /assessments/{id}/report?format=html\|pdf` | mirrors the reviews.py shape (PDF base64-in-JSON) so the existing blob pattern works; 409 if assessment not completed |
| `GET /assessments/{id}/export.xlsx` | `StreamingResponse` with the xlsx content-type — do NOT copy the base64 shape for a workbook (plan §10 explicitly) |
| `GET /assessments/{id}/compare/{other_id}` | both assessments must belong to the caller's org and be completed; returns overall + per-tactic % deltas and technique lists: newly_covered, regressed (covered→partial/not), na_changed; pure-Python diff of the two technique_results arrays |
| `GET /assessments` (extend) | add a small `domains_brief` per row (per-domain strict % + state counts) read from the stored summary JSONB — no N+1, no new query per row |

All org-scoped via the existing `_get_assessment` helper; viewer role
may read/download (plan §15 Q1 default).

### 4. Frontend (mitre pages only)

- Results page: **Download PDF** + **Download XLSX** buttons (blob
  pattern; XLSX via direct authenticated fetch → blob), disabled with a
  tooltip until status is completed.
- Results page: **Compare** selector listing the org's other completed
  assessments → delta view: overall/per-tactic delta chips (▲▼ with
  green/red semantics — improvement is MORE coverage) + three-column
  newly-covered / regressed / N/A-changed lists (versions/diff layout
  precedent).
- List page: per-domain mini-bars from the new `domains_brief` (the
  Phase 3 deferral), and a trend arrow vs the previous completed run.
- Keep the locked UI principles: data-dense, minimal borders, plain-
  English tooltips (e.g. "regressed = this technique was covered in the
  older run but isn't now"), mobile no-overflow.

### 5. Tests

Backend (`test_mitre_report.py`, extend `test_mitre_api.py`): HTML
report escapes a `<script>` payload planted in a rule name; XLSX
formula-injection prefix applied (`=HYPERLINK` cell arrives with `'`);
export endpoint returns the xlsx content-type via StreamingResponse;
report 409 on a non-completed assessment; compare golden case (two
seeded technique_results → exact newly_covered/regressed/na_changed +
deltas); compare cross-org → 404; list `domains_brief` present. PDF
rendering itself: guard with a skip-if-WeasyPrint-unavailable marker so
local dev stays green; HTML path is fully tested everywhere.
Frontend: `tsc --noEmit` clean; manual click-through (downloads open,
compare renders between two seeded runs, mobile widths hold).

## Acceptance (run, don't assume)

- `cd apps/api && python -m pytest tests/test_mitre_*.py -q` green;
  full suite **641 + new passed / 6 skipped** (669-ish; Docker Desktop +
  edgp-postgres up).
- `cd apps/web && npx tsc --noEmit` clean.
- `git status`: only `app/mitre/*` (both apps), mitre tests, session
  docs. Zero shared-file edits.
- Manual: PDF opens and matches the stored numbers; XLSX opens in Excel
  with the injection guard visible on a planted `=2+2` rule name;
  compare between two seeded runs shows correct deltas.

## Wrap-up

Do NOT commit/push/deploy unless the user explicitly says so. Report:
files, test output, the tagging-smoke result (or still-blocked), manual
evidence, deviations with reasons. Update
`docs/IMPLEMENTATION_PROGRESS.md` (Phase 4 done, Phase 5 next) and the
session handoff. Phase 5 that follows is: final adversarial pass
focused on the NEW surfaces (report XSS, XLSX formula injection,
compare authz), the audit_logs resource_type enum decision, prod deploy,
and closing the tagging smoke if still open.
