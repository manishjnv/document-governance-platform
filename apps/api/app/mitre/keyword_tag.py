"""Deterministic keyword/alias tagging pre-pass (Phase 6, coding-over-AI).

Runs between tag-validation and AI tagging: rows this module confidently
maps skip the LLM entirely; only the residue goes to
agents.tag_untagged_rows. Pure — no AI, no DB.

Two HIGH-PRECISION signal classes only (precision beats coverage: a rule
left for the AI is fine, a mis-mapped rule inflating coverage % is not):

1. Exact ATT&CK technique / sub-technique names appearing as a whole
   phrase (word-boundary, case-insensitive) in the rule text. Precision
   guards (2026-08-02 adversarial review, blocking finding V1):
   - names shorter than _MIN_NAME_LEN normalized chars skipped ("At");
   - single-word names skipped — MITRE names like "Credentials" or
     "Databases" are generic category labels that fire on benign rule
     text; distinctive single words (mimikatz, kerberoasting) belong in
     the curated alias file instead;
   - techniques living only in pre-compromise tactics (Reconnaissance
     TA0043 / Resource Development TA0042) skipped — a SIEM detection
     rule cannot observe them, and their names ("DNS Server", "Email
     Accounts") collide with routine ops-rule wording;
   - names carried by more than one technique ID across the three
     domains (e.g. "Phishing" = enterprise T1566 + mobile T1660) are
     dropped as ambiguous — the dump doesn't say which matrix it means.
2. A curated tool/command -> technique alias map
   (data/keyword_aliases.json), matched literally against the raw
   lowercased text so punctuation stays significant: "at.exe" never
   fires inside "look at exe files", "-enc" never inside
   "base64-encoded".

Every emitted ID passes attack_data resolve() (revoked remap, unknown/
deprecated drop). Matches get a fixed confidence >= the covered
threshold so they count as coverage, and a rationale naming exactly what
matched.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

from .attack_data import DEFAULT

# Fixed confidence for deterministic matches — above the 0.7 default
# covered threshold (an org that raises the threshold past this is asking
# for near-certainty; keyword matches then count as partial, which is fair).
KEYWORD_CONFIDENCE = 0.9
_MIN_NAME_LEN = 6  # normalized chars; kills "At"/"VNC"/"SSH"-class noise
# Pre-compromise tactics: not observable by SIEM detection rules; their
# technique names are category labels, not identifying phrases.
_PRE_COMPROMISE_TACTICS = {"TA0042", "TA0043"}
# Per-field scan cap: a keyword/alias match doesn't need 32KB of context,
# and an uncapped logic cell made a 5k-row dump cost ~50 min of worker
# thread (adversarial review, blocking finding V2). Mirrors ingest's
# 2000-char description cap.
_FIELD_CAP = 2000

_ALIAS_PATH = Path(__file__).resolve().parent / "data" / "keyword_aliases.json"


def _norm(value) -> str:
    """ingest.py-style normalization: lowercase, punctuation -> space."""
    text = re.sub(r"[^a-z0-9 ]", " ", str(value or "").lower())
    return re.sub(r"\s+", " ", text).strip()


def _raw(value) -> str:
    """Lowercase + collapse whitespace, KEEP punctuation (alias matching)."""
    return re.sub(r"\s+", " ", str(value or "").lower()).strip()


def _boundary_re(literal: str) -> re.Pattern:
    """Whole-token match: no [a-z0-9] on either side. The left boundary also
    rejects '.', so "asp.net user /add" / "base64-enc..." can't fire
    mid-token; the right side allows '.' so "mimikatz.exe" still matches."""
    return re.compile(rf"(?<![a-z0-9.]){re.escape(literal)}(?![a-z0-9])")


@lru_cache(maxsize=1)
def _load_aliases() -> tuple:
    data = json.loads(_ALIAS_PATH.read_text(encoding="utf-8"))
    return tuple((a["pattern"], a["technique_id"]) for a in data["aliases"])


@lru_cache(maxsize=8)  # keyed by AttackIndex identity; tests inject their own
def _matchers(index):
    """(name_matchers, alias_matchers) — each [(compiled_re, technique_id,
    rationale)]. Name matchers run on normalized text, alias matchers on raw
    lowercased text."""
    by_name: dict = {}
    for tech in index.techniques():
        if tech.get("deprecated") or tech.get("revoked"):
            continue
        tactics = set(tech.get("tactics") or [])
        if tactics and tactics <= _PRE_COMPROMISE_TACTICS:
            continue
        name = _norm(tech.get("name"))
        if len(name) < _MIN_NAME_LEN or " " not in name:
            continue
        by_name.setdefault(name, set()).add(tech["id"])
    name_matchers = [
        (
            _boundary_re(name),
            next(iter(ids)),
            f"rule text contains the ATT&CK technique name '{name}'",
        )
        for name, ids in by_name.items()
        if len(ids) == 1  # ambiguous cross-domain names are dropped
    ]
    alias_matchers = [
        (
            _boundary_re(_raw(pattern)),
            technique_id,
            f"rule text contains the known attacker tool/command '{pattern}'",
        )
        for pattern, technique_id in _load_aliases()
    ]
    return name_matchers, alias_matchers


def keyword_tag_rows(rows, index=None) -> dict:
    """Deterministically map untagged rules to techniques.

    rows: [{"row_ref", "name", "description", "logic"}] — customer-tagged
    rows must never be passed in (customer truth wins).
    Returns {row_ref: [mapping, ...]} for rows with >= 1 confident match;
    unmatched rows are simply absent. Mapping: {technique_id,
    source: "keyword", confidence, rationale}.

    CPU-bound (hundreds of regexes per row) — callers on the event loop
    should run it via asyncio.to_thread.
    ponytail: per-pattern regex loop; fold into one alternation regex if
    profiling ever shows pain on 5k-row dumps.
    """
    index = index if index is not None else DEFAULT
    name_matchers, alias_matchers = _matchers(index)

    out = {}
    for row in rows:
        fields = [
            str(row.get(f) or "")[:_FIELD_CAP]
            for f in ("name", "description", "logic")
        ]
        # Join with a non-alphanumeric separator so a field ending "net"
        # and the next starting "user" can't fake a "net user" match.
        norm_text = " | ".join(_norm(f) for f in fields)
        raw_text = " | ".join(_raw(f) for f in fields)

        mappings, seen = [], set()

        def _emit(technique_id, rationale):
            canonical, status = index.resolve(technique_id)
            if status in ("malformed", "unknown", "deprecated"):
                return
            if canonical in seen:
                return
            seen.add(canonical)
            mappings.append(
                {
                    "technique_id": canonical,
                    "source": "keyword",
                    "confidence": KEYWORD_CONFIDENCE,
                    "rationale": rationale,
                }
            )

        for pattern, technique_id, rationale in name_matchers:
            if pattern.search(norm_text):
                _emit(technique_id, rationale)
        for pattern, technique_id, rationale in alias_matchers:
            if pattern.search(raw_text):
                _emit(technique_id, rationale)

        if mappings:
            out[row["row_ref"]] = mappings
    return out
