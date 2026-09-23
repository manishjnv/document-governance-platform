"""Pure ingest for VVAH findings.json / SARIF 2.1.0 reports.

No DB access, no LLM calls — everything here is deterministic parsing +
normalization into the `code_reviews.report` JSONB shape documented in
docs/planning/CODE_REVIEW_MODULE_REFERENCE.md section 3. Every finding text
field is attacker-controlled (it flowed through the scanned repo and,
upstream, an LLM) so every access here is defensive: `.get()` with type
checks, caps on length/count, never a raise from a single bad entry.
"""

from __future__ import annotations

import io
import json
import re
import stat
import struct
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Optional

MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_FINDINGS = 2000
# 50 was the old kit-zip-only cap; a real scan-run upload (finding folders +
# hundreds of surefire XML reports) needs much more room.
MAX_ZIP_ENTRIES = 2000
MAX_ZIP_MEMBER_BYTES = MAX_REPORT_BYTES
MAX_ZIP_TOTAL_BYTES = 30 * 1024 * 1024
MAX_XML_FILES = 1000
MAX_TESTCASES = 50000  # JUnit cases kept for fix matching; beyond this the counts still add up
SEVERITIES = ("critical", "high", "medium", "low", "info")

_SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}
_TEXT_CAP = 20000
_TITLE_CAP = 500
_SUMMARY_CAP = 4000
_MAX_SARIF_DESCRIPTION = 6 * _TEXT_CAP  # whole sectioned blob; each section is then capped at _TEXT_CAP
_SARIF_LEVEL_SEVERITY = {"error": "high", "warning": "medium", "note": "low"}
_METRIC_KEYS = (
    "duration_sec",
    "total_files_in_scope",
    "analyzed_files_unique",
    "loc_scanned_by_language",
    "true_positive_count",
    "false_positive_count",
    "total_tokens",
)


class IngestError(ValueError):
    """Raised with a user-facing message on unparseable/unrecognized input."""


# --------------------------------------------------------------------------
# Defensive coercion helpers
# --------------------------------------------------------------------------


def _s(value: Any, cap: Optional[int] = None) -> str:
    if value is None:
        return ""
    text = value if isinstance(value, str) else str(value)
    return text[:cap] if cap else text


def _opt_s(value: Any, cap: Optional[int] = None) -> Optional[str]:
    if value is None:
        return None
    text = value if isinstance(value, str) else str(value)
    text = text[:cap] if cap else text
    return text or None


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _opt_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence(value: Any) -> float:
    f = _float_or_none(value)
    if f is None:
        return 0.0
    return max(0.0, min(1.0, f))


def _normalize_severity(raw: Any, assumptions: list) -> str:
    s = _s(raw).strip().lower()
    if s in _SEVERITY_RANK:
        return s
    assumptions.append(f"unknown severity {raw!r} normalized to medium")
    return "medium"


def _dict_or_empty(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: Any) -> list:
    return value if isinstance(value, list) else []


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def parse_report(raw: bytes) -> dict:
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise IngestError("not valid JSON")
    if not isinstance(obj, dict):
        raise IngestError("not valid JSON")

    if "findings" in obj and "repo_root" in obj:
        return _from_findings_json(obj)
    if "runs" in obj and ("$schema" in obj or "version" in obj):
        return _from_sarif(obj)
    raise IngestError(
        "Unrecognized file: expected a vvaharness findings.json or a SARIF 2.1.0 report"
    )


def parse_manifest(raw: bytes) -> dict:
    try:
        obj = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise IngestError("not valid JSON")
    if not isinstance(obj, dict):
        raise IngestError("not valid JSON")

    models: dict = {}
    for role, info in _dict_or_empty(obj.get("models")).items():
        if not isinstance(info, dict):
            continue
        models[str(role)] = {
            "id": _opt_s(info.get("id")),
            "provider": _opt_s(info.get("provider")),
        }

    totals = _dict_or_empty(obj.get("totals"))
    total_cost = totals.get("cost")
    if total_cost is None:
        total_cost = totals.get("cost_usd")

    return {
        "target_git_sha": _opt_s(obj.get("target_git_sha")),
        "tool_version": _opt_s(obj.get("version")),
        "duration_sec": _float_or_none(obj.get("duration_sec")),
        "models": models,
        "total_cost_usd": _float_or_none(total_cost),
        "total_tokens": _opt_int(totals.get("total_tokens")),
    }


def _unsafe_zip_name(name: str) -> bool:
    if not name or "\x00" in name:
        return True
    if name.startswith("/") or name.startswith("\\"):
        return True
    if ":" in name:  # drive letter, e.g. "C:\..."
        return True
    parts = name.replace("\\", "/").split("/")
    return any(p == ".." for p in parts)


def _is_junk_member(name: str) -> bool:
    """macOS zip junk: resource-fork folders/files that carry no scan data."""
    norm = name.replace("\\", "/")
    if "__MACOSX/" in norm:
        return True
    basename = norm.rsplit("/", 1)[-1]
    return basename == ".DS_Store" or basename.startswith("._")


