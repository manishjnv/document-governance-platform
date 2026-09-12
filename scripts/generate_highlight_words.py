"""Regenerates the web mirror of the Code Security Review highlight word
lists from apps/api/app/codereview/highlight_words.json (the single source
of truth, also loaded at runtime by report_xlsx.py / report_pptx.py).

Same pattern as generate_prompt_docs.py: the JSON is edited by hand, the
.ts file is generated and read-only. tests/test_codereview_report.py
fails when the mirror is stale.

Usage: python scripts/generate_highlight_words.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE = REPO_ROOT / "apps/api/app/codereview/highlight_words.json"
TARGET = REPO_ROOT / "apps/web/app/codereview/[reviewId]/components/highlightWords.ts"


def render(words: dict) -> str:
    risk = "|".join(words["risk"])
    fix = "|".join(words["fix"])
    return (
        "// GENERATED FILE - do not edit. Source: apps/api/app/codereview/highlight_words.json\n"
        "// Regenerate: python scripts/generate_highlight_words.py\n"
        f"export const RISK_RE = /\\b({risk})\\b/gi;\n"
        f"export const FIX_RE = /\\b({fix})\\b/gi;\n"
    )


def main() -> None:
    words = json.loads(SOURCE.read_text(encoding="utf-8"))
    TARGET.write_text(render(words), encoding="utf-8", newline="\n")
    print(f"wrote {TARGET.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
