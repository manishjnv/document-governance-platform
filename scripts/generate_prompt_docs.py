"""Regenerates prompts/*.md from apps/api/app/ai/agent.py's live
get_system_prompt() output -- run this after editing any agent's prompt
so the version-controlled reference copies never drift from what the
agents actually send. apps/api/app/ai/agent.py is the single source of
truth; these .md files are read-only mirrors for human review/diffing.

Usage: python scripts/generate_prompt_docs.py
"""

import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "api"))

from app.ai.agent import (  # noqa: E402
    CommercialReviewer,
    ConflictDetector,
    DeliveryReviewer,
    LegalReviewer,
    PMOReviewer,
    ScopeReviewer,
    SecurityReviewer,
)

AGENTS = {
    "scope": ScopeReviewer(),
    "delivery": DeliveryReviewer(),
    "commercial": CommercialReviewer(),
    "security": SecurityReviewer(),
    "pmo": PMOReviewer(),
    "legal": LegalReviewer(),
    # Not a review persona -- the Phase C2 conflict scan (orchestrator step,
    # org-disableable via CONFLICT-SCAN). Mirrored here like the others.
    "conflict": ConflictDetector(),
}


def render(slug: str, agent) -> str:
    sow = agent.get_system_prompt("SOW")
    rfp = agent.get_system_prompt("RFP")
    generated = date.today().isoformat()
    return f"""# {agent.name} -- prompt reference

**Auto-generated {generated} by `scripts/generate_prompt_docs.py`. Do not
edit this file directly** -- edit `apps/api/app/ai/agent.py`'s
`{agent.name}.get_system_prompt()` and re-run the generator instead, or
this file will drift from what the agent actually sends.

## SOW prompt

```
{sow}
```

## RFP prompt

```
{rfp}
```
"""


def main():
    prompts_dir = REPO_ROOT / "prompts"
    for slug, agent in AGENTS.items():
        out_path = prompts_dir / f"{slug}.md"
        out_path.write_text(render(slug, agent), encoding="utf-8")
        print(f"wrote {out_path.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
