"""Tests for the analytics & reporting endpoints.

T-2006 (document analytics), T-2007 (review metrics), T-2008 (performance
dashboard), T-2016 (custom report builder), T-2018 (report templates),
T-2020 (report archive & history).

app/routers/analytics.py is a new router main.py does not register (out of
scope for this task -- see its module docstring / this bundle's final
report). Registering it on the shared `main.app` once here, the same
ASGITransport pattern test_auth.py's history documents as the one that
actually works with the real async DB session (starlette's sync TestClient
runs the app on a separate thread/loop and breaks it).
"""

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.models.document import Document
from app.models.finding import Finding
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User

# Organization.kb_articles is a string-typed relationship("KBArticle", ...);
# SQLAlchemy only resolves that name if kb_article.py has been imported
# somewhere first. Nothing in this test's own import chain otherwise pulls
# it in (models/__init__.py doesn't list it yet -- a concurrent Wave 2
# bundle owns that model), so import it here just to register the class
# before any Organization() gets constructed below.
import app.models.kb_article  # noqa: F401
from app.routers.analytics import router as analytics_router
from main import app

# main.py deliberately isn't touched by this bundle -- see task boundary in
# the module docstring above. Registering here is idempotent enough for a
# single pytest session (module import happens once).
app.include_router(analytics_router)


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


def _auth_headers(user_id, email, org_id, role="admin") -> dict:
    token, _ = create_access_token(user_id=user_id, email=email, org_id=org_id, role=role)
    return {"Authorization": f"Bearer {token}"}


async def _seed_org_with_data(db_session, *, doc_count=2, review_count=2):
    """Create an org + user + N documents + N completed reviews (each with
    one finding), return (org, user, documents, reviews)."""
    org = Organization(name=f"Org-{uuid4()}", subscription_tier="pro")
    db_session.add(org)
    await db_session.flush()

    user = User(org_id=org.org_id, email=f"user-{uuid4()}@example.com", role="admin")
    db_session.add(user)
    await db_session.flush()

    documents = []
    for i in range(doc_count):
        doc = Document(
            org_id=org.org_id,
            document_group_id=uuid4(),
            filename=f"doc-{i}.pdf",
            original_filename=f"Doc {i}.pdf",
            file_size_bytes=1024,
            file_type="pdf",
            s3_path=f"s3://bucket/{uuid4()}/doc-{i}.pdf",
            version=1,
            uploaded_by_user_id=user.user_id,
        )
        db_session.add(doc)
        documents.append(doc)
    await db_session.flush()

    reviews = []
    now = datetime.now(timezone.utc)
    for i, doc in enumerate(documents[:review_count]):
        review = Review(
            org_id=org.org_id,
            doc_id=doc.doc_id,
            document_version=1,
            status="completed",
            overall_score=Decimal("70.00") + Decimal((i % 3) * 10),  # stays <= 100 for any review_count
            processing_time_seconds=30 + i,
            completed_at=now,
            created_at=now,
        )
        db_session.add(review)
        reviews.append(review)
    await db_session.flush()

    for i, review in enumerate(reviews):
        db_session.add(
            Finding(
                org_id=org.org_id,
                review_id=review.review_id,
                finding_source="rule",
                rule_id="SOW-001",
                category="scope",
                title="Missing scope",
                description="Scope section is incomplete",
                recommendation="Add a detailed scope section",
                severity="critical" if i == 0 else "major",
            )
        )

    await db_session.commit()
    return org, user, documents, reviews


class TestDocumentAnalytics:
    """T-2006."""

    async def test_document_analytics_counts_views(self, client, db_session):
        org, user, documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=1, review_count=1
        )
        doc = documents[0]
        headers = _auth_headers(user.user_id, user.email, org.org_id)

        other = User(org_id=org.org_id, email=f"viewer-{uuid4()}@example.com", role="viewer")
        db_session.add(other)
        await db_session.commit()
        other_headers = _auth_headers(other.user_id, other.email, org.org_id, role="viewer")

        # Two reads by the same user, one by a second user
        assert (await client.get(f"/api/v1/documents/{doc.doc_id}", headers=headers)).status_code == 200
        assert (await client.get(f"/api/v1/documents/{doc.doc_id}", headers=headers)).status_code == 200
        assert (
            await client.get(f"/api/v1/documents/{doc.doc_id}", headers=other_headers)
        ).status_code == 200

        response = await client.get(f"/api/v1/analytics/documents/{doc.doc_id}", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["view_count"] == 3
        assert data["unique_viewer_count"] == 2
        assert data["latest_review_score"] == 70.0
        assert data["latest_review_status"] == "completed"

    async def test_document_analytics_not_found(self, client, db_session):
        org, user, _documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=0, review_count=0
        )
        headers = _auth_headers(user.user_id, user.email, org.org_id)
        response = await client.get(f"/api/v1/analytics/documents/{uuid4()}", headers=headers)
        assert response.status_code == 404

    async def test_document_analytics_cross_org_denied(self, client, db_session):
        org_a, _user_a, docs_a, _reviews_a = await _seed_org_with_data(
            db_session, doc_count=1, review_count=1
        )
        org_b, user_b, _docs_b, _reviews_b = await _seed_org_with_data(
            db_session, doc_count=0, review_count=0
        )
        headers_b = _auth_headers(user_b.user_id, user_b.email, org_b.org_id)

        response = await client.get(
            f"/api/v1/analytics/documents/{docs_a[0].doc_id}", headers=headers_b
        )
        assert response.status_code == 404


