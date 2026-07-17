"""AI-generated document insights via Claude: executive summaries, key risk
extraction, and semantic document comparison.

T-2021: AI summary generation
T-2022: Key risks extraction
T-2024: Document comparison

Follows the same "system prompt + JSON code-block extraction" pattern as
app/ai/agent.py, but calls Claude with AsyncAnthropic + await rather than
agent.py's synchronous Anthropic() client. agent.py's sync client blocks the
event loop inside async handlers (confirmed: the orchestrator's asyncio.gather
over multiple agents ends up serial, not parallel); new call sites shouldn't
add to that debt, and it's also what the async mock_anthropic_client fixture
in conftest.py actually expects (its messages.create is an AsyncMock — calling
it without awaiting yields an un-awaited coroutine, not the mocked response).
"""

import json
import logging
import re
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)\s*```", re.DOTALL)


def _get_client(claude_client: Optional[Any]):
    """Return the injected client, or lazily construct a default one."""
    if claude_client is not None:
        return claude_client
    import anthropic

    return anthropic.AsyncAnthropic()


def _parse_json_response(response_text: str) -> Any:
    """Pull JSON out of a Claude response: prefer a ```json fenced block,
    fall back to parsing the whole response as JSON."""
    match = _JSON_BLOCK_RE.search(response_text)
    raw = match.group(1) if match else response_text
    return json.loads(raw)


async def generate_summary(document_text: str, claude_client: Optional[Any] = None) -> str:
    """3-5 sentence executive summary of a document, via Claude."""
    client = _get_client(claude_client)

    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=500,
        system=(
            "You are an expert document analyst. Write a concise executive summary "
            "of the provided document in 3 to 5 sentences, covering its purpose, key "
            "terms, and any notable risks. Respond with plain text only — no preamble, "
            "no markdown, no JSON."
        ),
        messages=[{"role": "user", "content": document_text}],
    )
    return response.content[0].text.strip()


async def extract_key_risks(
    document_text: str, findings: list[dict], claude_client: Optional[Any] = None
) -> list[dict]:
    """Top 3 risks for a document, informed by existing review findings plus
    the document text itself. Each risk: {"risk", "severity", "rationale"}."""
    client = _get_client(claude_client)

    findings_json = json.dumps(findings, default=str)
    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1000,
        system=(
            "You are an expert risk analyst reviewing a governance document. Using the "
            "document text and the list of findings already raised against it, identify "
            "the top 3 risks — they may restate/consolidate existing findings or surface "
            "new ones visible only from the full document text.\n\n"
            "Respond with a JSON array in a ```json code block, no other text:\n"
            '```json\n[{"risk": "string", "severity": "critical|major|medium|low", '
            '"rationale": "string"}]\n```'
        ),
        messages=[
            {
                "role": "user",
                "content": f"Existing findings:\n{findings_json}\n\nDocument:\n{document_text}",
            }
        ],
    )

    try:
        result = _parse_json_response(response.content[0].text)
    except (json.JSONDecodeError, AttributeError, IndexError, TypeError):
        logger.warning("extract_key_risks: could not parse Claude JSON response")
        return []

    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        return result.get("risks", [])
    return []


async def compare_documents(
    text_a: str, text_b: str, claude_client: Optional[Any] = None
) -> dict:
    """Semantic comparison of two document versions via Claude — substantive
    additions/removals/changes, not a naive line diff."""
    client = _get_client(claude_client)

    response = await client.messages.create(
        model=settings.claude_model,
        max_tokens=1500,
        system=(
            "You are an expert document analyst comparing two versions of the same "
            "governance document. Identify substantive additions, removals, and changes "
            "in meaning or obligations — ignore purely cosmetic/formatting differences.\n\n"
            "Respond with a JSON object in a ```json code block, no other text:\n"
            '```json\n{"added": ["string"], "removed": ["string"], "changed": ["string"], '
            '"summary": "string"}\n```'
        ),
        messages=[
            {
                "role": "user",
                "content": f"Document A (original):\n{text_a}\n\nDocument B (revised):\n{text_b}",
            }
        ],
    )

    try:
        result = _parse_json_response(response.content[0].text)
    except (json.JSONDecodeError, AttributeError, IndexError, TypeError):
        logger.warning("compare_documents: could not parse Claude JSON response")
        return {
            "added": [],
            "removed": [],
            "changed": [],
            "summary": response.content[0].text.strip(),
        }

    return {
        "added": result.get("added", []),
        "removed": result.get("removed", []),
        "changed": result.get("changed", []),
        "summary": result.get("summary", ""),
    }
