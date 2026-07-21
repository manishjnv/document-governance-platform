"""Scoring algorithm for document governance.

T-601-T-619: Scoring system with 7 categories + risk calculation
"""

import logging
import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)

# One-line, category-specific action a reviewer can take -- shared between
# _generate_next_steps (top-of-report "Recommended Next Steps") and the
# report's per-category scorecard guidance, so the two don't drift.
CATEGORY_GUIDANCE = {
    "completeness": "Add missing sections and deliverable details",
    "clarity": "Review ambiguous language and clarify terms",
    "consistency": "Resolve conflicting requirements",
    "commercial": "Define clear pricing and payment terms",
    "delivery": "Establish realistic timeline with milestones",
    "operations": "Define resources, assumptions, and constraints",
    "security": "Add security requirements and compliance clauses",
}


@dataclass
class CategoryScore:
    """Score for a single category (0-100)."""

    category: str
    score: float
    max_points: int
    points_earned: int
    findings: list[dict]
    status: str  # green (80+) | yellow (50-79) | red (<50)


@dataclass
class ScoringResult:
    """Complete scoring result for a document."""

    doc_id: str
    overall_score: float  # Weighted average of 7 categories
    risk_score: float  # Risk assessment (0-100, higher = worse)
    category_scores: dict[str, CategoryScore]
    summary: str
    next_steps: list[str]
    # Per-axis risk (Scope/Delivery/Commercial/Security/Governance/Legal/
    # Compliance), same 0-100 saturating scale as risk_score -- lets a
    # customer see WHICH kind of risk is high instead of one blended number.
    risk_breakdown: dict[str, float] = field(default_factory=dict)