class TestReviewMetrics:
    """T-2007."""

    async def test_review_metrics_scoped_to_org(self, client, db_session):
        org_a, user_a, _docs_a, _reviews_a = await _seed_org_with_data(
            db_session, doc_count=1, review_count=1
        )
        _org_b, _user_b, _docs_b, _reviews_b = await _seed_org_with_data(
            db_session, doc_count=1, review_count=1
        )
        headers_a = _auth_headers(user_a.user_id, user_a.email, org_a.org_id)

        response = await client.get("/api/v1/analytics/reviews/metrics", headers=headers_a)
        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "overall"
        total_reviews = sum(p["review_count"] for p in data["points"])
        assert total_reviews == 1  # not org_b's review


class TestPerformanceDashboard:
    """T-2008."""

    async def test_dashboard_counts_and_severity(self, client, db_session):
        org, user, _documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=3, review_count=2
        )
        headers = _auth_headers(user.user_id, user.email, org.org_id)

        response = await client.get("/api/v1/analytics/dashboard", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 3
        assert data["total_reviews"] == 2
        assert data["avg_overall_score"] == 75.0  # (70 + 80) / 2
        assert data["finding_counts_by_severity"]["critical"] == 1
        assert data["finding_counts_by_severity"]["major"] == 1
        assert data["finding_counts_by_severity"]["low"] == 0

    async def test_dashboard_isolated_between_orgs(self, client, db_session):
        _org_a, _user_a, _docs_a, _reviews_a = await _seed_org_with_data(
            db_session, doc_count=5, review_count=5
        )
        org_b, user_b, _docs_b, _reviews_b = await _seed_org_with_data(
            db_session, doc_count=0, review_count=0
        )
        headers_b = _auth_headers(user_b.user_id, user_b.email, org_b.org_id)

        response = await client.get("/api/v1/analytics/dashboard", headers=headers_b)
        assert response.status_code == 200
        data = response.json()
        assert data["total_documents"] == 0
        assert data["total_reviews"] == 0


class TestReportTemplates:
    """T-2018."""

    async def test_list_templates(self, client, db_session):
        org, user, _documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=0, review_count=0
        )
        headers = _auth_headers(user.user_id, user.email, org.org_id)

        response = await client.get("/api/v1/analytics/reports/templates", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "executive" in data
        assert "detailed" in data
        assert "compliance" in data
        assert "total_documents" in data["detailed"]


class TestReportArchive:
    """T-2016, T-2020."""

    async def test_create_report_with_template_and_read_back(self, client, db_session):
        org, user, _documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=2, review_count=2
        )
        headers = _auth_headers(user.user_id, user.email, org.org_id)

        create_resp = await client.post(
            "/api/v1/analytics/reports",
            json={"template": "executive"},
            headers=headers,
        )
        assert create_resp.status_code == 201
        created = create_resp.json()
        assert created["metrics"]["total_documents"] == 2
        assert "score_trends" in created["metrics"]
        report_id = created["report_id"]

        detail_resp = await client.get(f"/api/v1/analytics/reports/{report_id}", headers=headers)
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["report_type"] == "executive"
        assert detail["report_id"] == report_id

        list_resp = await client.get("/api/v1/analytics/reports", headers=headers)
        assert list_resp.status_code == 200
        listing = list_resp.json()
        assert len(listing) == 1
        assert listing[0]["report_id"] == report_id

    async def test_create_report_custom_metrics(self, client, db_session):
        org, user, _documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=1, review_count=1
        )
        headers = _auth_headers(user.user_id, user.email, org.org_id)

        response = await client.post(
            "/api/v1/analytics/reports",
            json={"metrics": ["total_documents", "avg_overall_score"]},
            headers=headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert set(data["metrics"].keys()) == {"total_documents", "avg_overall_score"}

    async def test_create_report_requires_metrics_or_template(self, client, db_session):
        org, user, _documents, _reviews = await _seed_org_with_data(
            db_session, doc_count=0, review_count=0
        )
        headers = _auth_headers(user.user_id, user.email, org.org_id)

        response = await client.post("/api/v1/analytics/reports", json={}, headers=headers)
        assert response.status_code == 422

    async def test_report_archive_isolated_between_orgs(self, client, db_session):
        org_a, user_a, _docs_a, _reviews_a = await _seed_org_with_data(
            db_session, doc_count=1, review_count=1
        )
        org_b, user_b, _docs_b, _reviews_b = await _seed_org_with_data(
            db_session, doc_count=0, review_count=0
        )
        headers_a = _auth_headers(user_a.user_id, user_a.email, org_a.org_id)
        headers_b = _auth_headers(user_b.user_id, user_b.email, org_b.org_id)

        create_resp = await client.post(
            "/api/v1/analytics/reports",
            json={"template": "compliance"},
            headers=headers_a,
        )
        report_id = create_resp.json()["report_id"]

        # org_b cannot read org_a's archived report
        detail_resp = await client.get(f"/api/v1/analytics/reports/{report_id}", headers=headers_b)
        assert detail_resp.status_code == 404

        # org_b's own listing is empty
        list_resp = await client.get("/api/v1/analytics/reports", headers=headers_b)
        assert list_resp.status_code == 200
        assert list_resp.json() == []
