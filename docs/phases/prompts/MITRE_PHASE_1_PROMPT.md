# Kickoff prompt — MITRE Assessment Phase 1 (persistence + ingest + API, tagged-only E2E)

Self-contained kickoff prompt. Paste everything below the line into a
fresh session (target model: Fable 5 main session).

---

Implement **Phase 1** of the MITRE ATT&CK coverage-assessment feature for
ScopeWise. This prompt carries the context you need;
`docs/planning/MITRE_ASSESSMENT_PLAN.md` (§6 data model, §7 pipeline, §8
API, §12 testing, §13 acceptance) is the authoritative design — read it
before deviating, and do not re-litigate decisions recorded there.

## Context

ScopeWise (this repo) is an AI SOW/RFP review platform: FastAPI backend
(`apps/api`), Next.js frontend (`apps/web`). The MITRE module is a new,
**fully isolated** feature: customer uploads a SIEM use-case/detection
dump (tagged or untagged) + a multi-sheet environment workbook + a slim
intake, and gets a deterministic ATT&CK coverage/gap assessment (all
numbers pure Python against a pinned dataset; LLM only for tagging and
narrative — later phases).

**Status:** Phase 0 is COMPLETE and verified (2026-08-01): pinned ATT&CK
**v19.1** dataset (`apps/api/app/mitre/data/attack.json` — enterprise 697
active / ics 97 / mobile 124 techniques), pure modules
`app/mitre/{attack_data,applicability,coverage}.py`, 23 unit tests. Full
suite baseline is **606 passed, 6 skipped** (per root CLAUDE.md — the old
"402/2" figure is dead). Phase 0 files may still be uncommitted — that is
expected (commits only on explicit user request).

**Roadmap:** P0 data+logic ✅ → **P1 (THIS): migration 029, models,
ingest, router/service, tagged-only end-to-end** → P2 LLM tagging +
narrative → P3 frontend → P4 reports/PDF/XLSX + trend → P5 sign-off +
deploy.

**Isolation contract:** pre-existing files you may edit in Phase 1 —
exactly two, both additive: `apps/api/main.py` (+1 import, +1
`app.include_router(...)` appended at the END of registrations; router
order elsewhere is load-bearing) and `apps/api/app/models/__init__.py`
(register the 3 new models in imports + `__all__`, FK targets before
dependents). Everything else is new files. Never touch `app/parser.py`,
`app/routers/*`, `app/ai/*`, existing models, or the frontend (Phase 3).

## Read first (one parallel burst), then state your plan in a few lines

1. Root `CLAUDE.md` (migrations 4-place rule, baselines, commit policy).
2. `docs/planning/MITRE_ASSESSMENT_PLAN.md` §6–§8, §12–§13.
3. **The Phase 0 modules** — `apps/api/app/mitre/attack_data.py`,
   `applicability.py`, `coverage.py`: their actual function signatures are
   the contract; call them, don't reinvent or modify them.
4. House patterns to copy: `app/routers/documents.py` (upload guards,
   `_sanitize_filename`, storage keys, MIME/size constants),
   `app/routers/reviews.py` (trigger + per-org config read + empty-parse
   422 guard), `app/models/review.py` (status lifecycle CHECKs),
   `migrations/027_finding_evidence.sql` (idempotent DDL style),
   `app/admin/customization.py` (org-override tunables pattern),
   `apps/api/tests/conftest.py` (real-Postgres test setup).

Before starting: run `git status` — another session was recently active
in this worktree (2026-08-01 incident); if you see unexpected in-progress
changes beyond the untracked `app/mitre/` Phase 0 files, tell the user
instead of proceeding. Never run destructive git commands.

## Deliverables

### 1. Migration `apps/api/migrations/029_mitre_assessment.sql`

**New tables only — zero ALTERs** (this deliberately keeps the
`test_insights_extra.py` hand-rolled fixture out of play; keep it that
way). Idempotent DDL, `DO $$` constraint guards, header comment listing
apply targets. House conventions: UUID v4 PKs, `org_id` FK →
`organizations.org_id` ON DELETE CASCADE, `created_by` FK → users SET
NULL, timestamps + `deleted_at`, string+CHECK enums (SQLite-portable in
ORM; strict checks in SQL).

