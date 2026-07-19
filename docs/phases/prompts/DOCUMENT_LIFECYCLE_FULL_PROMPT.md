Implement the full Document Lifecycle & Multi-Project plan for ScopeWise
(formerly EDGP) — all three phases (Projects, Versioning, Fix-verification)
in this session.

**Scope warning, read first:** this is a large amount of work for one
session — three interdependent features (first-class projects, document
versioning with a similarity-suggestion service, and a cross-version
finding-diff engine), each touching migrations, backend routers, and
frontend pages. If token/time budget runs out partway through, **stop at
the end of a completed phase, not mid-phase** — a half-built Phase B is
worse than a solid Phase A with B/C explicitly deferred. State clearly at
any stopping point which phases are actually done vs. still open.

## Context

Repo: E:\code\DocumentGovernancePlatform (public at
github.com/manishjnv/document-governance-platform, deployed at
https://scopewise.assessiq.in on a shared VPS at /opt/scopewise).

Before touching any code, read in one parallel batch:
- `CLAUDE.md` (repo root) — project conventions: docs folder purposes, the
  migration-must-apply-to-4-places rule, VPS deployment/Caddy safety
  rules, testing gotchas. Follow this throughout, not just at the start.
- `docs/phases/prompts/DOCUMENT_LIFECYCLE_PLAN_PROMPT.md` — the full plan
  this session executes. It already made the key decisions (which option
  was picked vs. rejected for each open design question) — do not
  re-litigate those, implement as written.
- `docs/RCA_LOG.md` — every bug fixed in past live-testing sessions.
  Entries #11/#12/#13 are the migration/fixture-drift pattern you WILL hit
  again if you're not careful (see CLAUDE.md's migrations section).
- `docs/IMPLEMENTATION_PROGRESS.md` — current overall project state.
- `docs/planning/SCORING_METHODOLOGY.md` — how scoring/risk works today;
  Phase A's per-project rollup metrics aggregate these same scores, and
  Phase C's fix-verification touches the same Finding/Review models.

## Phase A — Projects as a first-class entity (do this first, fully, before B)

1. New `projects` table (migration numbered after the latest file under
   `apps/api/migrations/` — check first): `project_id, org_id, name,
   created_at`, unique constraint on `(org_id, name)`.
2. Add `project_id` FK to `documents`. Keep the existing `project_name`
   column during this migration — don't drop it yet.
3. **Data migration**: for each distinct existing `project_name` per org,
   create a matching `Project` row and backfill `project_id`. Exact
   string matches auto-map. Near-duplicates (case/whitespace/punctuation
   variants) do NOT auto-merge — write them to a migration report
   (markdown under `docs/`) for manual review; leave those documents'
   `project_id` unset until a human decides.
4. API: `GET /api/v1/projects` (list, each with rollup stats: document
   count, average latest score, count with an open critical finding) and
   `POST /api/v1/projects` (create). Follow existing router conventions
   (`verify_org_access`, schemas in `apps/api/app/schemas/`).
5. Upload endpoint accepts `project_id` (or a new `project_name` string,
   which creates the Project row on the fly — keeps "create new" a
   one-round-trip flow).
6. Frontend: Upload page's free-text Project input becomes an
   autocomplete/select over existing projects + "create new."
7. Frontend: Dashboard default view groups documents by project
   (collapsible sections); add a per-project detail page with the rollup
   metrics.

**Checkpoint before starting Phase B:** full test suite green, TypeScript
clean, Phase A demonstrably working (create a project, upload into it two
ways, dashboard groups correctly, per-project page shows real numbers).

## Phase B — Document versioning (do after A is solid)

1. Wire `Document.document_group_id`/`version` (already exist in the
   schema, unused today — every upload currently gets a fresh
   `document_group_id`) into the upload flow: an explicit **"Upload new
   version of..."** action from an existing document's row sets
   `document_group_id` to the source doc's and `version` to max+1.
