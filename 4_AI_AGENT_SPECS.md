# AI Agent Specifications - Phase 1

**Model:** Claude 3.5 Sonnet
**Parallelization:** All 5 agents run concurrently (max 30 seconds total)
**Output Format:** Structured JSON (Pydantic validated)
**Confidence Scoring:** 0-100, derived from agent reasoning

---

## Agent Architecture

```
DocumentAnalyzer (orchestrator)
├── ScopeReviewer (parallel)
├── DeliveryReviewer (parallel)
├── CommercialReviewer (parallel)
├── SecurityReviewer (parallel)
└── PMOReviewer (parallel)
```

Each agent:
1. Receives document text + sections
2. Runs inference (max 30 seconds timeout)
3. Returns structured JSON
4. Applies confidence scoring
5. Detects findings (issues)

**Coordinator:** Aggregates all agent outputs, deduplicates, returns combined findings.

---

## Agent 1: Scope Reviewer

**Purpose:** Identify scope, deliverables, acceptance criteria, and scope boundary issues.

**Input:**
```python
{
  "document_text": str,
  "parsed_sections": [{
    "title": str,
    "content": str,
    "page": int
  }],
  "doc_filename": str
}
```

**System Prompt:**

```
You are an expert SOW (Statement of Work) scope analyst. Your task is to:

1. Extract the PROJECT SCOPE from the SOW
   - What is the project about?
   - What are the main deliverables?
   - What work is explicitly in scope?
   - What work is explicitly out of scope?

2. Extract ACCEPTANCE CRITERIA
   - How will success be measured?
   - What are the go-live criteria?
   - What conditions must be met for delivery acceptance?

3. Extract DELIVERABLES
   - List all tangible deliverables
   - For each: timeline, format, acceptance criteria
   - Are they clearly defined?

4. Identify SCOPE RISKS
   - Are deliverables ambiguous? (e.g., "software enhancements" without specifics)
   - Is scope boundary unclear? (e.g., "best effort" without limits)
   - Is there language suggesting scope creep? (e.g., "and other related work")
   - Are assumptions about scope documented?
   - Is there a change control process defined?

IMPORTANT:
- Be specific. Quote relevant text.
- If something is missing, note it as a risk.
- Only report what you find; don't speculate.
- Rate your confidence in each finding (0-100).

Output ONLY valid JSON. No markdown, no explanation.
```

**Output Schema:**

```python
from pydantic import BaseModel
from typing import List, Optional

class ScopeExtractions(BaseModel):
    project_scope: str  # 1-2 sentences summarizing project
    main_deliverables: List[str]  # ["Deliverable 1", "Deliverable 2", ...]
    explicit_out_of_scope: List[str]  # If mentioned
    acceptance_criteria_present: bool
    acceptance_criteria_text: Optional[str]  # Quoted from SOW
    change_control_process_defined: bool

class ScopeRisk(BaseModel):
    category: str  # "ambiguous_deliverable" | "missing_acceptance_criteria" | "scope_creep" | "undefined_boundary"
    severity: str  # "critical" | "major" | "medium" | "low"
    title: str  # Human-readable issue
    evidence: str  # Quoted text from document
    explanation: str  # Why this is a risk
    recommendation: str  # How to fix
    confidence: float  # 0-100

class ScopeReviewerOutput(BaseModel):
    extractions: ScopeExtractions
    risks: List[ScopeRisk]
    summary: str  # 1-2 sentence overall assessment
```

**Example Output:**

```json
{
  "extractions": {
    "project_scope": "Implement a cloud migration for XYZ Corp's on-premises infrastructure.",
    "main_deliverables": [
      "AWS VPC setup and configuration",
      "Server migration from on-premises to EC2",
      "Data migration and validation",
      "Training documentation"
    ],
    "explicit_out_of_scope": [
      "Application code refactoring"
    ],
    "acceptance_criteria_present": true,
    "acceptance_criteria_text": "All servers migrated and validated in UAT. Zero data loss. 99.9% uptime in production for 30 days post-go-live.",
    "change_control_process_defined": false
  },
  "risks": [
    {
      "category": "missing_acceptance_criteria",
      "severity": "major",
      "title": "Change control process not defined",
      "evidence": "No mention of how changes to scope will be managed during implementation.",
      "explanation": "Without a change control process, scope creep is likely. Who approves changes? What's the timeline?",
      "recommendation": "Add a section defining: (1) types of changes that trigger formal process, (2) approval authority, (3) timeline for decisions, (4) impact on pricing.",
      "confidence": 95.0
    }
  ],
  "summary": "Scope is generally well-defined with clear deliverables and acceptance criteria. Risk: no change control process defined."
}
```

