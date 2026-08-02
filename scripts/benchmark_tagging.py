"""Offline tagging-accuracy benchmark for the MITRE module (plan phase A2).

Dev-run-only — NEVER imported by the app (same class of tool as
scripts/build_attack_data.py and scripts/generate_mitre_samples.py).
Measures the deterministic keyword pre-pass (and optionally the real
MitreTaggingAgent) against public Sigma detection rules, which ship their
own ATT&CK tags as independently-authored ground truth.

Source: github.com/SigmaHQ/sigma — rules are licensed under the Detection
Rule License (DRL), https://github.com/SigmaHQ/sigma/blob/master/LICENSE.
Rule title/description/detection-logic/logsource text is used here only to
derive benchmark input rows; no rule content is redistributed by this repo,
and downloaded rules are cached outside the repo (a temp directory).

This script does NOT change any threshold, prompt, or alias in the module —
measurement only. Needs the apps/api environment (PyYAML must be
importable; it already is in this project's dev environment even though it
is not a runtime dependency of the app itself).

Usage:
    python scripts/benchmark_tagging.py [--n 300] [--seed 42] [--with-ai]
        [--sigma-path DIR] [--out results.json]
        [--dump-fixture apps/api/tests/fixtures/sigma_keyword_bench.json --fixture-n 25]
"""

import argparse
import asyncio
import io
import json
import random
import re
import sys
import tempfile
import urllib.request
import zipfile
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "apps" / "api"))

import yaml  # noqa: E402

from app.mitre.attack_data import DEFAULT  # noqa: E402
from app.mitre.keyword_tag import keyword_tag_rows  # noqa: E402

SIGMA_ZIP_URL = "https://github.com/SigmaHQ/sigma/archive/refs/heads/master.zip"
CACHE_DIR = Path(tempfile.gettempdir()) / "sigma-bench-cache"
ATTACK_TAG_RE = re.compile(r"^attack\.t(\d{4})(?:\.(\d{3}))?$", re.IGNORECASE)
_SKIP_DIR_MARKERS = ("deprecated", "unsupported")

CONFIDENCE_BUCKETS = [(0.0, 0.4), (0.4, 0.7), (0.7, 0.9), (0.9, 1.01)]


# ---------------------------------------------------------------------------
# Sigma acquisition
# ---------------------------------------------------------------------------

def fetch_sigma_rules_dir(sigma_path: str | None) -> Path:
    """A directory containing Sigma's rules/ tree — either the user-given
    path, or a cached extraction of the repo's default-branch zip."""
    if sigma_path:
        path = Path(sigma_path)
        if not path.exists():
            raise SystemExit(f"--sigma-path {path} does not exist")
        return path

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    extracted = CACHE_DIR / "sigma-master"
    if extracted.exists():
        print(f"  using cached clone at {extracted}")
        return extracted

    print(f"  downloading {SIGMA_ZIP_URL} (first run only, cached after)")
    with urllib.request.urlopen(SIGMA_ZIP_URL, timeout=120) as resp:
        blob = resp.read()
    print(f"  extracting ({len(blob) / 1e6:.1f} MB)")
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(CACHE_DIR)
    # GitHub zips extract to "<repo>-<branch>/"
    candidates = [p for p in CACHE_DIR.iterdir() if p.is_dir() and p.name.startswith("sigma-")]
    if not candidates:
        raise SystemExit("sigma zip extracted but no sigma-* directory found")
    candidates[0].rename(extracted)
    return extracted


def _canonical_tags(raw_tags: list) -> list[str]:
    """Sigma 'attack.t1055.001'-style tags -> canonical 'T1055.001' IDs,
    resolved through the pinned dataset (drops unknown/deprecated/malformed
    so ground truth only contains IDs the module itself would ever emit)."""
    out, seen = [], set()
    for tag in raw_tags or []:
        m = ATTACK_TAG_RE.match(str(tag or ""))
        if not m:
            continue
        tid = f"T{m.group(1)}" + (f".{m.group(2)}" if m.group(2) else "")
        canonical, status = DEFAULT.resolve(tid)
        if status in ("malformed", "unknown") or canonical is None:
            continue
        if canonical not in seen:
            seen.add(canonical)
            out.append(canonical)
    return out


