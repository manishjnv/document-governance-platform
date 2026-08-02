# Session handoff — 2026-08-02 — MITRE module reference + closeout docs

**Headline:** the MITRE module now has its permanent end-to-end reference:
`docs/planning/MITRE_MODULE_REFERENCE.md` — what the module is, every
file's role, pipeline semantics, JSONB shapes, the tagging ladder,
deterministic-engine rules, full API table, security posture with the
adversarial-review history, ops runbook, test map, and the Phase 0–7
build history with commits. `CLAUDE.md` now directs any session to read
it before touching either mitre folder; session memory points at it too.

**Commits (this session):**
- `9e1998f` — the reference doc + CLAUDE.md pointer + progress-index
  correction (see "Corrections" below).
- `51b1620` — Phase 8 (Navigator export) entries folded into the
  reference (file map, frontend, test map, §15 pending-commit row, §16
  status) with wording that stays truthful until its build session lands
  the code and stamps the hash.

**Tests pass:** not re-certified by this session — full-suite runs were
repeatedly blocked by cross-session `edgp_test` contention (see
Incidents). Certified chain of record: **687/7 at the Phase 7 gate**
(`b183f75`); the active Phase 8+9 session has since measured **702/7**
with its uncommitted work in-tree (per its CLAUDE.md baseline update).
`tsc --noEmit` re-verified clean here before the Phase 8/9 frontend work
began.

**Next action:** none for the docs. The active build session owns:
committing Phases 8+9, filling its handoffs' `[SUITE_RESULT]`, and
stamping the §15 history rows in the reference doc (the doc says exactly
where).

**Open questions:** none.

---

## Corrections made (stale-docs cleanup)

- **Prod state was better than documented:** the progress doc said
  "Phase 7 deploy pending"; SSH verification showed `/opt/scopewise` at
  `b183f75` with migrations 029–032 all applied to `scopewise_prod`
  (`logic` column + `keyword_tagged` CHECK confirmed). Corrected in the
  progress index and stated with the verification date in the reference.
- **Memory consolidated:** the project MITRE memory now records
  Phases 0–7 complete/deployed, the reference doc as entry point, and
  keeps the OpenRouter key-identity clarification (the app's SOW-audit
  key was never cap-blocked; only the personal tooling key was).

## Incidents

- **Shared `edgp_test` contention (twice):** concurrent pytest runs from
  two sessions deadlock on the TRUNCATE-based fixtures — symptom is
  spurious failures/ERRORs in unrelated files plus stacked
  `TRUNCATE organizations CASCADE` sessions in `pg_stat_activity`; killed
  clients leave lock-holding orphan backends that need
  `pg_terminate_backend`. Documented in the reference's testing section
  and memorialized as the single-runner rule (memory + this file).
- **Doc/commit races between parallel sessions** remain the top
  coordination hazard this week: this session found (and corrected, or
  deliberately left to the owner) stale notes written mid-flight by
  sibling sessions three separate times. Rule of thumb applied: verify
  against ground truth (git log, SSH, DB) before repeating any status
  claim, and never stage another session's in-flight files.

## Agent utilization

- Opus/Fable (main): everything — state reconnaissance across 8 phases of
  git/docs/memory, SSH prod verification, the reference doc itself, and
  the incident diagnosis (writing the module's book required the
  full-context read no cheap model could shortcut).
- Sonnet: n/a — no delegable mechanical work; docs judgment throughout.
- Haiku: n/a — no bulk sweeps.
- codex:rescue: n/a — companion still broken (memory 2026-07-23); no
  security-adjacent code changed this session (docs only).
