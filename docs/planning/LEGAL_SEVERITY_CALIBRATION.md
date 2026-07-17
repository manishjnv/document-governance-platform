# Legal Severity Calibration — SME Review Worksheet

**Status:** Engineering prep complete. SME sign-off NOT done — no legal SME
has reviewed this yet. Do not treat LegalReviewer severity/confidence as
production-trusted until someone with legal judgment completes Part 3 below.

## 1. How severity is currently assigned

`LegalReviewer` (`apps/api/app/ai/agent.py`) assigns `severity` per finding
as free-text LLM judgment — one of `critical|major|medium|low` — with no
numeric model behind it. There is no separate "calibration formula";
whatever the LLM writes into the JSON `severity` field is used as-is.

That severity then drives a fixed, code-side point penalty in
`apps/api/app/scoring/algorithm.py`:

| Severity | Specific penalty (category) | General penalty (all categories) |
|---|---|---|
| critical | -25 | -12 |
| major | -15 | -6 |
| medium | -8 | -3 |
| low | -4 | -1 |
| info | 0 | 0 |

So a legal finding the LLM calls "critical" costs a document up to 37 points
off its overall score. **The engineering risk isn't the point math (that's
fixed and tested) — it's whether the LLM's critical/major/medium/low label
matches what a real contracts lawyer would call it.**

## 2. Finding types LegalReviewer can emit

`missing_liability_cap | undefined_ip_ownership | missing_termination_clause | no_governing_law | missing_warranty | ambiguous_legal_language`

## 3. SME review worksheet (fill this in)

For each finding type, an SME should answer:

| Finding type | System's typical severity (observed) | SME's severity | Agree? | Notes |
|---|---|---|---|---|
| missing_liability_cap | major | | | |
| undefined_ip_ownership | major | | | |
| missing_termination_clause | major | | | |
| no_governing_law | major | | | |
| missing_warranty | major | | | |
| ambiguous_legal_language | medium | | | |

"Observed" column is from live smoke-test runs against sample SOW/RFP text
(2026-07-17, `deepseek/deepseek-chat` via OpenRouter) — see
`docs/planning/RFP_ACCURACY_VALIDATION.md` raw log for full finding text.
Small sample (2 documents); treat as a starting point for SME calibration
discussion, not a statistically valid distribution.

**Escalation question for the SME:** for a document with NO executed
contract terms yet (RFP), is a missing liability/IP/termination *disclosure*
really "major" the way it would be in an unsigned SOW clause, or should RFP
findings be down-weighted a severity tier since nothing is legally binding
yet? `LegalReviewer`'s RFP branch prompt already tells the model to treat
this more leniently ("flag it as such, don't assume it's automatically
critical the way an unsigned SOW clause would be") — SME should confirm the
model is actually following that instruction in practice, not just stating it.

## 4. What "done" looks like

- [ ] SME fills in the table above against a real (not synthetic) sample
- [ ] Any systematic over/under-severity pattern gets a prompt fix in
      `LegalReviewer.get_system_prompt()`, re-tested, and this doc updated
- [ ] Sign-off line added below with SME name + date

**Sign-off:** _(pending)_