**Confidence Scoring Logic:**

```python
def calculate_scope_confidence(finding: ScopeRisk) -> float:
    """
    Scope risks are typically high confidence because they're based on:
    - Explicit text patterns (e.g., "best effort" = scope creep)
    - Missing sections (e.g., no acceptance criteria)
    - Clear contradictions
    
    Base: 85-100
    Reduce by:
    - 10 points if evidence is inferred (not explicit)
    - 5 points if change to document could resolve
    
    Return: confidence score 0-100
    """
    confidence = 95.0  # Start high
    
    # Adjust based on evidence quality
    if "inferred" in finding.explanation.lower():
        confidence -= 10
    
    # Adjust based on how easy to fix
    if finding.category in ["ambiguous_deliverable", "undefined_boundary"]:
        confidence -= 5  # Can be clarified relatively easily
    
    return max(0, min(100, confidence))
```

---

## Agent 2: Delivery Reviewer

**Purpose:** Identify timeline, milestones, dependencies, and delivery risks.

**Input:**
```python
{
  "document_text": str,
  "parsed_sections": [...],
  "doc_filename": str
}
```

**System Prompt:**

```
You are an expert project delivery analyst. Your task is to:

1. Extract PROJECT TIMELINE
   - Start date
   - End date (go-live)
   - Total duration
   - Major milestones (with dates)

2. Extract DEPENDENCIES & ASSUMPTIONS
   - What external dependencies are listed?
   - What assumptions are documented?
   - What customer responsibilities are required?

3. Extract RESOURCE REQUIREMENTS
   - Team size (if mentioned)
   - Customer participation (e.g., "dedicated resources")
   - Infrastructure requirements

4. Identify DELIVERY RISKS
   - Are timeline dates unrealistic? (e.g., 6-month migration in 4 weeks)
   - Are dependencies unclear or unmanaged?
   - Are customer responsibilities missing?
   - Is there a delay/dispute resolution clause?
   - Is hypercare period defined?
   - Are rollback procedures documented?
   - Is there a warranty period?

IMPORTANT:
- Be specific. Quote relevant dates and commitments.
- Only report explicit issues; don't speculate about feasibility.
- If dates are missing, note it as a risk.
- Rate confidence in each finding (0-100).

Output ONLY valid JSON.
```

**Output Schema:**

```python
class DeliveryExtractions(BaseModel):
    start_date: Optional[str]  # "2024-Q2" or "TBD"
    end_date: Optional[str]
    total_duration_weeks: Optional[int]
    major_milestones: List[dict]  # [{"milestone": "UAT complete", "target_date": "2024-06-30"}]
    customer_dependencies: List[str]
    external_dependencies: List[str]
    documented_assumptions: List[str]
    hypercare_period_defined: bool
    warranty_period_defined: bool
    delay_clause_present: bool

class DeliveryRisk(BaseModel):
    category: str  # "missing_timeline" | "unrealistic_schedule" | "undefined_dependency" | "missing_hypercare" | "missing_warranty"
    severity: str
    title: str
    evidence: str
    explanation: str
    recommendation: str
    confidence: float

class DeliveryReviewerOutput(BaseModel):
    extractions: DeliveryExtractions
    risks: List[DeliveryRisk]
    summary: str
```

**Confidence Scoring Logic:**

```python
def calculate_delivery_confidence(finding: DeliveryRisk) -> float:
    """
    Delivery risks depend heavily on:
    - Explicit dates and timelines (high confidence)
    - Missing dates or hypercare (high confidence for "missing" findings)
    - Feasibility opinions (lower confidence, depends on context)
    
    Base: 80-100
    Reduce by:
    - 10 if speculating on feasibility without data
    - 5 if date is "soft" (e.g., "Q2" vs "2024-06-30")
    """
    confidence = 90.0
    
    if "feasible" in finding.explanation.lower() or "feasibility" in finding.explanation.lower():
        confidence -= 10  # Feasibility is speculative
    
    if finding.category == "missing_timeline":
        confidence = 98.0  # High confidence for missing items
    
    return max(0, min(100, confidence))
```

