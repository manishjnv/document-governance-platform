# Session handoff — MITRE Phase 12: detection-strength scoring (2026-08-02)

**Headline:** Phase 12 (fifth optional MITRE feature, plan §14) built
coding-first, tested, signed off (ACCEPT), committed as `436612a`,
pushed, deployed to prod (no migration). Suite **723 passed / 7
skipped**; `tsc --noEmit` clean.

## What shipped

Coverage said whether a rule EXISTS; detection strength now estimates
how well it would actually detect — as a separate, clearly-labeled
signal that never touches the coverage %.

- **`app/mitre/quality.py`** (pure): per covered/partial technique with
  direct qualifying rules, best-rule score = provenance base
  (customer/manual 30, keyword 25, AI-high 20, AI-low 10) + enabled
  bonus (30/15/0 — disabled can never be "strong") + logic present (10)
  + telemetry match (30; log_source/logic capped at 2000 chars through
  ranking's category bridge vs the technique's data sources) +
  redundancy (5/extra rule, cap 10). Buckets strong ≥75 / moderate ≥45 /
  weak. Rationale = fixed fragments only. Parent-partial-via-sub
  entries deliberately unscored. Stored on `technique_results`
  (`strength`, `strength_rationale`) + `summary.quality` rollup.
- **Optional AI** (`MitreQualityAgent`, prompt documented in
  `PROMPT_ENGINEERING_GUIDE.md`): only heuristic-inconclusive items
  (logic present, expected telemetry known, no match), behind new org
  setting `quality_ai_enabled` **OFF by default**; 40-item/25-batch/
  500-char caps; outputs clamped 0-100, unknown IDs dropped, rationale
  capped 300 and prefixed "AI-assessed:"; any failure keeps the
  heuristic. Quality never depends on AI.
- **Recompute** (Phase 10 path) re-annotates heuristic-only after a
  manual mapping edit (prior AI ratings intentionally replaced — the
  mappings changed).
- **UI:** strength chip + rationale line in the technique drawer; a
  "Strength" column on gap rows (partial gaps have scores); tooltips
  explicitly state it is separate from the coverage %.
- PDF/XLSX deliberately unchanged this phase (report surface can adopt
  `summary.quality` later; reviewer confirmed nothing breaks from the
  additive keys).

## Heuristic goldens (pinned in `test_mitre_quality.py`)

Customer+enabled+logic+telemetry-match = 100; same rule disabled = 70
(moderate, by design); telemetry match raises 60→90; low-confidence AI
mapping = 40 (weak); redundancy bonus capped (+10); no-standard-
telemetry techniques cap at 70 with an honest rationale note; only
covered/partial with direct rules are scored; AI pass clamped
(150→100), unknown-ID filtered, garbage-response degrades to heuristic.

## Verification

Full suite **723 passed / 7 skipped** + `tsc` clean. **Sonnet review:
ACCEPT, 7/7 checks, zero findings** (coverage invariance verified via
diff + grep; flag gate strict-bool and default-off; AI output
clamping/filtering; capped scans on attacker-controlled text;
fixed-fragment rationales; recompute parity; old-assessment frontend
guards). Ops note: the reviewer ran pytest against shared `edgp_test`
concurrently with the main suite run — the single-runner rule applies
to subagents too; tell future reviewers not to run the full suite. The
final certification run came back 723/7 green regardless (interference
shows as spurious failures, never spurious passes).

## Deploy

Standard VPS loop; no migration. Prod at `436612a`; smoke green.

## Next

Only Phase 13 remains (SIEM API pull + scheduled re-assessment) —
DESIGN-FIRST: start with `superpowers:brainstorming`, per the kickoff.

## Agent utilization

- Opus (Fable, main): recon, heuristic design, implementation, docs, deploy — self-executed
- Sonnet: adversarial review of the Phase 12 diff · verdict=ACCEPT · reworked: N
- Haiku: n/a — no bulk sweeps needed
- codex:rescue: n/a — companion outage; Sonnet takeover per standing fallback
