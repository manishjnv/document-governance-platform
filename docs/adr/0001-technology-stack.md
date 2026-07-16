# ADR-0001: Technology Stack Selection

**Date:** 2026-07-17  
**Status:** Accepted  
**Owner:** Architecture Team

---

## 1. Context

We are building an enterprise-grade AI-powered document governance platform (EDGP) from scratch. We need to select technologies that support:
- Multiple concurrent users and documents
- AI/LLM integration for document review
- Asynchronous processing (document parsing, AI reviews)
- Multi-tenancy with data isolation
- Production-grade security and monitoring
- Ability to evolve without major rewrites

### Constraints
- Build Phase 1 MVP in 12-16 weeks
- Team has Python/JavaScript expertise
- Must support cloud and on-premises deployment
- Open-source preferred where possible

---

## 2. Decision

### Chosen Stack

**Frontend:**
- Next.js 14 (React framework)
- TypeScript (type safety)
- Tailwind CSS + shadcn/ui (styling & components)
- React Query (data fetching)
- Zustand (state management)

**Backend:**
- FastAPI (Python web framework)
- PostgreSQL 16 (relational database)
- Redis 7 (caching & task queue)
- Celery (async task processing)
- SQLAlchemy (ORM)

**AI:**
- Claude 3.5 Sonnet (primary LLM)
- OpenAI GPT-4 Turbo (fallback)

**Infrastructure:**
- Docker + Docker Compose (local dev & deployment)
- Nginx (reverse proxy)
- Single EC2/VM for MVP (t3.large)

### Rationale

**Why Next.js over alternatives?**
- Built on React (team expertise)
- Full-stack capabilities (API routes)
- Excellent TypeScript support
- Server-side rendering options
- Great developer experience

**Why FastAPI over Django/Flask?**
- Async-first design (perfect for I/O-heavy operations)
- Automatic OpenAPI docs
- Built-in validation with Pydantic
- Modern Python features (3.11+)
- Excellent performance

**Why PostgreSQL over NoSQL?**
- ACID compliance (data integrity critical for legal documents)
- Complex queries (cross-document validation)
- Excellent full-text search
- JSONB for flexible metadata
- Multi-tenancy support with schemas

**Why Redis over Memcached?**
- Advanced data structures (queues, sets, sorted sets)
- Pub/Sub for notifications
- Persistence options
- Celery integration

**Why Celery over background jobs in FastAPI?**
- Distributed task processing
- Retry logic and monitoring
- Task persistence and history
- Scales horizontally for future growth

**Why Claude + OpenAI?**
- Claude: Superior reasoning for document review
- OpenAI: Fallback for availability
- Both support enterprise no-training clauses

---

## 3. Consequences

### Positive Impacts
✓ Team productivity: Python + JavaScript expertise directly applicable  
✓ Async architecture supports 1000+ concurrent documents easily  
✓ PostgreSQL ACID guarantees protect sensitive document data  
✓ Celery enables future horizontal scaling  
✓ Docker enables cloud-agnostic deployment  
✓ FastAPI auto-docs reduce documentation burden  

### Negative Impacts
✗ Celery adds operational complexity (requires Redis + workers)  
✗ PostgreSQL schema migrations require careful planning  
✗ TypeScript learning curve for frontend team (mitigated by existing JS knowledge)  
✗ Multi-model AI fallback adds latency & cost  

### Trade-offs
- Chose async complexity over simplicity: justifiable for scale requirements
- Chose two AI models over one: justifiable for reliability
- Chose PostgreSQL over NoSQL: ACID requirements dominate

### Migration Path
If PostgreSQL becomes bottleneck:
- Add read replicas for reporting queries
- Migrate to Postgres' native sharding (Citus) or Vitess
- Archive old reviews to separate database

If Celery becomes complex:
- Migrate to Temporal.io for workflow orchestration
- Or switch to managed queue (AWS SQS, GCP Pub/Sub)

---

## 4. Implementation Details

### Version Pins
- Python: 3.11+
- Node.js: 18+
- PostgreSQL: 16 (Alpine)
- Redis: 7 (Alpine)
- Next.js: 14
- FastAPI: 0.104+

### Key Dependencies
Backend: See `apps/api/requirements.txt`  
Frontend: See `apps/web/package.json`

### Configuration
Environment-based config via `.env` files  
Sensitive values: Never committed, loaded at runtime

---

## 5. Review & Approval

Approved by Architecture Team on 2026-07-17.

Future re-evaluation triggers:
- If P99 API latency exceeds 500ms
- If Celery queue depth consistently >1000 tasks
- If PostgreSQL replication lag exceeds 5 seconds
- If team feedback indicates pain points

