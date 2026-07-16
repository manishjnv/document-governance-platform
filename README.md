# Enterprise Document Governance Platform (EDGP)

An AI-powered platform for reviewing, validating, and improving business documents using organizational standards, industry best practices, and advanced AI.

## Project Structure

```
apps/
  web/          # Next.js 14 frontend (TypeScript, Tailwind)
  api/          # FastAPI backend (Python)

packages/
  shared/       # Shared types and utilities
  ui/           # Reusable React components
  config/       # Configuration management

review-packs/   # Pluggable review logic per document type
rules/          # Configuration-driven rules (JSON)
prompts/        # Version-controlled AI prompts
knowledge/      # Knowledge base and standards
docs/           # Documentation, guides, architecture diagrams
infra/          # Infrastructure as code (Docker, K8s)
docker/         # Docker configurations
scripts/        # Utility scripts
tests/          # Integration and end-to-end tests
```

## Quick Start

### 1. Set up local development environment

```bash
# Clone repository
git clone <repo>
cd DocumentGovernancePlatform

# Copy environment template
cp .env.example .env

# Start Docker services (PostgreSQL, Redis)
docker-compose up -d
```

### 2. Backend (FastAPI)

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Server: http://localhost:8000
Docs: http://localhost:8000/docs

### 3. Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000

## Development Workflow

1. Create feature branch: `git checkout -b feature/T-XXX-description`
2. Make changes
3. Commit with message: `T-XXX: description`
4. Push and create PR
5. After review and tests pass, merge to main

## Technology Stack

**Frontend:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, React Query  
**Backend:** FastAPI, Python, PostgreSQL, Redis, Celery  
**AI:** Claude 3.5 Sonnet, OpenAI GPT-4 (fallback)  
**Document Processing:** pypdf, python-docx  
**Infrastructure:** Docker, Docker Compose, Nginx

## Phase 1 Scope

MVP focuses on **SOW (Statement of Work) Review** with:
- 5 AI agents (Scope, Delivery, Commercial, Security, PMO)
- Rule engine
- Scoring model (0-100)
- PDF report generation
- Basic dashboard

Timeline: 12-16 weeks

See [1_PHASE1_SCOPE.md](1_PHASE1_SCOPE.md) for details.

## Documentation

- [Project Plan](Project_Plan.md) — Vision and long-term roadmap
- [Phase 1 Scope](1_PHASE1_SCOPE.md) — MVP features
- [Master Tasks](2_MASTER_TASKS.md) — Implementation roadmap (127 tasks)
- [Database Schema](3_DATABASE_SCHEMA.md) — Data model
- [AI Agent Specs](4_AI_AGENT_SPECS.md) — Agent prompts and outputs
- [Launch Criteria](5_LAUNCH_CRITERIA.md) — Success metrics and testing plan

## Contributing

See [CODING_STANDARDS.md](CODING_STANDARDS.md) for development guidelines.

## License

Proprietary — Internal use only
