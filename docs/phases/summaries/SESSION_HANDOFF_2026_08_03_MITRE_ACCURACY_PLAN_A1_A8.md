# Session handoff — MITRE accuracy & template improvement plan, A1–A8 + deploy (2026-08-03)

**Headline:** ran all 8 phases of `docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md`
sequentially in one session, one commit per logical unit, then deployed to
prod. Full backend suite (solo on `edgp_test`): **858 passed / 7 skipped**
(+49 over the 809/7 pre-plan baseline). `tsc --noEmit` clean throughout.
Migration 036 applied to `edgp_dev` + `edgp_test` + `scopewise_prod`. Prod
deployed at **`31738e8`**, smoke-tested end to end (assessment creation →
run → PDF/XLSX download), all green. A7 (security-adjacent) carried a
mandatory adversarial self-review: **one blocking finding, fixed before
commit; verdict ACCEPT.**

## Per-phase result table

| Phase | Item | Code commit | Docs commit | Tests added | Reworked? |
| --- | --- | --- | --- | --- | --- |
| A1 | Fix consultant review prompt doc | `4e7c1b9` | (same commit, docs-only) | 0 (docs-only) | N |
| A2 | Sigma-based tagging accuracy benchmark | `e2c0764` | `edb4681` | 2 (`test_mitre_tagging_benchmark.py`) | N |
| A3 | Rule-vs-inventory telemetry cross-check | `08a8542` | `edb4681` | 8 (7 quality goldens + 1 E2E) | N |
| A4 | Crown Jewels → gap-ranking lift | `9bf3bfb` | `a58401c` | 8 (ranking goldens) | N |
| A5 | Keyword alias expansion | `300e41c` | `30c368f` | 5 (FP-regression pins) | **Y** — cut 3 drafted aliases (msiexec.exe/secretsdump/iodine) after the A2 benchmark showed them adding false positives with no offsetting true positive |
| A6 | Customer template upgrade + migration 036 | `bd55785` | `9388213` | 34 (ingest/quality/ranking goldens + real-template round-trip) | N |
| A7 | Sentinel data-connector auto-import | `0688efa` | `4ab0da0` | 8 (mapping/degrade/secrecy/malformed-entry/E2E) | **Y** — adversarial self-review caught a crash bug before commit (see verdict below), fixed in the same commit |
| A8 | Threat-profile expansion + region weighting | `f56f1a3` | `ce08282` | 8 (region lookup/word-boundary/no-op/dedup/lift goldens) | N |
| — | Post-A8 baseline + §5/§6/§7 reference update | `3802b7d` | — | — | — |
| — | A1–A8 completion summary | `31738e8` | — | — | — |

Total: 17 commits, `2121f23..31738e8`, pushed and deployed.

## A2 metrics (Sigma benchmark, keyword layer, 300 rules, seed 42)

Measured against the checked-in alias set at the time of A2 (before A5's
additions):

| Variant | Precision | Recall | F1 |
| --- | --- | --- | --- |
| Exact technique-id | 0.365 | 0.145 | 0.207 |
| Parent-level-credit | 0.465 | 0.184 | 0.264 |

Caveat documented in the script and tests: Sigma rules typically carry
only their primary technique tag, so this is a conservative floor on the
pre-pass's real precision, not an exact figure — some counted
"false positives" are plausible untagged matches.

## A5 metrics (keyword alias expansion, before → after, same 300-rule sample)

| Variant | Precision (before → after) | Recall (before → after) |
| --- | --- | --- |
| Exact | 0.365 → **0.366** | 0.145 → **0.150** |
| Parent-credit | 0.465 → **0.482** | 0.184 → **0.196** |

All four figures non-decreasing/up, satisfying the phase's acceptance
gate. 16 entries added (39→55); 3 originally-drafted entries
(`msiexec.exe`, `secretsdump`, `iodine`) were cut after the benchmark
showed each firing inside a broad multi-tool/multi-binary catch-all Sigma
rule with no offsetting true positive on this sample — removed rather
than kept at the cost of precision.

## A7 adversarial sign-off verdict: **ACCEPT** (after one revise→fixed cycle)

Scope: Sentinel connector's new best-effort read of
`Microsoft.SecurityInsights/dataConnectors` and the router wiring that
auto-populates `environment_lists.log_sources`.

Reviewed: egress-guard bypass (no new host/scope — verified
`dataConnectors` needs no permission beyond the already-required
`Microsoft Sentinel Reader` role, unlike the Log Analytics tables API),
secret handling (auth header reused by reference, never logged/returned —
regression-tested), DoS/resource caps (response size still capped by the
shared `fetch_json`, entry count capped at `MAX_CONNECTORS=500`), failure
isolation (two independent tests: HTTP failure and network exception,
both confirmed the rule pull and assessment creation proceed normally),
assumption-text trust boundary (kind values are the customer's own tenant
data, same trust level as already-pulled rule names, same escaping path),
and coverage across all 3 trigger paths (manual token, vault connection,
scheduled worker) via the shared `_create_assessment_from_pull`.

