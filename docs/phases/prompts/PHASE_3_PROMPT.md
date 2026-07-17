# EDGP Phase 3: Performance, Scale & Mobile

**Target Duration**: 2-3 days  
**Total Tasks**: 100 (T-3001-T-3100)  
**Agents**: Sonnet5 (primary implementation) + Haiku (research/verification)  
**Status**: Ready to start after Phase 2  

---

## 📋 Phase 3 Objectives

Phase 2 (100 tasks) delivered advanced features. Phase 3 adds:

1. **Performance Optimization** (T-3001-T-3020) - Database, caching, queries
2. **Scalability & Infrastructure** (T-3021-T-3040) - **Scope cut (2026-07-17)**: no real traffic to justify most of this yet. Keep: Celery queue (built), rate limiting/circuit breaker (built), backup automation (safety-critical, never defer), basic Prometheus metrics (T-3036). Defer: read replicas (T-3021), table partitioning (T-3023), K8s ingress/autoscaling/sticky sessions (T-3031-3035), ELK distributed logging (T-3038), distributed tracing/OpenTelemetry (T-3030) — add when load data actually says you need them
3. **Mobile App (iOS/Android)** (T-3041-T-3060) - React Native cross-platform — **DEFERRED**, see note below
4. **Progressive Web App** (T-3061-T-3075) - Offline support, installable
5. **Accessibility (bare minimum)** (T-3076-T-3085, T-3096) - keyboard nav, ARIA, contrast, focus; i18n dropped, no compliance/localization need today

---

## 🎯 Task Breakdown by Category

### **T-3001-T-3020: Performance Optimization (20 tasks)**

#### T-3001-T-3005: Database Performance
- **T-3001**: Query optimization (add missing indexes, analyze slow queries)
- **T-3002**: Connection pooling tuning (adjust pool size, recycle time)
- **T-3003**: N+1 query elimination (eager loading with SQLAlchemy relationships)
- **T-3004**: Database statistics & VACUUM (maintenance jobs)
- **T-3005**: Query result caching (Redis cache layer for expensive queries)

#### T-3006-T-3010: API Response Optimization
- **T-3006**: Pagination implementation (cursor-based, offset-based)
- **T-3007**: Response compression (gzip, brotli)
- **T-3008**: API response time monitoring (add timing headers)
- **T-3009**: Lazy loading for nested resources (load on demand)
- **T-3010**: Batch API endpoints (GET /search?docs=id1,id2,id3)

#### T-3011-T-3015: Frontend Performance
- **T-3011**: Code splitting (lazy load routes with Next.js dynamic import)
- **T-3012**: Image optimization (next/image, WebP format, responsive)
- **T-3013**: JavaScript bundle analysis (webpack-bundle-analyzer)
- **T-3014**: CSS optimization (purge unused, minify)
- **T-3015**: Font optimization (subset fonts, WOFF2, preload)

#### T-3016-T-3020: Caching Strategy
- **T-3016**: HTTP caching headers (Cache-Control, ETag)
- **T-3017**: Browser caching (Service Worker, IndexedDB)
- **T-3018**: CDN integration (CloudFront or Cloudflare)
- **T-3019**: Cache invalidation strategy (tag-based, TTL)
- **T-3020**: Cache metrics & monitoring (hit rate, eviction)

**Sonnet5 Tasks**: T-3001, T-3002, T-3003, T-3006, T-3007, T-3011, T-3016, T-3018  
**Haiku Tasks**: T-3004, T-3005, T-3008, T-3009, T-3010, T-3012, T-3013, T-3014, T-3015, T-3017, T-3019, T-3020

---

### **T-3021-T-3040: Scalability & Infrastructure (20 tasks) — mostly DEFERRED (2026-07-17)**

> No production traffic yet to justify replicas/partitioning/K8s autoscaling/tracing. Build these when metrics say you need them, not speculatively.

