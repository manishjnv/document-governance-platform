# Code Security Review — Module Reference

**Status:** v1 build, 2026-09-11. Third ScopeWise module (after SOW Review and
MITRE Assessment). Imports the output of Visa's open-source
[Vulnerability Agentic Harness](https://github.com/visa/visa-vulnerability-agentic-harness)
(VVAH, Apache-2.0) and turns it into a reviewable findings register plus
client-ready XLSX / PPTX deliverables.

## 0. Product context (Q&A captured 2026-09-11)

**What kind of scanner VVAH is.** LLM-driven SAST (static application
security testing): it reads source code at rest. It is not an asset,
vulnerability-management, DAST, or network scanner and never touches
running systems. Versus classic SAST it threat-models the repo first,
uses multi-agent voting instead of only pattern rules (so it catches
logic flaws), and can propose/validate fixes. Tradeoffs: non-
deterministic, no published precision/recall, per-run token cost.

**Comparable products.** Rule-based SAST: Semgrep, SonarQube, Checkmarx,
Fortify, Veracode, CodeQL, Snyk Code. AI-native code security: Amazon
CodeGuru Security, GitHub Copilot Autofix, Snyk DeepCode AI, Aikido,
Corgea, ZeroPath, Mobb. Research harnesses: Google Big Sleep / OSS-Fuzz
AI, DARPA AIxCC tools, Anthropic Project Glasswing (VVAH's stated basis).
Not comparable (asset/infra or DAST): Nessus, Qualys, Rapid7 InsightVM,
Wiz, Orca, Burp Suite, OWASP ZAP.

**Who runs the scan.** The consultant, on their own key and machine (or
on a client-provided jump box when code may not leave the client
network; only `findings.json` comes out). Never the client via a portal
button in v1, and never ScopeWise server-side (see section 1). Cost sits
on the engagement: run `vvaharness estimate` before every scan.

**Input / output in one line.** In: `findings.json` (or `.sarif`) +
optional `run_manifest_*.json` from a `--stop-after s9` run. Out:
findings table + drawer, exploit chains, XLSX tracker, PPTX briefing
deck.

## 1. What this module is (and deliberately is not)

A consultant runs the scanner themselves, detection-only:

    vvaharness scan --repo /path/to/repo --stop-after s9

and uploads the resulting `security-scan/findings.json` (or the `.sarif`)
plus, optionally, `run_manifest_*.json`. ScopeWise stores the parsed
report per org, shows a severity-sorted findings table with a detail
drawer, and exports an XLSX tracker and a PPTX briefing deck.

**Not in scope (decided at feasibility, 2026-09-11):** ScopeWise never
clones repos or runs VVAH server-side. Reasons: VVAH has no spend cap and
defaults to Opus-class models; its own `docs/security.md` requires a
disposable container with egress firewalling for untrusted repos, which
the shared VPS cannot host; sub-70B models degrade its structured output;
and third-party scan authorization would shift onto the platform. No LLM
is called anywhere in this module — everything is deterministic.

**Isolation contract** (same as MITRE, `MITRE_MODULE_REFERENCE.md` §1):
module = `apps/api/app/codereview/` + `code_reviews` table +
`apps/web/app/codereview/`. Shared touchpoints, exhaustive: `main.py`
(+2 lines), `app/models/__init__.py` (+1 registration),
`app/models/enums.py` + `app/models/audit_log.py` + migration 039
(`code_review` audit resource type), `apps/web/components/AppShell.tsx`
(+1 nav entry). Nothing under `app/mitre/`, `app/routers/`, `app/ai/`
changes.

## 2. Storage — migration `039_code_review.sql`

One table. The normalized report lives in JSONB; no per-finding rows
(a results page always loads the whole review; nothing queries findings
across reviews).

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

Plus: widen `audit_logs.resource_type` CHECK with `'code_review'`
(mirror in `app/models/audit_log.py` and `enums.AuditResourceType`;
`audit_logs` is not one of `test_insights_extra.py`'s hand-rolled tables,
so that fixture needs no edit). Apply to edgp_dev, edgp_test, and prod on
deploy — no migration runner exists.

## 3. Normalized report shape (`code_reviews.report`)

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

**Caps:** upload ≤ 10 MB, ≤ 2000 findings kept (rest counted in
`dropped_count` with an assumption note), per-text-field 20000 chars.

## 4. API — `app/codereview/router.py`, prefix `/api/v1/codereview`

| Method/path | Role | Notes |
|---|---|---|
| `POST /reviews` (multipart: `report` file, optional `manifest` file, `name` form) | admin/reviewer | 201 → the GET shape. 422 on unparseable / wrong schema, 413 > 10 MB |
| `GET /reviews` | any | list rows: review_id, name, repo_label, git_sha, source_format, created_at, counts.total, counts.by_severity |
| `GET /reviews/{id}` | any | full row incl. `report` |
| `PATCH /reviews/{id}` `{name}` | admin/reviewer | rename |
| `DELETE /reviews/{id}` | admin/reviewer | soft delete |
| `GET /reviews/{id}/export.xlsx` | any | StreamingResponse, `<name>-code-review.xlsx` |
| `GET /reviews/{id}/export.pptx` | any | StreamingResponse, `<name>-briefing-deck.pptx` |

All queries org-scoped and `deleted_at IS NULL`. Audit actions:
`codereview.review_created` / `codereview.review_deleted`, resource_type
`code_review`. Upload trust boundary: reuse `_sanitize_filename` from
`app/routers/documents.py`; storage key
`org/{org_id}/codereview/{review_id}/{filename}` via `get_storage_instance()`.

## 5. Reports — `report_xlsx.py`, `report_pptx.py`

Same palette/helpers as MITRE (`report_common.resolve_branding`, `_guard`
pattern, BRAND `341954` / ACCENT `00A98B` / ZEBRA `F3F0F7`). Numbers only
from `report` JSONB. XLSX sheets: Read Me, Summary (counts, metrics,
manifest), Findings Register (one row per finding + blank Owner / Status /
Target date / Notes tracker columns), Exploit Chains. PPTX (~8 slides):
cover, how to read, headline tiles, severity + class charts, top-10
findings table, exploit chains, recommended next steps (derived:
critical/high first, grouped by file), closing with the VVAH attribution
and the "triage candidates, not confirmed vulnerabilities" caveat.

## 6. Frontend — `apps/web/app/codereview/`

`page.tsx` (list cards, mirrors `/mitre`), `new/page.tsx` (drag-drop
`findings.json`/`.sarif` + optional manifest + name, with the exact
`vvaharness scan … --stop-after s9` command shown), `[reviewId]/page.tsx`
(severity tiles → filter, sortable/searchable findings table, detail
drawer with the narrative blocks, export buttons), `lib.ts` (types only).
Inline axios per page (house rule). Nav: "Code Security Review".

## 7. Attribution

VVAH is Apache-2.0, © 2026 Visa, Inc. ScopeWise consumes its output files
only; no VVAH code is vendored. The results page footer and the PPTX
closing slide carry the attribution line.

## 8. Consultant scan kit (built 2026-09-11)

Goal: a consultant gets everything needed to produce the fixed-format
input from the upload page, without reading VVAH docs.

- **Pinned VVAH release, hosted in the repo.** VVAH has no PyPI package and
  no GitHub release assets, so the wheel is built from the tag
  (`pip wheel --no-deps git+…@v1.3.0`) and vendored at
  `apps/api/app/codereview/kit/vendor/vvaharness-1.3.0-py3-none-any.whl`
  (1.1 MB) with `LICENSE`, `NOTICE`, `THIRD_PARTY_LICENSES.md`. Pin +
  sha256 live in `kit/KIT_VERSION.json`. Bump the pin only after re-running
  the ingest tests (incl. the golden fixture, §9) against the new release.
- **Kit files** (`apps/api/app/codereview/kit/`), served by
  `GET /api/v1/codereview/kit.zip` (any authenticated user; built in memory
  by `kit.build_kit_zip()`, rooted at `scopewise-scan-kit/`):
  - `config.yaml` — partial VVAH profile: S1–S9 roles on
    `deepseek/deepseek-v4-pro`, the two high-volume survey roles
    (`autoexclude`, `graph_annotate`) on `deepseek/deepseek-v4-flash`, all
    `via: openai` against `OPENAI_BASE_URL` (default
    `https://openrouter.ai/api/v1`); `step0.callgraph_detection: llm`;
    `step4.runs: 1`; `step_remediate` / `step_validate` disabled. The
    `inject:` block is mandatory even in a partial profile (VVAH 1.3.0 has
    no default for it → `AttributeError: inject`); it points at optional,
    absent files.
  - `scopewise-scan.ps1` / `scopewise-scan.sh` — cd to the kit dir, require
    `.env` + `vvaharness` on PATH, `estimate` → y/N prompt → `scan --repo
    <path> --stop-after s9 --config config.yaml` → zip `findings.json` +
    `*.sarif` + newest `run_manifest_*.json` (all at zip root) as
    `scopewise-scan-<repo>-<yyyymmdd>.zip`. Both set `PYTHONUTF8=1` (VVAH
    prints UTF-8 glyphs; cp1252 consoles crash otherwise). The key is only
    ever read from `.env`.
  - Kit root shows one entry per platform: `setup.cmd` + `scopewise-scan.cmd`
    (Windows), `setup.sh` + `scopewise-scan.sh` (macOS/Linux). The
    PowerShell internals and `KIT_VERSION.json` live under `bin/` (user
    request 2026-09-12: "only one setup file to pick").
  - `setup.cmd` / `scopewise-scan.cmd` — Windows launchers that `Unblock-File`
    `bin\*.ps1` and run them with `-ExecutionPolicy Bypass`, because
    a downloaded unsigned `.ps1` is refused by the default policy (hit by the
    first real user on 2026-09-12).
  - `setup.ps1` / `setup.sh` — one-time install: creates `.venv` in the kit
    folder, pip-installs the vendored wheel, prompts for the OpenRouter key
    (hidden input) and writes `.env`. Added 2026-09-12 after the first user
    tried `pip install <kit>.zip` (the zip is not a Python package).
  - `README.md` — "Quick start (3 commands)" + "Manual install (plain pip)"
    + upload, ~45 lines. The scan scripts prefer `.venv` when present and
    fall back to `vvaharness` on PATH.
- **Upload accepts the kit zip** (`ingest.unpack_scan_zip`, pure): detected
  by `.zip` suffix or `PK` magic. Guards, all → 422: ≤ 50 entries,
  ≤ 10 MB declared per member, ≤ 30 MB declared total (checked before any
  read), no absolute / drive-letter / `..` / NUL names, symlink entries
  skipped, post-read size check, corrupt / encrypted / unsupported members
  → 422 never 500. Report = shallowest `findings.json`, else shallowest
  `*.sarif`; manifest = shallowest `run_manifest*.json` (an explicit
  `manifest` upload wins). Only the chosen members are decompressed; the
  extracted report is what gets stored, under its sanitized basename.
- **UI.** "Get the scanner" panel on `/codereview/new` (download button =
  blob GET with the bearer header, 3-step instructions, copyable direct
  command); dropzone accepts `.json/.sarif/.zip`.
- **Tests** (`test_codereview_kit.py`, `test_codereview_api.py`): kit zip
  contents + wheel sha256, config sanity, script sanity, kit endpoint 200,
  zip round-trip 201, entry-count / traversal / oversize / no-report / SARIF
  fallback cases.

Still out of scope: running the scan server-side.

## 9. Test data

`docs/sample/CodeReview_Sample/` (root) is **synthetic** (generated by
`scripts/generate_codereview_sample.py` to match VVAH's `FinalReport`
schema) — good for UI/ingest tests, not proof of real-scanner
compatibility.

`docs/sample/CodeReview_Sample/real/nodegoat/` is a **real VVAH 1.3.0 run**
(kit config, `--stop-after s9`) against `OWASP/NodeGoat` (Apache-2.0,
commit `c5cb68a`): 88 raw → 29 findings (6 critical / 5 high / 18 medium),
6 chains, 3.4M tokens, ≈ $4 on deepseek-v4-pro via OpenRouter, 103 min
wall clock — see its README. It is the golden fixture for
`test_codereview_ingest.py::test_real_nodegoat_golden`; if a VVAH bump
changes the schema, that test is what breaks first. Two schema facts the
synthetic sample had wrong, both handled in ingest now: real
`vuln_class_label` is `null` (fallback to `vuln_class`), and the tool
version only exists in the manifest (`version`), which the router copies
into `report.tool_version` when a manifest is uploaded.