2. Similarity-suggestion service: after ANY upload (not just ones flagged
   as a version), run a lightweight heuristic — same org + meaningful
   overlap in `parsed_sections` headings/content, or fuzzy filename match
   ignoring version-suffix noise ("_v2", "(revised)", etc.). If it matches
   an existing document group, surface a **dismissible, non-blocking**
   suggestion ("Possibly a new version of X, v3 — link as v4?"). Store
   the suggestion so it's visible later on the Documents page too, not
   just as a one-time toast the user might miss.
3. **"Link to existing document"** retroactive action: a searchable
   picker (by name/project/date, ranked by similarity if available) so a
   user who skipped/missed the suggestion can still link a standalone
   upload into a group later, without needing to recall an exact prior
   filename.
4. Frontend: Dashboard groups documents by `document_group_id`,
   collapsible v1..vN, each version's score/risk shown, a small trend
   indicator across versions.

**Do NOT auto-link silently under any circumstance** (rejected alternative
in the plan doc — a wrong silent merge is worse than an unlinked
document). Every link is either an explicit user action or an accepted
suggestion.

**Checkpoint before starting Phase C:** full test suite green, TypeScript
clean, upload a v2 of an existing document both via the explicit action
and via accepting a suggestion; confirm the dashboard's version grouping
and trend indicator render correctly.

## Phase C — Fix-verification diff (do last, depends on B)

1. On triggering a review for a document with a linked previous version
   (`document_group_id` has an earlier version with a completed review):
   fetch that previous review's findings.
2. Match previous findings to new findings by `category` (+
   `section_ref` where available, per the existing location-matching
   logic in `apps/api/app/routers/reviews.py`). A previous finding with
   no match in the new findings → mark it "Resolved (verified)" on the
   *previous* review's finding record. A previous finding that still
   matches → carry forward as "Still present," **independent of any
   manual "Mark Fixed" claim** made between versions — the manual claim
   never overrides what the re-review actually found.
3. Frontend: a version-diff view — given two versions, show three
   buckets: Resolved, New, Persisted. This is the actual payoff of
   versioning, not just a score trend line — make sure it's easy to find
   from the per-document version list built in Phase B.
4. Keep the existing "Mark Fixed" button's behavior (labeled as
   unverified user claim) — Phase C adds *automatic, re-review-verified*
   resolution on top of it, it doesn't replace the manual option.

## Conventions to follow (see CLAUDE.md for full detail)

- Every new migration: apply to `edgp_dev` AND `edgp_test` locally, AND
  check `tests/test_insights_extra.py` for any hand-rolled `CREATE TABLE`
  that mirrors a table you're changing, AND (if this session deploys) the
  VPS's `scopewise_prod` database. Four places, every time.
- Full backend suite (`cd apps/api && python -m pytest`) before and after
  each phase — stay at 402 passed / 2 skipped or better.
- `cd apps/web && npx tsc --noEmit` clean before committing any frontend
  change.
- One commit per logical unit per phase (migration+model, API, frontend,
  data-migration report as separate commits within each phase) — not one
  giant commit for the whole session.
- Only commit/push/deploy if explicitly asked, in this session's
  instructions or by the user mid-session.
- Update `docs/RCA_LOG.md` for any new bug found, and
  `docs/IMPLEMENTATION_PROGRESS.md` at the end of the session (or at each
  phase checkpoint if the session ends early).

## Exit criteria

- State plainly, phase by phase: which of A/B/C are fully done, which are
  partially done (and exactly what's left), which weren't started.
- Any phase claimed "done" must have passed its checkpoint above — don't
  claim Phase B done if the similarity-suggestion service is stubbed out,
  for instance.
- The 3 open questions from `DOCUMENT_LIFECYCLE_PLAN_PROMPT.md` (migration
  report format, similarity threshold/algorithm, whether to drop
  `project_name` after migration) — resolve them as you go and note the
  decision made, or flag them as still open if genuinely blocking.
