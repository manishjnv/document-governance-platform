# RCA / Incident Log

One entry per bug fixed during manual/live testing. Format: symptom → root
cause → fix (file:line) → prevention. Check this log before touching a file
listed below — several of these are copy-pasted patterns that recur.

---

## 2026-07-17/18: Live UI testing session (upload → review → search → dashboard)

### 1. Upload always 500'd: `s3_path` NOT NULL violation
- **Symptom:** every document upload returned 500, DB log showed
  `NotNullViolationError: null value in column "s3_path"`.
- **Root cause:** `Document(...)` constructor in `upload_document` never set
  `s3_path`, even though `storage.upload(storage_path, content)` computed it.
- **Fix:** `apps/api/app/routers/documents.py` — added `s3_path=storage_path`
  to the `Document(...)` call.
- **Prevention:** any new required column on `Document` needs someone to
  grep every `Document(...)` construction site, not just add the column.

### 2. Upload 500'd (2nd time, after #1 fixed): file_type case mismatch
- **Symptom:** `CheckViolationError: ck_documents_file_type` — DB only
  allows lowercase `'pdf'/'docx'`.
- **Root cause:** `file_type=file_type.upper()` in the same `Document(...)`
  call stored `"DOCX"`; `file_type` was already lowercase from
  `MIME_TO_TYPE.get(...).lower()` upstream.
- **Fix:** removed `.upper()` — store `file_type` as-is.
- **Prevention:** enum/constraint values in this codebase are lowercase;
  don't reformat a value that's already normalized upstream.

### 3. RFP uploads rejected: migration never applied locally
- **Symptom:** `document_type` CHECK constraint didn't include `'RFP'`.
- **Root cause:** `migrations/020_rfp_document_type.sql` existed in the repo
  but nothing had run it against the local dev Postgres container.
- **Fix:** applied manually via `docker exec -i edgp-postgres psql ... <
  020_rfp_document_type.sql`.
- **Prevention:** this project has no migration runner/tracking table yet
  (no `alembic_version` or similar) — a new migration file is not
  self-applying. Check `docker exec edgp-postgres psql -c "\d documents"`
  against the latest migration file before assuming schema is current.

### 4. Review always failed: `'str' object has no attribute 'get'` (x2 sites)
- **Symptom:** `POST /reviews/{id}/trigger` always 500'd after all 6 agents
  completed successfully, right at the scoring step.
- **Root cause:** `orchestrator._merge_findings` stores TWO things per agent
  under `merged_findings["agents"][name]`: `"findings"` (the raw per-agent
  JSON dict with keys like `deliverables`/`findings`/`overall_confidence`)
  AND a separately-flattened list at the top level `merged_findings["findings"]`
  (with `source_agent` tagged). Two call sites in `reviews.py` iterated
  `agent_info.get("findings", [])` — the raw dict, not the list — so
  Python iterated the dict's KEYS (strings), and `.get()` on a string
  crashed.
- **Fix:** both call sites (`app/routers/reviews.py`: scoring collection
  and DB-persistence loop) now use
  `orchestrated_result.merged_findings.get("findings", [])` directly
  instead of re-deriving it per-agent.
- **Prevention:** `merged_findings["agents"][x]["findings"]` is the RAW
  agent output dict, never iterate it directly as a findings list. Always
  use the top-level `merged_findings["findings"]`, which is already
  flattened and tagged with `source_agent`.

### 5. Review "completed" but DB commit failed: missing `completed_at`
- **Symptom:** `CheckViolationError: ck_reviews_completed_has_timestamp`.
- **Root cause:** `review.status = "completed"` was set without ever
  setting `review.completed_at`, but the DB requires both together.
- **Fix:** `apps/api/app/routers/reviews.py` — set
  `review.completed_at = datetime.utcnow()` alongside the status change.
- **Prevention:** any `status = "completed"` or `"failed"` assignment on
  `Review` must also satisfy `ck_reviews_completed_has_timestamp` /
  `ck_reviews_failed_has_error` in the same code path.

### 6. Every concurrent request froze while a review was running
- **Symptom:** login/search/dashboard all hung for the full ~80-90s of a
  review, even though FastAPI is async.
- **Root cause:** `ReviewAgent.review()` is `async def`, but called the
  underlying SDK (Anthropic, or the OpenRouter adapter) synchronously —
  `self.client.messages.create(...)` blocks the single-threaded asyncio
  event loop for the whole HTTP round-trip.
