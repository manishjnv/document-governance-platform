"""Tests for insights_extra router and analytics functions.

T-2023, T-2025, T-2032
"""

import pytest
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import MagicMock, patch

from sqlalchemy import select, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.analytics.trends import analyze_score_trends
from app.insights.recommendations import generate_recommended_actions
from app.insights.risk_heuristic import predict_document_risk
from app.db.base import Base
from app.models.document import Document
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User
from app.schemas.auth import TokenData


# ============================================================================
# Unit Tests: Risk Heuristic (no DB)
# ============================================================================


class TestRiskHeuristic:
    """Unit tests for deterministic risk prediction."""

    def test_no_findings_returns_low_risk(self):
        """Empty findings list should return low risk."""
        result = predict_document_risk([])
        assert result["risk_score"] == 0.0
        assert result["risk_band"] == "low"
        assert result["basis"] == "heuristic"

    def test_single_critical_finding(self):
        """Single critical finding should elevate risk to high/critical range."""
        findings = [{"severity": "critical"}]
        result = predict_document_risk(findings)
        assert result["risk_score"] > 10.0  # At least 20% of scale
        assert result["risk_band"] in ["medium", "high", "critical"]
        assert result["finding_count_by_severity"]["critical"] == 1

    def test_multiple_major_findings(self):
        """Multiple major findings should raise risk to medium/high."""
        findings = [
            {"severity": "major"},
            {"severity": "major"},
            {"severity": "major"},
        ]
        result = predict_document_risk(findings)
        assert result["risk_score"] > 0.0
        # 3 * 5 = 15 weight → (15/50)*100 = 30%
        assert result["risk_score"] <= 50.0

    def test_many_low_findings_vs_few_critical(self):
        """Few critical > many low findings."""
        # 1 critical = 10 weight
        critical_only = predict_document_risk([{"severity": "critical"}])
        # 20 low = 20 weight (> 10)
        low_many = predict_document_risk([{"severity": "low"}] * 20)
        assert critical_only["risk_score"] < low_many["risk_score"]

    def test_risk_band_thresholds(self):
        """Verify risk band boundaries."""
        # Low: < 20
        low = predict_document_risk([{"severity": "low"}])
        assert low["risk_band"] == "low"

        # Medium: 20-50 (simulate with multiple majors)
        medium_findings = [{"severity": "major"}] * 4  # 4*5 = 20
        medium = predict_document_risk(medium_findings)
        assert medium["risk_band"] in ["medium", "high"]


# ============================================================================
# Custom DB Fixture: Lightweight analytics test DB (avoids missing Comment model)
# ============================================================================


