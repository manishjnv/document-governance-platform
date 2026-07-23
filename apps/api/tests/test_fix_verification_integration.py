"""End-to-end check that POST /reviews/{doc_id}/trigger actually calls the
Phase C fix-verification wiring: reviewing a v2 document auto-resolves the
v1 review's findings that no longer appear, and keeps still-present ones
open regardless of a prior manual "Mark Fixed" claim."""

from dataclasses import dataclass, field
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

import app.routers.reviews as reviews_module
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
async def org_with_admin(db_session):
    org = Organization(name="Verify Test Org", subscription_tier="enterprise")
    db_session.add(org)
    await db_session.flush()

    admin = User(
        org_id=org.org_id, email="admin@verifytest.com",
        password_hash=hash_password("password123"), role="admin", is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    return {"org": org, "admin": admin}


async def _login(client, email, password="password123"):
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return response.json()["access_token"]


@dataclass
class _FakeReviewResult:
    results: list = field(default_factory=list)
    overall_confidence: float = 0.9
    total_duration_seconds: float = 1.0
    merged_findings: dict = field(default_factory=dict)
    rule_violations: list = field(default_factory=list)


def _fake_orchestrator(findings_types: list[str]):
    orchestrator = AsyncMock()
    orchestrator.review = AsyncMock(
        return_value=_FakeReviewResult(
            merged_findings={
                "findings": [
                    {
                        "type": t,
                        "source_agent": "scope",
                        "description": "desc",
                        "evidence": None,
                        "severity": "major",
                        "confidence": 0.8,
                        "recommendation": "fix it",
                    }
                    for t in findings_types
                ]
            }
        )
    )
    return orchestrator


class TestTriggerReviewVerifiesPreviousVersion:
    async def test_v2_review_resolves_and_persists_findings(
        self, client, db_session, org_with_admin, monkeypatch
    ):
        org, admin = org_with_admin["org"], org_with_admin["admin"]
        group_id = None

        doc_v1 = Document(
            org_id=org.org_id, uploaded_by_user_id=admin.user_id,
            filename="sow.pdf", original_filename="sow.pdf", file_size_bytes=1024,
            file_type="pdf", s3_path="s3://bucket/sow_v1.pdf", version=1,
            # >200 chars: trigger_review rejects unreadable/near-empty docs
            parsed_text="v1 text. " + "This agreement describes the scope of services in detail. " * 5,
        )
        db_session.add(doc_v1)
        await db_session.flush()
        group_id = doc_v1.document_group_id

        doc_v2 = Document(
            org_id=org.org_id, uploaded_by_user_id=admin.user_id,
            document_group_id=group_id,
            filename="sow_v2.pdf", original_filename="sow_v2.pdf", file_size_bytes=1024,
            file_type="pdf", s3_path="s3://bucket/sow_v2.pdf", version=2,
            parsed_text="v2 text. " + "This agreement describes the scope of services in detail. " * 5,
        )
        db_session.add(doc_v2)
        await db_session.commit()

        token = await _login(client, "admin@verifytest.com")

        # v1 review finds two issues: missing_liability_cap, undefined_sla.
        monkeypatch.setattr(
            reviews_module,
            "get_orchestrator",
            AsyncMock(return_value=_fake_orchestrator(["missing_liability_cap", "undefined_sla"])),
        )
        v1_response = await client.post(
            f"/api/v1/reviews/{doc_v1.doc_id}/trigger",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert v1_response.status_code == 202

        # v2 review only still finds undefined_sla -- missing_liability_cap
        # was actually fixed in the new text.
        monkeypatch.setattr(
            reviews_module,
            "get_orchestrator",
            AsyncMock(return_value=_fake_orchestrator(["undefined_sla"])),
        )
        v2_response = await client.post(
            f"/api/v1/reviews/{doc_v2.doc_id}/trigger",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert v2_response.status_code == 202

        from sqlalchemy import select

        v1_review_id = v1_response.json()["review_id"]
        findings_result = await db_session.execute(
            select(Finding).where(Finding.review_id == v1_review_id)
        )
        v1_findings = {f.category: f for f in findings_result.scalars().all()}

        assert v1_findings["missing_liability_cap"].status == "resolved"
        assert v1_findings["missing_liability_cap"].notes["resolution"] == "verified"

        assert v1_findings["undefined_sla"].status == "open"
        assert v1_findings["undefined_sla"].notes["resolution"] == "still_present"


class TestFindingDiffEndpoint:
    async def test_finding_diff_buckets(self, client, db_session, org_with_admin):
        org, admin = org_with_admin["org"], org_with_admin["admin"]

        doc_v1 = Document(
            org_id=org.org_id, uploaded_by_user_id=admin.user_id,
            filename="sow.pdf", original_filename="sow.pdf", file_size_bytes=1024,
            file_type="pdf", s3_path="s3://bucket/v1.pdf", version=1,
        )
        db_session.add(doc_v1)
        await db_session.flush()

        doc_v2 = Document(
            org_id=org.org_id, uploaded_by_user_id=admin.user_id,
            document_group_id=doc_v1.document_group_id,
            filename="sow_v2.pdf", original_filename="sow_v2.pdf", file_size_bytes=1024,
            file_type="pdf", s3_path="s3://bucket/v2.pdf", version=2,
        )
        db_session.add(doc_v2)
        await db_session.flush()

        from datetime import datetime, timezone

        review_v1 = Review(
            org_id=org.org_id, doc_id=doc_v1.doc_id, status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        review_v2 = Review(
            org_id=org.org_id, doc_id=doc_v2.doc_id, status="completed",
            completed_at=datetime.now(timezone.utc),
        )
        db_session.add_all([review_v1, review_v2])
        await db_session.flush()

        def _finding(review_id, category, status="open"):
            return Finding(
                org_id=org.org_id, review_id=review_id, finding_source="rule",
                rule_id="R1", category=category, title=category, description="d",
                severity="major", recommendation="r", status=status,
            )

        db_session.add_all(
            [
                _finding(review_v1.review_id, "missing_liability_cap", status="resolved"),
                _finding(review_v1.review_id, "undefined_sla"),
                _finding(review_v2.review_id, "undefined_sla"),
                _finding(review_v2.review_id, "vague_deliverables"),
            ]
        )
        await db_session.commit()

        token = await _login(client, "admin@verifytest.com")
        response = await client.get(
            f"/api/v1/documents/{doc_v1.doc_id}/versions/2/finding-diff",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        body = response.json()
        assert {f["category"] for f in body["resolved"]} == {"missing_liability_cap"}
        assert {f["category"] for f in body["persisted"]} == {"undefined_sla"}
        assert {f["category"] for f in body["new"]} == {"vague_deliverables"}
