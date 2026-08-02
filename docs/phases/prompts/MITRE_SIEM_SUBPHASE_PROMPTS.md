# Kickoff prompts — MITRE Phase 13 build sub-phases (13a–13d)

Design is locked in `docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md` —
**read it first in every session; it is the contract.** Run ONE sub-phase
per session, in order (13a → 13b → 13c → 13d); each gets its own
migration(s), minimal-targeted tests, Sonnet adversarial sign-off
(codex:rescue is down), and deploy on the user's go. Paste the shared
context + the one sub-phase block.

---

## SHARED CONTEXT (paste with every sub-phase)

ScopeWise MITRE module Phases 0–12 are COMPLETE and live in prod.
Phase 13 design is APPROVED and locked in
`docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md` — read it plus
`docs/planning/MITRE_MODULE_REFERENCE.md` and root `CLAUDE.md` before
editing anything; state your plan first. Do not re-litigate design
decisions (Sentinel first; token-at-trigger before vault; CSV-artifact
reuse of the create path; worker+beat single container) — if
implementation reveals a design flaw, STOP and surface it instead of
improvising.

Standing rules: isolation under `apps/api/app/mitre/*` +
`apps/web/app/mitre/*` (sole exception: 13c's `docker-compose.vps.yml`
worker container — shared-VPS caution per CLAUDE.md); never register
anything in `ReviewOrchestrator`; migrations → edgp_dev + edgp_test now
+ prod on deploy, ORM CheckConstraint lockstep (5th sync point); no LLM
anywhere in the pull path; secrets NEVER logged / echoed / sent to the
LLM / in reports, exports, or audit details; pytest SOLO (single-runner
rule — and tell review subagents NOT to run the suite); don't regress
the suite or `tsc`; adversarial sign-off BEFORE push; don't
commit/push/deploy unless the user asks.

---

## 13a — Connector framework + Sentinel, token-at-trigger (NO storage)

Build per plan §2.2/§2.4/§4: `app/mitre/connectors/` (base dispatch +
`egress.py` resolve-pin SSRF guard + `sentinel.py`), and
`POST /api/v1/mitre/assessments/from-siem` (admin/reviewer) where the
client secret lives ONLY in the request. Connector output is a canonical
template CSV fed through the EXISTING create internals (parse preview,
tag validation, stored artifact — all free). Provenance in
`params.siem` (`trigger: "manual"`). Frontend: "Pull from SIEM" entry in
the `/mitre/new` wizard (config fields + secret field marked
never-stored; result = the normal preview screen). No migration.

Egress guard is the load-bearing piece — build it exactly to plan §2.4
(https/443 only, resolve-then-pin with the full deny set, redirects
rejected, caps, secret-free errors) even though Sentinel's hosts are
fixed Microsoft domains.

Tests per plan §5 (no network ever): deny-set table + rebinding
fake-resolver, normalization goldens from a checked-in Sentinel-rule
fixture, endpoint E2E with faked transport, secret-non-persistence scan,
RBAC/org, empty-workspace error. **Review: REQUIRED (Sonnet)** — SSRF
completeness, secret handling, org scoping, caps.

## 13b — Credential vault (encrypted connections)

**Highest-risk sub-phase — heaviest review; offer the user an extra
review pass.** Build per plan §2.1: migration 034 `mitre_connections`
(org-scoped, soft-delete; non-secret `config` JSONB;
`secret_ciphertext` AES-256-GCM via `cryptography`; `key_version`;
master key from `SIEM_CRED_KEY` env — document the shared-VPS
limitation in-code). Connections CRUD (admin only; secret write-only,
never returned) + `POST /connections/{id}/test` (dry-run rule count) +
`POST /assessments/from-connection/{id}` (admin/reviewer). Decrypt only
inside the connector call; add the log-scrubbing test. VPS `.env` gains
`SIEM_CRED_KEY` at deploy (generate 32-byte base64; never commit it).

## 13c — Scheduler/worker infra

Build per plan §2.3/§2.5: `scopewise-worker` container in
`docker-compose.vps.yml` (same API image, `celery -A app.core.celery_app
worker -B`, no ports, mem/cpu limits — check `docker ps` + `ss -tlnp`
on the VPS first, touch nothing non-`scopewise-*`). Migration 035:
schedule columns on `mitre_connections` (`schedule_cadence`,
`schedule_hour_utc`, `schedule_weekday`, `last_scheduled_at`) +
admin PATCH. One beat sweep every 15 min → due connections → pull+run
task using the per-call-engine pattern from
`app/tasks/document_tasks.py` (memory 18954: the global engine binds to
the first loop — give the pipeline an optional session-factory param;
API path unchanged). Dedup per plan §2.3. Scheduled-run failures land
as `failed` assessments (plan §2.6), `trigger: "scheduled"` provenance.

## 13d — Provenance surfacing + failure observability

Build per plan §2.5/§2.6: list-page provenance chip + results-header
line + report audit-footer entry from `params.siem`; admin
connection-health view (last pull, last error, streak); email the org's
admins after 2 consecutive scheduled failures (existing SMTP config;
one notice per streak, reset on success — no notification storms; no
secrets or rule content in emails). No migration expected.
