# Session handoff 2026-09-23: SARIF import, external user access, dual-run fallout

**Headline:** Agentic SAST `.sarif` uploads now produce the full Code Review register/deck (was: title/CVSS only). Operator guide for scan-run folders: `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` §5. Deployed `24dbfaa`; both hosts 200; in-container Python 3.11 smoke imported the 121-finding Keycloak SARIF and built XLSX + PPTX.

**Commits:** `1033775` SARIF narrative/verdict/snippet import (RCA #34) · `1fec10c` `.gitattributes` LF pin + kit test (RCA #33, other session's work) · `8f92be2` dual-run docs, README rewrite, risk plan (other session's work; a client name scrubbed first) · `24dbfaa` baseline · this commit: gitignore `sample/` + `docs/sample/`, docs, RCA #35, handoff.

**Ops (no code):** talk2maq@gmail.com's own org `run_allowance` 0 → 5 (SQL + audit row; owner chose allowance over pro). scopewise.assessiq.in serves the app; office "redirect to scopesense.in" is a browser-cached 301 (RCA #35, clear site data).

**Gates:** full backend suite **998 → 999 passed / 7 skipped** (after the SARIF import, then after the kit upgrade; ~8 min solo on edgp_test). Code review + kit tests 42/42; fresh-DB migration apply + DB tests verified for CI. Secrets/TODO/CRLF scans clean.

**Repo hygiene:** all `*.pptx/*.ppt/*.xlsx/*.xls` gitignored (tracked templates/fixtures stay); `scripts/build_mitre_value_slide.py` kept local and ignored (owner call). `docs/sample/MITRE_Sample/file.xlsx` names the client — ignored, never commit. Re-upload pre-`1033775` SARIF reviews to get the full shape.

**Scan kit (later same day):** kit moved VVAH 1.3.0 → 1.4.0 via new `scripts/update_vvah_kit.py`; weekly `.github/workflows/vvah-kit-update.yml` opens a PR (repo setting "Actions may create PRs" turned on; issue fallback kept) when Visa ships a release; runbook `CODE_REVIEW_MODULE_REFERENCE.md` §8. Upload page gains an "About the scanner" panel (sweep OK at 1440/390). Deferred (owner has no AI credit): a real 1.4 NodeGoat scan to refresh the golden fixture; do not start it unasked.

**CI:** `ci-cd.yml` replaced — the old template targeted main/develop (never ran), pushed GHCR images and deployed to a nonexistent k8s cluster; now push/PR to master runs the full backend suite (Python 3.11, fresh Postgres from migrations/*.sql, Redis) + web tsc, deploys nothing.

**Next:** R1 in `docs/planning/RISK_REMEDIATION_PLAN.md`; optionally read per-finding `triage.json`/`diff.patch` so fix-mode runs show what was fixed.

**Agent utilization**
- Opus: main session — scan-zip analysis, importer change + fence/verdict fix found on real files, commit split of another session's tree, deploy, docs.
- Sonnet: 1 adversarial review of the SARIF ingest diff (codex fallback), verdict accept.
- Haiku: n/a — lookups were single-file or one DB query.
- codex:rescue: n/a — companion broken since 2026-07-23 (memory); Sonnet takeover, verdict=accept.
- Routing: sonnet · adversarial SARIF ingest review · reworked: N
