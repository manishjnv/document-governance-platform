# Phase 1 Launch Criteria & Success Metrics

**Launch Gate:** All metrics must pass before production release.
**Test Date:** 1 week before planned production launch.
**Stakeholder Sign-off:** Required before proceeding to production.

> **Scope update (2026-07-17):** Two spec'd-but-unbuilt agents (PMOReviewer) and net-new additions (LegalReviewer, ambiguous-language scan, RFP document-type support — see `4_AI_AGENT_SPECS.md`) are being added ahead of launch to cover legal/financial/functional/scope/entry-exit/fallback-plan review, which is the core value proposition (reduce manual SOW/RFP review) — this is a prerequisite for launch, not a post-launch add-on. Each addition must independently pass Metrics 1.1-1.4 below (precision ≥92%, recall ≥80%, calibration <5% error, dedup ≥99%) on its own test set before it counts toward "launch ready" — a 6th/7th agent that hallucinates findings actively erodes trust in the tool. RFP test set: minimum 10 real/representative RFPs, evaluated the same way as the existing 20-SOW set. Do not assume an addition is accurate because SOW review already passed the bar; test each new agent and the RFP rule set independently.

---

## Category 1: AI Agent Accuracy

### Metric 1.1: Precision (No False Positives)

**Definition:** Of all findings reported by agents, what % are actually real issues?

**Measurement Method:**
1. Select 20 SOWs from test set (mixed quality)
2. Run full review on each SOW
3. For each finding, manually verify:
   - [ ] Finding is accurate (reflects real issue in document)
   - [ ] Evidence text is correctly quoted
   - [ ] Recommendation is reasonable
4. Calculate: (Correct Findings) / (Total Findings)

**Success Criteria:**
- **Target:** ≥92% precision
- **Acceptable:** 90-92% (minor false positives acceptable)
- **Failure:** <90% (too many false positives)

**Example:**
- SOW1 generated 10 findings
- Manual review: 9 are valid, 1 is false positive
- Precision: 9/10 = 90% ✓

### Metric 1.2: Recall (Find Real Issues)

**Definition:** Of all real issues in an SOW, what % does the system find?

**Measurement Method:**
1. Select same 20 SOWs used for precision
2. Manually create ground truth (list all real issues in each SOW)
   - Critical issues (must find all)
   - Major issues (should find 80%+)
   - Medium/Low issues (70%+)
3. Run system review on each
4. Compare system findings to ground truth
5. Calculate: (System Found) / (Ground Truth Total)

**Success Criteria:**
- **Critical issues:** ≥95% recall
- **Major issues:** ≥80% recall
- **Medium/Low:** ≥70% recall
- **Overall:** ≥80% recall

**Example:**
- Ground truth for SOW1: 15 real issues (3 critical, 5 major, 7 medium)
- System found: 2 critical, 4 major, 5 medium = 11/15 issues
- Recall: 11/15 = 73% (fails if target is 80%)

### Metric 1.3: Confidence Score Calibration

**Definition:** When system reports 90% confidence, is the finding actually ~90% likely correct?

**Measurement Method:**
1. Collect all findings from Metric 1.2 test (20 SOWs)
2. Group by confidence ranges: [80-89], [90-94], [95-99], [100]
3. For each group, calculate actual precision
   - Group [90-94]: 45/50 correct = 90% actual precision ✓
   - Group [95-99]: 98/100 correct = 98% actual precision ✓
4. Check for calibration (reported ≈ actual)

**Success Criteria:**
- **Calibration error:** <5% deviation
- All confidence groups accurate within ±5%

**Example:**
- High confidence findings [95-99]: reported 97% confidence
- Actual precision: 95% (98% reported vs 95% actual = 3% error) ✓
- Low confidence findings [80-89]: reported 85% confidence
- Actual precision: 83% (85% reported vs 83% actual = 2% error) ✓

### Metric 1.4: Finding Deduplication

**Definition:** Are duplicate findings (same issue from multiple agents) correctly merged?

**Measurement Method:**
1. Identify SOWs where multiple agents report the same issue
2. Verify deduplication worked:
   - [ ] Issue appears only once in findings list
   - [ ] Evidence from both agents is combined
   - [ ] Higher confidence is used
3. Count false de-duplications (incorrectly merged different issues)

**Success Criteria:**
- **Deduplication accuracy:** ≥99%
- **False merges:** 0
- **Missed merges:** <1%