class DocumentScorer:
    """
    Score documents based on findings from AI agents and rule engine.

    T-601: Scoring algorithm (7 categories)
    """

    # Category weights (must sum to 1.0)
    WEIGHTS = {
        "completeness": 0.20,  # 20%
        "clarity": 0.15,  # 15%
        "consistency": 0.15,  # 15%
        "commercial": 0.20,  # 20%
        "delivery": 0.15,  # 15%
        "operations": 0.10,  # 10%
        "security": 0.05,  # 5%
    }

    # Points deducted per finding/violation whose description/rule_id
    # matched a category's specific keywords, scaled by severity -- replaces
    # the old flat per-category constants (10, 8, 12, 15, 20...) that ignored
    # severity entirely, so 5 findings all marked "critical" but generically
    # worded could score a perfect 100 if none happened to contain a
    # trigger word like "missing" or "ambiguous".
    _SPECIFIC_SEVERITY_PENALTY = {"critical": 25, "major": 15, "medium": 8, "low": 4, "info": 0}
    # Smaller points deducted from EVERY category per finding/violation,
    # regardless of whether it matched any category's keywords -- ensures
    # severity always affects scoring, not just specifically-worded findings.
    _GENERAL_SEVERITY_PENALTY = {"critical": 12, "major": 6, "medium": 3, "low": 1, "info": 0}
    # 2026-07-21 fix: this used to subtract the RAW, uncapped sum of the
    # above from every category (e.g. 18 critical + 30 major + 17 medium +
    # 2 low = 449 points off a 100-point category) -- any real document
    # with more than ~10-15 findings zeroed out all 7 categories AND
    # overall_score identically, regardless of what each category's own
    # findings actually looked like. Confirmed against production data:
    # every completed review had every category stored as exactly 0.00.
    # Same saturating-curve fix already applied to risk_score for the
    # identical "flat sum blows past any real cap" problem (see
    # RISK_SATURATION_K below) -- capped well under 100 (not eliminated
    # entirely) so severity volume still nudges every category down
    # proportionally, without erasing each category's own specific signal.
    # 40 is a judgment call (no industry standard for this), sized to
    # roughly 1.5x a single specific-severity critical penalty (25) so it's
    # comparable in magnitude, not dominant.
    GENERAL_PENALTY_CAP = 40.0

    # Risk model (2026-07-19 redesign): the old risk score was a flat
    # additive sum (critical*15 + major*10 + total_count) capped at 100,
    # which saturated to 100 for almost any real document with 4-5
    # critical findings -- every test document showed "100% High" with no
    # way to tell a somewhat-risky doc from an extremely-risky one.
    #
    # New model: each finding contributes RISK_SEVERITY_WEIGHTS[severity]
    # points to a raw sum, then a saturating curve
    # (100 * (1 - e^(-k * raw_sum))) maps that sum to 0-100. This has real
    # headroom in the middle of the range (2 criticals reads meaningfully
    # lower than 8 criticals) while still asymptotically approaching 100
    # for a genuinely bad document, instead of a hard cliff.
    RISK_SEVERITY_WEIGHTS = {"critical": 30, "major": 14, "medium": 5, "low": 1, "info": 0}
    # Calibrated against real review volume: a 6-agent + rule-engine review
    # on an actual SOW/RFP typically raises 30-400 raw severity points
    # (30-40+ findings is normal). k=0.0086 keeps meaningful separation
    # across that whole range instead of pinning everything past ~10
    # findings to 100 -- see docs/planning/SCORING_METHODOLOGY.md.
    RISK_SATURATION_K = 0.0086

    # Maps each finding to a customer-facing risk axis instead of one
    # blended number. Agent names match app/ai/agent.py; rule-engine
    # findings carry no agent_name, hence the "Compliance" fallback.
    # Public (not name-mangled) so app/routers/reviews.py can tag each
    # finding with its risk_area using the exact same mapping the Risk by
    # Area breakdown was computed from -- one source of truth, no drift.
    AXIS_BY_AGENT = {
        "ScopeReviewer": "Scope",
        "DeliveryReviewer": "Delivery",
        "CommercialReviewer": "Commercial",
        "SecurityReviewer": "Security",
        "PMOReviewer": "Governance",
        "LegalReviewer": "Legal",
    }

    def __init__(
        self,
        weight_overrides: Optional[dict[str, float]] = None,
        risk_weight_overrides: Optional[dict[str, float]] = None,
    ):
        # T-2093: per-org scoring weight customization (app/admin/customization.py).
        # WEIGHTS stays the untouched platform default (tests read it directly);
        # self.weights is what scoring actually uses.
        self.weights = {**self.WEIGHTS, **(weight_overrides or {})}
        # Same override pattern for the risk model (app/admin/customization.py
        # get_risk_weights) -- RISK_SEVERITY_WEIGHTS stays the platform
        # default, self.risk_weights is what risk scoring actually uses.
        self.risk_weights = {**self.RISK_SEVERITY_WEIGHTS, **(risk_weight_overrides or {})}
        self.max_points = {
            "completeness": 100,
            "clarity": 100,
            "consistency": 100,
            "commercial": 100,
            "delivery": 100,
            "operations": 100,
            "security": 100,
        }

    async def score_document(
        self,
        doc_id: str,
        findings: list[dict],
        rule_violations: list[dict],
    ) -> ScoringResult:
        """
        Score a document based on AI findings and rule violations.

        Returns ScoringResult with 7 category scores and risk assessment.
        """
        logger.info(f"Scoring document {doc_id}")

        # Initialize category scores
        category_scores = {}

        # Score each category
        category_scores["completeness"] = self._score_completeness(findings, rule_violations)
        category_scores["clarity"] = self._score_clarity(findings, rule_violations)
        category_scores["consistency"] = self._score_consistency(findings, rule_violations)
        category_scores["commercial"] = self._score_commercial(findings, rule_violations)
        category_scores["delivery"] = self._score_delivery(findings, rule_violations)
        category_scores["operations"] = self._score_operations(findings, rule_violations)
        category_scores["security"] = self._score_security(findings, rule_violations)

        # Apply the general severity penalty to every category, on top of
        # whatever category-specific keyword matches already deducted --
        # saturated (see GENERAL_PENALTY_CAP), not the raw sum, so a
        # document with many findings doesn't zero out every category
        # identically regardless of category-specific signal.
        general_penalty = self._saturate(
            self._general_penalty(findings, rule_violations), cap=self.GENERAL_PENALTY_CAP
        )
        if general_penalty:
            for cat_score in category_scores.values():
                cat_score.score = max(0.0, cat_score.score - general_penalty)
                cat_score.points_earned = int(cat_score.score)
                cat_score.status = (
                    "green" if cat_score.score >= 80
                    else ("yellow" if cat_score.score >= 50 else "red")
                )

        # Calculate overall score (weighted average)
        overall_score = self._calculate_overall_score(category_scores)

        # Calculate risk score (overall + per-axis breakdown)
        risk_score = self._calculate_risk_score(findings, rule_violations)
        risk_breakdown = self._calculate_risk_breakdown(findings, rule_violations)

        # Generate summary
        summary = self._generate_summary(overall_score, risk_score, category_scores)

        # Recommend next steps
        next_steps = self._generate_next_steps(category_scores, findings, rule_violations)

        return ScoringResult(
            doc_id=doc_id,
            overall_score=overall_score,
            risk_score=risk_score,
            category_scores=category_scores,
            summary=summary,
            next_steps=next_steps,
            risk_breakdown=risk_breakdown,
        )

    def _severity(self, item: dict) -> str:
        return str(item.get("severity", "")).lower()

    def _general_penalty(self, findings: list[dict], violations: list[dict]) -> float:
        return sum(
            self._GENERAL_SEVERITY_PENALTY.get(self._severity(item), 0)
            for item in findings + violations
        )

    def _score_completeness(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-602: Score completeness (sections, deliverables, requirements).

        Reduced by: missing sections, incomplete sections, missing acceptance criteria.
        """
        points = 100

        # Count missing-section findings
        missing_sections = [f for f in findings if "missing" in str(f).lower() and "section" in str(f).lower()]
        missing_sections += [v for v in violations if "missing section" in v.get("description", "").lower()]

        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 10) for i in missing_sections)

        # Count missing-criteria findings
        missing_criteria = [f for f in findings if "acceptance" in str(f).lower() or "criteria" in str(f).lower()]
        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 8) for i in missing_criteria)

        # Count incomplete-field findings
        incomplete = [v for v in violations if "incomplete" in v.get("description", "").lower()]
        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 5) for i in incomplete)

        points = max(0, min(100, points))

        return CategoryScore(
            category="completeness",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=missing_sections + missing_criteria + incomplete,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _score_clarity(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-603: Score clarity (ambiguous language, unclear terms, vague language).

        Reduced by: ambiguous findings, undefined terms, unclear language.
        """
        points = 100

        # Count ambiguous findings
        ambiguous = [
            f for f in findings
            if any(x in str(f).lower() for x in ["ambiguous", "unclear", "vague", "undefined"])
        ]
        ambiguous += [
            v for v in violations
            if any(x in v.get("description", "").lower() for x in ["ambiguous", "unclear", "vague"])
        ]

        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 12) for i in ambiguous)

        points = max(0, min(100, points))

        return CategoryScore(
            category="clarity",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=ambiguous,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _score_consistency(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-604: Score consistency (contradictions, inconsistent terms, repeated info).

        Reduced by: conflicting requirements, contradictory terms, inconsistencies.
        """
        points = 100

        # Count consistency issues
        inconsistent = [
            f for f in findings
            if any(x in str(f).lower() for x in ["conflict", "contradict", "inconsistent", "duplicate"])
        ]

        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 15) for i in inconsistent)

        points = max(0, min(100, points))

        return CategoryScore(
            category="consistency",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=inconsistent,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _score_commercial(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-605: Score commercial terms (pricing, payment, escalation, payment terms).

        Reduced by: missing pricing, ambiguous payment terms, missing escalation, payment gaps.
        """
        points = 100

        # Count commercial findings
        commercial_findings = [
            f for f in findings
            if any(x in str(f).lower() for x in ["pricing", "payment", "cost", "commercial"])
        ]
        commercial_findings += [
            v for v in violations
            if any(x in v.get("rule_id", "").lower() for x in ["sow-005", "sow-011"])  # Pricing rules
        ]

        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 20) for i in commercial_findings)

        points = max(0, min(100, points))

        return CategoryScore(
            category="commercial",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=commercial_findings,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _score_delivery(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-606: Score delivery (timeline, milestones, realistic dates).

        Reduced by: missing dates, unrealistic timeline, undefined dependencies.
        """
        points = 100

        # Count delivery findings
        delivery_findings = [
            f for f in findings
            if any(x in str(f).lower() for x in ["timeline", "milestone", "delivery", "schedule", "date"])
        ]
        delivery_findings += [
            v for v in violations
            if any(x in v.get("rule_id", "").lower() for x in ["sow-004", "sow-017", "sow-018"])  # Timeline rules
        ]

        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 15) for i in delivery_findings)

        points = max(0, min(100, points))

        return CategoryScore(
            category="delivery",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=delivery_findings,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _score_operations(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-607: Score operations (resources, assumptions, constraints, change control).

        Reduced by: missing resources, undefined assumptions, unclear constraints.
        """
        points = 100

        # Count operations findings. Keyword list extended 2026-07-17 to also
        # catch PMOReviewer findings (RACI/escalation/governance/SLA/entry-exit
        # criteria/fallback plan) -- those are operations-category concerns per
        # docs/planning/4_AI_AGENT_SPECS.md Agent 5, they just didn't exist as
        # a finding source before PMOReviewer was wired into the orchestrator.
        operations_findings = [
            f for f in findings
            if any(
                x in str(f).lower()
                for x in [
                    "resource", "assumption", "constraint", "operations",
                    "raci", "escalation", "governance", "sla",
                    "decision authority", "change management",
                    "entry criteria", "exit criteria", "fallback", "contingency",
                ]
            )
        ]
        operations_findings += [
            v for v in violations
            if any(x in v.get("rule_id", "").lower() for x in ["sow-007", "sow-014", "sow-019"])
        ]

        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 12) for i in operations_findings)

        points = max(0, min(100, points))

        return CategoryScore(
            category="operations",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=operations_findings,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _score_security(self, findings: list[dict], violations: list[dict]) -> CategoryScore:
        """
        T-608: Score security (compliance, data handling, audit rights, encryption).

        Reduced by: missing security controls, compliance gaps, audit gaps.
        """
        points = 100

        # Count security findings
        security_findings = [
            f for f in findings
            if any(x in str(f).lower() for x in ["security", "compliance", "audit", "encryption", "data"])
        ]
        security_findings += [
            v for v in violations
            if any(x in v.get("rule_id", "").lower() for x in ["sow-013"])  # Security rules
        ]

        # Security issues are more critical
        points -= sum(self._SPECIFIC_SEVERITY_PENALTY.get(self._severity(i), 25) for i in security_findings)

        points = max(0, min(100, points))

        return CategoryScore(
            category="security",
            score=float(points),
            max_points=100,
            points_earned=int(points),
            findings=security_findings,
            status="green" if points >= 80 else ("yellow" if points >= 50 else "red"),
        )

    def _calculate_overall_score(self, category_scores: dict[str, CategoryScore]) -> float:
        """
        T-609: Calculate overall score (weighted average of 7 categories).
        """
        total = 0.0
        for category, score_obj in category_scores.items():
            weight = self.weights.get(category, 0.0)
            total += score_obj.score * weight

        return round(total, 2)

    def _risk_raw_sum(self, items: list[dict]) -> float:
        """Sum of severity-weighted points across findings/violations."""
        return sum(self.risk_weights.get(self._severity(item), 0) for item in items)

    def _saturate(self, raw_sum: float, cap: float = 100.0) -> float:
        """Map a raw severity-weighted sum to 0-cap with diminishing returns.

        cap * (1 - e^(-k * raw_sum)) instead of a linear sum capped at cap:
        a linear+cap model saturates to the cap after just 4-5 critical
        findings (30 pts each already exceeds most reasonable caps), so
        every real-world document with several critical issues reads
        identically as "100, High" -- no signal left to distinguish "bad"
        from "catastrophic." The exponential curve keeps climbing (slower)
        past that point, so a 15-critical-finding document still scores
        visibly worse than a 5-critical-finding one instead of both
        pinning at the ceiling. Same RISK_SATURATION_K regardless of cap --
        1 - e^(-kx) approaches 1 at the same rate independent of the outer
        multiplier, so a lower cap is a scaled-down copy of the same curve
        shape, not a differently-calibrated one.
        """
        return round(cap * (1.0 - math.exp(-self.RISK_SATURATION_K * raw_sum)), 2)

    def _calculate_risk_score(self, findings: list[dict], violations: list[dict]) -> float:
        """
        T-614: Calculate risk score (0-100, higher = worse).

        Redesigned 2026-07-19 -- see RISK_SEVERITY_WEIGHTS/_saturate for why
        the old flat-sum-capped-at-100 model was replaced. Conceptually
        this approximates likelihood x impact (ISO 31000 / NIST SP 800-30
        risk-assessment framing): severity ~ impact, finding count ~
        likelihood signal, combined non-linearly rather than added and
        clipped.
        """
        return self._saturate(self._risk_raw_sum(findings + violations))

    def _calculate_risk_breakdown(self, findings: list[dict], violations: list[dict]) -> dict[str, float]:
        """Per-axis risk (Scope/Delivery/Commercial/Security/Governance/
        Legal/Compliance) so a customer can see WHICH kind of risk is high
        instead of one blended number. Same saturating curve as the
        overall risk score, computed independently per axis.
        """
        by_axis: dict[str, list[dict]] = {}

        for f in findings:
            axis = self.AXIS_BY_AGENT.get(f.get("source_agent", ""), "Other")
            by_axis.setdefault(axis, []).append(f)

        for v in violations:
            by_axis.setdefault("Compliance", []).append(v)

        return {axis: self._saturate(self._risk_raw_sum(items)) for axis, items in by_axis.items()}

    def _generate_summary(
        self,
        overall_score: float,
        risk_score: float,
        category_scores: dict[str, CategoryScore],
    ) -> str:
        """Generate executive summary."""
        # Determine health status
        if overall_score >= 80:
            health = "Strong"
        elif overall_score >= 60:
            health = "Moderate"
        else:
            health = "Weak"

        # Find worst categories
        worst = sorted(category_scores.items(), key=lambda x: x[1].score)[:2]
        worst_names = ", ".join([c[0].title() for c in worst])

        return (
            f"{health} document health (Score: {overall_score}/100). "
            f"Risk Level: {'High' if risk_score > 70 else 'Medium' if risk_score > 40 else 'Low'}. "
            f"Focus areas: {worst_names}."
        )

    def _generate_next_steps(
        self,
        category_scores: dict[str, CategoryScore],
        findings: list[dict],
        violations: list[dict],
    ) -> list[str]:
        """Generate recommended next steps."""
        steps = []

        # Add steps for low-scoring categories
        for category, score_obj in category_scores.items():
            if score_obj.score < 60 and category in CATEGORY_GUIDANCE:
                steps.append(CATEGORY_GUIDANCE[category])

        # Add critical issue steps. Checks both findings and rule_violations --
        # a critical AI-agent finding is just as urgent as a critical rule
        # violation, but only violations were checked here before.
        critical = [
            item for item in findings + violations
            if item.get("severity", "").lower() == "critical"
        ]
        if critical:
            steps.insert(0, f"Address {len(critical)} critical finding(s)")

        # Ensure we have at least 3 steps
        if not steps:
            steps.append("Document review complete. Minor refinements recommended.")

        return steps[:5]  # Return top 5 steps