- **Fix:** `apps/api/app/ai/agent.py` — wrapped the call in
  `await asyncio.to_thread(self.client.messages.create, ...)`.
- **Prevention:** any new agent/LLM call must go through `asyncio.to_thread`
  (or an actual async SDK client) — never call a sync client directly
  inside an `async def` route/agent method.

### 7. Dashboard "View" button 404'd
- **Symptom:** clicking View navigated to `/document/{id}`, a route that
  was never built.
- **Root cause:** dead route, likely a leftover placeholder from an
  earlier design that assumed a document-detail page would exist.
- **Fix:** `apps/web/app/dashboard/page.tsx` and
  `apps/web/app/search/page.tsx` — View now calls
  `GET /api/v1/reviews?doc_id=...&org_id=...`, takes the latest
  (`created_at desc`) result, and routes to `/results/{review_id}`. Shows
  "No review yet" if none exists.
- **Prevention:** there is still no document-detail page in this app —
  only a review-results page. Don't link to `/document/*` anywhere until
  one exists.

### 8. Dashboard "Filter by Type" dropdown did nothing
- **Symptom:** changing the Type filter never refetched the document list.
- **Root cause:** `onChange` set `filterType` state and `loading=true`, but
  no effect was wired to actually call `fetchDocuments()` again when
  `filterType` changed.
- **Fix:** `apps/web/app/dashboard/page.tsx` — added a `useEffect` keyed on
  `[filterType]` that calls `fetchDocuments()`; also fixed the dropdown's
  option values (`"ProjectPlan"` isn't a real `DocumentType`, and `"RFP"`
  was missing entirely) to match the actual enum (SOW/Proposal/RFP/Other).
- **Prevention:** a filter control that only sets state without a
  corresponding fetch trigger is a common silent no-op bug — always check
  the effect/handler wiring, not just that the state updates. Also: any
  dropdown of enum values should reference the backend enum directly, not
  a hand-typed list that can drift out of sync.