---

## Category 2: Performance & Scalability

### Metric 2.1: Review Completion Time

**Definition:** Average time from "start review" to "results ready."

**Measurement Method:**
1. Batch test: 100 SOWs (mix of sizes: 5 pages to 50 pages)
2. Record start_timestamp and completed_timestamp
3. Calculate duration for each
4. Report: mean, median, p95, p99

**Success Criteria:**
- **Mean:** ≤25 seconds
- **Median:** ≤22 seconds
- **P95:** ≤35 seconds
- **P99:** ≤45 seconds

**Example:**
- 100 SOWs reviewed
- Mean: 21 seconds ✓
- P95: 32 seconds ✓
- P99: 40 seconds ✓

### Metric 2.2: Document Upload Speed

**Definition:** Time to upload and parse a document.

**Measurement Method:**
1. Test 50 documents (various sizes: 1MB to 50MB, DOCX and PDF)
2. Record upload + parse time
3. Report: mean, max

**Success Criteria:**
- **Mean:** ≤5 seconds
- **Max:** ≤15 seconds (even for 50MB files)

### Metric 2.3: Concurrent Review Capacity

**Definition:** How many reviews can run simultaneously?

**Measurement Method:**
1. Start 10 concurrent reviews (10 SOWs at same time)
2. Monitor:
   - [ ] All 10 complete successfully (no failures)
   - [ ] Response times don't degrade significantly
   - [ ] Database/API doesn't crash
3. Repeat with 20 concurrent (if infrastructure allows)

**Success Criteria:**
- **10 concurrent:** All complete within 2x normal time
- **20 concurrent:** Optional (nice to have)
- **0 failures:** No errors under load

### Metric 2.4: Memory & CPU Usage

**Definition:** Resource utilization during review processing.

**Measurement Method:**
1. Run full test suite (100 SOWs over 2 hours)
2. Monitor:
   - Peak memory usage
   - Average CPU usage
   - Database connections (max)
3. Check for memory leaks (memory should stabilize)

**Success Criteria:**
- **Memory:** <2GB peak (API + worker)
- **CPU:** <70% average
- **DB connections:** <20 max (pool size)

---

## Category 3: Functional Completeness

### Metric 3.1: All Core Features Implemented

**Definition:** MVP feature checklist.

**Measurement Method:**
Test checklist (manual):

```
Authentication
  [ ] Login with email/password works
  [ ] JWT token issued and valid
  [ ] Token refresh works
  [ ] Logout clears session
  [ ] Azure AD login works (optional)

Document Management
  [ ] Upload DOCX file
  [ ] Upload PDF file
  [ ] List uploaded documents
  [ ] Document metadata displays correctly
  [ ] File size limits enforced (max 50MB)
  [ ] Delete document works (soft delete)

Review Engine
  [ ] Review starts on click
  [ ] All 6 agents run (Scope, Delivery, Commercial, Security, PMO, Legal) + ambiguous-language scan
  [ ] RFP document type reviews correctly (distinct rule set + agent branches from SOW)
  [ ] Findings generated and stored
  [ ] Scores calculated (7 categories + overall)
  [ ] Risk score calculated
  [ ] Status updates (pending → running → completed)

Report Generation
  [ ] PDF report generated
  [ ] Executive summary included
  [ ] Scorecard displays all 7 categories
  [ ] Risk heatmap visual generated
  [ ] Findings table accurate
  [ ] Evidence snippets included
  [ ] Recommendations included
  [ ] PDF download works

UI/UX
  [ ] Login page displays and works
  [ ] Dashboard loads
  [ ] Upload page functional
  [ ] Document list displays
  [ ] Results page shows findings
  [ ] Responsive design (mobile/tablet/desktop)
  [ ] No console errors
  [ ] Loading states display

Admin Functions
  [ ] Create organization
  [ ] Create user
  [ ] Assign user to org
  [ ] Set user role (admin/reviewer/viewer)
  [ ] View dashboard stats
```

**Success Criteria:**
- ≥95% of checkboxes checked
- All critical features (bolded) must pass
- No show-stopper bugs

### Metric 3.2: Error Handling

**Definition:** Graceful handling of failures.

**Measurement Method:**
Test scenarios:

