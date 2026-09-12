# Session handoff — 2026-09-11: Code Security Review module (VVAH import)

> Superseded for current state by `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` (feature doc, kept current). This file is a point-in-time session log.

**Headline:** reviewed github.com/visa/visa-vulnerability-agentic-harness
(VVAH, Apache-2.0, v1.3.0), judged it feasible only as an *import* feature
(never server-side scanning on the shared VPS), then built the third
isolated ScopeWise module end to end. Suite 941→**962 passed / 7 skipped**;
`tsc --noEmit` clean. **Nothing committed, nothing deployed** — the user
asked for feasibility first and approved the build plan; commit/push/prod
migration need an explicit go.

## Feasibility verdict (kept for the record)

- VVAH = LLM-driven source-code vulnerability scanner: repo on disk in,
  findings.json + Markdown + SARIF 2.1.0 + run manifest out. Detection-only
  via `--stop-after s9`; default profile edits code (S10/S11).
- Option A (built): consultant scans locally, uploads findings.json/SARIF,
  ScopeWise renders register + XLSX/PPTX deliverables. Deterministic, no LLM.
- Option B (deferred): run VVAH from a "paste repo URL" button. Blocked by:
  no spend cap + Opus-heavy defaults; VVAH's own security.md wants a
  disposable container with egress firewalling for untrusted repos (shared
  VPS can't host that); sub-70B/OpenRouter models degrade structured
  output; prompt-injection + secret egress from repo contents; scan
  authorization liability; 30-60 min jobs exceed the in-process asyncio
  pattern. Revisit only if Option A shows demand.

## Files (all uncommitted)

| Area | Files |
|---|---|
| Migration | `apps/api/migrations/039_code_review.sql` (applied to edgp_dev + edgp_test; **prod pending**) |
| ORM / shared | `app/models/code_review.py`; `app/models/__init__.py` (+1), `enums.py` (+`CODE_REVIEW`), `audit_log.py` (CHECK mirror), `main.py` (+2 lines) |
| Backend | `app/codereview/{__init__,ingest,router,report_xlsx,report_pptx}.py` |
| Frontend | `apps/web/app/codereview/{lib.ts,page.tsx,new/page.tsx,[reviewId]/page.tsx}`; `components/AppShell.tsx` (+1 nav entry) |
| Tests | `tests/test_codereview_{ingest,api,report}.py` (21) |
| Sample | `scripts/generate_codereview_sample.py` → `docs/sample/CodeReview_Sample/` (synthetic ACME set: findings.json, .sarif, run manifest, README) |
| Docs | `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` (contract), `CLAUDE.md` (baseline + module pointer), `docs/IMPLEMENTATION_PROGRESS.md` |

## Phase 3 critique findings (fixed before tests)

1. Exploit-chain `steps` index VVAH's original finding order; ingest
   re-sorts by severity/CVSS and renumbers, so chain links pointed at the
   wrong findings → `_pos` tracking + remap in `ingest._finalize`
   (0-based only when a 0 appears; unmappable steps kept verbatim). Test added.
2. Optional manifest upload had no size cap → same 413 guard as the report.
3. Unknown-severity assumption note repeated per finding → deduped.
4. `file` path uncapped → 500-char cap.
5. Synthetic sample carried an `AKIA…` string that would trip GitHub push
   protection → neutered in the generator and regenerated.

## Next action

0. **Next session kickoff:** `docs/phases/prompts/CODE_REVIEW_SCAN_KIT_PROMPT.md`
   (scan kit hosted in ScopeWise + real golden scan + single commit — user
   decisions recorded there). Task 0 of that prompt is the professional
   UI pass from `docs/planning/CODE_REVIEW_UI_PLAN.md`, with a screenshot
   sign-off before the kit work starts.

1. On the user's go: commit (one commit: module; stage files explicitly,
   never `git add docs/`), push, deploy, apply migration 039 to
   `scopewise_prod`, run the in-container import smoke on the 3.11 image.
2. Browser click-through: `/codereview/new` with
   `docs/sample/CodeReview_Sample/acme_findings.json` + manifest → table,
   drawer, both downloads.
3. Open question: whether the PPTX deck wants the org-branding settings
   (`report_display_name`) — currently uses `resolve_branding(None)` defaults.

## Agent utilization

- Opus/Fable (main): feasibility research (5 VVAH docs), contract doc,
  Phase 3 critique + 4 inline fixes, gates, full-suite verify, session docs.
- Sonnet: 3 parallel builders — backend (migration/model/ingest/router/tests/
  sample) · reworked: Y (chain remap, manifest cap, caps); reports
  (XLSX+PPTX+test) · reworked: N; frontend (3 pages + nav, tsc clean) ·
  reworked: N.
- Haiku: n/a — Explore agent (default model) did the one isolation-seam sweep.
- codex:rescue: n/a — no auth/classifier logic touched; upload trust
  boundary reuses the existing sanitizer/role deps and was Opus-reviewed.