### 9. Known, not yet fixed: `overall_score: 0.0` renders as `null`
- **Where:** `apps/api/app/routers/reviews.py` — the standalone
  `GET /reviews/{id}` endpoint (not the list-documents one added in #10)
  uses `float(review.overall_score) if review.overall_score else None`.
  `0.0` is falsy in Python, so a legitimately bad (0.0) score is displayed
  as missing instead of an actual zero.
- **Fix:** not yet applied here — same pattern was avoided in the new
  `list_documents` accuracy/completeness columns (uses `is not None`).
  Apply the same `is not None` fix to `get_review`/`list_reviews` if this
  surfaces again.
- **Prevention:** never use `if value else None` / `if value` as a
  null-check on a field that can be a meaningful `0` or `0.0` — always
  `is not None`.

### 10. Feature: Project label, dashboard stats, sortable table, accuracy/completeness columns (2026-07-18)
- Added `documents.project_name` (migration `021_document_project_name.sql`,
  optional, set via upload form), `list_documents` now embeds each
  document's latest completed review's `overall_score` /
  `score_completeness` as `latest_overall_score` /
  `latest_completeness_score` (one extra query per page, not N+1).
- Dashboard: sortable columns (tanstack `getSortedRowModel`), a stats row
  (total + per-type counts, computed client-side from the loaded page), and
  the two new score columns.
- Not a bug fix, but noted here so the `list_documents` query shape
  (documents page + one `Review.doc_id.in_(...)` query) is the reference
  pattern for any future "attach latest X" dashboard column.

### 11. New migration (021) not applied to `edgp_test` either
- **Symptom:** `test_documents.py::TestDeleteDocumentRBAC` errored with
  `UndefinedColumnError: column "project_name" ... does not exist`.
- **Root cause:** same class of bug as #3 — `edgp_dev` and `edgp_test` are
  two separate Postgres databases in the same container; applying a
  migration to one does not touch the other. Also discovered while here:
  migration 020 (RFP) had *never* been applied to `edgp_test` either, it
  just happened not to be exercised by a DB-inserting test yet.
- **Fix:** applied 021 and 020 to `edgp_test` via
  `docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < migrations/0XX_*.sql`.
- **Prevention:** **every new migration must be applied to BOTH `edgp_dev`
  and `edgp_test`** before considering it "done" — there is no migration
  runner/tracking table in this project, so nothing does this
  automatically. Check both databases' constraint/column state, not just
  one, whenever `docs/RCA_LOG.md` entry #3's advice applies.

### 12. New column broke a third, hand-rolled schema: `test_insights_extra.py`
- **Symptom:** `test_analyze_trends_*` (3 tests) failed with
  `sqlite3.OperationalError: table documents has no column named project_name`
  after adding the `project_name` column.
- **Root cause:** `test_insights_extra.py`'s `analytics_db` fixture creates
  its own **in-memory SQLite** schema via hand-written raw `CREATE TABLE`
  SQL (to dodge an unrelated `CommentReaction` FK issue) instead of using
  `Base.metadata.create_all()` off the real ORM models. That means there
  are now THREE places a documents-table schema can drift out of sync:
  `edgp_dev`, `edgp_test` (both via `migrations/*.sql`), and this fixture's
  inline SQL.
- **Fix:** added `project_name TEXT` to the raw `CREATE TABLE documents`
  in `tests/test_insights_extra.py`.
- **Prevention:** **any new column on `Document` (or any model this
  fixture mirrors) must also be added to `test_insights_extra.py`'s
  `analytics_db` fixture raw SQL** — grep for `CREATE TABLE documents` in
  the tests directory before considering a migration complete. This is a
  third location beyond entry #11's two databases.

### 13. Same class recurred for `reviews.risk_breakdown` (2026-07-19)
- **Symptom:** adding `Review.risk_breakdown` (migration 022, risk-model
  redesign) broke `TestAnalyticsTrends` again with
  `no such column: reviews.risk_breakdown` — identical shape to #12, just
  the `reviews` table's `CREATE TABLE` in the same fixture this time.
- **Fix:** added `risk_breakdown TEXT` to the raw `CREATE TABLE reviews`
  in `tests/test_insights_extra.py`.
- **Prevention:** entry #12's rule applies to `reviews`/any other model
  this fixture mirrors too, not just `documents` — **grep for `CREATE
  TABLE <model>` in `tests/test_insights_extra.py` for EVERY table a new
  column touches**, not just the one from the last incident.

### 14. OpenRouter model swap silently broke 3 of 5 candidate models: `max_tokens=2000` too small for reasoning-mode models (2026-07-19)

- **Symptom:** when benchmarking GLM-5.2, MiniMax M3, and Kimi K3 as
  cheaper OpenRouter alternatives, all three either returned truncated/
  unparseable JSON or `content: None` from `ReviewAgent.review()`
  (`apps/api/app/ai/agent.py`) — while DeepSeek and Qwen3.7-Plus worked
  fine on the identical prompt/document.
- **Root cause:** `max_tokens=2000` in the `messages.create(...)` call
  was inherited from the original Claude 3.5 Sonnet integration.
  GLM-5.2, MiniMax M3, and Kimi K3 all run "always-on thinking"/hidden-
  reasoning modes that consume completion tokens before the visible
  answer — confirmed directly on Kimi K3: `reasoning_tokens: 1997` out
  of a 2000-token budget, leaving 0 for actual output
  (`finish_reason: "length"`). Not a model-quality problem.
- **Fix:** raised `max_tokens` to 4000 (`apps/api/app/ai/agent.py`).
  Fixed GLM-5.2 and MiniMax M3 immediately. Kimi K3 still failed at
  4000 and needed 8000 to complete reliably — at that budget it cost
  ~$0.086/call (10-15x DeepSeek/GLM-5.2) due to reasoning overhead, so
  it was dropped from the fallback chain on cost/latency grounds
  instead of raising the ceiling further.
- **Prevention:** when adding any new OpenRouter model to the chain,
  don't assume a token budget tuned for one model family transfers to
  another — reasoning-mode models need meaningfully more headroom.
  Check `usage.completion_tokens_details.reasoning_tokens` in the raw
  response before trusting a `content: None` failure is a provider
  outage rather than a budget problem. Full benchmark methodology and
  per-model results in `docs/planning/AI_MODEL_ROUTING.md`.

### 15. Every real upload crashed with `NameError: name 'doc_id' is not defined` (2026-07-20)

- **Symptom:** `POST /api/v1/documents/upload` 500'd on every successful
  upload (file validated, stored, parsed, `Document` row committed — then
  crashed on the final log line before returning a response). Deployed to
  prod as part of the Document Lifecycle session's Phase B commit and went
  undetected through that session's full test suite (405/2 → 422/2, all
  green) because no test exercised the real HTTP upload success path —
  `test_documents.py` only covers delete, and the versioning tests
  construct `Document` rows directly via the ORM instead of calling
  `POST /upload`.
