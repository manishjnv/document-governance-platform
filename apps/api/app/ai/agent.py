"""Base AI agent class for document review."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Shared across all 6 agents (2026-07-20 prompt-accuracy pass -- see
# docs/planning/PROMPT_ENGINEERING_GUIDE.md). Targets the measured
# calibration gap from the 2026-07-18 accuracy pass
# (docs/planning/5_LAUNCH_CRITERIA.md Metric 1.3): structured-field
# extraction was right 75% of the time while stated confidence clustered
# at 80-100% -- models were defaulting to a "safe middle" score instead of
# actually discriminating between "I'm quoting exact text" and "I'm
# inferring from absence." This rubric gives concrete anchors instead of
# leaving confidence to the model's own untethered judgment.
_CONFIDENCE_CALIBRATION = """
CONFIDENCE CALIBRATION -- score EACH finding independently, not the review as a whole:
- 0.85-1.0: you are quoting exact clause text: the fact is explicitly and unambiguously stated.
- 0.60-0.84: the clause is present but requires interpretation, OR you're inferring it from a
  section that plausibly-but-not-certainly covers this point (e.g. general terms elsewhere).
- 0.30-0.59: you are inferring ABSENCE or ambiguity from what's not stated. There may be an
  attachment, exhibit, or referenced-but-not-included document you can't see -- account for that.
