# Session Handoff — 2026-07-19 Risk Scoring, Results UI, Deployment, Lifecycle Planning

**Headline:** Redesigned risk scoring (saturating curve + per-axis Risk by
Area breakdown), overhauled the results page UI (full-screen, resizable
split view, Document X-Ray, mark-fixed), deployed ScopeWise publicly to
GitHub + a shared VPS at https://scopewise.assessiq.in, then spent the
rest of the session in planning-only discussion on document versioning /
fix-verification / multi-project organization, ending in two prompt docs
for a future implementation session. Added a root `CLAUDE.md` after a
process mistake (prompt doc saved to scratch instead of `docs/`).

**Commits this session (in order):**
- `bf896af` — Full-width results, drag-resizable finding/document split, denser findings, deeper colors
- `e194e12` — Fix sidebar overlapping content: inline `paddingLeft:0` always beat the responsive class
- `87c1f56` — Add Document X-Ray panel; default to collapsed nav + 33/66 split view
- `5f952b1` — Redesign risk score: saturating curve + per-axis breakdown, add scoring methodology doc
- `914086e` — Fix transparent tooltip/dropdown/dialog: popover and accent theme colors were never defined
- `066c74f` — Route AI review through GLM-5.2/MiniMax M3/Qwen3.7-Plus fallback chain
- `f325049` — Add project CLAUDE.md and Document Lifecycle plan/prompt docs
- `331a7e7` — Add combined all-phases prompt for Document Lifecycle plan
- *(this session, pending)* — sample document set refresh; IMPLEMENTATION_PROGRESS.md update; this handoff doc

---

## What changed

**Risk scoring** (`apps/api/app/scoring/algorithm.py`, `app/models/review.py`,
`app/admin/customization.py`, migration `022_review_risk_model.sql`):
old model saturated almost every real document at "100%, High" with no
discrimination. New model: `100 * (1 - e^(-k * severity_weighted_sum))`,
`k=0.0086` (recalibrated from an initial 0.045 guess after observing real
review volumes of 30-400 raw severity points), plus a **Risk by Area**
per-axis breakdown (Compliance/Security/Governance/Scope/Legal/Commercial/
Delivery) stored as `Review.risk_breakdown` JSONB, tunable per-org via a
new `org_risk_weights` table following the existing
`get_scoring_weights`/`set_scoring_weight` customization pattern. Verified
on real production data: Risk Score 94.34%, breakdown ranged Compliance
64% → Delivery 5% — genuine spread vs. the old flat 100%. Full rationale
(ISO 31000/NIST likelihood×impact, PMBOK, IACCM most-negotiated-terms
research, FAR Part 15) written up in `docs/planning/SCORING_METHODOLOGY.md`,
which also honestly flags that finding-severity itself is still
LLM-assigned with no external calibration (tracked separately in
`docs/planning/LEGAL_SEVERITY_CALIBRATION.md`).

