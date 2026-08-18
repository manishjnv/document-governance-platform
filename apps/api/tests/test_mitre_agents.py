"""LLM-agent unit + pipeline tests (MITRE Phase 2). LLM is always faked —
a stub client on the agent (unit level) or patched driver functions
(pipeline level). No OpenRouter calls anywhere.
"""

import asyncio
import io
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from openpyxl import Workbook

from app.auth import create_access_token
from app.mitre import agents
from app.mitre.agents import (
    MitreNarrativeAgent,
    MitreTaggingAgent,
    build_template_narrative,
    extract_use_cases_from_text,
    generate_narrative,
    tag_untagged_rows,
)
from app.mitre.attack_data import AttackIndex
from app.models.organization import Organization
from app.models.user import User
from main import app


# ---------------------------------------------------------------------------
# Fake LLM plumbing (mimics the Anthropic/OpenRouter client surface).
# ---------------------------------------------------------------------------


class _FakeMessage:
    def __init__(self, text):
        self.content = [type("Block", (), {"text": text})()]


class _FakeMessages:
    def __init__(self, outer):
        self._outer = outer

    def create(self, **kwargs):
        self._outer.calls.append(kwargs)
        item = self._outer.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeMessage(item)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.messages = _FakeMessages(self)


def _agent(responses, fallbacks=(), cls=MitreTaggingAgent):
    agent = cls()
    agent.client = FakeClient(responses)
    agent.model = "fake-primary"
    agent._fallback_models = list(fallbacks)
    return agent


def _t(tid, deprecated=False, revoked=False, superseded_by=None):
    return {
        "id": tid, "name": tid, "tactics": ["TA0002"], "platforms": ["Windows"],
        "data_sources": [], "is_subtechnique": "." in tid,
        "parent_id": tid.split(".")[0] if "." in tid else None,
        "deprecated": deprecated, "revoked": revoked,
        "superseded_by": superseded_by, "summary": "",
    }


def _index():
    return AttackIndex({
        "version": "19.1",
        "domains": {"enterprise": {
            "tactics": [{"id": "TA0002", "shortname": "execution", "name": "Execution"}],
            "techniques": [
                _t("T1059"), _t("T1059.001"), _t("T1112"),
                _t("T1998", revoked=True, superseded_by="T1112"),
                _t("T1999", deprecated=True),
            ],
        }},
    })


def _rows(n, prefix="s"):
    return [
        {"row_ref": f"{prefix}:{i}", "name": f"rule {i}", "description": "", "logic": ""}
        for i in range(1, n + 1)
    ]


def _tag_response(refs, technique_ids, confidence):
    return json.dumps({
        "mappings": [
            {"row_ref": ref, "technique_ids": technique_ids,
             "confidence": confidence, "rationale": "r"}
            for ref in refs
        ],
        "overall_confidence": confidence,
    })


# ---------------------------------------------------------------------------
# tag_untagged_rows
# ---------------------------------------------------------------------------


async def test_tagging_two_batches_success():
    rows = _rows(30)
    responses = [
        _tag_response([r["row_ref"] for r in rows[:25]], ["T1059.001"], 0.9),
        _tag_response([r["row_ref"] for r in rows[25:]], ["T1112"], 0.8),
    ]
    result = await tag_untagged_rows(rows, index=_index(), agent=_agent(responses))
    assert result["batches_total"] == 2 and result["batches_failed"] == 0
    assert len(result["mappings_by_ref"]) == 30
    assert result["mappings_by_ref"]["s:1"][0] == {
        "technique_id": "T1059.001", "source": "ai", "confidence": 0.9, "rationale": "r",
    }
    assert result["models_used"] == ["fake-primary"]
    assert any("AI-tagged" in a for a in result["assumptions"])


