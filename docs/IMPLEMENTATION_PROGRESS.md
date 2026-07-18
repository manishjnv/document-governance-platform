# EDGP Implementation Progress

**Last Updated:** 2026-07-18 07:40 GMT+5:30
**Current Phase:** Phase 1-2 core product complete; pre-launch fix plan (`docs/phases/prompts/PRELAUNCH_FIX_PLAN_PROMPT.md`) Steps 1-2 done, Step 3 pending SME. Phase 3-7 scope-trimmed per `docs/phases/prompts/`.

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

1. **Build finding deduplication** — currently doesn't exist at all;
   Metric 1.4 is structurally unmeasurable until this is built.
2. Fix confidence calibration (17.95% error vs. <5% target) — likely needs
   agent prompt tuning per `docs/RCA_LOG.md`-style root-cause approach, not
   a blind confidence-score rescale.
3. Get a real ≥10-doc test set (user-supplied or approved synthetic) and
   re-run the full Metrics 1.1-1.4 validation against it — the 2026-07-18
   synthetic pass is a stopgap, not launch-gate evidence.
4. Get legal SME sign-off on `LEGAL_SEVERITY_CALIBRATION.md`.
5. Everything else in Phase 1-2 core scope (including the 16 "extra"
   routers, confirmed real 2026-07-18) is done; Phase 3-7 items are
   deliberately deferred, not blockers.
