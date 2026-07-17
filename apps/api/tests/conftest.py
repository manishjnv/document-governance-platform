"""Pytest configuration and fixtures.

T-920-T-926: Test infrastructure
"""

import pytest
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.db.base import Base


# Setup async event loop
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest.fixture(scope="session")
async def test_db():
    """Create test database."""
    # Use SQLite for testing
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, future=True
    )

    yield async_session

    await engine.dispose()


@pytest.fixture
async def db_session(test_db):
    """Create database session for test."""
    async with test_db() as session:
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
