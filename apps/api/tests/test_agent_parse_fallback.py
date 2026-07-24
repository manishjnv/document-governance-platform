"""Unparseable JSON from a model must advance the fallback chain, not
silently return zero findings (measured 2026-07-24: some fallback models
dropped 2-3 of 6 agents per review this way -- AI_MODEL_ROUTING.md)."""

import json
from unittest.mock import MagicMock

import pytest

from app.ai.agent import ScopeReviewer

_VALID = json.dumps(
    {
        "deliverables": [],
        "findings": [
            {
                "type": "ambiguous",
                "severity": "medium",
                "description": "x",
                "evidence": "y",
                "recommendation": "z",
                "confidence": 0.6,
            }
        ],
        "overall_confidence": 0.7,
    }
)


def _client_returning(texts):
    """Fake client whose messages.create yields each text in order."""
    client = MagicMock()
    responses = [MagicMock(content=[MagicMock(text=t)]) for t in texts]
    client.messages.create.side_effect = responses
    return client


@pytest.mark.asyncio
async def test_garbage_primary_falls_through_to_parseable_fallback():
    agent = ScopeReviewer()
    agent.model = "primary/model"
    agent._fallback_models = ["fallback/model"]
    agent.client = _client_returning(["I'm sorry, here are my thoughts...", _VALID])

    result = await agent.review("some document text")

    assert len(result["findings"]) == 1
    assert result["_model_used"] == "fallback/model"


@pytest.mark.asyncio
async def test_all_models_unparseable_degrades_to_raw_text():
    agent = ScopeReviewer()
    agent.model = "primary/model"
    agent._fallback_models = ["fallback/model"]
    agent.client = _client_returning(["garbage one", "garbage two"])

    result = await agent.review("some document text")

    assert result["findings"] == []
    assert result["raw_response"] == "garbage two"
    assert result["_model_used"] == "fallback/model"


@pytest.mark.asyncio
async def test_parseable_primary_never_calls_fallback():
    agent = ScopeReviewer()
    agent.model = "primary/model"
    agent._fallback_models = ["fallback/model"]
    agent.client = _client_returning([_VALID])

    result = await agent.review("some document text")

    assert result["_model_used"] == "primary/model"
    assert agent.client.messages.create.call_count == 1
