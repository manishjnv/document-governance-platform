# Code Security Review — Module Reference

Third ScopeWise module (after SOW Review and MITRE Assessment). Imports the
output of Visa's open-source
[Vulnerability Agentic Harness](https://github.com/visa/visa-vulnerability-agentic-harness)
(VVAH, Apache-2.0) and turns it into a reviewable findings register plus
client-ready XLSX / PPTX deliverables. Live in production at
`https://scopesense.in/codereview`.

This is the single living reference for the module — extend it in place as
the feature changes. Session handoffs and the original kickoff prompt are
historical logs only; see §0 for the rule.

## 0. Status & changelog

**Current state (2026-09-23):** shipped, deployed, in daily use. Prod commit
`24dbfaa` (SARIF narrative import `1033775`). Backend suite baseline
**998 passed / 7 skipped**; `npx tsc
--noEmit` clean. Migrations through `039_code_review.sql`, applied to
`edgp_dev`, `edgp_test`, and `scopewise_prod`. Deferred by user (not bugs,
not blocking): PPTX org branding (still `resolve_branding(None)`), a
`pricing:` table in the kit `config.yaml` so VVAH's own manifest reports
`cost_usd` instead of the README's list-price estimate.

**This section replaces per-session summaries for this feature — append
here, do not create a new doc.**

- **2026-09-23 — kit on VVAH 1.4.0 + auto-update:** weekly
  `vvah-kit-update.yml` + `scripts/update_vvah_kit.py` keep the kit on the
  latest VVAH release via a reviewed PR (§8 "Keeping the scan kit on the
  latest VVAH"); upload page gains an "About the scanner" panel (what it
  is, stages, what it finds, limits).
- **2026-09-23 — SARIF narrative import:** SARIF import now reads Agentic SAST 1.4.0's
  sectioned `properties.description` (impact, exploit scenario,
  preconditions, how to fix, adversarial verification), offensive priority,
  CWE category, code snippet, TP/FP verdict, `remediation` status and
  scan-degraded reason, so a raw
  `.sarif` upload gives the same register/deck detail as `findings.json`
  (RCA #34). Existing SARIF reviews must be re-uploaded to pick it up.
- **2026-09-12 — `2a5f918`:** PPTX remediation-plan cell stripped literal
  backticks before rendering as plain text (RCA #26).
- **2026-09-12 — `ce94179`:** sentence-split regex made ellipsis-safe in
  both `report_xlsx.py` and `FindingDrawer.tsx` so a fix recommendation
  containing `` `SELECT ... FOR UPDATE` `` is no longer truncated mid-code
  (RCA #24); added the "fix text rules in both languages in one commit"
  prevention rule.
- **2026-09-12 — `5ed1053`:** highlight word lists (risk/fix regexes)
  reduced to one source, `app/codereview/highlight_words.json`, with the
  web copy generated (`scripts/generate_highlight_words.py`) and a
  drift test (RCA #23); VVAH 1.3.0 schema coverage pinned with a
  full-field synthetic fixture (`acme_full_schema.json`) plus
  `FINDING_FIELDS_1_3_0` / `FINAL_REPORT_FIELDS_1_3_0` contract tests
  (closes RCA #25 permanently without a second real scan).
- **2026-09-12 — `a319895`:** scan-kit size guard — after `estimate`,
  refuse > 20,000 code files or > 500 MB ("scan a fresh clone" advice),
  warn above 2,000 files or when dependency/build folders are found.
  Triggered by a user scanning a 345k-file / 3.4 GB working folder that
  sat in S0 for 40 minutes.
- **2026-09-12 — `cf39b7d`:** demo reviews — `CODEREVIEW_DEMO_REVIEW_IDS`
  env var makes listed reviews readable/exportable by every signed-in
  user across orgs; `demo`/`editable` response flags; UI chip, rename/
  delete hidden. Prod demo: the NodeGoat golden review
  `49e45724-ff5d-4e53-937b-aba306d3cfd3`.
- **2026-09-12 — `0db4a86`:** XLSX made byte-deterministic — workbook
  `created`/`modified` properties pinned and the zip container rewritten
  with fixed entry timestamps (`_normalize_zip`), fixing a flaky
  determinism test once builds started taking > 1 s.
- **2026-09-12 — `e55a556`:** PPTX rebuilt on the MITRE report engine —
  12–17 slides depending on data, keyword-highlighted runs, styled native
  charts, section dividers with giant numbers, deterministic set-cover
  remediation ordering.
- **2026-09-12 — `d8681e7`:** XLSX professional pass — centred numbers,
  tinted severity/verdict/status chips, Status as a dropdown with
  conditional formatting, prose columns split into rich-text bullets with
  code/attack/fix highlighting, exploit-chain banner + "fix this first"
  column.
- **2026-09-12 — `cc46845`:** per-run transcript log
  (`logs/scan-<repo>-<timestamp>.log`) with failure pointers (transcript
  path, VVAH's `*_errors.jsonl`, run-manifest stage timeline).
- **2026-09-12 — `3b565a6`:** installer-style `setup.*` (banner, progress
  bar, green success box); kit root reduced to one setup entry per
  platform, PowerShell internals moved to `bin/`.
- **2026-09-12 — `00b64ee`:** `setup.cmd` / `scopewise-scan.cmd` Windows
  launchers — `Unblock-File` + `-ExecutionPolicy Bypass` around the
  downloaded (Mark-of-the-Web-flagged) `.ps1` scripts.
- **2026-09-12 — `7358769`:** step-by-step progress output during
  `setup.*` so the multi-minute pip install doesn't look hung.
- **2026-09-12 — `461ed68`:** `setup.ps1` / `setup.sh` one-time installers
  (`.venv`, vendored wheel, hidden-input key prompt, `.env`); scan scripts
  made venv-aware. Triggered by a user running `pip install <kit>.zip`
  directly (the zip is not a Python package).
- **2026-09-12 — `f2ffe3e`:** finding-drawer rework — plain-language
  section order, keyword highlighting, resizable sheet, quick-fact chips.
- **2026-09-11 (morning, single commit) — `ef18ab8`:** module shipped —
  backend (migration 039, model, ingest, router, XLSX/PPTX reports, 21
  tests), professional UI pass on all three pages
  (`docs/planning/CODE_REVIEW_UI_PLAN.md` §2–6, now merged into §7 below),
  consultant scan kit (VVAH v1.3.0 wheel vendored,
  `GET /api/v1/codereview/kit.zip`, zip upload with guards), and a real
  VVAH scan of `OWASP/NodeGoat` as the golden fixture. Migration 039
  applied to `scopewise_prod` same day. Suite 962→973 passed / 7 skipped.

## 1. Product context and feasibility verdict

**What kind of scanner VVAH is.** LLM-driven SAST (static application
security testing): it reads source code at rest. It is not an asset,
vulnerability-management, DAST, or network scanner and never touches
running systems. Versus classic SAST it threat-models the repo first, uses
multi-agent voting instead of only pattern rules (so it catches logic
flaws), and can propose/validate fixes. Tradeoffs: non-deterministic, no
published precision/recall, per-run token cost.

**Comparable products.** Rule-based SAST: Semgrep, SonarQube, Checkmarx,
Fortify, Veracode, CodeQL, Snyk Code. AI-native code security: Amazon
CodeGuru Security, GitHub Copilot Autofix, Snyk DeepCode AI, Aikido,
Corgea, ZeroPath, Mobb. Research harnesses: Google Big Sleep / OSS-Fuzz AI,
DARPA AIxCC tools, Anthropic Project Glasswing (VVAH's stated basis). Not
comparable (asset/infra or DAST): Nessus, Qualys, Rapid7 InsightVM, Wiz,
Orca, Burp Suite, OWASP ZAP.

**Who runs the scan.** The consultant, on their own key and machine (or on
a client-provided jump box when code may not leave the client network;
only `findings.json` comes out). Never the client via a portal button, and
never ScopeWise server-side. Cost sits on the engagement: run `vvaharness
estimate` before every scan.

**Input / output in one line.** In: `findings.json` (or `.sarif`) +
optional `run_manifest_*.json` from a `--stop-after s9` run. Out: findings
table + drawer, exploit chains, XLSX tracker, PPTX briefing deck.

**Feasibility verdict (decided 2026-09-11, still the design boundary):**
ScopeWise never clones repos or runs VVAH server-side ("Option B",
deferred — revisit only if the import path shows demand). Reasons:

- VVAH has no spend cap and defaults to Opus-class models.
- VVAH's own `docs/security.md` requires a disposable container with
  egress firewalling for untrusted repos, which the shared VPS cannot
  host.
- Sub-70B models degrade its structured output.
- Prompt-injection + secret egress from repo contents is a live risk when
  the platform, not the consultant, controls the target repo.
- Third-party scan authorization would shift onto the platform.
- 30–60 minute jobs exceed the in-process asyncio pattern the rest of
  ScopeWise uses.

No LLM is called anywhere in this module at request time — every number
the module computes is deterministic Python over the imported report.

## 2. Architecture & isolation contract

A consultant runs the scanner themselves, detection-only:

    vvaharness scan --repo /path/to/repo --stop-after s9

and uploads the resulting `security-scan/findings.json` (or the `.sarif`)
plus, optionally, `run_manifest_*.json`, or the kit's own zip (§8). ScopeWise
stores the parsed report per org, shows a severity-sorted findings table
with a detail drawer, and exports an XLSX tracker and a PPTX briefing deck.

**Isolation contract** (same pattern as MITRE, `MITRE_MODULE_REFERENCE.md`
§1): module = `apps/api/app/codereview/` + `code_reviews` table +
`apps/web/app/codereview/`. Shared touchpoints, exhaustive: `main.py`
(+2 lines), `app/models/__init__.py` (+1 registration),
`app/models/enums.py` + `app/models/audit_log.py` + migration 039
(`code_review` audit resource type), `apps/web/components/AppShell.tsx`
(+1 nav entry). Nothing under `app/mitre/`, `app/routers/`, `app/ai/`
changes.

**Storage — migration `039_code_review.sql`.** One table. The normalized
report lives in JSONB; no per-finding rows (a results page always loads
the whole review; nothing queries findings across reviews).

    code_reviews(
      review_id UUID PK, org_id UUID FK organizations CASCADE,
      name VARCHAR(255), repo_label VARCHAR(255), git_sha VARCHAR(64),
      source_format VARCHAR(10) CHECK IN ('findings','sarif'),
      source_path VARCHAR(500),        -- storage key of the uploaded file
      manifest_path VARCHAR(500),      -- optional run_manifest storage key
      report JSONB NOT NULL,           -- section 3 shape
      created_by UUID FK users SET NULL,
      created_at/updated_at TIMESTAMPTZ DEFAULT clock_timestamp(), deleted_at)
    ix_code_reviews_org (org_id)

Plus: widen `audit_logs.resource_type` CHECK with `'code_review'` (mirror
in `app/models/audit_log.py` and `enums.AuditResourceType`; `audit_logs` is
not one of `test_insights_extra.py`'s hand-rolled tables, so that fixture
needs no edit). Applied to `edgp_dev`, `edgp_test`, and `scopewise_prod` —
no migration runner exists in this codebase, so any future column here
needs the same four-way manual apply (see project `CLAUDE.md`).

## 3. Data model — normalized report shape

Produced by `app/codereview/ingest.py` from either input. All strings are
attacker-controlled (they come from the scanned repo via the LLM) — cap
lengths at ingest, `_guard` them in XLSX, never render as HTML.

    {
      "source_format": "findings" | "sarif",
      "tool": "vvaharness", "tool_version": str|null,
      "repo_name": str|null, "git_sha": str|null,
      "summary_text": str,                      # FinalReport.summary, cap 4000
      "degraded": bool, "degraded_reason": str,
      "assumptions": [str],                     # ingest notes (caps hit, unknown severity, ...)
      "counts": {
        "total": int,
        "by_severity": {"critical":n,"high":n,"medium":n,"low":n,"info":n},
        "by_vuln_class": {label: n},
        "by_file": {path: n}                      # top 20 only
      },
      "findings": [ {                           # sorted severity desc, cvss desc
        "idx": int,                             # 1-based, stable display number
        "title": str (cap 500), "severity": one of the 5 above,
        "vuln_class": str, "vuln_class_label": str, "cwe": str|null,
        "cvss_score": float|null, "cvss_vector": str|null, "cvss_rating": str|null,
        "file": str, "line_start": int, "line_end": int,
        "confidence": float 0-1, "votes": int,
        "verdict": "TRUE_POSITIVE"|"FALSE_POSITIVE"|null,
        "verdict_confidence": int|null, "verdict_reason": str,
        "description": str, "impact": str, "exploit_scenario": str,
        "preconditions": [str], "recommendation": str, "code_snippet": str,
        "exploitability_notes": str, "verifier_reasoning": str,
        "offensive_priority": str|null, "offensive_reason": str,
        "source_ref": str|null, "sink_ref": str|null,
        "duplicates": [{"file":str,"line_start":int,"line_end":int}]
      } ],                                      # each text field cap 20000 chars
      "chains": [ {"title": str, "steps": [int], "severity": str, "narrative": str} ],
      "dropped_count": int, "raw_findings_count": int,
      "metrics": {                              # all optional / null
        "duration_sec": float, "total_files_in_scope": int,
        "analyzed_files_unique": int, "loc_scanned_by_language": {lang: int},
        "true_positive_count": int, "false_positive_count": int,
        "total_tokens": int
      },
      "manifest": {                             # only when run_manifest uploaded
        "target_git_sha": str|null, "duration_sec": float|null,
        "models": {role: {"id": str, "provider": str}},
        "total_cost_usd": float|null, "total_tokens": int|null
      } | null
    }

**findings.json mapping** (VVAH `FinalReport`, `vvaharness/models/_scan.py`):
`findings[i]` is a `RankedFinding` = `{finding: Finding, severity, exploitability_notes}`;
copy `Finding.*` fields by name, take `severity` from the outer wrapper
(fallback inner), `exploitability_notes` outer-then-inner. `chains[]`,
`dropped[]` (count only), `raw_findings_count`, `metrics` (ScanMetrics),
`summary`, `degraded*`, `repo_name`, `git_sha` map 1:1. Severity vocab:
`critical|high|medium|low|info`; unknown → `medium` + assumption note.
Detect the format by the presence of top-level `findings` + `repo_root`
(findings.json) vs `runs` + `$schema`/`version` (SARIF).

**SARIF 2.1.0 mapping** (VVAH's own `md_to_sarif` output): per `runs[0].results[]`:
`ruleId`→vuln_class, `properties.severity` (fallback: `level` error→high,
warning→medium, note→low), `properties.{cwe,cvssScore,cvssVector,
cvssRating,confidence}`, `message.text`→description,
`locations[0].physicalLocation.{artifactLocation.uri, region.startLine/endLine}`,
`relatedLocations[]`→duplicates. Fields SARIF lacks stay empty strings.
`runs[0].tool.driver.{name,version}`→tool/tool_version.

**Real-vs-synthetic schema facts (RCA #25).** The synthetic sample
originally assumed `vuln_class_label` is always populated and that
`tool_version` lives in `findings.json`; the real VVAH 1.3.0 output proved
both wrong: `vuln_class_label` is `null` (ingest falls back to
`vuln_class`), and the tool version exists only in the run manifest
(`version`), which the router copies into `report.tool_version` when a
manifest is uploaded. VVAH 1.3.0's full field surface is now pinned by
`FINDING_FIELDS_1_3_0` / `FINAL_REPORT_FIELDS_1_3_0` contract tests plus
the every-field `acme_full_schema.json` fixture (§9), so a future VVAH
version bump that renames or drops a field fails a test instead of
silently rendering blank.

**Caps:** upload ≤ 10 MB, ≤ 2000 findings kept (rest counted in
`dropped_count` with an assumption note), per-text-field 20000 chars.

## 4. API — `app/codereview/router.py`, prefix `/api/v1/codereview`

| Method/path | Role | Notes |
|---|---|---|
| `POST /reviews` (multipart: `report` file, optional `manifest` file, `name` form) | admin/reviewer | 201 → the GET shape. Accepts `.json`/`.sarif`/`.zip` (kit output or ad-hoc zip, §8). 422 on unparseable / wrong schema, 413 > 10 MB |
| `GET /reviews` | any | list rows: review_id, name, repo_label, git_sha, source_format, created_at, counts.total, counts.by_severity, `demo`, `editable` |
| `GET /reviews/{id}` | any | full row incl. `report` |
| `PATCH /reviews/{id}` `{name}` | admin/reviewer, owner org only | rename |
| `DELETE /reviews/{id}` | admin/reviewer, owner org only | soft delete |
| `GET /reviews/{id}/export.xlsx` | any | StreamingResponse, `<name>-code-review.xlsx` |
| `GET /reviews/{id}/export.pptx` | any | StreamingResponse, `<name>-briefing-deck.pptx` |
| `GET /kit.zip` | any authenticated user | streams the consultant scan kit, built in memory (§8) |

All non-demo queries org-scoped and `deleted_at IS NULL`. **Demo reviews**
(`cf39b7d`, 2026-09-12): the env var `CODEREVIEW_DEMO_REVIEW_IDS`
(comma-separated review ids, wired in `docker-compose.vps.yml` from the
VPS `.env`) marks reviews every signed-in user may list, open and export
read-only, regardless of org; `PATCH`/`DELETE` stay owner-org only.
List/detail rows carry `demo` and `editable` so the UI hides rename/delete
and shows a "Demo" chip. Read per request (`_demo_ids()`), so changing the
list needs only a container recreate. Prod demo: the NodeGoat golden
review `49e45724-ff5d-4e53-937b-aba306d3cfd3`. Audit actions:
`codereview.review_created` / `codereview.review_deleted`, resource_type
`code_review`. Upload trust boundary: reuse `_sanitize_filename` from
`app/routers/documents.py`; storage key
`org/{org_id}/codereview/{review_id}/{filename}` via
`get_storage_instance()`.

**Zip upload guards** (`ingest.unpack_scan_zip`, pure, also covers the kit
output, §8): detected by `.zip` suffix or `PK` magic. All violations →
422, never 500: ≤ 50 entries, ≤ 10 MB declared per member, ≤ 30 MB declared
total (checked before any read), no absolute / drive-letter / `..` / NUL
names, symlink entries skipped (`stat.S_ISLNK`, fixed from an
operator-precedence bug that always tested bit 0), post-read size check,
corrupt / encrypted / unsupported members mapped to `IngestError` rather
than raw `BadZipFile`/`RuntimeError`. Report = shallowest `findings.json`,
else shallowest `*.sarif`; manifest = shallowest `run_manifest*.json` (an
explicit `manifest` upload wins). Only the chosen members are decompressed;
the extracted report is what gets stored, under its sanitized basename.

## 5. Ingest rules

- **Caps** (enforced in `ingest.py`): upload ≤ 10 MB; ≤ 2000 findings kept,
  remainder counted in `dropped_count` with an assumption note; each text
  field capped at 20000 chars; `file` path capped at 500 chars; optional
  manifest upload gets the same size cap as the report.
- **Sorting:** findings are sorted severity-desc then CVSS-desc and
  renumbered `idx` 1..N for stable display — this reordering is why chain
  steps must be remapped (next bullet).
- **Chain-step remap (RCA #22).** `chains[].steps` in VVAH's own
  `findings.json` index findings in VVAH's *original* emission order, not
  the sorted display order. `_from_findings_json` stamps a `_pos` per
  finding; `_finalize` builds a `pos_to_idx` map after sorting and remaps
  every chain step (0-based indexing only recognized when a literal `0`
  appears in the steps array; an unmappable step is kept verbatim rather
  than dropped), then strips the internal `_pos` field before persisting.
  Any future field that references another finding by position must be
  remapped in the same function that reorders — grep for `steps`,
  `canonical_idx`, `duplicates` whenever the sort key changes.
- **SARIF narrative (RCA #34):** `properties.description` is split on
  `#### <Heading>` lines (Description, Impact, Exploit scenario,
  Preconditions, How to fix, Adversarial verification; unknown headings end
  a section, text before the first heading is dropped). The first ```
  fenced block becomes `code_snippet` (never part of a section), a
  `**Exploitability:**` line goes to `exploitability_notes`, and a leading
  `**Verdict:** <TP|FP> (confidence: N/10) — reason` line in the
  verification section fills `verdict`/`verdict_confidence`/`verdict_reason`.
  `offensivePriority`/`offensivePriorityReason`, `category` (label) and
  `result.remediation` ("Remediation: <status>. <reason>" in
  `exploitability_notes`) are mapped; `run.properties.scanDegraded` plus
  the invocation notifications (minus "non-fatal error" lines, first 10)
  become `degraded`/`degraded_reason`.
- **Uploading Agentic SAST / VVAH 1.4 scan output (operator guide,
  2026-09-23).** A scan run folder (e.g. the Keycloak
  `Report_only_and_fix_mode.zip`, ~1000 files) holds, per run:
  `<repo>_<ts>_report.sarif` (upload this), `<repo>_<ts>_report.md`
  (human report; **not uploadable**, the importer is JSON-only), 25
  `NN_<slug>/` folders with `finding_case.json`, `evidence/triage.json`,
  `summary.md` and in fix mode `diff.patch` (not read), plus `config.yaml`,
  run log and Maven/surefire output (not read). In fix-mode runs the SARIF
  sits under `security-remediation/`.
  - **Do not upload the whole zip:** `MAX_ZIP_ENTRIES = 50`, so it is
    rejected. Upload the `.sarif` alone, or a zip holding only it.
  - **Upload formats accepted:** `findings.json`, `.sarif`, `.zip`
    (≤ 10 MB). Detection is by content: `findings`+`repo_root` keys →
    findings.json path; `runs` + `$schema`/`version` → SARIF path.
  - **What a SARIF upload fills** (since `1033775`): everything the
    findings.json path fills except exploit **chains** (SARIF has no field
    for them — they only exist in VVAH `findings.json`), `source_ref` /
    `sink_ref`, and the verdict on findings whose verification section
    lacks a `**Verdict:**` line (18 of 121 on Keycloak).
  - **"Scan degraded" banner** is the scanner's own flag
    (`run.properties.scanDegraded`). On the Keycloak run: exploit-chain
    analysis failed to parse (findings unranked, export falls back to
    severity/CVSS order) and 2 of 1805 deep-dive chunks timed out; ~100
    per-chunk "non-fatal error" notes are filtered out of the reason.
  - **Report-only vs fix mode:** both SARIFs carry the same 121 findings;
    they differ only in `result.remediation` status. What was actually fixed
    (14/25 on Keycloak) and the patches live in the per-finding
    `triage.json` / `diff.patch`, which the importer does not read. The
    Keycloak fix-mode Maven build failed at `keycloak-services`.
  - **Repo name / git SHA** are absent from SARIF: type a review name at
    upload.
  - Before `1033775` the same result came from a throwaway converter
    (`sample/upload_ready/sarif_to_findings.py`, local only, gitignored);
    it is obsolete — upload the SARIF directly. Reviews imported from SARIF
    before that commit keep the thin shape until re-uploaded.
- **Severity normalisation:** vocabulary is `critical|high|medium|low|info`;
  an unrecognized severity string falls back to `medium` with a
  deduplicated assumption note (an earlier build repeated the note once
  per offending finding).
- **Unknown-severity note dedup:** one assumption note per unique cause,
  not per finding — fixed as part of the initial build's Phase 3 critique.

## 6. Reports — XLSX and PPTX

Both share `report_common.resolve_branding`, the `_guard` formula-injection
guard, and the BRAND `341954` / ACCENT `00A98B` / ZEBRA `F3F0F7` palette
from MITRE.

**Highlight word lists — single source (RCA #23, `5ed1053`).** The
risk/fix keyword regexes used by the drawer, the XLSX, and the PPTX live
ONLY in `apps/api/app/codereview/highlight_words.json`. `report_xlsx.py`
loads it at import (`report_pptx.py` imports the compiled regexes from
there); the web copy
`apps/web/app/codereview/[reviewId]/components/highlightWords.ts` is
GENERATED by `python scripts/generate_highlight_words.py`, and
`test_codereview_report.py::test_highlight_words_web_mirror_is_current`
fails when it is stale. To add a word: edit the JSON (fragments must be
valid in both Python `re` and JS), run the script, commit both.

**Sentence-splitting rule (RCA #24, #26).** LLM prose is split into
bullet-sized sentences for both the XLSX rich-text cells and the PPTX
one-liners. The naive `[.!?]` + space + capital split cut sentences inside
code spans containing an ellipsis (`` `SELECT ... FOR UPDATE` ``); fixed
with a `(?<!\.\.)` lookbehind in both `report_xlsx.py`'s `_SENTENCE_SPLIT`
and `FindingDrawer.tsx`'s `sentences` memo — any text rule that exists in
both Python and TS must be fixed and tested in both places in the same
commit. A second bug (RCA #26) let literal backticks reach a PPTX table
cell that used plain `set_cell` instead of the `rich_runs` path that turns
backtick spans into blue mono runs; fixed by stripping `` ` `` before
`set_cell` on that one-line cell. Rule going forward: any plain-text
surface fed from LLM markdown needs the same de-markdown step; prefer
routing through `rich_runs` whenever the cell can hold runs.

**XLSX (`report_xlsx.py`).** Sheets: Read Me, Summary (counts, metrics,
manifest, section bands, severity chips, centred numbers with thousands
separators, duration in minutes, scanner version), Findings Register (one
row per finding + Owner / Status / Target date / Notes tracker columns;
Severity / Verdict / Status rendered as tinted chips using the same hex
tints as the web UI; Status is a dropdown — Open, In progress, Fixed,
Accepted risk, False positive — with conditional-format colours; long
prose columns — "What is wrong", "Why it matters", "How to fix", "How it
is exploited" — are split into bullet sentences as openpyxl
`CellRichText` with code tokens in Consolas blue, attack terms in rose
bold, and fix actions in green bold; row heights estimated from text
length; freeze at D2), Exploit Chains (explanatory banner, numbered steps
resolved to finding titles, a "Fix this first" column, bulleted
narrative). `_guard` still applies to every plain string; rich-text cells
start with a bullet so cannot be formulas.

**Determinism (`0db4a86`).** `wb.properties.created`/`modified` are pinned
and the zip container is rewritten with fixed entry timestamps
(`_normalize_zip`) so repeated exports of the same report are byte-
identical — needed once real-world build times exceeded 1 second and a
determinism test started flaking.

**PPTX (`report_pptx.py`, rebuilt `e55a556` on the MITRE deck engine:
keyword runs, auto-highlighted numbers, styled native charts with per-bar
colours, section dividers with giant numbers).** Deck slide list as
shipped, 12–17 slides depending on data: Cover → Executive Summary (5
tiles + the 3 most severe findings with impact one-liners) → Risk Profile
(severity column chart, type bar chart, top-5 files bar strip) → Findings
at a Glance (top 12, severity-tinted cells) → divider 01 → Critical
Findings spotlights, two per slide (what / why / fix as highlighted
bullets) → divider 02 → Exploit Chains drawn as pentagon → chevron step
flows with "Break it: fix #N first" → divider 03 → Remediation Plan
(table ordered by severity then chains broken; right column: greedy
set-cover "fewest fixes that break every chain", highs batched by file,
verify — the order is deterministic, ties → lowest idx) → Scan Coverage &
Confidence (4 tiles, LOC-by-language chart, verifier note, limits) → Next
Steps (4 numbered cards) → closing, with the VVAH attribution and the
"triage candidates" caveat. Body text 9.5–11 pt, tile numbers 30 pt.

**Visual QA recipe (PowerPoint COM).** The method that worked with no
LibreOffice on the build box: `Presentation.Export(dir, "PNG")` via
PowerShell's PowerPoint COM automation, then review the rendered PNGs
directly. Used for the NodeGoat deck; rendered slides kept at
`screenshots/codereview_deck_2026_09_12/`.

## 7. Frontend — `apps/web/app/codereview/`

Pages: `page.tsx` (list cards), `new/page.tsx` (two-column upload), `[reviewId]/page.tsx`
(results with tabs and drawer), `lib.ts` (types + pure helpers). Inline
axios per page (house rule). Nav entry: "Code Security Review", icon `Bug`.

**Information architecture, as built:** `/codereview` (list of reviews,
cards), `/codereview/new` (two-column: "Get the scanner" | "Upload
results"), `/codereview/[id]` (results: header band → severity strip →
tabbed Findings / Exploit chains / Scan details → table/cards + drawer).

**List page (`/codereview`).** Cards show name (truncate), repo label +
short sha chip, date; a stacked horizontal severity bar (critical→info,
proportional widths) with counts as a one-line legend; footer with total
findings, chain count, source-format chip (`findings.json` / `SARIF`).
Kebab menu (dropdown-menu) → Rename, Delete via a confirm dialog (never
`window.confirm`). Empty state with the two CTAs (Get scanner, New
review); skeleton cards while loading; inline alert on error, matching
MITRE.

**Upload page (`/codereview/new`).** Left column: "Get the scanner" card
with a live download button (blob GET with the bearer header — the "kit
download disabled" state from the design draft was replaced with a
working download once §8 shipped), 3-step instructions, and a copyable
direct `vvaharness scan … --stop-after s9` command. Right column: name
field, a single dropzone accepting `.json`/`.sarif`/`.zip` (≤ 10 MB), a
secondary dashed row for the optional manifest, primary submit button
full-width on mobile. Validation inline under the dropzone (type, size);
server `detail` surfaces in the same slot; submit shows a spinner +
"Parsing…" label. Columns stack below 768 px.

**Results page (`/codereview/[id]`).** Executive band (5 stat tiles + one
derived plain-English headline, `deriveHeadline()` — deterministic:
highest-severity count + top file) in the MITRE `ExecutiveBand` visual
style (thin border, no gradients). Severity strip of toggle chips
(critical→info) that filter the table and update counts live. Tabs:
Findings (sortable/searchable table — columns #, severity dot+label,
title, class, CWE link, CVSS mono, confidence mini-bar with vote-count
tooltip, file:lines mono, verdict chip; mobile falls back to card rows),
Exploit chains (one card per chain: title, severity chip, narrative, step
pills that open the drawer), Scan details (two definition lists — scan
metrics and run manifest — plus the `assumptions[]` list under "Ingest
notes"). Detail drawer (`Sheet`, resizable via `useSheetResize`, stored
width key `codereview-sheet-width`): header (#, severity chip, title),
meta grid (CWE link, CVSS score + vector, confidence/votes, verdict +
reason, file + lines, source → sink), sections in a fixed order — What is
wrong · Why it matters · How to fix · How it is exploited · Preconditions
· Code (`<pre>` with line-start numbering) · Exploitability · Verifier
reasoning · Also at — each heading with a colour marker and tooltip;
prev/next finding buttons respecting the current filter/sort; `?finding=N`
deep link read via `window.location.search` in the mount effect (not
`useSearchParams`, which would need a Suspense boundary at build time).
Footer carries the VVAH attribution line in muted text. States: loading
skeleton for band + 6 rows; a dismissible-per-session amber degraded
banner; empty filtered state.

**`RichText`/`Highlight` (drawer).** Sentence-split (abbreviation- and
ellipsis-safe, RCA #24) into bullets; code tokens/paths/endpoints render as
mono chips, URLs as links, attack words rose bold (`RISK_RE`), fix words
emerald bold (`FIX_RE`, only inside "How to fix") — sourced from the
single `highlight_words.json` (§6). Quick-fact chips and a full-width
green verdict-reason note sit above the sections; body text is slate-800
at 13.5 px.

**Visual system — matches the live ScopeWise theme.** Source of truth:
`apps/web/app/globals.css` + `tailwind.config.ts` +
`apps/web/app/mitre/lib.ts` chip classes; no invented tokens.

- **Base:** white background, Inter, foreground `222 47% 11%`, borders
  `border` (`214 32% 91%`), radius `0.5rem` (`rounded-md` on cards/inputs,
  `rounded-full` on chips). No shadows, no gradients.
- **Primary blue** `hsl(210 100% 40%)` (`text-primary` / `bg-primary`) is
  the only action colour: primary buttons, active nav, active severity
  chip outline, headline numbers in the executive band (`text-primary`, as
  `ExecutiveBand` does), links (CWE, deep link), focus rings (`ring-ring`),
  row hover `hover:bg-primary/5`.
- **Muted** (`bg-muted`, `text-muted-foreground`) for labels, empty
  states, footers, secondary chips (source format, sha).
- **Severity colours** — use wherever severity appears (tiles, strip,
  table dot + chip, stacked bar, drawer header, chain cards), always in
  the MITRE tinted-chip pattern `bg-{c}-100 text-{c}-800 border-{c}-200`
  plus a solid `bg-{c}-600` dot / bar segment:

  | Severity | c | Chip | Dot/bar |
  |---|---|---|---|
  | critical | rose | `bg-rose-100 text-rose-800 border-rose-200` | `bg-rose-600` |
  | high | orange | `bg-orange-100 text-orange-800 border-orange-200` | `bg-orange-500` |
  | medium | amber | `bg-amber-100 text-amber-800 border-amber-200` | `bg-amber-500` |
  | low | emerald | `bg-emerald-100 text-emerald-800 border-emerald-200` | `bg-emerald-600` |
  | info | sky | `bg-sky-100 text-sky-800 border-sky-200` | `bg-sky-500` |

  Verdict chips: TRUE_POSITIVE `emerald` tint, FALSE_POSITIVE `bg-muted
  text-muted-foreground` with a "Verifier: false positive" tooltip.
  Degraded banner: `amber` tint. Destructive actions: `text-destructive`.
  Every chip gets a tooltip (locked MITRE rule).
- **Colour in numbers:** executive-band tiles show the count in the
  severity colour (`text-rose-700`, `text-orange-600`, …) with muted
  labels; the stacked bar on list cards uses the dot colours in severity
  order left→right; confidence mini-bar uses `bg-primary`.
- **Type scale** (same as MITRE): page title `text-lg font-semibold`, tile
  number `text-2xl font-bold`, tile label `text-[11px]`, table `text-sm`,
  chips `text-[11px] font-medium`, mono for sha / CVSS vector / file paths
  (`font-mono text-xs`).
- **Spacing:** `p-3.5` cards, `gap-2`/`gap-3` grids, 36 px table rows,
  `mb-4` between page blocks. **Motion:** `transition-colors` 150 ms only;
  Sheet slide for the drawer. **Icons:** lucide outline 14–16 px, muted
  unless it is a severity dot; module icon is `Bug`.
- Dark mode is `class`-based but not shipped; tokens stay semantic so it
  works if enabled later.

## 8. Consultant scan kit

Goal: a consultant gets everything needed to produce the fixed-format
input from the upload page, without reading VVAH docs.

- **Pinned VVAH release, hosted in the repo.** VVAH has no PyPI package and
  no GitHub release assets, so the wheel is built from the tag
  (`pip wheel --no-deps git+…@<tag>`) and vendored at
  `apps/api/app/codereview/kit/vendor/vvaharness-<ver>-py3-none-any.whl`
  with `LICENSE`, `NOTICE`, `THIRD_PARTY_LICENSES.md`. Pin + sha256 live in
  `kit/bin/KIT_VERSION.json` (the source of truth; **1.4.0 since
  2026-09-23**, was 1.3.0).
- **Keeping the scan kit on the latest VVAH (2026-09-23).**
  - *Detect:* `.github/workflows/vvah-kit-update.yml` runs Mondays 04:00
    UTC (and on demand, optional `tag` input). It calls
    `scripts/update_vvah_kit.py --check` (exit 10 = a newer release than
    the pin). Manual check: `python scripts/update_vvah_kit.py --check`.
  - *Upgrade (automated):* `python scripts/update_vvah_kit.py [--tag vX.Y.Z]`
    builds and vendors the wheel, refreshes the three licence files, and
    rewrites every pin: `KIT_VERSION.json` (version, tag, wheel, sha256,
    date), the kit `README.md` install line, the `config.yaml` header, and
    `KIT_VERSION` in `apps/web/app/codereview/new/page.tsx`. It stops with
    a message if a pin's expected text is missing (hand-edited).
    `test_kit_version_pins_agree` fails if any pin drifts.
  - *CI gate before the PR:* installs the new wheel in a venv, prints
    `vvaharness --version`, loads the kit `config.yaml` with VVAH's own
    `vvaharness.config.load` (asserts remediate/validate stay off; no model
    spend), runs `tests/test_codereview_kit.py --noconftest`, then opens a
    PR `vvah-kit/<tag>` whose body carries the release's CHANGELOG section.
    Needs the repo setting "Allow GitHub Actions to create pull requests"
    (turned on 2026-09-23 via `gh api -X PUT …/actions/permissions/workflow`,
    default workflow permissions left read-only); if it is ever turned off
    the job falls back to an issue pointing at the pushed branch. The job
    never merges or deploys.
  - *Human steps before merging:* read the CHANGELOG section for
    `findings.json` schema (`vvaharness/models/_scan.py`), SARIF writer, CLI
    flag and default-profile changes; run the full backend suite; run one
    real scan (NodeGoat, small, few tokens) and upload its `findings.json`
    and `.sarif`; if new fields appear, extend the field lists in
    `test_codereview_ingest.py` (keep the old lists; older kits stay in
    consultants' hands) and `ingest.py`; review the "About the scanner"
    panel text on the upload page (stage names/limits come from VVAH's
    `docs/architecture.md`); deploy; tell consultants to re-download.
  - *Policy:* pin a tag + sha256, never float to `main`; upgrade within ~2
    weeks of a release; the importer stays backward compatible with every
    VVAH version still in use.
  - *1.3.0 → 1.4.0 findings (2026-09-23):* only headline change is
    exploit verification (beta, API only, off unless `EV_API_COLLECTION`
    is set; adds `ev_*` fields to `findings.json`, SARIF unchanged);
    `default.yaml` now disables S10/S11 (our kit already sets both off);
    `models/_scan.py` byte-identical; kit config loads unchanged. Not yet
    done: a real 1.4 NodeGoat scan to refresh the golden fixture — **deferred
    by the owner (no AI credit, 2026-09-23); do not start it unasked**.
- **Kit layout, as shipped** (`apps/api/app/codereview/kit/`), served by
  `GET /api/v1/codereview/kit.zip` (any authenticated user; built in
  memory by `kit.build_kit_zip()`, rooted at `scopewise-scan-kit/`): kit
  root shows exactly one setup entry per platform (`setup.cmd`/`.sh`,
  `scopewise-scan.cmd`/`.sh`, user request "only one setup file to pick"),
  with `README.md`, `config.yaml`, and the PowerShell internals
  (`bin/setup.ps1`, `bin/scopewise-scan.ps1`, `bin/KIT_VERSION.json`) and
  vendored release (`vendor/vvaharness-<ver>-py3-none-any.whl` + `LICENSE`,
  `NOTICE`, `THIRD_PARTY_LICENSES.md`) tucked under `bin/`/`vendor/`;
  `.venv`, `.env`, `logs/`, and produced zips appear after first use.

- **`config.yaml`** — partial VVAH profile: S1–S9 roles on
  `deepseek/deepseek-v4-pro`, the two high-volume survey roles
  (`autoexclude`, `graph_annotate`) on `deepseek/deepseek-v4-flash`, all
  `via: openai` against `OPENAI_BASE_URL` (default
  `https://openrouter.ai/api/v1`); `step0.callgraph_detection: llm`;
  `step4.runs: 1`; `step_remediate` / `step_validate` disabled. The
  `inject:` block is mandatory even in a partial profile (VVAH 1.3.0 has
  no default for it → `AttributeError: inject`); it points at optional,
  absent files.
- **`scopewise-scan.ps1` / `.sh`** — cd to the kit dir, require `.env` +
  `vvaharness` on PATH (prefers `.venv` when present), `estimate` → y/N
  prompt → `scan --repo <path> --stop-after s9 --config config.yaml` → zip
  `findings.json` + `*.sarif` + newest `run_manifest_*.json` (all at zip
  root) as `scopewise-scan-<repo>-<yyyymmdd>.zip`. Both set
  `PYTHONUTF8=1` (VVAH prints UTF-8 glyphs; cp1252 consoles crash
  otherwise). The key is only ever read from `.env`. Each run tees its
  full console output plus timestamped phase markers into
  `logs/scan-<repo>-<timestamp>.log` in the kit folder (local only, not
  in the zip); on a non-zero exit the script names the transcript, VVAH's
  `*_errors.jsonl` traceback and the `run_manifest` stage timeline.
  **Size guard** (after `estimate`): refuse > 20,000 code files or
  > 500 MB with "scan a fresh clone" advice; warn above 2,000 files or
  when dependency/build folders are found. Timing facts for setting
  expectations: NodeGoat (63 files) took 102 minutes; the floor is
  ≈ 10–15 minutes; a 2–3 minute scan is not possible.
- **`setup.cmd` / `scopewise-scan.cmd`** — Windows launchers that
  `cd /d %~dp0`, `Unblock-File bin\*.ps1`, and run them with
  `-ExecutionPolicy Bypass`, because a downloaded unsigned `.ps1` is
  refused by the default policy (Mark-of-the-Web) and `Set-Location` does
  not change the working directory a `cmd` child inherits.
- **`setup.ps1` / `setup.sh`** — one-time install with installer-style UX:
  banner → find Python ≥ 3.11 → create `.venv` in the kit folder →
  pip-install the vendored wheel with a live "resolving dependencies (n
  packages)" progress indicator → prompt for the OpenRouter key (hidden
  input) → write `.env` → green "Setup complete" box with the next
  command → "Press Enter to finish" when interactive (fails fast instead
  of hanging on `Read-Host` when there is no console). Failures show a
  red box and exit 1.
- **`README.md`** — "Quick start (3 commands)" + "Manual install (plain
  pip)" + upload instructions + a scan-time expectations table, ≈ 45
  lines.

**Windows / VVAH gotchas encoded in the scripts:** `PYTHONUTF8=1` (VVAH
prints Unicode glyphs that crash cp1252 consoles); native commands run
through `cmd /c … 2>&1` because `$ErrorActionPreference='Stop'` turns a
native stderr line into a terminating PowerShell error on PowerShell 5.1;
`Tee-Object` writes UTF-16 on PowerShell 5.1, so log lines are appended
with `-Encoding UTF8` instead; time format uses `HH\:mm\:ss` to avoid the
locale's date separator; `Set-Location` does not change the cwd a `cmd`
child process inherits, so every launcher does its own `cd /d %~dp0`; a
downloaded `.ps1` carries the Mark-of-the-Web and is refused by the
default execution policy, fixed with `Unblock-File` + `-ExecutionPolicy
Bypass` in the `.cmd` launchers rather than a global policy change. Cost/
time reality check: `OWASP/NodeGoat` (63 files) ≈ $4 on
`deepseek/deepseek-v4-pro`/`flash` via OpenRouter, ~102 minutes wall
clock.

**Upload accepts the kit zip** (`ingest.unpack_scan_zip`, §4 has the full
guard list) — detected by `.zip` suffix or `PK` magic; only the chosen
members are decompressed; extracted report stored under its sanitized
basename.

**UI.** "Get the scanner" panel on `/codereview/new` (live download
button, blob GET with the bearer header, 3-step instructions, copyable
direct command); dropzone accepts `.json`/`.sarif`/`.zip`.

**Tests** (`test_codereview_kit.py`, `test_codereview_api.py`): kit zip
contents + wheel sha256, config sanity, script sanity, kit endpoint 200,
zip round-trip 201, entry-count / traversal / oversize / no-report / SARIF
fallback cases.

## 9. Test data & tests

`docs/sample/CodeReview_Sample/` (root) is **synthetic** (generated by
`scripts/generate_codereview_sample.py` to match VVAH's `FinalReport`
schema) — good for UI/ingest tests, not proof of real-scanner
compatibility. `acme_full_schema.json` is a companion synthetic fixture
that populates every VVAH 1.3.0 field (added alongside the highlight-word
consolidation, `5ed1053`) so schema-coverage tests don't require a second
real scan.

`docs/sample/CodeReview_Sample/real/nodegoat/` is a **real VVAH 1.3.0
run** (kit config, `--stop-after s9`) against `OWASP/NodeGoat`
(Apache-2.0, commit `c5cb68a7084e4ae7dcc60e6a98768720a81841e8`): 88 raw →
29 findings (6 critical / 5 high / 18 medium), 6 chains, 3.4M tokens, ≈ $4
on `deepseek-v4-pro` via OpenRouter, 103 min wall clock — see its README.
It is the golden fixture for
`test_codereview_ingest.py::test_real_nodegoat_golden`; if a VVAH bump
changes the schema, that test is what breaks first. This review is also
the production demo (`49e45724-ff5d-4e53-937b-aba306d3cfd3`, §4).

**Pinned field lists:** `FINDING_FIELDS_1_3_0` / `FINAL_REPORT_FIELDS_1_3_0`
in the test suite assert VVAH 1.3.0's exact field surface, so a future
version bump that renames or drops a field fails loudly instead of
rendering silently blank.

**Test file map:**

| File | Guards |
|---|---|
| `test_codereview_ingest.py` | findings.json/SARIF parsing, chain-step remap (RCA #22), severity fallback, caps, the real NodeGoat golden, field-surface contract tests |
| `test_codereview_api.py` | CRUD, org scoping, demo-review cross-org access, zip upload round-trip and guards (entry count, traversal, oversize, no-report, SARIF fallback), audit logging |
| `test_codereview_report.py` | XLSX/PPTX structure, `_guard` formula-injection, highlight-word web-mirror freshness (RCA #23), ellipsis-safe sentence split (RCA #24), no raw backticks in PPTX plan table (RCA #26), determinism |
| `test_codereview_kit.py` | kit zip contents + wheel sha256, config sanity, script sanity, kit endpoint 200 |

## 10. Ops runbook

**Deploy loop** (standard ScopeWise VPS loop, see project `CLAUDE.md`):
`git push` → `ssh a11yos-vps "cd /opt/scopewise && git pull && docker
compose -f docker-compose.vps.yml --env-file .env build && GIT_SHA=$(git
rev-parse --short HEAD) docker compose -f docker-compose.vps.yml
--env-file .env up -d"` → apply migration 039 if not already applied →
smoke test.

**In-container smoke commands used after every deploy:**

    docker exec scopewise-api python -c "import app.codereview.router"
    docker exec scopewise-api python -c "import app.codereview.report_xlsx"
    docker exec scopewise-api python -c "import app.codereview.report_pptx"
    docker exec scopewise-api python -c "from app.codereview.report_xlsx import _sentences; assert '...' in _sentences('Use \`SELECT ... FOR UPDATE\` now.')[0]"

The last command is the ellipsis-safe-split regression check (RCA #24) —
run it whenever `_SENTENCE_SPLIT` changes.

**Manual prod UI check:** upload
`docs/sample/CodeReview_Sample/acme_findings.json` (or the golden zip) at
`/codereview/new` → confirm the findings table renders → open the drawer
and check highlight colouring → download both XLSX and PPTX and spot-check
against the report → delete the test review afterward so it doesn't linger
as a non-demo row.

**Demo flag:** `CODEREVIEW_DEMO_REVIEW_IDS` (comma-separated review UUIDs)
in the VPS `.env`, read by `docker-compose.vps.yml`; changing the list only
needs a container recreate, not a rebuild (§4).

## 11. Attribution & licence

VVAH is Apache-2.0, © 2026 Visa, Inc. ScopeWise consumes its output files
only; no VVAH code is vendored except the pinned wheel and its own licence
files inside the kit (§8). The results page footer and the PPTX closing
slide carry the attribution line. The top-level `LICENSE` (proprietary,
Foxfiber Retail LLP, with an Apache-2.0 vendor carve-out for the VVAH
wheel) and a Visa non-affiliation line are shown on the `/codereview`
shell.

## 12. RCA index

| # | One-line summary | Link |
|---|---|---|
| 22 | Exploit-chain step links pointed at the wrong findings after severity re-sort | `docs/RCA_LOG.md` §22 |
| 23 | Highlight word lists drifted between web drawer and XLSX/PPTX | `docs/RCA_LOG.md` §23 |
| 24 | PPTX/XLSX sentence split truncated fix text mid-code (ellipsis bug) | `docs/RCA_LOG.md` §24 |
| 25 | Synthetic fixture disagreed with real VVAH output on two fields | `docs/RCA_LOG.md` §25 |
| 26 | PPTX remediation-plan cell showed literal backticks | `docs/RCA_LOG.md` §26 |

## 13. Open items

- **PPTX org branding.** The deck still calls `resolve_branding(None)`
  (default palette/logo) rather than reading a per-org
  `report_display_name`/branding override. Deferred by the user, not
  forgotten — MITRE already has the per-org override plumbing this would
  reuse.
- **Kit `pricing:` table.** VVAH's `config.yaml` supports a per-model
  `pricing:` table that would let its own run manifest report
  `total_cost_usd` directly; today the kit README carries a hand-written
  list-price estimate instead. Deferred by the user.
- **Second real (Python) golden repo.** The only real-scan golden fixture
  is `OWASP/NodeGoat` (JavaScript). A second real repo, ideally
  Python-heavy so VVAH's Python-specific taint paths get golden coverage
  too, would broaden confidence beyond the synthetic full-schema fixture.
  Not scheduled — no known schema gap motivates it right now (RCA #25 is
  closed via the full-field synthetic fixture, §9).
