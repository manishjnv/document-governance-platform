# EDGP Pre-Launch Fix Plan: Router Audit, Accuracy Validation, Legal Sign-off

**Target Duration**: 1-2 days (excluding legal SME wait time)
**Status**: Ready to start
**Excludes**: All Phase 3-7 deferred scope (DB scaling, ML/analytics, enterprise integrations, SOC2, mobile) — do not touch, do not "clean up while you're in there."

---

## Context

`docs/IMPLEMENTATION_PROGRESS.md` claims Phase 1-2 core product is complete and pre-launch review-accuracy work is done. A review on 2026-07-18 found three problems that need fixing before that claim is trustworthy:

1. `apps/api/app/routers/` has ~15 more routers than the Phase 1 MVP scope (`docs/planning/1_PHASE1_SCOPE.md`) called for — `compliance.py`, `compliance_frameworks.py`, `governance.py`, `predictions.py`, `teams.py`, `notifications.py`, `approvals.py`, `approval_extra.py`, `insights.py`, `insights_extra.py`, `knowledge.py`, `admin_config.py`, `admin_extra.py`, `admin_ops.py`, `collab_extra.py`, `filter_templates.py`, `search_history.py`. Unclear which are real vs. stubs, and whether they're even mounted.
2. The core product promise — "the AI review is accurate" — is only smoke-tested (1 SOW + 1 RFP). The launch-gate metrics in `docs/planning/5_LAUNCH_CRITERIA.md` (precision ≥92%, recall ≥80%, calibration <5%, dedup ≥99%) have never been run against a real test set.
3. `docs/planning/LEGAL_SEVERITY_CALIBRATION.md` worksheet is prepared but has no legal SME sign-off.

Do these three in order. Steps 1 and 2 are code/data work; step 3 is a scheduling action, not implementation — do not attempt to fill in the legal worksheet yourself.

---

## Step 1 — Router scope audit (mechanical, ~30-45 min)

**Goal**: for every router in the "extra" list above, determine: (a) is it mounted in `apps/api/app/main.py`, (b) does it contain real DB-backed logic or is it a stub/placeholder (e.g. returns hardcoded data, `NotImplementedError`, or TODO-only bodies), (c) does it have test coverage in `apps/api/tests/`.

**How**: delegate to a Haiku or Sonnet subagent (read-only, mechanical, non-load-bearing) — do not burn Opus tokens reading 15 router files line by line.

**Subagent prompt contract** (adapt directly):
> Read `apps/api/app/main.py` to see which routers from `apps/api/app/routers/` are mounted. Then for each of these files: `compliance.py`, `compliance_frameworks.py`, `governance.py`, `predictions.py`, `teams.py`, `notifications.py`, `approvals.py`, `approval_extra.py`, `insights.py`, `insights_extra.py`, `knowledge.py`, `admin_config.py`, `admin_extra.py`, `admin_ops.py`, `collab_extra.py`, `filter_templates.py`, `search_history.py` — report: mounted (Y/N), real logic vs stub (with 1-line evidence, e.g. "queries `documents` table" vs "returns static dict"), and whether a matching `test_<name>*.py` exists under `apps/api/tests/`. Output a markdown table, one row per file. Do not modify any files.

**Decision rule after the report comes back** (Opus judgment, not delegated):
- Mounted + real logic + tested → leave alone, it's legitimately part of the shipped product; note it in IMPLEMENTATION_PROGRESS.md as in-scope (even if not in the original MVP doc, scope evolved).
- Mounted + stub/no real logic → either finish it (if trivial, <30 lines, this session) or unmount it and mark `docs/IMPLEMENTATION_PROGRESS.md` explicitly as "scaffolded, not launched."
- Not mounted → delete the file, it's dead code (per project convention: delete unused code rather than leave it as unreferenced scaffolding). Confirm nothing else imports it first with a grep.

**Exit criteria**: `docs/IMPLEMENTATION_PROGRESS.md` "Done" section accurately reflects what's real; no router is silently half-built; full pytest suite still green after any deletions (`cd apps/api && python -m pytest`).

