"""Endpoint tests for GET /api/v1/reviews/{review_id}/report.

Covers the report redesign wiring in app/routers/reviews.py: doc stats,
findings-count, per-category finding recompute, and -- the actual bug --
format=pdf previously ran pdf_bytes.decode("utf-8", errors="ignore") on
binary PDF data, corrupting it. format=pdf must now return valid base64
that decodes back to real PDF bytes.
"""

import base64
from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import hash_password
from app.models.document import Document
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User
from main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def completed_review(db_session):
    org = Organization(name="Report Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id, email="admin@reporttest.com",
        password_hash=hash_password("password123"), role="admin", is_active=True,
    )
    db_session.add(admin)
    await db_session.flush()

    doc = Document(
        org_id=org.org_id,
        uploaded_by_user_id=admin.user_id,
        filename="msa.docx",
        original_filename="MSA_Final.docx",
        file_size_bytes=2048,
        file_type="docx",
        s3_path="s3://bucket/msa.docx",
        document_type="SOW",
        version=1,
        page_count=9,
        project_name="Acme Rollout",
        parsed_sections=[{"heading": "Payment Terms"}, {"heading": "Scope of Work"}],
    )
    db_session.add(doc)
    await db_session.flush()

    review = Review(
        review_id=uuid4(),
        org_id=org.org_id,
        doc_id=doc.doc_id,
        triggered_by_user_id=admin.user_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        overall_score=42.0,
        risk_score=65.0,
        score_completeness=40.0,
        score_clarity=70.0,
        score_consistency=70.0,
        score_commercial=70.0,
        score_delivery=70.0,
        score_operations=70.0,
        score_security=90.0,
        executive_summary="Weak document health.",
        risk_breakdown={"Legal": 80.0, "Scope": 55.0},
        critical_finding_count=1,
        major_finding_count=1,
        medium_finding_count=0,
        low_finding_count=0,
        info_finding_count=0,
    )
    db_session.add(review)
    await db_session.flush()

    findings = [
        Finding(
            finding_id=uuid4(),
            org_id=org.org_id,
            review_id=review.review_id,
            finding_source="agent",
            agent_name="ScopeReviewer",
            category="completeness",
            title="Missing acceptance criteria",
            description="No acceptance criteria section found.",
            evidence="",
            section_ref="Scope of Work (p.3)",
            severity="critical",
            confidence=90,
            recommendation="Add an acceptance criteria section.",
            status="open",
        ),
        Finding(
            finding_id=uuid4(),
            org_id=org.org_id,
            review_id=review.review_id,
            finding_source="rule",
            rule_id="missing-termination-clause",
            category="legal",
            title="Missing termination clause",
            description="Required termination clause not found.",
            evidence="",
            severity="major",
            confidence=100,
            recommendation="Add a termination clause.",
            status="open",
        ),
    ]
    db_session.add_all(findings)
    await db_session.commit()
    await db_session.refresh(admin)

    return {"org": org, "admin": admin, "doc": doc, "review": review}


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


class TestGenerateReport:
    async def test_html_report_includes_new_sections(self, client, completed_review):
        token = await _login(client, "admin@reporttest.com")
        response = await client.get(
            f"/api/v1/reviews/{completed_review['review'].review_id}/report?format=html",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["format"] == "html"
        html = body["data"]

        assert "ScopeWise" in html
        assert "Acme Rollout" in html  # doc stats strip
        assert "Document X-Ray" in html
        assert "Payment Terms" in html  # section found
        assert "Missing termination clause" in html  # rule gap
        assert "Scope of Work (p.3)" in html  # finding section+page ref
        assert "Legal" in html  # top risk area
        assert "Scope" in html  # agent finding tagged with its risk_area
        assert "Compliance" in html  # rule finding tagged with its risk_area
        assert "Why it matters:" in html  # finding restructured into labeled points
        assert "Recommendation:" in html
        assert "scorecard-table" in html  # compact table, not the old card grid
        assert "Are all required sections" in html  # heatmap category description

    async def test_pdf_report_returns_valid_pdf_bytes(self, client, completed_review, require_weasyprint):
        """Regression: format=pdf used to decode binary PDF bytes as UTF-8
        with errors="ignore" before returning them, corrupting the file.
        The base64 payload must decode back to real, openable PDF bytes."""
        token = await _login(client, "admin@reporttest.com")
        response = await client.get(
            f"/api/v1/reviews/{completed_review['review'].review_id}/report?format=pdf",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["format"] == "pdf"

        pdf_bytes = base64.b64decode(body["data"])
        assert pdf_bytes.startswith(b"%PDF-")