---

## Agent 3: Commercial Reviewer

**Purpose:** Identify pricing, payment terms, and commercial risks.

**Input:** Same as above

**System Prompt:**

```
You are an expert commercial/pricing analyst. Your task is to:

1. Extract PRICING & PAYMENT TERMS
   - Total contract value (if stated)
   - Pricing model (fixed price, T&M, hybrid)
   - Payment schedule (e.g., "30% upfront, 70% upon go-live")
   - Currency
   - Inclusions/exclusions in pricing

2. Extract COST DRIVERS & ESCALATION
   - Are out-of-scope charges defined? (e.g., "additional resources at $X/hour")
   - Are there escalation clauses? (e.g., "price increases 3% annually")
   - Are there volume discounts or penalties?

3. Identify COMMERCIAL RISKS
   - Is pricing unclear or ambiguous?
   - Are payment conditions undefined?
   - Is "out of scope" pricing undefined?
   - Are financial incentives/penalties missing?
   - Is there no cancellation fee defined?
   - Are cost overrun scenarios unaddressed?

IMPORTANT:
- Focus on clarity of pricing, not fairness of terms.
- Quote pricing language directly.
- If critical terms are missing, note as critical risk.
- Rate confidence for each finding.

Output ONLY valid JSON.
```

**Output Schema:**

```python
class CommercialExtractions(BaseModel):
    total_contract_value: Optional[str]  # "₹50,00,000" or "$100,000" or "TBD"
    pricing_model: Optional[str]  # "fixed_price" | "time_and_material" | "hybrid"
    payment_schedule: Optional[str]  # "30% upfront, 70% upon go-live"
    out_of_scope_pricing_defined: bool
    out_of_scope_rate: Optional[str]  # "₹5,000/day for additional resources"
    escalation_clause_present: bool
    escalation_clause_text: Optional[str]
    currency: Optional[str]  # "INR" | "USD"

class CommercialRisk(BaseModel):
    category: str  # "ambiguous_pricing" | "undefined_payment_terms" | "undefined_oos_pricing" | "missing_escalation"
    severity: str
    title: str
    evidence: str
    explanation: str
    recommendation: str
    confidence: float

class CommercialReviewerOutput(BaseModel):
    extractions: CommercialExtractions
    risks: List[CommercialRisk]
    summary: str
```

**Confidence Scoring Logic:**

```python
def calculate_commercial_confidence(finding: CommercialRisk) -> float:
    """
    Commercial risks have high confidence for:
    - Missing pricing terms (explicit absence)
    - Ambiguous payment conditions (clear language showing ambiguity)
    - Undefined escalation
    
    Base: 85-100
    Reduce by 5-10 if interpreting intent rather than reading explicit text.
    """
    confidence = 90.0
    
    if finding.category in ["undefined_payment_terms", "undefined_oos_pricing", "missing_escalation"]:
        confidence = 98.0  # Missing items = high confidence
    
    if "inferred" in finding.explanation.lower():
        confidence -= 10
    
    return max(0, min(100, confidence))
```

---

## Agent 4: Security & Compliance Reviewer

**Purpose:** Identify security requirements, compliance mandates, and related risks.

**Input:** Same as above

**System Prompt:**

```
You are an expert information security and compliance analyst. Your task is to:

1. Extract SECURITY REQUIREMENTS
   - What security controls are mandated?
   - What authentication/encryption requirements?
   - What access control requirements?
   - What vulnerability management clauses?

2. Extract COMPLIANCE & AUDIT
   - What compliance frameworks are mentioned? (SOC2, ISO27001, HIPAA, PCI-DSS, etc.)
   - What audit rights are specified?
   - What reporting requirements?
   - What data classification levels?

3. Extract DATA HANDLING & PRIVACY
   - Where can data be stored/processed? (data residency)
   - Who has access rights?
   - What data retention requirements?
   - What data deletion requirements?

4. Identify SECURITY & COMPLIANCE RISKS
   - Are security clauses missing entirely?
   - Are compliance requirements vague?
   - Is data residency undefined?
   - Are audit rights missing?
   - Is there no disaster recovery/business continuity defined?
   - Are incident response procedures undefined?

IMPORTANT:
- This is about compliance, not about assessing whether requirements are realistic.
- Quote security language directly.
- Missing security clauses = critical risk.
- Be specific about which frameworks/standards are mentioned.

Output ONLY valid JSON.
```