---

## Step 2 — Review-accuracy validation against launch-gate metrics (the core gate, do not skip)

This is AI-classifier / accuracy-critical work — Tier 0, main session (Opus) judgment required for evaluating failures, not delegated to Sonnet/Haiku for the analysis itself. Mechanical steps (running the pipeline, computing metrics) can be scripted.

**Goal**: produce a real pass/fail result against the 4 metrics in `docs/planning/5_LAUNCH_CRITERIA.md` (Metrics 1.1-1.4): precision ≥92%, recall ≥80%, calibration error <5%, dedup rate ≥99%.

**Steps**:
1. **Get the test set.** Need ≥10 real or realistic documents (mix of SOW + RFP) with a known-correct set of expected findings per document (ground truth). Ask the user whether real historical SOWs/RFPs are available to supply, or whether to build a synthetic set — and if synthetic, flag explicitly that this is a stopgap per the existing IMPLEMENTATION_PROGRESS.md caveat, not launch-gate-quality evidence. **Do not silently proceed with only the existing 1-SOW-1-RFP smoke set and call it validated.**
2. **Run the pipeline.** For each test document: upload → trigger review via `ReviewOrchestrator` (see `apps/api/app/ai/orchestrator.py`) → capture the 6-agent findings output.
3. **Score against ground truth.** For each document, compare AI findings to expected findings:
   - Precision = correct findings / total findings raised
   - Recall = correct findings / total expected findings
   - Calibration error = |stated confidence − empirical accuracy| averaged across findings
   - Dedup rate = fraction of near-duplicate findings correctly merged (see `apps/api/app/scoring/algorithm.py` for existing dedup logic, don't reimplement)
4. **If a metric misses threshold**: identify which agent(s) and which document(s) are the failure source before touching prompts — this is systematic-debugging territory (root cause, not a rung on the ladder skipped). Common failure classes to check: agent prompt ambiguity (`apps/api/app/ai/agent.py`), rule engine false positives/negatives (`apps/api/app/rules/`), severity miscalibration (already partially fixed this session per progress doc — check regression).
5. **Iterate**: tune the specific failing component, re-run only the affected metric's calculation (not the full document set re-upload if findings are cached), until all 4 thresholds pass or the user accepts a documented exception.
6. **Record the result** in `docs/IMPLEMENTATION_PROGRESS.md` replacing the current "Smoke-tested... synthetic validation in progress" line with the actual numbers and pass/fail per metric, plus the test-set provenance (real vs synthetic, document count, source).

**Exit criteria**: `docs/planning/5_LAUNCH_CRITERIA.md` Metrics 1.1-1.4 have real measured numbers, not "in progress"; any metric below threshold has either been fixed and re-measured, or is explicitly accepted as a known gap with the user's sign-off recorded.

**Do not** route this analysis to Tier 2/4 (OpenRouter cheap/free models) — it's a security/accuracy-classifier-adjacent path per the routing rules.

---

## Step 3 — Legal severity calibration sign-off (scheduling action)

Not implementation work. Action: tell the user `docs/planning/LEGAL_SEVERITY_CALIBRATION.md` needs to go to an actual legal SME to fill in the comparison table and approve. Do not attempt to fill it in yourself or guess at legal severity judgments. Track it as an open item in `docs/IMPLEMENTATION_PROGRESS.md` "Pending" table until sign-off is received; when it comes back, record the SME's name/date and the outcome.

---

## Session exit

After Steps 1-2 (and 3 if sign-off arrives in-session):
- Full test suite run and result recorded (`cd apps/api && python -m pytest`).
- `docs/IMPLEMENTATION_PROGRESS.md` updated: router scope reconciled, accuracy metrics filled in with real numbers, legal item status current.
- One commit per logical unit (router cleanup separate from accuracy-validation-doc-update).
- Agent-utilization footer per global playbook (Opus/Sonnet/Haiku/codex:rescue lines).
- State plainly: tests pass Y/N, whether all 4 launch-gate metrics pass, what's still open.
