# Kickoff prompt — finish the complete app design canvas

Copy everything below the line into a fresh Claude Code session at
`E:\code\DocumentGovernancePlatform`.

---

Finish the ScopeWise complete-app design canvas. Read first, in order:
`docs/phases/summaries/SESSION_HANDOFF_2026_09_12_DESIGN_CANVAS.md` (state, toolchain,
gotchas), `docs/design/complete-app-2026-09-12/README.md`, `CONTRACT.md`, `dc.py`, `logic.js`,
`screens/dashboard.py` (model module), and the memory note `design-canvas-toolchain`. Design
only: change nothing under `apps/web`.

## Setup (once)

1. `git status` must be clean apart from anything you create. If `screens/*.py` files show as
   modified, that is a builder that was still writing when the last session ended: keep the
   on-disk version, commit it as WIP by name before editing.
2. Rebuild the standalone runtime folder if the scratchpad is gone: create
   `extract_runtime.py` per the memory note (slice the `reactUmd`, `reactDomUmd`, `supportJs`
   template literals out of the design skill's `payload.template.html` and write them as
   `reactUmd.js`, `reactDomUmd.js`, `supportJs.js`), set `DC_RUNTIME` to that folder, and
   confirm `python harness.py --screens Main --out <scratch>` passes.

## Work, one screen at a time, commit after each

For each of `Results`, `MitreDetail`, `CodeReviewDetail`:
- `python gen.py --only <Stem> && python check_labels.py && python harness.py --screens <Stem>
  --out <scratch>` and `--phone`; Read the PNGs.
- Fix what the handoff lists (Results: split pane width constraint + filter handlers;
  MitreDetail: wrap the matrix in an `overflow-x:auto` container, fix the cell→drawer and
  "tagged by you" clicks, add the two missing tooltip strings; CodeReviewDetail: find and fix
  the `{{` leak, then the graph node, row→drawer and Next clicks).
- Do not rewrite these modules; they are large and mostly right. Keep every inventory item.
- Commit: `git add docs/design/complete-app-2026-09-12/screens/<module>.py
  docs/design/complete-app-2026-09-12/labels/<Stem>.json docs/design/complete-app-2026-09-12/
  <Stem>.dc.html docs/design/complete-app-2026-09-12/<Stem>Phone.dc.html`.

## Then

1. Full sweep: `python gen.py && python check_labels.py` then `harness.py` over all 15 stems at
   both sizes; fix anything that regressed.
2. Reseed with all 30 artboards and `canvas.json` (remove the "Work in progress" note in
   gen.py), `--check`, republish to the SAME artifact URL
   https://claude.ai/code/artifact/9f120be7-d49e-4651-8ea3-a103269b5e24 with
   `contract "0.1.31"` and the same favicon (🧭); pass `url` if this session did not publish it.
3. Update `README.md` (status table complete), `IMPLEMENTATION_PROGRESS.md` (replace the "in
   progress" wording), and write the handoff with the 4-line agent-utilization footer.
4. Ask the owner for a review pass on the live canvas; apply feedback as targeted re-seeds.

## Constraints

- Sonnet builders only if needed, ≤4 concurrent, and tell them to write large modules in two
  Write calls (the 64k output cap killed one). The account's session limit resets on a 5-hour
  window; if agents die with a 429, wait rather than relaunching immediately.
- Never `git add docs/` wholesale; stage by name. Never edit `apps/web`.