**Output Schema:**

```python
class SecurityExtractions(BaseModel):
    security_controls_listed: List[str]  # ["encryption at rest", "MFA", "IP whitelisting"]
    compliance_frameworks: List[str]  # ["SOC2", "ISO27001", "HIPAA"]
    data_residency_requirement: Optional[str]  # "India only" or "TBD"
    audit_rights_defined: bool
    audit_frequency: Optional[str]  # "Annual", "Quarterly", "On-demand"
    incident_reporting_sla: Optional[str]  # "24 hours"
    disaster_recovery_defined: bool
    business_continuity_defined: bool

class SecurityRisk(BaseModel):
    category: str  # "missing_security_clauses" | "undefined_compliance" | "unclear_data_residency" | "missing_audit_rights"
    severity: str
    title: str
    evidence: str
    explanation: str
    recommendation: str
    confidence: float

class SecurityReviewerOutput(BaseModel):
    extractions: SecurityExtractions
    risks: List[SecurityRisk]
    summary: str
```

**Confidence Scoring Logic:**

```python
def calculate_security_confidence(finding: SecurityRisk) -> float:
    """
    Security risks have very high confidence when:
    - Compliance frameworks are completely missing
    - Audit rights undefined
    - Data residency unspecified
    
    These are often critical for regulated orgs.
    
    Base: 90-100
    Most security risks should be 95+ confidence (they're explicit absences).
    """
    confidence = 95.0
    
    if finding.category in ["missing_security_clauses", "undefined_compliance", "missing_audit_rights"]:
        confidence = 99.0  # Missing critical items
    
    return max(0, min(100, confidence))
```

---

## Agent 5: Project Operations (PMO) Reviewer

**Purpose:** Identify governance, RACI, escalation, and operational risks.

**Input:** Same as above

**System Prompt:**

```
You are an expert project operations and governance analyst. Your task is to:

1. Extract GOVERNANCE & RACI
   - Is a RACI matrix defined? (Responsible, Accountable, Consulted, Informed)
   - Who owns what? (e.g., "vendor owns infrastructure, customer owns applications")
   - What is the governance structure? (steering committee, working groups)

2. Extract ESCALATION & DECISIONS
   - What is the escalation path for issues/risks?
   - Who has decision authority at each level?
   - What is the decision timeline?
   - How are escalations resolved?

3. Extract SLAs & OPERATIONAL TERMS
   - Are Service Level Agreements (SLAs) defined? (if ongoing work)
   - What are the response/resolution times?
   - What are the uptime commitments?
   - What are the support hours?

4. Extract CHANGE MANAGEMENT
   - How are changes approved?
   - Who has change authority?
   - Is there a change request process?
   - Are there change windows defined?

5. Identify OPERATIONAL RISKS
   - Is RACI matrix missing?
   - Is escalation path undefined?
   - Are decision authorities unclear?
   - Are SLAs missing (for ongoing services)?
   - Is change process undefined?
   - Are support responsibilities unclear?

IMPORTANT:
- RACI is critical. Missing RACI = major risk.
- Quote governance language.
- Rate confidence in each finding.

Output ONLY valid JSON.
```

**Output Schema:**

```python
class OperationsExtractions(BaseModel):
    raci_matrix_present: bool
    raci_matrix_details: Optional[str]  # Quoted from document
    escalation_levels: List[str]  # ["L1 - Technical team lead", "L2 - Program manager", "L3 - Account manager"]
    escalation_timeframes: Optional[str]  # e.g., "L1: 2 hours, L2: 24 hours, L3: 48 hours"
    decision_authority: Optional[str]  # Who approves scope changes, etc.
    sla_defined: bool
    sla_response_time: Optional[str]  # e.g., "4 hours for critical"
    sla_resolution_time: Optional[str]  # e.g., "24 hours for critical"
    support_hours: Optional[str]  # "24x7" | "9-5 IST"
    change_management_process: Optional[str]

class OperationsRisk(BaseModel):
    category: str  # "missing_raci" | "undefined_escalation" | "unclear_decision_authority" | "missing_sla"
    severity: str
    title: str
    evidence: str
    explanation: str
    recommendation: str
    confidence: float

class PMOReviewerOutput(BaseModel):
    extractions: OperationsExtractions
    risks: List[OperationsRisk]
    summary: str
```

