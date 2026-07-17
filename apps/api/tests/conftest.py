"""Pytest configuration and fixtures.

T-920-T-926: Test infrastructure
"""

import pytest
import os

# Point Settings.database_url (and therefore app/db/session.py's module-level
# engine, used by any test that hits the app through a plain TestClient(app)
# without overriding get_db -- e.g. test_auth.py) at the disposable test
# database, never real dev data. A test once pointed at settings.database_url
# directly and nearly dropped core dev tables in teardown (see
# tests/test_search.py's history) -- this closes that hole at the source
# instead of trusting every test file to opt in individually. Must happen
# BEFORE `import app.config` constructs the Settings() singleton.
_TEST_DATABASE_URL_DEFAULT = (
    "postgresql+asyncpg://edgp_user:edgp_password@localhost:5432/edgp_test"
)
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", _TEST_DATABASE_URL_DEFAULT)

# TestClient sends Host: testserver by default; TrustedHostMiddleware (main.py)
# only allows ALLOWED_HOSTS (localhost,127.0.0.1 by default), so every request
# through the full app 400s before reaching a route. main.py reads this via a
# raw os.getenv().split(",") call (not through Settings), so import app.config
# FIRST — that constructs the Settings() singleton against the *original* env
# — then set ALLOWED_HOSTS to a comma string afterward. Setting it before that
# import instead makes pydantic-settings choke: Settings also declares an
# (unused — nothing reads settings.allowed_hosts) `allowed_hosts: list` field,
# and env-binds list-typed fields by json.loads()'ing the value, which a plain
# comma string isn't.
import app.config  # noqa: F401,E402

os.environ["ALLOWED_HOSTS"] = "localhost,127.0.0.1,testserver"

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Database fixtures
#
# The schema is Postgres-native by design (UUID/JSONB columns,
# clock_timestamp() defaults, tsvector/GIN full-text indexes, trigger-based
# updated_at) — see migrations/001_init_schema.sql's own header notes. An
# in-memory SQLite substitute can't compile any of that (postgresql.UUID has
# no SQLite compiler at all), so it was never a real test double, only a
# fixture that looked green on non-DB tests and errored on every DB-backed
# one. Point tests at a real, migrated Postgres database instead — same
# server as local dev (docker-compose's `postgres` service), separate
# `edgp_test` database so tests never touch dev data. Run
# `migrations/*.sql` against `edgp_test` once (docker exec ... psql) before
# running the suite; this fixture does not create schema itself.
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://edgp_user:edgp_password@localhost:5432/edgp_test",
)


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    yield engine


# Tried wrapping each test in one outer transaction + SAVEPOINT-per-commit
# (the standard SQLAlchemy recipe) first -- doesn't hold here, because tests
# drive requests through starlette's TestClient, which runs the ASGI app
# (and therefore the overridden get_db's session) on its own event
# loop/thread, decoupled from the one this fixture's connection was opened
# on; the rollback at teardown was a no-op against what TestClient had
# actually committed. TRUNCATE instead: simple, works regardless of which
# loop touched the data, and every table cascades from organizations (see
# migrations/001_init_schema.sql's ON DELETE CASCADE chain) so one
# statement clears the lot.
@pytest.fixture
async def db_session(test_engine):
    async with test_engine.begin() as conn:
        await conn.exec_driver_sql("TRUNCATE TABLE organizations CASCADE")

    session_factory = sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False, future=True
    )
    async with session_factory() as session:
        yield session


# Mock fixtures
@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.messages = MagicMock()
    client.messages.create = AsyncMock(
        return_value=MagicMock(
            content=[
                MagicMock(
                    text='{"findings": [], "overall_confidence": 0.85}'
                )
            ]
        )
    )
    return client


@pytest.fixture
def mock_storage():
    """Mock storage backend."""
    from unittest.mock import AsyncMock

    storage = AsyncMock()
    storage.upload = AsyncMock(return_value=True)
    storage.download = AsyncMock(return_value=b"file content")
    return storage


# Test data fixtures
@pytest.fixture
def sample_document():
    """Sample document for testing."""
    return {
        "filename": "test.pdf",
        "original_filename": "Test Document.pdf",
        "file_type": "PDF",
        "page_count": 5,
        "document_type": "SOW",
    }


@pytest.fixture
def sample_findings():
    """Sample findings for testing."""
    return [
        {
            "severity": "critical",
            "description": "Missing scope section",
            "type": "missing_criteria",
            "confidence": 0.95,
        },
        {
            "severity": "major",
            "description": "Ambiguous payment terms",
            "type": "ambiguous_pricing",
            "confidence": 0.80,
        },
    ]


@pytest.fixture
def sample_rule_violations():
    """Sample rule violations for testing."""
    return [
        {
            "rule_id": "SOW-001",
            "rule_name": "Executive Summary Required",
            "severity": "major",
            "description": "Missing Executive Summary section",
            "evidence": "Section not found in document",
            "recommendation": "Add an Executive Summary section",
        },
        {
            "rule_id": "SOW-011",
            "rule_name": "Payment Terms Required",
            "severity": "critical",
            "description": "Payment terms not clearly specified",
            "evidence": "'Net 30' or similar payment terms not found",
            "recommendation": "Specify payment terms (e.g., Net 30)",
        },
    ]


# Markers for test categorization
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "ai_accuracy: mark test as AI accuracy validation"
    )
