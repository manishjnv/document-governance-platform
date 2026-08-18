# MITRE Phase 13 — SIEM Integration Plan (design locked 2026-08-02)

**Status: SHIPPED — all four sub-phases (13a–13d) implemented, each with
its own adversarial sign-off; see §15 of `MITRE_MODULE_REFERENCE.md` for
commits.** This document remains the design contract of record.
Design session ran `superpowers:brainstorming` per the kickoff
(`docs/phases/prompts/MITRE_PHASE_13_SIEM_INTEGRATION_PROMPT.md`).
User decisions taken this session: **first connector = Microsoft
Sentinel**; **credential model v1 = token-at-trigger (no storage)**.
Build sub-phases run one per session from
`docs/phases/prompts/MITRE_SIEM_SUBPHASE_PROMPTS.md`, each with its own
migration(s), tests, Sonnet adversarial sign-off, and deploy.

## 1. Goal and non-goals

Pull detection rules straight from a customer SIEM into the existing
MITRE assessment pipeline, and (later) re-run assessments on a schedule
so the existing trend/compare fills in automatically.

Non-goals: writing anything back to the SIEM (read-only forever);
real-time/streaming sync; building trend storage (Phase 4's compare
model already exists and just gets fed); any LLM in the pull path
(coding-over-AI — mapping happens downstream in the existing tagging
ladder).

## 2. The six design decisions (resolved)

### 2.1 Credential model — staged, token-at-trigger first

- **13a ships with NO secret at rest.** `POST /assessments/from-siem`
  carries the client secret in the request body, uses it once in-process,
  and never persists, logs, or echoes it. This proves the entire
  pull→normalize→assess path with near-zero new secret risk.
- **13b adds the encrypted vault** only after 13a is proven: per-org
  `mitre_connections` rows with AES-256-GCM-encrypted secrets
  (`cryptography` lib), master key from a VPS env var
  (`SIEM_CRED_KEY`, 32-byte base64). **Acknowledged limitation:** the
  shared VPS has no KMS; an env-var master key means a host/root
  compromise exposes secrets. Mitigations: `key_version` column +
  re-encryption path for rotation; secrets write-only through the API
  (never returned, PATCH replaces); decrypt only inside the connector
  call; guidance to customers to grant least-privilege, revocable,
  read-only credentials (for Sentinel: a service principal with ONLY
  `Microsoft Sentinel Reader`). Scheduling (13c) requires 13b.

### 2.2 First connector — Microsoft Sentinel

Chosen by the user (most-requested; cleanest fit for no-secret-at-rest):

- Auth: Entra **client-credentials** flow — customer supplies tenant_id,
  client_id, client_secret; we exchange for a short-lived bearer token at
  `login.microsoftonline.com` (fixed host).
- Pull: Azure Management API `Microsoft.SecurityInsights/alertRules`
  under `management.azure.com` (fixed host) for the customer's
  subscription/resource-group/workspace (IDs, regex-validated).
- **Key security property: v1 never connects to a customer-supplied
  hostname.** Both endpoints are fixed Microsoft domains; the customer
  only supplies identifiers. The egress guard (2.4) is still built in
  13a because later connectors (Splunk/Elastic) take real hostnames.
- Normalization to the ingest row contract: displayName→name,
  description→description, query (KQL)→logic, enabled→enabled,
  techniques[]→tags (Sentinel carries ATT&CK technique IDs natively;
  sub-techniques appear where set; IDs go through the existing
  `build_mappings`/`resolve()` validation exactly like customer tags),
  log_source = "Microsoft Sentinel · <rule kind>". Fusion/anomaly rules
  without queries keep empty logic (scored accordingly by Phase 12).
- **Delivery form: the connector emits a canonical template CSV**
  (stdlib csv, template headers) which is then fed through the EXISTING
  create path (`ingest.parse_use_case_file` → `_build_use_case_rows` →
  same preview/rows/files as an upload). This buys, for free: tag
  validation, parse preview, row caps, the stored-artifact download, and
  compatibility with every downstream feature. The stored file is the
  audit artifact of what was pulled. Remap stays available (it's a real
  CSV); pdf/docx-style special cases don't apply.
