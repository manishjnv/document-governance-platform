# Session handoff — 2026-08-18/19: Splunk connector, report de-branding, PDF/PPTX uplift, tool-coverage overlay

**Headline:** one marathon session shipped (all deployed to prod at
scopewise.assessiq.in): the Splunk SIEM connector, full report
de-branding, the customer-friendly Assumptions rework, the six-piece PDF
report uplift, the PPTX uplift + three rounds of screenshot-review
polish, and the tool-native coverage overlay (design + T1 + T2). Plus the
MGH customer-data verification that started it all. Suite baseline moved
902→935 passed / 7 skipped across the session (CLAUDE.md is canonical).

## Commits (in order)

| Commit | What |
|---|---|
| `4e74353` | Splunk REST connector (connectors/splunk.py, egress ALLOWED_PORTS {443,8089}, migration 037, wizard tab, 15 tests; Sonnet adversarial ACCEPT + RecursionError hardening) |
| `e6deb61` | Docs for the above, baseline 905/7 |
| `4c02463` | Report de-branding (unbranded default; templates renamed `mitre-{use-cases,environment}-template.xlsx` + regenerated) + Assumptions tab 3-column plain-language rework + "restructured, never revoked" wording (source + render-time legacy rewrite) |
| `03785d9` | Docs, baseline 906/7 |
| `623667c` | PDF uplift: board page, Navigator-style heatmap, top-10 vs you (curated `top_attacker_techniques.json`, Red Canary TDR 2025), adversary + efficacy spotlights, closing page; wording lint test + AI-narrative leash |
| `caa91e1` | **Hotfix for a real prod outage**: PEP 701 f-string passed local 3.14, crashed prod 3.11 at import. Lesson memorialized (memory `prod-python-311-fstring-gotcha`): always run the in-container compile/render smoke after deploy |
| `32fdef9` | PPTX uplift: board slide, ATT&CK mosaic, top-10, adversary spotlight, closing projection — shared data builders moved to report_common so PDF and deck always agree |
| `1373b2e` | PPTX fill pass + hard 20-slide cap (merged Working/Open slide, dropped duplicate Headline slide, divider bullets, mosaic legend, roadmap payoff strip) |
| `ef10cb0` | Screenshot review #1: no score on cover (CONFIDENTIAL stamp), chart titles + % labels, balanced log-source table, fuller cards everywhere |
| `3236398` | Screenshot review #2: adversary technique table w/ per-technique rule counts, roadmap telemetry lines + "how" in payoff, next-steps always 6 highlighted boxes |
| `6a0067d` | Mosaic cells labeled with technique IDs (anonymous color bars carried no information) |
| `d3ef87f` | Assumptions dedup: `condense_assumptions()` collapses per-rule repeats ("… — affects 12 rules"); all explainers cut to one sentence |
| `8372323` | Tool-coverage overlay design plan + environment-template Security Tooling guidance (Notes column, canonical product names) |
| `a85000b` | Tool-coverage overlay T1+T2: curated `tool_coverage.json` (MITRE ATT&CK Evaluations), `compute_tool_overlay()` render-time engine, PDF board line + blue heatmap cells + gap-register notes, XLSX tracker column + Summary row, PPTX board line + blue mosaic + legend, UI strip + drawer credit card, 4 tests. **Incident:** the first version of this commit (`c642b6a`) accidentally swept untracked customer data (docs/sample/project/) into the public repo via `git add docs/` — fixed within ~2 minutes by soft-reset + force-push; the path is now gitignored. Lesson: stage docs files explicitly, never `git add docs/` wholesale |
| `0732f8c` | Attestation flow (T4): POST tool-attest creates 'tool_attested' rule rows (migration 038 + ORM lockstep) + inline recompute — confirmed alert paths count in the REAL score; drawer per-tool attest buttons |
| `f9de718` | Bulk attestation UI: 'Client confirmed — attest all N for <tool>' on the blue credit strip, confirmation dialog, 50-id chunking |
| `9828461` | PPTX board slide: covered split by provenance — SIEM rules vs attested tools vs combined (covered_split in report_common) |
| `67534a5` | Same split on UI (lib.coveredSplit line in the blue strip), PDF board tiles, XLSX Summary breakdown rows |
| (final) | PPTX typography pass: auto-highlight of every number/percentage in plain runs (regex keeps T-IDs/versions plain), body fonts +0.5pt via the shared text()/style_table helpers |

## Also in this session (no separate commit)

- **MGH verification** (`docs/sample/project/MGH`, untracked customer data):
  confirmed `output/` workbooks carry all 245 rules from `bin.xlsx`
  byte-exact; `template/` files were blank samples. verify.py + independent
  cross-checks, 0 errors.
- Adversary sign-off discipline: Splunk/egress diff got the Sonnet
  adversarial pass (codex:rescue still broken) — verdict ACCEPT, one
  hardening applied.

## Key design decisions (durable)

1. **Reports are unbranded by default** — `report_display_name` defaults
   to ""; per-org override still works. No product name in any generated
   artifact, template, or filename.
2. **Human wording is machine-enforced** — `test_mitre_wording.py` bans
   AI-tell phrases in templates/curated data/report modules;
   `generate_narrative` degrades to template text when AI output trips
   the same list.
3. **Real data only in reports** — every external figure carries source +
   year (Red Canary TDR 2025; MITRE ATT&CK Evaluations); curated files
   are test-enforced against attack.json; no invented benchmarks ever.
4. **PDF and PPTX compute shared numbers in one place** —
   `report_common.py` (`rule_health`, `compute_moves`, `top10_vs_you`,
   `adversary_spotlight`, `compute_tool_overlay`, `condense_assumptions`).
5. **PPTX hard cap: 20 slides** (test-enforced).
6. **Tool-coverage overlay is a render/read-time pure lookup** (deviation
   from the plan's pipeline approach — better: zero storage change, works
   retroactively on every existing assessment). Always a second labeled
   number; the caveat prints wherever it shows.

## Ops notes

- Migrations 037 + 038 applied to edgp_dev, edgp_test, scopewise_prod.
- Prod image is **Python 3.11** (dev 3.14) — run the in-container compile
  smoke after every deploy touching Python.
- Splunk connector awaits a reachable customer Splunk host + token
  (Splunk Cloud: allowlist the VPS egress IP on 8089).
- Tool-coverage data file refresh: once per ATT&CK Evaluations round
  (~yearly), data-only change.

## Open / next

- Attestation flow (T4) shipped 2026-08-19 — see plan doc.
- Tool-coverage: ranking demotion of tool-covered gaps deliberately
  deferred (ordering change would churn rank tests) — noted in plan.
- Client asked (MGH): option 1 = export their EDR's 90-day unique
  detections into the rule template (name + technique column is enough);
  conversion script offered.
- Elastic connector + connections CRUD UI still parked.

## Agent utilization

- Opus/Fable (main): all design, implementation, reviews, deploys — the
  session was interactive-iterative; self-execution beat delegation on
  hot files throughout.
- Sonnet: 1 adversarial security sign-off (Splunk connector/egress) —
  verdict ACCEPT, 1 hardening finding applied. Reworked: N.
- Haiku: n/a — no bulk sweeps needed.
- codex:rescue: n/a — companion broken (2026-07-23 memory); Sonnet
  takeover per standing fallback.
