# Documentation

Central index. User guides, API docs, architecture diagrams, and deployment runbooks.

## Structure

- `planning/` — scope, master tasks, DB schema, AI agent specs, launch criteria, roadmap, project plan
- `phases/prompts/` — the instructions/prompt given for each phase (PHASE_N_PROMPT.md)
- `phases/summaries/` — what was actually implemented per phase/wave (PHASE_N_SUMMARY.md)
- `IMPLEMENTATION_PROGRESS.md` — master feature-by-feature progress tracker, update as features ship
- `CODING_STANDARDS.md` — coding conventions
- `API_AUTH.md`, `DEVELOPMENT_SETUP.md`, `PRODUCTION_DEPLOYMENT.md`, `QUICK_START.md` — operational guides

## Convention

Each phase gets one prompt file and one summary file. When a feature ships, add an entry to `IMPLEMENTATION_PROGRESS.md` (feature name, phase, files touched, status) instead of creating a new root-level doc.
