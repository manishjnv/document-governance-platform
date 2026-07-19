# Document Lifecycle & Multi-Project Plan (Next Session)

**Target Duration**: 2-3 sessions (see sequencing below)
**Status**: Planning only — nothing in this doc is implemented yet
**Origin**: 2026-07-19 discussion on what happens after a customer marks a
finding "Fixed," re-uploads a revised document, and manages multiple
projects. Each open question below had several options discussed; this
doc picks ONE per topic (with the rejected alternatives noted briefly so
the reasoning isn't lost) rather than leaving multiple paths open.

---

## Context: the problem chain

1. Marking a finding "Fixed" today only changes that finding's status —
   it doesn't touch Overall Score, Risk Level, or Findings Summary counts
   (those are frozen at review time). A self-reported "fixed" checkbox
   with no re-verification would let someone claim a critical liability
   gap is resolved without changing a word of the contract.
2. The real fix requires a **new document version** + a **new AI
   review**, then comparing the new review's findings against the old
   one's to confirm the issue is actually gone.
3. That requires document versions to be *linked* to each other in the
   first place — the schema already supports this
   (`Document.document_group_id`, `Review.document_version`) but no
   upload flow wires it up; every upload today gets a fresh
   `document_group_id`.
4. Customers also manage multiple projects, each with their own set of
   documents (and each document potentially with its own version
   history) — needs an organizing structure above "document."

---

## Decisions (one path per topic, alternatives noted)

### 1. Fix verification: two-tier (user-claimed vs. system-verified)

**Decision:** "Mark Fixed" stays a user claim, labeled clearly as
unverified. Real verification only happens when the customer uploads a
new version of the SAME document and it gets re-reviewed — the new
review's findings are diffed against the previous version's; a
previously-open finding is auto-marked "Resolved (verified)" only if it
no longer appears in the new findings for the same category/section,
otherwise it's marked "Still present" regardless of any earlier manual
"Fixed" claim.

**Rejected alternative:** a live client-side score recompute that
excludes "Fixed" findings immediately. Rejected because it lets a score
improve without any actual change to the document — undermines the
product's whole value proposition (catching what the customer would
otherwise miss).

### 2. Document versioning: explicit action + passive suggestion, never silent auto-link

**Decision:**
- Primary path: an explicit **"Upload new version of..."** action from
  an existing document's row. Sets `document_group_id` to the source
  document's, increments `version`.
- Safety net for the "uploaded from the normal Upload page by mistake or
  didn't know" case: a background similarity check (same org + section-
  heading/content overlap, filename similarity ignoring version
  suffixes) runs after every upload — including ones the user didn't
  flag as a version — and surfaces a **dismissible, non-blocking
  suggestion** ("Possibly related to Document X, v3 — link as v4?").
  This re-runs / stays visible later, not just once at upload time.
- Retroactive fix: a **searchable "Link to existing document" picker**
  (search by name/project/date, ranked by similarity) on any standalone
  document, so linking is never a one-shot decision the user has to get
  right immediately, and never requires recalling an exact document
  name from memory.

**Rejected alternative:** automatic silent linking based on filename/
content match. Rejected — a wrong silent merge (two genuinely different
documents treated as versions of each other) is worse and harder to
notice than an unlinked document sitting standalone.

### 3. Multi-project organization: Project as a first-class entity

**Decision:** promote `project_name` (currently free text) to a real
selectable field backed by a `projects` table — autocomplete from
existing projects + "create new," not open text. Two views:
dashboard grouped by project (collapsible sections, each showing its
documents), plus a dedicated per-project page with rollup metrics
(average score across the project's documents, count with open critical
findings, risk trend over time).

**Rejected alternative:** leave `project_name` as free text
indefinitely. Rejected — typo/naming drift ("Acme," "ACME Corp," "Acme
Corp.") silently fragments one project into several with no way to
detect or merge them later without a data-cleanup pass.

---

## Implementation plan

### Phase A — Projects as a first-class entity (do first: self-contained, immediately useful, no dependency on B/C)

1. New `projects` table: `project_id, org_id, name, created_at`
   (+ unique constraint on `org_id, name`).
2. Add `project_id` FK to `documents`, keep the existing `project_name`
   column during migration (don't drop it in the same step).
3. **Data migration**: for each distinct existing `project_name` value
   per org, create a `Project` row; exact-string matches auto-map,
   near-duplicates (edit-distance or case/whitespace variants) get
   flagged in a migration report for manual merge decision — do not
   auto-merge near-duplicates silently.
4. API: `GET /api/v1/projects` (list, with rollup stats), `POST
   /api/v1/projects` (create). Upload endpoint accepts `project_id`
   (falls back to free-text creation of a new Project row if the name is
   new — keeps the "create new" autocomplete flow working in one step).
5. Frontend: replace the free-text Project input on Upload with an
   autocomplete/select (existing projects) + explicit "create new"
   option.
6. Frontend: Dashboard default view groups documents by project
   (collapsible sections); add a per-project detail page with the
   rollup metrics.

### Phase B — Document versioning (do second: bigger, needs the diff engine Phase C depends on)

1. Wire up `document_group_id`/`version` in the upload flow: "Upload new
   version of..." action (from a document row) vs. normal upload (new
   group).
2. Similarity-suggestion check: lightweight heuristic, run
   asynchronously after any upload; store suggestions somewhere
   queryable (not just a one-time toast) so they're visible later on the
   Documents page too.
3. "Link to existing document" searchable picker + retroactive linking
   endpoint.
4. Dashboard: group by `document_group_id`, collapsible v1..vN, each
   version's score/risk shown, small trend indicator across versions.

### Phase C — Fix-verification diff (do third: depends on B)

1. On triggering a review for a document that has a linked previous
   version (`document_group_id` has an earlier version with a completed
   review): fetch the previous review's findings.
2. Match previous findings to new findings by `category` (+ `section_ref`
   where available). A previous finding with no match in the new
   findings → mark it "Resolved (verified)" on the *previous* review's
   finding record. A previous finding that still matches → carry forward
   as "Still present," independent of any manual "Fixed" claim made
   between versions.
3. Version diff view (UI): given two versions, show three buckets —
   Resolved, New, Persisted — this is the actual payoff of versioning,
   not just a score trend line.

---

## Open questions to confirm before starting

1. Migration report format/location for near-duplicate project names —
   a doc, an admin-only endpoint, or a one-off script output?
2. Similarity threshold/algorithm for version-suggestion (section-heading
   overlap %? filename fuzzy match? both?) — needs a first-pass value,
   should be tunable per the existing customization pattern
   (`app/admin/customization.py`) rather than hardcoded.
3. Should `project_name` (free text) be dropped after migration, or kept
   read-only as a historical/audit field?

## Exit criteria

- Full test suite green after each phase (`cd apps/api && python -m
  pytest`).
- One commit per logical unit (per the phases above, not one giant
  commit).
- `docs/RCA_LOG.md` and `docs/IMPLEMENTATION_PROGRESS.md` updated per the
  existing session-exit convention.
