# EDGP Implementation Progress

**Last Updated:** 2026-08-01 09:30 GMT+5:30
**Current Phase:** Phase 1-2 core product complete + deployed live; pre-launch fix plan Steps 1-2 done, Step 3 pending SME. Document Lifecycle & Multi-Project plan (Projects/Versioning/Fix-verification) — all three phases implemented, deployed, mandatory-project + fuzzy name matching added on top. Auth is now seamless Google Sign-In + email-OTP only (no password anywhere in the real UI; unrecognized emails auto-create an account). New file types (.doc/.xlsx/.xls/.csv) supported. Enterprise SEO strategy written, a live Cloudflare misconfiguration blocking all AI crawlers was found and fixed, and **SEO Phase 1 (Foundation) is implemented and deployed live** (real marketing homepage/product/pricing/about/contact/sitemap/schema -- only GSC/GA4/Lighthouse remain, blocked on dashboard access). Full detail: `docs/phases/summaries/SESSION_HANDOFF_2026_07_20_LIFECYCLE_SSO_SEO.md`.

> Previous version of this doc (dated 07-17 02:00, showing "14% overall") was
> stale from early Phase 1 and did not reflect Phase 2/3 or the pre-launch
> review-accuracy push. Superseded by this version.

---

## ✅ Done

**Foundation, Auth, DB (Phase 1):** monorepo, Docker, FastAPI + Next.js
skeletons, JWT auth (login/logout/refresh/me/password-reset/signup),
bcrypt hashing, login rate-limiting + lockout (memory-capped), full DB
schema (6 tables, soft deletes, audit triggers), login UI. Only Azure AD
SSO (T-109, explicitly optional) is not built.

**Document management:** upload (PDF/DOCX), S3 storage with SSE-AES256,
filename path-traversal sanitization, parsing, RBAC on delete (viewer
blocked), soft delete.

**AI review engine:** 6 agents (Scope, Delivery, Commercial, Security, PMO,
Legal) run in parallel via `ReviewOrchestrator`, each with SOW- and
RFP-branching system prompts. Cross-cutting ambiguous-language regex scan.
Rule engine (20 SOW rules + 7 RFP rules). RFP is a first-class
`DocumentType` (enum + migration + rule set + agent prompts).

**OpenRouter model routing (2026-07-19):** primary/fallback chain
(GLM-5.2 → MiniMax M3 → Qwen3.7-Plus → DeepSeek) replaces the single
`deepseek-chat` default; fixed a `max_tokens=2000` truncation bug that
was silently breaking 3 of 5 candidate models. Full benchmark results
and rationale in `docs/planning/AI_MODEL_ROUTING.md`.

**Accuracy baseline (2026-07-22):** first measured precision/recall of the
live pipeline vs the 29-row ground truth in
`docs/sample/SOW_Sample/SOW_Review_Training_Guideline.md` — strict recall
72.4%, lenient 86.2%, effective precision ≈93%. Misses + rule-engine false
positives and fix list in `docs/planning/ACCURACY_BASELINE_2026_07_22.md`.

**Guideline feasibility plan — EXECUTED 2026-07-23** (all 4 phases of
`docs/phases/prompts/GUIDELINE_FEASIBILITY_PLAN_PROMPT.md`):

- **Phase A** (measured-defect fixes): section-presence matching normalizes
  numbered headings + word-boundary aliases (root cause of the 4 FPs);
  self-negating-finding filter at orchestrator ingestion; 13 guideline §5
  rules SOW-021..033 (keyword checks, org-disableable); ScopeReviewer
  per-service-line decomposition + DeliveryReviewer appendix-table audit.
  **Re-measured: strict recall 72.4% → 93.1%, rule FPs 4 → 0, precision
  ≈97%** (second dated measurement in ACCURACY_BASELINE_2026_07_22.md).
- **Phase B** (typed evidence, migration 027): findings gained
  evidence_type/page/line/anchors/matched_text (nullable). Rule engine
  stamps missing_section, ambiguous scan stamps location+matched_text,
  agent quotes derive location at ingestion. UI tag + quoted block.
- **Phase C**: broken-reference detector (`app/rules/references.py`,
  REF-SCAN toggle) + LLM ConflictDetector (separate orchestrator step,
  CONFLICT-SCAN toggle, degrades to [] on failure).
- **Phase D** (migration 028): reviews.audit_meta JSONB — parsed-text
  SHA-256, models actually used per agent, RULES_VERSION, git SHA;
  surfaced in API + results footer + PDF footer.

Plan's "Excludes" honored: no multi-backend AI, no customer-managed keys,
no dual review, no explainability sub-scores.

**Accuracy improvement sweep — 2026-07-24** (all dependency-free items;
details in `docs/phases/summaries/SESSION_HANDOFF_2026_07_24_ACCURACY_IMPROVEMENTS.md`):

- `scripts/accuracy_harness.py` — deterministic keyword scoring of any
  review run vs the 29-row ground truth (fast regression trend signal).
- Third dated measurement: **29/29 strict recall** on the test doc after
  ScopeReviewer environment-inventory + PMOReviewer open-items checks.
- Fuzzy evidence anchoring: 38/62 agent findings carry section+page (was ~2).
- **Measured 4-model comparison** (AI_MODEL_ROUTING.md): GLM-5.2 28/29
  (6/6 agents) >> MiniMax 24/29 (4/6) > DeepSeek 21/29 (6/6) > Qwen 19/29
  (3/6). Fallback order now DeepSeek>MiniMax>Qwen; unparseable JSON
  advances the model chain instead of silently dropping an agent.
- Conflict detector validated on subtle conflicts: 4/4 caught, 0 false
  (`Subtle_Conflicts_Test.docx` checked in as regression doc).
- **OCR for scanned PDFs** (tesseract in prod image, 30-page cap):
  previously-unreadable image-only PDF now parses (8.3K chars); without
  OCR, scanned PDFs fail loudly and reviews of unreadable docs 422.
- Admin: platform-wide super-admin page (search over people/sign-ins/
  activity); dashboard flattened to one table; findings' "Section N"
  mentions are jump links; DOCX page numbers real.

Remaining accuracy work is human-dependency-blocked: ≥10-doc labeled
ground truth, calibration tuning against it, RFP labels, legal SME
severity sign-off.

**Scoring & reporting:** 7-category weighted scoring, severity now actually
read from findings (was keyword-matching only — fixed), PDF report
generation via `xhtml2pdf` (was a placeholder), stored-XSS fix in HTML
report generator.

**Frontend:** dashboard, upload, search, results pages retrofitted onto
shadcn/ui component library; shared `AppShell` layout.

**Security/functional audit (2026-07-17):** RBAC gap fixed, path traversal
fixed, S3 encryption added, login lockout wired to actual config, signup
endpoint added, review status lifecycle fixed (pending→running before
orchestrator dispatch).

**Test suite:** 641 passed, 6 skipped (full suite, last run 2026-08-01 —
includes the 58 MITRE Phase 0-2 + hardening tests).

**Router scope audit (2026-07-18, Step 1 of fix plan):** all 16 "extra"
routers beyond the original Phase 1 MVP list are mounted in `main.py` and
have real, DB-backed logic — none are dead code or stubs (one exception:
`collab_extra.py`'s comment endpoints 501 defensively if the `Comment`
model fails to import, not a placeholder). `governance.py` lacks a
router-level test (only its underlying service functions are tested).
Two stale docstrings claiming non-mounted status were fixed. Scope is
larger than the original MVP doc but legitimately shipped — not scope
creep to clean up.

**Bug-fix pass (2026-07-17/18, live UI testing):** 8 real bugs found and
fixed across upload, review pipeline, event-loop blocking, and dead
frontend routes — see `docs/RCA_LOG.md` for full root-cause detail on
each. Dashboard/search: sortable table, working type filter, stats row,
Accuracy/Completeness/Project columns, review-in-progress loading state.
Branding: renamed from "EDGP" to "ScopeWise" with a tagline and new
favicon/logo across the app.

**Risk scoring redesign (2026-07-19):** Risk Score changed from a
threshold-based model that pinned nearly everything at "100%, High" to a
saturating curve (`100 * (1 - e^(-k * severity_weighted_sum))`,
`k=0.0086`, recalibrated against real 30-400 point review volumes) plus a
new **Risk by Area** breakdown (per-axis: Compliance/Security/Governance/
Scope/Legal/Commercial/Delivery), stored on `Review.risk_breakdown`
(JSONB, migration 022) and tunable per-org via `org_risk_weights`
(mirrors the existing `app/admin/customization.py` pattern). Verified on
real production data showing actual discrimination across axes instead of
a flat 100%. Full rationale (ISO 31000/NIST, PMBOK, IACCM, FAR Part 15
citations) in `docs/planning/SCORING_METHODOLOGY.md`.