def load_sigma_candidates(rules_dir: Path) -> list[dict]:
    """Every parseable Sigma rule under rules_dir/rules/ (falls back to the
    whole tree if a "rules" subdir doesn't exist) carrying >=1 resolvable
    ATT&CK technique tag. Row shape matches the module's use-case row:
    row_ref/name/description/logic/log_source, plus gt_technique_ids."""
    search_root = rules_dir / "rules" if (rules_dir / "rules").exists() else rules_dir
    candidates = []
    for path in sorted(search_root.rglob("*.yml")):
        rel = path.relative_to(rules_dir).as_posix().lower()
        if any(marker in rel for marker in _SKIP_DIR_MARKERS):
            continue
        try:
            docs = list(yaml.safe_load_all(path.read_text(encoding="utf-8", errors="ignore")))
        except yaml.YAMLError:
            continue
        rule = next((d for d in docs if isinstance(d, dict) and "title" in d), None)
        if not rule:
            continue
        gt_ids = _canonical_tags(rule.get("tags"))
        if not gt_ids:
            continue
        logsource = rule.get("logsource") or {}
        log_source = ", ".join(
            f"{k}: {v}" for k, v in logsource.items() if isinstance(v, str)
        )
        try:
            logic_text = yaml.safe_dump(rule.get("detection") or {}, default_flow_style=False)
        except yaml.YAMLError:
            logic_text = str(rule.get("detection") or "")
        candidates.append({
            "row_ref": rel,
            "name": str(rule.get("title") or ""),
            "description": str(rule.get("description") or ""),
            "logic": logic_text,
            "log_source": log_source,
            "gt_technique_ids": gt_ids,
        })
    return candidates


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def _parent(tid: str) -> str:
    return tid.split(".")[0]


def score(rows: list[dict], predictions_by_ref: dict, *, parent_credit: bool) -> dict:
    """Micro-averaged precision/recall/F1 across all rule-technique pairs.

    parent_credit=False: exact technique-id match (sub-technique granularity).
    parent_credit=True: a predicted id also counts correct if its PARENT
    matches the parent of any ground-truth id for that rule (and vice versa
    for recall) -- the "parent-level-credit" variant from the phase A2
    contract, since a SIEM rule dump commonly tags at the parent level.
    """
    tp = fp = fn = 0
    misses, false_tags = [], []
    for row in rows:
        gt = set(row["gt_technique_ids"])
        pred = {m["technique_id"] for m in predictions_by_ref.get(row["row_ref"], [])}
        if parent_credit:
            gt_parents = {_parent(g) for g in gt}
            pred_parents = {_parent(p) for p in pred}
            row_tp = sum(1 for p in pred if p in gt or _parent(p) in gt_parents)
            row_fp = len(pred) - row_tp
            row_fn = sum(1 for g in gt if g not in pred and _parent(g) not in pred_parents)
        else:
            row_tp = len(pred & gt)
            row_fp = len(pred - gt)
            row_fn = len(gt - pred)
        tp += row_tp
        fp += row_fp
        fn += row_fn
        if row_fn and len(misses) < 20:
            misses.append({"rule": row["name"], "missed": sorted(gt - pred)})
        if row_fp and len(false_tags) < 20:
            false_tags.append({"rule": row["name"], "false_tags": sorted(pred - gt)})
    precision = tp / (tp + fp) if (tp + fp) else None
    recall = tp / (tp + fn) if (tp + fn) else None
    f1 = (2 * precision * recall / (precision + recall)) if precision and recall else None
    return {
        "tp": tp, "fp": fp, "fn": fn,
        "precision": precision, "recall": recall, "f1": f1,
        "misses_sample": misses, "false_tags_sample": false_tags,
    }