- `mitre_assessments` — name, `status` CHECK
  (`pending|running|completed|failed`) with Review-style invariants
  (`completed ⇒ completed_at NOT NULL`, `failed ⇒ error_message NOT
  NULL`), `attack_version`, `params` JSONB (intake, detected column map,
  thresholds used), `technique_results` JSONB, `summary` JSONB,
  `error_message`, `completed_at`, `created_by`.
- `mitre_files` — assessment FK, `kind` CHECK (`use_cases|environment`),
  filename, `file_type` CHECK (`xlsx|xls|csv|pdf|docx`), `s3_path`,
  `parse_status`, `row_count`.
- `mitre_use_cases` — assessment FK, file FK, `row_ref`, name,
  description, log_source, `enabled` BOOL NULL (NULL = unknown),
  `mappings` JSONB, `mapping_status` CHECK
  (`customer_tagged|ai_tagged|unmapped|invalid`).
- `mitre_settings` — org-keyed tunables (customization.py pattern):
  defaults in code `confidence_covered=0.7`,
  `confidence_partial_floor=0.4`, `partial_credit=0.5`,
  `count_disabled_as_coverage=false`.

**Apply immediately** (no runner exists): `docker exec -i edgp-postgres
psql -U edgp_user -d edgp_dev < apps/api/migrations/029_mitre_assessment.sql`
and the same into `edgp_test` (tests fail without it). Prod
(`scopewise_prod`) is applied in Phase 5, not now.

### 2. Models

`app/models/{mitre_assessment,mitre_file,mitre_use_case}.py` — inherit
`Base + TimestampMixin + SoftDeleteMixin` from `app.db.base`; register all
three in `app/models/__init__.py`.

### 3. `app/mitre/ingest.py`

Structured readers producing EXACTLY the Phase 0 data contracts:

```python
# use case:   {"row_ref", "name", "enabled", "mappings": [{"technique_id","source","confidence"}]}
#             (+ description, log_source carried for persistence)
# environment: {"platforms": [...], "has_ics_assets", "has_managed_mobile",
#               "inventory_provided", "exclusions": [{"target","reason"}]}
```

- xlsx via openpyxl **direct cell access** (NOT `parse_document()` — the
  existing ExcelParser flattens sheets and destroys columns), xls via
  xlrd, csv via stdlib.
- Header detection: synonym lists (name/title/rule; description; logic/
  query/condition; technique/ttp/mitre/attack id; status/enabled/state;
  log source/data source/index). Detected mapping goes into `params` and
  the parse preview. No detectable name column → 422 pointing at the
  template (`apps/web/public/templates/` — templates ship in Phase 3;
  the 422 message can reference "the ScopeWise use-case template").
- Environment workbook: sheets by name synonyms (Assets, Log Sources,
  Tooling/Security Tooling, Crown Jewels); missing sheets tolerated,
  each absence → assumption line. Platform strings normalized to ATT&CK
  platform names via a small synonym map (windows/win → Windows, entra/
  azure ad → Identity Provider etc. — check `attack.json` platform
  vocabulary and cover the obvious aliases).
- Intake JSON (from the request): `{industry, region,
  count_disabled_as_coverage, exclusions: [{target, reason}]}`.
- Trust-boundary guards (server-side; mirror documents.py): MIME
  allowlist, 50MB cap, sanitized filenames, row caps **5,000 use-case /
  10,000 asset rows** (422 beyond, stated in the error), empty-parse 422.
