"""Base AI agent class for document review."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


class _OpenRouterMessage:
    def __init__(self, text: str):
        self.content = [type("Block", (), {"text": text})()]


class _OpenRouterMessages:
    """Mimics Anthropic's `client.messages` surface but calls OpenRouter's
    OpenAI-compatible chat completions endpoint. Lets ReviewAgent.review()
    stay provider-agnostic instead of branching on which SDK is active.
    """

    def __init__(self, client):
        self._client = client

    def create(self, model, max_tokens, temperature, system, messages):
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[{"role": "system", "content": system}, *messages],
        )
        return _OpenRouterMessage(response.choices[0].message.content)


class _OpenRouterClient:
    def __init__(self, api_key: str):
        from openai import OpenAI

        self.messages = _OpenRouterMessages(
            OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        )


class ReviewAgent(ABC):
    """
    Abstract base class for document review agents.

    **T-403: Agent base class**
    Each agent handles a specific review dimension.
    """

    def __init__(self, name: str, model: str = "claude-3-5-sonnet-20241022"):
        self.name = name
        self.model = model
        self.client = None
        self._fallback_models: list[str] = []

    async def initialize(self):
        """Initialize agent with API client.

        Uses OpenRouter (OpenAI-compatible) when settings.openrouter_api_key
        is set, else falls back to the default Anthropic client.
        """
        from app.config import settings

        if settings.openrouter_api_key:
            self.model = settings.openrouter_model
            self._fallback_models = list(settings.openrouter_fallback_models)
            self.client = _OpenRouterClient(settings.openrouter_api_key)
            logger.info(f"Agent '{self.name}' initialized with OpenRouter model {self.model}")
            return

        try:
            from anthropic import Anthropic

            self.client = Anthropic()
            logger.info(f"Agent '{self.name}' initialized with {self.model}")
        except ImportError:
            logger.error("anthropic SDK not installed")
            raise

    @abstractmethod
    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """Return the system prompt for this agent.

        document_type: "SOW" | "RFP" (docs/planning/4_AI_AGENT_SPECS.md
        "Document Type Coverage: SOW vs RFP" -- RFPs evaluate vendors
        rather than define delivered work, so each agent branches its
        instructions rather than assuming a signed SOW.
        """
        pass

    @abstractmethod
    def get_output_schema(self) -> dict:
        """Return the JSON schema for expected output."""
        pass

    async def review(self, document_text: str, document_type: str = "SOW") -> dict:
        """
        Review document and return structured findings.

        **T-406: Structured output parser**
        **T-407: Confidence scoring**
        """
        if not self.client:
            await self.initialize()

        try:
            logger.info(f"{self.name}: Starting review...")

            # Primary model + fallback chain (customer is waiting on this
            # call, so a single provider hiccup/429 shouldn't fail the
            # review outright).
            models_to_try = [self.model, *self._fallback_models]
            response = None
            last_error = None
            for attempt, model in enumerate(models_to_try):
                try:
                    # to_thread: self.client (Anthropic or the OpenRouter
                    # adapter) is a synchronous SDK call -- awaiting it
                    # directly would block the whole event loop for the
                    # entire ~10-90s request, freezing every other
                    # concurrent request (login, search, dashboard) on
                    # this single-worker dev server until it returns.
                    response = await asyncio.to_thread(
                        self.client.messages.create,
                        model=model,
                        max_tokens=4000,
                        temperature=0.7,
                        system=self.get_system_prompt(document_type),
                        messages=[
                            {
                                "role": "user",
                                "content": f"Please review this document and provide findings in JSON format:\n\n{document_text}",
                            }
                        ],
                    )
                    if attempt > 0:
                        logger.warning(f"{self.name}: succeeded on fallback model {model}")
                    break
                except Exception as e:
                    last_error = e
                    logger.warning(f"{self.name}: model {model} failed ({e}), trying next")
            if response is None:
                raise last_error

            # Extract text response
            response_text = response.content[0].text

            # Try to parse JSON from response
            try:
                # Look for JSON block
                import re

                json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group(1))
                else:
                    # Try parsing the whole response as JSON
                    result = json.loads(response_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw text
                logger.warning(f"{self.name}: Could not parse JSON response")
                result = {
                    "raw_response": response_text,
                    "confidence": 0.5,
                    "findings": [],
                }

            logger.info(f"{self.name}: Review complete")
            return result

        except Exception as e:
            logger.error(f"{self.name}: Review failed - {e}")
            raise

    def validate_output(self, output: dict) -> bool:
        """Validate output against schema. Can be overridden."""
        required_fields = self.get_output_schema().get("required", [])
        return all(field in output for field in required_fields)


class ScopeReviewer(ReviewAgent):
    """Reviews document scope and deliverables."""

    def __init__(self):
        super().__init__("ScopeReviewer")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """T-411: Scope Reviewer system prompt.

        RFP branch (added 2026-07-17, docs/planning/4_AI_AGENT_SPECS.md
        Document Type Coverage table): RFPs ask for evaluation criteria and
        the scope of the REQUESTED proposal, not delivered work -- there
        are no "deliverables" or "acceptance criteria" to extract yet.
        """
        if document_type == "RFP":
            doc_branch = """This document is an RFP (Request for Proposal), not a SOW. Analyze it and:

1. Extract the SCOPE OF THE REQUESTED PROPOSAL
   - What work/product is the issuer soliciting proposals for?
   - What must a compliant proposal cover?
2. Extract EVALUATION CRITERIA
   - How will submitted proposals be scored/evaluated?
   - Are weightings or scoring rubrics disclosed?
3. Detect scope boundaries for what vendors are being asked to propose on
4. Find ambiguous or missing evaluation criteria
5. Identify scope-creep-style risks: is the requested scope open-ended or unbounded for bidders to price?
"""
        else:
            doc_branch = """You are an expert project scope reviewer. Analyze the provided document and:

1. Extract all deliverables mentioned
2. Identify acceptance criteria for each deliverable
3. Detect scope boundaries and constraints
4. Find ambiguous or missing acceptance criteria
5. Identify potential scope creep indicators
"""

        return doc_branch + """
Provide your response as a JSON object with this structure:
{
    "deliverables": [
        {
            "name": "string",
            "description": "string",
            "acceptance_criteria": ["string"],
            "confidence": 0.0-1.0
        }
    ],
    "scope_boundaries": {
        "included": ["string"],
        "excluded": ["string"]
    },
    "findings": [
        {
            "type": "missing_criteria|ambiguous|scope_creep",
            "severity": "critical|major|medium|low",
            "description": "string",
            "evidence": "string",
            "recommendation": "string",
            "confidence": 0.0-1.0
        }
    ],
    "overall_confidence": 0.0-1.0
}"""

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["deliverables", "findings", "overall_confidence"],
            "properties": {
                "deliverables": {"type": "array"},
                "findings": {"type": "array"},
                "overall_confidence": {"type": "number"},
            },
        }


class DeliveryReviewer(ReviewAgent):
    """Reviews delivery timelines and project plan."""

    def __init__(self):
        super().__init__("DeliveryReviewer")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """T-419: Delivery Reviewer system prompt.

        RFP branch (2026-07-17): an RFP's "delivery" dates are the
        submission deadline, Q&A window, and award date -- not project
        milestones, since no work has been awarded yet.
        """
        if document_type == "RFP":
            doc_branch = """You are an expert procurement-process analyst. This document is an RFP (Request for Proposal). Analyze it for:

1. Submission deadline (date and time proposals are due)
2. Q&A / clarification window (when vendors can ask questions, when answers are published)
3. Award date / decision timeline (when the winning vendor will be notified)
4. Missing or unclear process dates
5. Risk indicators: unrealistic turnaround between Q&A close and submission, or no award timeline at all
"""
        else:
            doc_branch = """You are an expert project delivery analyst. Analyze the document for:

1. Timeline and milestones
2. Dependencies and critical path
3. Realistic assumptions about dates
4. Missing or unclear delivery dates
5. Risk indicators in the schedule
"""

        return doc_branch + """
Provide findings as JSON with:
{
    "timeline": {
        "start_date": "YYYY-MM-DD or null",
        "end_date": "YYYY-MM-DD or null",
        "milestones": [{"name": "string", "date": "YYYY-MM-DD", "confidence": 0.0-1.0}]
    },
    "dependencies": ["string"],
    "findings": [
        {
            "type": "missing_dates|unrealistic|undefined_dependency",
            "severity": "critical|major|medium|low",
            "description": "string",
            "confidence": 0.0-1.0
        }
    ],
    "overall_confidence": 0.0-1.0
}"""

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["timeline", "findings", "overall_confidence"],
        }


class CommercialReviewer(ReviewAgent):
    """Reviews commercial terms and pricing."""

    def __init__(self):
        super().__init__("CommercialReviewer")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """T-426: Commercial Reviewer system prompt.

        RFP branch (2026-07-17): an RFP rarely fixes a price -- it should
        disclose a budget range (or explicitly withhold one) and specify
        the pricing FORMAT it requires vendors to submit, not a fixed
        pricing model/payment schedule.
        """
        if document_type == "RFP":
            doc_branch = """You are an expert commercial/procurement analyst. This document is an RFP (Request for Proposal). Analyze for:

1. Budget range disclosure (is a budget or budget range given to bidders, or explicitly withheld?)
2. Pricing format required from vendors (e.g., fixed price vs. T&M breakdown, itemized vs. lump sum)
3. Cost evaluation weighting (how much does price factor into award, relative to other criteria?)
4. Ambiguous commercial language in what's being asked of bidders
5. Missing guidance that would cause incomparable vendor pricing (e.g., no required pricing template)
"""
        else:
            doc_branch = """You are an expert commercial analyst. Analyze for:

1. Pricing model and payment terms
2. Price escalation clauses
3. Out-of-scope pricing
4. Invoice timing and conditions
5. Ambiguous commercial language
"""

        return doc_branch + """
Provide findings as:
{
    "pricing": {
        "model": "fixed|time_and_materials|other",
        "total_amount": "decimal or null",
        "currency": "string",
        "payment_schedule": ["string"]
    },
    "findings": [
        {
            "type": "ambiguous_pricing|missing_terms|escalation_gap",
            "severity": "critical|major|medium|low",
            "description": "string",
            "confidence": 0.0-1.0
        }
    ],
    "overall_confidence": 0.0-1.0
}"""

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["pricing", "findings", "overall_confidence"],
        }


class SecurityReviewer(ReviewAgent):
    """Reviews security and compliance requirements."""

    def __init__(self):
        super().__init__("SecurityReviewer")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """T-433: Security Reviewer system prompt.

        document_type-conditional per docs/planning/4_AI_AGENT_SPECS.md's
        implementation requirement ("give each agent's system prompt a
        document_type-conditional instruction block") -- the spec's SOW-vs-RFP
        table doesn't define an RFP-specific security analysis (unlike
        Scope/Delivery/Commercial), so this branch narrows scope to what
        security posture an RFP can actually specify: REQUIRED security
        standards for bidders, not an executed vendor's controls.
        """
        if document_type == "RFP":
            doc_branch = """You are a security and compliance expert. This document is an RFP (Request for Proposal) -- evaluate what security/compliance standards it REQUIRES of bidding vendors (not a signed vendor's actual controls, which don't exist yet). Analyze for:

1. Security/compliance standards required of vendors (SOC2, ISO27001, etc.)
2. Data handling and privacy requirements imposed on bidders
3. Audit rights the issuer reserves over the eventual vendor
4. Encryption and access control requirements stated as a bidding requirement
5. Missing security requirements that should have been specified before award
"""
        else:
            doc_branch = """You are a security and compliance expert. Analyze for:

1. Security requirements and standards (SOC2, ISO27001, etc.)
2. Data handling and privacy clauses
3. Audit rights and compliance obligations
4. Encryption and access control requirements
5. Missing security controls
"""

        return doc_branch + """
Provide findings as:
{
    "compliance_requirements": ["SOC2", "ISO27001", ...],
    "security_controls": ["string"],
    "findings": [
        {
            "type": "missing_clause|compliance_gap|audit_gap",
            "severity": "critical|major|medium|low",
            "description": "string",
            "confidence": 0.0-1.0
        }
    ],
    "overall_confidence": 0.0-1.0
}"""

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["findings", "overall_confidence"],
        }


class PMOReviewer(ReviewAgent):
    """Reviews project governance, RACI, escalation, and operational risks.

    T-2101: net-new (2026-07-17) -- spec'd in docs/planning/4_AI_AGENT_SPECS.md
    "Agent 5: Project Operations (PMO) Reviewer" but never wired into
    orchestrator.py (only 4 of the original 5 agents were built). Includes
    the 2026-07-17 spec extension for entry/exit criteria and
    fallback/contingency-plan detection.
    """

    def __init__(self):
        super().__init__("PMOReviewer")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """PMO Reviewer system prompt (governance, RACI, escalation, SLAs,
        change management, entry/exit criteria, fallback plan).

        RFP branch (2026-07-17): an RFP has no live engagement to govern
        yet -- ask instead whether the RFP itself DEFINES the governance
        model bidders will be held to post-award (RACI, escalation, SLAs
        expected of the winning vendor), and whether contingency/fallback
        expectations are set as evaluation criteria.
        """
        if document_type == "RFP":
            doc_branch = """You are an expert project governance analyst. This document is an RFP (Request for Proposal) -- there is no live engagement to govern yet, so evaluate whether the RFP DEFINES the governance model the winning vendor will be held to. Analyze for:

1. Does the RFP specify the RACI/governance structure vendors must propose or accept?
2. Does the RFP define the escalation path / decision authority expected post-award?
3. Are SLA expectations (response/resolution times, uptime) specified as requirements for bidders to meet or propose against?
4. Does the RFP define change management expectations for the eventual engagement?
5. Does the RFP define entry criteria (what must be true before the awarded work starts) and exit/completion criteria bidders must propose against?
6. Does the RFP require or invite a fallback/contingency/rollback plan from bidders?
"""
        else:
            doc_branch = """You are an expert project operations and governance analyst. Analyze the document for:

1. GOVERNANCE & RACI
   - Is a RACI matrix defined? (Responsible, Accountable, Consulted, Informed)
   - Who owns what? (e.g., "vendor owns infrastructure, customer owns applications")
   - What is the governance structure? (steering committee, working groups)

2. ESCALATION & DECISIONS
   - What is the escalation path for issues/risks?
   - Who has decision authority at each level?
   - What is the decision timeline?

3. SLAs & OPERATIONAL TERMS
   - Are Service Level Agreements defined? (if ongoing work)
   - What are the response/resolution times, uptime commitments, support hours?

4. CHANGE MANAGEMENT
   - How are changes approved? Who has change authority? Change windows defined?

5. ENTRY & EXIT CRITERIA
   - Are entry criteria defined? (what must be true before work starts)
   - Are exit/completion criteria defined? (what must be true to consider work done/accepted)
   - Is there a documented fallback, contingency, or rollback plan if the engagement fails or is terminated early?

RACI is critical. Missing RACI = major risk. Entry/exit criteria and fallback plan are critical for fixed-scope engagements; major for ongoing/retainer engagements.
"""

        return doc_branch + """
IMPORTANT: Quote governance language directly. Only report what you find; don't speculate. Rate confidence in each finding (0-100 scaled to 0.0-1.0).

Provide your response as a JSON object with this structure:
{
    "governance": {
        "raci_matrix_present": true|false,
        "escalation_levels": ["string"],
        "sla_defined": true|false,
        "entry_exit_criteria_defined": true|false,
        "fallback_plan_defined": true|false
    },
    "findings": [
        {
            "type": "missing_raci|undefined_escalation|unclear_decision_authority|missing_sla|missing_entry_exit_criteria|missing_fallback_plan",
            "severity": "critical|major|medium|low",
            "description": "string",
            "evidence": "string",
            "recommendation": "string",
            "confidence": 0.0-1.0
        }
    ],
    "overall_confidence": 0.0-1.0
}"""

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["governance", "findings", "overall_confidence"],
        }


class LegalReviewer(ReviewAgent):
    """Reviews legal risk: liability, IP, indemnification, termination,
    governing law, warranty.

    T-2102: net-new (2026-07-17), docs/planning/4_AI_AGENT_SPECS.md
    "Agent 6: Legal Reviewer". Distinct from Commercial (pricing/payment)
    and PMO (governance/operations).
    """

    def __init__(self):
        super().__init__("LegalReviewer")

    def get_system_prompt(self, document_type: str = "SOW") -> str:
        """Legal Reviewer system prompt (liability, IP, termination,
        governing law, warranty).

        RFP branch (2026-07-17): an RFP has no executed legal terms to
        analyze -- ask instead whether it DISCLOSES the legal terms
        bidders will be bound to (a "contract terms preview"), since
        vendors need this to price and accept risk before submitting.
        """
        if document_type == "RFP":
            doc_branch = """You are an expert commercial-contracts lawyer. This document is an RFP (Request for Proposal) -- there is no executed contract yet, so evaluate whether it DISCLOSES the legal terms bidders will be bound to if awarded. Analyze for:

1. Does the RFP disclose the liability/indemnification terms the winning vendor will be held to?
2. Does the RFP state who will own IP in the delivered work, or defer this to contract negotiation?
3. Does the RFP disclose termination terms (for cause / for convenience) that will apply post-award?
4. Is governing law / jurisdiction disclosed for the eventual contract?
5. Are warranty expectations disclosed?
6. Flag ambiguous legal language in what's being asked of bidders (e.g., "standard terms apply" with no attachment).

Missing legal-terms disclosure in an RFP is a risk to VENDORS pricing the bid, and to the ISSUER if it invites disputes over undisclosed terms later -- flag it as such, don't assume it's automatically critical the way an unsigned SOW clause would be.
"""
        else:
            doc_branch = """You are an expert commercial-contracts lawyer reviewing this document. Analyze for:

1. LIABILITY & INDEMNIFICATION
   - Is there a limitation of liability clause? What is the cap?
   - Is indemnification defined? Which party indemnifies whom, for what?

2. INTELLECTUAL PROPERTY
   - Who owns work product / deliverables IP?
   - Are pre-existing IP rights (background IP) addressed?
   - Are third-party/open-source license obligations addressed?

3. TERMINATION
   - Termination for cause: defined, with cure period?
   - Termination for convenience: defined, with notice period?
   - What happens to in-progress work / payment on termination?

4. GOVERNING LAW & DISPUTE RESOLUTION
   - Governing law / jurisdiction specified? Arbitration or litigation? Venue specified?

5. WARRANTY
   - Is there a warranty clause? Disclaimer of implied warranties?

Flag ambiguous legal language explicitly (e.g., "reasonable efforts", "as applicable") as a finding, not just missing clauses.
"""

        return doc_branch + """
IMPORTANT: Quote the exact clause language as evidence. Rate confidence in each finding (0-100 scaled to 0.0-1.0).

Provide your response as a JSON object with this structure:
{
    "legal_terms": {
        "liability_cap": "string or null",
        "indemnification_defined": true|false,
        "ip_ownership": "vendor|customer|joint|undefined",
        "termination_for_cause": true|false,
        "governing_law": "string or null",
        "warranty_defined": true|false
    },
    "findings": [
        {
            "type": "missing_liability_cap|undefined_ip_ownership|missing_termination_clause|no_governing_law|missing_warranty|ambiguous_legal_language",
            "severity": "critical|major|medium|low",
            "description": "string",
            "evidence": "string",
            "recommendation": "string",
            "confidence": 0.0-1.0
        }
    ],
    "overall_confidence": 0.0-1.0
}"""

    def get_output_schema(self) -> dict:
        return {
            "type": "object",
            "required": ["legal_terms", "findings", "overall_confidence"],
        }
