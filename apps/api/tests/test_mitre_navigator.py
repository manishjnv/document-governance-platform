"""Navigator layer export tests (Phase 8). Pure golden layers + the
json/zip endpoint against real edgp_test Postgres. No LLM anywhere."""

import io
import json
import uuid
import zipfile
from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.auth import create_access_token
from app.mitre.navigator import build_navigator_layers
from app.models.mitre_assessment import MitreAssessment
from app.models.organization import Organization
from app.models.user import User
from main import app

GREEN, AMBER, RED, GREY = "#10b981", "#f59e0b", "#f43f5e", "#9ca3af"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


async def _make_user(db_session, *, role="admin"):
    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"{uuid.uuid4()}@x.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role=role
    )
    return org, user, {"Authorization": f"Bearer {token}"}


def _result(tid, state, domain="enterprise", refs=(), na_reason=None):
    return {
        "technique_id": tid, "domain": domain, "tactics": ["TA0002"],
        "state": state, "na_reason": na_reason, "use_case_refs": list(refs),
    }


_ENTERPRISE_RESULTS = [
    _result("T1059.001", "covered", refs=["s:1", "s:2"]),
    _result("T1003.001", "partial", refs=["s:3"]),
    _result("T1112", "not_covered"),
    _result("T1200", "not_applicable", na_reason="accepted risk, physical controls"),
]


async def _seed(db_session, org, user, *, status="completed", results=None, domains=("enterprise",)):
    assessment = MitreAssessment(
        assessment_id=uuid.uuid4(),
        org_id=org.org_id,
        name="Seeded assessment",
        status=status,
        attack_version="19.1",
        summary={"applicable_domains": list(domains)} if status == "completed" else None,
        technique_results=results if results is not None else _ENTERPRISE_RESULTS,
        completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        created_by=user.user_id,
        params={},
    )
    db_session.add(assessment)
    await db_session.commit()
    return assessment


# --- pure golden ---

def test_layer_golden_single_domain():
    class A:
        name = "Q3 SOC coverage"
        attack_version = "19.1"
        technique_results = _ENTERPRISE_RESULTS
        summary = {"applicable_domains": ["enterprise"]}

    layers = build_navigator_layers(A())
    assert [d for d, _ in layers] == ["enterprise"]
    layer = layers[0][1]
    assert layer["domain"] == "enterprise-attack"
    assert layer["versions"] == {"attack": "19.1", "navigator": "5.1.1", "layer": "4.5"}
    by_id = {t["techniqueID"]: t for t in layer["techniques"]}
    assert len(by_id) == 4
    assert by_id["T1059.001"]["color"] == GREEN
    assert by_id["T1059.001"]["comment"] == "2 mapped detection rule(s)"
    assert by_id["T1003.001"]["color"] == AMBER
    assert by_id["T1112"]["color"] == RED
    assert by_id["T1112"]["comment"] == ""
    assert by_id["T1200"]["color"] == GREY
    assert by_id["T1200"]["enabled"] is False
    assert by_id["T1200"]["comment"] == "accepted risk, physical controls"
    assert all(t["enabled"] for tid, t in by_id.items() if tid != "T1200")
    assert len(layer["legendItems"]) == 4


def test_layers_multi_domain_stable_order():
    class A:
        name = "x"
        attack_version = "19.1"
        technique_results = [
            _result("T0817", "covered", domain="ics", refs=["s:9"]),
            _result("T1059.001", "covered", refs=["s:1"]),
        ]
        summary = {"applicable_domains": ["ics", "enterprise"]}  # order in summary ignored

    layers = build_navigator_layers(A())
    assert [d for d, _ in layers] == ["enterprise", "ics"]
    assert layers[1][1]["domain"] == "ics-attack"


def test_non_applicable_domain_gets_no_layer():
    class A:
        name = "x"
        attack_version = "19.1"
        technique_results = _ENTERPRISE_RESULTS + [_result("T1660", "not_covered", domain="mobile")]
        summary = {"applicable_domains": ["enterprise"]}  # mobile gated out

    assert [d for d, _ in build_navigator_layers(A())] == ["enterprise"]


# --- endpoint ---

@pytest.mark.asyncio
async def test_navigator_endpoint_single_domain_json(client, db_session):
    org, user, headers = await _make_user(db_session, role="viewer")  # viewer-readable
    assessment = await _seed(db_session, org, user)
    res = await client.get(
        f"/api/v1/mitre/assessments/{assessment.assessment_id}/navigator", headers=headers
    )
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("application/json")
    assert 'filename="Seeded_assessment-navigator-enterprise.json"' in res.headers["content-disposition"]
    layer = json.loads(res.content)
    assert layer["domain"] == "enterprise-attack"
    assert len(layer["techniques"]) == 4


@pytest.mark.asyncio
async def test_navigator_endpoint_multi_domain_zip(client, db_session):
    org, user, headers = await _make_user(db_session)
    assessment = await _seed(
        db_session, org, user,
        results=_ENTERPRISE_RESULTS + [_result("T0817", "not_covered", domain="ics")],
        domains=("enterprise", "ics"),
    )
    res = await client.get(
        f"/api/v1/mitre/assessments/{assessment.assessment_id}/navigator", headers=headers
    )
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = sorted(zf.namelist())
    assert names == [
        "Seeded_assessment-navigator-enterprise.json",
        "Seeded_assessment-navigator-ics.json",
    ]
    ics_layer = json.loads(zf.read(names[1]))
    assert ics_layer["domain"] == "ics-attack"
    assert ics_layer["techniques"][0]["techniqueID"] == "T0817"


@pytest.mark.asyncio
async def test_navigator_cross_org_404_and_pending_409(client, db_session):
    org_a, user_a, headers_a = await _make_user(db_session)
    _, _, headers_b = await _make_user(db_session)
    completed = await _seed(db_session, org_a, user_a)
    pending = await _seed(db_session, org_a, user_a, status="pending")

    cross = await client.get(
        f"/api/v1/mitre/assessments/{completed.assessment_id}/navigator", headers=headers_b
    )
    assert cross.status_code == 404

    not_done = await client.get(
        f"/api/v1/mitre/assessments/{pending.assessment_id}/navigator", headers=headers_a
    )
    assert not_done.status_code == 409