**Confidence Scoring Logic:**

```python
def calculate_pmo_confidence(finding: OperationsRisk) -> float:
    """
    PMO risks are high confidence when:
    - RACI is completely missing (critical)
    - Escalation path undefined (critical)
    - No decision authority specified
    
    Lower confidence for:
    - Vague escalation timeframes (could be in supporting docs)
    
    Base: 90-100
    """
    confidence = 92.0
    
    if finding.category in ["missing_raci", "undefined_escalation", "unclear_decision_authority"]:
        confidence = 98.0  # Critical structural elements
    
    if "supporting documents" in finding.explanation.lower():
        confidence -= 5  # Could be defined elsewhere
    
    return max(0, min(100, confidence))
```

---

## Orchestrator: Coordinator

**Purpose:** Aggregate all 5 agent outputs, deduplicate findings, calculate overall scores.

**Algorithm:**

```python
async def orchestrate_review(document_text: str, parsed_sections: List[dict]) -> ReviewResult:
    # 1. Call all 5 agents in parallel
    results = await asyncio.gather(
        scope_reviewer.review(document_text, parsed_sections),
        delivery_reviewer.review(document_text, parsed_sections),
        commercial_reviewer.review(document_text, parsed_sections),
        security_reviewer.review(document_text, parsed_sections),
        pmo_reviewer.review(document_text, parsed_sections),
        timeout=30
    )
    
    # 2. Flatten findings from all agents
    all_findings = []
    for agent_result in results:
        all_findings.extend(agent_result.risks)
    
    # 3. Deduplicate findings (same issue reported by multiple agents)
    deduplicated = deduplicate_findings(all_findings)
    
    # 4. Calculate scores per category
    scores = calculate_category_scores(deduplicated)
    
    # 5. Calculate overall risk score
    risk_score = calculate_risk_score(deduplicated)
    
    # 6. Generate executive summary
    summary = generate_executive_summary(deduplicated, scores)
    
    return ReviewResult(
        findings=deduplicated,
        scores=scores,
        risk_score=risk_score,
        summary=summary
    )
```

**Deduplication Logic:**

```python
def deduplicate_findings(findings: List[Finding]) -> List[Finding]:
    """
    If multiple agents report the same issue, merge them.
    E.g., both Scope and PMO agents flag "missing acceptance criteria".
    """
    deduplicated = {}
    
    for finding in findings:
        # Create key from category + title (normalized)
        key = f"{finding.category}:{normalize_text(finding.title)}"
        
        if key not in deduplicated:
            deduplicated[key] = finding
        else:
            # Merge: take higher confidence, combine evidence
            existing = deduplicated[key]
            if finding.confidence > existing.confidence:
                deduplicated[key] = finding
            else:
                # Append evidence from multiple agents
                deduplicated[key].evidence += f"\n\n[Also noted by {finding.agent_name}]"
    
    return list(deduplicated.values())
```

**Category Scoring:**

```python
def calculate_category_scores(findings: List[Finding]) -> Dict[str, float]:
    """
    Score per category (0-100) based on findings in that category.
    
    Scoring model:
    - Start at 100
    - Critical finding in category: -30 points
    - Major finding in category: -15 points
    - Medium finding in category: -5 points
    - Low finding in category: -2 points
    - Info finding in category: -1 point
    
    Minimum score: 0
    """
    categories = {
        "completeness": 100,
        "clarity": 100,
        "consistency": 100,
        "commercial": 100,
        "delivery": 100,
        "operations": 100,
        "security": 100
    }
    
    for finding in findings:
        # Map finding category to scoring category
        score_category = map_finding_to_category(finding.category)
        if score_category in categories:
            if finding.severity == "critical":
                categories[score_category] -= 30
            elif finding.severity == "major":
                categories[score_category] -= 15
            elif finding.severity == "medium":
                categories[score_category] -= 5
            elif finding.severity == "low":
                categories[score_category] -= 2
            else:  # info
                categories[score_category] -= 1
    
    # Ensure no negative scores
    for cat in categories:
        categories[cat] = max(0, min(100, categories[cat]))
    
    return categories

def calculate_overall_score(category_scores: Dict[str, float]) -> float:
    """
    Overall score = average of all category scores.
    BUT: if any critical finding exists, cap overall at 70 max.
    """
    overall = sum(category_scores.values()) / len(category_scores)
    
    # Cap at 70 if critical issues exist
    # (enforced separately in orchestrator)
    
    return overall
```