- Caps: existing `MAX_USE_CASE_ROWS` (5,000) enforced during pull
  (stop + warn, not error); pagination capped (50 pages); per-page and
  total response-size caps.

### 2.2a Data-connector auto-import (plan phase A7, 2026-08-03)

Extends the pull with ONE additional read so Sentinel customers can skip
the manual Log Sources sheet — accuracy-plan phase A7, tracked in
`MITRE_ACCURACY_IMPROVEMENT_PLAN.md`.

- **API chosen: `Microsoft.SecurityInsights/dataConnectors` (ARM list),
  NOT the Log Analytics workspace "tables" API.** Both live under
  `management.azure.com` (already allowlisted) and both are reachable
  with the bearer token already obtained for the alertRules pull, but
  they require DIFFERENT Azure RBAC permissions: the tables API needs
  `Microsoft.OperationalInsights/workspaces/tables/read`, which the
  documented `Microsoft Sentinel Reader` role (§2.1) does **not**
  grant; `dataConnectors` is under `Microsoft.SecurityInsights/*`, the
  SAME resource provider as `alertRules`, so it IS covered by the role
  customers are already asked to grant. **This feature requires no new
  customer-side permission and no change to onboarding guidance.**
- No new host, no new egress capability, no new token scope — same
  `ALLOWED_HOSTS`, same bearer token, same `fetch_json` guard.
- Mapping: a curated in-code table (`sentinel._DATA_CONNECTOR_KIND_TO_SOURCE`)
  maps Microsoft's built-in data-connector `kind` values (e.g.
  `AzureActiveDirectory`, `MicrosoftDefenderAdvancedThreatProtection`,
  `Office365`, `AmazonWebServicesCloudTrail`) to source NAME STRINGS the
  module's EXISTING log-source keyword bridge (`ranking._LOG_SOURCE_RULES`)
  already recognizes (e.g. "Azure AD", "Microsoft Defender") — no new
  taxonomy invented. A `kind` absent from the table is reported in an
  assumption line, never silently dropped.
- Failure isolation: the data-connector read is wrapped so ANY failure
  (auth, network, unexpected shape) degrades to `[]` + one warning —
  it NEVER fails the rule pull or the assessment.
- Merge semantics: when the read yields ≥1 mapped source, the
  assessment's `environment_lists.log_sources` is auto-populated
  (`sheets_found.log_sources` marked "auto-imported") and `params.siem`
  notes the count; `environment.inventory_provided` (the Assets/platform
  flag) stays `False` — no platforms are derived, so the "coverage is a
  lower bound" assumption stays honest. There is currently no
  environment-workbook upload path on `/assessments/from-siem` or
  `/assessments/from-connection/{id}` (JSON-body endpoints only), so
  "explicit beats derived" has nothing to merge under today; the
  precedence rule is documented for when/if that changes.
- Adversarial sign-off: ACCEPT (see `docs/phases/summaries/` for the
  session handoff recording the review).

### 2.3 Scheduler/worker — Celery worker+beat container (13c)

- One new container `scopewise-worker` in `docker-compose.vps.yml`:
  same API image, command `celery -A app.core.celery_app worker -B
  --loglevel=info`, **no published ports**, `scopewise-net` only,
  resource-limited (`mem_limit: 512m`, `cpus: "0.5"`), standard
  shared-VPS caution (check `docker ps`/`ss -tlnp` before deploy; touch
  nothing non-`scopewise-*`).
- Celery beat (in-process `-B`, no separate beat container — one worker
  is enough at this scale) runs ONE periodic sweep every 15 minutes:
  find due schedules → enqueue one pull-and-run task per due connection.
- Schedule config lives ON `mitre_connections` (no extra table — YAGNI):
  `schedule_cadence` (`null|daily|weekly`), `schedule_hour_utc`,
  `schedule_weekday`, `last_scheduled_at`. Admin-only PATCH.
