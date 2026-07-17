# MASTER_TASKS.md - Phase 1 Implementation Roadmap

**Status:** Ready to start
**Total Tasks:** 127 atomic tasks
**Estimated Duration:** 12-16 weeks (3 person team)

---

## Task Numbering System

- **T-0xx:** Infrastructure & Setup
- **T-1xx:** Authentication & Identity
- **T-2xx:** Database & Schema
- **T-3xx:** Document Management
- **T-4xx:** AI Engine & Agents
- **T-5xx:** Rule Engine
- **T-6xx:** Scoring & Reporting
- **T-7xx:** Frontend UI
- **T-8xx:** Dashboard
- **T-9xx:** Testing & QA
- **T-10xx:** Deployment & Ops

---

# WEEK 1-2: Foundation & Authentication

## Epic: Project Setup (T-0xx)

- [ ] **T-001** Create monorepo structure (apps/web, apps/api, packages/shared, docs)
- [ ] **T-002** Set up GitHub repo with branch protection rules
- [ ] **T-003** Configure Docker Compose for local dev (PostgreSQL, Redis, app services)
- [ ] **T-004** Create .env.example with all required variables
- [ ] **T-005** Set up FastAPI project skeleton with logging
- [ ] **T-006** Set up Next.js project skeleton with TypeScript config
- [ ] **T-007** Document local dev setup instructions (README.md)
- [ ] **T-008** Create CODING_STANDARDS.md (naming, folder structure, error handling)
- [ ] **T-009** Set up pre-commit hooks (linting, formatting)
- [ ] **T-010** Create architecture decision record (ADR) folder structure

## Epic: Authentication (T-1xx)

- [ ] **T-101** Design JWT token schema (structure, claims, expiry, refresh logic)
- [ ] **T-102** Implement FastAPI auth middleware for JWT validation
- [ ] **T-103** Implement local login endpoint (POST /api/v1/auth/login)
  - Input: email, password
  - Output: access_token, refresh_token, expires_in
  - Error: 401 for invalid credentials
- [ ] **T-104** Implement logout endpoint (POST /api/v1/auth/logout)
- [ ] **T-105** Implement refresh token endpoint (POST /api/v1/auth/refresh)
- [ ] **T-106** Implement "get current user" endpoint (GET /api/v1/auth/me)
- [ ] **T-107** Implement password hashing (bcrypt) for user storage
- [ ] **T-108** Implement rate limiting on login (max 5 failed attempts)
- [ ] **T-109** Implement Azure AD/Entra ID OAuth integration (optional flow)
- [ ] **T-110** Add password reset flow (email link, token validation)
- [ ] **T-111** Create auth UI (login form, logout button)
- [ ] **T-112** Add auth tests (valid login, invalid creds, token refresh, expiry)
- [ ] **T-113** Document auth API spec (OpenAPI/Swagger)

---

# WEEK 2-3: Database & Document Schema

## Epic: Database Schema (T-2xx)

- [ ] **T-201** Design normalized schema (organizations, users, documents, reviews, findings, audit_logs)
- [ ] **T-202** Create PostgreSQL migration file (001_init_schema.sql)
- [ ] **T-203** Implement alembic migrations framework for schema versioning
- [ ] **T-204** Create indexes on frequently queried columns (org_id, doc_id, status)
- [ ] **T-205** Implement JSONB column for flexible finding metadata
- [ ] **T-206** Add created_at, updated_at, deleted_at timestamps to all tables
- [ ] **T-207** Implement soft delete pattern (deleted_at != null)
- [ ] **T-208** Create audit_logs table with full change tracking
- [ ] **T-209** Add foreign key constraints with CASCADE rules
- [ ] **T-210** Test schema with sample data (50 orgs, 500 users, 1000 docs)
- [ ] **T-211** Document schema diagram (ERD visual)
- [ ] **T-212** Document table definitions (schema_docs.md)
- [ ] **T-213** Implement database backup strategy in Docker Compose

## Epic: ORM & Database Layer (T-2xx cont.)

