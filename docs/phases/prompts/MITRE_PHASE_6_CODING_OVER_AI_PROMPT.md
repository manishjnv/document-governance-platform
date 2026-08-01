# Kickoff prompt — MITRE Phase 6 (coding/automation over AI)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session). Recommended fresh —
Task A changes coverage-affecting classifier logic and deserves its own
clean review context. Supersedes the earlier
`MITRE_PHASE_6_DETERMINISTIC_TAGGING_PROMPT.md` (which covered only
Task A).

---

Implement the **coding/automation-over-AI** improvements in the MITRE
module: replace or reduce LLM usage with deterministic code wherever code
matches the quality. **Standing rule: never lower deliverable quality to
avoid AI** — the bar is "can code match the quality?", not "can code
technically do it?". High precision beats coverage: for the tagger it is
always better to leave a rule for the AI than to mis-map it and inflate
coverage %.

## Context

ScopeWise MITRE module Phases 0–5 are COMPLETE and live in prod
(2026-08-02, HEAD ≈ `db98efb`): deterministic coverage/gap engine + AI
tagging/narrative + full `/api/v1/mitre` API + `/mitre` UI + PDF/XLSX
reports + trend compare, ATT&CK v19.1. Baseline **650 passed / 7
skipped**, `tsc` clean. Migrations 029 + 030 applied to all 3 DBs.

**LLM key note:** ScopeWise reads its OpenRouter key from
`settings.openrouter_api_key` (app config / VPS `.env`) — the SOW-audit
key, unlimited, healthy balance. Do NOT reason about the app's LLM budget
from `$OPENROUTER_API_KEY` / `~/.openrouter-key` (a separate personal
tooling key). AI tagging quality was verified 6/6 against the real key
on 2026-08-02.

**Where AI is used today, and the verdict on each (verified in code):**
| Path | Current | This phase |
| --- | --- | --- |
| Rules with explicit MITRE IDs | `service.build_mappings()` — pure, AI-free (customer_tagged skips AI) | Task D: keep; add a regression test if missing |
| Column/header + sheet + platform detection (`ingest.py`) | ALREADY pure synonym code (`_detect_columns`, `COLUMN_SYNONYMS`, `SHEET_SYNONYMS`, `_PLATFORM_RULES`) — **there is NO LLM fallback to remove** | Task B: widen the synonym/rule sets for robustness (pure code) |
| Log-source/tooling → ATT&CK data-source feasibility (`ranking.py`) | ALREADY pure keyword code (`_COMPONENT_CATEGORY_RULES`, `_LOG_SOURCE_RULES`, `_TOOLING_RULES`) — no AI | Task C: extend the maps; assert no AI path |
| Untagged-rule tagging (`agents.MitreTaggingAgent`, tagging mode) | ALL untagged rows go to the LLM | Task A: deterministic keyword/alias pre-pass; AI only for the residue |
| PDF/DOCX extraction; narrative prose | AI | OUT OF SCOPE — genuine AI-quality cases; leave as-is |

## Read first (one parallel burst), then state your plan

