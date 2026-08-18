"""2026-08-18 (user requirement): client-facing report text must read
human-typed, and cited data must be real. Two enforcement points:

1. Ban the common AI-tell phrases across report templates, curated data
   files, and the report/narrative modules. Python comment lines and raw
   regex-fragment lines (r"...") are stripped before matching — the banned
   list itself lives in agents.py as a regex.
2. The curated top-attacker-techniques file must name its source/year and
   every ID must resolve against the pinned ATT&CK dataset — the report
   only ever cites real published data.
"""

import re
from pathlib import Path

import pytest

_MITRE = Path(__file__).resolve().parents[1] / "app" / "mitre"

_BANNED = re.compile(
    r"\bleverag\w*\b|\bholistic\b|\bseamless\w*\b|\butiliz\w*\b"
    r"|\bfurthermore\b|\bmoreover\b|\bdelve\b|\bcutting-edge\b"
    r"|\bstate-of-the-art\b|\bbest-in-class\b|it is important to note"
    r"|in today'?s\b|overall security posture",
    re.IGNORECASE,
)

_FILES = (
    sorted((_MITRE / "templates").iterdir())
    + [
        _MITRE / "data" / name
        for name in (
            "technique_plain_language.json",
            "tactic_lines.json",
            "telemetry_fields.json",
            "top_attacker_techniques.json",
        )
    ]
    + [
        _MITRE / name
        for name in (
            "report.py",
            "report_xlsx.py",
            "report_pptx.py",
            "plain_language.py",
            "agents.py",
        )
    ]
)


@pytest.mark.parametrize("path", _FILES, ids=lambda p: p.name)
def test_no_ai_tell_phrases(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".py":
        text = "\n".join(
            line
            for line in text.splitlines()
            if not line.lstrip().startswith(("#", 'r"', "r'"))
        )
    hits = sorted({m.group(0).lower() for m in _BANNED.finditer(text)})
    assert not hits, f"{path.name} contains AI-tell wording: {hits}"


def test_top_attacker_techniques_file_is_sourced_and_valid():
    from app.mitre import attack_data

    cfg = attack_data.load_top_attacker_techniques()
    assert cfg.get("source") and cfg.get("year") and cfg.get("url")
    assert len(cfg["techniques"]) == 10
    seen_ranks = set()
    for entry in cfg["techniques"]:
        canonical, status = attack_data.DEFAULT.resolve(entry["id"])
        assert status in ("ok", "remapped"), (entry["id"], status)
        seen_ranks.add(entry["rank"])
    assert seen_ranks == set(range(1, 11))