- [ ] **T-214** Set up SQLAlchemy ORM with async support (async_sessionmaker)
- [ ] **T-215** Create Pydantic models for all tables (separate schema.py)
- [ ] **T-216** Implement base repository class with CRUD operations
- [ ] **T-217** Create repository subclasses (OrganizationRepo, UserRepo, DocumentRepo, ReviewRepo)
- [ ] **T-218** Implement soft delete in all queries (filter out deleted_at != null)
- [ ] **T-219** Add database connection pooling configuration
- [ ] **T-220** Test ORM with unit tests (create, read, update, delete per table)

---

# WEEK 2-3: Document Management APIs

## Epic: Document Upload & Storage (T-3xx)

- [ ] **T-301** Design S3/Blob storage key structure (org/{org_id}/doc/{doc_id}/v{version}.pdf)
- [ ] **T-302** Implement S3 client initialization (boto3 for AWS or azure.storage for Azure)
- [ ] **T-303** Create upload endpoint (POST /api/v1/documents/upload)
  - Accept: DOCX or PDF file
  - Return: doc_id, filename, upload_date, status=pending
  - Validate: Max 50MB, DOCX/PDF only
- [ ] **T-304** Implement file virus scanning (optional: ClamAV or upload to service)
- [ ] **T-305** Implement document type detection (SOW vs other, via filename + content)
- [ ] **T-306** Create list documents endpoint (GET /api/v1/documents?org_id=X&limit=50)
- [ ] **T-307** Create get document metadata endpoint (GET /api/v1/documents/{doc_id})
- [ ] **T-308** Create delete document endpoint (DELETE /api/v1/documents/{doc_id}) → soft delete
- [ ] **T-309** Implement S3 download/retrieve for later viewing
- [ ] **T-310** Add storage quota management (org can upload up to N GB)
- [ ] **T-311** Test upload with various file sizes and formats
- [ ] **T-312** Document upload API spec

## Epic: Document Parsing (T-3xx cont.)

- [ ] **T-313** Implement DOCX parser (extract text, preserve structure)
  - Use: python-docx library
  - Output: raw_text, sections (title, para, heading levels)
- [ ] **T-314** Implement PDF parser (extract text, preserve structure)
  - Use: pypdf library
  - Output: raw_text, sections (detected by font size/formatting)
- [ ] **T-315** Create text extraction pipeline (normalize whitespace, remove junk)
- [ ] **T-316** Store parsed content in PostgreSQL (documents.parsed_text column)
- [ ] **T-317** Implement SOW validation (must have required sections or flag as "unclear format")
- [ ] **T-318** Create document sections extraction (title, scope, timeline, etc. detection)
- [ ] **T-319** Test parsing with 10 real SOWs (verify text accuracy)
- [ ] **T-320** Document parsing logic (parsing_pipeline.md)

---

# WEEK 4-7: AI Review Agents

## Epic: AI Agent Infrastructure (T-4xx)

- [ ] **T-401** Design agent orchestrator pattern (coordinator that calls 5 agents in parallel)
- [ ] **T-402** Implement Claude API client (wrapper for async calls)
- [ ] **T-403** Create agent base class (handles prompting, parsing, error handling)
- [ ] **T-404** Implement retry logic with exponential backoff (max 3 retries)
- [ ] **T-405** Implement token counting (estimate costs per review)
- [ ] **T-406** Create structured output parser (JSON validation from LLM responses)
- [ ] **T-407** Implement confidence scoring from agent responses
- [ ] **T-408** Add request/response logging for all agent calls
- [ ] **T-409** Implement agent timeout (max 60 seconds per agent call)
- [ ] **T-410** Create agent test harness (run agents locally on test SOWs)

## Epic: Scope Reviewer Agent (T-4xx cont.)

- [ ] **T-411** Write Scope Reviewer system prompt (extract deliverables, acceptance criteria, scope boundaries)
- [ ] **T-412** Define Scope Reviewer output schema (JSON: [deliverables, criteria, boundaries, findings])
- [ ] **T-413** Implement Scope Reviewer as Python class
- [ ] **T-414** Create prompt template with section markers (e.g., [DELIVERABLES SECTION] extracted from...)
- [ ] **T-415** Implement Scope Reviewer findings:
  - Missing acceptance criteria
  - Ambiguous deliverable definitions
  - Scope boundaries unclear
  - Scope creep language detected