**Blocking finding (fixed before commit):** the per-entry mapping loop
(`for connector in connectors: (connector or {}).get("kind")`) would raise
an unhandled `AttributeError` on a non-dict, truthy entry (e.g. a bare
string) in the response's `value` array — this would have escaped the
narrow `except (EgressError, ConnectorError, KeyError)` handler and
propagated as an uncaught 500 through the router, defeating the explicit
contract that an inventory-pull failure must never fail the assessment.
**Fix:** wrapped the entire read+parse+map body in one broad
`except Exception` (logging only `type(exc).__name__`, never the
message — matching `egress.py`'s existing logging discipline) plus an
explicit `isinstance(connector, dict)` guard per entry. Regression test:
`test_data_connector_malformed_entries_degrade_not_crash`.

Non-blocking observations (documented, not fixed): the dataConnectors read
doesn't follow ARM pagination the way `alertRules` does (acceptable —
connector counts are typically small, and a partial import degrades
gracefully rather than producing wrong data); the connection dry-run
endpoint now makes the extra call even though it only surfaces
`rule_count` (a minor unnecessary API call, not a security issue).

## Deploy

- Pushed `2121f23..31738e8` to `origin/master`.
- VPS (`a11yos-vps`, `/opt/scopewise`): `git pull` (fast-forward, 37 files
  changed) → `docker compose -f docker-compose.vps.yml --env-file .env
  build` (all 3 images — api/worker/web — built clean) → `up -d`
  (api/worker/web recreated; redis/postgres untouched, already running).
  All 5 `scopewise-*` containers healthy within 30s. No other VPS
  container (`roadmap-*`, `assessiq-*`, `accessbridge-*`, `ti-platform-*`)
  touched.
- Migration 036 applied to `scopewise_prod` via
  `docker exec -i scopewise-postgres psql -U scopewise_user -d
  scopewise_prod` (piped, not `<` redirect — PowerShell incompatible):
  `BEGIN / ALTER TABLE / ALTER TABLE / COMMIT`, clean.

### Smoke test results (all pass)

- `GET /login` → 200, `GET /mitre` → 200, `GET /api/v1/health` → 200,
  unauthenticated `GET /api/v1/mitre/assessments` → 401 (correct).
- Full authenticated E2E (temporary `SMOKE-TEST-A1-A8` org/user created via
  the app's own DB session + `create_access_token`, since prod auth is
  Google/OTP-only with no password login path for scripted smoke tests;
  fully cleaned up — hard-deleted — afterward):
  - `POST /assessments` with a use-case dump carrying the new
    Severity/Last Triggered columns (plan phase A6) → 201; response
    `columns` correctly detected `severity`/`last_triggered` at their
    positions; parse preview clean, no warnings.
  - `POST /assessments/{id}/run` → assessment reached `status: completed`
    with an AI-generated narrative (confirms the LLM pipeline is healthy
    too).
  - **A3 telemetry cross-check assumption rendered exactly as designed:**
    *"T1078 is covered by rule 'Okta Impossible Travel', but its log
    source 'Okta' doesn't match anything in your Log Sources sheet —
    verify that telemetry is actually flowing."*
  - `GET .../report?format=pdf` → 200, base64 payload decodes to a valid
    PDF (`%PDF-1.7` magic bytes, 716 KB decoded).
  - `GET .../export.xlsx` → 200, valid "Microsoft Excel 2007+" file
    (174 KB).
  - Assessment soft-deleted via `DELETE`; temporary org/user/rows
    hard-deleted via a cleanup script. No residual test data left in
    `scopewise_prod`.

## Baselines updated

- `CLAUDE.md`: backend suite baseline **809→858 passed, 7 skipped**.
- `docs/planning/MITRE_MODULE_REFERENCE.md`: top-of-doc baseline updated
  to match; §4 (data model), §5 (ingest), §6 (deterministic engines), §7
  (tagging ladder), and §15 (build history) all updated with the A1–A8
  changes — see that doc for full technical detail on every phase.
- `docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md`: all 8 phases ticked
  ☑ in the Sequence & status table.
- `docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md`: new §2.2a documenting
  the A7 data-connector auto-import design decision (dataConnectors vs.
  tables API) and required permissions.

## Notes for the next session

- No phase needed the "skip-and-continue" escape hatch (A4/A5/A8 only,
  per the kickoff prompt) — all 8 phases completed as designed.
- A5's 3 cut aliases and A2/A5's Sigma-derived fixture caveat (ground
  truth is a precision floor, not an exact figure) are documented inline
  in `data/keyword_aliases.json`'s `_meta.notes` and
  `test_mitre_tagging_benchmark.py`'s docstring, respectively — read
  those before adding more aliases.
- `scripts/benchmark_tagging.py` caches its Sigma clone at
  `%TEMP%\sigma-bench-cache` (Windows) — delete that directory to force a
  fresh pull on the next benchmark run, or pass `--sigma-path` to point
  at a local clone.
- Optional/deferred by the plan itself: the "covered"→"has detection"
  relabel (needs a user decision, not a build session — flagged to raise
  once A6 shipped, which it now has).
- Still open, unrelated to this plan: Splunk/Elastic connectors,
  ICS/Mobile priority-tier entries, per-org priority-tier overrides (see
  `MITRE_MODULE_REFERENCE.md` §16).

## Agent utilization

- Single agent (Claude Sonnet 4.5) ran the entire plan end to end in one
  continuous session: all 8 phases' implementation, the A5
  benchmark-driven curation decisions, the A7 adversarial self-review
  (finding + fix before commit), the full post-A8 verification suite, and
  the production deploy + smoke test.
- Tests pass: Y (858/7 backend, `tsc --noEmit` clean).
- Open questions: none — plan fully executed as specified in the kickoff
  prompt, deploy authorized and completed.