- **Root cause:** `apps/api/app/routers/documents.py::upload_document` was
  refactored (Phase B, moving the storage/parsing logic into a shared
  `_store_uploaded_document` helper) so `doc_id` became a local variable
  *inside* the helper, not in `upload_document` itself anymore. A leftover
  `logger.info(f"Document {doc_id} uploaded...")` at the end of
  `upload_document` still referenced the now-out-of-scope name.
- **Fix:** `apps/api/app/routers/documents.py` — changed the log line to
  `doc.doc_id` (the `Document` object returned by the helper, already in
  scope).
- **Prevention:** a refactor that moves a variable into a helper function
  must be verified against every reference to that variable in the
  *caller*, not just the lines directly touched by the diff — grep the old
  variable name across the whole function after any such extraction, not
  just the block that was cut. Also: this class of bug (crash only on the
  success path, after every side effect has already committed) is
  invisible to tests that never hit a real success response — a new
  endpoint/refactor needs at least one HTTP-level test of the happy path,
  not just the validation/error branches, before being considered covered.

---

### 16. DOCX table-only documents silently parsed to empty text (2026-07-20)

- **Symptom:** Discovered while assembling a real-document test set for
  the AI accuracy work (`docs/sample/SOW_Template/*.docx`, downloaded
  TemplateLab SOW templates) -- every one of 27 real-world `.docx` files
  parsed with `status: "success"` and `raw_text: ""`. A document with
  real, substantial content (project fields, deliverables, team members)
  came back completely empty, with no error anywhere in the pipeline. Had
  this hit a real user upload, the review agents would have run against
  an empty string and reported findings based on nothing, while the UI
  showed a normal "review complete" result.
- **Root cause:** `apps/api/app/parser.py::DocxParser.parse()` only
  iterated `doc.paragraphs`. Any document whose content lives in a table
  (a common layout choice for structured SOW/RFP templates, not unique to
  TemplateLab) has zero paragraphs with real text, so the whole extraction
  loop produced nothing -- and because nothing raised an exception, the
  function returned its normal `status="success"` path with an empty
  string.
- **Fix:** switched to `doc.iter_inner_content()` (python-docx 1.2+),
  which yields `Paragraph` and `Table` objects in document order, and
  added `DocxParser._extract_table_text()` to flatten table cell text into
  the output (deduping merged cells, which python-docx repeats once per
  spanned grid position). 26 of 27 previously-empty files now extract
  real text; the 1 remaining case has a malformed table grid python-docx's
  `row.cells` can't resolve at all, and now correctly surfaces as
  `status="failed"` with an error message instead of the previous silent
  empty success -- strictly better even where the underlying file is
  genuinely unparseable with this library.
- **Prevention:** `status="success"` was never actually verified against
  "extracted something non-trivial" anywhere in the pipeline -- a parser
  returning empty text is currently indistinguishable from a parser that
  correctly found no content (e.g. a truly blank file). Worth adding a
  minimum-extracted-length sanity check (log a warning, don't fail the
  upload) so a future parser gap surfaces as a visible signal rather than
  a silent empty-success review. Not built in this pass -- flagged for
  whoever picks up the next parser-reliability sweep. Tests added in
  `apps/api/tests/test_parser_file_types.py::TestDocxParser` (table-only
  doc, merged-cell dedup, paragraphs+tables both captured) so this
  specific regression can't reappear silently.

### 17. RCA #16's fix required python-docx 1.2+, but requirements.txt still pinned 0.8.11 -- every real DOCX upload silently broke in production (2026-07-21)

- **Symptom:** User reported `SOC_SOW_Testing.docx` (uploaded to live
  ScopeWise, real content, `docs/sample/SOW_Sample/SOC_SOW_Testing.docx`
  is the same file) showed `document_type: null` ("Unknown" in the UI)
  and no "View Document" option after review. Queried prod directly:
  `parsed_text` length 0, `parsed_sections` count 0, `page_count` 0 --
  a real, non-trivial document stored as if it were blank.