- pdf/docx: accept the MIME types at upload BUT return 422 in Phase 1
  with a plain-English message ("PDF/DOCX rule dumps are enabled with AI
  extraction in an upcoming release — please use the XLSX template for
  now"). AI text-extraction lands in Phase 2.

### 4. `app/mitre/router.py` + `app/mitre/service.py`

`APIRouter(prefix="/api/v1/mitre", tags=["mitre"])`, mounted via the one
`main.py` line. Auth via existing `get_current_user` / role deps; every
query filtered `org_id == current_user.org_id` and `deleted_at IS NULL`;
`log_action()` audit + `invalidate_cache()` after writes. Storage via
`get_storage_instance()`, key `org/{org_id}/mitre/{assessment_id}/{fname}`.

Phase 1 endpoints (report/export/compare are Phase 4):

| Endpoint | Notes |
| --- | --- |
| `POST /assessments` | multipart: use_cases file, optional environment file, intake JSON. Create rows + parse synchronously + persist use cases → return parse preview (row count, detected columns/sheets, tagged/untagged/invalid split, warnings). Roles: admin/reviewer |
| `POST /assessments/{id}/run` | 202; 409 if already running/completed. Fire-and-forget `asyncio.create_task` (no LLM this phase, still async for forward-compat); pipeline wrapped in try/except → status `failed` + error_message. Background task uses its own `AsyncSession` |
| `GET /assessments` | org list: name, status, created, headline %, attack_version. Any role |
| `GET /assessments/{id}` | status + params + summary + technique_results. **Stale-run guard here**: `running` and updated_at older than 30 min → flip to `failed` ("interrupted — likely a restart; re-run"). Any role |
| `GET /assessments/{id}/use-cases` | paginated, filter by mapping_status. Any role |
| `PATCH /settings` + `GET /settings` | admin-only org tunables (the 4 keys above), customization.py get/set pattern — own module, no edits to existing admin files |
| `DELETE /assessments/{id}` | soft delete. Roles: admin/reviewer |

**Pipeline (tagged-only this phase)** in `service.py`: (1) tag
validation via `attack_data` — extract `T\d{4}(\.\d{3})?` from the tags
column, `resolve()` remaps revoked → successor, deprecated flagged,
invalid IDs → `mapping_status='invalid'` + assumption; valid customer
tags get `source='customer', confidence=1.0`; untagged rows →
`'unmapped'` + assumption ("N untagged rules not yet AI-mapped — tagging
lands in the next release"); (2) applicability from the environment dict;
(3) coverage with the org's tunables; (4) persist `technique_results` +
`summary` (rollups, assumptions, N/A list; gap ranking/roadmap/narrative
are Phase 2), transition status per the lifecycle CHECKs.

### 5. Tests — `apps/api/tests/test_mitre_ingest.py`, `test_mitre_api.py`

Minimal-targeted (project taste; no bloat). Small fixture files built
in-test with openpyxl. Cover: template-layout tagged xlsx happy path
**end-to-end with hand-computed expected coverage numbers**; messy-header
detection; untagged mix → unmapped + assumption; revoked-ID remap
surfaces in mappings; empty file 422; over-cap 422; pdf 422 message;
org isolation (cross-org GET/run/delete → 404/403); 409 double-run;
settings PATCH admin-only; stale-run guard. Reminder: migration 029 must
be applied to `edgp_test` BEFORE pytest.

## Acceptance (verify before claiming done — run, don't assume)

- `cd apps/api && python -m pytest tests/test_mitre_api.py tests/test_mitre_ingest.py -q` green.
- Full suite: **606 + new tests passed, 6 skipped, 0 failures** (Docker
  Desktop + `edgp-postgres` must be up; 269 collection errors = Docker is
  down, start it, don't debug).
- Migration applied to BOTH `edgp_dev` and `edgp_test`; `psql \d
  mitre_assessments` shows the CHECKs.
- `git status`: only new files + the two allowed edits (`main.py`,
  `app/models/__init__.py`) + docs updates.
- Manual smoke: one curl/httpx run of create→run→poll→results against the
  local dev server with a real template-layout xlsx.

## Wrap-up

Do NOT commit/push unless the user explicitly says so. Report: files
created, the two shared-file diffs verbatim, test output, the smoke-run
coverage numbers, deviations from this prompt (if any, with reasons).
Update `docs/IMPLEMENTATION_PROGRESS.md`'s MITRE entry (Phase 1 done,
Phase 2 next per plan §13) and add a session handoff in
`docs/phases/summaries/`.
