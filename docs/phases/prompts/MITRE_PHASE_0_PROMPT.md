# Kickoff prompt — MITRE Assessment Phase 0 (data + pure logic)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session).

---

Implement **Phase 0** of the new MITRE ATT&CK coverage-assessment feature
for ScopeWise. This prompt carries the full context you need;
`docs/planning/MITRE_ASSESSMENT_PLAN.md` is the authoritative design if
anything here seems ambiguous — read it before deviating, and do not
re-litigate decisions recorded there.

## Product context

ScopeWise (this repo) is an AI SOW/RFP review platform: FastAPI backend
(`apps/api`), Next.js frontend (`apps/web`), live at
<https://scopewise.assessiq.in>. A brand-new, **fully isolated** module is
being added: **MITRE ATT&CK coverage assessment** — a customer uploads
their SIEM use-case/detection-rule dump (xlsx/xls/csv/pdf/docx, with or
without MITRE technique tags) plus a multi-sheet environment workbook
(assets/platforms, log sources, security tooling, crown jewels) and a slim
intake (industry/region, disabled-rules policy, scope exclusions with
reasons). They receive an executive + detailed gap assessment: coverage %
overall / per domain / per tactic / per technique, N/A-with-reason,
assumptions, exact per-gap recommendations, short/mid/long-term roadmap,
PDF + XLSX exports, and trend comparison between runs.

**Decisions locked with the user (2026-08-01):** all three ATT&CK domains
(Enterprise + ICS + Mobile; the environment workbook gates which apply);
applicability-filtered coverage denominator (impossible techniques become
N/A-with-reason and leave the denominator); in-app + PDF + XLSX outputs;
point-in-time runs with trend comparison.

**Design principle:** every number (percentages, states, N/A reasons) is
computed deterministically by pure Python against a pinned, bundled ATT&CK
dataset. LLMs (later phases, OpenRouter only) contribute only tagging of
untagged rules and narrative prose.

**Isolation contract:** the whole feature is a new `apps/api/app/mitre/`
package + new `mitre_*` tables + a new `/mitre` frontend section. Across
ALL phases only two shared files change (one router line in
`apps/api/main.py`, one nav entry in `apps/web/components/AppShell.tsx`) —
and **neither happens in Phase 0**. The existing review pipeline
(`app/parser.py`, `app/routers/*`, `app/ai/*`, `app/models/*`) is
load-bearing and must not be touched.

## The 6-phase roadmap (you are doing Phase 0 only)

- **Phase 0 (THIS): ATT&CK data build + pure applicability/coverage logic + unit tests.**
- Phase 1: migration 029, models, router/service skeleton, tagged-only end-to-end.
- Phase 2: LLM tagging + narrative agents (subclassing `ReviewAgent` like the existing `ConflictDetector` precedent).
- Phase 3: frontend pages + nav entry.
- Phase 4: PDF/XLSX reports + trend compare.
- Phase 5: adversarial sign-off, prod migration, VPS deploy.

## Read first (one parallel burst)

Root `CLAUDE.md` (auto-loaded — honor migrations rule, testing baselines,
commit policy), `docs/planning/MITRE_ASSESSMENT_PLAN.md` (§5 reference
data, §7 pipeline semantics, §12 testing, §13 acceptance), and skim
`docs/RCA_LOG.md` for testing gotchas. Then state your implementation plan
in a few lines and proceed.

## Phase 0 scope

Pure data + pure functions. **No DB, no migrations, no API endpoints, no
LLM calls, no frontend. Do not edit ANY pre-existing file.** Every
deliverable is a new file. Dependencies: stdlib + already-installed
packages only; nothing added to `requirements.txt`.

## Data contracts (Phase 1 will feed these shapes; freeze them now)

```python
# A normalized use case (one detection rule) as later phases will supply it:
{
  "row_ref": "sheet1:14",
  "name": "Suspicious PowerShell EncodedCommand",
  "enabled": True,          # None = unknown (treat as enabled + assumption)
  "mappings": [             # empty list = unmapped
    {"technique_id": "T1059.001", "source": "customer",  # or "ai"
     "confidence": 1.0}     # customer tags are 1.0; AI tags 0.0-1.0
  ],
}

# Environment (from the workbook + intake), as applicability input:
{
  "platforms": ["Windows", "Linux", "Azure AD", ...],  # ATT&CK platform strings
  "has_ics_assets": False,     # gates the ICS domain
  "has_managed_mobile": False, # gates the Mobile domain
  "inventory_provided": True,  # False => filter nothing, add loud assumption
  "exclusions": [              # customer-declared scope exclusions
    {"target": "T1200", "reason": "accepted risk, physical controls"},
    {"target": "mobile", "reason": "BYOD unmanaged, not SOC scope"},
    # target may be a technique id, a domain, or an ATT&CK platform string
  ],
}
```

## Deliverables