def confidence_bucket_accuracy(rows: list[dict], predictions_by_ref: dict) -> dict:
    """Per-bucket hit rate: of predictions whose confidence falls in a
    bucket, what fraction are actually correct (technique_id in that rule's
    ground truth)? Empirically informs the 0.7/0.4 coverage thresholds."""
    buckets = {f"{lo}-{hi}": [0, 0] for lo, hi in CONFIDENCE_BUCKETS}  # [correct, total]
    gt_by_ref = {row["row_ref"]: set(row["gt_technique_ids"]) for row in rows}
    for row_ref, mappings in predictions_by_ref.items():
        gt = gt_by_ref.get(row_ref, set())
        for m in mappings:
            conf = float(m.get("confidence") or 0.0)
            for lo, hi in CONFIDENCE_BUCKETS:
                if lo <= conf < hi:
                    key = f"{lo}-{hi}"
                    buckets[key][1] += 1
                    if m["technique_id"] in gt:
                        buckets[key][0] += 1
                    break
    return {
        key: {"correct": c, "total": t, "accuracy": (c / t if t else None)}
        for key, (c, t) in buckets.items()
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=300, help="rules to sample")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sigma-path", default=None, help="local Sigma clone (skip download)")
    parser.add_argument("--with-ai", action="store_true", help="also run the real MitreTaggingAgent (uses configured OpenRouter key)")
    parser.add_argument("--out", default=None, help="write full JSON results here")
    parser.add_argument("--dump-fixture", default=None, help="write a small pinned fixture here")
    parser.add_argument("--fixture-n", type=int, default=25)
    args = parser.parse_args()

    print("Locating Sigma rules...")
    rules_dir = fetch_sigma_rules_dir(args.sigma_path)
    print("Parsing rules with resolvable ATT&CK tags...")
    candidates = load_sigma_candidates(rules_dir)
    print(f"  {len(candidates)} candidate rules found")
    if not candidates:
        raise SystemExit("no candidate rules with resolvable ATT&CK tags found")

    rng = random.Random(args.seed)
    sample = rng.sample(candidates, min(args.n, len(candidates)))
    print(f"  sampled {len(sample)} rules (seed={args.seed})")

    keyword_rows = [{"row_ref": r["row_ref"], "name": r["name"], "description": r["description"], "logic": r["logic"]} for r in sample]
    keyword_preds = keyword_tag_rows(keyword_rows)

    results = {
        "sample_size": len(sample),
        "seed": args.seed,
        "layers": {
            "keyword": {
                "exact": score(sample, keyword_preds, parent_credit=False),
                "parent_credit": score(sample, keyword_preds, parent_credit=True),
                "confidence_buckets": confidence_bucket_accuracy(sample, keyword_preds),
                "rows_with_any_prediction": sum(1 for r in sample if keyword_preds.get(r["row_ref"])),
            },
        },
    }

    if args.with_ai:
        from app.mitre.agents import tag_untagged_rows  # noqa: E402 (heavy import, only needed here)

        untagged = [row for row in keyword_rows if row["row_ref"] not in keyword_preds]
        print(f"  running the real AI tagger over {len(untagged)} keyword-residue rows...")
        ai_preds_only = asyncio.run(tag_untagged_rows(untagged))
        combined_preds = {**keyword_preds, **ai_preds_only}
        results["layers"]["ai_residue_only"] = {
            "exact": score(sample, ai_preds_only, parent_credit=False),
            "parent_credit": score(sample, ai_preds_only, parent_credit=True),
            "confidence_buckets": confidence_bucket_accuracy(sample, ai_preds_only),
        }
        results["layers"]["combined"] = {
            "exact": score(sample, combined_preds, parent_credit=False),
            "parent_credit": score(sample, combined_preds, parent_credit=True),
            "confidence_buckets": confidence_bucket_accuracy(sample, combined_preds),
        }

    # ---- printed table ----
    print("\n=== Tagging accuracy benchmark ===")
    print(f"Sample: {len(sample)} Sigma rules (seed={args.seed})\n")
    for layer_name, layer in results["layers"].items():
        print(f"-- {layer_name} --")
        for variant in ("exact", "parent_credit"):
            v = layer[variant]
            p = f"{v['precision']:.3f}" if v["precision"] is not None else "n/a"
            r = f"{v['recall']:.3f}" if v["recall"] is not None else "n/a"
            f1 = f"{v['f1']:.3f}" if v["f1"] is not None else "n/a"
            print(f"  {variant:14s} precision={p} recall={r} f1={f1} (tp={v['tp']} fp={v['fp']} fn={v['fn']})")
        print("  confidence buckets:")
        for bucket, stats in layer["confidence_buckets"].items():
            acc = f"{stats['accuracy']:.3f}" if stats["accuracy"] is not None else "n/a"
            print(f"    {bucket:10s} n={stats['total']:4d} accuracy={acc}")
        print()

    if args.out:
        Path(args.out).write_text(json.dumps(results, indent=2), encoding="utf-8")
        print(f"Full results written to {args.out}")

    if args.dump_fixture:
        # Diverse, deterministic slice: some rows the keyword layer hits,
        # some it misses -- a real regression pin, not a cherry-picked win.
        hits = [r for r in sample if keyword_preds.get(r["row_ref"])]
        misses = [r for r in sample if not keyword_preds.get(r["row_ref"])]
        half = args.fixture_n // 2
        fixture_rows = (hits[:half] + misses[: args.fixture_n - half])[: args.fixture_n]
        fixture_rows.sort(key=lambda r: r["row_ref"])  # stable ordering across regenerations
        Path(args.dump_fixture).parent.mkdir(parents=True, exist_ok=True)
        Path(args.dump_fixture).write_text(
            json.dumps({"rows": fixture_rows}, indent=2), encoding="utf-8"
        )
        print(f"Fixture ({len(fixture_rows)} rows) written to {args.dump_fixture}")

    return results


if __name__ == "__main__":
    main()