1. `app/mitre/service.py` (`build_mappings`, the run pipeline's tag/AI
   stages), `app/mitre/agents.py` (`tag_untagged_rows` + how it's called),
   `app/mitre/ingest.py` (`_detect_columns`, `COLUMN_SYNONYMS`,
   `SHEET_SYNONYMS`, `_PLATFORM_RULES`), `app/mitre/ranking.py` (the three
   keyword rule tables), `app/models/mitre_use_case.py` (the
   `mapping_status` CheckConstraint), `app/mitre/attack_data.py`
   (`resolve()`, technique names).
2. Root `CLAUDE.md` (migration 4-place rule + the 5th ORM-constraint
   sync-point added this session), `docs/planning/MITRE_ASSESSMENT_PLAN.md`
   §7, and `docs/planning/PROMPT_ENGINEERING_GUIDE.md` (do not edit LLM
   prompts here, but know where they live).

## Task A — deterministic keyword/alias tagging pre-pass (the main build)

Runs between tag-validation and AI-tagging: anything it confidently maps
skips the LLM; only the residue goes to `tag_untagged_rows`.

1. **`app/mitre/keyword_tag.py` (pure; no AI, no DB).**
   `keyword_tag_rows(rows, index=DEFAULT) -> {row_ref: [mapping,...]}`,
   each mapping `{technique_id, source:"keyword", confidence, rationale}`.
   HIGH-PRECISION signals only:
   - Exact ATT&CK technique / sub-technique **name** (from `attack.json`
     via `attack_data`) appearing as a whole phrase (word-boundary,
     case-insensitive) in the rule's name/description/logic — reuse the
     whole-word matching approach already in `ingest.py`/`ranking.py`
     (`_word_match`), do not substring-match ("cmd" inside "command" must
     NOT fire).
   - A curated **tool/command → technique** alias map in
     `app/mitre/data/keyword_aliases.json` — small, high-confidence, with
     a header note citing sources. Seed set (extend judiciously):
     mimikatz→T1003.001, `sekurlsa`→T1003.001, psexec→T1021.002,
     rundll32→T1218.011, regsvr32→T1218.010, mshta→T1218.005,
     certutil→T1105, bitsadmin→T1197, wmic→T1047, `schtasks`→T1053.005,
     `at.exe`→T1053.002, `vssadmin delete`→T1490, `wevtutil cl`→T1070.001,
     `-enc`/`encodedcommand`→T1059.001, `powershell`→T1059.001,
     `cmd.exe /c`→T1059.003, `net user`→T1136.001, `reg add`→T1112,
     `nltest`→T1482, `whoami`→T1033, `bcdedit`→T1490.
   - Validate EVERY emitted ID through `attack_data.resolve()` (remap
     revoked, drop invalid/deprecated). Dedup per row. Confidence = a
     fixed high value ≥ the covered threshold (e.g. 0.9) so matches count
     as coverage; `rationale` names exactly what matched.

2. **New `mapping_status = "keyword_tagged"`.** Requires, in lockstep
   (the CLAUDE.md 5-place migration rule + the 5th ORM sync-point):
   - Migration `031_mitre_keyword_tagged_status.sql` — idempotent,
     transaction-wrapped, drop+re-add the `ck_mitre_use_cases_mapping_status`
     CHECK adding `'keyword_tagged'`. Apply to edgp_dev + edgp_test now
     (prod on deploy).
   - Update the ORM `CheckConstraint` in `app/models/mitre_use_case.py` to
     match (else a `create_all`-bootstrapped DB 500s).
   - `service.py` summary `counts` gains `keyword_tagged`; results-page
     counts + technique drawer + `apps/web/app/mitre/lib.ts` get a source
     badge "Matched by rule" with a plain-English tooltip.

3. **Wire into `service.py`** before the AI-tag stage: run
   `keyword_tag_rows` over the `to_tag` set (rows with mapping_status
   `unmapped`/`invalid`); matched rows get `mappings` +
   `mapping_status="keyword_tagged"`; only STILL-unmapped rows go to
   `agents.tag_untagged_rows`. Add an assumption line ("N rules matched
   deterministically by rule/tool name; M sent to AI"). Preserve
   customer-tags-win and the AI degrade-to-unmapped behavior.

## Task B — widen ingest synonym/rule sets (pure code, no AI involved)

In `ingest.py`, broaden `COLUMN_SYNONYMS` (name/description/logic/tags/
status/log_source), `SHEET_SYNONYMS` (Assets/Log Sources/Tooling/Crown
Jewels), and `_PLATFORM_RULES` to cover more real-world SIEM export header
variants (e.g. tags: "att&ck id", "attack technique", "technique(s)",
"mitre_ttp"; log source: "index", "sourcetype", "data source",
"log_type"; status: "state", "is_enabled", "active"). Keep the template
escape hatch and the `IngestError` on a truly undetectable name column.
There is no LLM here to remove — this just reduces the "columns not
detected" friction so fewer files need the template. Add tests with
messy-but-real header rows.

## Task C — extend the feasibility keyword maps (pure code, no AI)

In `ranking.py`, broaden `_COMPONENT_CATEGORY_RULES`, `_LOG_SOURCE_RULES`,
and `_TOOLING_RULES` so more customer log-source/tooling names map onto
ATT&CK telemetry categories (more accurate short/mid/long bucketing).
Add a test asserting `ranking.py` imports no AI/agent module (guard
against future drift), plus golden cases for the new mappings.

## Task D — confirm explicit-MITRE-ID path stays code

`service.build_mappings()` already handles customer-tagged rules
deterministically (valid→customer_tagged, revoked→remap, invalid→noted).
No build needed; add a small regression test if one doesn't already
exist (valid + revoked + invalid tag in one row).

## Acceptance (run, don't assume)

- `pytest tests/test_mitre_*.py -q` green; full suite ≥ 650/7 (+ new).
- `tsc --noEmit` clean.
- Migration 031 applied to edgp_dev + edgp_test; ORM CheckConstraint
  updated to match; `\d mitre_use_cases` shows `keyword_tagged` allowed.
- **Quality gate (Task A):** on a seeded/real mixed dump, report the
  keyword-vs-AI split and hand-verify EVERY keyword mapping is correct
  (precision first); show the whole-word guard rejecting a near-miss.
- **Adversarial sign-off before push (Task A is coverage-affecting
  classifier logic):** Sonnet takeout (codex:rescue still down) — focus
  on false-positive mappings inflating coverage, the CHECK/ORM sync, and
  customer/AI/keyword provenance being preserved.
- `git status` clean after commits; only intended files touched.

## Wrap-up

Don't commit/push/deploy unless the user asks. Report per task: the
AI-call reduction on the test set (rows offloaded to keyword tagging vs
sent to AI), the quality spot-check, synonym/map additions, and
deviations. Update `docs/IMPLEMENTATION_PROGRESS.md` + the handoff.
Deploy = standard VPS loop + apply migration 031 to `scopewise_prod` +
smoke. This directly serves the standing coding-over-AI preference
recorded in memory.
