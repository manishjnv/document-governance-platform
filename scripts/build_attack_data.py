"""Build the pinned, compact ATT&CK dataset for the ScopeWise MITRE module.

Dev-run script — NEVER executed at app runtime. Downloads the official MITRE
attack-stix-data bundles for the pinned release, compacts them to the shape
consumed by apps/api/app/mitre/attack_data.py, and writes
apps/api/app/mitre/data/attack.json (checked into the repo; the app never
fetches from the internet).

Pinned release: ATT&CK v19.1 (newest published release as of 2026-08-01,
per https://github.com/mitre-attack/attack-stix-data index.json).

Upgrade procedure: bump ATTACK_VERSION, rerun, review the printed validation
summary, commit the regenerated attack.json. Old assessments keep the
version stamped on them at run time.

Note on data_sources: ATT&CK v18 removed the x_mitre_data_sources field from
techniques. Since v18, telemetry is modeled as detection-strategy --detects-->
technique, with strategies referencing analytics that cite data components.
We flatten that chain to per-technique data component names (still the legacy
field if a bundle carries it, for pre-v18 rebuilds).

Usage:  python scripts/build_attack_data.py
"""

import io
import json
import re
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ATTACK_VERSION = "19.1"
DOMAINS = {  # output key -> attack-stix-data collection name
    "enterprise": "enterprise-attack",
    "ics": "ics-attack",
    "mobile": "mobile-attack",
}
URL_TEMPLATE = (
    "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/"
    "{coll}/{coll}-{version}.json"
)
OUTPUT = Path(__file__).resolve().parent.parent / "apps/api/app/mitre/data/attack.json"
CACHE_DIR = Path(tempfile.gettempdir()) / "attack-stix-cache"

# Sanity floors for validation (counts include revoked/deprecated entries).
MIN_TECHNIQUES = {"enterprise": 600, "ics": 50, "mobile": 75}

TECHNIQUE_ID_RE = re.compile(r"^T\d{4}(\.\d{3})?$")
CITATION_RE = re.compile(r"\s*\(Citation:[^)]*\)")


def fetch_bundle(coll: str) -> dict:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cached = CACHE_DIR / f"{coll}-{ATTACK_VERSION}.json"
    if not cached.exists():
        url = URL_TEMPLATE.format(coll=coll, version=ATTACK_VERSION)
        print(f"  downloading {url}")
        urllib.request.urlretrieve(url, cached)
    print(f"  using {cached} ({cached.stat().st_size / 1e6:.1f} MB)")
    return json.loads(cached.read_text(encoding="utf-8"))


def attack_external_id(obj: dict) -> str | None:
    for ref in obj.get("external_references", []):
        ext_id = ref.get("external_id", "")
        if "attack.mitre.org" in ref.get("url", "") and ext_id:
            return ext_id
    return None


def first_sentence(text: str | None) -> str:
    if not text:
        return ""
    text = CITATION_RE.sub("", text).strip()
    # Split on sentence end followed by whitespace; good enough for a summary.
    parts = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)
    return re.sub(r"\s+", " ", parts[0]).strip()


def build_data_sources_map(objs: list[dict], id2obj: dict) -> dict:
    """technique STIX id -> sorted list of data component names (v18+ chain)."""
    component_name = {
        o["id"]: o.get("name", "") for o in objs if o["type"] == "x-mitre-data-component"
    }
    analytic_components: dict[str, set] = {}
    for o in objs:
        if o["type"] == "x-mitre-analytic":
            names = set()
            for ref in o.get("x_mitre_log_source_references", []):
                name = component_name.get(ref.get("x_mitre_data_component_ref", ""))
                if name:
                    names.add(name)
            analytic_components[o["id"]] = names
    result: dict[str, set] = {}
    for o in objs:
        if o["type"] != "relationship" or o["relationship_type"] != "detects":
            continue
        source = id2obj.get(o["source_ref"], {})
        names: set = set()
        if source.get("type") == "x-mitre-detection-strategy":
            for aref in source.get("x_mitre_analytic_refs", []):
                names |= analytic_components.get(aref, set())
        elif source.get("type") == "x-mitre-data-component":  # pre-v18 shape
            names = {source.get("name", "")} - {""}
        if names:
            result.setdefault(o["target_ref"], set()).update(names)
    return result


