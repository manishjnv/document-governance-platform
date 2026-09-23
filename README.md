# ScopeSense

AI-assisted review of Statements of Work (SOWs) and RFPs. Upload a document and
ScopeSense runs six specialist review agents plus a deterministic rule engine
over it, scores it 0–100, lists findings by severity with the clause they cite,
and produces a report you can hand to the business.

Live: **https://scopesense.in**

## What it does

| Module | What you get | Where |
|---|---|---|
| **Document review** | Six LLM review agents (Scope, Delivery, Commercial, Security, PMO, Legal), a conflict detector, a rule engine, 0–100 scoring and a PDF report. Projects, versioning, fix verification, approvals, comments and audit log. | `apps/api/app/ai`, `rules`, `scoring` · `/upload`, `/results`, `/projects` |
| **MITRE ATT&CK coverage assessment** | Maps an organisation's detections and tooling onto ATT&CK and produces coverage reports (PDF / PPTX / XLSX). It can pull from a SIEM such as Splunk and ships a Microsoft Sentinel workbook. | `apps/api/app/mitre` · `/mitre` |
| **Code security review** | Imports findings from the Visa Vulnerability Agentic Harness (`findings.json`) or SARIF and renders a findings register plus XLSX/PPTX deliverables. Deterministic, with no LLM and no server-side scanning. | `apps/api/app/codereview` · `/codereview` |

Supported upload formats: PDF, DOCX, DOC, XLSX, XLS, CSV.

## Architecture

```
Browser ──> Next.js 14 (apps/web) ──/api/...──> FastAPI (apps/api) ──> PostgreSQL 16
                                                     │
                                                     ├──> Redis ──> Celery worker (reports, scheduled pulls)
                                                     └──> OpenRouter (LLM calls for the review agents)
```

- **LLM provider:** all review-pipeline calls go through **OpenRouter** with a
  primary model and a fallback chain (`apps/api/app/config.py`,
  `apps/api/app/ai/agent.py`). This is a deliberate cost choice, so don't wire
  the pipeline to a model vendor directly. Model choice and measured accuracy
  are covered in [AI_MODEL_ROUTING.md](docs/planning/AI_MODEL_ROUTING.md).
- **Auth:** Google Sign-In and email one-time codes. There are no passwords.
- **Per-org customisation:** org admins can turn rules and agents on or off
  and change scoring and risk weights, via `apps/api/app/admin/customization.py`.

## Repository layout

```
apps/
  api/            FastAPI backend: routers, AI agents, rule engine, scoring, MITRE, code review
    migrations/   Numbered SQL migrations (applied by hand, see below)
    tests/        pytest suite
  web/            Next.js 14 + TypeScript + Tailwind + shadcn/ui frontend
prompts/          Generated, read-only mirror of the agents' prompts (source: apps/api/app/ai/agent.py)
scripts/          Generators and harnesses (prompt docs, templates, theme, accuracy, MITRE data)
marketplace/      Microsoft Sentinel content (workbook)
docs/             Planning, module references, RCA log, design, samples
k8s/              Kubernetes manifests (not used by the current deployment)
docker-compose.yml       Local Postgres + Redis
docker-compose.vps.yml   Production stack (postgres, redis, api, worker, web)
```

## Local development

Prerequisites: Python 3.11, Node.js 20, Docker.

### 1. Configuration

```bash
cp .env.example .env
cp apps/web/.env.example apps/web/.env.local
```

In `.env`, set at least:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | e.g. `postgresql+asyncpg://edgp_user:edgp_password@localhost:5432/edgp_dev` |
| `REDIS_URL` | `redis://localhost:6379` |
| `JWT_SECRET_KEY` | any long random string |
| `OPENROUTER_API_KEY` | needed to run real reviews |
| `REQUIRE_PAID_TIER_FOR_RUNS=false` | lets a free local org run reviews and assessments |

With `SMTP_*` left empty, email login codes are written to the API log instead
of being sent, so you can sign in locally without a mail server.
`GOOGLE_CLIENT_ID` and `NEXT_PUBLIC_GOOGLE_CLIENT_ID` are only needed for Google
Sign-In.

