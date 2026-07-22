# SOW Review Training Guideline

## Purpose

This document defines how an AI-powered SOW review engine should report
findings, including exact document findings, missing sections,
cross-document observations, broken references, and conflicting
statements.

## 1. Evidence Types

  Evidence Type     When to Use

---

  location          Text exists but contains an issue
  missing_section   Required section does not exist
  cross_document    Issue identified after reviewing the entire SOW
  conflict          Two sections contradict each other
  reference         Section references missing or invalid content

## 2. Findings from the Sample SOW

---

  ID        Section                    Page      Line(s) Finding           Recommendation    Severity

---

  SOW-001   Purpose                       1         9-13 Business          Define measurable Medium
                                                         objectives are    success criteria
    not measurable.   (MTTD, MTTR,
    detection
    coverage,
    compliance
    goals).

  SOW-002   Customer                      1        15-20 Infrastructure    Add endpoints,    Medium
            Environment                                  inventory is      servers, cloud
    incomplete.       accounts and
    critical
    applications.

  SOW-003   Scope of Services             2         3-12 SOC activities    Define            High
                                                         are not           monitoring,
    sufficiently      triage,
    detailed.         investigation,
    escalation and
    case closure.

  SOW-004   Scope of Services             2         3-12 Threat            Define IOC        High
                                                         Intelligence      lifecycle,
    lacks operational intelligence
    detail.           sources and
    reporting.

  SOW-005   Scope of Services             2         3-12 Threat Hunting    Add hunt          High
                                                         methodology       frequency,
    missing.          hypotheses, MITRE
                                                                           mapping and
    outputs.

  SOW-006   Scope of Services             2         3-12 Incident Response Define            High
                                                         lifecycle         identification,
    undefined.        containment,
    eradication,
    recovery and
    lessons learned.

  SOW-007   Deliverables                  2        14-22 Deliverables have Define acceptance High
                                                         no acceptance     criteria for each
                                                         criteria.         deliverable.

  SOW-008   Deliverables                  2        14-22 Report contents   Specify report    Medium
                                                         are undefined.    sections and
    KPIs.

  SOW-009   Service Levels                2        24-31 Only              Add               High
                                                         acknowledgement   investigation,
    SLA defined.      escalation,
    resolution and
    closure SLAs.

  SOW-010   Service Levels                2        24-31 Service           Specify           High
                                                         hours/time zone   operational
    missing.          coverage and
    holidays.

  SOW-011   Roles and                     3          2-8 Ownership is      Include a RACI    High
            Responsibilities                             unclear.          matrix.

  SOW-012   Governance                    3        10-14 Escalation matrix Define            Medium
                                                         missing.          operational,
    management and
    executive
    escalation.

  SOW-013   Assumptions                   3        16-24 Assumptions are   Convert           Medium
                                                         generic.          assumptions into
    measurable
    customer
    obligations.

  SOW-014   Assumptions                   3        20-24 Log onboarding    Define onboarding Medium
                                                         assumptions       expectations and
    missing.          timelines.

  SOW-015   Exclusions                    3        26-29 Out-of-scope      Explicitly        Medium
                                                         definition        exclude
    incomplete.       additional
    operational
    activities.

  SOW-016   Transition Plan               3        31-33 Transition lacks  Add phases,       Medium
                                                         timeline.         milestones and
    exit criteria.

  SOW-017   Commercial Model              4          2-7 Commercial terms  Add pricing,      High
                                                         incomplete.       invoices, taxes
    and payment
    terms.

  SOW-018   Commercial Model              4          2-7 Change request    Include           Medium
                                                         pricing           engineering rates
                                                         undefined.        and approval
    workflow.

  SOW-019   Open Items                    4         9-18 Uses ambiguous    Replace vague     High
                                                         contractual       language with
    wording.          measurable
    obligations.

  SOW-020   Open Items                    4         9-18 Prioritization    Define governance Medium
                                                         process           and approval
    undefined.        workflow.

  SOW-021   Risk Register                 4        20-25 Risks lack owners Add owner,        Medium
                                                         and mitigations.  probability,
    impact and
    mitigation.

  SOW-022   Acceptance                    4        27-29 Acceptance clause Define acceptance High
            Criteria                                     too generic.      per deliverable.

  SOW-023   Confidentiality               4        31-32 Confidentiality   Add data handling Medium
                                                         clause too        and retention
    generic.          requirements.

  SOW-024   Change Management             5          2-5 Approval workflow Define CR         Medium
                                                         missing.          lifecycle and
    approval
    authority.

  SOW-025   Appendix A                    5         7-22 Log inventory     Add owner, status Medium
                                                         lacks ownership.  and retention.

  SOW-026   Appendix A                    5         7-22 Log volume not    Add daily GB/EPS  Medium
                                                         documented.       estimates.

  SOW-027   Appendix B                    5        24-34 Shift allocation  Define shifts and High
                                                         missing.          regional
    coverage.

  SOW-028   Appendix B                    5        24-34 FTE allocation    Add utilization   Medium
                                                         missing.          percentages and
    hours.

