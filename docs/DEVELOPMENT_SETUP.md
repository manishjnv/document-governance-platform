# Local Development Setup

This guide walks you through setting up the EDGP development environment on your machine.

## Prerequisites

- **Git** — For version control
- **Docker & Docker Compose** — For database and cache services
- **Python 3.11+** — For the FastAPI backend
- **Node.js 18+** — For the Next.js frontend
- **npm or yarn** — Node package manager

## Quick Start (5 minutes)

### 1. Clone and Navigate

```bash
git clone <repository-url>
cd DocumentGovernancePlatform
```

### 2. Copy Environment Files

```bash
cp .env.example .env
cp apps/api/.env.example apps/api/.env  # (if needed)
cp apps/web/.env.example apps/web/.env.local
```

### 3. Start Docker Services

```bash
docker-compose up -d
```

This starts:
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

Verify:
```bash
docker ps
```

### 4. Backend Setup

```bash
cd apps/api
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs

### 5. Frontend Setup

```bash
cd apps/web
npm install
npm run dev
```

App: http://localhost:3000

## Detailed Guides

### Docker Services Management

**Start services:**
```bash
docker-compose up -d
```

**View logs:**
```bash
docker-compose logs -f postgres
docker-compose logs -f redis
```

**Stop services:**
```bash
docker-compose down
```

**Remove volumes (reset data):**
```bash
docker-compose down -v
```

### PostgreSQL Database

**Connect directly:**
```bash
docker-compose exec postgres psql -U edgp_user -d edgp_dev
```

**List databases:**
```sql
\l
```

**List tables:**
```sql
\dt
```

### FastAPI Backend

**Install dependencies:**
```bash
cd apps/api
pip install -r requirements.txt
```

**Run development server:**
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Run tests:**
```bash
pytest
```

**Run with logging:**
```bash
export LOG_LEVEL=DEBUG
uvicorn main:app --reload
```

**Database migrations (future):**
```bash
alembic upgrade head
alembic revision --autogenerate -m "description"
alembic upgrade head
```

### Next.js Frontend

**Install dependencies:**
```bash
cd apps/web
npm install
```

**Development server:**
```bash
npm run dev
```

**Build for production:**
```bash
npm run build
npm start
```

**Type checking:**
```bash
npm run type-check
```

**Linting:**
```bash
npm run lint
```

**Format code:**
```bash
npm run format
```

## Environment Variables

See `.env.example` for all available options.

**Required for development:**
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `NEXT_PUBLIC_API_URL` — API base URL

**Optional but recommended:**
- `CLAUDE_API_KEY` — For AI features
- `DEBUG=true` — Verbose logging

## Troubleshooting

### PostgreSQL Connection Error

```
Error: could not translate host name "postgres" to address
```

**Solution:** Docker is not running. Start Docker daemon.

```bash
docker-compose up -d
```

### Port Already in Use

```
Address already in use (:8000)
```

**Solution:** Change port or kill process:

```bash
lsof -i :8000  # Find process
kill -9 <PID>
```

Or use different port:
```bash
uvicorn main:app --port 8001
```

### npm install Fails

```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Virtual Environment Issues

```bash
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Database Locked

If PostgreSQL is not responding:

```bash
docker-compose restart postgres
```

## Git Workflow

### Before Starting Work

```bash
git pull origin main
git checkout -b feature/T-XXX-description
```

### During Development

Commit frequently:
```bash
git add <files>
git commit -m "T-XXX: brief description"
```

### Push and Create PR

```bash
git push origin feature/T-XXX-description
```

Then create a Pull Request on GitHub.

## IDE Setup

### VS Code

**Extensions:**
- Python
- Pylance
- FastAPI
- ES7+ React/Redux/React-Native snippets
- Tailwind CSS IntelliSense
- Prettier - Code formatter

**Settings:**
```json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode",
    "editor.formatOnSave": true
  }
}
```

### PyCharm

- Open `apps/api` as project
- Mark `app` folder as Sources Root
- Configure Python interpreter to `venv`

### WebStorm

- Open `apps/web` as project
- Configure Node.js interpreter

## Performance Tips

- Use `--reload` only for active development
- Close unused services to save RAM
- Use database indexes for frequently queried fields
- Cache API responses with React Query

## Getting Help

1. Check logs: `docker-compose logs`
2. Review error messages carefully
3. Search existing GitHub issues
4. Ask in team Slack channel
5. Check [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

## Next Steps

- Read [CODING_STANDARDS.md](../CODING_STANDARDS.md)
- Review database schema in [DATABASE_SCHEMA.md](./DATABASE_SCHEMA.md)
- Check AI agent specs in [AI_AGENT_SPECS.md](../4_AI_AGENT_SPECS.md)
