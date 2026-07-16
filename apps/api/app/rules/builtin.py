"""
Built-in validation rules (20 core SOW rules).

T-504: Create built-in rules as data structures (no database)
"""


def get_builtin_rules() -> list[dict]:
    """
    Return list of built-in SOW validation rules.

    Each rule is a dict with: rule_id, name, description, document_types,
    severity, check_type, params, recommendation.
    """
    return [
        # Section presence rules (T-505)
        {
            "rule_id": "SOW-001",
            "name": "Executive Summary Required",
            "description": "SOW must contain an Executive Summary or Overview section",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "section_presence",
            "params": {"required_sections": ["Executive Summary", "Overview", "Summary"]},
            "recommendation": "Add an Executive Summary section at the beginning of the document",
        },
        {
            "rule_id": "SOW-002",
            "name": "Scope of Work Section Required",
            "description": "SOW must clearly define the Scope of Work",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "section_presence",
            "params": {"required_sections": ["Scope of Work", "Scope", "Work Scope"]},
            "recommendation": "Add a dedicated Scope of Work section defining all deliverables",
        },
        {
            "rule_id": "SOW-003",
            "name": "Deliverables Section Required",
            "description": "SOW must list all deliverables explicitly",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "section_presence",
            "params": {"required_sections": ["Deliverables", "Delivery Items", "Outputs"]},
            "recommendation": "Create a Deliverables section listing all outputs with acceptance criteria",
        },
        {
            "rule_id": "SOW-004",
            "name": "Timeline/Schedule Required",
            "description": "SOW must specify project timeline and milestones",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "section_presence",
            "params": {"required_sections": ["Timeline", "Schedule", "Milestones", "Project Timeline"]},
            "recommendation": "Add a Timeline section with start date, end date, and key milestones",
        },
        {
            "rule_id": "SOW-005",
            "name": "Pricing/Cost Section Required",
            "description": "SOW must specify pricing and cost structure",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "section_presence",
            "params": {"required_sections": ["Pricing", "Cost", "Fees", "Investment"]},
            "recommendation": "Add a Pricing section specifying total cost, payment terms, and invoice schedule",
        },
        {
            "rule_id": "SOW-006",
            "name": "Terms and Conditions Required",
            "description": "SOW must include Terms and Conditions section",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "section_presence",
            "params": {"required_sections": ["Terms and Conditions", "Terms", "T&C"]},
            "recommendation": "Add a Terms and Conditions section covering payment, liability, and termination",
        },
        {
            "rule_id": "SOW-007",
            "name": "Assumptions and Constraints Required",
            "description": "SOW must document assumptions and constraints",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "section_presence",
            "params": {"required_sections": ["Assumptions", "Constraints", "Assumptions & Constraints"]},
            "recommendation": "Add Assumptions and Constraints section to clarify project boundaries",
        },
        # Word count rules (T-506)
        {
            "rule_id": "SOW-008",
            "name": "Scope Description Must Be Detailed",
            "description": "Scope of Work section must have sufficient detail (minimum 100 words)",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "word_count",
            "params": {"required_sections": ["Scope of Work", "Scope"], "min_words": 100},
            "recommendation": "Expand Scope section with more detailed description of work to be performed",
        },
        {
            "rule_id": "SOW-009",
            "name": "Deliverables Must Be Detailed",
            "description": "Deliverables section must have detailed descriptions (minimum 150 words)",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "word_count",
            "params": {"required_sections": ["Deliverables"], "min_words": 150},
            "recommendation": "Add detailed descriptions and acceptance criteria for each deliverable",
        },
        {
            "rule_id": "SOW-010",
            "name": "Terms Section Must Be Comprehensive",
            "description": "Terms and Conditions section must be comprehensive (minimum 100 words)",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "word_count",
            "params": {"required_sections": ["Terms and Conditions", "Terms"], "min_words": 100},
            "recommendation": "Expand Terms and Conditions with clear payment terms, liabilities, and dispute resolution",
        },
        # Keyword checks (T-508)
        {
            "rule_id": "SOW-011",
            "name": "Must Specify Payment Terms",
            "description": "SOW must explicitly mention payment terms (Net 30, Net 60, Due Upon Completion, etc.)",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "keyword",
            "params": {"keywords": ["net 30", "net 60", "net 90", "payment terms", "due upon", "invoice"]},
            "recommendation": "Add explicit payment terms in Pricing or Terms section (e.g., 'Net 30')",
        },
        {
            "rule_id": "SOW-012",
            "name": "Must Define Acceptance Criteria",
            "description": "SOW must define acceptance criteria for deliverables",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "keyword",
            "params": {"keywords": ["acceptance criteria", "acceptance", "acceptance date", "approved by", "signed off"]},
            "recommendation": "Define clear acceptance criteria for each deliverable (e.g., 'Approved by client, signed off by PM')",
        },
        {
            "rule_id": "SOW-013",
            "name": "Must Address Confidentiality",
            "description": "SOW should address confidentiality and data protection",
            "document_types": ["SOW"],
            "severity": "medium",
            "check_type": "keyword",
            "params": {"keywords": ["confidential", "confidentiality", "nda", "data protection", "privacy"]},
            "recommendation": "Add confidentiality and data protection clauses in Terms section",
        },
        {
            "rule_id": "SOW-014",
            "name": "Must Address Change Control",
            "description": "SOW should define change control or change request process",
            "document_types": ["SOW"],
            "severity": "medium",
            "check_type": "keyword",
            "params": {"keywords": ["change", "change request", "change control", "out of scope", "scope creep"]},
            "recommendation": "Add a Change Control section explaining how scope changes are handled",
        },
        # Conditional rules (T-507)
        {
            "rule_id": "SOW-015",
            "name": "High-Value SOW Must Have Escalation Clause",
            "description": "SOWs over $100K should have escalation/dispute resolution clause",
            "document_types": ["SOW"],
            "severity": "major",
            "check_type": "conditional",
            "params": {
                "condition": "$100",
                "required_field": "escalation"
            },
            "recommendation": "For SOWs > $100K, add escalation/dispute resolution procedures in Terms",
        },
        {
            "rule_id": "SOW-016",
            "name": "Long-Term SOW Must Define Support",
            "description": "Multi-year SOWs (>12 months) should define post-delivery support",
            "document_types": ["SOW"],
            "severity": "medium",
            "check_type": "conditional",
            "params": {
                "condition": "year",
                "required_field": "support"
            },
            "recommendation": "For multi-year engagements, add post-delivery support and maintenance clauses",
        },
        # Regex rules (T-508)
        {
            "rule_id": "SOW-017",
            "name": "Must Have Start Date",
            "description": "SOW must specify a project start date (YYYY-MM-DD or similar format)",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "regex",
            "params": {
                "pattern": r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|January|February|March|April|May|June|July|August|September|October|November|December.*\d{4}",
                "should_match": True
            },
            "recommendation": "Add an explicit start date in YYYY-MM-DD or other standard date format",
        },
        {
            "rule_id": "SOW-018",
            "name": "Must Have End Date or Duration",
            "description": "SOW must specify project end date or duration",
            "document_types": ["SOW"],
            "severity": "critical",
            "check_type": "regex",
            "params": {
                "pattern": r"end date|completion date|duration|weeks|months|days|through|until",
                "should_match": True
            },
            "recommendation": "Add project end date or specify duration (e.g., '6 months' or 'through 2026-12-31')",
        },
        {
            "rule_id": "SOW-019",
            "name": "Must Define Resource Requirements",
            "description": "SOW should specify team resources or staffing (FTE, roles, etc.)",
            "document_types": ["SOW"],
            "severity": "medium",
            "check_type": "keyword",
            "params": {"keywords": ["resource", "fte", "team", "staffing", "personnel", "headcount"]},
            "recommendation": "Define resource requirements, team roles, and FTE allocation",
        },
        {
            "rule_id": "SOW-020",
            "name": "Must Address Success Metrics",
            "description": "SOW should define how project success will be measured",
            "document_types": ["SOW"],
            "severity": "medium",
            "check_type": "keyword",
            "params": {"keywords": ["success criteria", "kpi", "metric", "measurement", "success"]},
            "recommendation": "Add Success Criteria section defining KPIs and how project success will be measured",
        },
    ]
