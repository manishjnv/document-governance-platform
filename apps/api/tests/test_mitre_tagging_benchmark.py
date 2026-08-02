"""Plan phase A2 — keyword-layer regression pin against Sigma-derived rules.

Pure, no network, no LLM: loads a small fixture of REAL Sigma detection
rules (title/description/detection-logic text, converted to the module's
use-case row shape) with their own ATT&CK tags kept as ground truth, and
asserts the deterministic keyword pre-pass doesn't regress below its
measured precision. Regenerate the fixture with:

    python scripts/benchmark_tagging.py --dump-fixture tests/fixtures/sigma_keyword_bench.json --fixture-n 25

This is a REGRESSION PIN, not the benchmark itself — the benchmark
(scripts/benchmark_tagging.py) is the dev-run-only tool that measures
precision/recall/F1 at scale against a fresh Sigma clone.

Ground-truth caveat: Sigma rules often carry only their PRIMARY technique
tag, not every technique the logic could arguably support, so this
fixture's "false positives" include some plausibly-correct extra matches
Sigma's authors simply didn't tag — precision here is a conservative
floor, not the pre-pass's true real-world precision.
"""

import json
from pathlib import Path

from app.mitre.keyword_tag import keyword_tag_rows

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "sigma_keyword_bench.json"

# Measured 2026-08-03 on the checked-in fixture: precision 0.267 (tp=4 fp=11
# fn=32). Floor set slightly below with room for keyword_aliases.json growth
# (plan phase A5) without breaking this pin — a real regression is a drop
# below this, not the exact value moving.
PRECISION_FLOOR = 0.25


def _load_rows():
    data = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return data["rows"]


def test_fixture_exists_and_is_shaped_correctly():
    rows = _load_rows()
    assert 20 <= len(rows) <= 30
    for row in rows:
        assert row["row_ref"] and row["name"]
        assert isinstance(row["gt_technique_ids"], list) and row["gt_technique_ids"]


def test_keyword_layer_precision_does_not_regress():
    rows = _load_rows()
    input_rows = [
        {"row_ref": r["row_ref"], "name": r["name"], "description": r["description"], "logic": r["logic"]}
        for r in rows
    ]
    predictions = keyword_tag_rows(input_rows)

    tp = fp = 0
    for row in rows:
        gt = set(row["gt_technique_ids"])
        pred = {m["technique_id"] for m in predictions.get(row["row_ref"], [])}
        tp += len(pred & gt)
        fp += len(pred - gt)

    assert tp + fp > 0, "keyword layer produced zero predictions on the fixture"
    precision = tp / (tp + fp)
    assert precision >= PRECISION_FLOOR, (
        f"keyword-layer precision {precision:.3f} on the pinned Sigma fixture "
        f"dropped below the floor {PRECISION_FLOOR} (tp={tp} fp={fp})"
    )
