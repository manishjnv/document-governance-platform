"""Tests for knowledge base features.

T-2036: FAQ database
T-2037: Similar findings search
T-2038: Issue resolution database
T-2039: Best practices guide
T-2040: Knowledge base search UI

Tests org-scoped isolation, full-text search, finding lookups.
Uses httpx.AsyncClient + ASGITransport to test HTTP endpoints against the real
Postgres db (TRUNCATE-isolated via conftest.py's db_session fixture).
"""

import pytest
from httpx import ASGITransport, AsyncClient
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.insights.knowledge import (
    create_article,
    delete_article,
    find_issue_resolution,
    list_articles,
    search_articles,
    search_similar_findings,
)
from app.models.document import Document
from app.models.finding import Finding
from app.models.kb_article import KBArticle
from app.models.organization import Organization
from app.models.review import Review
from app.models.user import User
from app.auth import hash_password
from main import app


async def _make_document(db_session, org_id):
    import uuid

    doc = Document(
        doc_id=uuid.uuid4(),
        document_group_id=uuid.uuid4(),
        org_id=org_id,
        filename="f.pdf",
        original_filename="f.pdf",
        file_size_bytes=100,
        file_type="pdf",
        s3_path=f"s3://bucket/{uuid.uuid4()}",
        version=1,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


@pytest.fixture
async def orgs_and_users(db_session):
    """Seed two orgs with users to test org isolation."""
    org1 = Organization(name="Org 1", subscription_tier="enterprise")
    org2 = Organization(name="Org 2", subscription_tier="enterprise")
    db_session.add(org1)
    db_session.add(org2)
    await db_session.flush()

    user1 = User(
        org_id=org1.org_id,
        email="user1@org1.com",
        password_hash=hash_password("password123"),
        full_name="User 1",
        role="admin",
        is_active=True,
    )
    user2 = User(
        org_id=org2.org_id,
        email="user2@org2.com",
        password_hash=hash_password("password123"),
        full_name="User 2",
        role="admin",
        is_active=True,
    )
    db_session.add(user1)
    db_session.add(user2)
    await db_session.commit()
    await db_session.refresh(user1)
    await db_session.refresh(user2)

    return (org1, user1), (org2, user2)


@pytest.fixture
async def kb_articles(db_session, orgs_and_users):
    """Seed knowledge base articles."""
    (org1, user1), (org2, user2) = orgs_and_users

    # Org 1 articles
    faq1 = await create_article(
        db_session,
        org1.org_id,
        "faq",
        "What is data retention?",
        "Data retention is the practice of keeping data according to legal requirements.",
        ["data", "compliance"],
        user1.user_id,
    )
    best_practice = await create_article(
        db_session,
        org1.org_id,
        "best_practice",
        "Data Privacy Best Practices",
        "Always encrypt sensitive data and implement access controls.",
        ["privacy", "security"],
        user1.user_id,
    )
    guide = await create_article(
        db_session,
        org1.org_id,
        "guide",
        "Complete Compliance Guide",
        "This guide covers GDPR, CCPA, and other privacy regulations.",
        ["compliance", "guide"],
        user1.user_id,
    )

    # Org 2 articles (different org)
    faq2 = await create_article(
        db_session,
        org2.org_id,
        "faq",
        "Org 2 Only FAQ",
        "This should not appear in Org 1 searches.",
        [],
        user2.user_id,
    )

    await db_session.commit()
    return {
        "org1": (org1, user1),
        "org2": (org2, user2),
        "articles": {
            "faq1": faq1,
            "best_practice": best_practice,
            "guide": guide,
            "faq2": faq2,
        },
    }


@pytest.fixture
async def findings(db_session, orgs_and_users):
    """Seed findings for similar-finding and resolution searches."""
    (org1, user1), (org2, user2) = orgs_and_users

    # Create a review for org1
    doc1 = await _make_document(db_session, org1.org_id)
    review1 = Review(
        org_id=org1.org_id,
        doc_id=doc1.doc_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(review1)
    await db_session.flush()

    # Org 1: mix of open and resolved findings
    finding_open = Finding(
        org_id=org1.org_id,
        review_id=review1.review_id,
        finding_source="agent",
        agent_name="DataPrivacy",
        category="Data Privacy",
        title="Missing encryption on sensitive fields",
        description="The document contains sensitive PII without encryption.",
        severity="critical",
        confidence=95.0,
        recommendation="Implement AES-256 encryption for all PII fields.",
        status="open",
    )

    finding_resolved = Finding(
        org_id=org1.org_id,
        review_id=review1.review_id,
        finding_source="agent",
        agent_name="DataPrivacy",
        category="Data Privacy",
        title="Expired data retention clause",
        description="The retention period has expired and should be updated.",
        severity="medium",
        confidence=85.0,
        recommendation="Update retention policy to comply with GDPR.",
        status="resolved",
    )

    # Org 2: findings (should not appear in org1 queries)
    doc2 = await _make_document(db_session, org2.org_id)
    review2 = Review(
        org_id=org2.org_id,
        doc_id=doc2.doc_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(review2)
    await db_session.flush()

    finding_org2 = Finding(
        org_id=org2.org_id,
        review_id=review2.review_id,
        finding_source="agent",
        agent_name="Compliance",
        category="Data Privacy",
        title="Org 2 only finding",
        description="Should not appear in Org 1 queries.",
        severity="low",
        confidence=50.0,
        recommendation="N/A",
        status="open",
    )

    db_session.add(finding_open)
    db_session.add(finding_resolved)
    db_session.add(finding_org2)
    await db_session.commit()

    return {
        "org1": (org1, user1),
        "org2": (org2, user2),
        "findings": {
            "open": finding_open,
            "resolved": finding_resolved,
            "org2_only": finding_org2,
        },
    }


class TestCreateArticle:
    """Test creating knowledge base articles."""

    async def test_create_faq(self, db_session, orgs_and_users):
        org, user = orgs_and_users[0]
        article = await create_article(
            db_session,
            org.org_id,
            "faq",
            "Test FAQ",
            "This is a test FAQ.",
            ["test", "faq"],
            user.user_id,
        )

        assert article.article_id is not None
        assert article.article_type == "faq"
        assert article.title == "Test FAQ"
        assert article.org_id == org.org_id
        assert article.tags == ["test", "faq"]

    async def test_create_best_practice(self, db_session, orgs_and_users):
        org, user = orgs_and_users[0]
        article = await create_article(
            db_session,
            org.org_id,
            "best_practice",
            "Security Best Practice",
            "Always use HTTPS.",
        )

        assert article.article_type == "best_practice"
        assert article.title == "Security Best Practice"
        assert article.tags == []


class TestListArticles:
    """Test listing knowledge base articles."""

    async def test_list_all_articles(self, db_session, kb_articles):
        org, user = kb_articles["org1"]
        articles = await list_articles(db_session, org.org_id)

        assert len(articles) == 3
        titles = {a.title for a in articles}
        assert "What is data retention?" in titles
        assert "Data Privacy Best Practices" in titles
        assert "Complete Compliance Guide" in titles

    async def test_list_by_type(self, db_session, kb_articles):
        org, user = kb_articles["org1"]
        faqs = await list_articles(db_session, org.org_id, article_type="faq")

        assert len(faqs) == 1
        assert faqs[0].title == "What is data retention?"

        guides = await list_articles(db_session, org.org_id, article_type="guide")
        assert len(guides) == 1
        assert guides[0].title == "Complete Compliance Guide"

    async def test_list_org_isolation(self, db_session, kb_articles):
        org1, user1 = kb_articles["org1"]
        org2, user2 = kb_articles["org2"]

        org1_articles = await list_articles(db_session, org1.org_id)
        org2_articles = await list_articles(db_session, org2.org_id)

        assert len(org1_articles) == 3
        assert len(org2_articles) == 1
        assert org2_articles[0].title == "Org 2 Only FAQ"


class TestSearchArticles:
    """Test full-text search over knowledge base."""

    async def test_search_by_title(self, db_session, kb_articles):
        org, user = kb_articles["org1"]
        results = await search_articles(db_session, org.org_id, "data retention")

        assert len(results) >= 1
        result_titles = [r["title"] for r in results]
        assert any("data retention" in t.lower() for t in result_titles)

    async def test_search_by_content(self, db_session, kb_articles):
        org, user = kb_articles["org1"]
        results = await search_articles(db_session, org.org_id, "encryption")

        assert len(results) >= 1
        assert any("encrypt" in r["snippet"].lower() for r in results)

    async def test_search_empty_query(self, db_session, kb_articles):
        org, user = kb_articles["org1"]

        with pytest.raises(ValueError, match="search query must not be empty"):
            await search_articles(db_session, org.org_id, "   ")

    async def test_search_no_results(self, db_session, kb_articles):
        org, user = kb_articles["org1"]
        results = await search_articles(db_session, org.org_id, "nonexistent")

        assert len(results) == 0

    async def test_search_org_isolation(self, db_session, kb_articles):
        org1, user1 = kb_articles["org1"]
        org2, user2 = kb_articles["org2"]

        # Org 2 FAQ should not appear in org1 search. Note: "only" is an
        # English full-text stopword (websearch_to_tsquery('english', 'only')
        # returns an empty tsquery, so it can never match anything) -- use
        # "appear" instead, a real lexeme unique to org2's article content.
        org1_results = await search_articles(db_session, org1.org_id, "appear")
        org2_results = await search_articles(db_session, org2.org_id, "appear")

        assert len(org1_results) == 0
        assert len(org2_results) >= 1


class TestDeleteArticle:
    """Test soft-deleting articles."""

    async def test_delete_article(self, db_session, kb_articles):
        org, user = kb_articles["org1"]
        article_id = kb_articles["articles"]["faq1"].article_id

        await delete_article(db_session, org.org_id, article_id)
        await db_session.commit()

        # Article should be soft-deleted, not appear in list
        articles = await list_articles(db_session, org.org_id)
        assert len(articles) == 2
        assert not any(a.article_id == article_id for a in articles)

    async def test_delete_article_not_found(self, db_session, orgs_and_users):
        org, user = orgs_and_users[0]

        with pytest.raises(ValueError, match="Article not found"):
            await delete_article(db_session, org.org_id, __import__("uuid").uuid4())

    async def test_delete_article_wrong_org(self, db_session, kb_articles):
        org1, user1 = kb_articles["org1"]
        org2, user2 = kb_articles["org2"]
        article_id = kb_articles["articles"]["faq1"].article_id  # org1's article

        with pytest.raises(ValueError, match="Article not found"):
            # Try to delete org1's article as org2
            await delete_article(db_session, org2.org_id, article_id)


class TestSimilarFindings:
    """Test similar findings search."""

    async def test_search_similar_findings(self, db_session, findings):
        org1, user1 = findings["org1"]
        results = await search_similar_findings(db_session, org1.org_id, "encryption")

        assert len(results) >= 1
        assert any("encryption" in r["title"].lower() for r in results)

    async def test_similar_findings_org_isolation(self, db_session, findings):
        org1, user1 = findings["org1"]
        org2, user2 = findings["org2"]

        # Org 1 search should not return org 2's findings
        org1_results = await search_similar_findings(db_session, org1.org_id, "org 2")
        org2_results = await search_similar_findings(db_session, org2.org_id, "org 2")

        assert len(org1_results) == 0
        assert len(org2_results) >= 1

    async def test_similar_findings_empty_query(self, db_session, findings):
        org1, user1 = findings["org1"]

        with pytest.raises(ValueError, match="search query must not be empty"):
            await search_similar_findings(db_session, org1.org_id, "   ")


class TestIssueResolution:
    """Test finding issue resolutions by category."""

    async def test_find_resolutions_by_category(self, db_session, findings):
        org1, user1 = findings["org1"]
        results = await find_issue_resolution(db_session, org1.org_id, "Data Privacy")

        # Should only return resolved findings
        assert len(results) >= 1
        resolved_finding = results[0]
        assert resolved_finding["title"] == "Expired data retention clause"
        assert "Update retention policy" in resolved_finding["recommendation"]

    async def test_find_resolutions_excludes_open(self, db_session, findings):
        org1, user1 = findings["org1"]
        results = await find_issue_resolution(db_session, org1.org_id, "Data Privacy")

        # The open finding should not appear
        titles = [r["title"] for r in results]
        assert "Missing encryption on sensitive fields" not in titles

    async def test_find_resolutions_org_isolation(self, db_session, findings):
        org1, user1 = findings["org1"]
        org2, user2 = findings["org2"]

        org1_results = await find_issue_resolution(db_session, org1.org_id, "Data Privacy")
        org2_results = await find_issue_resolution(db_session, org2.org_id, "Data Privacy")

        # Org 1 has resolved findings; org 2's open finding doesn't count
        assert len(org1_results) >= 1
        assert len(org2_results) == 0

    async def test_find_resolutions_nonexistent_category(self, db_session, findings):
        org1, user1 = findings["org1"]
        results = await find_issue_resolution(db_session, org1.org_id, "NonExistent")

        assert len(results) == 0


class TestHTTPEndpoints:
    """Test HTTP API endpoints for knowledge base."""

    @pytest.fixture
    async def authenticated_client(self, client, orgs_and_users, db_session):
        """Return authenticated client and user fixture."""
        org, user = orgs_and_users[0]
        # Build a real access token via the production helper (app/auth.py) --
        # matches what app/dependencies.py's get_current_user actually expects
        # (user_id/org_id/role/type claims, jwt_secret_key/jwt_algorithm), same
        # pattern as tests/test_auth.py.
        from app.auth import create_access_token

        token, _ = create_access_token(user.user_id, user.email, org.org_id, user.role)
        client.headers.update({"Authorization": f"Bearer {token}"})
        return client, org, user

    async def test_post_article_endpoint(self, authenticated_client, db_session):
        client, org, user = authenticated_client
        response = await client.post(
            "/api/v1/knowledge-base/articles",
            params={
                "article_type": "faq",
                "title": "Test FAQ via API",
                "content": "This is a test.",
                "tags": ["test"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["article_type"] == "faq"
        assert data["title"] == "Test FAQ via API"
        assert data["org_id"] == str(org.org_id)

    async def test_get_articles_endpoint(self, authenticated_client, db_session, kb_articles):
        client, org, user = authenticated_client
        response = await client.get("/api/v1/knowledge-base/articles")

        assert response.status_code == 200
        data = response.json()
        assert "articles" in data
        assert len(data["articles"]) >= 0

    async def test_delete_article_endpoint(self, authenticated_client, db_session, kb_articles):
        client, org, user = authenticated_client
        # Get an article to delete
        articles = await list_articles(db_session, org.org_id)
        article_id = articles[0].article_id

        response = await client.delete(f"/api/v1/knowledge-base/articles/{article_id}")
        assert response.status_code == 204

    async def test_search_articles_endpoint(self, authenticated_client, db_session, kb_articles):
        client, org, user = authenticated_client
        response = await client.get("/api/v1/knowledge-base/articles/search", params={"q": "data"})

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert data["query"] == "data"

    async def test_similar_findings_endpoint(self, authenticated_client, db_session, findings):
        client, org, user = authenticated_client
        response = await client.get(
            "/api/v1/knowledge-base/similar-findings", params={"q": "encryption"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    async def test_issue_resolutions_endpoint(self, authenticated_client, db_session, findings):
        client, org, user = authenticated_client
        response = await client.get(
            "/api/v1/knowledge-base/issue-resolutions", params={"category": "Data Privacy"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "category" in data