#### T-3021-T-3025: Database Scaling
- ~~T-3021: Read replicas setup~~ — **DEFERRED**, no read-load pressure yet
- **T-3022**: Write scaling with connection pooling (PgBouncer) — **Keep** (cheap, already using pooling)
- ~~T-3023: Table partitioning~~ — **DEFERRED**, revisit at real data volume
- ~~T-3024: Archival strategy~~ — **DEFERRED**
- **T-3025**: Backup & restore automation (daily snapshots to S3) — **Keep, safety-critical, never defer**

#### T-3026-T-3030: Application Scaling
- **T-3026**: Async task queue setup (Celery + Redis) — **Keep** (already built, Wave 2)
- **T-3027**: Background jobs (document parsing, PDF generation) — **Keep** (already built, Wave 2)
- **T-3028**: Rate limiting & throttling — **Keep** (already built, Wave 2)
- **T-3029**: Circuit breaker pattern — **Keep** (already built, Wave 2)
- ~~T-3030: Distributed tracing (OpenTelemetry, Jaeger)~~ — **DEFERRED**, add when debugging multi-service latency is an actual problem

#### T-3031-T-3035: Load Balancing — **all DEFERRED**
- ~~T-3031-T-3035~~ (K8s Ingress, LB health checks, sticky sessions, IP rate limiting, auto-scaling) — no multi-instance deployment yet to load-balance across

#### T-3036-T-3040: Monitoring & Observability
- **T-3036**: Prometheus metrics (request latency, error rates) — **Keep**, cheap and useful from day one
- ~~T-3037: Grafana dashboards~~ — **DEFERRED**, revisit once there's enough metric volume to warrant dashboards
- ~~T-3038: Distributed logging (ELK stack)~~ — **DEFERRED**, single-instance logs suffice for now
- **T-3039**: Error tracking & alerting (Sentry) — **Keep**, cheap and catches real bugs early
- ~~T-3040: Performance profiling~~ — **DEFERRED**, do this on-demand when a perf issue is reported, not as scheduled work

**Sonnet5 Tasks (kept)**: T-3022, T-3025, T-3026, T-3027, T-3036  
**Haiku Tasks (kept)**: T-3028, T-3029, T-3039

---

### **T-3041-T-3060: Mobile App (iOS/Android) (20 tasks) — DEFERRED (2026-07-17)**

> **Deferred to future improvement.** Doc review/approval workflow is desktop-first; PWA (T-3061-3075) covers offline + installable + mobile-browser use at a fraction of the cost. Revisit only if there's concrete demand for app-store presence or native push notifications. Skip these 20 tasks in this phase.

#### T-3041-T-3045: React Native Setup
- **T-3041**: React Native project scaffolding (Expo or bare workflow)
- **T-3042**: Platform-specific navigation (React Navigation)
- **T-3043**: Authentication flow (OAuth, JWT token refresh)
- **T-3044**: API client setup (Axios, retry logic)
- **T-3045**: Error handling & user feedback (Toast, alerts)

#### T-3046-T-3050: Core Features
- **T-3046**: Document upload (camera roll, file picker)
- **T-3047**: Document list & search (infinite scroll)
- **T-3048**: Review results display (scorecard, findings)
- **T-3049**: Push notifications (Firebase Cloud Messaging)
- **T-3050**: Offline mode (SQLite local database)

#### T-3051-T-3055: UI/UX Polish
- **T-3051**: Native UI components (platform-specific buttons, alerts)
- **T-3052**: Dark mode support (system preference)
- **T-3053**: Responsive layouts (tablet + phone)
- **T-3054**: Performance optimization (lazy rendering, virtualization)
- **T-3055**: App icon & splash screen (branded assets)

#### T-3056-T-3060: Release & Distribution
- **T-3056**: iOS app signing (certificates, provisioning profiles)
- **T-3057**: Android app signing (keystore, version codes)
- **T-3058**: App Store submission (metadata, screenshots)
- **T-3059**: Play Store submission (same)
- **T-3060**: Over-the-air updates (EAS Updates or CodePush)

