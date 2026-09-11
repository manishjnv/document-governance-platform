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
import stat
import struct
import zipfile
from typing import Any, Optional

MAX_REPORT_BYTES = 10 * 1024 * 1024
MAX_FINDINGS = 2000
MAX_ZIP_ENTRIES = 50
MAX_ZIP_MEMBER_BYTES = MAX_REPORT_BYTES
MAX_ZIP_TOTAL_BYTES = 30 * 1024 * 1024
SEVERITIES = ("critical", "high", "medium", "low", "info")

_SEVERITY_RANK = {s: i for i, s in enumerate(SEVERITIES)}
_TEXT_CAP = 20000
_TITLE_CAP = 500
_SUMMARY_CAP = 4000
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


def unpack_scan_zip(raw: bytes) -> tuple[bytes, str, Optional[bytes], Optional[str]]:
    """Extract findings/sarif report + optional manifest from a consultant
    scan-kit zip. Attacker-controlled input: bounded entry count, bounded
    per-member and total declared sizes checked BEFORE reading (zip-bomb
    guard), path-traversal rejection, symlinks ignored rather than followed.
    """
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
        members = [info for info in zf.infolist() if not info.is_dir()]
    except (zipfile.BadZipFile, struct.error, OverflowError, ValueError):
        raise IngestError("Not a valid zip file")
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

    def _read(info: zipfile.ZipInfo) -> bytes:
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

    report_info = None
    report_kind_rank = None  # 0 = findings.json, 1 = .sarif
    for depth, basename, info in candidates:
        if basename == "findings.json":
            rank = 0
        elif basename.lower().endswith(".sarif"):
            rank = 1
        else:
            continue
        if report_kind_rank is None or rank < report_kind_rank or (
            rank == report_kind_rank and depth < report_info[0]
        ):
            report_kind_rank = rank
            report_info = (depth, basename, info)

    if report_info is None:
        raise IngestError("Zip contains no findings.json or .sarif")

    manifest_info = None
    for depth, basename, info in candidates:
        if basename.startswith("run_manifest") and basename.lower().endswith(".json"):
            if manifest_info is None or depth < manifest_info[0]:
                manifest_info = (depth, basename, info)

    report_bytes = _read(report_info[2])
    report_name = report_info[1]
    manifest_bytes = None
    manifest_name = None
    if manifest_info is not None:
        manifest_bytes = _read(manifest_info[2])
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

    return _finalize(
        source_format="sarif",
        tool=_opt_s(driver.get("name")) or "vvaharness",
        tool_version=_opt_s(driver.get("version")),
        repo_name=None,
        git_sha=None,
        summary_text="",
        degraded=False,
        degraded_reason="",
        assumptions=assumptions,
        raw_findings=raw_findings,
        chains=[],
        dropped_count=0,
        raw_findings_count=len(results),
        metrics=_map_metrics(None),
    )


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
    return {
        "idx": 0,
        "title": _s(message.get("text"), _TITLE_CAP),
        "severity": _normalize_severity(severity_raw, assumptions),
        "vuln_class": rule_id,
        "vuln_class_label": rule_id,
        "cwe": _opt_s(props.get("cwe")),
        "cvss_score": _float_or_none(props.get("cvssScore")),
        "cvss_vector": _opt_s(props.get("cvssVector")),
        "cvss_rating": _opt_s(props.get("cvssRating")),
        "file": _s(artifact.get("uri")),
        "line_start": _int(region.get("startLine"), 0),
        "line_end": _int(region.get("endLine"), 0),
        "confidence": _confidence(props.get("confidence")),
        "votes": 1,
        "verdict": None,
        "verdict_confidence": None,
        "verdict_reason": "",
        "description": _s(message.get("text"), _TEXT_CAP),
        "impact": "",
        "exploit_scenario": "",
        "preconditions": [],
        "recommendation": "",
        "code_snippet": "",
        "exploitability_notes": "",
        "verifier_reasoning": "",
        "offensive_priority": None,
        "offensive_reason": "",
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
