"""Tests for AI document insights: summary, key risks, comparison.

T-2021, T-2022, T-2024

Note: apps/api/tests/conftest.py's test_db/db_session fixtures create tables
via Base.metadata.create_all against sqlite+aiosqlite — this fails at table
creation for every real model here (Document/Review/Finding all use
postgresql JSONB / UUID columns SQLite can't compile; confirmed by running
create_all directly against the same fixture setup). So org-scoping is
tested at the router-function level with a mocked AsyncSession instead of a
real DB round trip.
"""

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.insights.ai_insights import compare_documents, extract_key_risks, generate_summary
from app.models.document import Document
from app.routers import insights as insights_router
from app.schemas.auth import TokenData


SAME_ORG = uuid4()


def _mock_response(text: str) -> MagicMock:
    return MagicMock(content=[MagicMock(text=text)])


def _token(org_id=SAME_ORG) -> TokenData:
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    return TokenData(
        user_id=uuid4(),
        email="user@example.com",
        org_id=org_id,
        role="reviewer",
        exp=now + timedelta(hours=1),
        iat=now,
    )


def _document(org_id=SAME_ORG, text: str = "some document text") -> Document:
    """Plain in-memory Document instance — not persisted, just used as the
    canned return value from a mocked db.execute()."""
    return Document(
        doc_id=uuid4(),
        document_group_id=uuid4(),
        org_id=org_id,
        filename="f.pdf",
        original_filename="f.pdf",
        file_size_bytes=100,
        file_type="pdf",
        s3_path="s3://bucket/f.pdf",
        version=1,
        parsed_text=text,
        deleted_at=None,
    )


def _db_returning(*scalar_results) -> AsyncMock:
    """AsyncSession mock whose execute() yields, in order, a result object
    for each item in scalar_results (each item is what scalar_one_or_none()
    should return, or a list for scalars().all())."""
    db = AsyncMock()
    results = []
    for item in scalar_results:
        result = MagicMock()
        if isinstance(item, list):
            result.scalars.return_value.all.return_value = item
        else:
            result.scalar_one_or_none.return_value = item
        results.append(result)
    db.execute = AsyncMock(side_effect=results)
    return db


# ---------------------------------------------------------------------------
# ai_insights.py: Claude call + JSON parsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_summary_returns_plain_text(mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = _mock_response(
        "This SOW covers a 6-month engagement with three deliverables and net-30 terms."
    )

    summary = await generate_summary("full document text", claude_client=mock_anthropic_client)

    assert "SOW" in summary
    mock_anthropic_client.messages.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_extract_key_risks_parses_json_block(mock_anthropic_client):
    payload = [
        {
            "risk": "Undefined payment schedule",
            "severity": "critical",
            "rationale": "No net terms specified anywhere in the document",
        },
    ]
    mock_anthropic_client.messages.create.return_value = _mock_response(
        f"Here is my analysis:\n```json\n{json.dumps(payload)}\n```"
    )

    risks = await extract_key_risks(
        "doc text",
        [{"severity": "critical", "description": "missing payment terms"}],
        claude_client=mock_anthropic_client,
    )

    assert risks == payload