1. **`scripts/build_attack_data.py`** — dev-run script (never at runtime):
   downloads the MITRE `attack-stix-data` bundles (enterprise-attack,
   ics-attack, mobile-attack from
   github.com/mitre-attack/attack-stix-data), pinned to the newest
   published ATT&CK release at time of writing (record the version in the
   script header and the output), and compacts them to
   `apps/api/app/mitre/data/attack.json`:

   ```json
   {"version": "…", "generated_at": "…",
    "domains": {"enterprise|ics|mobile": {
      "tactics": [{"id": "TA0002", "shortname": "execution", "name": "Execution"}],
      "techniques": [{"id": "T1059.001", "name": "…", "tactics": ["TA0002"],
        "platforms": ["Windows"], "data_sources": ["…"],
        "is_subtechnique": true, "parent_id": "T1059",
        "deprecated": false, "revoked": false, "superseded_by": null,
        "summary": "first sentence of description"}]}}}
   ```

   Built-in validation: per-domain technique counts above a sanity floor
   (Enterprise ≫ ICS/Mobile), every revoked technique has `superseded_by`,
   every sub-technique has a valid `parent_id`.
2. **`apps/api/app/mitre/data/attack.json`** — generated once, checked in.
   The app must never fetch from the internet.
3. **`apps/api/app/mitre/data/technique_priorities.json`** — curated tier
   list of ~40 high-prevalence techniques (used later for gap ranking);
   cite sources in a header field (public threat reporting, e.g. Red
   Canary Threat Detection Report, CISA advisories). **Flag this file for
   a 10-minute user review** (plan §15 open question 3).
4. **`apps/api/app/mitre/__init__.py` + `attack_data.py`** — loads the
   pinned JSON once at module level; lookup helpers; technique-ID
   validation (regex `T\d{4}(\.\d{3})?`); revoked → `superseded_by`
   remapping; deprecated flagging.
5. **`apps/api/app/mitre/applicability.py`** — pure functions:
   environment dict → per-technique N/A decisions with reason strings.
   Rules (most specific reason wins): domain gating (`has_ics_assets`
   False → every ICS technique N/A "ICS matrix: no OT/ICS assets declared
   in inventory"; same for mobile); platform filtering (technique whose
   `platforms` don't intersect the environment's platforms → N/A naming
   the missing platform); customer exclusions (verbatim reason, attributed
   `customer-declared`); deprecated techniques → N/A "deprecated in ATT&CK
   vNN"; `inventory_provided` False → filter nothing except exclusions +
   return the loud assumption line ("no environment inventory provided —
   full matrices assumed applicable; coverage % is a lower bound").
6. **`apps/api/app/mitre/coverage.py`** — pure functions: use-case list +
   applicability result → per-technique states + rollups. Semantics:
   - States: `covered | partial | not_covered | not_applicable`.
   - `covered`: ≥1 enabled mapping with confidence ≥ 0.7.
   - `partial`: only disabled-rule mappings, or only 0.4–0.7-confidence
     mappings. (Disabled-counts-as-coverage policy flag defaults to No;
     accept it as a parameter now so Phase 1 can wire the org setting.)
   - Mappings < 0.4 confidence don't count at all (they become
     assumptions later).
   - Sub-technique rollup: a parent with no direct mapping but ≥1 covered
     sub-technique reports `partial` at parent level; both levels appear
     in results.
   - Multi-tactic techniques count in every tactic they belong to.
   - Headline coverage % = covered / applicable (strict); secondary
     weighted % credits partial at 0.5.
   - Rollups: overall, per-domain, per-tactic, plus the full per-technique
     result list `[{technique_id, domain, tactics, state, na_reason,
     use_case_refs}]`.
   - Inputs/outputs are plain dicts/lists — no ORM, no app imports beyond
     `attack_data`.
7. **Tests** (project taste: minimal targeted, base functionality, no
   bloat): `apps/api/tests/test_mitre_applicability.py` and
   `apps/api/tests/test_mitre_coverage.py` — domain gating, platform
   filter, exclusion attribution + most-specific-wins, no-inventory
   behavior, revoked remap, deprecated exclusion, malformed IDs,
   disabled/low-confidence → partial, the disabled-policy parameter,
   sub-technique rollup, multi-tactic counting, strict + weighted % golden
   cases.

## Acceptance (verify before claiming done)

- `cd apps/api && python -m pytest tests/test_mitre_applicability.py tests/test_mitre_coverage.py -q` — all green.
- Full suite still **402 passed, 2 skipped**. (Needs Docker Desktop +
  `edgp-postgres` up — 269 collection errors just means Docker is down;
  start it, don't debug.) Phase 0 touches no existing file, so any
  regression means the no-touch rule was broken — stop and fix.
- `build_attack_data.py` validation passes; per-domain counts printed.
- `git status` shows only new files; `requirements.txt` untouched.

## Wrap-up

Do NOT commit/push unless the user explicitly says so. Report: files
created, test output, attack.json version + per-domain counts, and present
`technique_priorities.json` for user review. Update
`docs/IMPLEMENTATION_PROGRESS.md`'s MITRE entry (Phase 0 done, Phase 1
next per `docs/planning/MITRE_ASSESSMENT_PLAN.md` §13) and add a session
handoff note in `docs/phases/summaries/` if the session did more than this
phase.