def compact_domain(bundle: dict) -> dict:
    objs = bundle["objects"]
    id2obj = {o["id"]: o for o in objs}
    ds_map = build_data_sources_map(objs, id2obj)

    revoked_by = {}  # technique STIX id -> superseding external id
    for o in objs:
        if o["type"] == "relationship" and o["relationship_type"] == "revoked-by":
            target = id2obj.get(o["target_ref"], {})
            ext = attack_external_id(target)
            if ext:
                revoked_by[o["source_ref"]] = ext

    # Tactic order follows the matrix definition when present.
    matrix = next((o for o in objs if o["type"] == "x-mitre-matrix"), None)
    tactic_objs = {o["id"]: o for o in objs if o["type"] == "x-mitre-tactic"}
    ordered = (
        [tactic_objs[t] for t in matrix.get("tactic_refs", []) if t in tactic_objs]
        if matrix
        else sorted(tactic_objs.values(), key=lambda o: attack_external_id(o) or "")
    )
    tactics, shortname_to_id = [], {}
    for t in ordered:
        ext = attack_external_id(t)
        short = t.get("x_mitre_shortname", "")
        if not ext:
            continue
        tactics.append({"id": ext, "shortname": short, "name": t.get("name", "")})
        shortname_to_id[short] = ext

    techniques = []
    for o in objs:
        if o["type"] != "attack-pattern":
            continue
        ext = attack_external_id(o)
        if not ext or not TECHNIQUE_ID_RE.match(ext):
            continue
        is_sub = bool(o.get("x_mitre_is_subtechnique")) or "." in ext
        techniques.append(
            {
                "id": ext,
                "name": o.get("name", ""),
                "tactics": sorted(
                    {
                        shortname_to_id[p["phase_name"]]
                        for p in o.get("kill_chain_phases", [])
                        if p.get("phase_name") in shortname_to_id
                    }
                ),
                "platforms": o.get("x_mitre_platforms", []) or [],
                # Legacy field when present (pre-v18); else the v18+ chain.
                "data_sources": o.get("x_mitre_data_sources")
                or sorted(ds_map.get(o["id"], ())),
                "is_subtechnique": is_sub,
                "parent_id": ext.split(".")[0] if is_sub else None,
                "deprecated": bool(o.get("x_mitre_deprecated")),
                "revoked": bool(o.get("revoked")),
                "superseded_by": revoked_by.get(o["id"]),
                "summary": first_sentence(o.get("description")),
            }
        )
    techniques.sort(key=lambda t: t["id"])
    return {"tactics": tactics, "techniques": techniques}


def validate(domains: dict) -> list[str]:
    errors = []
    for name, dd in domains.items():
        techs = dd["techniques"]
        ids = {t["id"] for t in techs}
        if len(techs) < MIN_TECHNIQUES[name]:
            errors.append(
                f"{name}: {len(techs)} techniques < sanity floor {MIN_TECHNIQUES[name]}"
            )
        for t in techs:
            if t["revoked"] and not t["superseded_by"]:
                errors.append(f"{name}: revoked {t['id']} has no superseded_by")
            if t["is_subtechnique"] and t["parent_id"] not in ids:
                errors.append(f"{name}: sub-technique {t['id']} parent missing")
        if not dd["tactics"]:
            errors.append(f"{name}: no tactics extracted")
    ent = len(domains["enterprise"]["techniques"])
    for other in ("ics", "mobile"):
        if ent <= 2 * len(domains[other]["techniques"]):
            errors.append(f"enterprise ({ent}) not >> {other}")
    return errors


def main() -> int:
    domains = {}
    for key, coll in DOMAINS.items():
        print(f"{key}:")
        domains[key] = compact_domain(fetch_bundle(coll))

    errors = validate(domains)
    if errors:
        print("\nVALIDATION FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    output = {
        "version": ATTACK_VERSION,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "domains": domains,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    buf = io.StringIO()
    json.dump(output, buf, indent=1, ensure_ascii=False)
    OUTPUT.write_text(buf.getvalue(), encoding="utf-8", newline="\n")

    print(f"\nATT&CK v{ATTACK_VERSION} -> {OUTPUT} ({OUTPUT.stat().st_size / 1e6:.1f} MB)")
    for name, dd in domains.items():
        techs = dd["techniques"]
        active = [t for t in techs if not t["revoked"] and not t["deprecated"]]
        with_ds = sum(1 for t in active if t["data_sources"])
        print(
            f"  {name}: {len(techs)} techniques ({len(active)} active, "
            f"{sum(1 for t in techs if t['is_subtechnique'])} sub-techniques, "
            f"{sum(1 for t in techs if t['revoked'])} revoked, "
            f"{sum(1 for t in techs if t['deprecated'])} deprecated), "
            f"{len(dd['tactics'])} tactics, {with_ds}/{len(active)} active with data sources"
        )
    print("validation: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