@pytest.mark.asyncio
async def test_extract_key_risks_handles_unparsable_response(mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = _mock_response("not JSON at all")

    risks = await extract_key_risks("doc text", [], claude_client=mock_anthropic_client)

    assert risks == []


@pytest.mark.asyncio
async def test_compare_documents_parses_json_block(mock_anthropic_client):
    payload = {
        "added": ["New SLA clause"],
        "removed": [],
        "changed": ["Payment terms extended from Net 30 to Net 45"],
        "summary": "Minor commercial updates, no scope changes.",
    }
    mock_anthropic_client.messages.create.return_value = _mock_response(
        f"```json\n{json.dumps(payload)}\n```"
    )

    result = await compare_documents("text a", "text b", claude_client=mock_anthropic_client)

    assert result == payload


@pytest.mark.asyncio
async def test_compare_documents_falls_back_on_unparsable_response(mock_anthropic_client):
    mock_anthropic_client.messages.create.return_value = _mock_response("no json here")

    result = await compare_documents("text a", "text b", claude_client=mock_anthropic_client)

    assert result == {"added": [], "removed": [], "changed": [], "summary": "no json here"}


# ---------------------------------------------------------------------------
# Router: org-scoping (cross-org access rejected)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_summary_rejects_document_outside_org():
    """Org-scoped query returning nothing (cross-org doc_id) -> 404, and
    Claude is never called."""
    user = _token(org_id=SAME_ORG)
    db = _db_returning(None)  # org-scoped lookup finds nothing

    with pytest.raises(HTTPException) as exc_info:
        await insights_router.get_document_summary(uuid4(), current_user=user, db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_summary_allows_document_in_own_org(monkeypatch):
    user = _token(org_id=SAME_ORG)
    doc = _document(org_id=SAME_ORG)
    db = _db_returning(doc)

    fake_summary = AsyncMock(return_value="A concise summary.")
    monkeypatch.setattr(insights_router, "generate_summary", fake_summary)

    result = await insights_router.get_document_summary(doc.doc_id, current_user=user, db=db)

    assert result == {"doc_id": str(doc.doc_id), "summary": "A concise summary."}
    fake_summary.assert_awaited_once_with(doc.parsed_text)


@pytest.mark.asyncio
async def test_risks_rejects_document_outside_org():
    user = _token(org_id=SAME_ORG)
    db = _db_returning(None)

    with pytest.raises(HTTPException) as exc_info:
        await insights_router.get_document_risks(uuid4(), current_user=user, db=db)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_risks_allows_document_in_own_org_with_no_review(monkeypatch):
    user = _token(org_id=SAME_ORG)
    doc = _document(org_id=SAME_ORG)
    # doc lookup succeeds, then latest-review lookup finds none
    db = _db_returning(doc, None)

    fake_risks = AsyncMock(return_value=[{"risk": "x", "severity": "low", "rationale": "y"}])
    monkeypatch.setattr(insights_router, "extract_key_risks", fake_risks)

    result = await insights_router.get_document_risks(doc.doc_id, current_user=user, db=db)

    assert result["doc_id"] == str(doc.doc_id)
    assert result["risks"] == [{"risk": "x", "severity": "low", "rationale": "y"}]
    fake_risks.assert_awaited_once_with(doc.parsed_text, [])


@pytest.mark.asyncio
async def test_compare_rejects_when_second_document_is_cross_org():
    """doc_id_a resolves in-org, doc_id_b does not -> 404 before Claude runs."""
    user = _token(org_id=SAME_ORG)
    doc_a = _document(org_id=SAME_ORG)
    db = _db_returning(doc_a, None)

    with pytest.raises(HTTPException) as exc_info:
        await insights_router.compare_two_documents(
            doc_a.doc_id, uuid4(), current_user=user, db=db
        )

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_compare_allows_two_documents_in_own_org(monkeypatch):
    user = _token(org_id=SAME_ORG)
    doc_a = _document(org_id=SAME_ORG, text="text a")
    doc_b = _document(org_id=SAME_ORG, text="text b")
    db = _db_returning(doc_a, doc_b)

    fake_compare = AsyncMock(
        return_value={"added": [], "removed": [], "changed": [], "summary": "no changes"}
    )
    monkeypatch.setattr(insights_router, "compare_documents", fake_compare)

    result = await insights_router.compare_two_documents(
        doc_a.doc_id, doc_b.doc_id, current_user=user, db=db
    )

    assert result["doc_id_a"] == str(doc_a.doc_id)
    assert result["doc_id_b"] == str(doc_b.doc_id)
    assert result["summary"] == "no changes"
    fake_compare.assert_awaited_once_with("text a", "text b")
