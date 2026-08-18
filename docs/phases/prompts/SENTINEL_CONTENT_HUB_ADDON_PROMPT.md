# Kickoff: Sentinel Content Hub add-on (Phase A — workbook v0)

Read `docs/planning/SENTINEL_CONTENT_HUB_ADDON_PLAN.md` (the plan) and
`docs/planning/SENTINEL_CONTENT_HUB_EVALUATION.md` (the market research
behind it), then start **Phase A**:

1. Create `marketplace/sentinel/` with `scripts/generate_workbook_data.py`
   exporting ATT&CK v19.1 technique metadata, the log-source mapping
   (`apps/api/app/mitre/ranking.py::_LOG_SOURCE_RULES`), and prevalence
   weights into static JSON grids.
2. Build the "honest coverage" workbook JSON (5 features per the plan's
   Tier-1 table), testable by pasting into Sentinel → Workbooks → Advanced
   Editor.

Prereq to confirm with the user before step 2's live testing: a dev
Sentinel workspace exists (or create one — near-zero cost, 31-day trial).
Partner Center enrollment (Phase C.1) is user-owned and should already be
in flight — ask for status, don't block on it.
