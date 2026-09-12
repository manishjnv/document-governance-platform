# Session handoff — 2026-09-11 (evening): Code Security Review UI pass + scan kit + golden scan

> Superseded for current state by `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md` (feature doc, kept current). This file is a point-in-time session log.

**Headline:** the Code Security Review module went from "built, uncommitted"
to shipped in ONE commit: professional UI pass on all three pages
(`CODE_REVIEW_UI_PLAN.md` §2–6), consultant scan kit hosted in ScopeWise
(VVAH v1.3.0 wheel vendored, `GET /api/v1/codereview/kit.zip`, zip upload
with guards), and a real VVAH scan of `OWASP/NodeGoat` as the golden
fixture. Suite **973 passed / 7 skipped** (baseline was 962/7); `tsc --noEmit` clean. Commit
the single commit "Code Security Review module: VVAH findings import, XLSX/PPTX deliverables, consultant scan kit, real golden scan" (`git log -1 -- apps/api/app/codereview/kit`), pushed and deployed to the VPS on 2026-09-12 (migration 039
applied to `scopewise_prod`, in-container import smoke on the 3.11 image,
golden zip uploaded at `/codereview/new`).

Timeline: the 2026-09-11 evening session built everything and stopped at
the user's request while the real NodeGoat scan was at S3; the scratchpad
(clone, venv, partial checkpoints) did not survive the session, so the
2026-09-12 session re-ran the scan from the vendored wheel (same estimate),
landed the fixture, ran the suite and shipped.

## What changed

| Area | Change |
|---|---|
| UI (`apps/web/app/codereview/`) | `lib.ts` gains `SEVERITY_META.{dot,text}`, `VERDICT_META`, `SOURCE_FORMAT_LABEL`, `filterFindings`, `deriveHeadline`; list page (severity bar, kebab + dialogs, sort, skeletons); upload page (two-column, "Get the scanner" with live download, single `.json/.sarif/.zip` dropzone); results page split into `[reviewId]/components/{ReviewBand,SeverityStrip,FindingsTable,FindingDrawer,ChainsTab,ScanDetailsTab}.tsx` |
| Kit (`apps/api/app/codereview/kit/`) | `vendor/` (wheel + LICENSE/NOTICE/THIRD_PARTY_LICENSES), `KIT_VERSION.json`, `config.yaml`, `scopewise-scan.{ps1,sh}`, `README.md`; `kit.py` builds the zip in memory |
| API | `GET /kit.zip` (any user); `POST /reviews` accepts the kit zip via `ingest.unpack_scan_zip` |
| Golden | `docs/sample/CodeReview_Sample/real/nodegoat/` (findings.json, SARIF, manifest, kit-style zip, README) + `test_real_nodegoat_golden`; ingest fixes for real schema (`vuln_class_label` null → class id; tool version from manifest) |
| Tests | +`test_codereview_kit.py` (3), +7 in `test_codereview_api.py`, +1 golden in `test_codereview_ingest.py` |
| Docs | reference §8–9 → built, UI plan → built, `IMPLEMENTATION_PROGRESS.md`, `CLAUDE.md` baseline |

## Phase 3 critique findings (fixed before gates)

1. Upload page exported a non-page constant from `page.tsx` (Next build
   error) and used Radix `Tooltip` without a `TooltipProvider` → removed
   export, wrapped the page.
2. Drawer used `useSearchParams` (needs a Suspense boundary at build) →
   `window.location.search` in the mount effect.
3. Zip unpacker symlink check had an operator-precedence bug
   (`a & b == c` → always tested bit 0) → `stat.S_ISLNK(...)`. Corrupt /
   encrypted / unsupported members raised `BadZipFile`/`RuntimeError` → 500;
   now mapped to `IngestError` → 422 (self-check script proved both).
4. Duplicate date on list cards, uppercase format chip, overflowing file
   path in the drawer meta grid, wrapping verdict chip — polished.