**Sonnet5 Tasks**: T-3041, T-3042, T-3043, T-3046, T-3048, T-3051, T-3053, T-3056, T-3058  
**Haiku Tasks**: T-3044, T-3045, T-3047, T-3049, T-3050, T-3052, T-3054, T-3055, T-3057, T-3059, T-3060

---

### **T-3061-T-3075: Progressive Web App (15 tasks)**

#### T-3061-T-3065: PWA Fundamentals
- **T-3061**: manifest.json (icons, theme, display mode)
- **T-3062**: Service Worker registration (caching strategies)
- **T-3063**: Offline support (background sync)
- **T-3064**: Installability (install banner, Add to Home Screen)
- **T-3065**: Update notifications (new version available prompt)

#### T-3066-T-3070: Offline Functionality
- **T-3066**: IndexedDB setup (local data persistence)
- **T-3067**: Offline document list (cached from last sync)
- **T-3068**: Queue offline actions (upload when online)
- **T-3069**: Sync status indicator (online/offline badge)
- **T-3070**: Conflict resolution (manual or auto-merge)

#### T-3071-T-3075: PWA Distribution
- **T-3071**: HTTPS enforcement (all PWAs require HTTPS)
- **T-3072**: Web app store submission (Microsoft, Google)
- **T-3073**: Deep linking (open document from browser)
- **T-3074**: Share target API (share from other apps)
- **T-3075**: PWA analytics (installation rate, usage)

**Sonnet5 Tasks**: T-3061, T-3062, T-3063, T-3066, T-3067, T-3071, T-3073  
**Haiku Tasks**: T-3064, T-3065, T-3068, T-3069, T-3070, T-3072, T-3074, T-3075

---

### **T-3076-T-3085: Accessibility (bare minimum) (10 tasks) — i18n DROPPED (2026-07-17)**

> **Scope cut.** No compliance mandate and no non-English users today — full WCAG 2.1 audit (screen reader testing, formal certification) and i18n (translations, RTL, locale routing) are not worth the cost. Keep only the free/cheap wins that shadcn + semantic markup mostly give you already. Revisit full a11y/i18n if a real compliance or localization requirement shows up.

- **T-3076**: Semantic HTML (proper heading hierarchy, alt text)
- **T-3077**: Keyboard navigation (Tab, Enter, Esc)
- **T-3078**: Focus indicators (visible focus ring)
- **T-3079**: Color contrast (4.5:1 minimum)
- **T-3080**: ARIA labels (landmarks, live regions)
- **T-3082**: Form accessibility (labels, error messages, hints)
- **T-3083**: Modal dialogs (trap focus, restore on close)
- **T-3084**: Skip links (skip to main content)
- **T-3085**: Accessibility audit (Lighthouse, axe)
- **T-3096**: Accessibility unit tests (jest-axe)

**Sonnet5 Tasks**: T-3076, T-3077, T-3079, T-3082, T-3096  
**Haiku Tasks**: T-3078, T-3080, T-3083, T-3084, T-3085

---

## 🚀 Recommended Execution Order

### **Wave 1 (Days 1-2): Performance & Optimization**
Run in parallel:
- **Sonnet5**: T-3001, T-3002, T-3003, T-3006, T-3007, T-3011, T-3016
- **Haiku**: T-3004, T-3005, T-3008, T-3009, T-3010, T-3012, T-3013

### **Wave 2 (Days 2-3): Scaling & Infrastructure**
Run in parallel:
- **Sonnet5**: T-3021, T-3022, T-3026, T-3027, T-3031, T-3032, T-3036
- **Haiku**: T-3023, T-3024, T-3025, T-3028, T-3029, T-3033, T-3034, T-3037

### **Wave 3 (Days 3+): PWA & Accessibility**
Run in parallel:
- **Sonnet5**: T-3061, T-3062, T-3076, T-3077
- **Haiku**: T-3063, T-3064, T-3078, T-3080

