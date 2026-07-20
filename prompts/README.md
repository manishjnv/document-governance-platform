# Prompt Library

Version-controlled reference copies of the 6 AI review agents' system
prompts, mirroring `apps/api/app/ai/agent.py`'s
`get_system_prompt("SOW"/"RFP")` methods.

**`apps/api/app/ai/agent.py` is the single source of truth.** These
`.md` files are auto-generated read-only mirrors for human review/
diffing prompt changes across sessions -- they are never loaded at
runtime. After editing any agent's prompt in `agent.py`, regenerate:

```bash
python scripts/generate_prompt_docs.py
```

- `scope.md` -- ScopeReviewer (deliverables, acceptance criteria, exclusions, scope creep)
- `delivery.md` -- DeliveryReviewer (timeline, dependencies, staffing, schedule buffer)
- `commercial.md` -- CommercialReviewer (pricing, payment terms, renewal, currency/tax)
- `security.md` -- SecurityReviewer (compliance standards, personnel security, breach notification, accessibility)
- `pmo.md` -- PMOReviewer (RACI, escalation, SLAs, entry/exit criteria, reporting cadence)
- `legal.md` -- LegalReviewer (liability, IP, termination, confidentiality, insurance, force majeure)

Design rationale, sources used, and the 2026-07-20 accuracy-focused
revision are documented in
`docs/planning/PROMPT_ENGINEERING_GUIDE.md`.

There is no `classifier.md` -- document-type detection
(`DocxParser._detect_type()` etc. in `apps/api/app/parser.py`) is
keyword/section-based, not an LLM prompt. The original scaffold listed
one aspirationally; removed here to match what's actually built, not
what was planned.
