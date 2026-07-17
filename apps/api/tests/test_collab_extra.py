"""Tests for collab_extra: threads, reactions, digest.

T-2063: comment threads
T-2065: comment emoji reactions
T-2077: daily digest
"""

import pytest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.collab.threads import build_comment_tree
from app.collab.reactions import toggle_reaction, get_reaction_counts
from app.collab.digest import build_daily_digest


# ===== Comment Tree Tests (pure function, no DB) =====

def test_build_comment_tree_empty_list():
    """Empty input returns empty output."""
    result = build_comment_tree([])
    assert result == []


def test_build_comment_tree_single_top_level():
    """Single comment with no parent is top-level."""
    comment = {
        "comment_id": uuid.uuid4(),
        "parent_comment_id": None,
        "content": "Hello",
    }
    result = build_comment_tree([comment])

    assert len(result) == 1
    assert result[0]["content"] == "Hello"
    assert result[0]["children"] == []


def test_build_comment_tree_parent_and_reply():
    """Reply nests under parent."""
    parent_id = uuid.uuid4()
    reply_id = uuid.uuid4()

    comments = [
        {"comment_id": parent_id, "parent_comment_id": None, "content": "Parent"},
        {"comment_id": reply_id, "parent_comment_id": parent_id, "content": "Reply"},
    ]

    result = build_comment_tree(comments)

    assert len(result) == 1
    assert result[0]["content"] == "Parent"
    assert len(result[0]["children"]) == 1
    assert result[0]["children"][0]["content"] == "Reply"


def test_build_comment_tree_multiple_replies():
    """Multiple replies to same parent."""
    parent_id = uuid.uuid4()
    reply1_id = uuid.uuid4()
    reply2_id = uuid.uuid4()

    comments = [
        {"comment_id": parent_id, "parent_comment_id": None, "content": "Parent"},
        {"comment_id": reply1_id, "parent_comment_id": parent_id, "content": "Reply1"},
        {"comment_id": reply2_id, "parent_comment_id": parent_id, "content": "Reply2"},
    ]

    result = build_comment_tree(comments)

    assert len(result) == 1
    assert len(result[0]["children"]) == 2
    assert result[0]["children"][0]["content"] == "Reply1"
    assert result[0]["children"][1]["content"] == "Reply2"


def test_build_comment_tree_multiple_top_level():
    """Multiple top-level comments stay at root."""
    id1, id2 = uuid.uuid4(), uuid.uuid4()

    comments = [
        {"comment_id": id1, "parent_comment_id": None, "content": "First"},
        {"comment_id": id2, "parent_comment_id": None, "content": "Second"},
    ]

    result = build_comment_tree(comments)

    assert len(result) == 2
    assert result[0]["content"] == "First"
    assert result[1]["content"] == "Second"


def test_build_comment_tree_no_mutation_of_input():
    """Original list is not mutated."""
    parent_id = uuid.uuid4()
    reply_id = uuid.uuid4()

    comments = [
        {"comment_id": parent_id, "parent_comment_id": None, "content": "Parent"},
        {"comment_id": reply_id, "parent_comment_id": parent_id, "content": "Reply"},
    ]

    original_copy = [dict(c) for c in comments]
    build_comment_tree(comments)

    # Input should be unchanged (no children key added to originals)
    assert comments == original_copy


# ===== Reaction Tests (mocked DB) =====

@pytest.mark.asyncio
async def test_toggle_insert_then_delete():
    """Toggle inserts, toggle again deletes."""
    comment_id = uuid.uuid4()
    user_id = uuid.uuid4()
    emoji = "👍"

    # Mock DB session
    db = AsyncMock()

    # First call: no existing reaction
    db.execute = AsyncMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)

    # First toggle: should insert
    result1 = await toggle_reaction(db, comment_id, user_id, emoji)
    assert result1 is True

    # Verify reaction was added
    assert db.add.call_count == 1

    # Second call: reaction exists
    db.execute.reset_mock()
    db.add.reset_mock()

    mock_reaction = MagicMock()
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=mock_reaction)

    # Second toggle: should delete
    result2 = await toggle_reaction(db, comment_id, user_id, emoji)
    assert result2 is False

    # Verify reaction was deleted
    assert db.delete.call_count == 1


@pytest.mark.asyncio
async def test_get_reaction_counts():
    """Count reactions by emoji."""
    comment_id = uuid.uuid4()

    # Mock DB session with grouped results
    db = AsyncMock()

    mock_result = [
        ("👍", 2),
        ("❤️", 1),
    ]

    db.execute.return_value.all = MagicMock(return_value=mock_result)

    counts = await get_reaction_counts(db, comment_id)

    assert counts.get("👍") == 2
    assert counts.get("❤️") == 1


@pytest.mark.asyncio
async def test_get_reaction_counts_empty():
    """Empty counts when no reactions."""
    comment_id = uuid.uuid4()

    db = AsyncMock()
    db.execute.return_value.all = MagicMock(return_value=[])

    counts = await get_reaction_counts(db, comment_id)
    assert counts == {}


# ===== Digest Tests (mocked DB) =====

@pytest.mark.asyncio
async def test_digest_runs_without_error():
    """Digest builder handles empty DB gracefully."""
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    # Mock DB session
    db = AsyncMock()
    db.execute.return_value.all = MagicMock(return_value=[])

    digest = await build_daily_digest(db, user_id, org_id)

    assert "Daily Digest for" in digest
    assert "End of Digest" in digest
    assert isinstance(digest, str)
    assert len(digest) > 0