- [ ] **T-416** Add confidence scoring (0-100 for each finding)
- [ ] **T-417** Test Scope Reviewer on 5 test SOWs
- [ ] **T-418** Document Scope Reviewer spec (scope_reviewer_spec.md)

## Epic: Delivery Reviewer Agent (T-4xx cont.)

- [ ] **T-419** Write Delivery Reviewer system prompt (extract timeline, milestones, dependencies, assumptions)
- [ ] **T-420** Define Delivery Reviewer output schema
- [ ] **T-421** Implement Delivery Reviewer as Python class
- [ ] **T-422** Implement Delivery Reviewer findings:
  - Missing timeline
  - Unrealistic milestone dates
  - Undefined dependencies
  - Missing assumptions
  - No delay clause
  - No hypercare period defined
- [ ] **T-423** Add confidence scoring
- [ ] **T-424** Test Delivery Reviewer on 5 test SOWs
- [ ] **T-425** Document Delivery Reviewer spec

## Epic: Commercial Reviewer Agent (T-4xx cont.)

- [ ] **T-426** Write Commercial Reviewer system prompt (extract pricing, payment terms, conditions)
- [ ] **T-427** Define Commercial Reviewer output schema
- [ ] **T-428** Implement Commercial Reviewer as Python class
- [ ] **T-429** Implement Commercial Reviewer findings:
  - Ambiguous pricing model
  - Missing payment terms
  - Unclear invoicing schedule
  - No price escalation clause
  - Missing payment condition triggers
  - Ambiguous out-of-scope pricing
- [ ] **T-430** Add confidence scoring
- [ ] **T-431** Test Commercial Reviewer on 5 test SOWs
- [ ] **T-432** Document Commercial Reviewer spec

## Epic: Security & Compliance Reviewer Agent (T-4xx cont.)

- [ ] **T-433** Write Security Reviewer system prompt (extract security requirements, compliance mandates, data clauses)
- [ ] **T-434** Define Security Reviewer output schema
- [ ] **T-435** Implement Security Reviewer as Python class
- [ ] **T-436** Implement Security Reviewer findings:
  - Missing security clauses
  - Undefined compliance requirements (SOC2, ISO27001, etc.)
  - No data handling clause
  - Missing audit rights clause
  - No data residency specification
  - Missing encryption requirements
- [ ] **T-437** Add confidence scoring
- [ ] **T-438** Test Security Reviewer on 5 test SOWs
- [ ] **T-439** Document Security Reviewer spec

## Epic: Project Operations Reviewer Agent (T-4xx cont.)

- [ ] **T-440** Write PMO Reviewer system prompt (extract RACI, escalation, governance, resource needs)
- [ ] **T-441** Define PMO Reviewer output schema
- [ ] **T-442** Implement PMO Reviewer as Python class
- [ ] **T-443** Implement PMO Reviewer findings:
  - Missing RACI matrix
  - Unclear escalation path
  - Missing governance structure
  - No change control process
  - Undefined resource commitment
  - No SLA definitions
- [ ] **T-444** Add confidence scoring
- [ ] **T-445** Test PMO Reviewer on 5 test SOWs
- [ ] **T-446** Document PMO Reviewer spec

## Epic: Agent Orchestration (T-4xx cont.)

- [ ] **T-447** Implement ReviewOrchestrator class
  - Call all 5 agents in parallel (asyncio.gather)
  - Aggregate findings
  - Return combined result within 30 seconds
- [ ] **T-448** Implement agent fallback (if one agent times out, continue with others)
- [ ] **T-449** Implement agent result caching (same SOW, same agent = cached for 24h)
- [ ] **T-450** Create async review task (Celery task or FastAPI BackgroundTask)
- [ ] **T-451** Implement review status tracking (pending → running → completed → error)
- [ ] **T-452** Test orchestrator end-to-end with 10 test SOWs
- [ ] **T-453** Document orchestrator pattern

---

