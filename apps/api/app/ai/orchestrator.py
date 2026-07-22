"""AI agent orchestrator for coordinating document reviews."""

import asyncio
import difflib
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Optional

from app.ai.agent import (
    CommercialReviewer,
    DeliveryReviewer,
    LegalReviewer,
    PMOReviewer,
    ScopeReviewer,
    SecurityReviewer,
)

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {"critical": 4, "major": 3, "medium": 2, "low": 1}

# Self-negating findings: an agent occasionally emits a "finding" whose own
# description says there is nothing wrong ("Missing Accessibility Standard --
# ...requirement is not applicable to this SOW", shipped to a real user,
# 2026-07-22 accuracy baseline). The prompts now say to omit these, but the
# model is probabilistic -- this deterministic backstop drops them before
# persistence. "is compliant" deliberately does not match "is not compliant".
_SELF_NEGATING = re.compile(
    r"\b(not applicable|no issues? (?:were |was )?(?:found|identified)"
    r"|no concerns? (?:were |was )?(?:found|identified)"
    r"|does not apply|is (?:fully )?compliant)\b",
    re.IGNORECASE,
)


def _is_self_negating(finding: dict) -> bool:
    head = str(finding.get("description") or finding.get("title") or "")[:300]
    return bool(_SELF_NEGATING.search(head))


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
            PMOReviewer(),
            LegalReviewer(),
        ]
        self.initialized = False

        # ponytail: evidence-text fuzzy match via stdlib difflib, not an
        # embedding model -- findings quote the document verbatim, so
        # lexical overlap is a strong same-issue signal without adding an
        # ML dependency. Revisit if evidence-text dedup proves insufficient.
        self.dedupe_similarity_threshold = 0.82
        self.dedupe_min_evidence_length = 20

    async def initialize(self):
        """Initialize all agents."""
        if self.initialized:
            return

        for agent in self.agents:
            await agent.initialize()

        self.initialized = True
        logger.info(f"Orchestrator initialized with {len(self.agents)} agents")

    async def review(
        self,
        doc_id: str,
        document_text: str,
        document_type: str = "SOW",
        sections: Optional[dict] = None,
        enabled_agent_names: Optional[set[str]] = None,
        enabled_rule_ids: Optional[set[str]] = None,
    ) -> OrchestratedReview:
        """
        Run all agents in parallel and orchestrate results.

        **T-447: ReviewOrchestrator - call all 5 agents in parallel**
        **T-448: Agent fallback handling**
        **T-450: Async review task**
        **T-451: Review status tracking**
        **T-509: Run rule engine in parallel with AI agents**

        enabled_agent_names / enabled_rule_ids: T-2091/T-2092 per-org
        customization (app/admin/customization.py). None means unrestricted
        (all agents/rules) -- this is a shared global instance across orgs,
        so filtering happens per-call, never by mutating self.agents.
        """
        if not self.initialized:
            await self.initialize()

        start_time = time.time()
        logger.info(f"Starting orchestrated review for {doc_id}")

        active_agents = (
            self.agents
            if enabled_agent_names is None
            else [a for a in self.agents if a.name in enabled_agent_names]
        )

        # Run all agents AND rule engine AND ambiguous-language scan in parallel
        agent_tasks = [
            self._run_agent(agent, document_text, document_type) for agent in active_agents
        ]
        rule_task = self._run_rule_engine(
            document_text, document_type, sections or {}, enabled_rule_ids
        )
        ambiguous_task = self._run_ambiguous_language_scan(document_text, sections or {})

        all_tasks = agent_tasks + [rule_task, ambiguous_task]
        all_results = await asyncio.gather(*all_tasks, return_exceptions=False)

        # Split results: agents, rule-engine violations, ambiguous-language violations
        results = [r for r in all_results[:-2] if r is not None]  # Agent results
        rule_violations = (all_results[-2] or []) + (all_results[-1] or [])  # Rule + ambiguous-language

        # Determine overall status
        successful = sum(1 for r in results if r.error is None)
        total_agents = len(active_agents)

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

    async def _run_rule_engine(
        self,
        document_text: str,
        document_type: str,
        sections: dict,
        enabled_rule_ids: Optional[set[str]] = None,
    ) -> list:
        """
        Run rule engine to validate document against configured rules.

        **T-509: Integrate rule engine with orchestrator**
        """
        start_time = time.time()

        try:
            from app.rules import get_rule_executor

            executor = await get_rule_executor()
            violations = await executor.validate(
                document_text, document_type, sections, enabled_rule_ids
            )

            duration = time.time() - start_time
            logger.info(f"Rule engine complete: {len(violations)} violations found in {duration:.1f}s")

            return violations

        except Exception as e:
            logger.error(f"Rule engine failed: {e}")
            return []

    async def _run_ambiguous_language_scan(
        self, document_text: str, sections: dict
    ) -> list:
        """
        Run the rule-based ambiguous-language scanner (not an LLM agent).

        **T-2103: ambiguous-language cross-cutting scan, added 2026-07-17**
        docs/planning/4_AI_AGENT_SPECS.md "Cross-Cutting: Ambiguous Language
        Detector" -- runs against the full document text for every
        document type, in the same parallel fan-out as the rule engine.
        """
        start_time = time.time()

        try:
            from app.rules.ambiguous_language import scan_ambiguous_language

            violations = scan_ambiguous_language(document_text, sections)

            duration = time.time() - start_time
            logger.info(
                f"Ambiguous-language scan complete: {len(violations)} phrases flagged in {duration:.1f}s"
            )

            return violations

        except Exception as e:
            logger.error(f"Ambiguous-language scan failed: {e}")
            return []

    # T-409: agent timeout, plus one retry at a longer window (2026-07-20).
    # A live smoke test against real OpenRouter output found a DIFFERENT
    # agent hitting the 60s ceiling on each of 2 runs (not the same one
    # each time) -- that's response-latency variance from the model
    # backend, not a per-agent prompt-length problem. Losing an entire
    # agent's findings to one slow response is a real accuracy cost, so
    # one retry at a longer window trades worst-case latency for not
    # silently dropping a whole agent's output. Retry window is 120s, not
    # 90s: on a real 46-page federal contract (~30K input tokens),
    # SecurityReviewer exhausted 60s+90s while LegalReviewer's successful
    # retry ran ~65s -- large documents legitimately need the headroom.
    # ponytail: fixed windows, not scaled-by-document-length; revisit if
    # even 120s proves insufficient on real customer documents.
    _AGENT_TIMEOUTS_SECONDS = (60.0, 120.0)

    async def _run_agent(
        self, agent, document_text: str, document_type: str = "SOW"
    ) -> Optional[ReviewResult]:
        """Run a single agent with error handling, timeout, and one retry
        on timeout specifically (non-timeout errors already get a
        fallback-model chain inside agent.review() itself, so they're not
        retried again here)."""
        start_time = time.time()

        for attempt, timeout in enumerate(self._AGENT_TIMEOUTS_SECONDS):
            try:
                findings = await asyncio.wait_for(
                    agent.review(document_text, document_type), timeout=timeout
                )

                # T-407: Confidence scoring
                confidence = findings.get("overall_confidence", 0.5)

                duration = time.time() - start_time
                if attempt > 0:
                    logger.warning(f"{agent.name}: succeeded on timeout retry")

                return ReviewResult(
                    agent_name=agent.name,
                    findings=findings,
                    confidence=confidence,
                    duration_seconds=duration,
                )

            except asyncio.TimeoutError:
                logger.warning(
                    f"{agent.name} timed out after {timeout:.0f}s "
                    f"(attempt {attempt + 1}/{len(self._AGENT_TIMEOUTS_SECONDS)})"
                )
                continue

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

        # Every attempt timed out.
        duration = time.time() - start_time
        logger.warning(f"{agent.name} timed out after {duration:.1f}s (all retries exhausted)")
        return ReviewResult(
            agent_name=agent.name,
            findings={},
            confidence=0.0,
            duration_seconds=duration,
            error="timeout",
        )

    def _merge_findings(self, results: list[ReviewResult]) -> dict:
        """Merge findings from all agents into unified structure, then
        collapse cross-agent duplicates (same underlying issue reported by
        more than one agent) into a single finding -- Metric 1.4."""
        merged = {
            "findings": [],
            "agents": {},
        }

        raw_findings = []
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
                        if _is_self_negating(finding):
                            logger.info(
                                f"Dropped self-negating finding from {result.agent_name}: "
                                f"{str(finding.get('title') or finding.get('description'))[:80]}"
                            )
                            continue
                        finding["source_agent"] = result.agent_name
                        raw_findings.append(finding)

        merged["findings"] = self._dedupe_findings(raw_findings)
        return merged

    def _dedupe_findings(self, findings: list[dict]) -> list[dict]:
        """Collapses findings from DIFFERENT agents that quote the same (or
        near-identical) evidence text into one finding. Same-agent
        duplicates are left alone -- that's more likely a prompt/parsing
        issue worth surfacing, not cross-agent corroboration. A
        conservative similarity threshold plus a minimum evidence length
        keep false merges at zero per the launch criteria's "0 false
        merges" requirement, at the cost of some missed merges on short or
        vague evidence (tolerated up to <1% per spec) -- findings with no
        evidence, or evidence too short to compare reliably, are never
        merged."""
        n = len(findings)
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[ri] = rj

        for i in range(n):
            evidence_i = (findings[i].get("evidence") or "").strip().lower()
            if len(evidence_i) < self.dedupe_min_evidence_length:
                continue
            for j in range(i + 1, n):
                if findings[i]["source_agent"] == findings[j]["source_agent"]:
                    continue
                evidence_j = (findings[j].get("evidence") or "").strip().lower()
                if len(evidence_j) < self.dedupe_min_evidence_length:
                    continue
                ratio = difflib.SequenceMatcher(None, evidence_i, evidence_j).ratio()
                if ratio >= self.dedupe_similarity_threshold:
                    union(i, j)

        groups: dict[int, list[dict]] = {}
        for i in range(n):
            groups.setdefault(find(i), []).append(findings[i])

        deduped = []
        for group in groups.values():
            deduped.append(group[0] if len(group) == 1 else self._combine_findings(group))
        return deduped

    def _combine_findings(self, group: list[dict]) -> dict:
        """Merges a group of duplicate findings into one: the
        highest-confidence finding's fields are the base, severity is the
        most severe reported (a corroborated finding shouldn't lose
        severity), evidence and contributing agents are combined."""
        base = max(group, key=lambda f: f.get("confidence", 0))
        agents = sorted({f["source_agent"] for f in group})
        top_severity = max(
            (f.get("severity", "medium").lower() for f in group),
            key=lambda s: _SEVERITY_RANK.get(s, 0),
        )
        evidences = []
        for f in group:
            ev = (f.get("evidence") or "").strip()
            if ev and ev not in evidences:
                evidences.append(ev)

        merged = dict(base)
        merged["severity"] = top_severity
        merged["evidence"] = " | ".join(evidences) if evidences else base.get("evidence")
        merged["source_agent"] = ", ".join(agents)[:100]  # matches Finding.agent_name String(100)
        merged["merged_from_agents"] = agents
        merged["confidence"] = max(f.get("confidence", 0) for f in group)
        return merged
