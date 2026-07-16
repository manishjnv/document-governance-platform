"""Base AI agent class for document review."""

import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

logger = logging.getLogger(__name__)


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

    async def initialize(self):
        """Initialize agent with API client."""
        try:
            from anthropic import Anthropic

            self.client = Anthropic()
            logger.info(f"Agent '{self.name}' initialized with {self.model}")
        except ImportError:
            logger.error("anthropic SDK not installed")
            raise

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent."""
        pass

    @abstractmethod
    def get_output_schema(self) -> dict:
        """Return the JSON schema for expected output."""
        pass

    async def review(self, document_text: str) -> dict:
        """
        Review document and return structured findings.

        **T-406: Structured output parser**
        **T-407: Confidence scoring**
        """
        if not self.client:
            await self.initialize()

        try:
            logger.info(f"{self.name}: Starting review...")

            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system=self.get_system_prompt(),
                messages=[
                    {
                        "role": "user",
                        "content": f"Please review this document and provide findings in JSON format:\n\n{document_text}",
                    }
                ],
            )

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

    def get_system_prompt(self) -> str:
        """T-411: Scope Reviewer system prompt"""
        return """You are an expert project scope reviewer. Analyze the provided document and:

1. Extract all deliverables mentioned
2. Identify acceptance criteria for each deliverable
3. Detect scope boundaries and constraints
4. Find ambiguous or missing acceptance criteria
5. Identify potential scope creep indicators

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

    def get_system_prompt(self) -> str:
        """T-419: Delivery Reviewer system prompt"""
        return """You are an expert project delivery analyst. Analyze the document for:

1. Timeline and milestones
2. Dependencies and critical path
3. Realistic assumptions about dates
4. Missing or unclear delivery dates
5. Risk indicators in the schedule

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

    def get_system_prompt(self) -> str:
        """T-426: Commercial Reviewer system prompt"""
        return """You are an expert commercial analyst. Analyze for:

1. Pricing model and payment terms
2. Price escalation clauses
3. Out-of-scope pricing
4. Invoice timing and conditions
5. Ambiguous commercial language

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

    def get_system_prompt(self) -> str:
        """T-433: Security Reviewer system prompt"""
        return """You are a security and compliance expert. Analyze for:

1. Security requirements and standards (SOC2, ISO27001, etc.)
2. Data handling and privacy clauses
3. Audit rights and compliance obligations
4. Encryption and access control requirements
5. Missing security controls

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