# WEEK 7-8: Rule Engine

## Epic: Rule Engine (T-5xx)

- [ ] **T-501** Design rule format (JSON schema: rule_id, name, doc_type, severity, check_type, params)
- [ ] **T-502** Implement rule loader (load from JSON files or database)
- [ ] **T-503** Implement rule executor (evaluate conditions, return pass/fail + message)
- [ ] **T-504** Create built-in rules (20 core SOW rules as JSON):
  - rule-001: SOW must have acceptance criteria
  - rule-002: SOW must have timeline
  - rule-003: SOW must define scope boundaries
  - rule-004: SOW must have RACI
  - ... (20 total, see rule_engine_spec.md)
- [ ] **T-505** Implement section presence checks (e.g., "Acceptance Criteria" section must exist)
- [ ] **T-506** Implement section word count checks (e.g., "Acceptance Criteria" must be >50 words)
- [ ] **T-507** Implement conditional rules (e.g., "if SOW > $100K, then delay clause required")
- [ ] **T-508** Implement keyword-based checks (e.g., search for "acceptance criteria" in document)
- [ ] **T-509** Store rule results in findings table
- [ ] **T-510** Create rule management API (GET /api/v1/rules, no create/update in Phase 1)
- [ ] **T-511** Test all 20 rules on test SOW set
- [ ] **T-512** Document rule format and built-in rules

---

# WEEK 8-9: Scoring & Reporting

## Epic: Scoring Model (T-6xx)

- [ ] **T-601** Design scoring algorithm (7 categories, 0-100 each, equally weighted → 0-100 overall)
- [ ] **T-602** Implement category scorers:
  - Completeness (% of required sections found)
  - Clarity (ambiguity scan on deliverables/timeline)
  - Consistency (internal contradiction checks)
  - Commercial (pricing/payment clarity)
  - Delivery (timeline/milestone definition)
  - Operations (RACI/governance)
  - Security (compliance coverage)
- [ ] **T-603** Implement scoring from agent findings (higher confidence → higher score contribution)
- [ ] **T-604** Implement scoring from rule results (pass=+points, fail=-points)
- [ ] **T-605** Add penalty for critical findings (overall score capped at 70 if any critical issue)
- [ ] **T-606** Implement risk score (aggregate severity of all findings)
- [ ] **T-607** Test scoring on 20 test SOWs (verify reasonableness)
- [ ] **T-608** Document scoring algorithm

## Epic: Report Generation (T-6xx cont.)

- [ ] **T-609** Design report template (HTML)
- [ ] **T-610** Implement executive summary generator (1 paragraph: quality score, top 3 risks, recommendation)
- [ ] **T-611** Implement scorecard section (7 categories with 0-100 scores)
- [ ] **T-612** Implement risk heatmap (visual grid: severity vs likelihood)
- [ ] **T-613** Implement detailed findings section (table: priority, issue, evidence, recommendation)
- [ ] **T-614** Implement PDF export (reportlab or weasyprint)
- [ ] **T-615** Add organization branding to PDF (logo, footer, colors)
- [ ] **T-616** Implement report caching (same review = cached for 48h)
- [ ] **T-617** Create report generation API (GET /api/v1/reviews/{id}/report)
- [ ] **T-618** Test PDF generation with various findings
- [ ] **T-619** Document report format

---

# WEEK 9-10: Frontend UI

## Epic: Core Pages (T-7xx)

- [ ] **T-701** Create layout component (header, sidebar, main content)
- [ ] **T-702** Create login page (email/password form, Entra ID button)
- [ ] **T-703** Create authenticated dashboard (redirect if not logged in)
- [ ] **T-704** Create upload page (drag-and-drop DOCX/PDF upload)
- [ ] **T-705** Implement upload progress indicator
- [ ] **T-706** Create document list page (table: filename, upload date, status)
- [ ] **T-707** Create review results page (scorecard + findings list)
- [ ] **T-708** Create findings detail modal (click finding → show evidence + recommendation)
- [ ] **T-709** Implement findings filtering (by severity, by agent, by status)
- [ ] **T-710** Create report PDF download button