async def test_failed_batch_degrades_to_unmapped_without_raising():
    rows = _rows(30)
    responses = [
        RuntimeError("provider down"),   # batch 1, attempt 1
        RuntimeError("provider down"),   # batch 1, retry
        _tag_response([r["row_ref"] for r in rows[25:]], ["T1112"], 0.9),  # batch 2
    ]
    result = await tag_untagged_rows(rows, index=_index(), agent=_agent(responses))
    assert result["batches_failed"] == 1
    assert "s:1" not in result["mappings_by_ref"]
    assert "s:26" in result["mappings_by_ref"]
    assert any("AI tagging unavailable for 25 rules" in a for a in result["assumptions"])


async def test_garbage_json_advances_model_chain():
    rows = _rows(1)
    responses = ["this is { not json", _tag_response(["s:1"], ["T1059.001"], 0.85)]
    result = await tag_untagged_rows(
        rows, index=_index(), agent=_agent(responses, fallbacks=["fake-fallback"])
    )
    assert result["mappings_by_ref"]["s:1"][0]["technique_id"] == "T1059.001"
    assert result["models_used"] == ["fake-fallback"]


async def test_invalid_and_revoked_ai_ids_handled():
    rows = _rows(1)
    responses = [_tag_response(["s:1"], ["T1998", "T4242", "banana", "T1999"], 0.9)]
    result = await tag_untagged_rows(rows, index=_index(), agent=_agent(responses))
    assert result["mappings_by_ref"]["s:1"] == [
        {"technique_id": "T1112", "source": "ai", "confidence": 0.9, "rationale": "r"}
    ]
    assert any("3 invalid or deprecated" in a for a in result["assumptions"])
    assert any("1 AI-suggested" in a and "restructured" in a for a in result["assumptions"])


async def test_low_confidence_mapping_stays_unmapped():
    rows = _rows(1)
    responses = [_tag_response(["s:1"], ["T1059.001"], 0.3)]
    result = await tag_untagged_rows(rows, index=_index(), agent=_agent(responses))
    assert result["mappings_by_ref"] == {}
    assert any("confidence floor" in a for a in result["assumptions"])


# ---------------------------------------------------------------------------
# extraction mode
# ---------------------------------------------------------------------------


async def test_extraction_happy_path():
    response = json.dumps({
        "use_cases": [
            {"name": "PS Encoded", "description": "d1", "technique_ids": ["T1059.001"], "confidence": 0.8},
            {"name": "", "description": "ignored", "technique_ids": [], "confidence": 0.9},
            {"name": "Registry watch", "description": "d2", "technique_ids": [], "confidence": 0.9},
        ],
        "overall_confidence": 0.8,
    })
    result = await extract_use_cases_from_text(
        "some pdf text", index=_index(), agent=_agent([response])
    )
    assert result["chunks_total"] == 1 and result["chunks_failed"] == 0
    assert [r["row_ref"] for r in result["rows"]] == ["doc:1:1", "doc:1:3"]
    assert result["rows"][0]["mapping_status"] == "ai_tagged"
    assert result["rows"][0]["mappings"][0]["technique_id"] == "T1059.001"
    assert result["rows"][1]["mapping_status"] == "unmapped"
    assert any("AI-extracted" in a for a in result["assumptions"])


# ---------------------------------------------------------------------------
# narrative
# ---------------------------------------------------------------------------

_COMPUTED = {
    "overall": {"strict_pct": 25.0, "covered": 1, "applicable": 4,
                "partial": 1, "not_covered": 2, "not_applicable": 1},
    "top_gaps": [
        {"technique_id": "T1112", "name": "Modify Registry", "state": "not_covered",
         "tier": 2, "feasibility": "short", "via": "Sysmon",
         "hint": "telemetry already onboarded (Sysmon covers registry) — build the detection now"},
    ],
    "roadmap_counts": {"short": 1, "mid": 0, "long": 1},
}


async def test_narrative_ai_path():
    response = json.dumps({
        "executive_summary": "Coverage is 25.0%.",
        "gap_recommendations": {"T1112": "Build a Sysmon registry detection."},
        "roadmap_prose": {"short": "s", "mid": "m", "long": "l"},
    })
    result = await generate_narrative(_COMPUTED, agent=_agent([response], cls=MitreNarrativeAgent))
    assert result["generated_by"] == "ai"
    assert result["model_used"] == "fake-primary"
    assert result["narrative"]["gap_recommendations"]["T1112"].startswith("Build")