- **Root cause:** RCA #16 (previous entry, 2026-07-20) rewrote
  `DocxParser.parse()` to call `Document.iter_inner_content()` and its
  own writeup even says "(python-docx 1.2+)" -- but `requirements.txt`
  was never updated off `python-docx==0.8.11`, which predates that
  method entirely. Locally, tests passed anyway because the dev venv
  already had python-docx 1.2.0 installed from an earlier ad-hoc
  upgrade that was never reflected in requirements.txt -- so every local
  test run and every "it works on my machine" check was silently
  validating against a different dependency version than what the
  Docker image (built fresh from requirements.txt) actually shipped.
  Confirmed by copying the sample file into the live `scopewise-api`
  container and parsing it there directly:
  `AttributeError: 'Document' object has no attribute
  'iter_inner_content'` -- caught by `DocxParser.parse()`'s own
  `except Exception`, logged, and returned as a normal-looking
  `status="failed"` `ParseResult` with no exception ever reaching
  `documents.py`'s own try/except, so nothing was ever logged as a
  parsing failure at the request layer either. This affected **every**
  DOCX upload in production since whenever RCA #16 was first deployed,
  not just this one file.
- **Fix:** `requirements.txt` repinned to `python-docx==1.2.0` (matches
  what was already proven working locally), with a comment explaining
  exactly which method requires it and why. Verified by rebuilding the
  actual `scopewise-api` Docker image and parsing the same sample file
  inside the freshly-built container before deploying -- not just
  re-running local tests, which would have passed either way.
- **Prevention:** a requirements.txt pin is only as good as whether the
  local dev environment actually matches it -- nothing here enforces
  that a locally-installed package version equals the pinned one. The
  real guardrail that caught this was rebuilding the Docker image and
  testing inside it directly, which should be standard practice before
  claiming any parser/dependency-adjacent fix is deployed correctly (not
  just "tests pass locally"). Also added `PATCH
  /api/v1/documents/{doc_id}/type` (previously no way to manually
  correct a document's type at all -- auto-detection has no retry path,
  so a document that parsed to empty text, or was just detected wrong,
  was permanently stuck showing "Unknown" with no recovery option in
  the UI).

### 18. Every completed review had all 7 category scores AND overall_score stored as exactly 0.00 (2026-07-21)

- **Symptom:** User asked what "Completeness"/"Accuracy" on the dashboard
  mean, since both always showed 0. Queried production directly across
  all completed reviews: `overall_score`, `score_completeness`,
  `score_clarity`, `score_consistency`, `score_commercial`,
  `score_delivery`, `score_operations`, and `score_security` were **all
  exactly 0.00 on every single review**, despite 31-67 real findings per
  review and legitimate `risk_score` values (94-100%) -- so it wasn't a
  parsing/empty-document problem, real findings existed.