---

## 📁 Phase 3 Codebase Structure

```
apps/api/
├── app/
│   ├── performance/
│   │   ├── indexing.py        # T-3001: Index optimization
│   │   ├── caching.py         # T-3005: Redis caching layer
│   │   └── monitoring.py      # T-3036: Prometheus metrics
│   ├── scaling/
│   │   ├── replication.py     # T-3021: Read replicas
│   │   ├── partitioning.py    # T-3023: Table partitioning
│   │   └── tasks.py           # T-3026: Celery tasks
│   └── routers/
│       ├── batch.py           # T-3010: Batch endpoints
│       └── async_tasks.py     # T-3027: Background job endpoints
│
apps/mobile/                    # NEW: React Native app
├── src/
│   ├── screens/
│   │   ├── LoginScreen.tsx    # T-3043: Auth
│   │   ├── DocumentListScreen.tsx  # T-3047: List
│   │   └── ResultsScreen.tsx  # T-3048: Results
│   ├── components/
│   │   ├── DocumentUpload.tsx # T-3046: Upload
│   │   └── PushNotifications.tsx  # T-3049: Push
│   ├── services/
│   │   ├── api.ts            # T-3044: API client
│   │   └── offlineSync.ts    # T-3050: Offline
│   └── app.json              # T-3055: Config
│
apps/web/
├── app/
│   └── _offline/             # T-3068: Offline pages
├── public/
│   └── manifest.json         # T-3061: PWA manifest
├── service-worker.ts         # T-3062: Service Worker
├── i18n/
│   ├── en.json              # T-3087: English
│   ├── es.json              # T-3087: Spanish
│   ├── fr.json              # T-3087: French
│   └── config.ts            # T-3086: i18n setup
└── middleware.ts             # T-3094: URL-based routing
```

---

## 💾 Database Schema Additions

### Performance Improvements:
```sql
-- T-3001: Add strategic indexes
CREATE INDEX CONCURRENTLY idx_documents_org_created ON documents(org_id, created_at DESC);
CREATE INDEX CONCURRENTLY idx_findings_severity ON findings(severity, org_id);
CREATE INDEX CONCURRENTLY idx_reviews_completed_at ON reviews(completed_at DESC);

-- T-3023: Partition audit logs by month
CREATE TABLE audit_logs_2026_01 PARTITION OF audit_logs
  FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

-- T-3025: Backup tracking
CREATE TABLE backup_metadata (
  backup_id UUID PRIMARY KEY,
  backup_date TIMESTAMP,
  backup_location TEXT,
  size_bytes BIGINT,
  status VARCHAR(50)
);
```

---

## 🧪 Testing Requirements

### Performance Tests:
- Load test: 1000 concurrent users
- Database: 100k+ documents, 500k+ findings
- API response: < 200ms p50, < 1000ms p99
- Frontend: Lighthouse score > 90

### Mobile Tests:
- iOS app: iPhone 12 Mini, iPhone 14 Pro Max
- Android: Pixel 6, Samsung Galaxy S22
- Offline mode: works without network
- OTA updates: seamless

### Accessibility Tests:
- Keyboard: navigate entire app with Tab/Enter
- Screen reader: all content accessible (NVDA/JAWS)
- Color: 4.5:1 contrast on all text
- Mobile: pinch-zoom works, text resize

### i18n Tests:
- All languages render correctly
- RTL layouts work properly
- Dates/times format by locale
- Translation completeness > 95% per language

---

## 📊 Phase 3 Statistics

- **Tasks**: 100 (T-3001-T-3100)
- **Estimated Duration**: 2-3 days (Sonnet5 + Haiku parallel)
- **Code Lines**: ~12,000 (backend optimization + mobile + PWA)
- **API Endpoints**: 10+ (new, optimized)
- **Database Changes**: 15+ (indexes, partitions)
- **Mobile App**: 100% feature parity with web
- **Languages Supported**: 6+ (EN, ES, FR, DE, JA, ZH)
- **Tests**: 60+ (performance + accessibility + i18n)
- **Git Commits**: 15-20 (incremental)

