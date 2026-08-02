# Session handoff — MITRE Phase 13 COMPLETE: 13c+13d shipped (2026-08-02)

**Headline:** Phase 13 (SIEM integration) is fully shipped. This session
built and deployed 13c (scheduler/worker) + 13d (provenance + failure
observability) as commit `496b2bb`, completing the 13.0→13d arc
(design `598c2dc`, 13a `09b545e`, 13b `a94aabb`). Final suite **781
passed / 7 skipped**; `tsc` clean. Every sub-phase carried its own
Sonnet adversarial sign-off; 13c and 13d were both REVISE→fixed→ACCEPT
with re-verification.

## State corrections made this session (worth knowing)

- 13c was believed deployed but was actually **uncommitted** in the
  working tree (its final certification run — 775/7 — arrived only this
  session). It shipped with 13d in `496b2bb`.
- **Prod's 13b vault was unconfigured**: `SIEM_CRED_KEY` never made it
  into the VPS `.env`/compose during the 13b deploy, so saved-connection
  endpoints were 503ing (clean failure by design). Fixed this deploy:
  the key is generated into `.env` (openssl rand, never committed) and
  mapped into both `api` and `worker` services.

## 13c — scheduler/worker (review: REVISE→fixed→ACCEPT)

`scopewise-worker` compose service (same API image; `celery -A
app.core.celery_app worker -B`, concurrency 2, **no ports**, 512m/0.5cpu,
least-privilege env — no JWT/OAuth, review fix). Migration 035 schedule
columns on `mitre_connections` (+3 ORM CheckConstraints in lockstep);
admin PATCH validates the cadence/hour/weekday trio as a unit. The
15-minute beat sweep: due-instant math is pure (`most_recent_due`),
`last_scheduled_at` advances exactly at enqueue (failed runs advance —
no storms; dedup-skips don't — slots retry), **stale `running` rows
(>30 min) are flipped to failed by the sweep itself** so a crashed
worker/deploy-restart can never block a schedule forever (review fix),
and `pending` previews never block. Every Celery task uses the
fresh-engine-per-call pattern (memory 18954); the pipeline gained an
optional `session_factory` param (API path unchanged). Scheduled
failures land as visible `failed` assessments with actionable messages.

## 13d — provenance + observability (review: REVISE→fixed→ACCEPT)

`params.siem` now surfaces: list-page chip ("Sentinel · auto"), results
header line (trigger/connection/workspace/pulled-at/rule-count), report
audit-footer source line (all `_esc`'d, non-secret fields only).
`GET /connections` returns per-connection `health` (last pull/status,
last error, consecutive scheduled-failure streak — manual pulls neither
count nor reset; math shared with the notifier via
`tasks.connection_health`). **Admin email fires at exactly 2 consecutive
scheduled failures** — storage-free once-per-streak semantics, reset on
success; the review's key catch: a sweep stale-flip that lands the
streak on 2 now notifies too (otherwise a routine deploy-restart could
consume the threshold silently). Emails carry connection metadata + the
static connector error only — never credentials, never rule content;
connection names are CRLF-collapsed (Subject-header hardening, review
minor). New `/mitre/connections` admin page: health table + Test button
(creation stays API-side this phase).

## Tests

18 new this session (10 schedule + 6 health/notification + 2 review
regressions), 781/7 final. Notable pins: notify at exactly 2 / once per
streak / reset-on-success / stale-flip-notifies; sweep
advance-and-dedup semantics; no secrets or rule content in emails;
CRLF name collapse; report-footer provenance secret-free.

## Deploy

`git push` → VPS loop with worker build → migrations 034 (idempotent
re-apply) + 035 to `scopewise_prod` → smoke. `SIEM_CRED_KEY` generated
into `.env` this deploy (32-byte base64). Worker ops notes live in
`MITRE_MODULE_REFERENCE.md` §14.

## Next

Phase 13 has no open sub-phases. Future optional work (reference §16):
Splunk ES / Elastic connectors (first customer-supplied hostnames — the
egress guard's full deny set finally gets real traffic), connections
CRUD UI, ICS/Mobile priority-file entries, per-org tier overrides.

## Agent utilization

- Opus (Fable, main): recon, 13c+13d implementation, docs, deploy — self-executed
- Sonnet: 13c adversarial review · REVISE→ACCEPT · reworked: Y (stale-block heal + worker env) ; 13d review · REVISE→ACCEPT · reworked: Y (stale-flip notify + CRLF names)
- Haiku: n/a — no bulk sweeps needed
- codex:rescue: n/a — companion outage; Sonnet takeover per standing fallback