### 2. Database and Redis

```bash
docker compose up -d        # edgp-postgres (5432) + edgp-redis (6379)
```

There is **no migration runner**. Apply every migration in order once, then
each new one as it lands:

```bash
for f in apps/api/migrations/0*.sql; do
  docker exec -i edgp-postgres psql -U edgp_user -d edgp_dev < "$f"
done
```

The test suite uses a second database, `edgp_test`, in the same container.
Create it and apply the same migrations to it.

### 3. API

```bash
cd apps/api
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload                          # http://localhost:8000/docs
```

Background jobs such as PDF rendering and scheduled SIEM pulls need a worker:

```bash
celery -A app.core.celery_app worker -B --loglevel=info
```

### 4. Web

```bash
cd apps/web
npm install
npm run dev                                        # http://localhost:3000
```

## Testing

```bash
cd apps/api && python -m pytest        # full backend suite, runs against edgp_test
cd apps/web && npx tsc --noEmit        # frontend type-check, must be clean
python apps/web/tests/ui_sweep.py --base http://localhost:3000   # layout sweep at 1440/390 px
```

The backend suite takes about 10 minutes. Run only one copy at a time, because
two parallel runs deadlock on the shared `edgp_test` database. The current
pass/skip baseline is recorded in [CLAUDE.md](CLAUDE.md#testing).

## Working on the codebase

Read these before changing the matching area:

| If you touch… | Read first |
|---|---|
| An agent prompt in `app/ai/agent.py` | [PROMPT_ENGINEERING_GUIDE.md](docs/planning/PROMPT_ENGINEERING_GUIDE.md), then run `python scripts/generate_prompt_docs.py` |
| Scoring or risk logic | [SCORING_METHODOLOGY.md](docs/planning/SCORING_METHODOLOGY.md) |
| Anything under `mitre/` | [MITRE_MODULE_REFERENCE.md](docs/planning/MITRE_MODULE_REFERENCE.md) |
| Anything under `codereview/` | [CODE_REVIEW_MODULE_REFERENCE.md](docs/planning/CODE_REVIEW_MODULE_REFERENCE.md) |
| A new SQL migration | The "Migrations" section of [CLAUDE.md](CLAUDE.md). A migration must reach dev, test and prod, plus the hand-rolled schema in `tests/test_insights_extra.py` and any matching ORM `CheckConstraint`. |
| A bug fix | Add an entry to [RCA_LOG.md](docs/RCA_LOG.md) |

Other useful documents:

- [IMPLEMENTATION_PROGRESS.md](docs/IMPLEMENTATION_PROGRESS.md): what is done and what is pending
- [4_AI_AGENT_SPECS.md](docs/planning/4_AI_AGENT_SPECS.md): what each agent checks and returns
- [3_DATABASE_SCHEMA.md](docs/planning/3_DATABASE_SCHEMA.md): data model
- [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) · [API_AUTH.md](docs/API_AUTH.md)
- [docs/sample/](docs/sample/): sample SOWs and RFPs for manual testing and accuracy work

Commits are small, with one logical change per commit.

## Deployment

Production runs `docker-compose.vps.yml` on a shared VPS behind Cloudflare and
Caddy. The compose project, container and volume names (`scopewise-*`) predate
the product rename and are kept on purpose. The deploy loop, Caddy rules and
port allocation are documented in [CLAUDE.md](CLAUDE.md#vps-deployment-shared-host--be-careful)
and [PRODUCTION_DEPLOYMENT.md](docs/PRODUCTION_DEPLOYMENT.md).
`docker-compose.prod.yml` is for a dedicated host and is not the live setup.

## License

Proprietary. Copyright © 2026 Foxfiber Retail LLP. The source is public so
people can read and review it, but no rights to use, copy or host it are
granted. See [LICENSE](LICENSE). `apps/api/app/codereview/kit/vendor/` contains
third-party code under the Apache License 2.0.