---

## Execution Flow

```
1. User uploads SOW
   ↓
2. Parse document (extract text + sections)
   ↓
3. Trigger review (async Celery task)
   ↓
4. Call Orchestrator (5 agents in parallel, max 30 seconds)
   ├─ Scope Reviewer (max 30s)
   ├─ Delivery Reviewer (max 30s)
   ├─ Commercial Reviewer (max 30s)
   ├─ Security Reviewer (max 30s)
   └─ PMO Reviewer (max 30s)
   ↓
5. Aggregate findings (deduplicate)
   ↓
6. Calculate scores (per category + overall)
   ↓
7. Generate report (PDF)
   ↓
8. Store in DB (findings, scores, summary)
   ↓
9. Return to user (review complete)
```

**Timeouts:**
- Per agent: 30 seconds (fail gracefully if timeout)
- Total orchestration: 35 seconds (5 agents + 5 seconds overhead)
- User sees "Review in progress..." until complete

---

## Error Handling

**If agent times out:**
```python
try:
    result = await asyncio.wait_for(agent.review(...), timeout=30)
except asyncio.TimeoutError:
    result = PartialResult(
        finding="Agent timeout",
        severity="info",
        confidence=0
    )
    # Continue with other agents
```

**If agent returns invalid JSON:**
```python
try:
    output = ScopeReviewerOutput.parse_raw(response)
except ValidationError as e:
    log.error(f"Agent returned invalid JSON: {e}")
    # Retry once, then fail gracefully
```

**If API rate limit hit:**
```python
# Implement exponential backoff
for attempt in range(3):
    try:
        result = call_claude_api(prompt)
        return result
    except RateLimitError:
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)  # 1s, 2s, 4s
        else:
            raise
```

---

## Testing AI Agents

**Test Dataset:** 30 real SOWs
- 10 high-quality SOWs (few findings)
- 10 medium-quality SOWs (moderate findings)
- 10 low-quality SOWs (many findings)

**Ground Truth:** For each SOW, manually identify:
- Expected findings (by category and severity)
- Confidence threshold

**Evaluation Metrics:**

```
Precision = (Correct Findings) / (All Findings)
Recall = (Correct Findings) / (Expected Findings)
F1 = 2 * (Precision * Recall) / (Precision + Recall)

Target (Phase 1):
- Precision ≥ 92% (no false positives)
- Recall ≥ 80% (find real issues)
- F1 ≥ 85%
```

**Example Test:**

```python
def test_scope_reviewer_on_test_set():
    test_sow = load_test_sow("sow_001.pdf")
    expected_findings = [
        Finding(category="missing_acceptance_criteria", severity="critical"),
        Finding(category="ambiguous_deliverable", severity="major"),
    ]
    
    result = scope_reviewer.review(test_sow.text, test_sow.sections)
    
    assert len(result.risks) == len(expected_findings)
    assert result.risks[0].category == "missing_acceptance_criteria"
    assert result.risks[0].severity == "critical"
    assert result.risks[0].confidence >= 90
```

---

## Performance & Cost Optimization

**Phase 1 (MVP):**
- 5 serial API calls × 3 agents = 15 calls per review
- Cost: ~$0.30 per review (Sonnet pricing: $3/M input tokens, $15/M output tokens)
- Target: <30 seconds per review

**Phase 2 (Optimization):**
- Caching: same document = cached results for 24 hours
- Batch processing: review multiple docs in queue (Celery)
- Model optimization: switch to Haiku for preliminary screening, Sonnet for deep review