- **Root cause:** `DocumentScorer.score_document()` applies a smaller
  "general" severity penalty to *every* category on top of each
  category's own keyword-matched deductions (`_GENERAL_SEVERITY_PENALTY`,
  intended so severity always affects scoring even for findings that
  don't happen to use a category's trigger words). That penalty was a
  raw, uncapped linear sum across *all* findings, then subtracted in
  full from every category's 100-point budget. For one real review (18
  critical + 30 major + 17 medium + 2 low findings), the raw sum was
  **449** -- so every category landed at `max(0, 100 - 449) = 0`,
  identically, regardless of what each category's own findings actually
  covered. Any real document with more than ~10-15 findings hits this
  (this codebase's own calibration notes say 30-40+ is typical for a
  real SOW/RFP review), so this has likely been live for a long time.
  This is the *exact same failure shape* `risk_score` already hit and
  was fixed for on 2026-07-19 (RCA/SCORING_METHODOLOGY.md's "the old
  risk score was a flat additive sum... capped at 100... saturated
  almost immediately") -- the fix just never got applied to this second,
  separate flat-sum site.
- **Fix:** the general penalty's raw sum is now passed through the same
  saturating curve already used for `risk_score` (`DocumentScorer.
  _saturate`, now parameterized with a `cap` instead of hardcoding 100),
  capped at a new `GENERAL_PENALTY_CAP = 40` -- severity volume alone can
  now only ever pull a category down to 60, never to 0, so
  category-specific findings have to contribute for a category to
  actually go red. 40 was a deliberate judgment call (confirmed with the
  user, no industry standard exists for this specific number) -- see
  `docs/planning/SCORING_METHODOLOGY.md` for the full reasoning.
  `tests/test_scoring.py::test_score_status_red` was actually relying on
  the bug (5 generic critical findings alone forcing every category red
  via the old unbounded penalty) and had to be rewritten to use
  category-specific findings instead; added
  `test_high_finding_volume_does_not_zero_every_category` reproducing
  the exact production finding distribution as a permanent regression
  guard.
- **Prevention:** this class of bug (a flat/linear sum against
  unbounded real-world volume) has now recurred twice in the same
  scoring module. Checked the rest of `algorithm.py` for the same
  pattern: each of the 7 categories' own *specific*-penalty deductions
  (`_score_completeness`/`_score_clarity`/etc., all `points -=
  sum(_SPECIFIC_SEVERITY_PENALTY...)`) is also an uncapped linear sum,
  just isolated to one category and range-clamped at the end
  (`max(0, min(100, points))`) rather than zeroing all 7 at once like
  the general penalty did -- lower severity (a category with enough of
  its *own* findings hitting 0 is more defensible than an unrelated
  category getting zeroed by a flood of other-category findings), but
  the same underlying "no headroom past a handful of critical findings"
  flaw the risk_score redesign was meant to eliminate everywhere. Not
  fixed in this pass -- flagged for whoever picks up the next
  scoring-calibration sweep, since capping 7 more constants is its own
  design decision (what should each category's ceiling be?) rather than
  a mechanical extension of this fix.
- **Addendum (same day, ~3h later):** the flagged follow-up became
  urgent immediately. Re-running the review on the real
  `SOC_SOW_Testing.docx` (70 findings) after the cap fix still produced
  6 of 7 categories at exactly 0.00 -- the per-category uncapped sums
  flagged above were doing the zeroing on their own, and the capped
  general penalty (saturating to ~39/40 for any high-volume document)
  wiped out whatever survived. Final design (verified against the real
  70-finding review, user-approved): (1) every category's own penalty
  sum now maps through a saturating curve
  (`_saturating_category_score`, `CATEGORY_SATURATION_K = 0.017`,
  calibrated so one critical match ~= 65/yellow, no more hard cliff at
  0); (2) the cross-category general penalty was **retired entirely**
  rather than re-capped -- it double-counted the severity signal each
  category's own penalty already carries, and overall severity/volume
  is already captured correctly by risk_score. Result on the real
  document: overall 15.0, categories spread 0.07-87.3 (consistency,
  with only 1 matched finding, correctly reads green while
  heavily-matched categories read near-0) instead of uniform zeros.
  Two pre-existing tests (`test_score_with_critical_findings`,
  `test_score_status_red`) were asserting on the double-counting
  behavior and were updated to assert on the matched categories
  instead. Lesson repeated three times in one module now: **any
  unbounded linear sum fed by real-world finding volume will blow past
  a fixed budget; saturate at the source, and never stack two volume-
  driven shrink mechanisms on the same signal.**

---

*(Append new entries above this line, most recent first is NOT required —
keep chronological.)*

### 19. Review of an unreadable (image-only) PDF "succeeded" with 28 bogus findings (2026-07-23/24)

- **Symptom:** During RFP pipeline validation, an image-only PDF uploaded
  to production stored `parsed_text=""`/`page_count=0`, yet triggering a
  review returned `status: completed` with 28 findings — every SOW
  section-presence rule fired "missing section" against an empty
  document, and all 6 agents received empty text (returning unparseable
  chatter that the old parse-fallback silently converted to zero
  findings). A real user would have seen a plausible-looking, entirely
  fictional review.
- **Root cause:** two layers, both "empty success". (a)
  `PdfParser.parse()` counted its own `--- Page N ---` markers as
  content, so a PDF with no text layer returned `status="success"` with
  an empty body — the exact failure class RCA #16 documented for DOCX
  and whose prevention note ("minimum-extracted-length sanity check")
  was flagged but not built. (b) `trigger_review` ran the pipeline on
  `doc.parsed_text or ""` with no floor.
- **Fix (both layers + capability):** `trigger_review` now 422s with a
  plain-language error when parsed text is under 200 chars
  (`test_review_trigger_guard.py`); `PdfParser` fails loudly when the
  body (excluding page markers) is under 200 chars; and scanned PDFs now
  actually parse via OCR fallback (tesseract + pypdfium2 rendering,
  30-page cap, in the prod image) — the sample scanned SOW extracts
  8.3K chars. Unparseable agent JSON also now advances the model
  fallback chain instead of silently yielding zero findings
  (`test_agent_parse_fallback.py`).
- **Prevention:** the RCA #16 prevention item is now built and enforced
  at the trust boundary (trigger), not just logged. Regression tests:
  `test_review_trigger_guard.py`,
  `test_parser_file_types.py::TestScannedPdfHandling`,
  `test_agent_parse_fallback.py`. Pattern to remember: any parser or
  model adapter that can produce "empty but status=success" needs a
  content floor at the next trust boundary — status flags alone lie.
