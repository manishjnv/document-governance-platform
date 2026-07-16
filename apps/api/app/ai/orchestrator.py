"""AI agent orchestrator for coordinating document reviews."""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from app.ai.agent import (
    CommercialReviewer,
    DeliveryReviewer,
    ScopeReviewer,
    SecurityReviewer,
)

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result from a single agent review."""

    agent_name: str
    findings: dict
    confidence: float
    duration_seconds: float
    error: Optional[str] = None


@dataclass
class OrchestratedReview:
    """Complete orchestrated review result."""

    doc_id: str
    status: str  # success | partial | failed
    results: list[ReviewResult]
    overall_confidence: float
    total_duration_seconds: float
    merged_findings: dict
    rule_violations: list = field(default_factory=list)  # T-509: Rule engine results


class ReviewOrchestrator:
    """
    Orchestrates multiple specialized AI agents.

    **T-401: Agent orchestrator pattern**
    **T-447: Orchestrator implementation**
    """

    def __init__(self):
        self.agents = [
            ScopeReviewer(),
            DeliveryReviewer(),
            CommercialReviewer(),
            SecurityReviewer(),
        ]
        self.initialized = False

    async def initialize(self):
        """Initialize all agents."""
        if self.initialized:
            return

        for agent in self.agents:
            await agent.initialize()

        self.initialized = True
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    async def review(self, doc_id: str, document_text: str, document_type: str = "SOW", sections: Optional[dict] = None) -> OrchestratedReview:
        """
        Run all agents in parallel and orchestrate results.

        **T-447: ReviewOrchestrator - call all 5 agents in parallel**
        **T-448: Agent fallback handling**
        **T-450: Async review task**
        **T-451: Review status tracking**
        **T-509: Run rule engine in parallel with AI agents**
        """
        if not self.initialized:
            await self.initialize()

        start_time = time.time()
        logger.info(f"Starting orchestrated review for {doc_id}")

        # Run all agents AND rule engine in parallel
        agent_tasks = [self._run_agent(agent, document_text) for agent in self.agents]
        rule_task = self._run_rule_engine(document_text, document_type, sections or {})

        all_tasks = agent_tasks + [rule_task]
        all_results = await asyncio.gather(*all_tasks, return_exceptions=False)

        # Split results: agents and rules
        results = [r for r in all_results[:-1] if r is not None]  # Agent results
        rule_violations = all_results[-1] or []  # Rule violations

        # Determine overall status
        successful = sum(1 for r in results if r.error is None)
        total_agents = len(self.agents)

        if successful == total_agents:
            status = "success"
        elif successful > 0:
            status = "partial"
        else:
            status = "failed"

        # Calculate overall confidence (average of agent confidences)
        confidences = [r.confidence for r in results if r.error is None]
        overall_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        total_duration = time.time() - start_time

        # Merge findings
        merged_findings = self._merge_findings(results)

        orchestrated_result = OrchestratedReview(
            doc_id=doc_id,
            status=status,
            results=results,
            overall_confidence=overall_confidence,
            total_duration_seconds=total_duration,
            merged_findings=merged_findings,
            rule_violations=[
                {
                    "rule_id": v.rule_id,
                    "rule_name": v.rule_name,
                    "severity": v.severity.value,
                    "description": v.description,
                    "evidence": v.evidence,
                    "recommendation": v.recommendation,
                }
                for v in rule_violations
            ],
        )

        logger.info(
            f"Review complete for {doc_id}: {status} "
            f"({successful}/{total_agents} agents, confidence {overall_confidence:.2f}, "
            f"{len(rule_violations)} rule violations, {total_duration:.1f}s)"
        )

        return orchestrated_result

    async def _run_rule_engine(self, document_text: str, document_type: str, sections: dict) -> list:
        """
        Run rule engine to validate document against configured rules.

        **T-509: Integrate rule engine with orchestrator**
        """
        start_time = time.time()

        try:
            from app.rules import get_rule_executor

            executor = await get_rule_executor()
            violations = await executor.validate(document_text, document_type, sections)

            duration = time.time() - start_time
            logger.info(f"Rule engine complete: {len(violations)} violations found in {duration:.1f}s")

            return violations

        except Exception as e:
            logger.error(f"Rule engine failed: {e}")
            return []

    async def _run_agent(
        self, agent, document_text: str
    ) -> Optional[ReviewResult]:
        """Run a single agent with error handling and timeout."""
        start_time = time.time()

        try:
            # T-409: Implement agent timeout (max 60 seconds)
            findings = await asyncio.wait_for(
                agent.review(document_text), timeout=60.0
            )

            # T-407: Confidence scoring
            confidence = findings.get("overall_confidence", 0.5)

            duration = time.time() - start_time

            return ReviewResult(
                agent_name=agent.name,
                findings=findings,
                confidence=confidence,
                duration_seconds=duration,
            )

        except asyncio.TimeoutError:
            duration = time.time() - start_time
            logger.warning(f"{agent.name} timed out after {duration:.1f}s")
            return ReviewResult(
                agent_name=agent.name,
                findings={},
                confidence=0.0,
                duration_seconds=duration,
                error="timeout",
            )

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"{agent.name} failed: {e}")
            # T-448: Agent fallback (continue with other agents)
            return ReviewResult(
                agent_name=agent.name,
                findings={},
                confidence=0.0,
                duration_seconds=duration,
                error=str(e),
            )

    def _merge_findings(self, results: list[ReviewResult]) -> dict:
        """Merge findings from all agents into unified structure."""
        merged = {
            "findings": [],
            "agents": {},
        }

        for result in results:
            if result.error:
                merged["agents"][result.agent_name] = {
                    "status": "error",
                    "error": result.error,
                }
            else:
                merged["agents"][result.agent_name] = {
                    "status": "success",
                    "findings": result.findings,
                    "confidence": result.confidence,
                    "duration_seconds": result.duration_seconds,
                }

                # Extract findings from agent result
                if "findings" in result.findings:
                    for finding in result.findings["findings"]:
                        finding["source_agent"] = result.agent_name
                        merged["findings"].append(finding)

        return merged