**Results page overhaul** (`apps/web/app/results/[reviewId]/page.tsx`,
`apps/web/components/AppShell.tsx`, `globals.css`, `tailwind.config.ts`):
full-screen layout; drag-resizable findings/document split pane (default
33/66, hideable document pane); clickable severity-filtered Findings
Summary; new "Document X-Ray" panel (parsed sections list, missing-section
detection) sitting above the Findings Summary; evidence-to-document
linking with scroll+highlight on click; mark-fixed/reopen per finding via
new `PATCH /api/v1/reviews/{review_id}/findings/{finding_id}`, explicitly
labeled as an unverified user claim (see Document Lifecycle plan below for
why this isn't a real "fix" until re-verified). `AppShell` sidebar made
collapsible (default collapsed) and drag-resizable by width. Fixed two
real bugs along the way: a stale inline `paddingLeft:0` that always beat
the responsive Tailwind class controlling layout push, and missing
`--popover`/`--accent` CSS custom properties that made tooltips/dropdowns
render transparent.

**OpenRouter model routing** (`app/ai/agent.py`, `app/ai/config.py`):
fallback chain GLM-5.2 → MiniMax M3 → Qwen3.7-Plus → DeepSeek replaces a
single hardcoded model; fixed a `max_tokens=2000` truncation bug that was
silently breaking most candidate models, removed `moonshotai/kimi-k3`
from the chain (its reasoning tokens consumed the entire budget before
producing output). Full benchmark methodology and per-model results in
`docs/planning/AI_MODEL_ROUTING.md`.

**Public deployment:** pushed the repo public to
`github.com/manishjnv/document-governance-platform`; deployed to a shared
VPS (72.61.227.64 / srv1150121.hstgr.cloud) at `/opt/scopewise`, isolated
via its own Docker network/volumes/container names
(`scopewise-net`/`scopewise-*`) and ports 9094 (web)/9095 (api), fronted
by the existing Caddy reverse proxy + Cloudflare DNS at
`scopewise.assessiq.in`. Migration 022 applied to all three required
Postgres targets (`edgp_dev`, `edgp_test`, `scopewise_prod`).

**Document Lifecycle & Multi-Project planning (design-only, no code):**
worked through, in conversation, what should happen when a customer marks
a finding "fixed" and re-uploads a revised document, and how multiple
projects with multiple document versions should be organized. Landed on
three decisions (see `docs/phases/prompts/DOCUMENT_LIFECYCLE_PLAN_PROMPT.md`
for full reasoning and rejected alternatives):
1. **Fix verification is two-tier** — "Mark Fixed" stays a self-reported,
   clearly-labeled-unverified claim; real verification only happens when a
   new document version is uploaded, re-reviewed, and its findings are
   diffed against the previous version's.
2. **Versioning is explicit-action-first, never silent** — an explicit
   "Upload new version of..." action is primary; a background similarity
   check surfaces a dismissible (never auto-applied) suggestion as a
   safety net; a retroactive "link to existing document" picker covers
   the case where a user misses or ignores the suggestion.
3. **Projects become a first-class entity** — `project_name` free text is
   promoted to a real `projects` table with autocomplete + explicit
   "create new," to stop typo/naming drift from silently fragmenting one
   project into several.

Two prompt docs came out of this: `DOCUMENT_LIFECYCLE_PLAN_PROMPT.md` (the
full plan, decisions + phase breakdown) and
`DOCUMENT_LIFECYCLE_FULL_PROMPT.md` (a self-contained kickoff prompt to
implement all three phases — Projects → Versioning → Fix-verification —
in a single future session, in that dependency order, with a checkpoint
after each phase).

**Process fix:** a "next session" prompt doc was mistakenly saved to the
Windows scratch/Temp directory instead of the repo's established
`docs/phases/prompts/` location (where 8+ similar files already existed).
Caught by the user, corrected, and turned into a lasting fix: a new root
`CLAUDE.md` documenting the docs/ folder layout and other repo
conventions (migration-to-4-places rule, testing baselines, VPS deploy
specifics), plus a personal memory update, so a future session doesn't
need the user (a non-technical "vibe coder") to catch this kind of
misplacement themselves.

**Sample documents refreshed:** replaced the 2 generic placeholder samples
(`sample_rfp.docx`, `sample_sow.docx`) with real-world SOW/RFP template
sets (~140 files across `RFP_Sample/`, `RFP_template/`, `SOW_Template/`)
for more representative manual UI testing.

**Note on `AGENTS.md`:** an untracked `AGENTS.md` file appeared at the repo
root this session containing a raw memory-plugin context dump (wrapped in
`<claude-mem-context>` tags), not actual repo content or instructions —
almost certainly an accidental write by the claude-mem tooling, not
intentional work. **Left uncommitted and untouched** rather than either
committing stray content or deleting something that might matter — flagged
here for the user to review/delete as they see fit.

## Next action

Run `docs/phases/prompts/DOCUMENT_LIFECYCLE_FULL_PROMPT.md` in a new
session to implement Projects → Versioning → Fix-verification. Zero code
written for any of the three phases yet — this session was planning-only
for that part.

## Open questions (carried from the plan doc, unresolved)

1. Migration report format/location for near-duplicate project names.
2. Similarity threshold/algorithm for the version-suggestion heuristic.
3. Whether `project_name` (free text) gets dropped after migration or kept
   read-only as a historical field.
4. What to do about the stray `AGENTS.md` file (delete it, or is it
   expected by some tooling?).

## Tests

Full backend suite verified green (402 passed / 2 skipped) after the risk
scoring and UI changes; `npx tsc --noEmit` clean after each frontend
change. Not re-run after the sample-document/docs-only changes at session
end since no code changed.