**Results page overhaul (2026-07-18/19):** full-screen layout, drag-
resizable findings/document split (33/66 default, hideable document
pane), clickable severity-filtered Findings Summary, a "Document X-Ray"
panel (parsed sections, missing-section detection), evidence-to-document
linking with scroll+highlight, and a mark-fixed/reopen action per finding
(`PATCH /reviews/{id}/findings/{finding_id}`) — explicitly labeled as an
unverified user claim, not a re-verified fix (see Document Lifecycle plan
below for why). `AppShell` sidebar made collapsible + drag-resizable.

**Public deployment (2026-07-19):** live at
https://scopewise.assessiq.in, self-hosted on a shared VPS
(`/opt/scopewise`, isolated Docker network/volumes/containers, ports
9094/9095), behind Cloudflare + the existing Caddy reverse proxy. Repo is
public at github.com/manishjnv/document-governance-platform.

**Document Lifecycle & Multi-Project planning (2026-07-19):** design-only
session (no code) on what happens when a customer marks a finding
"fixed," re-uploads a revised document, and manages multiple projects.
Decisions + full 3-phase implementation plan in
`docs/phases/prompts/DOCUMENT_LIFECYCLE_PLAN_PROMPT.md`; a combined
kickoff prompt for all 3 phases (Projects → Versioning →
Fix-verification diff) in
`docs/phases/prompts/DOCUMENT_LIFECYCLE_FULL_PROMPT.md`. **Not started.**

**Repo/process convention (2026-07-19):** added root `CLAUDE.md`
documenting docs/ folder layout, the migration-must-apply-to-4-places
rule, testing baselines, and VPS deployment specifics — written after a
process mistake (a "next session" prompt doc was saved to a scratch temp
directory instead of the established `docs/phases/prompts/` location).

**Document Lifecycle & Multi-Project implementation (2026-07-19):** all three
phases from `docs/phases/prompts/DOCUMENT_LIFECYCLE_PLAN_PROMPT.md` built in
one session.
- **Phase A (Projects):** new `projects` table (migration 023), `project_id`
  FK on `documents` alongside the existing free-text `project_name` (kept,
  not dropped — open question #3 resolved as "keep read-only" since the
  backfill script re-derives project_id from it and a human may still want
  the original label). `GET/POST /api/v1/projects` with per-project rollup
  stats (doc count, avg latest score, open-critical count). Upload accepts
  `project_id` or falls back to `project_name` (creates-on-the-fly).
  `scripts/backfill_projects.py` did the one-off data migration — exact
  `project_name` matches auto-map, near-duplicates flagged (not auto-merged)
  into `docs/phases/summaries/PROJECT_MIGRATION_REPORT.md` (open question #1
  resolved as a markdown report, not an admin endpoint — no admin UI exists
  yet to surface one). Dashboard groups by project (collapsible `<details>`
  sections — native HTML, no new dependency); new `/projects/[id]` detail
  page. Upload page's project field is a native `<datalist>` autocomplete +
  free-text create-new.
- **Phase B (Versioning):** discovered mid-session that backend primitives
  (`app/insights/similarity.py`, `app/routers/documents_extra.py` — T-2026
  through T-2029: similarity scoring, duplicate detection, version list,
  line-level text diff) already existed from an earlier, unrelated "Phase 2
  Wave 2" commit, wired into `main.py` but with no upload-flow trigger and
  no frontend. Reused rather than rebuilt. Added: migration 024
  (`document_link_suggestions` table +
  `organizations.similarity_suggestion_threshold`, open question #2 resolved
  as a per-org scalar column rather than the keyed
  `app/admin/customization.py` pattern — there's only one value to tune, a
  keyed table would be over-engineering); `suggest_version_link()` runs
  after every upload (text-similarity via existing cosine function OR
  filename similarity with version-suffix noise stripped —
  `_v2`/`(revised)`/etc.); dismissible suggestions persist on the Documents
  page (`GET/PATCH /api/v1/documents/suggestions`) rather than a one-time
  toast; explicit "Upload new version of..." action
  (`POST /{doc_id}/versions`); retroactive "link to existing document"
  action (`POST /{doc_id}/link`). Dashboard nests versions per document
  (expand/collapse) with a score trend arrow vs. the previous version. Never
  auto-links silently — every link is an explicit accept or upload action.
- **Phase C (Fix-verification diff):** `app/insights/fix_verification.py`
  matches a previous version's completed-review findings against a new
  review's findings by category (+ `section_ref` when both are present).
  Wired into `trigger_review` — a previous finding with no match is marked
  `resolved` with `notes.resolution = "verified"`; a finding that still
  matches is marked `still_present` and, critically, a prior manual "Mark
  Fixed" claim is reset back to `open` (the re-review's actual result always
  wins over the unverified claim, per the plan's core design decision).
  Reused the existing `notes` JSONB column on `Finding` instead of a new
  migration/CHECK-constraint change to the `status` enum. New
  `GET /{doc_id}/versions/{other_version}/finding-diff` endpoint powers a
  three-column Resolved/New/Persisted view at `/versions/diff`, linked
  directly from each version row's "Compare vs vN" action on the dashboard.
- **Not done / explicitly out of scope this session:** no manual browser
  click-through — verified via backend HTTP-layer tests (`pytest`, real
  Postgres) and `tsc --noEmit`, not a live UI session, given three phases in
  one session; state this explicitly rather than claim it. VPS deployment
  of these changes: see next action.

**OpenRouter model routing upgrade (2026-07-19/20):** benchmarked GLM-5.2,
MiniMax M3, Qwen3.7-Plus, and Kimi K3 as candidates on top of the existing
DeepSeek-only setup, using `LegalReviewer` against a sample SOW with
planted legal gaps. Found and fixed a real bug in the process: the
inherited `max_tokens=2000` (from the original Claude 3.5 Sonnet
integration) silently truncated 3 of 5 candidates because reasoning-mode
models spend completion tokens on hidden thinking before the visible
answer — see RCA_LOG.md entry #14. Raised to 4000, which fixed GLM-5.2
and MiniMax M3; Kimi K3 needed 8000 to complete but at ~$0.086/call
(10-15x the alternatives) so it was excluded on cost/latency grounds, not
quality. New chain: GLM-5.2 (primary) → MiniMax M3 → Qwen3.7-Plus →
DeepSeek (fallback, in order). Full methodology, per-model results, and
known gaps (only Legal reviewer tested, only one sample doc, no
long-document token-scaling test) in `docs/planning/AI_MODEL_ROUTING.md`.
Deployed to production (`apps/api` container rebuilt on the VPS).

