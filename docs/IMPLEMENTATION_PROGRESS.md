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

**Phase 6 COMPLETE — coding-over-AI (2026-08-02, built, NOT yet
committed/deployed):** deterministic keyword/alias tagging pre-pass per
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
Phase 2 behavior; documented, needs a schema column — deferred). Full
suite **686 passed / 7 skipped** (+36), `tsc` clean. Deploy checklist:
commit → push → VPS loop → **apply migration 031 to scopewise_prod** →
smoke.

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