```
Network Failures
  [ ] API timeout → show "review timed out, try again" message
  [ ] S3 upload fails → show error, allow retry
  [ ] Claude API unavailable → show error, log for support

Validation Failures
  [ ] Upload non-PDF/DOCX file → reject with clear message
  [ ] File >50MB → reject with size limit message
  [ ] Corrupted PDF → skip parsing, alert user
  [ ] No org_id in JWT → 401 error

Edge Cases
  [ ] Review SOW with 0 pages → handle gracefully
  [ ] Review SOW with 500 pages → process (or warn if too large)
  [ ] Agent returns invalid JSON → retry, then fail gracefully
  [ ] Agent timeout (30s) → continue with other agents
  [ ] Database connection lost → show "server error" page
```

**Success Criteria:**
- All scenarios handled gracefully
- No 500 errors without logging/alerting
- User sees clear error messages

### Metric 3.3: Data Integrity

**Definition:** Data is correctly stored and retrievable.

**Measurement Method:**

```
  [ ] Review data matches report output
  [ ] Findings count matches database
  [ ] Scores calculated consistently
  [ ] Audit logs record all actions
  [ ] Soft deletes work (deleted items don't appear in lists)
  [ ] Org isolation: user A cannot see org B data
  [ ] Multiple reviews of same doc don't conflict
```

**Success Criteria:**
- All checks pass
- 100% data integrity (no lost/corrupted data)

---

## Category 4: Security

### Metric 4.1: Authentication & Authorization

**Definition:** Only authorized users can access their data.

**Measurement Method:**

```
  [ ] Non-authenticated user cannot access /api endpoints (401)
  [ ] Expired JWT rejected (401)
  [ ] User can only access own org data (403 for org_id mismatch)
  [ ] Viewer role cannot delete documents (403)
  [ ] Admin role can create users
  [ ] Rate limiting on login (5 failures → 15min lockout)
  [ ] Password hashed with bcrypt (not plaintext)
  [ ] Password reset token expires after 1 hour
  [ ] CORS configured (only allow expected origins)
```

**Success Criteria:**
- All checks pass
- No unauthorized access possible

### Metric 4.2: Data Privacy

**Definition:** User data is encrypted and not exposed.

**Measurement Method:**

```
  [ ] Passwords never logged
  [ ] SOW content not used for model training (Claude no-data-retention)
  [ ] S3 encryption enabled (at rest)
  [ ] HTTPS enforced (TLS 1.2+)
  [ ] Database credentials in environment variables (not hardcoded)
  [ ] Audit logs don't contain sensitive data
  [ ] API responses don't expose stack traces to clients
  [ ] Error messages generic (don't leak system info)
```

**Success Criteria:**
- All checks pass
- Pen test (if done) passes
- No data leakage findings

### Metric 4.3: Input Validation

**Definition:** All user inputs validated, no injection attacks.

**Measurement Method:**

```
  [ ] SQL injection: malicious SQL in search doesn't break query
  [ ] XSS: JavaScript in findings display as text, not executed
  [ ] File upload: no executable files allowed
  [ ] Filename: special characters sanitized in S3
  [ ] Email: valid format required
```

**Success Criteria:**
- All checks pass
- No injection vulnerabilities

---

## Category 5: Documentation & Operations

### Metric 5.1: Documentation Complete

**Definition:** All necessary documentation exists.

**Checklist:**

```
  [ ] API documentation (OpenAPI/Swagger, all endpoints)
  [ ] Database schema documentation (ERD, table descriptions)
  [ ] AI agent specifications (prompts, outputs, confidence)
  [ ] Deployment runbook (step-by-step instructions)
  [ ] User guide (how to upload, interpret results)
  [ ] Admin guide (manage users, orgs, rules)
  [ ] Developer guide (local setup, testing, adding agents)
  [ ] Troubleshooting guide (common issues + fixes)
  [ ] Architecture diagram (components, data flow)
  [ ] Configuration guide (.env variables, settings)
```

**Success Criteria:**
- All docs complete and reviewed
- Each doc has revision date
- Links checked and working

### Metric 5.2: Deployment Readiness

**Definition:** Production deployment can be executed safely.

**Checklist:**

```
  [ ] Dockerfile builds without errors
  [ ] Docker Compose production config working
  [ ] Health check endpoint responds (/health)
  [ ] Logging working (all important events logged)
  [ ] Monitoring set up (uptime, error rate alerts)
  [ ] Backup strategy documented and tested
  [ ] Rollback procedure documented
  [ ] Database migrations tested (forward + backward)
  [ ] SSL certificate installed
  [ ] Secrets management in place (no hardcoded keys)
  [ ] Load test passed (Metric 2.3)
  [ ] Security scan passed (or issues mitigated)
```

