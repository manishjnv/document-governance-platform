# EDGP Implementation Progress

**Last Updated:** 2026-07-19 21:10 GMT+5:30
**Current Phase:** Phase 1-2 core product complete + deployed live; pre-launch fix plan Steps 1-2 done, Step 3 pending SME. Document Lifecycle & Multi-Project plan (Projects/Versioning/Fix-verification) is planned and prompted but **not yet implemented** — see "Next action".

> Previous version of this doc (dated 07-17 02:00, showing "14% overall") was
> stale from early Phase 1 and did not reflect Phase 2/3 or the pre-launch
> review-accuracy push. Superseded by this version.

---

## ✅ Done

**Foundation, Auth, DB (Phase 1):** monorepo, Docker, FastAPI + Next.js
skeletons, JWT auth (login/logout/refresh/me/password-reset/signup),
bcrypt hashing, login rate-limiting + lockout (memory-capped), full DB
schema (6 tables, soft deletes, audit triggers), login UI. Only Azure AD
SSO (T-109, explicitly optional) is not built.

**Document management:** upload (PDF/DOCX), S3 storage with SSE-AES256,
filename path-traversal sanitization, parsing, RBAC on delete (viewer
blocked), soft delete.

**AI review engine:** 6 agents (Scope, Delivery, Commercial, Security, PMO,
Legal) run in parallel via `ReviewOrchestrator`, each with SOW- and
RFP-branching system prompts. Cross-cutting ambiguous-language regex scan.
Rule engine (20 SOW rules + 7 RFP rules). RFP is a first-class
`DocumentType` (enum + migration + rule set + agent prompts).

**OpenRouter model routing (2026-07-19):** primary/fallback chain
(GLM-5.2 → MiniMax M3 → Qwen3.7-Plus → DeepSeek) replaces the single
`deepseek-chat` default; fixed a `max_tokens=2000` truncation bug that
was silently breaking 3 of 5 candidate models. Full benchmark results
and rationale in `docs/planning/AI_MODEL_ROUTING.md`.

**Scoring & reporting:** 7-category weighted scoring, severity now actually
read from findings (was keyword-matching only — fixed), PDF report
generation via `xhtml2pdf` (was a placeholder), stored-XSS fix in HTML
report generator.

**Frontend:** dashboard, upload, search, results pages retrofitted onto
shadcn/ui component library; shared `AppShell` layout.

**Security/functional audit (2026-07-17):** RBAC gap fixed, path traversal
fixed, S3 encryption added, login lockout wired to actual config, signup
endpoint added, review status lifecycle fixed (pending→running before
orchestrator dispatch).

**Test suite:** 402 passed, 2 skipped (full suite, last run 2026-07-17).

**Router scope audit (2026-07-18, Step 1 of fix plan):** all 16 "extra"
routers beyond the original Phase 1 MVP list are mounted in `main.py` and
have real, DB-backed logic — none are dead code or stubs (one exception:
`collab_extra.py`'s comment endpoints 501 defensively if the `Comment`
model fails to import, not a placeholder). `governance.py` lacks a
router-level test (only its underlying service functions are tested).
Two stale docstrings claiming non-mounted status were fixed. Scope is
larger than the original MVP doc but legitimately shipped — not scope
creep to clean up.

**Bug-fix pass (2026-07-17/18, live UI testing):** 8 real bugs found and
fixed across upload, review pipeline, event-loop blocking, and dead
frontend routes — see `docs/RCA_LOG.md` for full root-cause detail on
each. Dashboard/search: sortable table, working type filter, stats row,
Accuracy/Completeness/Project columns, review-in-progress loading state.
Branding: renamed from "EDGP" to "ScopeWise" with a tagline and new
favicon/logo across the app.

**Risk scoring redesign (2026-07-19):** Risk Score changed from a
threshold-based model that pinned nearly everything at "100%, High" to a
saturating curve (`100 * (1 - e^(-k * severity_weighted_sum))`,
`k=0.0086`, recalibrated against real 30-400 point review volumes) plus a
new **Risk by Area** breakdown (per-axis: Compliance/Security/Governance/
Scope/Legal/Commercial/Delivery), stored on `Review.risk_breakdown`
(JSONB, migration 022) and tunable per-org via `org_risk_weights`
(mirrors the existing `app/admin/customization.py` pattern). Verified on
real production data showing actual discrimination across axes instead of
a flat 100%. Full rationale (ISO 31000/NIST, PMBOK, IACCM, FAR Part 15
citations) in `docs/planning/SCORING_METHODOLOGY.md`.

**Results page overhaul (2026-07-18/19):** full-screen layout, drag-
resizable findings/document split (33/66 default, hideable document
pane), clickable severity-filtered Findings Summary, a "Document X-Ray"
panel (parsed sections, missing-section detection), evidence-to-document
linking with scroll+highlight, and a mark-fixed/reopen action per finding
(`PATCH /reviews/{id}/findings/{finding_id}`) — explicitly labeled as an
unverified user claim, not a re-verified fix (see Document Lifecycle plan
below for why). `AppShell` sidebar made collapsible + drag-resizable.

