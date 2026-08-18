# PDF Report Uplift — plan (2026-08-18)

User-agreed scope (session 2026-08-18; "thoughts" phase done, build approved).
Goal: the PDF should read like a hand-built consulting deliverable. Three
hard rules from the user, all enforced in code:

1. **Every number real and traceable** — computed from stored JSONB or cited
   to a named public report + year. No invented benchmarks, no peer
   percentiles.
2. **Data richness** — more evidence per page, not more prose.
3. **Human wording** — short pointer sentences, verdict first; nothing that
   reads AI-generated. Enforced by a banned-phrase lint test, not discipline.

## The six pieces

| # | Piece | Data source | Where in the PDF |
|---|---|---|---|
| 1 | **Board page** — one-page "Where you stand": big verdict, count tiles, top-3 gaps, top-3 moves, trend arrow | stored summary + compare | after cover, own page (kept in `scope=executive`) |
| 2 | **Navigator-style heatmap** — parent techniques grouped into per-tactic columns (replaces the flat cell-soup grid) | technique_results (tactics already on each row) | detailed section, per domain |
| 3 | **Top-10 attacker techniques vs you** — Red Canary TDR 2025 top-10 list × your coverage states | new curated `data/top_attacker_techniques.json` (source + year printed on page; IDs test-resolved against attack.json) | detailed, before tactics |
| 4 | **Adversary spotlight** — chosen threat actor (or industry profile) kill-chain strip colored by your real states + blind-spot list | `threat_profiles.json` (sources cited in-file) × technique_results | detailed, before tactics; skipped when no actor/industry |
| 5 | **Detection efficacy spotlight** — enabled rules with Last Triggered "never", disabled rules; "counts as coverage, unproven" framing | use_cases (severity/last_triggered, migration 036) | detailed, before roadmap |
| 6 | **Closing page** — "Your next 90 days": current→projected % (computed by re-running the coverage ratio with short-term items closed — the existing `projected` math), 3 moves, honesty box, footer strip w/ assessment ID | stored summary + use_cases | last page before audit footer |

## Wording enforcement

- `tests/test_mitre_wording.py`: bans AI-tell phrases (leverage, robust,
  holistic, seamless, utilize, "it is important to note", "in today's",
  furthermore, moreover, delve, cutting-edge, state-of-the-art,
  best-in-class, "overall security posture", "this highlights") across
  report templates, curated data JSONs, and the report/narrative modules.
  Python comment lines stripped before matching.
- `agents.py` AI-narrative leash: `generate_narrative` degrades to the
  template narrative when the AI text trips the same banned list — AI
  wording can never reach a client unchecked.
- Hand-edit pass over existing report strings at build time.

## Explicitly rejected (user decisions this session)

- "Since last assessment" delta page — dropped by user.
- Fake peer percentiles / invented benchmarks — never.
- QR code on closing page — skipped (assessment ID + plain text pointer
  instead; no new dependency).

## Sources used for curated top-10 (verify on yearly refresh)

- Red Canary Threat Detection Report 2025, "Top ATT&CK Techniques"
  (redcanary.com/threat-detection-report/techniques/): T1078.004,
  T1059.001, T1059.003, T1530, T1105, T1114.003, T1047, T1204.004,
  T1564.008, T1027.
- Refresh cadence: once per TDR release (~March); update the JSON's
  `source`/`year` fields with the list.
