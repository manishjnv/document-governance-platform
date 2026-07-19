# CLAUDE.md — ScopeWise (Document Governance Platform)

Project-specific overlay. This wins over the global playbook where the two
conflict; otherwise the global playbook's orchestration rules still apply.

## What this is

AI-powered SOW/RFP document review platform. Product name is **ScopeWise**
(rebranded from "EDGP" — if you see "EDGP" in old comments/docs, it's the
same product, historical name only, do not reintroduce it in new
user-facing text). Backend: FastAPI (`apps/api`). Frontend: Next.js
(`apps/web`). 6 AI review agents (Scope/Delivery/Commercial/Security/PMO/
Legal) + a rule engine, per `docs/planning/4_AI_AGENT_SPECS.md`.

- Public repo: github.com/manishjnv/document-governance-platform
- Live deployment: https://scopewise.assessiq.in
- LLM provider: OpenRouter (see `apps/api/app/ai/agent.py` — never
  Anthropic/OpenAI/Google directly for the review pipeline itself, that's
  a deliberate cost choice).

## Where things go (read this before creating any new file)

- `docs/IMPLEMENTATION_PROGRESS.md` — master index of what's done/pending.
  Update at the end of any session that changes project state.
- `docs/RCA_LOG.md` — root-cause log for every bug found in live testing.
  **Check this before touching a file it mentions** — several entries are
  copy-pasted patterns that recur (see Migrations section below).
- `docs/planning/` — specs, launch criteria, scoring methodology. Durable
  reference docs, not session logs.
- `docs/phases/prompts/` — **runnable plan/prompt documents meant to kick
  off a future session** (e.g. `PRELAUNCH_FIX_PLAN_PROMPT.md`,
  `DOCUMENT_LIFECYCLE_PLAN_PROMPT.md`). Any plan, prompt, or "run this
  next session" deliverable goes here, **never in the scratchpad/Temp
  directory** — scratch is for throwaway session-local files (test
  scripts, one-off debug output), not for anything meant to persist or be
  read by a future session.
- `docs/phases/summaries/` — session handoff summaries.
- `docs/sample/` — sample SOW/RFP documents for manual UI testing.

