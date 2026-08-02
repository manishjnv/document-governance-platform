# Session handoff — MITRE Phase 14i review + fix + deploy (2026-08-03)

**Headline:** reviewed the Phase 14i implementation delivered by a separate
session (telemetry field guidance per gap), found and fixed **one real
regression** before it shipped, then committed and deployed. Prod at
**`75b58bf`**. Suite **809 passed / 7 skipped**; `tsc --noEmit` clean; no
migration; no coverage/scoring change.

## What Phase 14i delivers

Answers the customer question *"you say this technique isn't covered and my
Windows Event Logs could see it — but what does my query actually need, and
is my connector even sending it?"*

- **`app/mitre/data/telemetry_fields.json`** (new, curated): the top **35 of
  113** ATT&CK data-source components by technique-reference frequency —
  **88%** of all technique→component references. Each entry has `fields`
  (plain-English query parameters), `where` (vendor-neutral usual sources),
  and `gotcha` (the single most common reason an *already-onboarded* source
  still can't support the detection). Hand-written, never runtime-LLM.
- **`plain_language.telemetry_requirements()` / `telemetry_lines()`**: pure,
  curated-entry-or-bare-component-name, no invented guidance.
- **Three read-only surfaces**: `explain` endpoint `good.telemetry` → the
  drawer's existing "What would good look like?" block; XLSX **"Log fields
  needed"** column on Gaps & Recommendations; PDF/HTML gap register.

The curated content is the real value and it is good — e.g. *"Windows Event
ID 4688 does not include the command line unless 'Include command line in
process creation events' is turned on"*, *"encoded PowerShell only decodes
in Script Block Logging (4104)"*, *"most onboarded 'network' sources forward
flow metadata, not payload content"*.

## The regression I caught (fixed before commit)

The PDF gap register printed the **full guidance on every gap**. But 487
techniques share "Process Creation", so on the real 842-gap customer sample
(`docs/sample/MITRE_Sample/UploadSample/`) this repeated **1,231,546
characters ≈ 680 extra pages** — 752 of 842 gaps carried an average of 1,462
chars each, max 4,868.

**Fix:** each gap now *names* its telemetry components; the guidance prints
**once** in a "Log fields reference" table after the register — **35 rows,
19 KB**, the same information at ~1/65th the paper. The table is emitted
inside the register section (not the appendices) so the per-tab `gaps` PDF
scope keeps it, while the `executive` cut still drops it. Both verified.

Note for future work here: `report.py` was refactored into Jinja templates
by the Phase 14h branding session — new report fragments go in
`app/mitre/templates/*.html` plus the context dict, **not** the old
f-string. `_JINJA_ENV` runs `autoescape=False` because fragments are
pre-escaped with `_esc()`; keep escaping at the point of construction.

## Verification performed (not taken on trust)

- All 35 curated keys are real component names in `attack.json`; every entry
  has non-empty `fields`/`where`/`gotcha`.
- **Honesty boundary scan** across every curated string for phrasing that
  would claim field-level knowledge we don't have ("your source is missing",
  "not sending", "lacks"): **zero hits**. Wording is consistently "your query
  needs X … verify the connector" — correct, since the product never ingests
  raw logs.
- XLSX column inserted at position 7, so the existing colored fills and
  centering (columns 4–5) still land on Priority/State.
- Full suite 809/7 reproduced locally (solo on `edgp_test`, single-runner
  rule respected); `tsc --noEmit` clean.
- Post-deploy: curated guidance for `T1059.001` returned from the running
  prod container; `/mitre` 200, API 401 unauth, all `scopewise-*` healthy.

## Housekeeping

- Reverted the two sample `.xlsx` files whose only diff was a one-byte
  regeneration timestamp (commit noise).
- `docs/sample/MITRE_Sample/template/IC-Simple-Cyber-Security-Risk-Assessment-11680_PDF.pdf`
  is still **untracked** — not mine to commit; decide whether it belongs.
- `.gitignore` still carries an **uncommitted `*docs/` line** that ignores
  the whole docs tree; every docs commit needs `git add -f` because of it.
  If it is ever committed, new docs will silently stop being added. Worth
  deleting or narrowing.
- CLAUDE.md baseline updated 803 → **809 passed / 7 skipped**.

## Next action

None pending. Phase 14 (14a–14i) is complete and deployed. Optional backlog
unchanged: Splunk/Elastic connectors, connections CRUD UI, and the deferred
UX list at the bottom of `MITRE_UX_CLARITY_PLAN.md`. Tests pass: Y.
Open questions: none.

## Agent utilization

- Opus (main): review of the delivered diff, regression measurement, the
  reference-table fix, docs correction, deploy and prod verification
- Sonnet: Phase 14i implementation (separate session) — reworked: **Y**
  (PDF per-gap repetition replaced with a print-once reference table)
- Haiku: n/a — no bulk sweeps
- codex:rescue: n/a — read-only presentation surfaces over curated static
  content; no security/auth/classifier surface touched