---

## 🔌 External Dependencies

### Phase 3 integrations:
- **Mobile**: Expo or bare React Native
- **Mobile Push**: Firebase Cloud Messaging (FCM)
- **Offline**: SQLite (React Native), IndexedDB (PWA)
- **Observability**: OpenTelemetry, Jaeger, Prometheus
- **i18n**: react-i18next, next-i18next
- **Accessibility**: jest-axe, axe-core
- **Database**: PostgreSQL replication, PgBouncer
- **Task Queue**: Celery, Redis

---

## ⚠️ Known Constraints

1. **Database Replication**: Primary must stay in sync with replicas
2. **Mobile Offline**: SQLite has 10MB data limit (compression required)
3. **PWA Cache**: Service Worker cache versioning critical
4. **i18n Performance**: Large translation bundles slow bundle size
5. **Accessibility**: Some components need ARIA, not all covered by defaults
6. **React Native**: Platform differences (iOS ≠ Android)

---

## 🎯 Success Criteria

### Phase 3 is complete when:
✅ All 100 tasks have production code + tests  
✅ Lighthouse score: 90+ (all categories)  
✅ Mobile app: iOS + Android builds released  
✅ PWA: installable, works offline  
✅ i18n: 6+ languages fully translated  
✅ Accessibility: WCAG 2.1 AA certified  
✅ Performance: < 200ms p50 API latency  
✅ Load test: 1000 concurrent users, no errors  
✅ Code coverage: > 80% (new + existing)  
✅ All tests passing (unit + integration + E2E)  
✅ Security scanning passes (Trivy, Bandit)  
✅ Documentation complete  

---

## 🚀 Getting Started

### Pre-Phase 3 Checklist:
- [ ] Phase 1 complete (90%)
- [ ] Phase 2 complete (100%)
- [ ] Review PHASE_2_SUMMARY.md
- [ ] Set up React Native environment
- [ ] Prepare i18n translation files
- [ ] Plan mobile feature parity matrix

### Launch Commands:
```bash
# Performance analysis
pytest tests/performance -v --benchmark

# Mobile setup
cd apps/mobile
npm install
npm start

# PWA service worker
npm run build:web

# i18n extraction
npm run i18n:extract
```

---

## 📞 Phase 2 Context

**Key Files from Phase 2**:
- `apps/api/app/analytics/` - Analytics foundation
- `apps/api/app/collab/` - Collaboration features
- `apps/web/app/(admin)/` - Admin templates
- `.github/workflows/ci-cd.yml` - CI/CD pipeline

**Database**: PostgreSQL 16 with 15+ tables
**Frontend**: Next.js 14 with TypeScript
**Backend**: FastAPI with async SQLAlchemy

---

## 💡 Prompt Template for Agents

### For Sonnet5:
```
Implement Phase 3 Performance Tasks (T-3001-T-3020):

Core: Database query optimization, caching, pagination
- Add strategic indexes to hot tables
- Implement Redis caching for expensive queries
- Add pagination to all list endpoints
- Profile & optimize slow queries

Report: Performance benchmarks (queries < 50ms)
Include: Tests, monitoring metrics
```

### For Haiku:
```
Research & verify Phase 3 Performance (T-3001-T-3020):

Research:
- Best practices for PostgreSQL indexing
- Redis caching strategies
- API pagination patterns
- Performance monitoring tools

Report: Architecture decisions for Phase 3
```

---

**Phase 1 Status**: ✅ Done (90%)  
**Phase 2 Status**: 📋 Ready (100 tasks)  
**Phase 3 Status**: 🚀 Ready (100 tasks, ready now)  

**Total Project**: 300 tasks across 3 phases  
**Total Duration**: 7-9 days (all phases)

Ready to launch Phase 3? 🚀
