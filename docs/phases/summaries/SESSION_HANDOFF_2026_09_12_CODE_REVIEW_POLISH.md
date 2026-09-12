# Session handoff — 2026-09-12: Code Security Review shipped, then polished from live use

**Headline:** the Code Security Review module went live in the morning
(commit `ef18ab8`: module + UI pass + hosted scan kit + real NodeGoat golden
scan; migration 039 applied to prod). The rest of the day was driven by the
user actually using it on prod and on their own Windows machine, which
produced nine follow-up commits: a plain-language finding drawer, a
self-installing scan kit that survives Windows download blocking, per-run
transcript logs, a professional XLSX tracker with rich-text highlighting,
and a rebuilt PPTX briefing deck on the MITRE engine. Everything is
committed, pushed and deployed (last deploy `0db4a86`). Suite baseline
**973 passed / 7 skipped** (measured after `ef18ab8`; later commits touched
only report/kit code with their own tests green).

## Commits in order (all on master, all deployed)

| Commit | What | Why (user feedback that triggered it) |
|---|---|---|
| `ef18ab8` | Module, UI pass, kit, golden fixture, docs | Planned scope (kickoff prompt) |
| `f2ffe3e` | Finding drawer rework | "keywords highlighted, simple words in pointers, critical first, darker font, colour, tooltips, resizable with mouse" |
| `461ed68` | `setup.ps1` / `setup.sh`, venv-aware scan scripts, darker UI text | User ran `pip install <kit>.zip` — the zip is not a Python package |
| `00b64ee` | `setup.cmd` / `scopewise-scan.cmd` launchers | PowerShell refused the downloaded `.ps1`: "not digitally signed" (Mark-of-the-Web) |
| `7358769` | Step-by-step progress in setup | Double-clicked window looked hung during the 1–3 min pip install |
| `3b565a6` | Installer-style setup (banner, progress bar, green box, Press Enter), kit root = one setup file per platform, internals in `bin/` | "progress bar and success message like a professional installer"; "too many setup files" |
| `cc46845` | Per-run transcript log `logs/scan-<repo>-<ts>.log` + failure pointers | "are we keeping a detailed log with timeline to know if something failed" |
| `d8681e7` | XLSX: chips, centred numbers, rich-text bullets with highlights, status dropdown, explained chains | Screenshots of the old workbook: plain, wall-of-text, chains unexplained |
| `e55a556` | PPTX rebuilt on the MITRE engine, 12–17 slides, data-rich | "review both ppt engines, get best of both, professional, compact, larger font, data rich" |
| `0db4a86` | XLSX byte-deterministic (pinned core.xml + zip entry timestamps) | Determinism test went flaky once builds took > 1 s |

## What each area looks like now

### Finding drawer (`apps/web/app/codereview/[reviewId]/components/FindingDrawer.tsx`)
- Sections in decision order: What is wrong · Why it matters · How to fix ·
  How it is exploited · Preconditions · Code · Exploitability · Verifier
  reasoning · Also at. Each heading has a colour marker and a tooltip.
- `RichText`: sentence split (abbreviation-safe) → bullets; `Highlight`:
  code tokens/paths/endpoints as mono chips, URLs as links, attack words
  rose bold (`RISK_RE`), fix words emerald bold (`FIX_RE`, only in How to
  fix). The same two regex lists are mirrored in `report_xlsx.py` and
  reused by `report_pptx.py` so UI, XLSX and PPTX highlight identically.
- Quick-fact chips (CWE link, CVSS coloured by score, confidence bar,
  verdict, file, source → sink), verdict reason in a full-width green note,
  body text slate-800 at 13.5 px, visible drag grip with its own stored
  width (`codereview-sheet-width`), `?finding=N` deep link via
  `window.location` (no `useSearchParams` → no Suspense boundary needed).

