# Phase 1 MVP Scope - Enterprise SOW Review Platform

**Objective:** Launch a production-ready SOW review engine in 12-16 weeks with core functionality only.

**Tagline:** "Every SOW risk, caught before signature."

---

## What We WILL Build

### 1. Core Features (Week 1-16)

#### Authentication & Identity (Week 1-2)
- Microsoft Entra ID (Azure AD) integration
- Local login fallback (email/password)
- Basic RBAC (Admin, Reviewer, Viewer)
- JWT token management
- MFA optional (add in Phase 2)

#### Document Management (Week 2-3)
- Upload single DOCX or PDF SOW
- Auto-detect document type (validate it's actually a SOW)
- Store with version 1.0
- Search by filename or content
- No folder structure (single flat library for MVP)

#### AI Review Engine (Week 4-7)
**5 Specialized Agents Only (not 11)**

1. **Scope Reviewer**
   - Extracts: Deliverables, acceptance criteria, scope boundaries
   - Detects: Ambiguous language, incomplete definitions, scope creep risks
   
2. **Delivery Reviewer**
   - Extracts: Timeline, milestones, dependencies, assumptions
   - Detects: Missing dates, unrealistic schedules, undefined dependencies
   
3. **Commercial Reviewer**
   - Extracts: Pricing, payment terms, pricing conditions
   - Detects: Ambiguous pricing, missing escalation clauses, unclear payment triggers
   
4. **Security & Compliance Reviewer**
   - Extracts: Security requirements, compliance mandates, data handling clauses
   - Detects: Missing security clauses, compliance gaps, audit obligations
   
5. **Project Operations Reviewer**
   - Extracts: RACI, escalation paths, governance, resource requirements
   - Detects: Unclear ownership, missing escalation criteria, undefined roles

**Agent Outputs (Structured)**
- Field extractions (JSON)
- Findings (with evidence, severity, recommendation)
- Confidence score (0-100)
- No free-form text

#### Rule Engine (Week 7-8)
**Configuration-Driven, No Code Required**

Built-in rules (configurable):
- Every SOW must have acceptance criteria
- Every SOW must have a timeline
- Every SOW must have RACI matrix
- Every SOW >$100K must have delay clauses
- Every SOW must define what "out of scope" means

Rule format (JSON-based, no hardcoding):
```json
{
  "rule_id": "sow-001",
  "name": "SOW must have acceptance criteria",
  "document_type": "SOW",
  "severity": "critical",
  "check_type": "section_presence",
  "required_sections": ["Acceptance Criteria"],
  "message": "Acceptance criteria define how success is measured. Missing definition creates delivery risk."
}
```

#### Scoring Model (Week 8)
**0-100 Overall Score**

Categories (equally weighted):
- Completeness (all required sections present)
- Clarity (language ambiguity scan)
- Consistency (internal contradictions)
- Commercial (pricing/payment clarity)
- Delivery (timeline/milestone definition)
- Operations (RACI/governance clarity)
- Security (compliance requirement coverage)

Risk Scoring:
- **Critical** (70-100 points impact) → Red
- **Major** (30-69 points) → Orange
- **Medium** (10-29 points) → Yellow
- **Low** (0-9 points) → Blue
- **Info** (documentation) → Gray

#### Report Generation (Week 9)
**Static PDF + Web Viewer**

Report includes:
- Executive summary (1 page)
- Quality scorecard (7 categories, 0-100 each)
- Risk heatmap (visual by severity)
- Detailed findings (50 max per report)
- Recommended sections to add/clarify
- Evidence snippets (quoted text from SOW)
- PDF export with logo/branding

No Word export in MVP.

#### Dashboard - Basic (Week 10)
Admin/Reviewer view only:
- Total SOWs reviewed (count)
- Average quality score (trend line)
- Critical findings count
- Recent reviews (list)
- Most common issues (top 5)

No team analytics in Phase 1.

### 2. Technology Stack

**Frontend**
- Next.js 14 (TypeScript)
- Tailwind CSS + shadcn/ui
- React Hook Form (form handling)
- PDF rendering: react-pdf
- Chart.js for scoring visualization

**Backend**
- FastAPI (Python)
- PostgreSQL 16 (single database, no sharding)
- Redis 7 (caching + queues)
- Celery (async task processing for AI)
- Python-pptx for PDF generation (reportlab)

**AI**
- Claude 3.5 Sonnet (primary model)
- OpenAI GPT-4 Turbo (fallback, optional)
- No local models in MVP

**Document Processing**
- pypdf (PDF text extraction)
- python-docx (DOCX parsing)
- No OCR needed in Phase 1 (assume digital SOWs)

**Storage**
- S3 or Azure Blob (document versions)
- PostgreSQL (metadata, findings, audit logs)

**Infrastructure**
- Docker + Docker Compose (local dev)
- Single EC2/VM for MVP (t3.large, 2-4 CPU, 8GB RAM)
- Nginx (reverse proxy)
- No Kubernetes in Phase 1

---

## What We WON'T Build (Removed from Phase 1)

❌ **Not in Phase 1**
- Multiple document type analysis (Proposal, Project Plan, HLD, etc.)
- Cross-document validation
- Clause library / knowledge base
- Custom rule builder (UI)
- Workflow approvals / change tracking
- Version comparison
- Collaboration comments
- AI-powered rewriting
- Dashboard team analytics
- Enterprise SSO (Okta, etc.)
- Advanced search / full-text index
- Document fingerprinting / dedup
- Any ML/training on user data

---

## API Surface (Minimal)

```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me

POST   /api/v1/documents/upload
GET    /api/v1/documents
GET    /api/v1/documents/{id}
DELETE /api/v1/documents/{id}

POST   /api/v1/reviews (trigger async review)
GET    /api/v1/reviews/{id}
GET    /api/v1/reviews/{id}/report

GET    /api/v1/dashboard/stats
```

**No GraphQL.** No WebSockets. Polling only for async status.

---

## Database Tables (Minimal Set)

- `organizations` (org_id, name, subscription_tier)
- `users` (user_id, org_id, email, role, mfa_enabled)
- `documents` (doc_id, org_id, user_id, filename, upload_date, s3_path, version)
- `reviews` (review_id, doc_id, status, started_at, completed_at, overall_score)
- `findings` (finding_id, review_id, agent, severity, section, evidence, confidence)
- `audit_logs` (log_id, org_id, user_id, action, timestamp, details)

No relationships tables. No versioning complexity. No change history in Phase 1.

---

## Deployment Targets

- **Single-tenant MVP:** Own VM or small container
- **Optional:** Heroku for demo (not production)
- **Future:** Multi-tenant SaaS on Kubernetes

---

## Success Criteria for Phase 1 Launch

1. **Accuracy:** ≥92% precision on test SOW set (no false positives on real issues)
2. **Coverage:** Identifies ≥80% of known risk patterns in test SOWs
3. **Speed:** Review completes in <30 seconds for average 10-page SOW
4. **Reliability:** 99.5% uptime on production
5. **UI:** Can upload, analyze, export report in <2 minutes
6. **Security:** No data leakage, audit logs functional

---

## Out of Scope (Explicitly)

- Mobile app
- Offline mode
- Real-time collaboration
- Advanced analytics
- Machine learning on review data
- Custom model fine-tuning
- Integration with JIRA/ServiceNow
- Workflow automation
- Contract templates
- Clause suggestions
- Competitive analysis

These features are **Phase 2+**.

---

## Development Phases (16-Week Timeline)

| Week | Focus | Deliverable |
|------|-------|-------------|
| 1-2 | Auth, DB schema, API scaffolding | /api/v1/auth endpoints live |
| 2-3 | Document upload & parsing | Upload UI, S3 integration |
| 4-5 | Scope & Delivery agents | Agent prompts finalized, local testing |
| 5-6 | Commercial & Security agents | All 5 agents in test mode |
| 6-7 | Operations agent & rule engine | Rule JSON schema defined |
| 7-8 | Scoring & report generation | PDF export working |
| 8-9 | Web UI for review results | Interactive findings viewer |
| 9-10 | Dashboard (basic stats) | Admin dashboard live |
| 10-12 | Integration testing & bug fixes | End-to-end flow tested |
| 12-14 | Security audit & hardening | Pen test if possible |
| 14-16 | Load testing & production prep | Deploy to staging |

---

## Team & Estimated Effort

**Minimum:** 3 people, 12 weeks
- 1 Backend Lead (FastAPI, LLM integration, DB)
- 1 Frontend Lead (Next.js, UI/UX)
- 1 DevOps/QA (Infrastructure, testing, security)

**Ideal:** 4 people, 10 weeks
- Add: 1 AI/Prompt Engineer (agent tuning, confidence scoring)

---

## Launch Readiness Checklist

- [ ] Phase 1 scope document signed off (this doc)
- [ ] MASTER_TASKS.md created with atomic tasks
- [ ] Database schema designed & reviewed
- [ ] AI agent specs finalized (prompts, outputs)
- [ ] Test SOW dataset prepared (30+ real SOWs)
- [ ] Success metrics defined & measurable
- [ ] Security review completed
- [ ] Deployment runbook written
- [ ] User docs drafted
- [ ] Stakeholder sign-off on features

---

## Guiding Principle for Phase 1

**"Do one thing perfectly, not ten things badly."**

- Perfect SOW review
- Perfect risk detection
- Perfect audit trail
- Perfect data security

Everything else waits for Phase 2.
