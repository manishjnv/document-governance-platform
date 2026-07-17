"""Tests for predictions endpoints and analytics functions.

T-2030: Version comparison setup (contract verification)
T-2033: Missing sections suggestion
T-2034: Anomaly detection
T-2035: Confidence intervals
"""

import pytest
from decimal import Decimal
from uuid import uuid4

from app.analytics.anomaly import detect_score_anomalies
from app.analytics.confidence import add_confidence_interval
from app.insights.section_recommender import suggest_missing_sections
from app.models.document import Document
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User


# ============================================================================
# Unit Tests: Section Recommender (no DB)
# ============================================================================


class TestSectionRecommender:
    """Unit tests for missing section detection."""

    def test_sow_missing_payment_terms(self):
        """SOW missing 'payment terms' should be detected."""
        parsed_sections = {
            "Scope of Work": "...",
            "Deliverables": "...",
            "Timeline": "...",
            "Acceptance Criteria": "...",
            # Missing: Payment Terms
        }
        missing = suggest_missing_sections("SOW", parsed_sections)
        assert "payment terms" in missing

    def test_sow_has_all_sections(self):
        """SOW with all sections should return empty list."""
        parsed_sections = {
            "Scope": "...",
            "Deliverables": "...",
            "Payment Terms and Conditions": "...",  # Substring match
            "Project Timeline": "...",
            "Acceptance Criteria": "...",
        }
        missing = suggest_missing_sections("SOW", parsed_sections)
        assert len(missing) == 0

    def test_proposal_missing_sections(self):
        """Proposal missing 'pricing' should be detected."""
        parsed_sections = {
            "Executive Summary": "...",
            "Approach": "...",
            "Timeline": "...",
            # Missing: Pricing, Terms
        }
        missing = suggest_missing_sections("Proposal", parsed_sections)
        assert "pricing" in missing
        assert "terms" in missing

    def test_case_insensitive_matching(self):
        """Section matching should be case-insensitive."""
        parsed_sections = {
            "SCOPE": "...",
            "DELIVERABLES": "...",
            "PAYMENT TERMS": "...",
            "TIMELINE": "...",
            "ACCEPTANCE CRITERIA": "...",
        }
        missing = suggest_missing_sections("SOW", parsed_sections)
        assert len(missing) == 0

    def test_unknown_document_type(self):
        """Unknown document type should return empty checklist."""
        parsed_sections = {"Some Section": "..."}
        missing = suggest_missing_sections("UnknownType", parsed_sections)
        assert len(missing) == 0

    def test_empty_parsed_sections(self):
        """Empty parsed_sections should return full checklist."""
        missing = suggest_missing_sections("SOW", {})
        expected = ["scope", "deliverables", "payment terms", "timeline", "acceptance criteria"]
        assert set(missing) == set(expected)


# ============================================================================
# Unit Tests: Confidence Intervals (no DB)
# ============================================================================


class TestConfidenceInterval:
    """Unit tests for confidence interval calculation."""

    def test_no_findings_low_confidence(self):
        """Zero findings should yield low confidence and wide margin."""
        result = add_confidence_interval(50.0, 0)
        assert result["confidence"] == "low"
        assert result["lower_bound"] == 20.0  # 50 - 30
        assert result["upper_bound"] == 80.0  # 50 + 30
        assert result["risk_score"] == 50.0

    def test_few_findings_low_confidence(self):
        """< 3 findings should yield low confidence."""
        result = add_confidence_interval(75.0, 2)
        assert result["confidence"] == "low"
        # margin = max(0, 30 - 2*3) = 24
        assert result["lower_bound"] == 51.0  # 75 - 24
        assert result["upper_bound"] == 99.0  # clamped to 100 → 99

    def test_medium_findings_medium_confidence(self):
        """3-7 findings should yield medium confidence."""
        result = add_confidence_interval(60.0, 5)
        assert result["confidence"] == "medium"
        # margin = max(0, 30 - 5*3) = 15
        assert result["lower_bound"] == 45.0
        assert result["upper_bound"] == 75.0

    def test_many_findings_high_confidence(self):
        """8+ findings should yield high confidence and tight margin."""
        result = add_confidence_interval(40.0, 10)
        assert result["confidence"] == "high"
        # margin = max(0, 30 - 10*3) = 0
        assert result["lower_bound"] == 40.0
        assert result["upper_bound"] == 40.0

    def test_bounds_clamped_to_0_100(self):
        """Bounds should never exceed [0, 100]."""
        result = add_confidence_interval(5.0, 0)  # 5 - 30 < 0, 5 + 30 = 35
        assert result["lower_bound"] == 0.0
        assert result["upper_bound"] == 35.0

        result = add_confidence_interval(95.0, 0)  # 95 - 30 = 65, 95 + 30 > 100
        assert result["lower_bound"] == 65.0
        assert result["upper_bound"] == 100.0


# ============================================================================
# Database Tests: Anomaly Detection
# ============================================================================