**Success Criteria:**
- All checks pass
- One-command deployment possible

### Metric 5.3: Support & Monitoring

**Definition:** System can be monitored and issues debugged.

**Checklist:**

```
  [ ] Error tracking set up (Sentry or similar)
  [ ] Logs centralized and searchable
  [ ] Uptime monitoring active (Pingdom, etc.)
  [ ] Performance metrics tracked (response times, etc.)
  [ ] Alert thresholds configured (error rate >1%, memory >2GB, etc.)
  [ ] On-call runbook exists (who handles issues at 2am)
  [ ] Support email monitored
  [ ] Incident response process documented
```

**Success Criteria:**
- All items in place
- Test alert: send test incident, verify team responds

---

## Category 6: Stakeholder Acceptance

### Metric 6.1: User Acceptance Testing (UAT)

**Definition:** End users validate system meets requirements.

**Measurement Method:**

1. **Test Participants:** 3-5 power users (internal team or selected customers)
2. **Test Scenarios:** 10-15 realistic workflows
   - Upload and review a SOW
   - Interpret findings and scores
   - Export PDF report
   - View dashboard
   - Manage users (admin only)
3. **Feedback Collection:**
   - System Usability Scale (SUS) survey
   - 5-point satisfaction rating
   - Open feedback on each scenario
4. **Acceptance Criteria:**
   - ≥80% scenarios pass without issues
   - SUS score ≥70 (acceptable)
   - Satisfaction ≥4/5 (satisfied)
   - No critical usability issues

**Example:**
```
Scenario: Upload SOW and interpret results
  Duration: 5 minutes
  Result: ✓ Passed (user found findings clear and actionable)
  Feedback: "Loved the confidence scores. Made prioritization easy."

Scenario: Generate PDF report for stakeholder
  Duration: 2 minutes
  Result: ✓ Passed (PDF formatted well, included all elements)
  Feedback: "Professional looking. Would show this to my boss."

[... 13 more scenarios ...]

Overall: 14/15 scenarios passed. SUS score: 76. Ready to launch.
```

### Metric 6.2: Stakeholder Sign-off

**Definition:** Key stakeholders approve release.

**Sign-off Matrix:**

| Stakeholder | Role | Sign-off | Date | Comments |
|-------------|------|----------|------|----------|
| Product Manager | Feature completeness | [ ] | | |
| Security Lead | Security review | [ ] | | |
| Operations Lead | Production readiness | [ ] | | |
| Executive Sponsor | Business value | [ ] | | |

**Success Criteria:**
- All 4 stakeholders sign-off
- No open blockers
- Any issues have mitigation plan

---

## Pre-Launch Testing Schedule

### Week 12 (Code Complete)
- [ ] Metric 1.1-1.4: AI accuracy testing
- [ ] Metric 3.1-3.3: Functional completeness
- [ ] Metric 4.1-4.3: Security testing

### Week 13 (Bug Fixes)
- [ ] Fix issues from Week 12
- [ ] Metric 2.1-2.4: Performance testing
- [ ] Re-test critical paths

### Week 14 (Pre-Launch)
- [ ] Metric 5.1-5.2: Documentation & deployment
- [ ] Metric 6.1: UAT with power users
- [ ] Final security & compliance check

### Week 15 (Launch)
- [ ] Metric 6.2: Stakeholder sign-off
- [ ] Deploy to production
- [ ] Monitor for 24-48 hours

---

## Failure Scenarios & Mitigation

### Scenario: Precision <90% (too many false positives)

**Root Cause:** Agent prompts too aggressive, hallucinating issues.

**Mitigation:**
1. Analyze which agent is problematic
2. Refine prompt (add "only report if you have evidence" clause)
3. Reduce confidence scores for that agent
4. Re-test on subset, then full test set

**Decision:** 
- If fixed within 2 days → stay on schedule
- If needs 3+ days → delay launch 1 week, re-test

### Scenario: Recall <80% (missing real issues)

**Root Cause:** Agent prompts too conservative, not thorough enough.

**Mitigation:**
1. Analyze which categories have low recall
2. Refine prompt (add more examples of issues)
3. Extend agent timeout (if consistently timing out early)
4. Add rule engine fallback for commonly missed issues

