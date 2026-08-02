# Kickoff — MITRE accuracy & template improvement (run ALL phases + deploy)

Paste this into a fresh session to execute the whole plan sequentially
and deploy at the end (deploy is pre-authorized by this prompt):

```text
Read docs/planning/MITRE_ACCURACY_IMPROVEMENT_PLAN.md in full — its
Ground rules apply to everything below. Execute phases A1 through A8 IN
ORDER, one at a time, following each phase's own prompt block exactly.
Do not start a phase until the previous one is fully green.

Per phase: implement per the phase contract, run the touched-module
tests, commit per logical unit, and tick the phase in the plan's
Sequence & status table. Notes:
- A2's benchmark metrics and A5's before/after tables go in the final
  summary.
- A6 is the only phase with a migration (036): apply it to edgp_dev AND
  edgp_test immediately (no runner exists), grep
  test_insights_extra.py's hand-rolled schema and ORM CheckConstraints
  per the CLAUDE.md 5-point checklist.
- A7 is security-adjacent: STOP before pushing it and run the
  adversarial sign-off (Sonnet takeover per the codex:rescue outage
  memory — self-contained prompt, egress-guard + secret-handling attack
  vectors, verdict logged). Do not proceed past A7 without an
  accept/revise-resolved verdict.
- If a phase's approach turns out wrong (not just buggy), stop and
  report rather than forcing it; skip-and-continue is allowed only for
  A4/A5/A8 (mark the phase ☐ with a note), never for A6/A7.

After A8: run the FULL backend suite alone on edgp_test (check
pg_stat_activity first; baseline 809/7 grows with new tests — update
the CLAUDE.md baseline line) + npx tsc --noEmit. Update
MITRE_MODULE_REFERENCE.md (§5 §6 §7 §15 as touched),
IMPLEMENTATION_PROGRESS.md, and the plan's status table. Commit docs.

DEPLOY (authorized): push to master, then the standard VPS loop —
ssh a11yos-vps "cd /opt/scopewise && git pull && docker compose -f
docker-compose.vps.yml --env-file .env build && GIT_SHA=$(git rev-parse
--short HEAD) docker compose -f docker-compose.vps.yml --env-file .env
up -d" — then apply migration 036 to scopewise_prod (docker exec -i
scopewise-postgres psql -U scopewise_user -d scopewise_prod <
apps/api/migrations/036_*.sql), then smoke: /login 200, /mitre 200,
create+run a sample-kit assessment end-to-end, download PDF + XLSX,
confirm the new template columns parse and the telemetry cross-check
assumption renders. Touch ONLY scopewise-* containers on the VPS.

Finish with: per-phase result table (commit SHA, tests added, reworked
Y/N), A2/A5 metrics, the A7 sign-off verdict, deploy SHA + smoke
results, and a session handoff in docs/phases/summaries/.
```

Fallback: to run one phase at a time instead, use the plan doc's
per-phase prompt blocks directly (original one-phase-per-session mode).
Order: A1 → A2 → A3 → A4 → A5 → A6 (migration 036) → A7 (sign-off
required) → A8.
