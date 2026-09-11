# Kickoff prompt — Code Security Review: scan kit + real golden scan + single commit

Paste everything below the line into a fresh Claude Code session opened at
`E:\code\DocumentGovernancePlatform`.

---

## Context (read these first, in one parallel burst)

1. `CLAUDE.md` (project overlay), `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md`
   (the module contract — sections 0–9; section 8 is what you are building,
   section 9 is the golden-scan task) and `docs/planning/CODE_REVIEW_UI_PLAN.md`
   (the UI pass that comes first).
2. `docs/phases/summaries/SESSION_HANDOFF_2026_09_11_CODE_REVIEW_MODULE.md`
   (what the previous session built and left uncommitted).
3. `docs/RCA_LOG.md` entries #3/#11/#12/#13 (migrations must be applied by
   hand to every DB) and the memories `edgp-test-single-runner-rule`,
   `prod-python-311-fstring-gotcha`, and the 2026-08-19 customer-data
   incident note (never `git add docs/` wholesale).

State you are inheriting: the whole Code Security Review module
(`apps/api/app/codereview/`, `apps/web/app/codereview/`, migration 039,
model, 21 tests, synthetic sample under `docs/sample/CodeReview_Sample/`,
docs) is **built, verified (962 passed / 7 skipped, `tsc --noEmit` clean),
applied to edgp_dev + edgp_test, and NOT committed**. Do not rebuild it;
extend it. `git status` will also show unrelated pre-existing uncommitted
files (MarketingFooter.tsx, apps/web/app/privacy/, marketplace/,
scripts/generate_sentinel_workbook.py, MITRE UploadSample changes) — leave
those out of your commit unless the user says otherwise.

Decisions already made by the user (do not re-ask):

- **Host the VVAH release inside ScopeWise** (not just a GitHub link).
- **One commit** covering the existing module + the scan kit + the golden
  fixture.
- **Run one real VVAH scan of a small public repo** for a golden fixture,
  gated on the `vvaharness estimate` output.
- ScopeWise never runs VVAH server-side (section 1 of the reference).

## Goal

Ship the consultant scan kit (reference section 8), capture a real VVAH
`findings.json` as a golden fixture (section 9), and land everything in a
single commit — Phase 0 plan first, wait for the user's approval, then
build via Sonnet subagents with Opus critique per the global playbook.

## Tasks

### 0. Professional UI pass (do this FIRST, then get a screenshot sign-off)

Implement `docs/planning/CODE_REVIEW_UI_PLAN.md` sections 2–6 on the
three existing pages (list, upload, results + drawer). One Sonnet agent
per page in parallel, Opus critique of the diff, `npx tsc --noEmit`
clean, manual pass at 400/768/1280 px with the synthetic sample. Stop
and show the user screenshots before continuing to A. The upload page's
"Get the scanner" card is built here with the download button disabled;
task A enables it.

### A. Host VVAH + build the kit

1. Pin VVAH: check the latest release tag at
   github.com/visa/visa-vulnerability-agentic-harness (v1.3.0 at
   2026-09-11). Build or download its wheel/sdist plus `LICENSE`,
   `NOTICE`, `THIRD_PARTY_LICENSES.md`. Put the artefacts in
   `apps/api/app/codereview/kit/vendor/` **only if < 5 MB total**;
   otherwise store them through the platform storage backend under
   `platform/codereview/kit/<version>/` and add a one-off upload script in
   `scripts/`. Record the pinned version + sha256 in
   `apps/api/app/codereview/kit/KIT_VERSION.json`.
2. Kit files in `apps/api/app/codereview/kit/`:
   - `config.yaml` — every S0–S9 role routed via an OpenAI-compatible
     endpoint (`OPENAI_BASE_URL=https://openrouter.ai/api/v1`), mid-tier
     reasoning models per VVAH `docs/models.md` (verify the current
     recommended list; do not guess model ids), remediation/validation
     disabled, `stop_after: s9` if the profile supports it.
   - `scopewise-scan.ps1` and `scopewise-scan.sh` — `estimate` → print
     the estimate and prompt Y/N → `scan --repo <path> --stop-after s9
     --config config.yaml` → zip `security-scan/findings.json`,
     `*.sarif`, `run_manifest_*.json` as
     `scopewise-scan-<repo>-<yyyymmdd>.zip`. Never write the API key
     anywhere; read it from `.env` / env var.
   - `README.md` — install (Python 3.11+, `pip install <wheel>`), key
     setup, run, upload. Plain words, ≤ 40 lines.
3. `GET /api/v1/codereview/kit.zip` (any authenticated user) streams the
   kit (files above + the vendored release or a signed download link when
   stored in the backend). Add the VVAH attribution to the zip root.
4. Upload accepts the kit zip: extend `POST /reviews` so a `.zip` `report`
   upload is opened in memory, `findings.json` (fallback `.sarif`) and the
   manifest are picked from inside it, then the existing ingest path runs
   unchanged. Guards: ≤ 50 entries, ≤ 10 MB uncompressed per file, ≤ 30 MB
   total, no path traversal (`..`, absolute paths). Reuse
   `ingest.MAX_REPORT_BYTES`.
