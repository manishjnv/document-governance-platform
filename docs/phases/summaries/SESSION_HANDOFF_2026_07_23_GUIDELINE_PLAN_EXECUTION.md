# Session Handoff — 2026-07-23 — Guideline Feasibility Plan Executed (A→D)

**Headline:** All four phases of
`docs/phases/prompts/GUIDELINE_FEASIBILITY_PLAN_PROMPT.md` executed,
deployed, and measured. Strict recall on the 29-row ground truth went
**72.4% → 93.1%**, rule-engine false positives **4 → 0**, effective
precision ≈93% → ≈97%. Both exit gates passed (A: ≥79% required; C: see
below).

## Commits (this session)

| SHA | What |
|---|---|
| 0ea801f | A1+A3: section-presence matching fix (numbered headings, word-boundary aliases) + 13 guideline rules SOW-021..033 |
| a291e78 | A2: self-negating finding filter at orchestrator ingestion |
| bbf264a | A4: Scope per-service decomposition + Delivery appendix-table audit prompts; not-applicable-omit rule |
| 08caf22 | Adversarial-review fixes: hedge-aware self-negation filter, hyphen-aware alias boundaries |
| d707d09 | Phase A re-measurement appended to ACCURACY_BASELINE_2026_07_22.md |
| 24125fa | Phase B: typed evidence model (migration 027) — model/schema/producers/UI |
| ec9f3b8 | Phase C: reference detector (REF-SCAN) + conflict LLM scan (CONFLICT-SCAN) |
| a0f13e4 | Adversarial-review fix: word-boundary reference resolution |
| b33ba54 | Phase D: audit_meta JSONB (migration 028), models-used capture, footers |
| (last) | Session-exit docs (this file, IMPLEMENTATION_PROGRESS.md, C-gate measurement) |

## Key facts for a future session

- **Migrations 027 + 028 applied to all 4 places** (edgp_dev, edgp_test,
  scopewise_prod, hand-rolled schemas in `test_insights_extra.py`).
- Test baseline is now **560 passed, 6 skipped** (was 505; skips are
  pre-existing env-dependent ones). `npx tsc --noEmit` clean.
- The 4 FP rules (SOW-001/002/003/007) fixed at the *matcher* level
  (`engine._normalize_heading` + `_alias_in_headings`), not just synonyms —
  numbered headings ("3. Scope of Services") were never matchable before.
- Self-negating filter is two-tier (`orchestrator._SELF_NEGATING_DIRECT` /
  `_CLEAN_BILL` + `_HEDGE_OR_CONTRAST`) — "is not compliant" and
  "no issues in §3 but §4 lacks X" survive; verified by tests.
- REF-SCAN and CONFLICT-SCAN are pseudo rule ids in
  `customization.VALID_RULE_IDS` → org-disableable via existing plumbing.
- ConflictDetector is mirrored to `prompts/conflict.md`;
  `scripts/generate_prompt_docs.py` now includes it.
- `RULES_VERSION` ("2026-07-23.1") in `builtin.py` — **bump on any rule
  change**, it lands in every review's `audit_meta`.
- OpenRouter latency variance is real: 2 of 5 VPS reruns lost one agent to
  a double timeout (60s+120s). Measurement runs must check "6/6 agents"
  before scoring; rerun if partial.
- Rerun harness: `/tmp/rerun_review.py` on the VPS host + inside
  `scopewise-api` (in-process ASGI, mints admin JWT, uploads
  `/tmp/SOC_SOW_Testing.docx`, polls, dumps `/tmp/rerun_findings.json`).

## Remaining gaps (not blockers, tracked)

- SOW-002 (Customer Environment inventory) and SOW-020 (open-items
  prioritization) remain partial matches — the last 2 of 29.
- `audit_meta.app_git_sha` reads "unknown" — the VPS compose doesn't pass a
  GIT_SHA env/build arg yet. Cosmetic; wire it in docker-compose.vps.yml
  when convenient.
- Conflict scan found 0 contradictions on the test doc (doc has deliberate
  *ambiguities*, arguably no hard *contradictions*) — quality unproven on a
  doc with real conflicts; park per plan's abort criterion, revisit with a
  synthetic conflicting doc if needed.
- DOCX pagination still returns page_count=1 → page/line evidence fields
  stay null for DOCX (known ceiling, plan says don't block on it).
- File-level SHA-256 deferred (audit_meta hashes parsed_text) — needs a
  documents migration if a customer asks for file integrity.

## Next action

Launch-criteria Metrics 1.3 (confidence calibration, 17.95% error vs <5%
target) is now the largest unaddressed accuracy metric.

## Agent utilization

- Opus (Fable 5, main): design + all judgment calls, A1/A2/A4/B/C/D
  implementation (files hot in context, under delegation threshold per
  playbook), scoring vs ground truth, docs.
- Sonnet: 2 adversarial reviews (Phase A diff → revise, 2 real bugs fixed;
  Phase C diff → revise, 1 real bug fixed). `sonnet · adversarial review A ·
  reworked: N`; `sonnet · adversarial review C · reworked: N`.
- Haiku: n/a — no bulk-read/grep sweeps needed (targeted reads sufficed).
- codex:rescue: n/a — pre-flight found last codex job failed with a
  persistent model-config 400 (gpt-5 unsupported on ChatGPT account);
  Sonnet takeover per fallback ladder, verdicts: revise→accept ×2.
