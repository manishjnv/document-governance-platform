# Session handoff — MITRE accuracy arc: plan authoring, verification, hardening (2026-08-03)

**Headline:** Orchestration session for the full MITRE accuracy arc: reviewed
`Claude_MITRE_Assessment_Review_Prompt.md` against the live module, authored
the 11-phase `MITRE_ACCURACY_IMPROVEMENT_PLAN.md` (A1–A11), independently
verified all three build sessions' output (A1–A8, A9, A10+A11), ran an
independent adversarial review of A7 that found and shipped one hardening
fix, fixed one A9 leftover, and answered live-testing questions on the Acme
assessment. Prod: `38b3e73`, suite **879/7**, tsc clean, tree clean, all
pushed.

**Commits this session (orchestrator-authored):**
- `e16b2a2` plan A1–A8 + run-all kickoff prompt
- `64b99e4` A7 hardening: Sentinel connector `kind[:200]` truncation + regression test
- `6af5a3c` plan A9 + baseline 859
- `3fd35f6` A9 fix: XLSX Read Me pointed at deleted 'Gaps & Recommendations' sheet
- `f64f6ed` plan A10 (device-level truth) · `f91694f` plan A11 (visual polish)
(Build-session commits are listed in their own handoffs:
`SESSION_HANDOFF_2026_08_03_MITRE_ACCURACY_PLAN_A1_A8.md` and the A9/A10+A11
handoffs.)

**Tests:** 879 passed / 7 skipped (reproduced independently after each build
session: 858→859→863→879). **Next action:** none queued — only parked item is
the "covered"→"has detection" relabel (user positioning decision).
**Open questions:** none.

---

## Detail

### 1. Review that seeded the plan
Consultant-style review of the user's data-collection review prompt found:
(a) the prompt embedded no field inventory to review; (b) two asks violated
product invariants (sample logs, diagrams); (c) it promised layers the
inputs can't support (parser/normalization coverage, mainframe). Module
audit found Crown Jewels parsed-but-unused, AI tagging validated only by a
6/6 smoke, and telemetry-match signal never surfaced as a warning.

### 2. The plan (docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md)
A1 prompt-doc fix · A2 Sigma benchmark · A3 shelfware detector · A4 Crown
Jewels ranking · A5 keyword aliases 39→55 · A6 template upgrade + migration
036 · A7 Sentinel data-connector auto-import · A8 threat/region profiles ·
A9 XLSX Technique Tracker + PDF roadmap dedup · A10 device-level truth
(platform synonyms, per-stream guidance, coverage-by-log-source,
unmonitored-capability check) · A11 visual polish (header fills, template
border grid, executive PDF flow). All ☑ in the plan's status table.

### 3. Verification highlights (independent, per build session)
- **A1–A8:** all claims reproduced (suite, prod DB migration 036 columns,
  artifact counts). Deviation: A7's "adversarial sign-off" was a
  self-review — closed by running an independent Sonnet adversarial pass,
  which CONFIRMED one finding: attacker-controlled Sentinel connector
  `kind` was uncapped → could permanently break XLSX export via Excel's
  32,767-char cell limit. Fixed + regression test (`64b99e4`), deployed.
- **A9:** all claims reproduced; one leftover found (Read Me referencing
  the deleted Gaps sheet) → fixed (`3fd35f6`), deployed. Honest 116→114
  page result accepted; remaining page-count lever (compact P3/P4
  register mode) deliberately not built.
- **A10+A11:** all claims reproduced, zero defects. Template values proven
  byte-identical pre/post styling (initial mismatch was blank pre-formatted
  border rows + a bug in the verifier's own comparison script). Live
  template styling, PDF orphan-prevention CSS, and stay-unmapped IoT/z-OS
  pin all confirmed in code/prod.

### 4. Live-testing Q&A (Acme assessment, prod DB read-only queries)
- **"109 TTPs tagged but only 70 covered":** reconciled exactly — 152
  customer tag entries → 70 distinct technique IDs (duplicates + revoked
  remaps T1562→T1685 family); all 70 covered (100% hit rate). Not a bug.
- **"Unmapped asset entries":** explained Assets-sheet platform scoping vs
  Log-Sources feasibility credit; Photon/Infoblox/Rubrik misses became
  A10 piece 1; IoT/z-OS correctly stay unmapped (no honest ATT&CK
  platform) and are now regression-pinned.
- **"Device sends OS logs but not DNS logs":** coverage correctly refuses
  credit; the missing device-level story became A10 piece 4
  (unmonitored-capability check) — live in prod, both findings fired in
  the deploy smoke.
- **Navigator button:** explained (ATT&CK Navigator layer export for
  overlay/interop workflows).

### 5. Lessons for future sessions
- Build sessions may satisfy "adversarial sign-off" with a self-review —
  the orchestrator must check the verdict's provenance and re-run an
  independent pass for security-adjacent diffs.
- When verifying "byte-identical" claims on xlsx files, compare cell
  VALUES row-filtered correctly (cells vs values bug) and expect dimension
  growth from styled blank rows.
- The Acme sample (109 rules / 12-platform environment) is a good standing
  prod smoke target; test assessments should be archived after use.

## Agent utilization
- Opus/Fable (main): plan authoring, all verification passes, A7/A9 fixes, prod DB reconciliation, deploys
- Sonnet: 1 — independent adversarial review of A7 diff (verdict REVISE→fixed, finding confirmed real); build sessions ran separately per kickoff prompts
- Haiku: n/a — verification greps/queries were few and context-dependent
- codex:rescue: n/a — companion MCP outage per memory; Sonnet takeover pattern used