5. VVAH partial profile crashed with `AttributeError: inject` (no built-in
   default for that block) → `inject:` block added to `config.yaml`. VVAH's
   CLI also crashes on cp1252 consoles → scripts set `PYTHONUTF8=1`.

## Golden scan facts

- Target: `OWASP/NodeGoat` (Apache-2.0), commit `c5cb68a7084e4ae7dcc60e6a98768720a81841e8`,
  shallow clone at `<scratchpad>/target-nodegoat`. Scratchpad =
  `C:\Users\manis\AppData\Local\Temp\claude\e--code-DocumentGovernancePlatform\7e0972f5-e7f2-4db8-bfdc-849d0aeffea7\scratchpad` (persists on disk after the session).
- `vvaharness estimate`: 63 code files, 1,293,982 bytes, ~323k raw input
  tokens (VVAH multiplies across stages); projected about $3–4 on
  deepseek-v4-pro/flash — under the $5 gate, so the scan was started.
- Run dir `<scratchpad>/kitrun/` holds `config.yaml` (copy of the kit
  config) and `.env` with the project SOW-audit OpenRouter key (never
  commit; delete when done). Venv: `<scratchpad>/venv311/` (Python 3.11.9,
  vvaharness 1.3.0 installed). Log: `<scratchpad>/scan.log`.
- Status at stop: S0 callgraph, S1 preprocess, S2 threat model done; S3
  decompose running. First attempt died on the missing `inject:` block
  (fixed in the kit config). If the process was killed with the session,
  VVAH keeps per-stage checkpoints under `~/.vvaharness/state`, so resume
  with `--resume` (repo unchanged, so it is safe):

      cd <scratchpad>/kitrun
      PYTHONUTF8=1 <scratchpad>/venv311/Scripts/vvaharness scan --repo <scratchpad>/target-nodegoat --stop-after s9 --config config.yaml --resume

  Outputs land in `<scratchpad>/target-nodegoat/security-scan/findings.json`
  + `*.sarif`, and `run_manifest_*.json` in `kitrun/`.
- Then: copy the three files to `docs/sample/CodeReview_Sample/real/nodegoat/`
  with a README (repo, sha, licence, VVAH 1.3.0, models, tokens, cost from
  the manifest), secret-scan them, add `test_real_nodegoat_golden` to
  `apps/api/tests/test_codereview_ingest.py` (total count, severity
  histogram, every finding has file+title, chain steps within 1..N). If the
  real schema differs from the synthetic assumptions, fix `ingest.py` and
  regenerate the synthetic sample — the real file wins.

## Next action

Shipped. Follow-ups, none blocking: (1) browser click-through of the zip
upload on prod with the golden zip (done once at deploy — see headline);
(2) decide whether the PPTX deck should use org branding
(`report_display_name`) — still `resolve_branding(None)`; (3) consider a
`pricing:` table in the kit config so VVAH's manifest reports `cost_usd`
itself instead of the README's list-price estimate; (4) delete the scratch
`kitrun/.env` copies of the project key (done for this session's
scratchpad at exit).

## Agent utilization

- Opus/Fable (main): Phase 0, `lib.ts` contract, 3 UI critiques + inline
  fixes, zip-path line review + 2 defect fixes, kit endpoint, VVAH research
  (models.md / configuration.md / profiles), estimate + scan run, gates,
  docs, commit.
- Sonnet: list page · reworked: N; upload page · reworked: Y (invalid page
  export, missing TooltipProvider); results page · reworked: Y
  (useSearchParams, chip tooltips); kit files + endpoint module · reworked:
  Y (missing `inject` block, PYTHONUTF8); zip upload + tests · reworked: Y
  (symlink precedence bug, uncaught zipfile errors); adversarial zip review
  · verdict=revise → fixed (byte-capped streamed read, wider malformed-zip catch); re-verified with a lying-header zip → 422.
- Haiku: n/a — no multi-file fact sweeps were needed.
- codex:rescue: n/a — companion broken per memory; Sonnet takeover for the
  zip trust-boundary adversarial pass.
