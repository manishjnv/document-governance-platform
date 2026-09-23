# Session handoff 2026-09-23: SARIF import, external user access, dual-run fallout

**Headline:** Agentic SAST `.sarif` uploads now produce the full Code Review register/deck (was: title/CVSS only). Operator guide for scan-run folders: `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` §5. Deployed `24dbfaa`; both hosts 200; in-container Python 3.11 smoke imported the 121-finding Keycloak SARIF and built XLSX + PPTX.

**Commits:** `1033775` SARIF narrative/verdict/snippet import (RCA #34) · `1fec10c` `.gitattributes` LF pin + kit test (RCA #33, other session's work) · `8f92be2` dual-run docs, README rewrite, risk plan (other session's work; a client name scrubbed first) · `24dbfaa` baseline · this commit: gitignore `sample/` + `docs/sample/`, docs, RCA #35, handoff.

**Ops (no code):** talk2maq@gmail.com's own org `run_allowance` 0 → 5 (SQL + audit row; owner chose allowance over pro). scopewise.assessiq.in serves the app; office "redirect to scopesense.in" is a browser-cached 301 (RCA #35, clear site data).

**Gates:** full backend suite **998 passed / 7 skipped** (8 min 16 s, solo on edgp_test). Code review tests 37/37. Secrets/TODO/CRLF scans clean.

**Left for the owner:** commit or discard `docs/planning/MITRE_AUTOMATION_VALUE_SLIDE_*.{pptx,xlsx}` + `scripts/build_mitre_value_slide.py` (internal Wipro pitch, public repo). `docs/sample/MITRE_Sample/file.xlsx` names the client — now ignored, never commit. Re-upload pre-`1033775` SARIF reviews to get the full shape.

**Next:** R1 in `docs/planning/RISK_REMEDIATION_PLAN.md`; optionally read per-finding `triage.json`/`diff.patch` so fix-mode runs show what was fixed.

**Agent utilization**
- Opus: main session — scan-zip analysis, importer change + fence/verdict fix found on real files, commit split of another session's tree, deploy, docs.
- Sonnet: 1 adversarial review of the SARIF ingest diff (codex fallback), verdict accept.
- Haiku: n/a — lookups were single-file or one DB query.
- codex:rescue: n/a — companion broken since 2026-07-23 (memory); Sonnet takeover, verdict=accept.
- Routing: sonnet · adversarial SARIF ingest review · reworked: N
