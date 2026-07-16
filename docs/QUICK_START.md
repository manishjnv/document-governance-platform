# Quick Start Guide

Get EDGP running locally in 5 minutes.

## Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose

## Backend Setup (FastAPI)

### 1. Open Terminal in `apps/api`

```bash
cd apps/api
```

### 2. Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start Docker Services (PostgreSQL + Redis)

In a **separate terminal**, from the project root:

```bash
docker-compose up -d
```

Verify services are running:
```bash
docker-compose ps
```

### 5. Run the Server

Back in the `apps/api` terminal (with venv activated):

```bash
uvicorn main:app --reload
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 6. Access the API

- **Interactive Docs:** http://localhost:8000/docs
- **Health Check:** http://localhost:8000/health
- **OpenAPI Schema:** http://localhost:8000/openapi.json

## Frontend Setup (Next.js)

### 1. Open Terminal in `apps/web`

```bash
cd apps/web
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Run Dev Server

```bash
npm run dev
```

You should see:
```
▲ Next.js 14.0.0
- Local:        http://localhost:3000
```

### 4. Access the App

Open http://localhost:3000

## Test Login Credentials

**Phase 1 MVP uses test data:**

- **Email:** admin@example.com
- **Password:** password123

(These will be replaced with real database in T-201+)

## Verify Everything Works

### Test Backend

```bash
# From apps/api directory
python test_startup.py
```

Or manually:
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "edgp-api",
  "version": "1.0.0"
}
```

### Test Auth Endpoint

```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "password123"
  }'
```

Expected response: JWT tokens

```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "expires_in": 86400,
  "token_type": "bearer",
  "user_id": 1,
  "email": "admin@example.com",
  "first_name": "Admin",
  "last_name": "User",
  "org_id": 1,
  "role": "admin"
}
```

## Troubleshooting

### `ERR_EMPTY_RESPONSE` when accessing http://localhost:8000/docs

**Problem:** Server isn't responding

**Solution:**
1. Check server is running: `uvicorn main:app --reload`
2. Check port 8000 is available: `lsof -i :8000` (macOS/Linux) or `netstat -ano | findstr :8000` (Windows)
3. Check for errors in terminal

### `ModuleNotFoundError: No module named 'main'`

**Problem:** Running uvicorn from wrong directory

**Solution:**
```bash
cd apps/api
uvicorn main:app --reload
```

### `pydantic.errors.PydanticUserError: 'regex' is removed`

**Problem:** Old Pydantic syntax in code

**Solution:** Already fixed in the latest commit. Update to latest code.

### Docker services not starting

**Problem:** PostgreSQL or Redis won't start

**Solution:**
```bash
# From project root
docker-compose down -v  # Remove volumes
docker-compose up -d    # Restart
```

### `bcrypt: no backends available`

**Problem:** bcrypt library not installed

**Solution:**
```bash
pip install bcrypt
```

## Next Steps

1. Read [DEVELOPMENT_SETUP.md](./DEVELOPMENT_SETUP.md) for deeper dev environment info
2. Review [API_AUTH.md](./API_AUTH.md) to understand auth endpoints
3. Check [CODING_STANDARDS.md](../CODING_STANDARDS.md) for contribution guidelines

## Common Commands

```bash
# Terminal 1: Backend
cd apps/api
source venv/bin/activate  # or venv\Scripts\activate on Windows
uvicorn main:app --reload

# Terminal 2: Frontend
cd apps/web
npm run dev

# Terminal 3: Docker services (from project root)
docker-compose up

# Terminal 4: Git/debugging
# Keep this free for git, testing, etc.
```

## API Examples

### Get Current User

```bash
# 1. Get token from login
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"password123"}' \
  | jq -r '.access_token')

# 2. Use token to get current user
curl http://localhost:8000/api/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token":"<your_refresh_token>"}'
```

## IDE Setup

### VS Code
- Python extension
- Pylance
- FastAPI extension

### PyCharm
- Configure Python interpreter to use venv
- Mark `apps/api` as Sources Root

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit as needed. Key variables:
- `DATABASE_URL`: PostgreSQL connection
- `REDIS_URL`: Redis connection
- `NEXT_PUBLIC_API_URL`: Frontend API base URL

---

**Everything working?** ✓ You're ready to develop!

See [MASTER_TASKS.md](../2_MASTER_TASKS.md) for next implementation tasks.