## Epic: User Flows (T-7xx cont.)

- [ ] **T-711** Implement upload → review → report flow
  - Upload doc
  - Show "Review in progress..."
  - Poll status every 2 seconds
  - Show results when complete
- [ ] **T-712** Implement error handling (failed review, timeout, etc.)
- [ ] **T-713** Implement loading states (spinners, skeleton screens)
- [ ] **T-714** Implement responsive design (mobile, tablet, desktop)
- [ ] **T-715** Add form validation (required fields, file type)
- [ ] **T-716** Test UI on Chrome, Firefox, Safari

## Epic: Styling & Branding (T-7xx cont.)

- [ ] **T-717** Create design system (colors, typography, spacing)
- [ ] **T-718** Use Tailwind CSS + shadcn/ui components
- [ ] **T-719** Implement dark mode toggle (optional)
- [ ] **T-720** Test accessibility (WCAG AA compliance)

---

# WEEK 10-11: Dashboard & Admin

## Epic: Basic Dashboard (T-8xx)

- [ ] **T-801** Create dashboard page (for admin only)
- [ ] **T-802** Implement total documents reviewed (count)
- [ ] **T-803** Implement average quality score (with 7-day trend)
- [ ] **T-804** Implement critical findings count (how many documents with 1+ critical issue)
- [ ] **T-805** Implement recent reviews widget (last 10 reviews: doc name, score, date)
- [ ] **T-806** Implement most common issues widget (top 5 finding types across all reviews)
- [ ] **T-807** Implement quality score distribution (histogram: 0-20, 20-40, ..., 80-100)
- [ ] **T-808** Add date range filter (last 7 days, 30 days, 90 days, custom)
- [ ] **T-809** Test dashboard with sample data

---

# WEEK 11-12: Testing & QA

## Epic: Unit Tests (T-9xx)

- [ ] **T-901** Unit tests for all database models (CRUD operations)
- [ ] **T-902** Unit tests for authentication (valid login, invalid creds, token refresh)
- [ ] **T-903** Unit tests for document parsing (DOCX, PDF)
- [ ] **T-904** Unit tests for each agent (mock Claude API, verify output schema)
- [ ] **T-905** Unit tests for rule engine (all 20 rules)
- [ ] **T-906** Unit tests for scoring logic (edge cases: all critical issues, all info)
- [ ] **T-907** Unit tests for report generation (PDF structure)
- [ ] **T-908** Target: ≥80% code coverage

## Epic: Integration Tests (T-9xx cont.)

- [ ] **T-909** Integration test: upload SOW → trigger review → get findings
- [ ] **T-910** Integration test: multi-document workflow (upload 3 SOWs, review all)
- [ ] **T-911** Integration test: API auth flow (login → token → request → logout)
- [ ] **T-912** Integration test: S3 upload/download
- [ ] **T-913** Integration test: report PDF generation

## Epic: QA & Test Data (T-9xx cont.)

- [ ] **T-914** Prepare test SOW dataset (30 real SOWs with known issues)
- [ ] **T-915** Prepare ground truth (for each SOW, list expected findings)
- [ ] **T-916** Run accuracy test (agents find ≥80% of expected findings)
- [ ] **T-917** Run performance test (average review time <30 seconds)
- [ ] **T-918** Run load test (simulate 10 concurrent reviews)
- [ ] **T-919** Manual UAT with stakeholders
- [ ] **T-920** Create bug tracking and triage process

## Epic: Security Testing (T-9xx cont.)

- [ ] **T-921** Penetration test (or code review) for auth bypass
- [ ] **T-922** Test SQL injection in search queries
- [ ] **T-923** Test CSRF protection
- [ ] **T-924** Test data isolation between orgs (user from org A cannot see org B data)
- [ ] **T-925** Test audit logging (all actions logged with user + timestamp)
- [ ] **T-926** Test password reset security (token expiry, single-use)

---

# WEEK 12-14: Deployment & Production

## Epic: Infrastructure & DevOps (T-10xx)