SOW-029   Signature                     6         2-12 Contract metadata Add revision      Low
                                                         incomplete.       history,
    approvers and
    version
    information.
-----------------------------------------------------------------------------------------------

## 3. Missing Section Template

```json
{
  "finding_id":"SOW-042",
  "category":"Missing Section",
  "section_expected":"Key Performance Indicators (KPI)",
  "page":null,
  "line_start":null,
  "line_end":null,
  "status":"Not Found",
  "recommendation":"Add measurable KPIs."
}
```

## 4. Broken Reference Template

```json
{
  "finding_id":"SOW-081",
  "category":"Broken Reference",
  "section":"Appendix A",
  "page":18,
  "line_start":42,
  "matched_text":"Refer to Appendix C",
  "issue":"Appendix C does not exist."
}
```

## 5. Cross-Document Missing Sections

- Project milestones
- KPI section
- Service credits
- RACI matrix
- Compliance requirements
- Data retention policy
- Exit / transition-out plan
- Disaster Recovery
- Business Continuity
- Intellectual Property
- Payment schedule
- Customer staffing assumptions
- Glossary

## 6. Recommended Evidence Model

---

  Field                               Description

---

  finding_id                          Unique identifier

  evidence_type                       location, missing_section,
                                      cross_document, conflict, reference

  category                            Finding category

  severity                            Critical, High, Medium, Low

  section                             Current section

  page                                Page number or null

  line_start                          Starting line or null

  line_end                            Ending line or null

  anchor_before                       Previous section if missing

  anchor_after                        Next section if missing

  matched_text                        Supporting text or null

  issue                               Description

  recommendation                      Suggested improvement

  confidence                          AI confidence score

status                              Found, Missing, Conflicting
---------------------------------------------------------------

# Enterprise Trust Framework for an AI SOW Review Platform



> **Objective:** Address the question from enterprise management:

>

> **"Why should we trust this application with confidential

> documents?"**

>

> This document contains additional guidance beyond the previous SOW

> Review Training Guideline.



------------------------------------------------------------------------



# Core Principle



Do not position the product as **an AI that reviews documents**.



Position it as an **Enterprise Assurance Platform** where AI is only one

component of a controlled, auditable decision framework.



    Document

    │

    Parser

    │

    Rule Engine

    │

    Knowledge Base

    │

    Cross-document Validation

    │

    LLM Reasoning

    │

    Evidence Collection

    │

    Risk Scoring

    │

    Explainable Findings



------------------------------------------------------------------------



# Trust Pillars



## 1. Security



Customer questions the platform should answer clearly:



-   Where are documents stored?

-   Is encryption enabled at rest and in transit?

-   Is customer data used for AI training?

-   Who can access documents?

-   How long are documents retained?

-   Can customers configure deletion policies?

-   Can the solution run inside the customer's cloud?

-   Are audit logs available?



### Recommended capabilities



-   AES-256 encryption at rest

-   TLS 1.3 in transit

-   Regional data residency

-   Customer-managed encryption keys (optional)

-   Automatic document deletion policies

