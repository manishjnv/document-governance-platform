"""Tests for the 2026-07-20 prompt-accuracy revision
(docs/planning/PROMPT_ENGINEERING_GUIDE.md): the shared confidence-
calibration rubric and each agent's new checklist items. Structural only
(no API calls) -- catches accidental prompt regressions across all 6
agents in one place, complementing the more detailed per-agent contract
tests in test_legal_reviewer.py / test_pmo_reviewer.py.
"""

import pytest

from app.ai.agent import (
    CommercialReviewer,
    DeliveryReviewer,
    LegalReviewer,
    PMOReviewer,
    ScopeReviewer,
    SecurityReviewer,
)

ALL_AGENTS = [
    ScopeReviewer(),
    DeliveryReviewer(),
    CommercialReviewer(),
    SecurityReviewer(),
    PMOReviewer(),
    LegalReviewer(),
]


@pytest.mark.parametrize("agent", ALL_AGENTS, ids=lambda a: a.name)
class TestConfidenceCalibrationRubricPresent:
    """Every agent's prompt (both branches) must carry the shared
    calibration rubric -- this is the direct fix for the measured 17.95%
    calibration error (5_LAUNCH_CRITERIA.md Metric 1.3)."""

    def test_sow_prompt_has_calibration_rubric(self, agent):
        prompt = agent.get_system_prompt("SOW")
        assert "CONFIDENCE CALIBRATION" in prompt
        assert "0.85-1.0" in prompt

    def test_rfp_prompt_has_calibration_rubric(self, agent):
        prompt = agent.get_system_prompt("RFP")
        assert "CONFIDENCE CALIBRATION" in prompt
        assert "0.85-1.0" in prompt


class TestScopeReviewerNewChecks:
    def test_sow_prompt_covers_exclusions_and_assumptions(self):
        prompt = ScopeReviewer().get_system_prompt("SOW").lower()
        assert "explicit exclusions" in prompt
        assert "unstated client-side assumptions" in prompt

    def test_schema_includes_new_finding_types(self):
        prompt = ScopeReviewer().get_system_prompt("SOW")
        assert "missing_exclusions" in prompt
        assert "unstated_assumption" in prompt


class TestDeliveryReviewerNewChecks:
    def test_sow_prompt_covers_staffing_and_buffer(self):
        prompt = DeliveryReviewer().get_system_prompt("SOW").lower()
        assert "staffing" in prompt or "resource availability" in prompt
        assert "schedule buffer" in prompt

    def test_schema_includes_new_finding_types(self):
        prompt = DeliveryReviewer().get_system_prompt("SOW")
        assert "unconfirmed_staffing" in prompt
        assert "no_schedule_buffer" in prompt


class TestCommercialReviewerNewChecks:
    def test_sow_prompt_covers_renewal_and_currency(self):
        prompt = CommercialReviewer().get_system_prompt("SOW").lower()
        assert "renewal" in prompt
        assert "currency" in prompt

    def test_schema_includes_new_finding_types(self):
        prompt = CommercialReviewer().get_system_prompt("SOW")
        assert "renewal_risk" in prompt
        assert "currency_tax_gap" in prompt


class TestSecurityReviewerNewChecks:
    def test_sow_prompt_covers_personnel_breach_accessibility(self):
        prompt = SecurityReviewer().get_system_prompt("SOW").lower()
        assert "personnel security" in prompt
        assert "breach" in prompt or "incident notification" in prompt
        assert "accessibility" in prompt

    def test_schema_includes_new_finding_types(self):
        prompt = SecurityReviewer().get_system_prompt("SOW")
        assert "missing_personnel_security" in prompt
        assert "missing_breach_notification" in prompt
        assert "missing_accessibility_standard" in prompt


class TestPMOReviewerNewChecks:
    def test_sow_prompt_covers_reporting_cadence_and_risk_register(self):
        prompt = PMOReviewer().get_system_prompt("SOW").lower()
        assert "reporting cadence" in prompt
        assert "risk register" in prompt or "raid log" in prompt

    def test_schema_includes_new_finding_types(self):
        prompt = PMOReviewer().get_system_prompt("SOW")
        assert "vague_reporting_cadence" in prompt
        assert "missing_risk_register" in prompt


class TestLegalReviewerNewChecks:
    def test_sow_prompt_covers_confidentiality_insurance_force_majeure(self):
        prompt = LegalReviewer().get_system_prompt("SOW").lower()
        assert "mutual" in prompt
        assert "insurance" in prompt
        assert "assignment" in prompt or "subcontract" in prompt
        assert "force majeure" in prompt

    def test_schema_includes_new_finding_types(self):
        prompt = LegalReviewer().get_system_prompt("SOW")
        assert "one_sided_confidentiality" in prompt
        assert "missing_insurance_requirement" in prompt
        assert "missing_force_majeure" in prompt