**Decision:** 
- If recall improves to ≥80% within 2 days → stay on schedule
- Otherwise → delay launch 1 week

### Scenario: Mean review time >30 seconds

**Root Cause:** API is slow, agents timing out, bottleneck in orchestration.

**Mitigation:**
1. Profile orchestrator: which agent is slowest?
2. Reduce token usage in prompt (be more concise)
3. Switch to Haiku for preliminary fast pass + Sonnet for detailed review (Phase 2)
4. Increase timeout (if infrastructure can handle)
5. Consider serial vs parallel execution trade-off

**Decision:** 
- If mean <28s → acceptable, launch on schedule
- If 28-30s → borderline, launch with monitoring
- If >30s → delay 1 week, optimize

### Scenario: UAT reveals critical usability issue

**Root Cause:** UI confusing, workflow unclear, or unexpected user behavior.

**Mitigation:**
1. Understand issue from user feedback
2. Quick fix (1-2 day turnaround for critical issues)
3. Re-test with same UAT user
4. Proceed if resolved

**Decision:** 
- If fixed within 2 days → stay on schedule
- If needs design rethink (>2 days) → delay launch 1 week

### Scenario: Security vulnerability found

**Root Cause:** Pen test or code review uncovers auth bypass, data leak, etc.

**Mitigation:**
1. Severity assessment:
   - Critical (data leak, auth bypass) → **must fix before launch**
   - Major (CSRF, rate limiting) → fix, test, then launch
   - Minor (logging info) → document as Phase 2 fix
2. Fix + regression test

**Decision:** 
- Critical: delay launch indefinitely until fixed
- Major: fix and re-test (2-3 days)
- Minor: document, launch with note

---

## Launch Sign-off Template

```
PHASE 1 LAUNCH READINESS REPORT

Date: [date]
Prepared by: [name]

METRIC SUMMARY
==============

Category 1: AI Accuracy
  Precision: 92.5% ✓ (target ≥92%)
  Recall: 81.0% ✓ (target ≥80%)
  Confidence Calibration: 3.2% error ✓ (target <5%)
  Deduplication: 99.2% ✓ (target ≥99%)

Category 2: Performance
  Mean review time: 23.4 seconds ✓ (target ≤25s)
  P95 time: 31.2 seconds ✓ (target ≤35s)
  Upload speed: 4.1 seconds ✓ (target ≤5s)
  Concurrent capacity: 15 simultaneous ✓ (target ≥10)

Category 3: Functional Completeness
  Feature checklist: 48/50 ✓ (96%, target ≥95%)
  Error handling: PASS ✓
  Data integrity: PASS ✓

Category 4: Security
  Auth & authorization: PASS ✓
  Data privacy: PASS ✓
  Input validation: PASS ✓

Category 5: Operations
  Documentation: COMPLETE ✓
  Deployment readiness: PASS ✓
  Monitoring: ACTIVE ✓

Category 6: Stakeholder Acceptance
  UAT: 14/15 scenarios, SUS 76 ✓
  Sign-offs: 4/4 ✓

OVERALL STATUS: APPROVED FOR PRODUCTION LAUNCH

Open Issues: None
Risks: Low
Recommended Actions: Monitor for 48 hours post-launch, alert on-call if error rate >1%

Signed:
___________________ [Product Manager]
___________________ [Security Lead]
___________________ [Operations Lead]
___________________ [Executive Sponsor]
```

---

## Post-Launch Monitoring (Week 1)

After production launch, monitor:

```
Critical Metrics (alert if threshold breached):
  [ ] Error rate >1% → page on-call
  [ ] Response time >40s (p95) → investigate
  [ ] Memory usage >2.5GB → check for leak
  [ ] Review accuracy complaints >3 → escalate

Weekly Metrics:
  [ ] User adoption (docs uploaded/week)
  [ ] Review completion rate (% reviews finishing)
  [ ] Customer satisfaction (NPS if surveys sent)
  [ ] Bug reports (priority + frequency)

Action Plan if Issues Found:
  - Critical issue → incident response, potential hotfix
  - Major issue → prioritize for Phase 1.1 (1 week later)
  - Minor issue → backlog for Phase 2

Success Criteria (end of Week 1):
  - Zero critical bugs
  - Error rate <0.5%
  - User feedback positive
  - No security incidents
```