**Rule of thumb:** if a file is a deliverable someone (you or a future
session) will want to find again, it goes in the repo under `docs/`. If
it's disposable (a scratch script, an ad-hoc test harness, intermediate
debug output), it goes in the scratchpad. When unsure, check for an
existing similar file first (`docs/phases/prompts/` already has 8+ files
— match that pattern, don't invent a new location).

## Migrations — the #1 recurring mistake (RCA entries #3, #11, #12, #13)

There is **no migration runner or tracking table**. A new `.sql` file
under `apps/api/migrations/` does nothing by itself. Every new migration
must be manually applied to **all** of:

1. Local `edgp_dev` Postgres: `docker exec -i edgp-postgres psql -U
   edgp_user -d edgp_dev < apps/api/migrations/0XX_*.sql`
2. Local `edgp_test` Postgres (separate database, same container):
   `docker exec -i edgp-postgres psql -U edgp_user -d edgp_test < ...`
3. **If deployed:** the VPS's `scopewise_prod` Postgres: `docker exec -i
   scopewise-postgres psql -U scopewise_user -d scopewise_prod < ...`
4. `apps/api/tests/test_insights_extra.py`'s `analytics_db` fixture —
   this test file has its own **hand-rolled raw SQL `CREATE TABLE`**
   schema (to dodge an unrelated FK issue) that duplicates `documents`
   and `reviews` columns, separate from the real migrations. Grep this
   file for `CREATE TABLE <model>` for every table a new column touches
   and add the column there too, or `TestAnalyticsTrends` will fail with
   a cryptic `no such column` error.

Forgetting any of these four is the single most common bug this session
hit (repeatedly). Check all four every time, not just the one from the
last incident.

## Testing

- Full backend suite: `cd apps/api && python -m pytest` — baseline is
  **402 passed, 2 skipped**. Don't regress this.
- Frontend type-check: `cd apps/web && npx tsc --noEmit` — must be clean
  before committing any frontend change.
- `apps/web` dev server on Windows: if `next dev`/`next build` hangs
  indefinitely at "Starting..." with no compile output, it's very likely
  Windows Defender real-time scanning a freshly-touched `node_modules`/
  `.next` tree, not a code bug. Fix: add a Defender exclusion for the
  project folder (`E:\code\DocumentGovernancePlatform`) and restart the
  Defender service (`Restart-Service WinDefend -Force`, admin shell) —
  this fully resolved it once already this session.

## Git / deployment

- One commit per logical unit (not one giant commit per session) —
  `git log --oneline` shows the established pattern.
- Only commit/push/deploy when explicitly asked — don't assume standing
  permission from an earlier "yes" in the conversation.
- Push uses the account's own noreply-email pattern per the global
  playbook (`manishjnv` GitHub account, email-privacy block on
  live.com-authored pushes) — not usually needed here since commits are
  already authored as `Claude Code <claude@anthropic.com>`.

### VPS deployment (shared host — be careful)

- SSH alias: `a11yos-vps` (in `~/.ssh/config`, key already set up).
- App lives at `/opt/scopewise` on the VPS, **isolated**: own Docker
  network (`scopewise-net`), own named volumes (`scopewise_*`), own
  container names (`scopewise-*`). Ports 9094 (web) / 9095 (api) — chosen
  because they were free; check `ss -tlnp`/`docker ps` before ever adding
  a new port, this VPS runs several other unrelated projects
  (`assessiq-*`, `accessbridge-*`, `roadmap-*`, `ti-platform-*`). **Never
  touch containers/volumes/configs that aren't `scopewise-*`.**
- Domain routing: `https://scopewise.assessiq.in` → Cloudflare (proxied,
  wildcard `*.assessiq.in` origin cert already covers it) → Caddy
  (`ti-platform-caddy-1`, config at `/opt/ti-platform/caddy/Caddyfile` on
  the VPS) → the two `scopewise-*` containers.
- **Caddyfile edits: truncate-write only (`cat file > Caddyfile`), NEVER
  `mv`** — a documented bind-mount inode trap from a prior incident
  (RCA note baked into the Caddyfile itself). Always back up first
  (`cp Caddyfile Caddyfile.bak.$(date -u +%Y%m%dT%H%M%SZ)`), validate with
  `docker exec ti-platform-caddy-1 caddy validate --config /tmp/new
  --adapter caddyfile` before replacing the live file, then `caddy
  reload` (not restart) to avoid downtime for other sites.
- Standard deploy loop: `git push` locally → `ssh a11yos-vps "cd
  /opt/scopewise && git pull && docker compose -f docker-compose.vps.yml
  --env-file .env build && docker compose -f docker-compose.vps.yml
  --env-file .env up -d"` → apply any new migration (see above) → smoke
  test `https://scopewise.assessiq.in/login`.
- `docker-compose.vps.yml` is distinct from `docker-compose.prod.yml`
  (the latter assumes a dedicated host on standard ports — not this
  VPS). Don't conflate the two.

## Product context worth knowing

- Scoring/risk methodology and why it's designed the way it is:
  `docs/planning/SCORING_METHODOLOGY.md` — cites the real frameworks
  behind it (ISO 31000/NIST risk framing, PMBOK scope structure, IACCM
  most-negotiated-terms research, FAR Part 15 RFP structure). Read this
  before changing scoring/risk logic.
- Finding severity (critical/major/medium/low) is LLM-assigned with no
  external validation yet — tracked in
  `docs/planning/LEGAL_SEVERITY_CALIBRATION.md`, needs a legal SME
  sign-off before being fully trusted.
- Per-org customization (rule enable/disable, agent enable/disable,
  scoring weights, risk weights) already has backend plumbing in
  `apps/api/app/admin/customization.py` — no admin UI yet, but any new
  tunable constant added to scoring/rules should follow this same
  get/set-with-org-override pattern rather than being a hardcoded
  constant, so it stays consistent with what's already there.