class TestAnomalyDetection:
    """Tests for anomaly detection using real DB fixtures."""

    @pytest.mark.asyncio
    async def test_anomaly_below_org_mean(self, db_session):
        """Review far below org mean should be flagged as anomaly."""
        org = Organization(name="Test Org", subscription_tier="enterprise")
        db_session.add(org)
        await db_session.flush()

        user = User(
            org_id=org.org_id,
            email="user@example.com",
            password_hash="hashed_pw",
            full_name="Test User",
            role="reviewer",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        doc = Document(
            org_id=org.org_id,
            doc_id=uuid4(),
            uploaded_by_user_id=user.user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="SOW",
        )
        db_session.add(doc)
        await db_session.flush()

        # Create 5 completed reviews with scores around 70
        for i in range(5):
            review = Review(
                review_id=uuid4(),
                org_id=org.org_id,
                doc_id=doc.doc_id,
                document_version=1,
                status="completed",
                overall_score=Decimal("70.00"),
            )
            db_session.add(review)
        await db_session.flush()

        # Create target review with anomalously low score (30)
        target_review = Review(
            org_id=org.org_id,
            doc_id=doc.doc_id,
            document_version=1,
            status="completed",
            overall_score=Decimal("30.00"),
        )
        db_session.add(target_review)
        await db_session.commit()

        # Detect anomaly
        result = await detect_score_anomalies(db_session, org.org_id, target_review.review_id)

        assert result["review_id"] == str(target_review.review_id)
        assert result["overall_score"] == 30.0
        assert result["org_mean"] == 70.0
        assert result["is_anomaly"] is True
        assert result["deviation"] > 2.0

    @pytest.mark.asyncio
    async def test_no_anomaly_close_to_mean(self, db_session):
        """Review close to org mean should not be flagged."""
        org = Organization(name="Test Org", subscription_tier="enterprise")
        db_session.add(org)
        await db_session.flush()

        user = User(
            org_id=org.org_id,
            email="user@example.com",
            password_hash="hashed_pw",
            full_name="Test User",
            role="reviewer",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        doc = Document(
            org_id=org.org_id,
            doc_id=uuid4(),
            uploaded_by_user_id=user.user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="SOW",
        )
        db_session.add(doc)
        await db_session.flush()

        # Create historical reviews around 70
        for i in range(5):
            review = Review(
                review_id=uuid4(),
                org_id=org.org_id,
                doc_id=doc.doc_id,
                document_version=1,
                status="completed",
                overall_score=Decimal("70.00"),
            )
            db_session.add(review)
        await db_session.flush()

        # Target review at 72 (within 1 std dev)
        target_review = Review(
            org_id=org.org_id,
            doc_id=doc.doc_id,
            document_version=1,
            status="completed",
            overall_score=Decimal("72.00"),
        )
        db_session.add(target_review)
        await db_session.commit()

        result = await detect_score_anomalies(db_session, org.org_id, target_review.review_id)

        assert result["is_anomaly"] is False
        assert result["deviation"] < 2.0

    @pytest.mark.asyncio
    async def test_insufficient_historical_data(self, db_session):
        """< 2 historical reviews should skip anomaly check."""
        org = Organization(name="Test Org", subscription_tier="enterprise")
        db_session.add(org)
        await db_session.flush()

        user = User(
            org_id=org.org_id,
            email="user@example.com",
            password_hash="hashed_pw",
            full_name="Test User",
            role="reviewer",
            is_active=True,
        )
        db_session.add(user)
        await db_session.flush()

        doc = Document(
            org_id=org.org_id,
            doc_id=uuid4(),
            uploaded_by_user_id=user.user_id,
            filename="test.pdf",
            original_filename="test.pdf",
            file_type="pdf",
            file_size_bytes=1000,
            document_type="SOW",
        )
        db_session.add(doc)
        await db_session.flush()

        # Only one historical review
        historical = Review(
            review_id=uuid4(),
            org_id=org.org_id,
            doc_id=doc.doc_id,
            document_version=1,
            status="completed",
            overall_score=Decimal("70.00"),
        )
        db_session.add(historical)
        await db_session.flush()

        # Target review
        target_review = Review(
            org_id=org.org_id,
            doc_id=doc.doc_id,
            document_version=1,
            status="completed",
            overall_score=Decimal("30.00"),
        )
        db_session.add(target_review)
        await db_session.commit()

        result = await detect_score_anomalies(db_session, org.org_id, target_review.review_id)

        # Should return None for mean/stdev, False for anomaly
        assert result["org_mean"] is None
        assert result["org_stdev"] is None
        assert result["is_anomaly"] is False
        assert result["deviation"] is None

    @pytest.mark.asyncio
    async def test_nonexistent_review(self, db_session):
        """Nonexistent review should return None values."""
        org = Organization(name="Test Org", subscription_tier="enterprise")
        db_session.add(org)
        await db_session.commit()

        fake_review_id = uuid4()
        result = await detect_score_anomalies(db_session, org.org_id, fake_review_id)

        assert result["review_id"] == str(fake_review_id)
        assert result["overall_score"] is None
        assert result["is_anomaly"] is False