### Scan kit (`apps/api/app/codereview/kit/`)
```
setup.cmd / setup.sh               ← the only "setup" entries a user sees
scopewise-scan.cmd / .sh           ← run a scan
README.md  config.yaml  bin/  vendor/  (+ .venv, .env, logs/, zips after use)
bin/setup.ps1, bin/scopewise-scan.ps1, bin/KIT_VERSION.json
vendor/vvaharness-1.3.0-py3-none-any.whl + LICENSE, NOTICE, THIRD_PARTY_LICENSES.md
```
- `.cmd` launchers: `cd /d %~dp0`, `Unblock-File .\bin\*.ps1`, run the
  `.ps1` with `-ExecutionPolicy Bypass`, propagate exit code. Users type
  `.\setup.cmd` (PowerShell needs the `.\`).
- `setup.*`: banner → 4 steps (find Python ≥ 3.11 · create `.venv` ·
  install wheel with a live "resolving dependencies (n packages)" bar ·
  hidden key prompt → `.env`) → green "Setup complete" box with the next
  command → "Press Enter to finish" when interactive. Failures: red box,
  "Press Enter to close", exit 1. Non-interactive runs (no console) fail
  fast instead of hanging on `Read-Host`.
- `scopewise-scan.*`: prefer `.venv`, require `.env`, estimate → y/N →
  scan `--stop-after s9` → zip `findings.json` + `*.sarif` + newest
  `run_manifest_*.json` at the zip root. Every run tees output plus
  timestamped phase markers into `logs/scan-<repo>-<timestamp>.log`
  (UTF-8, local only). On failure prints the transcript path, VVAH's
  `<repo>/security-scan/*_errors.jsonl` and the `run_manifest` stage
  timeline, and the usual causes.
- Windows gotchas encoded in the scripts: `PYTHONUTF8=1` (VVAH prints
  glyphs; cp1252 consoles crash); native commands run through `cmd /c …
  2>&1` because `$ErrorActionPreference='Stop'` turns a native stderr
  line into a terminating error in PowerShell 5.1; `Tee-Object` writes
  UTF-16 in 5.1, so lines are appended with `-Encoding UTF8`; time format
  `HH\:mm\:ss` (locale separator); `Set-Location` does not change the cwd
  a `cmd` child inherits, so launchers `cd /d` themselves.

### XLSX (`report_xlsx.py`)
- Summary: section bands, severity chips, centred numbers with
  thousands separators, duration in minutes, scanner version.
- Findings Register: plain-language headings; Severity / Verdict / Status
  as tinted chips (same hex as the web UI); Status dropdown (Open, In
  progress, Fixed, Accepted risk, False positive) with conditional-format
  colours; prose columns as `CellRichText` bullets with code (Consolas
  blue), attack (rose bold) and fix (green bold) runs; row heights
  estimated from text; freeze at D2.
- Exploit Chains: banner explaining what a chain is, steps resolved to
  `1. #3  <title>` lines, "Fix this first" column, bulleted narrative.
- Determinism: `wb.properties.created/modified` pinned and the zip is
  rewritten with fixed entry timestamps (`_normalize_zip`).

### PPTX (`report_pptx.py`)
Cover → Executive Summary (5 tiles + top-3 findings) → Risk Profile
(severity chart in severity colours, type chart, top-5 files strip) →
Findings at a Glance (top 10, tinted cells) → divider 01 → Critical
Findings spotlights, 2 per slide (What/Why/Fix highlighted bullets, file,
CVSS, CWE, verifier tick) → divider 02 → Exploit Chains as pentagon →
chevron step flows with "Break it: fix #N first" → divider 03 →
Remediation Plan (table by severity then chains broken; side cards:
greedy set cover "fewest fixes that break every chain", highs batched by
file, verify) → Scan Coverage & Confidence (4 tiles, LOC-by-language
chart, verifier note, limits) → Next Steps (4 cards) → closing. Rendered
slides of the NodeGoat deck: `screenshots/codereview_deck_2026_09_12/`.
Visual QA method that worked: PowerPoint COM `Presentation.Export(dir,
"PNG")` from PowerShell, then view the PNGs (no LibreOffice on this box).

## Verification done today
- Kit: unzipped the prod-built zip and ran `setup.cmd` end to end three
  times (fresh, re-run with existing `.env`, from the user's actual
  blocked Downloads copy); scan launcher usage + estimate + expected 401
  with a dummy key; transcript contained the 401 lines and all markers.
- XLSX/PPTX: built from the real NodeGoat fixture; structure checked with
  openpyxl / python-pptx; deck rendered to PNG and reviewed; layout fixes
  applied (table overflow, spotlight overlap, remediation column width,
  word-boundary trimming); report tests 4/4 × 6 runs.
- Every deploy: `docker exec scopewise-api python -c "import …"` smoke on
  the 3.11 image; public routes 200/401 as expected.

## Late-session additions (same day, after the docs commit `63810e2`)

| Commit | What |
|---|---|
| `a319895` | Scan kit size guard: after `estimate`, refuse > 20,000 code files / 500 MB, warn > 2,000 files or when `node_modules`/`.venv`/`dist`/`build`/`.next` exist; README timing table. Triggered by the user scanning `E:\code\DhanRadar` working folder (345k files, 3.4 GB) — 40 min stuck in S0. Rule: scan a fresh `git clone`. |
| `cf39b7d` | **Demo reviews**: `CODEREVIEW_DEMO_REVIEW_IDS` env (compose → VPS `.env`) makes listed code reviews readable/exportable by every signed-in user across orgs; `demo`/`editable` flags; UI chip + hidden edit controls; cross-org test. Prod: NodeGoat golden review `49e45724-ff5d-4e53-937b-aba306d3cfd3`. |
| `ee19ff9` | **Demo assessments** for MITRE: `MITRE_DEMO_ASSESSMENT_IDS`; `_read_org()` resolves the owner org for read endpoints only (get, use-cases, explain, report, xlsx/pptx/navigator); writes stay owner-only; UI chip, `canEdit` gated. Prod: "Acme MITRE Assessment" `0fe2d3e2-7d59-4385-abbe-7055c49130fa`. Both demos are what talk2maq@gmail.com (or any Google login) sees. |
| `e83f435` | Web: empty `NEXT_PUBLIC_API_URL` = same-origin API, for the scopesense.in dual-run. |
| (other session) `4ddfd9f`, `fab4da8`, `644ab3b` | Blog/SEO commits from a parallel session — not this work. |

Domain: `scopesense.in` registered; Cloudflare zone configured from the VPS
(DNS, Full strict, HTTPS, TLS 1.2, Authenticated Origin Pulls); blocked on
the registrar's 24 h nameserver hold and the Origin cert (only issuable once
the zone is active). Full runbook: `docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md`;
kickoff for the follow-up: `docs/phases/prompts/SCOPESENSE_CUTOVER_PROMPT.md`.
Dual-run for ~30 days; both hosts live; product name stays ScopeWise.

Guidance given on scan expectations: VVAH has a 10–15 min floor; NodeGoat
(63 files) took 102 min; a 2–3 min scan is not possible — for demos upload
the golden zip; smallest real scan `we45/Vulnerable-Flask-App` (~20 min).

## Open items / ideas (none blocking)
- PPTX org branding (`report_display_name`) still `resolve_branding(None)`.
- A `pricing:` table in the kit config would make VVAH's manifest report
  `cost_usd` itself (today the README carries a list-price estimate).
- Highlight word lists (`RISK_RE`, `FIX_RE`) are hand-curated; extend on
  request — three copies to keep in sync (drawer, xlsx, pptx imports xlsx's).
- `docs/sample/CodeReview_Sample/real/nodegoat/` review on prod is the
  demo; a second real repo (Python) would broaden the golden coverage.

## Agent utilization
- Opus/Fable (main): all of today's follow-ups were written directly —
  each was a single-file or two-file change with the files hot in context
  (drawer, kit scripts, both report builders), plus visual QA via
  PowerPoint export and all deploys.
- Sonnet: n/a today (morning's module build used 3 UI + 2 backend builders
  and one adversarial zip review — see the 2026-09-11 scan-kit handoff).
- Haiku: n/a.
- codex:rescue: n/a — companion broken per memory; no new trust-boundary
  code today (report builders only read stored JSONB; kit scripts run on
  the consultant's machine).
