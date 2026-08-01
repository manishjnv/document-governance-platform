# Kickoff prompt — MITRE Phase 6 (deterministic keyword-tagging pre-pass)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session). Recommended fresh —
this changes coverage-affecting classifier logic and deserves its own
clean review context.

---

Add a **deterministic keyword/alias tagging pre-pass** to the MITRE
module so the LLM tagger is only called for rules that deterministic
matching can't confidently map. This directly serves the standing
preference "prefer coding/automation over AI wherever quality is equal"
and reduces OpenRouter spend/cap pressure. Do NOT lower tagging quality
to save AI calls — the pre-pass must be HIGH-PRECISION (better to leave a
rule for the AI than to mis-map it and inflate coverage).

## Context

ScopeWise MITRE module Phases 0–5 are COMPLETE and live in prod
(2026-08-02, HEAD ≈ `f813f4c`). Deterministic coverage engine + AI
tagging/narrative + full API + `/mitre` UI + reports + trend, ATT&CK
v19.1. Baseline **650 passed / 7 skipped**, `tsc` clean. How tagging
works today (`app/mitre/service.py` pipeline + `app/mitre/agents.py`):
- Customer-tagged rows: validated deterministically, never sent to AI.
- Untagged/invalid rows: ALL sent to `MitreTaggingAgent` (LLM) in
  ~25-row batches. **This is the step this phase offloads.**
- Coverage math (`coverage.py`) reads each use case's `mappings`
  (`technique_id`/`source`/`confidence`) + `enabled` — NOT
  `mapping_status`. `mapping_status` drives only the summary counts
  (customer_tagged/ai_tagged/unmapped/invalid).

## Goal

Between tag-validation and AI-tagging, run a pure deterministic pass over
the still-unmapped rows. Anything it confidently maps skips the LLM;
only the residue goes to the AI tagger. Net effect: fewer AI calls, more
determinism, transparent provenance — same or better quality.

## Deliverables

1. **`app/mitre/keyword_tag.py` (pure, no AI, no DB).**
   `keyword_tag_rows(rows, index=DEFAULT) -> {row_ref: [mapping, ...]}`
   where each mapping is `{technique_id, source: "keyword", confidence,
   rationale}`. Matching signals, HIGH-PRECISION only:
   - Exact ATT&CK technique / sub-technique **name** or a curated alias
     appearing as a whole phrase (word-boundary, case-insensitive) in the
     rule's name/description/logic. Pull names from the pinned
     `attack.json` via `attack_data`.
   - A curated **tool/command → technique** alias map in
     `app/mitre/data/keyword_aliases.json` (e.g. mimikatz→T1003.001,
     psexec→T1021.002, rundll32→T1218.011, regsvr32→T1218.010,
     certutil→T1105, wmic→T1047, schtasks→T1053.005, vssadmin
     delete→T1490, "encoded command"/`-enc`→T1059.001, bitsadmin→T1197).
     Cite a source note in the file header; keep it small and
     high-confidence. Validate every ID through `attack_data.resolve()`.
   - Confidence: fixed high value (≥ the covered threshold, e.g. 0.9) so
     matches count as coverage; `rationale` names what matched. NEVER
     emit on a weak/substring match (no "cmd" inside "command", etc.).
   - Deduplicate technique IDs per row; a row may get multiple.

2. **New `mapping_status = "keyword_tagged"`** (so the summary counts and
   the UI drawer can distinguish it from AI/customer). This needs:
   - Migration `031_mitre_keyword_tagged_status.sql` extending the
     `mitre_use_cases.mapping_status` CHECK — **and** the matching ORM
     `CheckConstraint` if one exists on the model (the 5th-sync-point
     rule in CLAUDE.md — grep `app/models/mitre_use_case.py` for
     `CheckConstraint`; update both or a create_all-bootstrapped DB
     500s). Idempotent, txn-wrapped; apply to edgp_dev + edgp_test (+
     prod on deploy).
   - Update the summary counts in `service.py` (+`keyword_tagged`) and
     the results-page counts/drawer + `lib.ts` display metadata
     (source badge "Matched by rule" with a plain-English tooltip).

3. **Wire into `service.py`** before the AI-tag stage: run
   `keyword_tag_rows` on the unmapped/invalid rows; set matched rows to
   `mappings` + `mapping_status="keyword_tagged"`; only the STILL-unmapped
   rows go to `agents.tag_untagged_rows`. Add an assumption line ("N
   rules matched deterministically by rule/tool name; M sent to AI").
   Keep the customer-tags-win and AI-degrade behavior intact.

4. **Tests** (`test_mitre_keyword_tag.py` + extend `test_mitre_api.py`):
   exact-name match, alias match, whole-word guard (no substring false
   positives — the quality-critical test), revoked-alias remap, invalid
   alias rejected, dedup, and an E2E where a mix of keyword-matchable +
   AI-only rows routes correctly with AI mocked (assert the AI tagger is
   called only with the residue).

## Acceptance

- `pytest tests/test_mitre_*.py -q` green; full suite ≥ 650/7 (+ new).
- `tsc --noEmit` clean.
- Migration 031 applied to edgp_dev + edgp_test; ORM CheckConstraint
  updated to match.
- **Quality gate**: on a seeded/real dump, spot-check that every
  keyword mapping is correct (precision first) — report the
  keyword-vs-AI split and any near-misses the whole-word guard rejected.
- This is coverage-affecting classifier logic → **adversarial sign-off
  before push** (Sonnet takeout per the codex:rescue outage): focus on
  false-positive mappings inflating coverage, the new CHECK/ORM sync,
  and that customer/AI provenance is preserved.

## Wrap-up

Don't commit/push/deploy unless the user asks. Report the AI-call
reduction (rows offloaded to keyword tagging vs sent to AI on the test
set), quality spot-check, and deviations. Update
`IMPLEMENTATION_PROGRESS.md` and the handoff. Deploy = standard VPS loop
+ apply migration 031 to `scopewise_prod`.

Note (still open, external): the AI-tagging *quality* eyeball from
Phase 2/5 remains blocked on the OpenRouter daily cap — if the cap is
lifted by the time you run this, do that spot-check too (it pairs
naturally with this phase's keyword-vs-AI comparison).