**Project made mandatory on upload (2026-07-19/20):** `POST
/api/v1/documents` now 422s if neither `project_id` nor `project_name` is
given (upload form's client-side validation mirrors this); previously
project was optional, which is what produced the "unprojected documents"
case the Phase A backfill had to flag as near-duplicates rather than
auto-map. Added `PATCH /documents/{id}/project` to retroactively assign a
project to any document left unprojected by that backfill. 422/422 tests
still passing, `tsc --noEmit` clean. Deployed to production (both `api`
and `web` containers rebuilt).

**Sample documents (2026-07-19):** replaced the 2 generic placeholder
samples (`sample_rfp.docx`, `sample_sow.docx`) with real-world SOW/RFP
template sets under `docs/sample/{RFP_Sample,RFP_template,SOW_Template}/`
(~140 files) for manual UI testing across varied real document formats/
layouts.

**Seamless passwordless auth + Cloudflare AI-crawler fix + SEO Phase 1
(2026-07-20):** Removed all password UI from `/login` -- now Google
Sign-In + 4-digit email OTP only, both auto-provisioning a user/org on
first use via `_get_or_create_user` (`apps/api/app/routers/auth.py`).
Existing `/auth/login`, `/signup`, `/password-reset*` endpoints kept
as-is (unused by any UI, still used internally by ~15 test files as JWT
plumbing -- deliberate scope-limiting decision, not an oversight).
Found and fixed a live production issue: Cloudflare's zone-wide
`ai_bots_protection` bot-management setting was silently blocking every
AI crawler (GPTBot, ClaudeBot, Google-Extended, etc.) sitewide;
disabling it broke the managed robots.txt (404), fixed by adding a
native `apps/web/app/robots.ts`. Note this Cloudflare zone setting is
shared with `assessiq.in` (the main site) -- confirmed the main site's
own robots.txt is unaffected (served natively from its own origin), but
the zone-wide AI-bot-blocking policy itself is an open decision for the
user, not re-litigated here. Implemented SEO Phase 1 (Foundation)
directly in-session after discovering a scheduled cloud routine could
not push code (sandbox has no git write credentials): real marketing
homepage + `/product`, `/pricing`, `/about`, `/contact` pages, native
`sitemap.ts`/`robots.ts`, per-page metadata, JSON-LD schema. All live
and curl-verified on `scopewise.assessiq.in`. Full writeup:
`docs/phases/summaries/SESSION_HANDOFF_2026_07_20_LIFECYCLE_SSO_SEO.md`.

**MITRE ATT&CK coverage assessment — planning (2026-08-01):** design-only
session (no code). New fully-isolated module (`app/mitre/` + `/mitre`
frontend section, two one-line shared-file touchpoints): customer uploads
a SIEM use-case dump (tagged or untagged; xlsx/xls/csv/pdf/docx) + a
multi-sheet environment workbook (assets/platforms, log sources, security
tooling, crown jewels) + a slim on-screen intake (industry/region,
disabled-rules policy, scope exclusions with reasons), and gets an
executive + detailed gap assessment: coverage % overall / per domain
(Enterprise+ICS+Mobile) / per tactic / per technique,
applicability-filtered denominator with N/A-with-reason, assumptions,
exact per-gap recommendations, short/mid/long-term roadmap, PDF + XLSX
exports, trend comparison between runs. All decisions + 6-phase
implementation plan in `docs/planning/MITRE_ASSESSMENT_PLAN.md`.
**Phase 0 COMPLETE (2026-08-01):** pinned ATT&CK **v19.1** dataset
generated and checked in (`apps/api/app/mitre/data/attack.json`, 0.7 MB:
enterprise 858 techniques / 15 tactics, ics 118 / 12, mobile 190 / 14,
revoked+deprecated flagged; build via `scripts/build_attack_data.py`,
committed `ba645bc`). New pure-logic modules under `apps/api/app/mitre/`:
`attack_data.py` (module-level loader, `AttackIndex`, `resolve()` with
revoked→`superseded_by` remap), `applicability.py` (domain gating,
platform filter with PRE exemption + skip inside gated/excluded domains,
technique/platform/domain-scoped customer exclusions, most-specific-
reason-wins, loud no-inventory assumption) and `coverage.py`
(covered/partial/not_covered/not_applicable, 0.7/0.4 confidence
thresholds, `disabled_counts_as_coverage` param, sub-technique rollup,
multi-tactic counting, strict + weighted %). Curated
`data/technique_priorities.json` (40 techniques, tiers 1–3, sourced) —
**pending user review** (plan §15 Q3). Tests:
`tests/test_mitre_{applicability,coverage}.py`, 23 passed; full suite
**606 passed / 6 skipped**, 0 failures (the "402 passed / 2 skipped"
baseline in CLAUDE.md is stale — suite was already 571/6 on 2026-07-24).
Gotchas baked into the data: ATT&CK v19 restructured defense tampering
(T1562.001→T1685, T1070.001→T1685.005); mobile T1454 is revoked upstream
with no successor (allowlisted in the build validation); Mobile ships two
matrices (tactic extraction unions them).
**Phase 1 COMPLETE (2026-08-01):** persistence + ingest + API, tagged-only
end-to-end. Migration `029_mitre_assessment.sql` (4 new tables, zero
ALTERs, applied to `edgp_dev` + `edgp_test`; prod in Phase 5), models
`MitreAssessment/MitreFile/MitreUseCase` (+registry), `app/mitre/ingest.py`
(openpyxl/xlrd/csv direct-cell readers, header-synonym detection,
ATT&CK-platform normalization, 50MB/5k/10k caps, pdf/docx deferred to
Phase 2 with a plain-English 422), `router.py` (create+parse-preview /
run-202-with-stale-guard / list / get / use-cases / settings GET+PATCH /
soft-delete, all org-scoped) + `service.py` (fire-and-forget pipeline on
its own session; tag validation at create time so the preview shows the
tagged/untagged/invalid split; org tunables in `mitre_settings`). Shared
files touched: `main.py` (+2 lines), `app/models/__init__.py` (+3
imports/entries) — exactly the allowed set. Tests
`test_mitre_{ingest,api}.py` (16) green; **full suite 622 passed / 6
skipped**; live dev-server smoke run verified create→run→poll→results
with correct states and %s. Deviations (all declared in the handoff):
coverage thresholds became optional kwargs so org settings aren't dead
knobs; ICS "None"-platform techniques exempted from platform filtering
(real-data bug); audit rows use `resource_type='organization'`
(audit_logs CHECK is closed; extending it needs an ALTER — Phase 5
decision); timestamps in the module are tz-aware (naive utcnow breaks the
30-min stale-run guard on a +05:30 host).
**Phase 2 COMPLETE (2026-08-01, evening):** LLM tagging + narrative + gap
ranking. `app/mitre/agents.py`: `MitreTaggingAgent` (ConflictDetector
pattern, registered nowhere; two prompt modes via the `document_type`
param — "tagging" for ~25-row batches, "extraction" for pdf/docx text
chunks; all AI-emitted IDs re-validated through `attack_data.resolve()`,
sub-0.4-confidence dropped to unmapped) + `MitreNarrativeAgent`
(never-introduces-numbers rule; degrades to deterministic template text),
plus 60s/120s wait_for retry drivers — a failed batch degrades to unmapped;
only all-batches-failed + zero-customer-tags fails the assessment.
`app/mitre/ranking.py`: pure tier → feasibility → tactic gap ranking with
a keyword bridge from customer log-sources/tooling to ATT&CK
data-component categories; roadmap buckets short (source onboarded) /
mid (tooling owned) / long (new capability). Pipeline order now: extract
(pdf/docx, replaces the Phase 1 422) → AI-tag → applicability → coverage
→ rank → narrative → persist; `params.models_used` audit stamp. Prompts
documented in `PROMPT_ENGINEERING_GUIDE.md` (2026-08-01 section — NOT
mirrored to `prompts/`). Tests: +14 (`test_mitre_{agents,ranking}.py`,
LLM faked), all 53 mitre green, full suite **636 passed / 6 skipped**.
Live smoke: pipeline exercised end-to-end against a real OpenRouter
outage — the key is over its account spending cap (403 on all 4 models),
so the degrade paths are live-verified (unmapped + template narrative +
completed with honest assumptions) but the **AI-tagging quality
spot-check is PENDING a working key** — re-run
`mitre_smoke2`-style once the cap resets.
**Hardened + DEPLOYED TO PROD (2026-08-01, night):** pre-push adversarial
sign-off (Sonnet takeover per the codex:rescue outage) returned REVISE
with 3 blocking resource-exhaustion findings, all fixed same-session:
process-wide `Semaphore(3)` pipeline cap + early commits so the pooled DB
connection is released before every LLM wait (`expire_on_commit=False`);
workbook-wide xlsx/xls budgets (20 sheets / 15,050 cumulative rows /
64-col width — the old per-sheet cap allowed a many-sheet zip bomb);
pdf/docx extraction capped at 40 chunks + 5,000 rows with assumption
lines. Plus non-blocking: `log_source[:255]`, `description[:2000]`,
intake `industry/region[:200]`. Cross-org isolation and prompt-injection
containment passed clean. +5 cap tests → **full suite 641 passed / 6
skipped**. Deployed: commits through `14b1b7b` pushed, VPS containers
rebuilt with GIT_SHA, **migration 029 applied to `scopewise_prod`** (all
4 mitre tables verified), smoke: health 200, `/api/v1/mitre/assessments`
401 unauthenticated, /login 200. Note: prod AI tagging will degrade
gracefully (unmapped + template narrative) until the OpenRouter account
cap resets.
**Phase 3 COMPLETE (2026-08-01, night):** frontend. New
`apps/web/app/mitre/`: list page (status badge, strict-% bar with
weighted tooltip, empty state), `/mitre/new` single-page wizard (§2
privacy notice before any file, two drag-drop zones with client
validation, template download links, industry/region selects,
disabled-rules toggle, scope-exclusions editor, inline parse preview with
detected-column chips → run → redirect), `/mitre/[id]` results
(full-width; 5s visibility-aware polling while running; failed/pending
states with re-run; executive band; CSS-grid Navigator-style tactic
heatmap with click-through technique drawer via shadcn Sheet; ranked gap
table + short/mid/long roadmap with the narrative `generated_by` badge;
assumptions + grouped N/A appendix). 5 modular panel components under
`app/mitre/components/`, props-only. Templates
`public/templates/scopewise-mitre-{use-cases,environment}.xlsx`
(generated via throwaway script, verified through the real ingest
parser). Shared-file edit: exactly the one `AppShell.tsx` NAV_ITEMS entry
(`Target` icon). `tsc --noEmit` clean. **Verified in a real browser**
(playwright-core + local dev stack): full walk new → preview → run →
results, drawer, all three tabs, list; mobile 390px shows 0px horizontal
overflow on every page (one real bug found and fixed: the roadmap grid
lacked `grid-cols-1`, letting nowrap items force 48px page overflow).
Known deviation: per-domain mini-bars on the LIST page skipped — the
list endpoint returns only headline %s (API gap, noted for Phase 4's
list-endpoint touch).
**Phase 4 COMPLETE (2026-08-02, ~midnight):** reports + trend compare.
`app/mitre/report.py`: exec+detailed HTML report (house ReportGenerator
pattern — `_esc()` on every customer/LLM string, A4 print CSS, numbers
ONLY from stored summary/technique_results; use-case appendix capped at
500 rows with the XLSX holding everything) + lazy-WeasyPrint
`generate_pdf` + 8-sheet XLSX register with the formula-injection guard
(`=`/`+`/`-`/`@` → apostrophe prefix). `service.compare_assessments`:
pure diff (newly_covered / regressed / na_changed, overall + per-tactic
deltas, attack-version-mismatch flag). Endpoints:
`GET .../report?format=html|pdf` (base64-in-JSON, 409 non-completed,
viewer-readable per plan §15 Q1), `GET .../export.xlsx`
(StreamingResponse, real content-type), `GET .../compare/{other_id}`
(cross-org 404, non-completed 409), and `GET /assessments` now carries
`domains_brief` (closes the Phase 3 deferral, no N+1). Frontend:
PDF/XLSX download buttons (blob patterns, disabled-with-tooltip until
completed), a Compare tab (delta chips with improvement-is-green
semantics incl. inverted metrics, tactics-that-moved chips, 3-column
newly/regressed/N-A-changed lists), list-page per-domain mini-bars +
trend arrow vs previous completed run. Tests: +9
(`test_mitre_report.py` — XSS escape, formula guard incl. real workbook
readback, 409s, compare golden + cross-org 404, domains_brief; PDF test
auto-skips where WeasyPrint's native libs are absent). Full suite **649
passed / 7 skipped** (641 baseline + 8, +1 local-only PDF skip);
`tsc --noEmit` clean. Browser click-through: real XLSX downloaded via
the button and verified (8 sheets, `'=2+2` + `'=HYPERLINK` guards
visible), PDF button surfaces the graceful local-env error (WeasyPrint
is prod-image-only — full PDF check lands with Phase 5 deploy), compare
between two seeded runs showed correct deltas (+0.3 pts, 2 newly
covered, N/A change from the dropped exclusion), mobile 390px at 0px
overflow (one fix: `max-w-full` on the compare `<select>`).
**Phase 4 adversarial sign-off + PROD DEPLOY (2026-08-02):** pre-push
Sonnet-takeover review of the new surfaces (compare cross-org authz,
report XSS, XLSX injection across all 8 sheets) returned **ACCEPT**;
both non-blocking items fixed in the same commit — `compare_assessments`
now uses `.get()` on the unenforced `technique_results`/`summary` JSONB
so schema drift degrades instead of 500ing (+regression test), and the
three synchronous report/xlsx builders run via `run_in_threadpool` so a
large assessment can't stall the single-worker event loop. Pushed
through `8a608c0`, VPS rebuilt with `GIT_SHA=8a608c0`, live smoke green
(`/mitre` 200, `/api/v1/mitre/assessments` 401 unauth, health 200).
**Phase 5 COMPLETE — MITRE module LAUNCH-READY (2026-08-02):** closeout
phase, all tasks done. (1) **Real-PDF render smoke on prod: PASS** —
`generate_pdf` in the `scopewise-api` container returns a valid `%PDF`
(WeasyPrint native libs present), closing the only capability that
couldn't be tested locally. (2) **audit_logs resource_type enum**: chose
to extend the CHECK (audit clarity matters for a security product) —
migration `030_audit_mitre_resource_type.sql` adds `mitre_assessment`
(idempotent, transaction-wrapped), `enums.AuditResourceType` +
`app/models/audit_log.py`'s ORM `CheckConstraint` updated in lockstep,
and the create/complete/delete audit calls now use it (settings_updated
stays `organization` — genuinely an org-level change). (3) **Whole-module
adversarial review (Sonnet takeout)**: REVISE → fixed same-session — the
blocking find was a real bug this session introduced (the ORM
`CheckConstraint` in audit_log.py was the pre-030 5-value set; a
`create_all`-bootstrapped DB would 500 every mitre audit write — now a
documented 5th migration sync-point in CLAUDE.md); two non-blocking fixes
also applied (org_id added to the fire-and-forget pipeline queries to
honor the stated invariant; migration wrapped in a transaction). Endpoint
cross-org isolation, XSS/formula/prompt-injection containment, and
agents-absent-from-orchestrator all re-confirmed clean. Migration 030
applied to edgp_dev + edgp_test (prod on this deploy). Full suite **650
passed / 7 skipped**, `tsc` clean.

**§15 open questions resolved:** Q1 — viewers MAY download the XLSX/PDF
(same as review reports; accepted). Q2 — a marketing/SEO page for the
feature is a separate content task, not part of this build. Q3 —
`technique_priorities.json` is user-approved (stamped in-file 2026-08-01).

**Deferred by design (plan §14 — NOT blockers):** interactive
column-mapping wizard, per-mapping AI-override UI, threat-informed
actor/industry weighting, ATT&CK Navigator layer export, scheduled/
continuous re-assessment, per-rule detection-quality scoring. **No
residual blockers.** The AI-tagging *quality* spot-check was run
2026-08-02 against the real prod key (the SOW-audit key in `apps/api`
config / VPS `.env`, unlimited, account balance ~$17.26) inside the
`scopewise-api` container: **6/6 correct** (PowerShell `-enc`→T1059.001
+T1027, LSASS→T1003.001, schtasks→T1053.005, RDP brute force→T1110,
mimikatz→T1003.001, service 7045→T1543.003), one clean GLM-5.2 batch, no
hallucinated IDs. Correction to earlier notes in this doc: the prior
"AI tagging cap-blocked/pending" claim was wrong — it checked a separate
local tooling key ($OPENROUTER_API_KEY / ~/.openrouter-key, $2-capped),
not ScopeWise's key; prod AI tagging was never blocked. The project's
LLM key is read from `settings.openrouter_api_key` (app config / `.env`),
never the shell env — verify the app's LLM budget there or in-container,
not via a global env var.

**Phase 6 COMPLETE + DEPLOYED — coding-over-AI (2026-08-02, HEAD
`68ade56`):** committed as 4 logical units + router logic-cap follow-up,
migration 031 applied to scopewise_prod (CHECK verified), VPS rebuilt,
live smoke green (`/mitre` 200, keyword pre-pass verified in-container:
mimikatz→T1003.001 alias, schtasks→T1053.005 name). Deterministic
keyword/alias tagging pre-pass per
`docs/phases/prompts/MITRE_PHASE_6_CODING_OVER_AI_PROMPT.md`. (Task A)
New pure `app/mitre/keyword_tag.py` + curated
`app/mitre/data/keyword_aliases.json` (39 tool/command aliases with
cited sources): untagged rules are matched against exact ATT&CK
technique names (multi-word only, pre-compromise TA0042/TA0043
excluded, cross-domain-ambiguous names dropped) and literal alias
patterns with punctuation-significant boundaries (`at.exe` never fires
on "look at exe files"); every ID re-validated through
`attack_data.resolve()`; matches get `mapping_status='keyword_tagged'`
(migration `031_mitre_keyword_tagged_status.sql` + ORM CheckConstraint
in lockstep, applied to edgp_dev+edgp_test, **prod pending deploy**),
confidence 0.9, and skip the LLM — only the residue goes to AI tagging;
an AI-down run now survives on keyword matches alone. Drawer shows
"Matched by rule" via `SOURCE_META` (lib.ts). Quality gate on a 22-rule
realistic dump: **14 keyword-tagged / 8 AI (63% fewer AI calls), every
mapping hand-verified, zero false positives**, all near-miss traps
rejected. (Task B) ingest header/sheet/platform synonyms widened
(~90 real-world variants: "att&ck id", "mitre_ttp", "kql query", AKS,
Duo, Palo Alto, iPadOS, modbus…). (Task C) ranking feasibility maps
extended from a deterministic scan of all 113 ATT&CK data components —
new `mobile` (MDM/EMM) and `ot` (Claroty/Nozomi/Dragos) telemetry
categories fix mobile/ICS gaps wrongly bucketed "no standard
telemetry"; recon/threat-intel components left unmatched on purpose;
`test_deterministic_modules_import_no_ai` guards the whole pure layer.
(Task D) `build_mappings` regression test added (valid+revoked+invalid
in one row). **Adversarial sign-off (Sonnet takeover): REVISE → both
blocking findings fixed same-session → re-verified ACCEPT (reviewer
empirically confirmed all FP cases closed)** — (V1) MITRE recon/resource-dev
category-word names ("Credentials", "DNS Server") could false-map
benign ops rules at 0.9 and inflate coverage → excluded pre-compromise
tactics + single-word names from the name index (distinctive singles
live in the alias file), reviewer's 6 empirical FP rules pinned as
regression tests; (V2) uncapped 32K logic cells → ~50 min worker-thread
scan on a 5k-row dump → `_FIELD_CAP=2000` in the matcher + the router's
logic-fallback capped at the root. Non-blocking: the logic column is
dropped at create when BOTH description and logic exist (pre-existing
Phase 2 behavior; documented, needs a schema column — deferred to Phase 7,
`docs/phases/prompts/MITRE_PHASE_7_PERSIST_LOGIC_PROMPT.md`). Full
suite **686 passed / 7 skipped** (+36), `tsc` clean. DEPLOYED to prod
2026-08-02 (see header of this section).

**Phase 7 COMPLETE — persist detection logic (2026-08-02, committed +
pushed as `999ee5d`/`b183f75`, DEPLOYED: prod verified at `b183f75` with
migration 032 applied to `scopewise_prod`):** closes the one carried-over quality gap per
`docs/phases/prompts/MITRE_PHASE_7_PERSIST_LOGIC_PROMPT.md` — a dump
with BOTH a description and a logic column used to silently drop the
logic text at create time, so neither tagger ever saw the actual rule
condition. Migration `032_mitre_use_case_logic.sql` adds
`mitre_use_cases.logic` (plain nullable TEXT, no CHECK → 5th-sync-point
rule N/A; applied to edgp_dev+edgp_test, **prod pending deploy**);
the model gains the field; `router.create_assessment` stores
description and logic separately (logic keeps the Phase 6 `[:2000]`
cap); `service.py` feeds `uc.logic` to BOTH the keyword pre-pass and
the AI tagger (existing caps apply: `_FIELD_CAP=2000` scan,
`EXCERPT_CAP=500` LLM); XLSX "Use-Case Mappings" gains a `_guard`ed
"Logic" column (HTML report + drawer never showed description, so
nothing added there per the prompt's only-if-shown rule; nothing in the
frontend renders description — verified — so un-folding regresses no UI).
**Before/after on a 12-rule both-columns dump: keyword-tagged 1/12 →
10/12** (9 fewer rows to AI; all new mappings hand-verified; residue =
genuinely fuzzy rules only). New E2E regression test covers
persist-both + keyword-from-logic-only + AI-receives-logic; XLSX guard
test extended (J-column payload apostrophe-guarded). Light Sonnet
adversarial pass (logic-injection vectors): **ACCEPT, zero blocking**
(prompt injection / caps / report injection / NULL safety all verified
clean; narrative agent confirmed to never receive raw logic). Full suite
**687 passed / 7 skipped** (+1), no frontend change. **The MITRE module
now has NO known quality gaps** — everything remaining is plan-§14
optional feature work, built only on request. Deploy checklist: commit
→ push → VPS loop → **apply migration 032 to scopewise_prod** → smoke.

**Phase 8 COMPLETE — ATT&CK Navigator layer export (2026-08-02, commit
`cdf6cce`, DEPLOYED to prod in the `ed9cec9` deploy):** first optional
feature (plan §14) per
`docs/phases/prompts/MITRE_OPTIONAL_FEATURES_PROMPT.md`. New pure
`app/mitre/navigator.py` builds one Navigator layer (format 4.5) per
applicable domain from the stored `technique_results` — colors reuse the
report palette, N/A techniques are `enabled:false` with the reason as
the comment, `versions.attack` pinned from the assessment, no
timestamps (byte-stable golden tests). `GET
/assessments/{id}/navigator` (viewer-readable, org-scoped, 409 unless
completed) returns layer JSON for one domain or an in-memory zip of
per-domain layers; results page gains a "Navigator" download button next
to PDF/XLSX. No AI, no migration, no DB change; no adversarial review
required (read-only JSON, per the kickoff). 6 new tests (3 pure golden
plus endpoint json/zip/authz). Full suite **702 passed / 7 skipped** (Phases 8+9 certified together on an isolated test DB); `tsc` clean.
`MITRE_MODULE_REFERENCE.md` API table updated. Deployed 2026-08-02 with
Phase 9 (VPS at `ed9cec9`, no prod migration); live smoke: `/mitre` 200,
navigator endpoint mounted + auth-gated (401 unauth), GIT_SHA confirmed
in-container.

**Phase 9 COMPLETE — interactive column-mapping wizard (2026-08-02,
commit `ed9cec9`, DEPLOYED to prod):** second optional feature (plan
§14). When auto-detection maps a dump wrong or misses a column (tags
under a non-synonym header being the classic), the wizard now shows the
raw header row + first 5 sample rows and lets the user map the six
ScopeWise fields by hand; `POST /assessments/{id}/remap`
(admin/reviewer, org-scoped, pending-only) re-downloads the stored file
and re-parses it with the explicit map (`validate_column_override`:
unknown fields / out-of-range / bool-as-int / duplicate targets /
missing name all 422), replacing the parsed rows and updating
`params.columns` — with an **atomic status-conditional guard** in the
same transaction as the row replacement so a concurrent /run can't
interleave (a real TOCTOU found in self-review AND independently
flagged as the Sonnet reviewer's one blocking finding; fix is the
reviewer's own prescribed pattern, re-verified ACCEPT). Review's two
smaller items applied: remap parse offloaded via `run_in_threadpool`,
and the pre-existing CSV reader cap gap closed (MAX_ROW_CELLS /
MAX_TOTAL_ROWS now enforced like xlsx/xls). Create-time 422 for a
wholly undetectable name column still stands (template escape hatch) —
remap corrects wrong/missed columns on an otherwise-detected sheet.
9 new tests (6 remap E2E incl. authz/TOCTOU-409/extraction-422 + 3
ingest unit). Full suite **702 passed / 7 skipped** (Phases 8+9 certified together on an isolated test DB); `tsc` clean. Test-infra note:
concurrent-session suite runs on shared `edgp_test` caused repeated
deadlocks/phantom failures today — resolved via a session-private
schema-cloned DB + `TEST_DATABASE_URL` (protocol in memory:
`edgp-test-single-runner-rule`).

**Phase 10 COMPLETE — per-mapping reviewer override + inline recompute
(2026-08-02, commit `6ce8e48`, DEPLOYED to prod):** third optional
feature (plan §14). An admin/reviewer can now correct one rule's
technique mappings post-run (remove a wrong AI/keyword tag, add a missing
one, or unmap entirely) via
`PATCH /assessments/{id}/use-cases/{use_case_id}/mappings` — body is the
FULL new technique-ID list (max 20), every ID validated through
`attack_data.resolve()` (revoked→successor with a note;
deprecated/unknown/malformed → 422), row becomes
`mapping_status='manual'` with `source='manual'` @ confidence 1.0
(migration 033 extends the CHECK + the ORM CheckConstraint in lockstep —
the 5th sync point honored). Coverage/gaps/roadmap/N-A/counts are then
**recomputed inline by the pure engines** (`service.recompute_results`,
no LLM) using the thresholds stamped at run time; narrative prose is
kept with an assumption note that it may predate the edit.
`SELECT … FOR UPDATE` on the assessment serializes concurrent edits;
completed-only (409 otherwise); audited as `mitre.mappings_edited`.
Drawer UI: role-gated remove-X per mapped rule + "map another rule to
this technique" select, provenance badge "Edited by reviewer". 5 new
tests (recompute state-flip + counts + audit row, empty-list unmap,
invalid/over-cap 422s, non-completed 409, cross-org 404 both ways +
viewer 403). Full suite **707 passed / 7 skipped** (solo on shared
`edgp_test`); `tsc` clean; Sonnet adversarial review **ACCEPT** (no
blocking findings; verified cross-org scoping, resolve() coverage,
recompute parity with the pipeline's persist block, FOR UPDATE race
handling, audit correctness).

**Phase 11 COMPLETE — threat-informed gap weighting (2026-08-02, commit
`62f1df2`, DEPLOYED to prod):** fourth optional feature (plan §14),
fully deterministic per the coding-over-AI rule — no LLM anywhere in the
path. New curated `app/mitre/data/threat_profiles.json`: 10 industry
profiles keyed to the wizard's INDUSTRIES values (banking/insurance
alias onto financial services) + 10 named ATT&CK groups (FIN7, Wizard
Spider, Lazarus, APT28/29/41, Sandworm, Volt Typhoon, Scattered Spider,
LockBit affiliates), 143 technique IDs total, every one machine-validated
to resolve `ok` against the pinned v19.1 dataset (test-enforced), sources
cited in the file header (DBIR 2025, CISA #StopRansomware/AA23-325A/
AA23-320A/AA24-038A, M-Trends, Dragos, HC3, FS-ISAC, ATT&CK Groups).
`ranking.build_threat_profile()` + a second sort key right after tier:
profile-relevant gaps rank above EQUAL-TIER peers — never a tier jump,
never any change to coverage %/states (ranking runs strictly downstream
of coverage; verified in review). Gaps carry `threat_relevance` labels;
the narrative's top-gaps input includes them; an assumption line records
the active profile. Org tunable `threat_weighting_enabled` (default on,
`mitre_settings` pattern); the Phase 10 recompute path honors the same
profile + the toggle stamped in `params.thresholds`. Intake gains
optional `threat_actors` (validated against the curated catalog, deduped,
max 10, unknown → 422); new `GET /threat-catalog` endpoint feeds the
wizard's actor chips; gap rows show a violet "Threat match" chip with a
plain-English tooltip. No migration. 6 new tests
(`test_mitre_threat_profile.py`) + the settings round-trip updated for
the 5th tunable. Full suite **713 passed / 7 skipped** (solo on shared
`edgp_test`); `tsc` clean; Sonnet light review **ACCEPT** (one cosmetic
duplicate-actor note, fixed same session).

**Phase 12 COMPLETE — per-rule detection-strength scoring (2026-08-02,
commit `436612a`, DEPLOYED to prod):** fifth optional feature (plan §14),
coding-first per the coding-over-AI rule. New pure
`app/mitre/quality.py`: a deterministic 0-100 "detection strength" per
covered/partial technique that has direct qualifying rules — provenance
base (customer/manual 30, keyword 25, high-conf AI 20, low-conf AI 10) +
enabled bonus (30 / 15 unknown / 0 disabled, so a disabled rule can
never read "strong") + detection-logic-present (10) + telemetry match
(30: the rule's log_source/logic, capped at 2000 chars, run through
ranking.py's existing data-component category bridge against the
technique's ATT&CK data sources) + redundancy (5 per extra rule, cap
10). Buckets strong ≥75 / moderate ≥45 / weak; rationale built from
fixed fragments only (no raw rule text). Stored as
`strength`/`strength_rationale` on technique_results + a
`summary.quality` rollup {scored, avg_strength, strong, moderate, weak}.
**Deliberately separate from coverage %** — coverage/applicability/
ranking untouched (review-verified); the methodology footnote's
"presence, not efficacy" caveat now has its efficacy counterpart.
**AI strictly optional:** new `MitreQualityAgent` (own prompt, rubric
bands matching the heuristic buckets) re-rates only
heuristic-inconclusive items (logic present, expected telemetry known,
no match), gated behind new org setting `quality_ai_enabled` — **OFF by
default** — capped 40 items/25-per-batch/500-char excerpts, outputs
clamped 0-100 with unknown IDs dropped, any failure keeps the heuristic;
merged scores visibly prefixed "AI-assessed:". The Phase 10 manual-edit
recompute re-annotates heuristic-only. UI: strength chip + rationale in
the technique drawer, a "Strength" column on gap rows; tooltips state
it is distinct from the coverage %. No migration. 10 new tests
(`test_mitre_quality.py`) + the settings round-trip gained the 6th key.
Full suite **723 passed / 7 skipped**; `tsc` clean; Sonnet review
**ACCEPT** (7/7 checks, zero findings). Prompt documented in
`PROMPT_ENGINEERING_GUIDE.md`.

**Phase 13 SIEM integration — DESIGN APPROVED + 13a COMPLETE (2026-08-02):**
multi-session sub-project (design → 13a connector → 13b vault → 13c
scheduler → 13d observability). Design locked in
`docs/planning/MITRE_SIEM_INTEGRATION_PLAN.md` (Sentinel first,
token-at-trigger before an encrypted vault, CSV-artifact reuse of the
create path, resolve-then-pin egress, worker+beat single container,
honest env-key compromise); per-sub-phase kickoff prompts in
`docs/phases/prompts/MITRE_SIEM_SUBPHASE_PROMPTS.md`.
**13a done (committed, NOT deployed):** `app/mitre/connectors/`
(`egress.py` stdlib SSRF guard — allowlist-before-resolve, resolve-then-pin
global-unicast-only, TLS-SNI-on-hostname closes rebinding, redirects
errored, caps, NaN-safe Retry-After; `sentinel.py` Entra→alertRules pull
normalized to the template CSV; `base.py` dispatch) + `POST
/assessments/from-siem` (secret in-request only, popped/used-once/never
stored; feeds the existing create path via extracted
`_persist_new_assessment`) + a "Pull from Sentinel" wizard tab. No
migration. Adversarial sign-off REVISE→ACCEPT (hostile Retry-After crash
+ dot-only resource-group regex, both fixed). 32 new tests; **full suite
755 passed / 7 skipped**; `tsc` clean. Commits `598c2dc` (design docs) +
`09b545e` (13a code).
**13b done (credential vault):** migration 034 `mitre_connections`
(org-scoped, soft-delete, `secret_ciphertext` BYTEA, `key_version`,
platform CHECK + ORM lockstep); `connectors/vault.py` AES-256-GCM
(fresh nonce/encryption, ciphertext AAD-bound to connection_id, fail-
closed key_version, master key from `SIEM_CRED_KEY` env — documented
no-KMS shared-VPS compromise); admin-only connections CRUD with the
secret WRITE-ONLY (popped/del'd, never returned/logged/echoed) +
`POST /connections/{id}/test` + `POST /assessments/from-connection/{id}`
(decrypt in-process only, `del` in finally); vault-unconfigured → clean
503. 10 new tests (crypto round-trip, AAD-transplant/key-version/corrupt
refusal, secret-absence scans, log-scrubbing); **full suite 765/7**;
`tsc` clean. Heaviest Sonnet sign-off ACCEPT (empirical crypto probes).
**13c+13d done (`496b2bb`, DEPLOYED — Phase 13 COMPLETE):**
scheduler/worker — `scopewise-worker` compose service (Celery worker +
in-process beat, no ports, 512m/0.5cpu, least-privilege env: no
JWT/OAuth), migration 035 schedule columns (+3 ORM CHECKs in lockstep),
admin PATCH schedule validation, 15-min sweep with advance-on-enqueue
dedup, **stale-running self-heal** (a crashed run can't block the
schedule; review fix) and pending previews non-blocking, per-call-engine
discipline everywhere + `run_assessment_pipeline(session_factory=…)`;
scheduled failures land as visible `failed` assessments. Provenance +
observability — `params.siem` on the list (chip), results header, and
report audit footer; `GET /connections` health (last pull/error +
consecutive scheduled-failure streak); **admin email at exactly 2
consecutive scheduled failures** (one notice per streak, reset on
success, stale-flips notify too — review fix; never secrets/rule
content, CRLF-collapsed names harden the Subject header);
`/mitre/connections` admin health page. Also closed the 13b prod gap
(`SIEM_CRED_KEY` was missing from the compose env). Both sub-phase
reviews REVISE→fixed→ACCEPT. 18 new tests; **full suite 781 passed /
7 skipped**; `tsc` clean. Ops: worker env needs `SIEM_CRED_KEY` +
`SMTP_*`; migrations 034–035 in all 3 DBs.

**MITRE Phase 14a COMPLETE (2026-08-02) — gap drill-down drawer (UX
clarity for non-technical users):** first of six sub-phases in
`docs/planning/MITRE_UX_CLARITY_PLAN.md` (kickoff prompts:
`docs/phases/prompts/MITRE_PHASE_14_UX_PROMPT.md`; 14b–14f pending).
The technique drawer now renders four plain-language blocks for every
state — *what is this* (curated definition + "attackers use this to…"),
*where is the gap* (tactic story line, your-log-source-that-could-see-it,
platforms), *why is it a gap* (deterministic one-sentence why-phrase:
no-rule count / disabled rule / low-confidence AI / sub-technique rollup /
covered proof + strength / N-A verbatim), *what would good look like*
(vendor-neutral detection sketch + closest-covered-rule starting point).
Backing: two NEW hand-curated data files
(`app/mitre/data/technique_plain_language.json` — 57 techniques =
priorities ∪ threat-profiles union; `data/tactic_lines.json` — 21 tactic
shortnames), pure `app/mitre/plain_language.py`, and
`GET /assessments/{id}/techniques/{tid}/explain` (org-scoped, read-only,
deterministic — no runtime LLM, no migration, no pipeline change). 16 new
tests (file validation vs the pinned dataset, why-phrase goldens incl.
the sample-kit covered-vs-disabled acceptance, endpoint E2E); **full
suite 797 passed / 7 skipped**; `tsc` clean.

**MITRE Phase 14 COMPLETE — 14b–14g all shipped (2026-08-02, one
session):** the remaining six sub-phases of
`docs/planning/MITRE_UX_CLARITY_PLAN.md`, one commit each. **14b**
(`eea44e3`) every number clickable — DrillDownPanel + RuleListPanel
behind tiles/heatmap headers/N-A counts/rule chips/wizard preview tiles,
names enriched into GET, headline subtitle + "is this % bad?" popover,
pluralization + header-definition microcopy. **14c** (`4a2325f`) XLSX
polish — Read Me guide sheet, color fills, register Name/plain-words/Why
columns, numeric sort + plain statuses, feasibility-grouped gaps,
Summary explanations. **14d** (`36415d2`) project metadata riding
params.intake (no migration) + files[] in GET + wizard inputs + header
line + UploadSummaryCard; also lands the 14g parser (additive per-entry
environment `interpretations`). **14e** (`c15ab34`) PDF redesign — cover
with metadata/upload summary/TOC (real page numbers), ≤2-page executive
(traffic-light scorecard, top-5 fixes with curated definitions + threat
tie-ins + cross-refs, effort-to-impact projection, trend vs previous
run), detailed stacked bars/heatmap grids/feasibility-grouped gap
register with why+sketch+via+AI badge per entry, evidence appendix.
**14f** (`c64b324`) past-run history — header Past-runs dropdown with
delta + Compare shortcut, list search/filter/sparkline, inline rename +
soft archive (JSONB flag, PATCH endpoint, no deletes, archived stays in
Compare). **14g** (`bee1f8f`) evidence trail — explain gains
expected-telemetry + in-scope-because, rule panel shows the mapping
journey verbatim, XLSX How-We-Read-Your-Files sheet, threat-profile
matches chip. No migrations anywhere in Phase 14; **full suite 800
passed / 7 skipped**; `tsc` clean; deployed to prod.

**MITRE Phase 14 polish — user-feedback pass (2026-08-02, deployed
`4f93523`):** five refinements from walking the deployed UI. **(1)
Resizable panels** (`6051af6`): drawer + both drill-down panels gain a
mouse-draggable left-edge handle (`useSheetResize.tsx` — shared width
remembered in localStorage, keyboard-arrow accessible, clamped to the
viewport; phones stay full-width). **(2) Heatmap context** (`6051af6`):
cells show "ID Name" truncated in the same footprint; one delegated
custom tooltip serves all ~900 cells (solid background, smooth fade,
plain-words state + N/A reason) instead of native `title`; drawer hides
the ICS "None"/PRE pseudo-platforms and fixes a/an grammar; mobile
guards added (past-runs dropdown viewport clamp, header row wraps).
**(3) XLSX Summary redesign** (`bdde5f5`): sectioned sheet with branded
title band, EXECUTIVE SUMMARY (narrative text + "is this % bad?"
context), KEY NUMBERS (traffic-light coverage cell, state-colored
counts), TOP 5 THINGS TO FIX FIRST (effort fills + recommendations),
ABOUT THIS ASSESSMENT. **(4) Gaps table density** (`4f93523`): rows
~50% tighter, single-line technique, pastel pills replaced with
dot+text that carries meaning — "P1 · Critical", "70 · Moderate",
"Build now · via Sysmon". **(5) Assumptions & N/A redesign**
(`4f93523`): two-column accent-bordered assumptions grid; N/A appendix
as reason-aggregated group cards (37 identical "deprecated" rows → one
line) with technique chips that open the drawer. Numbers untouched;
suite stays **800/7**, `tsc` clean.

**Polish wave 2 (same evening, deployed `2698eda`):** heatmap hover
fixes — tooltip out of the space-y margin flow (`9eabcd1`), hover-intent
glide between cells + collapsible matrices + legend-as-filter
(`4d579c2`); report tables bordered grid with brand-blue headers and
zebra rows (`35f5d40`); readability + space pass — no light-grey fonts,
filled state/priority pills, N/A appendix one-row-per-reason,
two-column assumptions, compact appendix tables (`a9534b5`);
attack-stage tables gain header rows + balanced columns and the XLSX
gains all-cell borders (`9256ab1`); the `/mitre` list page becomes a
responsive card grid with plain-words coverage lines and labeled matrix
bars (`b8d0e75`); export scopes land — `scope=executive` 1–3 page
leadership PDF, per-tab PDF/Excel cuts inline in the tab bar, clarified
Navigator tooltip — plus the XLSX Summary emphasis pass (visible
all-cell borders, executive summary as five compact bold/italic
pointers, bold centered values) and the on-page "is it covered?"
search over technique/tactic/platform/rule with state-grouped results
(`2698eda`). Suite **801 passed / 7 skipped** (executive-scope test
added); `tsc` clean; all render-verified in the prod container.

**MITRE Phase 14h — report branding & polish (2026-08-02), 4 sequential
commits, full detail in `docs/planning/MITRE_MODULE_REFERENCE.md` §11/§15:**
**(1) Refactor** (`fa7ba86`): split the monolithic `report.py` into
Jinja2 `templates/` (base/cover/executive/detail/appendix/style.css) +
`report_common.py` (shared constants/helpers) + `report_xlsx.py` (XLSX
builder) — zero behavior change, pure structural split.
**(2) Branding** (`e5ff17a`): three new org-scoped `mitre_settings`
overrides — report display name, accent color (hex-validated), optional
watermark text — flow through to both the PDF (logo + repeating page
header + diagonal watermark via WeasyPrint CSS GCPM) and the XLSX
builder; no migration (reuses the existing generic settings table).
**(3) XLSX polish** (`77221f9`): native `DataBarRule` conditional
formatting + a `BarChart` on the Coverage by Tactic sheet; a genuine
3-color `ColorScaleRule` and a numeric (sortable) Priority column with
a `"P"0` display format on Gaps & Recommendations, replacing the old
static per-tier cell fill; `Read Me` sheet protection
(`protection.sheet = True`, no password — accidental-edit guard only);
workbook core properties (title/creator/description) — openpyxl-native
only throughout, xlsxwriter intentionally never used. Note: openpyxl has
no wired-up support for the docProps "Company" extended property (dead
code excluded from serialization in the library itself, confirmed by
source inspection); `description` carries the org display name instead.
**(4) PDF metadata + docs** (this update): `<meta>` tags in `base.html`
so WeasyPrint stamps `/Author`, `/Subject`, `/Keywords` on the generated
PDF; this doc and `MITRE_MODULE_REFERENCE.md` updated. All four units
verified individually and together against the full backend suite (no
regressions, no computed number changed anywhere) and `tsc --noEmit`;
no DB migration in any of the four. Suite **802 passed / 7 skipped**
after unit 3 (+1 new XLSX-polish test).
**Post-14h (2026-08-02/03):** deploy exposed a missing `Jinja2` pin in
`requirements.txt` (prod crash-loop, hotfixed + redeployed as
`f7b5263` — dev-installed-but-undeclared deps are invisible locally,
fatal in the image). **Independently verified 2026-08-03** by the
orchestrating session: suite **803 passed / 7 skipped** (new baseline,
CLAUDE.md updated), `tsc` clean, prod at `f7b5263` with all 5
containers healthy and `/health` + login 200; no migrations, no
scoring-code changes, no forbidden libs; a stray uncommitted
`.gitignore` `*docs/` line (would have ignored the whole docs/ tree)
was caught and reverted. Handoff:
`docs/phases/summaries/SESSION_HANDOFF_2026_08_03_MITRE_KIT_P14_VERIFY.md`.

**MITRE Phase 14i — "What logs do I need?" per gap (2026-08-03, plan
§14h's second, distinctly-titled section in `MITRE_UX_CLARITY_PLAN.md`;
relabeled 14i in the module reference to avoid colliding with the
already-shipped report-branding Phase 14h):** closes the gap where a
not-covered technique named a log-source *category* but never the
**fields** a query needs or why an already-onboarded source might still
lack them. New curated `app/mitre/data/telemetry_fields.json`: the top 35
(of 113) ATT&CK data-source components by technique-reference frequency
(83%/88% coverage at top 25/35, measured against the pinned v19.1
dataset), each with hand-written `fields` (plain-English query
parameters), `where` (vendor-neutral usual event sources), and `gotcha`
(the single most common reason an already-onboarded source still can't
support the detection — never generated at runtime, reviewed like code).
Pure `plain_language.telemetry_requirements()` (curated entry or bare
component-name fallback for the long tail) + `telemetry_lines()`
(shared deterministic one-line-per-component rendering). Surfaced in
exactly three read-only places, no new UI area: `explain` endpoint gains
`good.telemetry`, rendered in the drawer's existing "What would good look
like?" block (one compact line per component — fields, where, then the
gotcha in muted text); XLSX Gaps & Recommendations gains a "Log fields
needed" column (existing bordered/wrapped styling helpers reused, no new
styling code); PDF/HTML gap register gains one "Log fields needed" line
per gap under the existing detection sketch. Honesty boundary held
throughout — every surface reads "your query needs X; your `<source>`
should carry it," never "your source is missing X," since the product
never ingests raw logs and cannot verify field-level coverage. No
coverage/scoring/pipeline change, no migration, no new settings; the 62
techniques with no ATT&CK data sources keep their unchanged "bespoke
detection engineering" verdict. Tests: 6 new in
`test_mitre_plain_language.py` (component-key validity against
attack.json, entry completeness, all-35-present guard,
curated-vs-uncurated-degrade goldens for T1059.001/T1219.003, explain
endpoint wiring) + the XLSX structure golden in `test_mitre_report.py`
extended for the new column. Verified end to end against the regenerated
sample kit (T1059.001 gap shows fields+where+gotcha identically in the
drawer data, the XLSX cell, and the PDF/HTML register). Suite **809
passed / 7 skipped** (+6 over the 803/7 baseline); `tsc --noEmit` clean;
`docs/planning/MITRE_MODULE_REFERENCE.md` updated (file map, API table,
§11 reports, §13 tests, §15 history).

---

## ⏳ Pending (not deferred — actual launch blockers)

| Item | Status | Blocker |
|---|---|---|
| AI accuracy validation (Metrics 1.1-1.4) | **Measured 2026-07-18** on a 12-doc synthetic set: rule-engine precision/recall **100%/100% PASS**; confidence calibration **17.95% error, FAIL**; dedup **NOT MEASURABLE**. **2026-07-20: dedup built, prompt-accuracy revision shipped, and validated live against real OpenRouter output** on a real 46-page federal contract (`docs/planning/5_LAUNCH_CRITERIA.md`'s "Real-document spot-check" section) — found and fixed 3 real bugs in the process (`max_tokens` too small for large docs, no timeout retry, 3 of 6 agents missing an `evidence` field entirely). Calibration and new checklist items visibly worked correctly on real output. **Still not a scored precision/recall pass** — that needs hand-built ground truth. | Real ≥10-doc test set still needed for a full scored pass. `docs/sample/Real_Federal_Contracts/` added 2026-07-20 (4 real, awarded federal contracts) as the current best real-document source — still government-only, no real commercial SOW/RFP exists in-repo yet, and still short of 10. |
| ~~Finding deduplication is unimplemented~~ **Built 2026-07-20** | `orchestrator._merge_findings()` now cross-agent-deduplicates via evidence-text similarity (`apps/api/app/ai/orchestrator.py::_dedupe_findings`, stdlib `difflib`, no ML dependency) | None — built and validated live (0 false merges across 93 real findings tested this session) |
| **DOCX table-only documents parsed to empty text** (found 2026-07-20, RCA #16) | **Fixed.** `DocxParser.parse()` only walked `doc.paragraphs`; any table-laid-out document (common real-world SOW/RFP template pattern) silently returned `status="success"` with `raw_text=""`. Now walks `doc.iter_inner_content()` (paragraphs + tables in order). | None — fixed, tested, deployed |
| **3 of 6 agents never had an `evidence` field in their schema** (found 2026-07-20 via live testing) | **Fixed.** Delivery/Commercial/Security silently broke dedup + clause-location for their findings since both depend on evidence text. Added the field + quote instruction, matching Scope/PMO/Legal. | None — fixed, tested, deployed |
| **`max_tokens=4000` too small for large real documents** (found 2026-07-20) | **Fixed.** Raised to 8000 — GLM-5.2 was hitting `finish_reason="length"` and returning truncated JSON on ~30K-token real documents. | None — fixed, deployed |
| **Agent timeout had no retry** (found 2026-07-20) | **Fixed.** A live run showed a different agent randomly hitting the 60s ceiling each time (latency variance, not a per-agent issue) — added one retry at 90s. | None — fixed, tested, deployed |
| Legal severity calibration | Worksheet prepared (`docs/planning/LEGAL_SEVERITY_CALIBRATION.md`) | Needs a legal SME to actually fill in the comparison table and sign off — scheduling action, not implementation work |

## Deferred by design (see phase prompt docs for rationale, not re-litigated here)

- Phase 3: DB scaling infra (read replicas, partitioning, tracing, ELK, Grafana), mobile app
- Phase 4: ML/analytics (no training data yet)
- Phase 5: Enterprise integrations (no signed contracts)
- Phase 6: SLA credits, video training, partner program (kept: bare ticket + KB CRUD)
- Phase 7: SOC2/pen-testing, feedback/NPS (kept: informal bug-triage/patching practice)

---

## Key files

Backend: `apps/api/app/ai/agent.py` (6 agents + OpenRouter dev/test adapter),
`apps/api/app/ai/orchestrator.py`, `apps/api/app/rules/` (engine + builtin +
ambiguous_language), `apps/api/app/scoring/`, `apps/api/app/core/login_lockout.py`.

Frontend: `apps/web/app/{dashboard,upload,search,results,login}/page.tsx`,
`apps/web/components/AppShell.tsx`.

Docs: `docs/planning/4_AI_AGENT_SPECS.md` (agent specs), `docs/planning/5_LAUNCH_CRITERIA.md`
(launch gate metrics + measured results), `docs/planning/PROMPT_ENGINEERING_GUIDE.md`
(prompt-revision rationale, sources, changelog — read before editing any agent's prompt),
`docs/planning/LEGAL_SEVERITY_CALIBRATION.md`
(SME worksheet), `docs/RCA_LOG.md` (every bug fixed this session, root cause +
prevention), `docs/phases/prompts/PHASE_{3-7}_PROMPT.md` (scope-trim rationale per phase).
`prompts/*.md` — auto-generated read-only mirror of agent prompts, regenerate via
`python scripts/generate_prompt_docs.py` after editing `agent.py`.

---

## Next action

1. **Manual browser click-through still open** for Projects/Versioning/
   Fix-verification flows, mandatory-project upload validation, seamless
   Google/OTP login, and the new marketing pages -- all deployed and
   backend/type-checked or live-`curl`-verified, but not yet driven
   through an actual browser session.
2. **SEO: Phase 1-2 fully done, Phase 3-4 partially done (2026-07-20).**
   GSC sitemap submitted (existing `assessiq.in` Domain property covers
   the subdomain, no separate verification needed -- waiting on Google's
   crawl to confirm "Success"), GA4 live (`G-BS21BGYW3B`, base pageviews
   only, no per-CTA events yet), Lighthouse baseline recorded (homepage
   79, /product 89). Phase 2 fully shipped: 3 use-case pages, 3 solution
   pages, all 15 glossary terms, internal linking. Phase 3-4: blog engine
   built + 3 of 8 Month 1-2 posts published (5 more + all of Month 3-4
   still to draft), `/compare/*` and case study still blocked on legal
   sign-off / a real customer respectively. Full detail:
   `docs/phases/summaries/SESSION_HANDOFF_2026_07_20_SEO_PHASE2_4.md` and
   the checklist in `docs/planning/seo/IMPLEMENTATION_ROADMAP.md`.
3. **Model routing: only spot-tested.** `AI_MODEL_ROUTING.md`'s benchmark
   covered one reviewer type (Legal) on one sample document. Worth a
   broader sweep (other 5 reviewer types, RFP docs, longer documents)
   before fully trusting GLM-5.2/MiniMax M3 output in production —
   current confidence is "fixed a real bug, spot-checked the fix," not a
   full accuracy validation.
3. **Build finding deduplication** — currently doesn't exist at all;
   Metric 1.4 is structurally unmeasurable until this is built.
4. Fix confidence calibration (17.95% error vs. <5% target) — likely needs
   agent prompt tuning per `docs/RCA_LOG.md`-style root-cause approach, not
   a blind confidence-score rescale.
5. Get a real ≥10-doc test set (user-supplied or approved synthetic) and
   re-run the full Metrics 1.1-1.4 validation against it — the 2026-07-18
   synthetic pass is a stopgap, not launch-gate evidence.
6. Get legal SME sign-off on `LEGAL_SEVERITY_CALIBRATION.md`.
7. Everything else in Phase 1-2 core scope (including the 16 "extra"
   routers, confirmed real 2026-07-18) is done and live in production;
   Phase 3-7 items are deliberately deferred, not blockers.