- Dedup: a due schedule is skipped (with a logged reason) if that
  connection already has a pending/running assessment, or if
  `last_scheduled_at` is inside the cadence window.
- **Known hazard to handle in 13c (memory 18954):** the app-wide async
  engine binds to the first event loop; Celery tasks calling
  `asyncio.run()` must use the per-call-engine pattern from
  `app/tasks/document_tasks.py` (fresh engine + dispose per task) for
  BOTH the pull and the pipeline run. The pipeline body gets an optional
  session-factory parameter for this; API-path behavior unchanged.

### 2.4 Egress / SSRF posture (built in 13a, shared by all connectors)

New `app/mitre/connectors/egress.py`, the only outbound-HTTP door for
connector code:

- **https only**, port 443 only (per-connector allowlists are explicit
  constants, never config).
- **Resolve-then-pin:** resolve the hostname once, validate EVERY
  resolved address against the deny set — RFC-1918, loopback, link-local
  `169.254.0.0/16` (incl. the cloud metadata IP), CGNAT `100.64.0.0/10`,
  reserved/multicast, `::1`, `fc00::/7`, `fe80::/10`, v4-mapped v6 —
  then **connect to the validated IP** (host header/SNI set to the
  original name). Rejecting at connect time, not parse time, closes the
  DNS-rebinding TOCTOU this project has been bitten by before.
- **Redirects disabled entirely** (the Microsoft APIs don't need them; a
  redirect is treated as an error).
- Timeouts (connect 10s / total 60s per request), response-size cap
  (20 MB per response), page cap, no retries on 4xx, bounded retries
  with backoff on 429/5xx.
- Secrets never appear in URLs, logs, or error strings (auth via
  headers; exception messages scrubbed).
- Everything above unit-tested with a fake transport/resolver — **tests
  make no real network calls**.

### 2.5 Scheduled re-assessment semantics (13c/13d)

- Cadence: daily or weekly per connection, admin-configured, off by
  default. 15-min sweep granularity is deliberate — this is trend data,
  not alerting.
- Every run (manual pull or scheduled) records provenance in
  `params.siem`: `{platform, workspace ref, connection_id?, trigger:
  "manual"|"scheduled", pulled_at, rule_count, connector_version}` — and
  shows in the UI (list-page chip + results header) and report audit
  footer.
- Scheduled runs create ordinary assessments; the existing Phase 4
  compare/trend picks them up with zero new storage. The list page's
  existing trend arrow covers "coverage trend updates automatically";
  13d adds nothing fancier unless asked.

### 2.6 Failure & observability