5. Frontend: "Get the scanner" panel on `apps/web/app/codereview/new/page.tsx`
   with the download button (blob download with Authorization header,
   same pattern as the results-page exports) and the three-step
   instructions; the dropzone also accepts `.zip`. `npx tsc --noEmit` clean.
6. Tests (minimal, base functionality only): kit endpoint 200 + zip
   contains the 4 files; zip upload round-trip → 201; zip guards (too many
   entries, traversal, oversize) → 422/413; config.yaml sanity (every role
   has id/via/provider, no remediation role enabled).

### B. Real golden scan

1. Install the pinned VVAH into a throwaway venv under the scratchpad.
2. Target: a small, permissively licensed, deliberately vulnerable public
   repo (candidates: `OWASP/NodeGoat`, `digininja/DVWA`,
   `we45/Vulnerable-Flask-App`, `adamdoupe/WackoPicko`; prefer Python or
   JS so VVAH's S0 taint plugin runs). Clone it into the scratchpad.
3. Run `vvaharness estimate --repo <path>` with the kit `config.yaml` and
   the project's OpenRouter key (the SOW-audit key in `apps/api/.env` —
   see memory `openrouter-key-identity`; never the $2-capped personal
   key). **Show the user the estimate and wait for approval before
   scanning.** Abort if the estimate exceeds ~$5 or the user declines.
4. Run the scan with `--stop-after s9`. Copy `findings.json`, the
   `.sarif`, and `run_manifest_*.json` into
   `docs/sample/CodeReview_Sample/real/<repo>/` with a README naming the
   repo, commit sha, license, VVAH version, models, tokens and cost.
5. Check the real files contain no secrets (`grep` the secret patterns from
   the global playbook Phase 2) — VVAH redacts, but verify.
6. Add a golden test in `apps/api/tests/test_codereview_ingest.py`: parse
   the real `findings.json` and assert stable facts (total count, severity
   histogram, every finding has file + title, chain steps within 1..N).
   If the real schema differs from the synthetic assumptions, fix
   `ingest.py` and regenerate the synthetic sample to match — the real
   file wins.

### C. Verify, document, commit

1. Phase 2 gates on the diff: secrets scan, `TODO|FIXME|XXX` grep, the
   module's test files, then the full suite solo on edgp_test (check
   `pg_stat_activity` first). Baseline to beat: 962 passed / 7 skipped
   plus your new tests. `cd apps/web && npx tsc --noEmit`.
2. Docs: update `CODE_REVIEW_MODULE_REFERENCE.md` sections 8–9 from
   "planned" to "built" (kit contents, endpoint, zip guards, pinned
   version, golden repo facts), the `CLAUDE.md` baseline line, an
   `IMPLEMENTATION_PROGRESS.md` entry, and a session handoff under
   `docs/phases/summaries/` with the 4-line agent-utilization footer.
3. **One commit.** Stage explicitly by path: `apps/api/app/codereview/`,
   `apps/api/app/models/code_review.py`, the 4 shared backend files,
   `apps/api/migrations/039_code_review.sql`, `apps/api/tests/test_codereview_*.py`,
   `apps/web/app/codereview/`, `apps/web/components/AppShell.tsx`,
   `scripts/generate_codereview_sample.py`, `docs/sample/CodeReview_Sample/`
   (both synthetic and `real/`), `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md`,
   `docs/planning/CODE_REVIEW_UI_PLAN.md`,
   `docs/phases/prompts/CODE_REVIEW_SCAN_KIT_PROMPT.md`, the summary,
   `docs/IMPLEMENTATION_PROGRESS.md`, `CLAUDE.md`. Never `git add docs/`
   or `git add -A`. Suggested message: "Code Security Review module: VVAH
   findings import, XLSX/PPTX deliverables, consultant scan kit, real
   golden scan". End with the attribution line your session gives you.
4. Do **not** push or deploy unless the user says so in that session. If
   they do: `git push`, VPS deploy loop from `CLAUDE.md`, apply migration
   039 to `scopewise_prod`, then the in-container import smoke
   (`python -c "import app.codereview.router"`) on the 3.11 image, then
   upload the golden zip at `https://scopewise.assessiq.in/codereview/new`.

## Constraints

- Ponytail mode: shortest working diff; no new dependencies (stdlib
  `zipfile`, existing openpyxl/python-pptx only).
- Load-bearing shared files get the line-by-line Opus review; the zip
  upload path is a trust boundary — Opus reviews it, and a Sonnet
  adversarial pass (codex:rescue is broken per memory) covers zip-bomb /
  traversal / oversize before commit.
- Python 3.11-compatible (prod image).
- Never send the OpenRouter key, customer data, or prompt contents to
  Tier 2/4 models.

## Deliverable shape

Phase 0 (plan + what you will delegate) → wait → build → gates → critique
→ verify → docs → one commit → tell the user: tests pass Y/N, commit sha,
the golden repo + cost, and the exact next action (push/deploy or not).
