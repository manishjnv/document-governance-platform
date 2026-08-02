# Kickoff prompt — MITRE Phase 7 (persist detection-logic → better tagging, less AI)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session).

---

Close the one carried-over quality gap in the MITRE module: **the
detection-logic/query text is dropped when a dump has both a description
and a logic column**, so neither the keyword pre-pass nor the AI tagger
ever sees the actual rule condition in that (common) case. Persisting and
feeding the logic text improves tagging precision/recall AND increases
keyword matches (more literal tool/command strings live in the query),
which further reduces AI calls — directly serving the standing
coding-over-AI preference.

## Context

ScopeWise MITRE module Phases 0–6 are COMPLETE and live in prod
(2026-08-02, HEAD ≈ `68ade56`): deterministic coverage/gap engine, AI
tagging + a deterministic keyword/alias pre-pass (Phase 6), full API,
`/mitre` UI, PDF/XLSX reports, trend compare, ATT&CK v19.1. Baseline
**686 passed / 7 skipped**, `tsc` clean. Migrations 029–031 in all 3 DBs.
LLM key = SOW-audit key in app config / VPS `.env` (unlimited); never
judge budget from `$OPENROUTER_API_KEY`.

**The gap (verified in code):**
- `ingest.parse_use_case_file` already extracts a `logic` field per row.
- BUT `mitre_use_cases` has **no `logic` column**, and
  `router.create_assessment` stores
  `description = row["description"] or (row["logic"] or "")[:2000]` — so
  when a description exists, the logic is **discarded at create time**.
- `service.py`'s AI-tag stage passes `"logic": ""` to
  `agents.tag_untagged_rows`, and `keyword_tag_rows` receives no logic —
  both taggers effectively work from name + description only.

## Goal

Persist the detection logic and feed it to both taggers, without
regressing anything. Keep description and logic as distinct fields.

## Read first (one parallel burst), then state your plan

`app/mitre/ingest.py` (the row dict's `logic`), `app/mitre/router.py`
(`create_assessment` persistence + the logic-fallback line),
`app/mitre/service.py` (the `to_tag` dict build + keyword pre-pass call),
`app/mitre/keyword_tag.py` (already reads name/description/logic),
`app/models/mitre_use_case.py`, `app/mitre/report.py` (does the use-case
appendix surface description? if so, logic needs the same `_esc`
treatment when shown), root `CLAUDE.md` migrations rule.

## Deliverables

1. **Migration `032_mitre_use_case_logic.sql`** — idempotent,
   txn-wrapped, `ALTER TABLE mitre_use_cases ADD COLUMN IF NOT EXISTS
   logic TEXT`. Plain column (no CHECK) → the 5th ORM-sync-point rule
   doesn't apply, but still add the field to the model. Apply to
   edgp_dev + edgp_test now (prod on deploy). `mitre_use_cases` is NOT one
   of `test_insights_extra.py`'s 5 tables → no fixture edit.

2. **Model** — add `logic: Mapped[Optional[str]]` (Text, nullable) to
   `app/models/mitre_use_case.py`.

3. **Persist at create** (`router.create_assessment`): store
   `description` and `logic` **separately** (stop collapsing logic into
   description). Keep the `[:2000]` cap on logic (matches the Phase 6
   adversarial fix); keep description’s existing cap. The extraction
   (pdf/docx) path and customer-tagged rows keep working.

4. **Feed both taggers** (`service.py`): in the `to_tag` build, pass
   `"logic": uc.logic or ""` to `agents.tag_untagged_rows`, and make sure
   the keyword pre-pass receives name+description+logic for each row
   (it already matches across all three — just supply the real logic).

5. **Surface safely (only if already shown):** if the report use-case
   appendix or the results-page drawer displays description, add logic
   alongside it — HTML through `_esc`, XLSX through the existing `_guard`
   (logic is attacker-controlled and often contains `=`/quotes). If logic
   isn't surfaced in v1, skip the UI and just persist+feed it (note it).

## Tests (extend existing mitre test files)

- ingest→persist: a row with BOTH description and logic stores both
  (regression for the exact dropped-logic bug).
- keyword pre-pass fires on a tool string that appears ONLY in the logic
  column while description is present (would miss today).
- AI-tag stage receives non-empty logic (assert on the mocked agent's
  input).
- report/XLSX: a logic cell with a `=`/`<script>` payload is escaped/
  guarded if surfaced.
- Full suite stays green (≥ 686/7 + new); `tsc` clean if any UI touched.

## Acceptance (run, don't assume)

- `pytest tests/test_mitre_*.py -q` green; full suite ≥ 686/7 + new.
- Migration 032 applied to edgp_dev + edgp_test; `\d mitre_use_cases`
  shows `logic`.
- `git status`: only `app/mitre/*`, `app/models/mitre_use_case.py`,
  migration, mitre tests, (optional UI), session docs.
- Quick before/after on a dump that has both columns: show the keyword/AI
  split improves (more keyword matches, fewer AI) now that logic is seen.
- Low-risk change, but it feeds the classifier — a brief Sonnet
  adversarial pass before push (injection via the newly-persisted logic
  into prompts/reports; cap enforced) is sufficient; not the full
  ceremony.

## Wrap-up

Don't commit/push/deploy unless the user asks. Report the tagging
before/after, files, tests, deviations. Update
`docs/IMPLEMENTATION_PROGRESS.md` + handoff. Deploy = standard VPS loop +
migration 032 to `scopewise_prod` + smoke.

## After this, the MITRE module has NO known quality gaps.

Everything remaining is **optional feature work deferred by design**
(plan §14), to build only if the user asks — not blockers:
- interactive column-mapping wizard
- per-mapping AI-override UI (accept/reject/edit individual mappings)
- threat-informed weighting (actor/industry technique prioritization)
- ATT&CK Navigator layer JSON export
- scheduled/continuous re-assessment + SIEM API pull
- per-rule detection-quality scoring (v1 scores presence, not efficacy)