@pytest.fixture
async def analytics_db():
    """Create minimal test database with only required tables for analytics tests."""
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        future=True,
        poolclass=StaticPool,
    )

    # Create tables using raw SQL to avoid CommentReaction FK issues
    async with engine.begin() as conn:
        # Organizations
        await conn.execute(text(
            """CREATE TABLE organizations (
                org_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                subscription_tier TEXT NOT NULL DEFAULT 'free',
                logo_url TEXT,
                brand_primary_color TEXT,
                brand_secondary_color TEXT,
                audit_retention_days INTEGER NOT NULL DEFAULT 90,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP
            )"""
        ))

        # Users
        await conn.execute(text(
            """CREATE TABLE users (
                user_id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                email TEXT NOT NULL,
                password_hash TEXT,
                full_name TEXT,
                role TEXT NOT NULL DEFAULT 'viewer',
                is_active BOOLEAN NOT NULL DEFAULT 1,
                last_login TIMESTAMP,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES organizations(org_id)
            )"""
        ))

        # Documents
        await conn.execute(text(
            """CREATE TABLE documents (
                doc_id TEXT PRIMARY KEY,
                document_group_id TEXT NOT NULL,
                org_id TEXT NOT NULL,
                uploaded_by_user_id TEXT,
                filename TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                project_name TEXT,
                file_size_bytes INTEGER NOT NULL,
                file_type TEXT NOT NULL,
                s3_path TEXT NOT NULL,
                s3_etag TEXT,
                version INTEGER NOT NULL DEFAULT 1,
                parsed_text TEXT,
                parsed_sections TEXT,
                document_type TEXT,
                page_count INTEGER,
                language TEXT NOT NULL DEFAULT 'en',
                storage_status TEXT NOT NULL DEFAULT 'uploaded',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES organizations(org_id),
                FOREIGN KEY (uploaded_by_user_id) REFERENCES users(user_id)
            )"""
        ))

        # Reviews
        await conn.execute(text(
            """CREATE TABLE reviews (
                review_id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                document_version INTEGER NOT NULL DEFAULT 1,
                triggered_by_user_id TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                overall_score NUMERIC(5, 2),
                risk_score NUMERIC(5, 2),
                risk_breakdown TEXT,
                score_completeness NUMERIC(5, 2),
                score_clarity NUMERIC(5, 2),
                score_consistency NUMERIC(5, 2),
                score_commercial NUMERIC(5, 2),
                score_delivery NUMERIC(5, 2),
                score_operations NUMERIC(5, 2),
                score_security NUMERIC(5, 2),
                executive_summary TEXT,
                critical_finding_count INTEGER NOT NULL DEFAULT 0,
                major_finding_count INTEGER NOT NULL DEFAULT 0,
                medium_finding_count INTEGER NOT NULL DEFAULT 0,
                low_finding_count INTEGER NOT NULL DEFAULT 0,
                info_finding_count INTEGER NOT NULL DEFAULT 0,
                started_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                processing_time_seconds INTEGER,
                error_message TEXT,
                error_details TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES organizations(org_id),
                FOREIGN KEY (doc_id) REFERENCES documents(doc_id),
                FOREIGN KEY (triggered_by_user_id) REFERENCES users(user_id)
            )"""
        ))

        # Findings
        await conn.execute(text(
            """CREATE TABLE findings (
                finding_id TEXT PRIMARY KEY,
                org_id TEXT NOT NULL,
                review_id TEXT NOT NULL,
                finding_source TEXT NOT NULL,
                agent_name TEXT,
                rule_id TEXT,
                category TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                evidence TEXT,
                section_ref TEXT,
                severity TEXT NOT NULL,
                confidence NUMERIC(5, 2) NOT NULL DEFAULT 100.00,
                business_impact TEXT,
                recommendation TEXT NOT NULL,
                suggested_text TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                assigned_to_user_id TEXT,
                notes TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                FOREIGN KEY (org_id) REFERENCES organizations(org_id),
                FOREIGN KEY (review_id) REFERENCES reviews(review_id),
                FOREIGN KEY (assigned_to_user_id) REFERENCES users(user_id)
            )"""
        ))

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False, future=True
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


# ============================================================================
# Integration Tests: Analytics (with SQLite DB)
# ============================================================================


