# Session handoff 2026-09-23/24: scanner-run import, scan kit auto-update, CI, external access

**Headline:** Code Security Review now takes a whole Agentic SAST / VVAH 1.4 run folder zipped and reports each fix checked against the real test results (Keycloak fix #22 "Fixed" by the scanner but it broke `SecureRedirectUrisEnforcerExecutorTest`). Single source of truth: `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` §0 changelog, §3 data model, §5 ingest + operator guide, §6 reports, §7 UI, §8 kit auto-update. Live app at `c1286be` (later commits are docs only); CI green (1011 passed).

**Code Review:** SARIF narrative/verdict/snippet import (`1033775`, RCA #34) · run-zip extras: fix status vs JUnit/Maven, patch, top-25 scanner evidence, coverage + threat model (`8f47373`, `4e44967`, `1e9a365`, RCA #36) · deck keeps 12 slides: fix strip on Executive Summary, Fix column, "Scanner fix" on spotlights/remediation, Scan run evidence panel, one-line facts (`2cc8179`, RCA #38) · review page full width, fix cards + Fix chips, file name first, CWE id links, phone overflow fixes (RCA #39) · global error boundary reloads once on stale-build chunk errors (`5030a27`, RCA #37).

**Scan kit:** VVAH 1.3.0 → 1.4.0 (`89b4d5b`); `scripts/update_vvah_kit.py` + weekly `.github/workflows/vvah-kit-update.yml` open a PR on a new Visa release (repo setting "Actions may create PRs" turned on). "About the scanner" panel on the upload page, checked against VVAH 1.4 docs (Claude-native; OpenRouter is only the kit preset).

**CI:** `ci-cd.yml` rewritten (old template never ran and targeted k8s/GHCR): full backend suite on Python 3.11 with a fresh DB from `migrations/*.sql` + web tsc, deploys nothing. Test-only deps in `apps/api/requirements-dev.txt`; pytest 9.0.3 / pytest-asyncio 1.3.0 pins.

**Other session's work committed:** `.gitattributes` LF pin (RCA #33), dual-run + risk-plan docs (client name scrubbed). Browser-cached 301 on the old host explained (RCA #35).

**Ops (no code):** talk2maq@gmail.com: own org, `run_allowance` 5 for MITRE; "Keycloak Fix v1" copied into their org as review `c2e7f3be-…` (snapshot, audit row `shared_from_review`; re-copy if the original is re-uploaded). Verified as that user: list, page, drawer, XLSX Fixes sheet, PPTX fix slides.

**Repo hygiene:** `sample/`, `docs/sample/`, all `*.pptx/*.xlsx` gitignored (tracked templates/fixtures kept); `scripts/build_mitre_value_slide.py` local only. Upload files: `sample/upload_ready/keycloak_{fix_mode,report_only}_run.zip`.

**Gates:** backend 1006 passed / 7 skipped locally, 1011 / 2 in CI; code review + kit tests green; every changed slide rendered via PowerPoint COM; live page checked at 1440/1024/390 with headless Playwright (short-lived token).

**Deferred / next:** real VVAH 1.4 NodeGoat scan to refresh the golden fixture (owner has no AI credit — do not start unasked); R1 in `docs/planning/RISK_REMEDIATION_PLAN.md`; end of dual-run ~2026-10-23 (cut-over doc §4).

**Agent utilization**
- Opus: orchestration, specs/contract, diff review, slide and page visual QA, prod debugging, deploys, docs.
- Sonnet: 3 parallel builders (run-zip ingest, exporters, UI) + 2 adversarial reviews (SARIF ingest: accept; run-zip ingest: revise → CPU DoS fixed).
- Haiku: n/a — lookups were single-file or one query.
- codex:rescue: n/a — companion broken since 2026-07-23; Sonnet takeover both times.
- Routing: sonnet · run-zip ingest builder · reworked: Y (DoS found in review) | sonnet · exporters · reworked: Y (slide overflow, label) | sonnet · UI · reworked: N