**Public deployment (2026-07-19):** live at
https://scopewise.assessiq.in, self-hosted on a shared VPS
(`/opt/scopewise`, isolated Docker network/volumes/containers, ports
9094/9095), behind Cloudflare + the existing Caddy reverse proxy. Repo is
public at github.com/manishjnv/document-governance-platform.

**Document Lifecycle & Multi-Project planning (2026-07-19):** design-only
session (no code) on what happens when a customer marks a finding
"fixed," re-uploads a revised document, and manages multiple projects.
Decisions + full 3-phase implementation plan in
`docs/phases/prompts/DOCUMENT_LIFECYCLE_PLAN_PROMPT.md`; a combined
kickoff prompt for all 3 phases (Projects → Versioning →
Fix-verification diff) in
`docs/phases/prompts/DOCUMENT_LIFECYCLE_FULL_PROMPT.md`. **Not started.**

**Repo/process convention (2026-07-19):** added root `CLAUDE.md`
documenting docs/ folder layout, the migration-must-apply-to-4-places
rule, testing baselines, and VPS deployment specifics — written after a
process mistake (a "next session" prompt doc was saved to a scratch temp
directory instead of the established `docs/phases/prompts/` location).

**Sample documents (2026-07-19):** replaced the 2 generic placeholder
samples (`sample_rfp.docx`, `sample_sow.docx`) with real-world SOW/RFP
template sets under `docs/sample/{RFP_Sample,RFP_template,SOW_Template}/`
(~140 files) for manual UI testing across varied real document formats/
layouts.

---

## ⏳ Pending (not deferred — actual launch blockers)

| Item | Status | Blocker |
|---|---|---|
| AI accuracy validation (Metrics 1.1-1.4) | **Measured 2026-07-18** on a 12-doc synthetic set (see `docs/planning/5_LAUNCH_CRITERIA.md` "Measured Results"): rule-engine precision/recall **100%/100% PASS**; confidence calibration **17.95% error, FAIL** (target <5%); dedup **NOT MEASURABLE** | Real ≥10-doc test set still needed for launch-gate-quality evidence (synthetic is a stopgap); calibration needs prompt/confidence tuning; dedup needs to be BUILT (see below) — none of this is done yet, only measured |
| **Finding deduplication is unimplemented** (new finding, 2026-07-18) | `orchestrator._merge_findings()` concatenates all agent findings with no cross-agent duplicate detection at all | Metric 1.4 cannot pass until this is built, or the launch gate explicitly descopes it with sign-off |
| Legal severity calibration | Worksheet prepared (`docs/planning/LEGAL_SEVERITY_CALIBRATION.md`) | Needs a legal SME to actually fill in the comparison table and sign off — scheduling action, not implementation work |

## Deferred by design (see phase prompt docs for rationale, not re-litigated here)

- Phase 3: DB scaling infra (read replicas, partitioning, tracing, ELK, Grafana), mobile app
- Phase 4: ML/analytics (no training data yet)
- Phase 5: Enterprise integrations (no signed contracts)
- Phase 6: SLA credits, video training, partner program (kept: bare ticket + KB CRUD)
- Phase 7: SOC2/pen-testing, feedback/NPS (kept: informal bug-triage/patching practice)

---

## Key files

Backend: `apps/api/app/ai/agent.py` (6 agents + OpenRouter dev/test adapter),
`apps/api/app/ai/orchestrator.py`, `apps/api/app/rules/` (engine + builtin +
ambiguous_language), `apps/api/app/scoring/`, `apps/api/app/core/login_lockout.py`.

Frontend: `apps/web/app/{dashboard,upload,search,results,login}/page.tsx`,
`apps/web/components/AppShell.tsx`.

Docs: `docs/planning/4_AI_AGENT_SPECS.md` (agent specs), `docs/planning/5_LAUNCH_CRITERIA.md`
(launch gate metrics + measured results), `docs/planning/LEGAL_SEVERITY_CALIBRATION.md`
(SME worksheet), `docs/RCA_LOG.md` (every bug fixed this session, root cause +
prevention), `docs/phases/prompts/PHASE_{3-7}_PROMPT.md` (scope-trim rationale per phase).

---

## Next action

1. **Run `docs/phases/prompts/DOCUMENT_LIFECYCLE_FULL_PROMPT.md`** in a
   new session — implements Projects (first-class entity) → Document
   versioning → Fix-verification diff, in that dependency order. Planned
   2026-07-19, zero code written yet.
2. **Build finding deduplication** — currently doesn't exist at all;
   Metric 1.4 is structurally unmeasurable until this is built.
3. Fix confidence calibration (17.95% error vs. <5% target) — likely needs
   agent prompt tuning per `docs/RCA_LOG.md`-style root-cause approach, not
   a blind confidence-score rescale.
4. Get a real ≥10-doc test set (user-supplied or approved synthetic) and
   re-run the full Metrics 1.1-1.4 validation against it — the 2026-07-18
   synthetic pass is a stopgap, not launch-gate evidence.
5. Get legal SME sign-off on `LEGAL_SEVERITY_CALIBRATION.md`.
6. Everything else in Phase 1-2 core scope (including the 16 "extra"
   routers, confirmed real 2026-07-18) is done and live in production;
   Phase 3-7 items are deliberately deferred, not blockers.