- [ ] **T-1001** Create Dockerfile for FastAPI app
- [ ] **T-1002** Create Dockerfile for Next.js app
- [ ] **T-1003** Create docker-compose.prod.yml (PostgreSQL, Redis, Nginx, apps)
- [ ] **T-1004** Set up Nginx reverse proxy (route /api to FastAPI, / to Next.js)
- [ ] **T-1005** Create SSL certificate (Let's Encrypt)
- [ ] **T-1006** Implement environment-based configuration (dev, staging, prod)
- [ ] **T-1007** Create deployment script (one-command deploy to staging/prod)
- [ ] **T-1008** Set up monitoring (basic: uptime, error rate, response time)
- [ ] **T-1009** Set up log aggregation (centralized logs for debugging)
- [ ] **T-1010** Create database backup strategy (daily automated backups)
- [ ] **T-1011** Document infrastructure diagram

## Epic: Production Hardening (T-10xx cont.)

- [ ] **T-1012** Enable HTTPS everywhere
- [ ] **T-1013** Implement rate limiting (per IP, per user)
- [ ] **T-1014** Implement request logging (all requests, response time)
- [ ] **T-1015** Implement error handling (no stack traces to users)
- [ ] **T-1016** Implement data encryption (at rest: S3 encryption, in transit: HTTPS)
- [ ] **T-1017** Implement secrets management (.env not in git, use env vars)
- [ ] **T-1018** Enable CORS (allow only expected origins)
- [ ] **T-1019** Implement health check endpoints (/health)
- [ ] **T-1020** Create incident response runbook

## Epic: Documentation (T-10xx cont.)

- [ ] **T-1021** Create deployment runbook (step-by-step deploy process)
- [ ] **T-1022** Create API documentation (OpenAPI/Swagger)
- [ ] **T-1023** Create user guide (how to upload, interpret results)
- [ ] **T-1024** Create admin guide (manage users, organizations)
- [ ] **T-1025** Create developer guide (how to run locally, add new agents)
- [ ] **T-1026** Create troubleshooting guide (common issues + fixes)
- [ ] **T-1027** Document all configuration options

## Epic: Launch (T-10xx cont.)

- [ ] **T-1028** Deploy to staging environment
- [ ] **T-1029** Run full end-to-end test in staging
- [ ] **T-1030** Get sign-off from stakeholders
- [ ] **T-1031** Deploy to production
- [ ] **T-1032** Monitor production for 24 hours
- [ ] **T-1033** Publish release notes
- [ ] **T-1034** Announce to users
- [ ] **T-1035** Collect initial feedback

---

## Task Dependencies & Critical Path

**Critical Path (must finish these first):**
1. T-201 → T-220 (Database schema)
2. T-301 → T-320 (Document parsing)
3. T-401 → T-453 (Agent orchestration)
4. T-501 → T-512 (Rule engine)
5. T-601 → T-619 (Scoring & reporting)
6. T-701 → T-720 (Frontend)

**Can run in parallel:**
- T-1xx (Auth) ↔ T-2xx (Database)
- T-4xx (Agents) ↔ T-5xx (Rules) — separate concerns
- T-7xx (Frontend) ↔ T-4xx-6xx (Backend) — via API mocking

**Must complete before launch:**
- T-901 → T-926 (All tests)
- T-1001 → T-1027 (Deployment & docs)

---

## Tracking Progress

Create a spreadsheet or Jira board:
- **Status:** Not Started | In Progress | Review | Done
- **Owner:** (person responsible)
- **Start Date:** (actual)
- **End Date:** (actual vs planned)
- **Blockers:** (if any)

Weekly review: Mark completed tasks, adjust timeline, surface blockers.

---

## Success Criteria (Task-Level)

Each task is done when:
1. Code is written & committed
2. Unit/integration tests pass (if applicable)
3. Code review approved
4. No regressions introduced
5. Documentation updated

Do not proceed to next task until previous task is "Done."

---

## Notes

- **No task should take >1 week.** If it does, break it down further.
- **Test as you go.** Don't leave testing for the end.
- **Document as you build.** Don't document after launch.
- **Deploy often.** Merge to main → deploy to staging weekly.
- **Communicate blockers early.** Don't wait until you're stuck.