async def test_narrative_degrades_to_template():
    result = await generate_narrative(
        _COMPUTED,
        agent=_agent([RuntimeError("down"), RuntimeError("down")], cls=MitreNarrativeAgent),
    )
    assert result["generated_by"] == "template"
    narrative = result["narrative"]
    assert "25.0%" in narrative["executive_summary"]  # numbers verbatim
    assert "T1112" in narrative["gap_recommendations"]
    assert set(narrative["roadmap_prose"]) == {"short", "mid", "long"}


def test_template_narrative_uses_only_given_numbers():
    narrative = build_template_narrative(_COMPUTED)
    assert "1 of 4" in narrative["executive_summary"]
    assert "Modify Registry (T1112)" in narrative["executive_summary"]


# ---------------------------------------------------------------------------
# pipeline: all tagging batches fail + zero customer tags -> failed status
# ---------------------------------------------------------------------------


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c


_XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _untagged_dump() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.append(["Use Case Name", "MITRE Technique(s)", "Status"])
    ws.append(["Anomaly rule A", "", "Enabled"])
    ws.append(["Anomaly rule B", "", "Enabled"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_all_batches_fail_zero_customer_tags_fails_assessment(
    client, db_session, monkeypatch
):
    async def all_fail(rows, **kwargs):
        return {
            "mappings_by_ref": {}, "assumptions": ["AI tagging unavailable (stub)"],
            "models_used": [], "batches_total": 1, "batches_failed": 1,
        }

    monkeypatch.setattr(agents, "tag_untagged_rows", all_fail)

    org = Organization(org_id=uuid.uuid4(), name=f"org-{uuid.uuid4()}")
    user = User(user_id=uuid.uuid4(), org_id=org.org_id, email=f"{uuid.uuid4()}@x.com")
    db_session.add_all([org, user])
    await db_session.commit()
    token, _ = create_access_token(
        user_id=user.user_id, email=user.email, org_id=org.org_id, role="admin"
    )
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/mitre/assessments",
        headers=headers,
        files={"use_cases": ("rules.xlsx", _untagged_dump(), _XLSX_MIME)},
    )
    assert created.status_code == 201, created.text
    aid = created.json()["assessment_id"]

    run = await client.post(f"/api/v1/mitre/assessments/{aid}/run", headers=headers)
    assert run.status_code == 202
    for _ in range(150):
        body = (await client.get(f"/api/v1/mitre/assessments/{aid}", headers=headers)).json()
        if body["status"] in ("completed", "failed"):
            break
        await asyncio.sleep(0.1)
    assert body["status"] == "failed"
    assert "AI tagging is temporarily unavailable" in body["error_message"]


# ---------------------------------------------------------------------------
# extraction budgets (2026-08-01 adversarial review, blocking finding #3)
# ---------------------------------------------------------------------------


async def test_extraction_row_cap(monkeypatch):
    monkeypatch.setattr(agents, "MAX_USE_CASE_ROWS", 3)
    response = json.dumps({
        "use_cases": [
            {"name": f"rule {i}", "description": "d", "technique_ids": [], "confidence": 0.9}
            for i in range(6)
        ],
    })
    result = await extract_use_cases_from_text(
        "some pdf text", index=_index(), agent=_agent([response])
    )
    assert len(result["rows"]) == 3
    assert any("stopped at the" in a for a in result["assumptions"])


async def test_extraction_chunk_cap(monkeypatch):
    monkeypatch.setattr(agents, "MAX_EXTRACTION_CHUNKS", 2)
    empty = json.dumps({"use_cases": []})
    long_text = ("line of rule text\n" * 600) * 3  # > 2 chunks at 9000 chars
    result = await extract_use_cases_from_text(
        long_text, index=_index(), agent=_agent([empty, empty])
    )
    assert result["chunks_total"] == 2
    assert any("first" in a and "sections" in a for a in result["assumptions"])