- Below 0.30: you are guessing, or the document is too fragmentary to judge reliably.
Do NOT default to 0.8-0.9 as a "safe middle" score. If you are not quoting exact text, your
confidence should usually be below 0.7. A finding you're genuinely unsure about with a low
confidence score is more useful than a false-certain one -- it tells the reader where to look
harder, rather than implying the AI already checked thoroughly.
"""


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
                        # 4000 (docs/planning/AI_MODEL_ROUTING.md's Round 2 fix)
                        # was validated against a 3.7K-char test document only
                        # -- that doc's own "Known gaps" section flagged
                        # "longer real-world documents may need a higher
                        # ceiling, no scaling test was done." Confirmed
                        # 2026-07-20 against a real 119K-char/30K-token
                        # federal contract: GLM-5.2 hit finish_reason="length"
                        # and returned truncated, unparseable JSON at 4000.
                        # Raising the ceiling costs nothing for calls that
                        # don't need it (OpenRouter bills actual completion
                        # tokens generated, not the max allowed).
                        max_tokens=8000,
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
6. Check for EXPLICIT EXCLUSIONS -- does the document state what is NOT included, or only
   what is? A deliverables list with no exclusions is a common scope-creep entry point: anything
   not explicitly excluded tends to get argued into scope later.
7. Check for UNSTATED CLIENT-SIDE ASSUMPTIONS -- does delivery depend on the client providing
   access, approvals, data, or decisions on a timeline the document never actually commits the
   client to? An assumption that's never stated as a dependency is a risk the vendor is silently
   carrying alone.

Note: a deterministic rule engine already checks for the PRESENCE of an "Assumptions and
Constraints" section by keyword/section match -- your job is to judge the QUALITY of what's
there (or the risk of what's silently missing), not just restate that a section exists.
"""

        return doc_branch + _CONFIDENCE_CALIBRATION + """
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
            "type": "missing_criteria|ambiguous|scope_creep|missing_exclusions|unstated_assumption",
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
6. STAFFING/RESOURCE AVAILABILITY -- does the schedule depend on named individuals, a specific
   team size, or specialist roles the document never confirms are actually available for the
   stated dates? A timeline with no named or role-based resourcing behind it is optimistic by
   default, not realistic.
7. SCHEDULE BUFFER -- is there any contingency/buffer time built in, or does every milestone
   assume zero slippage anywhere upstream? A schedule with zero slack across multiple sequential
   dependencies is a specific, callable-out risk, not just "aggressive."
"""

        return doc_branch + _CONFIDENCE_CALIBRATION + """
IMPORTANT: Quote the exact document language as evidence for each finding, even when the finding
is about something MISSING -- quote the section header or nearby text that should have contained
it, so the finding can be located in the document. Only omit evidence when nothing in the document
is relevant to quote (e.g. the entire timeline concept is absent).

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
            "type": "missing_dates|unrealistic|undefined_dependency|unconfirmed_staffing|no_schedule_buffer",
            "severity": "critical|major|medium|low",
            "description": "string",
            "evidence": "string",
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
6. RENEWAL/AUTO-RENEWAL TERMS -- if this is an ongoing or retainer-style engagement, does it
   auto-renew unless cancelled, and if so, is the cancellation notice period and deadline clear?
   Silent auto-renewal with a short/buried notice window is a common commercial trap.
7. CURRENCY & TAX TREATMENT -- if the engagement could be cross-border (parties in different
   countries, or currency not explicitly tied to one party's home currency), is the billing
   currency fixed, and is responsibility for taxes/duties/withholding stated? Leave this out if
   there's no indication of a cross-border engagement -- don't force the check where it doesn't apply.
"""

        return doc_branch + _CONFIDENCE_CALIBRATION + """
IMPORTANT: Quote the exact document language as evidence for each finding, even when the finding
is about something MISSING -- quote the section header or nearby text that should have contained
it, so the finding can be located in the document. Only omit evidence when nothing in the document
is relevant to quote (e.g. the document has no pricing section anywhere).

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
            "type": "ambiguous_pricing|missing_terms|escalation_gap|renewal_risk|currency_tax_gap",
            "severity": "critical|major|medium|low",
            "description": "string",
            "evidence": "string",
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
6. PERSONNEL SECURITY -- if vendor staff will access sensitive systems, data, or facilities, does
   the document require background checks, security clearances, or vetting? Common in
   government/regulated engagements, easy to silently omit in commercial ones handling sensitive data.
7. BREACH/INCIDENT NOTIFICATION TIMELINE -- if a data breach or security incident occurs, does the
   document state how quickly the vendor must notify the client (e.g. "within 24/48/72 hours")? A
   security section that requires controls but never specifies incident response timing leaves the
   client blind to how fast they'd even find out.
8. ACCESSIBILITY COMPLIANCE -- if the deliverable is a public-facing or government-adjacent
   product (website, app, portal), does the document reference an accessibility standard (WCAG,
   Section 508)? Skip this check entirely if the deliverable is clearly internal-only tooling with
   no public-facing component -- don't force it where it doesn't apply.
"""

        return doc_branch + _CONFIDENCE_CALIBRATION + """
IMPORTANT: Quote the exact document language as evidence for each finding, even when the finding
is about something MISSING -- quote the section header or nearby text that should have contained
it, so the finding can be located in the document. Only omit evidence when nothing in the document
is relevant to quote (e.g. the document has no security section anywhere).

Provide findings as:
{
    "compliance_requirements": ["SOC2", "ISO27001", ...],
    "security_controls": ["string"],
    "findings": [
        {
            "type": "missing_clause|compliance_gap|audit_gap|missing_personnel_security|missing_breach_notification|missing_accessibility_standard",
            "severity": "critical|major|medium|low",
            "description": "string",
            "evidence": "string",
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

6. REPORTING & RISK TRACKING
   - Is a reporting cadence specified (weekly status, monthly steering committee), or just "regular
     updates" with no actual frequency? Vague cadence language is functionally no cadence.
   - Is there any mention of a risk register, RAID log, or equivalent ongoing risk-tracking
     mechanism -- or does the document only address risk implicitly through the escalation path?

RACI is critical. Missing RACI = major risk. Entry/exit criteria and fallback plan are critical for fixed-scope engagements; major for ongoing/retainer engagements.
"""

        return doc_branch + _CONFIDENCE_CALIBRATION + """
IMPORTANT: Quote governance language directly. Only report what you find; don't speculate. Rate confidence in each finding (0-100 scaled to 0.0-1.0).

Provide your response as a JSON object with this structure:
{
    "governance": {
        "raci_matrix_present": true|false,
        "escalation_levels": ["string"],
        "sla_defined": true|false,
        "entry_exit_criteria_defined": true|false,
        "fallback_plan_defined": true|false,
        "reporting_cadence_defined": true|false
    },
    "findings": [
        {
            "type": "missing_raci|undefined_escalation|unclear_decision_authority|missing_sla|missing_entry_exit_criteria|missing_fallback_plan|vague_reporting_cadence|missing_risk_register",
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

6. CONFIDENTIALITY
   - Is confidentiality MUTUAL (both parties bound) or one-sided (only the client's information
     protected)? A one-sided confidentiality clause is a specific, callable-out asymmetry, not just
     "confidentiality is addressed."
   - Is there a stated DURATION or survival period after termination? "Confidential forever" and
     "confidentiality ends at termination" are both real clauses that mean very different things --
     if neither is stated, that's a gap. (Note: a rule engine already checks whether the WORD
     "confidential" appears at all -- your value-add here is judging mutuality and duration, not
     restating that the section exists.)

7. INSURANCE, ASSIGNMENT & FORCE MAJEURE
   - Does the document require the vendor to carry insurance (general liability, professional
     liability/E&O, cyber)? For engagements with real operational or data risk, no insurance
     requirement at all is worth flagging.
   - Can either party assign or subcontract the agreement without the other's consent? Silent on
     this usually defaults to "yes" under most governing law, which may not be what either party
     actually wants.
   - Is force majeure addressed (excusable delay for events outside either party's control)? Its
     absence matters more for longer or higher-risk engagements than short fixed-scope ones --
     weight the finding's severity accordingly rather than always flagging it as critical.

Flag ambiguous legal language explicitly (e.g., "reasonable efforts", "as applicable") as a finding, not just missing clauses.
"""

        return doc_branch + _CONFIDENCE_CALIBRATION + """
IMPORTANT: Quote the exact clause language as evidence. Rate confidence in each finding (0-100 scaled to 0.0-1.0).

Provide your response as a JSON object with this structure:
{
    "legal_terms": {
        "liability_cap": "string or null",
        "indemnification_defined": true|false,
        "ip_ownership": "vendor|customer|joint|undefined",
        "termination_for_cause": true|false,
        "governing_law": "string or null",
        "warranty_defined": true|false,
        "confidentiality_mutual": true|false|null,
        "insurance_required": true|false
    },
    "findings": [
        {
            "type": "missing_liability_cap|undefined_ip_ownership|missing_termination_clause|no_governing_law|missing_warranty|ambiguous_legal_language|one_sided_confidentiality|missing_confidentiality_duration|missing_insurance_requirement|unaddressed_assignment|missing_force_majeure",
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
