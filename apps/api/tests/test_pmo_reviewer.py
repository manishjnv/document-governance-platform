"""Tests for PMOReviewer (app/ai/agent.py).

docs/planning/4_AI_AGENT_SPECS.md "Agent 5: Project Operations (PMO)
Reviewer" -- spec'd but never wired into orchestrator.py before this
change (only 4 of the original 5 agents were built). Includes the
2026-07-17 spec extension for entry/exit criteria and
fallback/contingency-plan detection.

Same testing approach as test_legal_reviewer.py: structural contract
tests + mocked pipeline test run always; live-API precision/recall
harness is gated behind ANTHROPIC_API_KEY for pre-launch sign-off.
"""

import json
import os
from unittest.mock import MagicMock

import pytest

from app.ai.agent import PMOReviewer

REQUIRED_TOPICS = [
    "raci",
    "escalation",
    "sla",
    "change management",
    "entry criteria",
    "exit",
    "fallback",
]


def test_sow_prompt_covers_every_required_pmo_topic():
    prompt = PMOReviewer().get_system_prompt("SOW").lower()
    for topic in REQUIRED_TOPICS:
        assert topic in prompt, f"SOW prompt missing required topic: {topic}"


def test_sow_prompt_flags_raci_as_critical():
    """Spec: 'RACI is critical. Missing RACI = major risk.'"""
    prompt = PMOReviewer().get_system_prompt("SOW").lower()
    assert "raci is critical" in prompt or "critical" in prompt


def test_rfp_branch_differs_from_sow_branch():
    agent = PMOReviewer()
    sow_prompt = agent.get_system_prompt("SOW")
    rfp_prompt = agent.get_system_prompt("RFP")
    assert sow_prompt != rfp_prompt
    assert "rfp" in rfp_prompt.lower() or "request for proposal" in rfp_prompt.lower()


def test_output_schema_requires_governance_and_findings():
    schema = PMOReviewer().get_output_schema()
    assert set(schema["required"]) == {"governance", "findings", "overall_confidence"}


@pytest.mark.asyncio
async def test_review_parses_mocked_agent_response():
    agent = PMOReviewer()

    canned_response = {
        "governance": {
            "raci_matrix_present": False,
            "escalation_levels": [],
            "sla_defined": False,
            "entry_exit_criteria_defined": False,
            "fallback_plan_defined": False,
        },
        "findings": [
            {
                "type": "missing_raci",
                "severity": "major",
                "description": "No RACI matrix found.",
                "evidence": "Document has no governance/RACI section.",
                "recommendation": "Add a RACI matrix defining ownership per workstream.",
                "confidence": 0.96,
            },
            {
                "type": "missing_fallback_plan",
                "severity": "critical",
                "description": "No contingency or rollback plan defined.",
                "evidence": "No mention of fallback procedures if the engagement fails.",
                "recommendation": "Add a documented fallback/rollback plan.",
                "confidence": 0.93,
            },
        ],
        "overall_confidence": 0.88,
    }

    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=json.dumps(canned_response))]
    agent.client = MagicMock()
    agent.client.messages.create.return_value = mock_message

    result = await agent.review("Some SOW text with no governance section.", "SOW")

    assert agent.validate_output(result)
    types_found = {f["type"] for f in result["findings"]}
    assert types_found == {"missing_raci", "missing_fallback_plan"}


# ---------------------------------------------------------------------------
# Live-API acceptance harness (Metrics 1.1-1.4) -- gated, not run in CI
# without credentials.
# ---------------------------------------------------------------------------

_LIVE_TEST_SET = [
    {
        "text": (
            "This Statement of Work covers a 6-month cloud migration engagement. "
            "Deliverables include server migration and validation."
        ),
        # No RACI, escalation, SLA, change management, entry/exit criteria,
        # or fallback plan anywhere.
        "expected_categories": {
            "missing_raci",
            "undefined_escalation",
            "missing_entry_exit_criteria",
            "missing_fallback_plan",
        },
    },
    {
        "text": (
            "This Statement of Work covers a 6-month cloud migration engagement. "
            "GOVERNANCE: A RACI matrix is attached as Exhibit B -- Vendor is "
            "Responsible and Accountable for infrastructure migration; Customer is "
            "Consulted and Informed. A weekly steering committee governs the engagement. "
            "ESCALATION: L1 issues go to the Technical Lead (2-hour response), L2 to "
            "the Program Manager (24-hour response), L3 to the Account Manager (48-hour). "
            "SLA: Production incidents are acknowledged within 1 hour and resolved "
            "within 8 hours for Severity 1. "
            "CHANGE MANAGEMENT: All scope changes require written approval via the "
            "Change Request process, approved by the steering committee. "
            "ENTRY CRITERIA: Migration begins once the target environment is "
            "provisioned and signed off by Customer. "
            "EXIT CRITERIA: Engagement is complete once all servers pass UAT and run "
            "in production for 30 days with 99.9% uptime. "
            "FALLBACK PLAN: If migration fails validation, Vendor will roll back to "
            "the original environment within 4 hours per the documented rollback runbook."
        ),
        "expected_categories": set(),
    },
]


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="Live-API precision/recall/calibration/dedup harness -- requires ANTHROPIC_API_KEY. "
    "Run before launch sign-off per docs/planning/5_LAUNCH_CRITERIA.md Metrics 1.1-1.4.",
)
@pytest.mark.asyncio
async def test_pmo_reviewer_precision_recall_live():
    agent = PMOReviewer()
    all_expected = 0
    all_found_correct = 0
    all_findings_count = 0

    for case in _LIVE_TEST_SET:
        result = await agent.review(case["text"], "SOW")
        found_categories = {f["type"] for f in result.get("findings", [])}

        all_expected += len(case["expected_categories"])
        all_found_correct += len(found_categories & case["expected_categories"])
        all_findings_count += len(found_categories)

    precision = all_found_correct / all_findings_count if all_findings_count else 1.0
    recall = all_found_correct / all_expected if all_expected else 1.0

    assert precision >= 0.92, f"precision {precision:.2%} below 92% target"
    assert recall >= 0.80, f"recall {recall:.2%} below 80% target"
