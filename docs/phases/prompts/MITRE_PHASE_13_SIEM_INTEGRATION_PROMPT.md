# Kickoff prompt — MITRE Phase 13 (SIEM pull + scheduled re-assessment) — DESIGN FIRST

Self-contained kickoff. Paste everything below the line into a fresh
session (target model: Fable 5 main session). **This is a multi-session
sub-project, not a single build.** Session 1 is DESIGN ONLY (brainstorming
→ approved decomposed spec). Code starts only after the user approves the
design, and each build sub-phase is its own session + adversarial sign-off
+ deploy.

---

Plan and then implement **Phase 13** of the MITRE module: pull detection
rules directly from a customer SIEM and (optionally) re-run assessments on
a schedule so coverage trend updates automatically.

**START by invoking the `superpowers:brainstorming` skill.** Do NOT write
any code, migration, or connector in this first session — this feature
introduces genuinely new high-risk surfaces the module has never had, and
building any of them ad-hoc is the wrong move. The deliverable of session
1 is an approved, decomposed spec written to
`docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md`.

## Context

ScopeWise MITRE module Phases 0–12 are COMPLETE and live in prod
(HEAD `436612a`): deterministic coverage/gap engine + keyword pre-pass +
AI residue tagging + narrative + reviewer overrides + threat weighting +
detection-strength scoring, full `/api/v1/mitre` API + `/mitre` UI + PDF/
XLSX/Navigator exports + trend compare. ATT&CK v19.1. Backend baseline
**723 passed / 7 skipped**; `tsc` clean. Migrations 029–033 in all 3 DBs.
LLM key = SOW-audit key in app config / VPS `.env`; never judge budget
from `$OPENROUTER_API_KEY` ([[reference-openrouter-key-identity]]).

**What already exists that this builds on:** the ingest row contract
(name/description/logic/tags/status/log_source), the full assessment
pipeline, and the **trend/compare data model from Phase 4** — so an
auto-run just feeds an existing shape; you are NOT building trend storage.

## Why design-first (the hard surfaces — the brainstorming must resolve each)

1. **Customer SIEM credentials.** The module stores no third-party secrets
   today; this changes the threat model materially. Decide the credential
   model — the single biggest decision:
   - (a) **No storage** — customer pastes a token at trigger time; enables
     manual pull but NOT scheduling. Lowest risk, smallest surface.
   - (b) **Encrypted-at-rest** token/secret in the DB — enables scheduling
     but needs real key management: where does the encryption key live?
     (the VPS has no KMS; an env-var key on a shared host is the likely
     but imperfect answer — weigh it). Rotation, per-org isolation,
     least-privilege scopes.
   - (c) **OAuth / short-lived** where the platform supports it (Sentinel
     via an Entra service principal; Splunk token; Elastic API key).
   Recommend starting at (a) to ship value with near-zero secret-at-rest
   risk, then (b/c) only once (a) proves the pipeline.
2. **Which SIEM(s) first.** Splunk ES, Microsoft Sentinel, Elastic
   Security are the big three. v1 = ONE connector behind a clean
   interface. Pick it with the user (Sentinel and Splunk are the most
   common asks). Each has a different rule format to normalize to the
   ingest contract.
3. **Scheduler/worker.** `app/core/celery_app.py` exists but **no beat
   scheduler or worker runs in the standard VPS deploy** — scheduling
   needs that infra stood up: a new `scopewise-*` worker (and beat)
   container in `docker-compose.vps.yml` on a SHARED VPS. Per CLAUDE.md,
   check free ports / existing containers and keep strict `scopewise-*`
   isolation; never touch other projects' containers. Decide: Celery
   beat vs. a simpler in-container cron; resource limits.
4. **Egress / SSRF.** The app will make outbound calls to
   customer-supplied SIEM hostnames — a first-class SSRF surface (internal
   metadata endpoints, private/link-local ranges, redirect-based
   rebinding). This project has hit an SSRF TOCTOU before. Mandatory
   posture to design: scheme/port allowlist, deny RFC-1918/link-local/
   metadata IPs resolved AT connect time (not just parse time — TOCTOU),
   redirect limits, timeouts, response-size caps.
