# Session handoff 2026-09-20: rename to ScopeSense, search signals to scopesense.in

**Headline:** Product renamed ScopeWise -> ScopeSense in all user-facing text; SEO canonical, sitemap and robots now name scopesense.in. Both hosts still serve, no host redirect (dual-run to ~2026-10-13). The one place the facts live: `docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md` section "Rename to ScopeSense".

**Gates:** `npx tsc --noEmit` clean. Name-asserting backend tests without a DB: 8 passed. Full backend suite run later the same day once Docker Desktop was started: **996 passed, 7 skipped, 0 failed** (baseline was 985 / 7; `CLAUDE.md` Testing line updated).

**Not renamed on purpose:** infrastructure names, the browser storage key, `scopewiseNote`, scan-kit file names, the Sentinel workbook id (see `CLAUDE.md`).

**Next:** at the end of the dual-run add the host 301 and use the search consoles' change-of-address tools; decide on the scan-kit and marketplace listing names.

**Agent utilisation:** Opus/Fable main only (session started in the Foxfiber project). Sonnet n/a: the rename was one scripted, reviewed replace, not N hand edits. Haiku n/a. codex:rescue n/a: no auth, CORS, env or classifier code touched.
