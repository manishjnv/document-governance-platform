# Risk Remediation Plan

Eight items from the 2026-09-21 whole-project review, each with the evidence,
the fix, the acceptance test and the routing. Work the items top to bottom; each
is sized to one session or less and none depends on another unless stated.

Kickoff: `docs/phases/prompts/RISK_REMEDIATION_PROMPT.md`.

## §0 Status & changelog

| # | Risk | Severity | Status |
|---|---|---|---|
| R1 | Prod review model is unmeasured | High (product quality) | open |
| R2 | Legal severity calibration has no SME sign-off | High (trust), blocked on a person | open |
| R3 | `IMPLEMENTATION_PROGRESS.md` is stale and 1,500 lines | Medium | open |
| R4 | No migration runner; same bug four times | Medium (recurring) | open |
| R5 | MITRE exports render stale stored summaries (RCA #21) | Medium (client-facing) | open |
| R6 | `docs/planning/` sprawl breaks the single-reference rule | Low | open |
| R7 | Open verification items (click-through, Lighthouse) | Low | open |
| R8 | Two live URLs; move to scopesense.in only | Medium (owner decision 2026-09-21) | redirect live 2026-09-21, **reverted 2026-09-23** (office proxy blocks the new domain); redo ~2026-10-23 per cutover doc §4 |

- 2026-09-21: plan written. Nothing implemented yet.
- 2026-09-23: R8 reverted, dual-run resumed until ~2026-10-23.
- 2026-09-21: R8 executed same day: old host 301s every path to scopesense.in
  (detail and verification in `SCOPESENSE_DOMAIN_CUTOVER.md` §4).
- 2026-09-21: R8 added. Owner wants scopesense.in as the single URL now, not at
  the 2026-10-12 end of dual-run.

When an item ships: set its status here with the date and SHA, add the RCA entry
if it fixed a bug, and delete the item's detail section once nothing in it is
still needed.

---

## R1. Prod review model is unmeasured

**Evidence.** Prod api + worker have run `nvidia/nemotron-3.5-lightning:free`
since `8ae053b` (2026-09-12) because the paid OpenRouter key is at its $2 limit
(memory `reference_openrouter_key_identity`). The code default is still
`z-ai/glm-5.2` with a paid fallback chain (`apps/api/app/config.py:63-71`), and
every measured number we have is for that paid chain:
`docs/planning/ACCURACY_BASELINE_2026_07_22.md` (strict recall 21/29 = 72.4%,
lenient 86.2%, precision about 93%, 6/6 agents) and the model comparison in
`docs/planning/AI_MODEL_ROUTING.md`. Nothing has been measured on the free
model. RCA #14 shows a model swap has silently broken agents before.

**Also open from the launch criteria:** confidence calibration failed at 17.95%
error (2026-07-18), and the scored pass covers one document, not the 10 the
criteria ask for.

**Fix, in order. Stop as soon as one step answers the question.**

1. Measure, no code. Re-run the review of `SOC_SOW_Testing.docx` on prod (or
   locally with the VPS model env), save `GET /api/v1/reviews/{id}/results` to
   the scratchpad, run `python scripts/accuracy_harness.py <findings.json>`.
   Record: agents returning parseable JSON (n/6), strict recall vs 72.4%,
   finding count vs 73, wall time. The harness is a keyword approximation, so
   compare harness-to-harness: run it on the stored paid-chain review
   `0c40b7a6-2411-4618-a8b1-8eedf083b4e5` too for a like-for-like number.
2. Decide against a threshold set before looking: free model stays if 6/6 agents
   parse and strict recall is within 10 points of the paid chain on the same
   harness. Otherwise the owner chooses: top up the key and revert the VPS
   `.env` model vars, or try the next `:free` model and re-measure.
3. Append the result as a dated section to `ACCURACY_BASELINE_2026_07_22.md`
   (it is the accuracy reference; do not create a new doc) and one line to
   `AI_MODEL_ROUTING.md`.
4. Only if step 2 keeps the free model: make the prod model visible. Confirm
   `audit_meta` on a review records the model actually used; if it does not,
   add it there. No new table, no admin UI.

**Not in this item:** the 10-document real test set and the calibration fix.
Both need hand-built ground truth, which is owner time, not session time. They
stay in `5_LAUNCH_CRITERIA.md`.

**Acceptance.** A dated free-model row in the accuracy baseline with n/6 agents
and recall, and a recorded keep / revert decision.

**Routing.** Opus runs it (judgement on the comparison). No subagents. Never
send the document or prompts through the personal tooling key.

---

## R2. Legal severity calibration has no SME sign-off

**Evidence.** Severity is LLM-assigned with no external validation. The
worksheet exists (`docs/planning/LEGAL_SEVERITY_CALIBRATION.md`,
`scripts/severity_calibration_{run,ingest}.py`, `docs/planning/severity_calibration/`).
The blocker is a person, not code.

**Fix.**
1. Owner names a legal reviewer and a date. Without that, nothing here moves.
2. Session prep (30 min): regenerate the worksheet from current prod output with
   `severity_calibration_run.py` so the SME reviews today's model, not July's.
   Do this after R1, since R1 may change the model.
3. After the SME returns it: `severity_calibration_ingest.py`, then adjust the
   Legal agent prompt per `PROMPT_ENGINEERING_GUIDE.md` and regenerate
   `prompts/`.

**Interim mitigation (cheap, do now if not already present).** Check the results
page and the PDF/XLSX exports for a line saying severity is AI-assigned and not
legal advice. If any surface lacks it, add the one sentence. Grep first:
`/terms` may already cover it.

**Acceptance.** SME sign-off recorded in the calibration doc, or the interim
disclaimer confirmed on every surface that shows a severity.

---

## R3. `IMPLEMENTATION_PROGRESS.md` is stale and 1,500 lines

**Evidence.** Title still says "EDGP". "Current Phase" and "Next action" are
from 2026-07-20. "Next action" lists dedup as unbuilt (built 2026-07-20, stated
in the same file) and has two items numbered 3. At least five Done entries say
"uncommitted" or "NOT pushed" for work that shipped. The Done section is 1,400
lines of session narrative that already lives in the handoffs and module
references, which is the "fact in two docs" bug the project rule forbids.

**Fix.** Rewrite as an index, target 150 lines or fewer:

- Header: product name, live hosts, test baseline, latest migration number,
  last deploy SHA.
- One table, one row per feature area: status, one line, link to its living
  reference. Areas: SOW review engine, document lifecycle, auth, MITRE, Code
  Security Review, UI redesign, marketing + SEO, entitlements, infra + domain.
- Pending (true launch blockers only), Deferred by design, Next action
  (rewritten from this plan and the current open items).
- Drop the session narrative. Before deleting any entry, confirm the fact
  exists in a handoff under `docs/phases/summaries/` or a module reference. If
  it exists nowhere else, move it to the right reference first.

**Acceptance.** File is 150 lines or fewer, contains no "uncommitted" or "NOT
pushed", every link resolves, and `git diff --stat` shows no other doc lost
content.

**Routing.** Sonnet drafts from the contract above, Opus reviews the diff for
lost facts. Docs only, not load-bearing.

---

## R4. No migration runner; the same bug four times

**Evidence.** RCA #3, #11, #12, #13 are one bug: a migration not applied
everywhere. 40 plain `.sql` files in `apps/api/migrations/`, applied by hand to
four places plus the ORM `CheckConstraint` sync point (CLAUDE.md "Migrations").

**Fix. Smallest thing that removes the bug class; no Alembic.**

1. `scripts/migrate.py`, stdlib + the existing DB driver, about 60 lines:
   - creates `schema_migrations(filename text primary key, applied_at timestamptz)`
     if absent;
   - `--status` lists unapplied files; default applies them in filename order,
     each file in one transaction, recording the row on success;
   - `--baseline NNN` records files up to NNN as applied without running them,
     for the three databases that already have 001-040;
   - takes a DSN argument or env var, so the same script serves `edgp_dev`,
     `edgp_test` and `scopewise_prod` (on the VPS via `docker exec` into the api
     container).
2. Baseline all three databases at 040. Before baselining, verify 040 is really
   there (`\d organizations` shows `run_allowance`). Do not assume.
3. One test in the existing suite that fails when drift exists: every column
   named in an `ADD COLUMN` across `migrations/*.sql` for `documents` and
   `reviews` also appears in the hand-rolled `CREATE TABLE` strings in
   `apps/api/tests/test_insights_extra.py`. This covers sync point 4, which a
   runner cannot.
4. Add `python scripts/migrate.py` to the deploy loop in CLAUDE.md after
   `up -d`, and cut the Migrations section down to: run the script on each
   database, plus the two points it cannot cover (the hand-rolled test schema,
   now guarded by the test, and ORM `CheckConstraint` strings).

**Not in this item:** rollback / down migrations, checksums, a lock table. One
operator, one deploy at a time. Add a lock only if two deploys ever race.

**Acceptance.** `migrate.py --status` reports zero pending on all three
databases; a throwaway `041_test.sql` applies once and is skipped on the second
run (then removed); the drift test fails when a column is deleted from the
hand-rolled schema and passes when restored; full suite still 996 / 7.

**Routing.** Load-bearing (touches prod DB). Sonnet writes the script against
this contract in a worktree, Opus reviews the diff line by line, Sonnet
adversarial pass before it runs on prod (codex:rescue is down, memory
`project_codex_rescue_broken_2026_07_23`). Prod baseline only on an explicit
owner "go".

---

## R5. MITRE exports render stale stored summaries (RCA #21)

**Evidence.** The 2026-08-20 feasibility gate fixed the "Okta-based detection
for RDP" class in code, but exports render from the stored summary. Any
assessment run before the fix, including the client's, still exports the bad
recommendations until it is re-run (IMPLEMENTATION_PROGRESS ops note, RCA #21).

**Fix.**
1. Read-only query on prod: list assessments whose last run predates the fix
   deploy, with org and name. Expected count is small.
2. Owner decides which to re-run. Re-running spends LLM tokens and the client
   assessment needs the wizard inputs repeated (see the local memory
   on the client engagement, kept out of the repo).
3. Guard against the next occurrence only if step 1 shows more than a handful
   or this has happened twice: store the engine version on the summary at run
   time and show a "generated by an older engine, re-run before exporting"
   banner on the export buttons when it is older than the current one. Read
   `MITRE_MODULE_REFERENCE.md` first; check whether `audit_meta` / `GIT_SHA`
   already gives a usable version before adding a field.

**Acceptance.** List produced and each stale assessment either re-run or
explicitly accepted by the owner. Step 3 only if its condition is met.

---

## R6. `docs/planning/` sprawl

**Evidence.** Rule since 2026-09-12: one living reference per feature, built
plans merged and deleted. Still present beside `MITRE_MODULE_REFERENCE.md`:

| Doc | Lines | Self-declared status | Action |
|---|---|---|---|
| `MITRE_SIEM_INTEGRATION_PLAN.md` | 276 | SHIPPED | merge what the reference lacks, delete |
| `MITRE_TOOL_COVERAGE_PLAN.md` | 133 | shipped (memory says deployed) | merge, delete |
| `MITRE_UX_CLARITY_PLAN.md` | 442 | "approved-pending", but Phase 14 shipped | verify, merge, delete |
| `MITRE_ASSESSMENT_PLAN.md` | 593 | "not started", stale; CLAUDE.md cites it as design rationale | fix the status line, keep as rationale |
| `MITRE_ACCURACY_IMPROVEMENT_PLAN.md` | 676 | in progress | keep, it is live work |
| `HOMEPAGE_BRANDING_SEO_PLAN.md` | 272 | steps 1-6 of 8 done, rest shipped later | verify, fold the remainder into `SEO_STRATEGY.md`, delete |
| `PDF_REPORT_UPLIFT_PLAN.md` | 52 | none | check whether built; merge or keep |
| `SENTINEL_CONTENT_HUB_ADDON_PLAN.md` | 155 | planned, not started | keep |

Also stub to a pointer any completed kickoff prompt in `docs/phases/prompts/`
that still holds a full plan (check the MITRE phase prompts and
`PENDING_WORK_RUNBOOK_2026_09_12.md`).

**Fix.** One doc at a time: diff its facts against the reference, move what is
missing, delete the plan, fix inbound links
(`grep -rn "<FILENAME>" docs CLAUDE.md`). Never `git add docs/` wholesale
(customer-data incident 2026-08-19); add files by name.

**Acceptance.** No doc in `docs/planning/` claims a status that contradicts the
code; no broken links; each deleted doc's unique facts are findable in its
reference.

**Routing.** One Haiku per doc for the "which facts are missing from the
reference" sweep, Opus approves each merge. Do after R3 so the index links to
the final file set.

---

## R7. Open verification items

| Item | Due | How |
|---|---|---|
| Browser click-through: Projects / Versioning / Fix-verification, mandatory-project upload, Google + OTP login | any session | Chrome tools against prod, read-only paths plus one throwaway upload |
| Lighthouse + real-data screenshot pass after the UI redesign | any session | `UI_REDESIGN_BUILD_PLAN.md` §0 lists it as open |
| Blog `Person` author, per-CTA GA4 events | needs owner input (real name + title) | `SEO_STRATEGY.md` |
| Partner Center verification | external, in review | nothing to build |

---

## R8. Move to scopesense.in as the only URL

**Evidence.** Two hosts serve identical pages (`scopewise.assessiq.in`,
`scopesense.in`). Search signals already point at scopesense.in (2026-09-20),
but the old host still answers 200, so links, bookmarks, sign-in sessions and
any crawler that ignores the canonical are split across two origins. The old
name is also the retired product name.

**Fix.** The steps live in one place:
`docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md` §4 (pre-check, Caddy 301 keeping
path and query, verify, search-engine resubmit, tighten CORS / OAuth two weeks
later, code and doc references). Do not restate them here.

**The one real risk.** A user behind an office proxy that blocks the new domain
loses access entirely. §4 step 1 checks the old host's access log for real
traffic before the redirect goes in.

**Acceptance.** Old host 301s every path, including `/api/*`, to the same path
on scopesense.in; scopesense.in login (Google and OTP) works; one unrelated
tenant on the shared Caddy still returns 200; CLAUDE.md and the module
references name scopesense.in as the live URL.

**Routing.** Opus executes the Caddy change itself (shared-host file, RCA'd
inode trap, truncate-write only). Haiku runs the post-change curl grid. Doc
reference updates are one small commit. Needs an explicit owner "go" at the
Caddy step; it is a prod change on a host other projects share.

---

## Suggested session order

0. **R8:** redirect applied 2026-09-21, reverted 2026-09-23 (office proxy).
   Redo on or after 2026-10-23, then tighten two weeks later.
1. **Session A:** R1 (measure), then R5 step 1 (query). Both are read-mostly and
   both may produce an owner decision.
2. **Session B:** R4 (migration runner). The only code item; needs a full suite
   run, so keep the session solo on `edgp_test`.
3. **Session C:** R3 then R6 (docs), plus the R2 interim disclaimer check.

R2 proper starts when the owner has an SME and a date.