-   Immutable audit logs

-   Role-based access control

-   SSO (SAML/OIDC)

-   MFA

-   Private networking support



------------------------------------------------------------------------



## 2. Customer-Controlled AI



Avoid requiring a single AI provider.



Support multiple inference backends.



Examples:



-   Azure OpenAI

-   AWS Bedrock

-   Google Vertex AI

-   Self-hosted Llama

-   Self-hosted Mistral



Benefits



-   Customer retains AI provider choice

-   Easier enterprise approval

-   Supports regulated industries



------------------------------------------------------------------------



## 3. Explainability



Every finding should contain:



-   Requirement

-   Evidence

-   Analysis

-   Business impact

-   Recommendation

-   Industry reference

-   Confidence



Never present unexplained AI conclusions.



------------------------------------------------------------------------



## 4. Evidence-Based Review



Every finding should be traceable to:



-   Exact document text

-   Missing section

-   Cross-document inconsistency

-   Industry rule

-   Best practice recommendation



Evidence should always be visible.



------------------------------------------------------------------------



## 5. Rule Library



Maintain a structured rule library.



Example attributes



-   Rule ID

-   Category

-   Requirement

-   Detection Logic

-   Severity

-   Recommendation

-   Industry Reference



Example



Rule ID: SEC-104



Requirement:



Incident Response must include



-   Identification

-   Containment

-   Recovery

-   Lessons Learned



Reference:



-   NIST SP 800-61



------------------------------------------------------------------------



## 6. Human Verification



Do not claim perfect accuracy.



Instead display



-   Confidence Score

-   Human Review Recommended

-   Evidence Quality



------------------------------------------------------------------------



# Explainable Finding Workflow



Every finding should follow:



Requirement



↓



Evidence



↓



Analysis



↓



Risk



↓



Recommendation



↓



Reference



------------------------------------------------------------------------



# Confidence Model



Instead of a single confidence value, expose:



-   Finding Confidence

-   Evidence Strength

-   Rule Match Quality

-   Cross-document Validation

-   Industry Reference Availability



------------------------------------------------------------------------



# Auditability



Each review should record:



-   Document SHA-256 hash

-   Analysis timestamp (UTC)

-   Rule library version

-   Model version

-   Application version

-   Review identifier

-   User performing analysis



Benefits



-   Repeatability

-   Non-repudiation

-   Audit trail

-   Version comparison



------------------------------------------------------------------------



# Compliance Mapping



Allow every finding to map to one or more standards.



Examples



-   ISO 27001

-   NIST CSF

-   NIST SP 800-61

-   CIS Controls

-   PCI DSS

-   SOC 2

-   GDPR

-   HIPAA



This provides objective justification for findings.



------------------------------------------------------------------------



# Deployment Models



Support multiple deployment options.



  Deployment                    Typical Customer

  ----------------------------- --------------------

  SaaS                          SMB

  Dedicated Cloud               Enterprise

  Customer AWS Account          Large Enterprise

  Customer Azure Subscription   Financial Services

  On-premises                   Government

  Air-gapped                    Defense



------------------------------------------------------------------------



# Explainability Score



Display quality of every finding.



Example metrics



-   Evidence Strength

-   Rule Match

-   Cross-document Validation

-   Standards Mapping

-   AI Reasoning Quality



These metrics improve reviewer confidence.



------------------------------------------------------------------------



# Enterprise Governance Features



Recommended capabilities



-   Approval workflow

-   Dual-review mode

-   Reviewer comments

-   Finding lifecycle

-   Finding assignment

-   Risk acceptance

-   Exception approval

-   Review history

-   Version comparison

-   Export with audit evidence



------------------------------------------------------------------------



# Product Positioning



Avoid



> AI SOW Reviewer



Prefer



> Enterprise Delivery Assurance Platform



or



> Enterprise Document Assurance Platform



or



> AI-assisted Governance and Assurance Platform



Messaging



> Every finding is traceable, explainable, evidence-backed and aligned

> to industry standards. AI assists analysis while rules, evidence and

> governance provide enterprise-grade trust.
