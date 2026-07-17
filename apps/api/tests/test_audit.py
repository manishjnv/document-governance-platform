"""Tests for T-2041 (audit write helper) and T-2044 (audit search API).

T-2042 (audit_logs storage) is already satisfied by the existing
app/models/audit_log.py + migrations/001_init_schema.sql -- not retested here.
"""

import itertools
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import event, select
from sqlalchemy.engine import Engine

from app.compliance.audit import log_action
from app.models.audit_log import AuditLog

# Side-effect imports: register Organization/User on Base.metadata before
# conftest's session-scoped `test_db` fixture runs create_all (audit_logs has
# FKs to both).
from app.models.organization import Organization  # noqa: F401
from app.models.user import User  # noqa: F401

# Any import of `app.models.*` runs app/models/__init__.py as a side effect
# (Python always executes a package's __init__ before its submodules), which
# currently imports CommentReaction without importing its FK target Comment
# -- a parallel-agent bug in a file this task is explicitly not allowed to
# touch (models/__init__.py). Importing Comment here ourselves supplies the
# missing registration so create_all doesn't blow up for the whole shared
# test session. Remove once app/models/__init__.py itself imports Comment.
from app.models.comment import Comment  # noqa: F401
from app.routers.audit import search_audit_logs

_log_id_counter = itertools.count(1)


@event.listens_for(AuditLog, "before_insert")
def _assign_sqlite_log_id(mapper, connection, target):
    """AuditLog.log_id is BigInteger (Postgres BIGSERIAL in prod). SQLite
    only auto-populates a PK on NULL insert when the column is declared
    exactly `INTEGER PRIMARY KEY`; BIGINT PRIMARY KEY doesn't get that
    ROWID-alias behavior, so the in-memory test DB needs a value assigned
    client-side. No-op outside SQLite (target.log_id already set by the
    server_default RETURNING path elsewhere)."""
    if target.log_id is None:
        target.log_id = next(_log_id_counter)


@event.listens_for(Engine, "connect")
def _register_clock_timestamp(dbapi_connection, connection_record):
    """AuditLog.created_at's server_default is func.clock_timestamp() --
    Postgres-only. conftest.py's test DB is SQLite (no clock_timestamp()),
    so register a Python-side equivalent on every new DBAPI connection.
    Self-contained to this test file; does not touch conftest.py/db/base.py.
    No-ops for non-sqlite DBAPI connections (e.g. real Postgres in prod),
    which don't have create_function and already have a real clock_timestamp.
    """
    try:
        dbapi_connection.create_function(
            "clock_timestamp", 0, lambda: datetime.utcnow().isoformat(sep=" ")
        )
    except AttributeError:
        pass


def _user(org_id, role="admin"):
    """Duck-typed stand-in for TokenData.

    TokenData.org_id/.user_id are typed `int` (Phase 1 in-memory auth stub --
    see app/schemas/auth.py) while AuditLog.org_id/.user_id are real UUID
    columns. That mismatch is a pre-existing gap across documents.py/
    reviews.py too (see report), not introduced or fixed here. A plain
    SimpleNamespace sidesteps TokenData's `org_id: int` validation so these
    tests can exercise the router's real UUID-based org scoping against the
    real DB schema.
    """
    return SimpleNamespace(user_id=uuid4(), org_id=org_id, role=role)


@pytest.mark.asyncio
async def test_log_action_writes_org_scoped_row_committed_by_caller(db_session):
    org_id = uuid4()
    user_id = uuid4()
    resource_id = uuid4()

    await log_action(
        db_session,
        org_id=org_id,
        user_id=user_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=resource_id,
        details={"foo": "bar"},
    )

    # log_action must NOT commit -- a rollback here should discard the row.
    await db_session.rollback()
    result = await db_session.execute(select(AuditLog).where(AuditLog.org_id == org_id))
    assert result.scalar_one_or_none() is None

    # Re-add; only the caller's own commit makes it durable.
    await log_action(
        db_session,
        org_id=org_id,
        user_id=user_id,
        action="document.uploaded",
        resource_type="document",
        resource_id=resource_id,
        details={"foo": "bar"},
    )
    await db_session.commit()

    result = await db_session.execute(select(AuditLog).where(AuditLog.org_id == org_id))
    row = result.scalar_one()
    assert row.org_id == org_id
    assert row.user_id == user_id
    assert row.action == "document.uploaded"
    assert row.resource_type == "document"
    assert row.resource_id == resource_id
    assert row.details == {"foo": "bar"}


@pytest.mark.asyncio
async def test_log_action_raises_on_invalid_resource_type(db_session):
    with pytest.raises(ValueError):
        await log_action(
            db_session,
            org_id=uuid4(),
            user_id=uuid4(),
            action="whatever",
            resource_type="not_a_real_resource_type",
        )
    # Failed before staging anything.
    assert not db_session.new


@pytest.mark.asyncio
async def test_search_audit_logs_filters_and_is_org_scoped(db_session):
    org_a = uuid4()
    org_b = uuid4()
    user_a = uuid4()

    await log_action(
        db_session,
        org_id=org_a,
        user_id=user_a,
        action="document.uploaded",
        resource_type="document",
        resource_id=uuid4(),
    )
    await log_action(
        db_session,
        org_id=org_a,
        user_id=user_a,
        action="review.completed",
        resource_type="review",
        resource_id=uuid4(),
    )
    await log_action(
        db_session,
        org_id=org_b,
        user_id=uuid4(),
        action="document.uploaded",
        resource_type="document",
        resource_id=uuid4(),
    )
    await db_session.commit()

    # Unfiltered: only org A's 2 rows come back.
    results = await search_audit_logs(
        user_id=None,
        action=None,
        resource_type=None,
        date_from=None,
        date_to=None,
        skip=0,
        limit=50,
        current_user=_user(org_a),
        db=db_session,
    )
    assert len(results) == 2
    assert all(r["org_id"] == str(org_a) for r in results)

    # Filtered by action: only the upload row.
    results = await search_audit_logs(
        user_id=None,
        action="document.uploaded",
        resource_type=None,
        date_from=None,
        date_to=None,
        skip=0,
        limit=50,
        current_user=_user(org_a),
        db=db_session,
    )
    assert len(results) == 1
    assert results[0]["action"] == "document.uploaded"

    # Org B's caller can never see org A's rows (or vice versa).
    results = await search_audit_logs(
        user_id=None,
        action=None,
        resource_type=None,
        date_from=None,
        date_to=None,
        skip=0,
        limit=50,
        current_user=_user(org_b),
        db=db_session,
    )
    assert len(results) == 1
    assert results[0]["org_id"] == str(org_b)
