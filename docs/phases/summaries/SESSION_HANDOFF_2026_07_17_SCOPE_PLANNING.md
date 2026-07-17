# Session Handoff — 2026-07-17 Scope Planning

**Headline:** Trimmed Phase 3-7 speculative scope; planned + spec'd the pre-launch core review-accuracy work (Legal/PMO agents, ambiguous-language scan, RFP support). No implementation yet — this session was planning-only.

**Commits this session:**
- `b1b521e` — Update AI agent specs and launch criteria for core review-accuracy work (`docs/planning/4_AI_AGENT_SPECS.md`, `5_LAUNCH_CRITERIA.md`)
- (Phase 3-7 prompt-doc scope trims already landed separately in `434aeeb`, prior to this session)

---

## What changed

**Phase 3-7 scope cuts** (`docs/phases/prompts/PHASE_{3,4,5,6,7}_PROMPT.md`, committed in `434aeeb`):
- Phase 3: dropped i18n, trimmed accessibility to bare minimum, trimmed scalability infra (K8s autoscaling, ELK, read replicas, distributed tracing) to only what's built/safety-critical
- Phase 4 (ML/Analytics): fully deferred — cold-start problem, no training data yet
- Phase 5 (Enterprise Integrations): fully deferred — no signed customer contract behind any integration
- Phase 6 (SLA/Support): trimmed to bare ticketing + KB, dropped SLA credits/video training/partner program
- Phase 7 (Maintenance): reframed as ongoing practice, not a scheduled task list; deferred SOC2/pen-testing and feedback/NPS systems

**Core review-accuracy plan** (`docs/planning/4_AI_AGENT_SPECS.md`, `5_LAUNCH_CRITERIA.md`, committed in `b1b521e`):
- Found: `orchestrator.py` only wires 4 of the 5 originally spec'd agents — `PMOReviewer` was spec'd but never built
- Found: no `LegalReviewer` agent existed at all
- Found: no ambiguous/open-ended language detection anywhere
- Found: `RFP` is not a supported `DocumentType` — enum only has SOW/Proposal/Other; all 20 built-in rules are SOW-only
- Spec'd: LegalReviewer agent, extended PMOReviewer (+ entry/exit criteria + fallback-plan checks), cross-cutting ambiguous-language rule scan, RFP document-type support (enum + DB constraint + new rule set + doc-type-conditional agent prompts)
- Gated: every new agent/rule set must independently pass the existing precision/recall/calibration/dedup bar (Metrics 1.1-1.4 in `5_LAUNCH_CRITERIA.md`) on its own test set before shipping

## Next action

Run the implementation prompt (already handed to a new session) covering: LegalReviewer build, PMOReviewer build, ambiguous-language scan, RFP support, orchestrator wiring to 6 agents + rule engine + scan. Acceptance gated on Metrics 1.1-1.4 per new agent/rule set.

## Open questions

- Real test-set sourcing for RFP accuracy validation (need ≥10 representative RFPs — likely need user to supply or approve synthetic ones)
- Whether Legal risk severity calibration needs legal SME review before trusting confidence scores in production

## Tests

Not run this session (planning-only, no code changed).

---

## Agent-utilization footer

- Opus/main session: gap analysis (read `ai_insights.py`, `agent.py`, `orchestrator.py`, `builtin.py`, `enums.py`, `4_AI_AGENT_SPECS.md`, `5_LAUNCH_CRITERIA.md`), plan authored and written into planning docs directly (small diff, no subagent needed)
- Sonnet: n/a — no implementation subagents dispatched this session
- Haiku: n/a — no bulk sweeps needed
- codex:rescue: n/a — no security/auth/classifier code touched, docs-only session