- **A failed or empty pull NEVER produces a misleading assessment.**
  Auth/network/parse failure → no assessment row at all for manual pulls
  (4xx/5xx with an actionable message: bad credentials vs missing role
  vs unreachable vs rate-limited); for scheduled runs → a `failed`
  assessment row with plain-English `error_message` so the failure is
  visible in the UI, and `last_scheduled_at` still advances (no retry
  storms). A pull returning 0 rules is an explicit error ("the service
  principal can see the workspace but it contains no analytics rules —
  check the workspace reference"), never a 0%-coverage run.
- Scheduled-failure notification (13d): after 2 consecutive failures for
  a connection, email the org's admins via the existing SMTP config;
  one notice per failure streak, reset on success.
- Rate limits: respect 429 Retry-After with bounded backoff; give up
  cleanly into the failure path above.

## 3. Sub-phase decomposition (each = own session + sign-off + deploy)

| Sub-phase | Delivers | Migrations | Risk focus of the adversarial review |
| --- | --- | --- | --- |
| **13a** | `app/mitre/connectors/` (base interface + `egress.py` + `sentinel.py`), `POST /assessments/from-siem` (token-at-trigger), CSV-artifact reuse of the create path, provenance `params.siem`, wizard "Pull from SIEM" tab | none | SSRF guard correctness (rebinding, deny-set completeness), secret-never-persisted/logged, org scoping, caps |
| **13b** | `mitre_connections` vault (AES-256-GCM, env master key, key_version), connections CRUD + test endpoint, `POST /assessments/from-connection/{id}` | 034 (mitre_connections) | **Heaviest review**; secret handling end-to-end (write-only, decrypt scope, log/LLM/report exclusion), crypto choices, rotation path — consider an extra review pass |
| **13c** | `scopewise-worker` container (worker+beat), schedule columns + sweep task, per-call-engine task wrappers, dedup | 035 (schedule columns) | Shared-VPS deploy safety, event-loop/engine correctness, dedup races, resource limits |
| **13d** | Provenance surfacing (list chip, results header, report footer), failure notifications, connection-health admin view | none | Notification abuse/noise, no secret leakage into UI/emails |

Standing rules for every sub-phase: isolation under `apps/api/app/mitre/*`
+ `apps/web/app/mitre/*` (sole exception: the 13c compose edit); nothing
registered in `ReviewOrchestrator`; migrations to all DBs + ORM
CheckConstraint lockstep; minimal-targeted tests, pytest run SOLO
(single-runner rule — applies to review subagents too); no LLM in the
pull path; Sonnet adversarial sign-off before every push; don't
commit/push/deploy without the user's go.

## 4. Interfaces (contract sketch, 13a)

```text
app/mitre/connectors/base.py
    ConnectorError(user_message)            # actionable, secret-free
    PullResult = {csv_bytes, rule_count, warnings: [str], stats: {...}}
    pull_rules(platform: str, config: dict, secret: str) -> PullResult
        # dispatches to the platform module; validates config shape first

app/mitre/connectors/egress.py
    guarded_client(allowed_hosts: set[str]) -> httpx.Client
        # resolve-pin transport, https/443 only, no redirects, caps

app/mitre/connectors/sentinel.py
    CONFIG_FIELDS = tenant_id, client_id, subscription_id,
                    resource_group, workspace  (each regex-validated)
    ALLOWED_HOSTS = {login.microsoftonline.com, management.azure.com}
    pull(config, secret) -> PullResult      # token -> list rules -> CSV

POST /api/v1/mitre/assessments/from-siem   (admin, reviewer)
    body: {platform: "sentinel", config: {...}, secret: "...",
           name?, intake?}                  # secret used once, discarded
    -> the existing create-assessment response (parse preview), with
       params.siem provenance; 422 config/regex errors; 502-style
       ConnectorError messages for upstream failures
```

## 5. Test strategy

- 13a: egress unit tests (deny-set table incl. rebinding fake-resolver
  case, scheme/port, redirect rejection, size cap); Sentinel
  normalization goldens from a checked-in fixture of real-shaped rule
  JSON (incl. technique tags, disabled rules, query-less Fusion rules);
  endpoint E2E with a faked transport (secret non-persistence asserted
  by scanning the stored assessment/params/files; cross-org/RBAC; empty
  workspace → error). No test touches the network.
- 13b: crypto round-trip + key_version, secret-never-returned API tests,
  log-scrubbing test, org isolation on connections.
- 13c: sweep dedup unit tests, due-schedule math, per-call-engine task
  smoke (in-process call like `test_tasks.py` does today).
- 13d: notification trigger/reset logic, provenance rendering.

## 6. Open items deliberately deferred

- ~~Splunk ES~~ / Elastic connectors: after 13a proves the interface
  (each is its own session; Splunk introduces the first customer-supplied
  hostname → the egress guard's full deny-set gets its first real use).
  **Splunk shipped 2026-08-18** (`connectors/splunk.py`): saved-searches
  pull, Bearer token, strict FQDN config + egress deny set, port limited
  to 8089/443 (egress `ALLOWED_PORTS` — the one deliberate widening of
  the "443 only" v1 posture, for Splunk's management port), migration
  037. Built ahead of a reachable customer Splunk environment — first
  live pull needs only a real host + token (Splunk Cloud: allowlist the
  ScopeWise egress IP on the stack's management port).
- KMS-grade key management: revisit if/when the app moves off the shared
  VPS; the plan's env-var key is explicitly a documented compromise.
- Webhook/push-based sync, rule write-back, per-rule drift alerts: out
  of scope entirely.
