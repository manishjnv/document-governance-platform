Implement the Document Lifecycle & Multi-Project plan for ScopeWise
(formerly EDGP), starting with Phase A only this session.

## Context

Repo: E:\code\DocumentGovernancePlatform (also public at
github.com/manishjnv/document-governance-platform, deployed at
https://scopewise.assessiq.in on a shared VPS at /opt/scopewise).

Before touching any code, read in one parallel batch:
- `docs/phases/prompts/DOCUMENT_LIFECYCLE_PLAN_PROMPT.md` — the full plan
  this session executes. It already made the key decisions (which option
  was picked vs. rejected for each open design question) — do not
  re-litigate those, just implement Phase A as written.
- `docs/RCA_LOG.md` — every bug fixed in the last live-testing session.
  Several are copy-pasted patterns that WILL recur if you touch the same
  files again (e.g. entry #11/#12/#13: any new migration or model column
  must be applied to BOTH `edgp_dev` and `edgp_test` local Postgres
  databases, AND `test_insights_extra.py`'s hand-rolled SQLite fixture
  schema, AND (if this session deploys) the VPS's `scopewise_prod` DB).
- `docs/IMPLEMENTATION_PROGRESS.md` — current overall project state.
- `docs/planning/SCORING_METHODOLOGY.md` — for context on how scoring/
  risk already works, since Phase A's per-project rollup metrics will
  aggregate these same per-document scores.

## What to build this session: Phase A only (Projects as a first-class entity)

Do NOT start Phase B (versioning) or Phase C (fix-verification diff) —
those depend on Phase A being solid first and are separate future
sessions per the plan doc's sequencing.

Concretely, from `DOCUMENT_LIFECYCLE_PLAN_PROMPT.md`'s Phase A section:

1. New `projects` table (migration, numbered after whatever the latest
   migration file is under `apps/api/migrations/` — check first, don't
   assume a number): `project_id, org_id, name, created_at`, unique
   constraint on `(org_id, name)`.
2. Add `project_id` FK to `documents`. Keep the existing `project_name`
   column in place during this migration — do not drop it yet.
3. **Data migration** for existing data: for each distinct `project_name`
   value already in `documents` per org, create a matching `Project` row
   and backfill `project_id`. Exact string matches auto-map. For
   near-duplicates (case/whitespace/punctuation variants of what's
   probably the same project name), do NOT auto-merge — write them to a
   migration report (a markdown file under `docs/` is fine) for manual
   review, and leave those documents' `project_id` unset until a human
   decides.
4. API: `GET /api/v1/projects` (list projects for the org, each with
   rollup stats: document count, average latest score across its
   documents, count of documents with an open critical finding) and
   `POST /api/v1/projects` (create). Follow the existing router
   conventions in `apps/api/app/routers/` (org-scoped via
   `verify_org_access`, response models in `apps/api/app/schemas/`).
5. Update the upload endpoint (`apps/api/app/routers/documents.py`) to
   accept `project_id` as well as (or instead of) the current
   `project_name` query param — if a `project_id` isn't given but a new
   `project_name` string is, create the Project row on the fly so the
   frontend's "create new" autocomplete flow works in one round-trip
   without a separate create-then-upload step.
6. Frontend: replace the free-text Project input on the Upload page
   (`apps/web/app/upload/page.tsx`) with an autocomplete/select over
   existing projects plus an explicit "create new" option.
7. Frontend: Dashboard (`apps/web/app/dashboard/page.tsx`) default view
   groups documents by project in collapsible sections instead of one
   flat table. Add a new per-project detail page/route showing the
   rollup metrics from step 4.

## Conventions to follow (established this repo, not generic advice)

- Every new migration file gets applied to BOTH local Postgres databases
  (`edgp_dev` AND `edgp_test`, via `docker exec -i edgp-postgres psql -U
  edgp_user -d <db> < migrations/0XX_*.sql`) before you consider it done
  — they are separate databases in the same container and migrations
  never auto-apply. If this session also deploys to the VPS, the
  migration needs to run there too (VPS: `docker exec -i
  scopewise-postgres psql -U scopewise_user -d scopewise_prod < ...`).
- Grep `tests/test_insights_extra.py` for any hand-rolled `CREATE TABLE
  <model>` that mirrors a table you're changing (it has its own inline
  SQLite schema, separate from the real migrations) and update it too —
  this has broken twice already (RCA entries #12, #13).
- Run the full backend suite (`cd apps/api && python -m pytest`) before
  and after your changes; it should stay at 402 passed / 2 skipped (or
  better).
- TypeScript: `cd apps/web && npx tsc --noEmit` must be clean before
  committing any frontend change.
- One commit per logical unit (e.g. migration+model separate from
  frontend UI separate from the data-migration report), not one giant
  commit — matches how this session's history is structured
  (`git log --oneline` to see the pattern).
- Only commit/push/deploy if explicitly asked to in this session's
  instructions or by the user mid-session — don't assume permission
  beyond what's asked.
- Update `docs/RCA_LOG.md` if you hit any new bug, and
  `docs/IMPLEMENTATION_PROGRESS.md` at session end, per the existing
  format in both files.

## Exit criteria for this session

- Phase A fully working end-to-end: create a project, upload a document
  into it (both via existing-project select and via "create new"),
  confirm the dashboard groups it correctly and the per-project page
  shows real rollup numbers.
- Existing free-text `project_name` documents from before this migration
  still display correctly (via the backfilled `project_id`, or flagged in
  the migration report if ambiguous).
- Full test suite green, TypeScript clean.
- State plainly at the end: what got done, what's still open (the 3
  "open questions" from the plan doc if not yet resolved), and confirm
  Phase B/C are explicitly NOT started yet.
