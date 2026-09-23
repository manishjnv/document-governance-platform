# Kickoff: risk remediation

Plan: `docs/planning/RISK_REMEDIATION_PLAN.md` (§0 has the status table; work
the first open item in "Suggested session order").

Paste to start a session:

> Read `docs/planning/RISK_REMEDIATION_PLAN.md`. Do the next open item in its
> session order (Session A first: R1 measure the prod free model with
> `scripts/accuracy_harness.py`, then R5 step 1 stale-assessment query). Follow
> the item's fix steps, acceptance test and routing as written. State the plan
> and wait for my go before touching prod or code. On finish: update the plan's
> §0 status row, add an RCA entry if a bug was fixed, write the session handoff.

Constraints that apply to every item: nothing is committed, pushed, deployed or
run against `scopewise_prod` without an explicit go; the backend suite runs solo
on `edgp_test`; add docs by file name, never `git add docs/`.