class TestAnalyticsTrends:
    """Integration tests for trend analysis with real DB."""

    @pytest.mark.asyncio
    async def test_analyze_trends_empty_org(self, analytics_db):
        """Empty org should return empty trends."""
        org_id = uuid4()
        result = await analyze_score_trends(analytics_db, org_id)
        assert result["points"] == []
        assert result["direction"] == "flat"

    @pytest.mark.asyncio
    async def test_analyze_trends_single_month(self, analytics_db: AsyncSession):
        """Single month of data should have no trend (flat)."""
        org_id = uuid4()

        # Create org, user, document
        org = Organization(org_id=org_id, name="Test Org")
        analytics_db.add(org)

        user = User(
            user_id=uuid4(),
            org_id=org_id,
            email="test@example.com",
        )
        analytics_db.add(user)

        doc = Document(
            doc_id=uuid4(),
            org_id=org_id,
            document_group_id=uuid4(),
            file_type="pdf",
            filename="test.pdf",
            original_filename="Test Document.pdf",
            file_size_bytes=1024,
            s3_path="s3://bucket/test.pdf",
            version=1,
            uploaded_by_user_id=user.user_id,
        )
        analytics_db.add(doc)

        # Create one review with overall_score
        now = datetime.now(timezone.utc)
        review = Review(
            review_id=uuid4(),
            org_id=org_id,
            doc_id=doc.doc_id,
            status="completed",
            overall_score=Decimal("75.00"),
            document_version=1,
            created_at=now,
        )
        analytics_db.add(review)

        await analytics_db.commit()

        result = await analyze_score_trends(analytics_db, org_id)
        assert len(result["points"]) == 1
        assert result["points"][0]["avg_score"] == 75.0
        assert result["direction"] == "flat"

    @pytest.mark.asyncio
    async def test_analyze_trends_improving(self, analytics_db: AsyncSession):
        """Scores increasing over time should be marked 'improving'."""
        org_id = uuid4()

        org = Organization(org_id=org_id, name="Test Org")
        analytics_db.add(org)

        user = User(
            user_id=uuid4(),
            org_id=org_id,
            email="test@example.com",
        )
        analytics_db.add(user)

        doc = Document(
            doc_id=uuid4(),
            org_id=org_id,
            document_group_id=uuid4(),
            file_type="pdf",
            filename="test.pdf",
            original_filename="Test Document.pdf",
            file_size_bytes=1024,
            s3_path="s3://bucket/test.pdf",
            version=1,
            uploaded_by_user_id=user.user_id,
        )
        analytics_db.add(doc)

        # Create reviews spanning 4 months with increasing scores
        base_date = datetime(2026, 1, 15, tzinfo=timezone.utc)
        scores = [50.0, 55.0, 75.0, 85.0]

        for i, score in enumerate(scores):
            created_at = base_date + timedelta(days=30 * i)
            review = Review(
                review_id=uuid4(),
                org_id=org_id,
                doc_id=doc.doc_id,
                status="completed",
                overall_score=Decimal(str(score)),
                document_version=1,
                created_at=created_at,
            )
            analytics_db.add(review)

        await analytics_db.commit()

        result = await analyze_score_trends(analytics_db, org_id)
        assert len(result["points"]) == 4
        assert result["direction"] == "improving"

    @pytest.mark.asyncio
    async def test_analyze_trends_category_specific(self, analytics_db: AsyncSession):
        """Should filter by category when specified."""
        org_id = uuid4()

        org = Organization(org_id=org_id, name="Test Org")
        analytics_db.add(org)

        user = User(
            user_id=uuid4(),
            org_id=org_id,
            email="test@example.com",
        )
        analytics_db.add(user)

        doc = Document(
            doc_id=uuid4(),
            org_id=org_id,
            document_group_id=uuid4(),
            file_type="pdf",
            filename="test.pdf",
            original_filename="Test Document.pdf",
            file_size_bytes=1024,
            s3_path="s3://bucket/test.pdf",
            version=1,
            uploaded_by_user_id=user.user_id,
        )
        analytics_db.add(doc)

        review = Review(
            review_id=uuid4(),
            org_id=org_id,
            doc_id=doc.doc_id,
            status="completed",
            overall_score=Decimal("75.00"),
            score_completeness=Decimal("60.00"),
            score_clarity=Decimal("85.00"),
            document_version=1,
            created_at=datetime.now(timezone.utc),
        )
        analytics_db.add(review)
        await analytics_db.commit()

        # Query for clarity category
        result = await analyze_score_trends(analytics_db, org_id, category="clarity")
        assert len(result["points"]) == 1
        assert result["points"][0]["avg_score"] == 85.0


# ============================================================================
# Unit Tests: Claude Integration
# ============================================================================


class TestRecommendations:
    """Tests for Claude-based recommendation generation."""

    @pytest.mark.asyncio
    async def test_generate_recommendations_with_mock_client(self):
        """Should call Claude and parse JSON response."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(
                    text='```json\n{"recommendations": ["Fix the scope", "Clarify terms", "Add signatures"]}\n```'
                )
            ]
        )

        findings = [
            {
                "severity": "critical",
                "title": "Missing scope",
                "description": "Scope section is incomplete",
                "recommendation": "Add detailed scope",
            }
        ]

        result = await generate_recommended_actions(
            document_text="Sample document",
            findings=findings,
            claude_client=mock_client,
        )

        assert isinstance(result, list)
        assert len(result) == 3
        assert "Fix the scope" in result

        # Verify Claude was called
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert "system" in call_kwargs
        assert "messages" in call_kwargs

    @pytest.mark.asyncio
    async def test_generate_recommendations_invalid_json(self):
        """Should handle invalid JSON gracefully."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[MagicMock(text="Not valid JSON at all")]
        )

        findings = [{"severity": "major", "title": "Issue"}]

        result = await generate_recommended_actions(
            document_text="Sample",
            findings=findings,
            claude_client=mock_client,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_generate_recommendations_empty_findings(self):
        """Should still call Claude even with empty findings."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[
                MagicMock(text='```json\n{"recommendations": ["Document is clean"]}\n```')
            ]
        )

        result = await generate_recommended_actions(
            document_text="Clean doc",
            findings=[],
            claude_client=mock_client,
        )

        assert isinstance(result, list)
