"""Generate recommended actions from document findings using Claude."""

import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


async def generate_recommended_actions(
    document_text: str,
    findings: list[dict],
    claude_client=None,
) -> list[str]:
    """
    Generate concrete, actionable recommended actions for a document based on findings.

    Args:
        document_text: The document content to review
        findings: List of findings dicts with keys: severity, title, description, recommendation
        claude_client: Optional Anthropic client (default: create new)

    Returns:
        List of 3-5 actionable recommendations (strings)
    """
    # Lazy init of Claude client if not provided (allows injection for testing)
    if claude_client is None:
        try:
            from anthropic import Anthropic

            claude_client = Anthropic()
        except ImportError:
            logger.error("anthropic SDK not installed")
            raise

    # Format findings for Claude
    findings_text = "\n".join(
        [
            f"- [{f.get('severity', 'unknown').upper()}] {f.get('title', 'Unknown')}: {f.get('description', '')} "
            f"(Recommendation: {f.get('recommendation', 'No recommendation')})"
            for f in findings
        ]
    )

    system_prompt = (
        "You are a document governance expert. Given a document and its findings, "
        "provide 3-5 concrete, prioritized, actionable recommendations for improvement. "
        "Each recommendation must be specific and implementable. "
        "Return ONLY a JSON object with key 'recommendations' containing a list of strings."
    )

    user_message = (
        f"Document preview:\n{document_text[:500]}...\n\n"
        f"Findings from review:\n{findings_text}\n\n"
        f"Provide 3-5 prioritized, actionable recommendations to address these findings."
    )

    try:
        response = claude_client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1000,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        response_text = response.content[0].text

        # Try to parse JSON from response
        try:
            # Look for JSON block
            json_match = re.search(r"```json\s*(.*?)\s*```", response_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(1))
            else:
                # Try parsing the whole response as JSON
                result = json.loads(response_text)

            recommendations = result.get("recommendations", [])
            if isinstance(recommendations, list):
                return recommendations
            else:
                logger.warning("Recommendations field is not a list, returning empty")
                return []

        except json.JSONDecodeError:
            logger.warning("Could not parse JSON from Claude response")
            return []

    except Exception as e:
        logger.error(f"Error generating recommendations: {e}")
        raise