def _open_zip_candidates(raw: bytes) -> tuple[zipfile.ZipFile, list[tuple[int, str, zipfile.ZipInfo]]]:
    """Open + guard a zip and return its safe, non-junk members as
    (depth, basename, info). Attacker-controlled input: macOS junk dropped
    before anything is counted, bounded entry count, bounded per-member and
    total declared sizes checked BEFORE reading (zip-bomb guard),
    path-traversal rejection, symlinks ignored rather than followed. Shared
    by unpack_scan_zip and read_run_extras so these guards live once.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
        members = [info for info in zf.infolist() if not info.is_dir()]
    except (zipfile.BadZipFile, struct.error, OverflowError, ValueError):
        raise IngestError("Not a valid zip file")

    members = [info for info in members if not _is_junk_member(info.filename)]
    if len(members) > MAX_ZIP_ENTRIES:
        raise IngestError(f"Zip has too many entries (max {MAX_ZIP_ENTRIES})")

    total_declared = 0
    candidates = []  # (depth, basename, info)
    for info in members:
        name = info.filename
        if _unsafe_zip_name(name):
            raise IngestError(f"Zip contains an unsafe path: {name!r}")
        if stat.S_ISLNK(info.external_attr >> 16):  # unix mode bits live in the high word
            continue
        if info.file_size > MAX_ZIP_MEMBER_BYTES:
            raise IngestError(
                f"Zip member too large: {name} (max {MAX_ZIP_MEMBER_BYTES / (1024 * 1024)}MB)"
            )
        total_declared += info.file_size
        if total_declared > MAX_ZIP_TOTAL_BYTES:
            raise IngestError(
                f"Zip too large uncompressed (max {MAX_ZIP_TOTAL_BYTES / (1024 * 1024)}MB)"
            )
        basename = name.replace("\\", "/").rsplit("/", 1)[-1]
        depth = name.count("/")
        candidates.append((depth, basename, info))

    return zf, candidates


def _read_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
    # Stream with a hard byte cap so a lying header can't inflate past the
    # limit in memory (belt and braces over the declared-size checks above).
    chunks = []
    got = 0
    try:
        with zf.open(info) as fh:
            while True:
                chunk = fh.read(65536)
                if not chunk:
                    break
                got += len(chunk)
                if got > MAX_ZIP_MEMBER_BYTES:
                    raise IngestError(f"Zip member too large: {info.filename}")
                chunks.append(chunk)
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError, ValueError) as exc:
        # corrupt CRC, encrypted member, unsupported compression -> 422, never 500
        raise IngestError(f"Zip member could not be read: {info.filename}") from exc
    data = b"".join(chunks)
    if len(data) != info.file_size:
        raise IngestError(f"Zip member size mismatch: {info.filename}")
    return data


def _report_candidate(candidates):
    """Pick the best findings.json/.sarif candidate (findings.json ranked
    over .sarif, shallowest first) and every distinct top-level path segment
    ("" = zip root) that holds one — the latter is the multi-run check."""
    report_info = None
    report_kind_rank = None  # 0 = findings.json, 1 = .sarif
    top_segments = set()
    for depth, basename, info in candidates:
        if basename == "findings.json":
            rank = 0
        elif basename.lower().endswith(".sarif"):
            rank = 1
        else:
            continue
        top = info.filename.replace("\\", "/").split("/", 1)[0] if depth else ""
        top_segments.add(top)
        if report_kind_rank is None or rank < report_kind_rank or (
            rank == report_kind_rank and depth < report_info[0]
        ):
            report_kind_rank = rank
            report_info = (depth, basename, info)
    return report_info, top_segments


def _report_top_segment(candidates) -> Optional[str]:
    report_info, _ = _report_candidate(candidates)
    if report_info is None:
        return None
    depth, _basename, info = report_info
    name = info.filename.replace("\\", "/")
    return name.split("/", 1)[0] if depth else ""


def unpack_scan_zip(raw: bytes) -> tuple[bytes, str, Optional[bytes], Optional[str]]:
    """Extract findings/sarif report + optional manifest from a consultant
    scan-kit or full scan-run zip. See _open_zip_candidates for the input
    guards. Rejects a zip whose report candidates sit under more than one
    top-level run folder — one run per upload.
    """
    zf, candidates = _open_zip_candidates(raw)

    report_info, top_segments = _report_candidate(candidates)
    if report_info is None:
        raise IngestError("Zip contains no findings.json or .sarif")
    if len(top_segments) > 1:
        labels = sorted(seg or "(zip root)" for seg in top_segments)
        raise IngestError(
            f"This zip holds {len(top_segments)} scan runs ({', '.join(labels)}). "
            "Zip one run folder and upload it on its own."
        )

    manifest_info = None
    for depth, basename, info in candidates:
        if basename.startswith("run_manifest") and basename.lower().endswith(".json"):
            if manifest_info is None or depth < manifest_info[0]:
                manifest_info = (depth, basename, info)

    report_bytes = _read_member(zf, report_info[2])
    report_name = report_info[1]
    manifest_bytes = None
    manifest_name = None
    if manifest_info is not None:
        manifest_bytes = _read_member(zf, manifest_info[2])
        manifest_name = manifest_info[1]

    return report_bytes, report_name, manifest_bytes, manifest_name


# --------------------------------------------------------------------------
# findings.json (VVAH FinalReport)
# --------------------------------------------------------------------------


def _from_findings_json(obj: dict) -> dict:
    assumptions: list = []
    raw_list = _list_or_empty(obj.get("findings"))

    raw_findings = []
    for pos, entry in enumerate(raw_list):
        if not isinstance(entry, dict):
            assumptions.append("a malformed finding entry was skipped")
            continue
        inner = entry.get("finding")
        if not isinstance(inner, dict):
            inner = entry
        try:
            mapped = _map_findings_json_entry(entry, inner, assumptions)
        except Exception:  # noqa: BLE001 — never let one bad entry crash ingest
            assumptions.append("a malformed finding entry was skipped")
            continue
        mapped["_pos"] = pos  # original VVAH position; chain steps refer to it
        raw_findings.append(mapped)

    dropped_list = obj.get("dropped")
    dropped_count = (
        len(dropped_list) if isinstance(dropped_list, list) else _int(obj.get("dropped_count"), 0)
    )

    return _finalize(
        source_format="findings",
        tool="vvaharness",
        tool_version=_opt_s(obj.get("tool_version")),
        repo_name=_opt_s(obj.get("repo_name")),
        git_sha=_opt_s(obj.get("git_sha")),
        summary_text=_s(obj.get("summary"), _SUMMARY_CAP),
        degraded=bool(obj.get("degraded", False)),
        degraded_reason=_s(obj.get("degraded_reason"), _TEXT_CAP),
        assumptions=assumptions,
        raw_findings=raw_findings,
        chains=_map_chains(obj.get("chains")),
        dropped_count=dropped_count,
        raw_findings_count=_int(obj.get("raw_findings_count"), len(raw_list)),
        metrics=_map_metrics(obj.get("metrics")),
    )


def _map_findings_json_entry(entry: dict, inner: dict, assumptions: list) -> dict:
    severity_raw = entry.get("severity")
    if severity_raw is None:
        severity_raw = inner.get("severity")

    exploit_notes = entry.get("exploitability_notes")
    if exploit_notes is None:
        exploit_notes = inner.get("exploitability_notes")

    verdict = inner.get("verdict")
    if verdict not in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
        verdict = None

    preconditions_raw = inner.get("preconditions")
    preconditions = (
        [_s(p, _TEXT_CAP) for p in preconditions_raw if isinstance(p, (str, int, float))]
        if isinstance(preconditions_raw, list)
        else []
    )

    return {
        "idx": 0,
        "title": _s(inner.get("title"), _TITLE_CAP),
        "severity": _normalize_severity(severity_raw, assumptions),
        "vuln_class": _opt_s(inner.get("vuln_class")),
        # real VVAH 1.3.0 output leaves vuln_class_label null -> fall back to the class id
        "vuln_class_label": _opt_s(inner.get("vuln_class_label")) or _opt_s(inner.get("vuln_class")),
        "cwe": _opt_s(inner.get("cwe")),
        "cvss_score": _float_or_none(inner.get("cvss_score")),
        "cvss_vector": _opt_s(inner.get("cvss_vector")),
        "cvss_rating": _opt_s(inner.get("cvss_rating")),
        "file": _s(inner.get("file"), _TITLE_CAP),
        "line_start": _int(inner.get("line_start"), 0),
        "line_end": _int(inner.get("line_end"), 0),
        "confidence": _confidence(inner.get("confidence")),
        "votes": _int(inner.get("votes"), 1),
        "verdict": verdict,
        "verdict_confidence": _opt_int(inner.get("verdict_confidence")),
        "verdict_reason": _s(inner.get("verdict_reason"), _TEXT_CAP),
        "description": _s(inner.get("description"), _TEXT_CAP),
        "impact": _s(inner.get("impact"), _TEXT_CAP),
        "exploit_scenario": _s(inner.get("exploit_scenario"), _TEXT_CAP),
        "preconditions": preconditions,
        "recommendation": _s(inner.get("recommendation"), _TEXT_CAP),
        "code_snippet": _s(inner.get("code_snippet"), _TEXT_CAP),
        "exploitability_notes": _s(exploit_notes, _TEXT_CAP),
        "verifier_reasoning": _s(inner.get("verifier_reasoning"), _TEXT_CAP),
        "offensive_priority": _opt_s(inner.get("offensive_priority")),
        "offensive_reason": _s(inner.get("offensive_reason"), _TEXT_CAP),
        "source_ref": _opt_s(inner.get("source_ref")),
        "sink_ref": _opt_s(inner.get("sink_ref")),
        "duplicates": _map_duplicates(inner.get("duplicates")),
    }


def _map_duplicates(value: Any) -> list:
    out = []
    for d in _list_or_empty(value):
        if not isinstance(d, dict):
            continue
        out.append(
            {
                "file": _s(d.get("file")),
                "line_start": _int(d.get("line_start"), 0),
                "line_end": _int(d.get("line_end"), 0),
            }
        )
    return out


def _map_chains(value: Any) -> list:
    out = []
    for c in _list_or_empty(value):
        if not isinstance(c, dict):
            continue
        steps_raw = c.get("steps")
        steps = [_int(s) for s in steps_raw] if isinstance(steps_raw, list) else []
        out.append(
            {
                "title": _s(c.get("title"), _TITLE_CAP),
                "steps": steps,
                "severity": _s(c.get("severity")).strip().lower() or "medium",
                "narrative": _s(c.get("narrative"), _TEXT_CAP),
            }
        )
    return out


def _map_metrics(value: Any) -> dict:
    metrics: dict = {k: None for k in _METRIC_KEYS}
    d = _dict_or_empty(value)
    if not d:
        return metrics
    metrics["duration_sec"] = _float_or_none(d.get("duration_sec"))
    for k in (
        "total_files_in_scope",
        "analyzed_files_unique",
        "true_positive_count",
        "false_positive_count",
        "total_tokens",
    ):
        metrics[k] = _opt_int(d.get(k))
    loc = d.get("loc_scanned_by_language")
    metrics["loc_scanned_by_language"] = (
        {str(k): _int(v) for k, v in loc.items()} if isinstance(loc, dict) else None
    )
    return metrics


# --------------------------------------------------------------------------
# SARIF 2.1.0
# --------------------------------------------------------------------------


def _from_sarif(obj: dict) -> dict:
    assumptions: list = []
    runs = _list_or_empty(obj.get("runs"))
    run = runs[0] if runs and isinstance(runs[0], dict) else {}
    driver = _dict_or_empty(_dict_or_empty(run.get("tool")).get("driver"))
    results = _list_or_empty(run.get("results"))

    raw_findings = []
    for result in results:
        if not isinstance(result, dict):
            assumptions.append("a malformed finding entry was skipped")
            continue
        try:
            raw_findings.append(_map_sarif_result(result, assumptions))
        except Exception:  # noqa: BLE001
            assumptions.append("a malformed finding entry was skipped")

    # Scan-health notes (Agentic SAST): skip the per-chunk "N non-fatal error(s)" noise.
    notes = []
    for inv in _list_or_empty(run.get("invocations")):
        for note in _list_or_empty(_dict_or_empty(inv).get("toolExecutionNotifications")):
            text = _s(_dict_or_empty(_dict_or_empty(note).get("message")).get("text"), _TITLE_CAP)
            if text and "non-fatal error" not in text:
                notes.append(text)

    return _finalize(
        source_format="sarif",
        tool=_opt_s(driver.get("name")) or "vvaharness",
        tool_version=_opt_s(driver.get("version")),
        repo_name=None,
        git_sha=None,
        summary_text="",
        degraded=_dict_or_empty(run.get("properties")).get("scanDegraded") is True,
        degraded_reason=_s(". ".join(notes[:10]), _TEXT_CAP),
        assumptions=assumptions,
        raw_findings=raw_findings,
        chains=[],
        dropped_count=0,
        raw_findings_count=len(results),
        metrics=_map_metrics(None),
    )


_SARIF_SECTIONS = {
    "description": "description",
    "impact": "impact",
    "exploit scenario": "exploit_scenario",
    "preconditions": "preconditions",
    "how to fix": "recommendation",
    "adversarial verification": "verifier_reasoning",
}


def _split_sarif_sections(text: str) -> dict:
    """Split '#### Heading' markdown into known fields; unknown headings end a
    section. Line-based (no regex over attacker text); text before the first
    known heading is dropped (it is dedup boilerplate). The first fenced code
    block becomes code_snippet and a '**Exploitability:**' line becomes
    exploitability, wherever they sit, so neither leaks into another field."""
    out: dict = {}
    key = None
    fence = None  # None = outside a block; list = collecting the first block; False = skipping later blocks
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            if fence is None and "code_snippet" not in out:
                fence = []
            elif isinstance(fence, list):
                out["code_snippet"] = fence
                fence = None
            else:
                fence = None if fence is False else False
            continue
        if fence is not None:
            if isinstance(fence, list):
                fence.append(line)
            continue
        if stripped.startswith("**Exploitability:**"):
            out["exploitability"] = [stripped[len("**Exploitability:**"):]]
            continue
        if stripped.startswith("#"):
            key = _SARIF_SECTIONS.get(stripped.lstrip("#").strip().lower())
            if key:
                out[key] = []
            continue
        if key:
            out[key].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def _parse_sarif_verdict(text: str) -> tuple:
    """'**Verdict:** TRUE_POSITIVE (confidence: 9/10) — reason' -> (verdict, confidence, reason)."""
    first = text.strip().split("\n", 1)[0].strip()
    if not first.startswith("**Verdict:**"):
        return None, None, ""
    rest = first[len("**Verdict:**"):].strip()
    word = rest.split(" ", 1)[0]
    verdict = word if word in ("TRUE_POSITIVE", "FALSE_POSITIVE") else None
    confidence = None
    if "(confidence:" in rest:
        confidence = _opt_int(rest.split("(confidence:", 1)[1].split("/", 1)[0].strip())
    reason = rest.split("—", 1)[1].strip() if "—" in rest else ""
    return verdict, confidence, reason


def _map_sarif_result(result: dict, assumptions: list) -> dict:
    props = _dict_or_empty(result.get("properties"))
    severity_raw = props.get("severity")
    if severity_raw is None:
        level = _s(result.get("level")).strip().lower()
        severity_raw = _SARIF_LEVEL_SEVERITY.get(level, "medium")

    message = _dict_or_empty(result.get("message"))
    locations = _list_or_empty(result.get("locations"))
    loc0 = locations[0] if locations and isinstance(locations[0], dict) else {}
    phys = _dict_or_empty(loc0.get("physicalLocation"))
    artifact = _dict_or_empty(phys.get("artifactLocation"))
    region = _dict_or_empty(phys.get("region"))

    duplicates = []
    for rel in _list_or_empty(result.get("relatedLocations")):
        if not isinstance(rel, dict):
            continue
        rphys = _dict_or_empty(rel.get("physicalLocation"))
        rartifact = _dict_or_empty(rphys.get("artifactLocation"))
        rregion = _dict_or_empty(rphys.get("region"))
        duplicates.append(
            {
                "file": _s(rartifact.get("uri")),
                "line_start": _int(rregion.get("startLine"), 0),
                "line_end": _int(rregion.get("endLine"), 0),
            }
        )

    rule_id = _opt_s(result.get("ruleId"))
    # Agentic SAST puts the narrative in properties.description as "#### <Heading>" sections.
    sections = _split_sarif_sections(_s(props.get("description"), _MAX_SARIF_DESCRIPTION))
    remediation = _dict_or_empty(result.get("remediation"))
    remediation_note = ""
    if remediation.get("remediationStatus"):
        remediation_note = (
            f"Remediation: {_s(remediation.get('remediationStatus'), 50)}. "
            f"{_s(remediation.get('remediationReason'))}"
        ).strip()
    notes = "\n\n".join(n for n in (sections.get("exploitability", ""), remediation_note) if n)
    verdict, verdict_confidence, verdict_reason = _parse_sarif_verdict(
        sections.get("verifier_reasoning", "")
    )
    preconditions = [
        line.lstrip("-*0123456789.) ").strip()
        for line in sections.get("preconditions", "").splitlines()
        if line.strip()
    ]
    title = _s(message.get("text"), _TITLE_CAP)
    if title.endswith("]") and " [CVSS " in title:  # CVSS has its own columns
        title = title.rsplit(" [CVSS ", 1)[0].rstrip()
    return {
        "idx": 0,
        "title": title,
        "severity": _normalize_severity(severity_raw, assumptions),
        "vuln_class": rule_id,
        "vuln_class_label": _opt_s(props.get("category")) or rule_id,
        "cwe": _opt_s(props.get("cwe")),
        "cvss_score": _float_or_none(props.get("cvssScore")),
        "cvss_vector": _opt_s(props.get("cvssVector")),
        "cvss_rating": _opt_s(props.get("cvssRating")),
        "file": _s(artifact.get("uri")),
        "line_start": _int(region.get("startLine"), 0),
        "line_end": _int(region.get("endLine"), 0),
        "confidence": _confidence(props.get("confidence")),
        "votes": 1,
        "verdict": verdict,
        "verdict_confidence": verdict_confidence,
        "verdict_reason": _s(verdict_reason, _TEXT_CAP),
        "description": _s(sections.get("description") or message.get("text"), _TEXT_CAP),
        "impact": _s(sections.get("impact"), _TEXT_CAP),
        "exploit_scenario": _s(sections.get("exploit_scenario"), _TEXT_CAP),
        "preconditions": [_s(p, _TEXT_CAP) for p in preconditions[:50]],
        "recommendation": _s(sections.get("recommendation"), _TEXT_CAP),
        "code_snippet": _s(sections.get("code_snippet"), _TEXT_CAP),
        "exploitability_notes": _s(notes, _TEXT_CAP),
        "verifier_reasoning": _s(sections.get("verifier_reasoning"), _TEXT_CAP),
        "offensive_priority": _opt_s(props.get("offensivePriority"), 20),
        "offensive_reason": _s(props.get("offensivePriorityReason"), _TEXT_CAP),
        "source_ref": None,
        "sink_ref": None,
        "duplicates": duplicates,
    }


# --------------------------------------------------------------------------
# Shared: sort/cap, counts, final assembly
# --------------------------------------------------------------------------


def _sort_key(f: dict):
    cvss = f["cvss_score"]
    cvss_key = (0, -cvss) if cvss is not None else (1, 0.0)
    return (
        _SEVERITY_RANK.get(f["severity"], len(SEVERITIES)),
        cvss_key,
        f["file"] or "",
        f["line_start"] or 0,
    )


def _build_counts(findings: list) -> dict:
    by_severity = {s: 0 for s in SEVERITIES}
    by_vuln_class: dict = {}
    by_file: dict = {}
    for f in findings:
        by_severity[f["severity"]] = by_severity.get(f["severity"], 0) + 1
        label = f["vuln_class_label"] or f["vuln_class"] or "unknown"
        by_vuln_class[label] = by_vuln_class.get(label, 0) + 1
        path = f["file"] or "unknown"
        by_file[path] = by_file.get(path, 0) + 1
    top_files = dict(sorted(by_file.items(), key=lambda kv: (-kv[1], kv[0]))[:20])
    return {
        "total": len(findings),
        "by_severity": by_severity,
        "by_vuln_class": by_vuln_class,
        "by_file": top_files,
    }


def _finalize(
    *,
    source_format: str,
    tool: str,
    tool_version: Optional[str],
    repo_name: Optional[str],
    git_sha: Optional[str],
    summary_text: str,
    degraded: bool,
    degraded_reason: str,
    assumptions: list,
    raw_findings: list,
    chains: list,
    dropped_count: int,
    raw_findings_count: int,
    metrics: dict,
) -> dict:
    findings = sorted(raw_findings, key=_sort_key)
    if len(findings) > MAX_FINDINGS:
        overflow = len(findings) - MAX_FINDINGS
        findings = findings[:MAX_FINDINGS]
        dropped_count += overflow
        assumptions.append(
            f"kept the first {MAX_FINDINGS} findings after sorting; {overflow} more were dropped"
        )
    pos_to_idx: dict = {}
    for i, f in enumerate(findings, start=1):
        f["idx"] = i
        if "_pos" in f:
            pos_to_idx[f.pop("_pos")] = i

    # Chain steps index VVAH's original findings order; we re-sorted and
    # renumbered, so remap them onto our display idx. ponytail: VVAH doesn't
    # document 0- vs 1-based steps — treat as 0-based only when a 0 appears;
    # unmappable steps are kept verbatim rather than dropped.
    if pos_to_idx and chains:
        all_steps = [s for c in chains for s in c["steps"]]
        offset = 0 if 0 in all_steps else 1
        for c in chains:
            c["steps"] = [pos_to_idx.get(s - offset, s) for s in c["steps"]]

    # dedupe repeated notes (e.g. one per unknown-severity finding), keep order
    assumptions = list(dict.fromkeys(assumptions))

    return {
        "source_format": source_format,
        "tool": tool,
        "tool_version": tool_version,
        "repo_name": repo_name,
        "git_sha": git_sha,
        "summary_text": summary_text,
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "assumptions": assumptions,
        "counts": _build_counts(findings),
        "findings": findings,
        "chains": chains,
        "dropped_count": dropped_count,
        "raw_findings_count": raw_findings_count,
        "metrics": metrics,
        "manifest": None,
    }


# --------------------------------------------------------------------------
# Scan-run extras (real VVAH/Agentic SAST run-folder uploads): triage.json,
# finding_case.json, diff.patch, report.md, JUnit XML, Maven console log.
# See docs/planning/CODE_REVIEW_MODULE_REFERENCE.md for the layout. Every
# key here is OPTIONAL and absent for a plain findings.json/.sarif/kit-zip
# upload — read_run_extras returns None and apply_run_extras is never
# called for those.
# --------------------------------------------------------------------------

_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
_MVN_SKIPPED_RE = re.compile(r"^\[INFO\]\s+(.+?)\s*\.{2,}\s*SKIPPED\s*$")
_HEALTH_DROP_PREFIXES = ("Non-fatal errors logged by stage", "Full error log")
_XML_DANGEROUS = (b"<!DOCTYPE", b"<!ENTITY")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _diff_patch_files(text: str) -> list:
    files = []
    for line in text.splitlines():
        if line.startswith("+++ b/"):
            f = line[len("+++ b/"):].strip()
            if f and f not in files:
                files.append(f)
    return [_s(f, 500) for f in files[:50]]


def _fix_status(triage: dict) -> str:
    if _s(triage.get("mode")).strip().lower() == "report-only":
        return "not_attempted"
    verdict = _s(triage.get("verdict")).strip()
    final_verdict = _s(triage.get("final_verdict")).strip().upper()
    if verdict == "Fixed" and final_verdict == "ACCEPT":
        return "fixed"
    if verdict == "Fixed":
        return "patch_rejected"
    if verdict == "Needs Review":
        return "needs_review"
    return "not_fixed"


def _java_stem_and_package(path: str) -> tuple:
    p = _s(path).replace("\\", "/")
    filename = p.rsplit("/", 1)[-1]
    stem = filename[:-5] if filename.endswith(".java") else filename
    marker = "src/main/java/"
    idx = p.find(marker)
    pkg_path = p[idx + len(marker):] if idx != -1 else p
    package = ".".join(pkg_path.split("/")[:-1])
    return stem, package


def _index_testcases(testcases: list) -> dict:
    """Index JUnit cases once by class name and package, so matching a fix's
    files is a dict lookup, not files x testcases per fix (a crafted run zip
    with many fix folders and a huge JUnit file was a CPU DoS)."""
    fail_by_last: dict = {}
    fail_by_pkg: dict = {}
    pkgs = set()
    for tc in testcases:
        classname = tc["classname"]
        last = classname.rsplit(".", 1)[-1] if "." in classname else classname
        cn_pkg = classname.rsplit(".", 1)[0] if "." in classname else ""
        pkgs.add(cn_pkg)
        if tc["failed"]:
            hit = (last, tc["name"], tc["message"])
            fail_by_last.setdefault(last, []).append(hit)
            fail_by_pkg.setdefault(cn_pkg, []).append(hit)
    return {"fail_by_last": fail_by_last, "fail_by_pkg": fail_by_pkg, "pkgs": pkgs}


def _compute_fix_tests(files: list, index: dict, junit_present: bool) -> tuple:
    """See CODE_REVIEW_MODULE_REFERENCE.md 'tests' matching rule: a failing
    testcase 'hits' a changed file by stem-derived name or by package."""
    hits = []  # (last_classname_segment, test_name, message), file order, no repeats
    any_passed = False
    for file_ in files:
        stem, package = _java_stem_and_package(file_)
        for key in (stem + "Test", stem + "Tests", "Test" + stem):
            hits.extend(h for h in index["fail_by_last"].get(key, ()) if h not in hits and len(hits) < 3)
        hits.extend(h for h in index["fail_by_pkg"].get(package, ()) if h not in hits and len(hits) < 3)
        if package in index["pkgs"]:
            any_passed = True
    if hits:
        parts = [f"{last}.{name} failed after this change" for last, name, _msg in hits[:3]]
        return "broke_tests", "; ".join(parts)
    if any_passed:
        return "passed", ""
    if junit_present:
        return "not_tested", ""
    return "no_test_results", ""


def _junit_testcase_info(tc_el) -> dict:
    failure_el = None
    for child in tc_el:
        if child.tag.rsplit("}", 1)[-1] in ("failure", "error"):
            failure_el = child
            break
    return {
        "classname": _s(tc_el.get("classname"), 500),
        "name": _s(tc_el.get("name"), 200),
        "failed": failure_el is not None,
        "message": _s(failure_el.get("message") if failure_el is not None else "", 300),
    }


def _parse_maven_log(text: str) -> dict:
    clean = _strip_ansi(text)
    build = "failure" if "BUILD FAILURE" in clean else ("success" if "BUILD SUCCESS" in clean else None)
    not_run = []
    for line in clean.splitlines():
        m = _MVN_SKIPPED_RE.match(line.strip())
        if m:
            name = m.group(1).strip()
            if name and name not in not_run:
                not_run.append(name)
    return {"build": build, "not_run_modules": not_run[:50]}


def _md_section(text: str, heading: str) -> str:
    marker = f"## {heading}"
    i = text.find(marker)
    if i == -1:
        return ""
    start = i + len(marker)
    j = text.find("\n## ", start)
    return text[start:j] if j != -1 else text[start:]


def _md_bullets(section: str) -> list:
    return [line.strip()[2:].strip() for line in section.splitlines() if line.strip().startswith("- ")]


def _clean_health_bullet(raw: str) -> str:
    s = raw.strip()
    changed = True
    while changed:
        changed = False
        for prefix in ("⚠️", "**", "- "):
            if s.startswith(prefix):
                s = s[len(prefix):].strip()
                changed = True
    return s.replace("**", "")


def _parse_report_md(text: str) -> dict:
    coverage_pct = files_in_scope = files_analyzed = chunks = duration_sec = None
    for bullet in _md_bullets(_md_section(text, "Scan Metrics")):
        if bullet.startswith("Coverage:"):
            coverage_pct = _float_or_none(bullet.split(":", 1)[1].strip().rstrip("%"))
        elif bullet.startswith("Files in scope:"):
            files_in_scope = _opt_int(bullet.split(":", 1)[1].strip())
        elif bullet.startswith("Files analyzed (unique):"):
            files_analyzed = _opt_int(bullet.split(":", 1)[1].strip())
        elif bullet.startswith("Duration (sec):"):
            duration_sec = _float_or_none(bullet.split(":", 1)[1].strip())
        elif bullet.startswith("Chunks:"):
            chunks = _opt_int(bullet.split(":", 1)[1].strip().split(" ", 1)[0])

    health = []
    for bullet in _md_bullets(_md_section(text, "Scan Health")):
        cleaned = _clean_health_bullet(bullet)
        if not cleaned or cleaned.startswith(_HEALTH_DROP_PREFIXES):
            continue
        health.append(_s(cleaned, 500))
        if len(health) >= 20:
            break

    return {
        "coverage_pct": coverage_pct,
        "files_in_scope": files_in_scope,
        "files_analyzed": files_analyzed,
        "chunks": chunks,
        "duration_sec": duration_sec,
        "health": health,
        "threat_model": _s(_md_section(text, "Threat Model").strip(), 8000),
    }


def read_run_extras(raw: bytes) -> Optional[dict]:
    """Best-effort read of the extra files that sit alongside a real scan-run
    upload (triage.json / finding_case.json / diff.patch / report.md / JUnit
    XML / Maven console log), scoped to the chosen report's top-level run
    folder. Never raises: a bad extra file is skipped with a note. Returns
    None when the zip carries none of these (plain findings.json/.sarif/kit
    uploads keep behaving exactly as before).
    """
    try:
        zf, candidates = _open_zip_candidates(raw)
        top = _report_top_segment(candidates)
    except IngestError:
        return None
    if top is None:
        return None
    prefix = f"{top}/" if top else ""

    notes: list = []
    cases: dict = {}
    report_md_text = None
    maven_text = None
    junit_suites: list = []
    xml_seen = 0

    for _depth, basename, info in candidates:
        name = info.filename.replace("\\", "/")
        if not name.startswith(prefix):
            continue
        rel = name[len(prefix):]
        if not rel:
            continue
        parts = rel.split("/")
        lower = basename.lower()
        try:
            if basename == "finding_case.json" and len(parts) >= 2:
                data = json.loads(_read_member(zf, info))
                if isinstance(data, dict):
                    cases.setdefault("/".join(parts[:-1]), {})["case_finding"] = _dict_or_empty(
                        data.get("finding")
                    )
            elif basename == "triage.json" and len(parts) >= 3 and parts[-2] == "evidence":
                data = json.loads(_read_member(zf, info))
                if isinstance(data, dict):
                    cases.setdefault("/".join(parts[:-2]), {})["triage"] = data
            elif basename == "diff.patch" and len(parts) >= 3 and parts[-2] == "evidence":
                text = _read_member(zf, info).decode("utf-8", "replace")
                cases.setdefault("/".join(parts[:-2]), {})["diff_text"] = text
            elif lower.endswith("report.md") and report_md_text is None:
                report_md_text = _read_member(zf, info).decode("utf-8", "replace")
            elif basename == "mvn_test_results.txt" and maven_text is None:
                maven_text = _read_member(zf, info).decode("utf-8", "replace")
            elif lower.endswith(".xml"):
                if xml_seen >= MAX_XML_FILES:
                    continue
                xml_seen += 1
                data = _read_member(zf, info)
                # whole file: a long leading comment could push a DOCTYPE past any prefix check
                if any(marker in data for marker in _XML_DANGEROUS):
                    notes.append(f"skipped {basename}: disallowed XML construct")
                    continue
                try:
                    root = ET.fromstring(data)
                except ET.ParseError:
                    notes.append(f"skipped {basename}: could not parse XML")
                    continue
                tag = root.tag.rsplit("}", 1)[-1]
                if tag == "testsuites":
                    junit_suites.extend(el for el in root if el.tag.rsplit("}", 1)[-1] == "testsuite")
                elif tag == "testsuite":
                    junit_suites.append(root)
        except Exception:  # noqa: BLE001 — one bad extra file must never break ingest
            notes.append(f"skipped {basename}: could not be read")
            continue

    junit = None
    if junit_suites:
        testcases = []
        suites_n = len(junit_suites)
        cases_n = failures_n = errors_n = skipped_n = 0
        for suite in junit_suites:
            cases_n += _int(suite.get("tests"), 0)
            failures_n += _int(suite.get("failures"), 0)
            errors_n += _int(suite.get("errors"), 0)
            skipped_n += _int(suite.get("skipped"), 0)
            for tc in suite:
                if tc.tag.rsplit("}", 1)[-1] == "testcase":
                    if len(testcases) < MAX_TESTCASES:
                        testcases.append(_junit_testcase_info(tc))
        junit = {
            "suites": suites_n,
            "cases": cases_n,
            "failures": failures_n,
            "errors": errors_n,
            "skipped": skipped_n,
            "testcases": testcases,
        }

    report_md = _parse_report_md(report_md_text) if report_md_text is not None else None
    maven = _parse_maven_log(maven_text) if maven_text is not None else None

    if not cases and report_md is None and junit is None and maven is None:
        return None

    return {
        "notes": notes,
        "cases": list(cases.values()),
        "report_md": report_md,
        "junit": junit,
        "maven": maven,
    }


def apply_run_extras(report: dict, extras: dict) -> None:
    """Mutate a parsed report (parse_report's output) with the extra scan-run
    context read_run_extras found: per-finding 'deep'/'fix' keys, verdict
    backfill from finding_case.json, and a report-level 'run_extras'
    summary. Findings are matched to triage/finding_case data by title
    (stripped, case-insensitive), falling back to (file, line_start). Never
    raises — an unmatched extra just adds a note.
    """
    findings = report.get("findings") or []
    by_title: dict = {}
    by_file_line: dict = {}
    for f in findings:
        title_key = _s(f.get("title")).strip().lower()
        if title_key and title_key not in by_title:
            by_title[title_key] = f
        key = (_s(f.get("file")).strip(), _int(f.get("line_start"), 0))
        if key not in by_file_line:
            by_file_line[key] = f

    notes = list(extras.get("notes") or [])
    mode_counts: dict = {}
    fix_counts: dict = {}
    deep_verified = 0
    unmatched = 0
    junit = extras.get("junit")
    testcases = junit["testcases"] if junit else []
    test_index = _index_testcases(testcases)

    for case in extras.get("cases") or []:
        triage = case.get("triage") or {}
        case_finding = case.get("case_finding") or {}

        title = triage.get("title") or case_finding.get("title")
        file_ = triage.get("file") or case_finding.get("file")
        line_start = case_finding.get("line_start")

        finding = None
        if title:
            finding = by_title.get(_s(title).strip().lower())
        if finding is None and file_ is not None:
            finding = by_file_line.get((_s(file_).strip(), _int(line_start, 0)))
        if finding is None:
            unmatched += 1
            continue

        if triage:
            gates = _dict_or_empty(triage.get("gates"))
            finding["deep"] = {
                "root_cause": _s(triage.get("root_cause"), _TEXT_CAP),
                "gates": {
                    "source": _s(gates.get("source"), 20),
                    "sink": _s(gates.get("sink"), 20),
                    "missing_control": _s(gates.get("missing_control"), 20),
                },
                "remaining_risks": [_s(x, _TEXT_CAP) for x in _list_or_empty(triage.get("remaining_risks"))[:20]],
                "recommendations": [_s(x, _TEXT_CAP) for x in _list_or_empty(triage.get("recommendations"))[:20]],
                "summary": _s(triage.get("summary"), _SUMMARY_CAP),
            }
            deep_verified += 1

            mode = _s(triage.get("mode")).strip().lower()
            if mode in ("fix", "report-only"):
                mode_counts[mode] = mode_counts.get(mode, 0) + 1

            status = _fix_status(triage)
            fix_counts[status] = fix_counts.get(status, 0) + 1

            diff_text = case.get("diff_text") or ""
            files = _diff_patch_files(diff_text)
            patch = _s(diff_text, 60000)
            if len(diff_text) > 60000:
                patch += "\n... (truncated)"

            tests = None
            tests_detail = ""
            if status in ("fixed", "patch_rejected") and files:
                tests, tests_detail = _compute_fix_tests(files, test_index, junit is not None)

            finding["fix"] = {
                "status": status,
                "scanner_verdict": _s(triage.get("verdict"), 100),
                "policy_action": _opt_s(triage.get("policy_action")),
                "policy_reason": _s(triage.get("policy_reason"), _TEXT_CAP),
                "files": files,
                "patch": patch,
                "tests": tests,
                "tests_detail": tests_detail,
            }

        if case_finding:
            if not finding.get("verdict"):
                v = case_finding.get("verdict")
                if v in ("TRUE_POSITIVE", "FALSE_POSITIVE"):
                    finding["verdict"] = v
            if finding.get("verdict_confidence") is None:
                finding["verdict_confidence"] = _opt_int(case_finding.get("verdict_confidence"))
            if not finding.get("verdict_reason"):
                finding["verdict_reason"] = _s(case_finding.get("verdict_reason"), _TEXT_CAP)
            if not finding.get("code_snippet"):
                finding["code_snippet"] = _s(case_finding.get("code_snippet"), _TEXT_CAP)

    if unmatched:
        notes.append(f"{unmatched} scanner evidence folders matched no finding")

    mode = max(mode_counts, key=mode_counts.get) if mode_counts else None

    tests_block = None
    if junit is not None or extras.get("maven") is not None:
        maven = extras.get("maven") or {}
        failing = []
        for tc in testcases:
            if tc["failed"]:
                last = tc["classname"].rsplit(".", 1)[-1] if "." in tc["classname"] else tc["classname"]
                failing.append({"test": f"{last}.{tc['name']}", "message": tc["message"]})
        tests_block = {
            "build": maven.get("build"),
            "suites": junit["suites"] if junit else 0,
            "cases": junit["cases"] if junit else 0,
            "failures": junit["failures"] if junit else 0,
            "errors": junit["errors"] if junit else 0,
            "skipped": junit["skipped"] if junit else 0,
            "failing": failing[:50],
            "not_run_modules": (maven.get("not_run_modules") or [])[:50],
        }

    coverage_block = dict(extras["report_md"]) if extras.get("report_md") is not None else None

    report["run_extras"] = {
        "mode": mode,
        "deep_verified": deep_verified,
        "total": len(findings),
        "fix_counts": fix_counts,
        "tests": tests_block,
        "coverage": coverage_block,
    }

    if notes:
        report["assumptions"] = list(dict.fromkeys([*(report.get("assumptions") or []), *notes]))
