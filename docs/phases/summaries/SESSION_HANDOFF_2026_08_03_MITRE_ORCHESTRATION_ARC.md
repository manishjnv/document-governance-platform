# Session handoff — MITRE module orchestration arc + scheduler fix

**Date:** 2026-08-03 (long multi-day orchestration conversation).
**Single source of truth for the module:** `docs/planning/MITRE_MODULE_REFERENCE.md`.

## Headline

This session drove the entire MITRE ATT&CK coverage-assessment feature from
design through production: wrote the design + every phase kickoff prompt,
independently verified each delegated build session's output against ground
truth (git / SSH / DB — not the report), committed and deployed each phase,
and directly fixed a production scheduler defect the delegated report had
missed. The module is live in prod through Phase 14i + a nav consolidation.

## Verified current state (checked this turn, not trusted from notes)

- **Local HEAD == prod HEAD == `8becf2b`**; `origin/master..HEAD` empty
  (all pushed); working tree clean.
- **All 5 `scopewise-*` containers up**; `scopewise-worker` **healthy**
  (the beat scheduler fix below is holding); postgres/redis stable.
- Migrations 029–035 in all three DBs (Phase 14 added none).

## What this session directly did (attestable)

- Designed the module (`MITRE_ASSESSMENT_PLAN.md`) and authored all phase
  kickoff prompts (0–13 sub-phases, optional 8–13, sample kit, Phase 13
  design-first).
- Verified + committed + deployed Phases 0–13 as delegated sessions
  produced them; caught two "done-but-broken" reports **before** trusting
  them: (1) a 56-min/112-error "full suite" that was `edgp_test`
  contention, not regressions; (2) the beat scheduler defect below.
- **Fixed the MITRE scheduler (commit `8cead2f`)** — see RCA.
- Corrected a wrong-key misdiagnosis (app uses the SOW-audit key, not the
  $2-capped personal tooling key — `reference-openrouter-key-identity`).

## RCA — MITRE scheduler never ran in prod (fixed `8cead2f`)

- **Symptom:** `scopewise-worker` showed `unhealthy`; the 15-min
  `mitre.schedule_sweep` never fired (no scheduled re-assessment).
- **Cause (two):** (1) `celery worker -B` wrote its beat schedule DB to
  the CWD `/app`, not writable by `appuser` → `_gdbm.error: Permission
  denied: celerybeat-schedule` → beat crashed on startup. (2) The worker
  service had no `healthcheck:` override, so it inherited the api image's
  `curl :8000/health` probe, which a worker (no HTTP server) can never
  pass.
- **Fix (`docker-compose.vps.yml` worker service):**
  `--schedule=/tmp/celerybeat-schedule` (writable; schedule is
  code-defined so an ephemeral file is fine) + a `celery inspect ping`
  healthcheck. Verified: worker healthy, beat starts clean, schedule file
  created.
- **Prevention:** a worker container must never inherit the api image's
  HTTP healthcheck; celery beat needs a writable `--schedule` path. Now in
  CLAUDE.md-adjacent memory.

## Shipped by OTHER sessions after my last verification — NOT re-verified here

Flagged honestly so the next session verifies before trusting:
- Phase 14h (report → Jinja templates + `report_xlsx.py` split, branding,
  xlsx polish, PDF metadata; Jinja2 pin hotfix `f7b5263` after an
  undeclared-dep prod crash-loop).
- Phase 14i (`telemetry_fields.json` "what logs do I need?" per gap).
- Nav consolidation (`9f6e091`…`8becf2b`: Documents/Upload/Search → "SOW
  Review"; `ts_headline` highlight rendering).
- **Suite baseline:** the Phase-14 sessions claim **809/7**; the last
  figure I personally certified was **765/7** (13b, on a private DB).
  14h/14i/nav not run in this session — reconfirm on a clean/private DB
  before relying on 809/7.

## Tests

Not run this turn. Last self-certified: 765/7 (13b). Reconfirm per the
`edgp-test-single-runner-rule` (private DB clone if any other session is
active — several times this week concurrent runs corrupted the signal).

## Open items / next actions

1. **`SIEM_CRED_KEY` is NOT set in the VPS `.env`** → saved SIEM
   connections 503 until provisioned (token-at-trigger + manual pulls work
   now). Generate 32-byte base64, add to `.env`, redeploy api+worker.
2. Independently verify 14h/14i/nav against ground truth + a clean suite
   (they shipped unverified-by-me).
3. Optional remaining module work: Splunk ES / Elastic connectors (first
   customer-hostname connectors — where the egress deny-set meets real
   traffic) and a connections-CRUD UI. Build only if asked.
4. Standing hazard: **serialize sessions** on this worktree/`edgp_test` —
   concurrent runs caused contaminated suites and one deploy-despite-ban
   incident this week.

## Agent-utilization footer

- **Opus/Fable (main):** all orchestration, design + prompt authoring,
  ground-truth verification of every delegated phase, commits, deploys,
  the beat-scheduler fix. Tier 0.
- **Sonnet:** per-phase adversarial sign-offs (REVISE→ACCEPT on 13a/13b
  and others) — codex:rescue down, Sonnet takeover per standing approval.
- **Haiku:** n/a.
- **codex:rescue:** n/a — companion broken (`codex-rescue-broken-2026-07-23`).