5. **Scope of "scheduled re-assessment."** Cadence, per-org config, dedup
   with manual runs, what feeds the existing trend/compare, and how a
   run's provenance (manual vs scheduled vs which connector) is recorded.
6. **Failure & observability.** Connector auth failure, partial pulls,
   credential expiry, rate limits — how they surface (assessment status,
   assumptions, an admin notification?), and never silently produce a
   misleading "0% coverage" from a failed pull.

## Proposed decomposition (the brainstorming refines/approves this)

Each sub-phase = its own session, own migration(s), own tests, own
adversarial sign-off (Sonnet takeover — codex:rescue down), own deploy.

- **13.0 — Design** (THIS session): brainstorm the six areas above →
  `docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md` + one kickoff prompt per
  sub-phase. Get user approval. No code.
- **13a — Connector framework + ONE connector, token-at-trigger (no
  storage, no scheduler).** A `app/mitre/connectors/` package with a base
  interface (`pull_rules(config, secret) -> [ingest rows]`) + one real
  connector; a `POST /assessments/from-siem` that takes connection config
  + a token IN THE REQUEST (never persisted), pulls read-only, normalizes
  to the ingest contract, and runs the existing pipeline. **Full SSRF
  defense here** (it's the first outbound call). Proves the whole path
  with zero secret at rest. Adversarial sign-off REQUIRED.
- **13b — Credential vault.** Encrypted-at-rest connection storage + key
  management + per-org isolation + scoping, so pulls run without
  re-entering the secret. **Highest-risk sub-phase — the heaviest
  adversarial review; consider asking the user for an extra pass.** Secrets
  NEVER logged, NEVER sent to the LLM, NEVER in reports/exports.
- **13c — Scheduler/worker infra.** Stand up the `scopewise-*` worker/beat
  container (or cron) in `docker-compose.vps.yml`; per-org schedule config;
  auto-run wiring; dedup with manual runs. Infra + shared-VPS change →
  sign-off + careful deploy.
- **13d — Auto-trend + observability.** Wire scheduled runs into the
  existing compare/trend; run provenance; failure surfacing/notifications.

## Standing rules (unchanged, apply to every sub-phase)

- Isolation: code stays under `apps/api/app/mitre/*` and
  `apps/web/app/mitre/*`; the only new shared-infra edit is the worker
  container in `docker-compose.vps.yml` (13c) — treat it with the
  CLAUDE.md shared-VPS caution. Never register anything in
  `ReviewOrchestrator.agents`.
- Migrations: apply every `.sql` to edgp_dev + edgp_test now, prod on
  deploy; if it ALTERs a CHECK also declared as an ORM `CheckConstraint`,
  update that too (5th sync-point).
- Coding-over-AI: connectors and normalization are plain code; no LLM in
  the pull path (the existing tagging pipeline handles mapping downstream).
- Tests: minimal-targeted; **run pytest SOLO** — one process per
  `edgp_test`, or a session-private clone
  ([[edgp-test-single-runner-rule]]). Don't regress 723/7; `tsc` clean.
- Security-adjacent throughout (credentials + egress) → adversarial
  sign-off before every push; log outcomes.
- Don't commit/push/deploy unless the user asks. One commit per logical
  unit. Deploy = standard VPS loop + migration to prod + smoke.

## Read first (this session)

Root `CLAUDE.md` (VPS/shared-host rules, migrations), `docs/planning/
MITRE_ASSESSMENT_PLAN.md` §14, `docs/planning/MITRE_MODULE_REFERENCE.md`
(current architecture), `app/core/celery_app.py` +
`app/tasks/document_tasks.py` (the one existing Celery task + its
per-call-engine pattern), `docker-compose.vps.yml`, and any existing
outbound-HTTP/SSRF handling in the repo (grep for how document/S3 fetches
guard URLs). Then run `superpowers:brainstorming` and produce the plan.

## How to run

Session 1: `Read docs/phases/prompts/MITRE_PHASE_13_SIEM_INTEGRATION_PROMPT.md
and run it — DESIGN ONLY this session (brainstorming → approved
MITRE_SIEM_INTEGRATION_PLAN.md + per-sub-phase kickoff prompts). MITRE
Phases 0-12 are live in prod; baseline 723/7. Write no code until I approve
the design.` Later sessions run the per-sub-phase prompts the design
produces, one at a time.
