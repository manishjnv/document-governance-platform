# Real VVAH scan — OWASP/NodeGoat (golden fixture)

The only **real** scanner output in this folder tree (everything one level
up is synthetic). Produced 2026-09-11/12 with the ScopeWise scan kit exactly
as a consultant would run it; used by
`apps/api/tests/test_codereview_ingest.py::test_real_nodegoat_golden`.

| | |
|---|---|
| Target | https://github.com/OWASP/NodeGoat (Apache-2.0), shallow clone |
| Commit | `c5cb68a7084e4ae7dcc60e6a98768720a81841e8` |
| Scanner | vvaharness 1.3.0 (kit wheel), `scan --stop-after s9 --config config.yaml` |
| Models | S1–S9 `deepseek/deepseek-v4-pro`, `autoexclude`/`graph_annotate` `deepseek/deepseek-v4-flash`, all via OpenRouter (`via: openai`) |
| Estimate | 63 code files, 1,293,982 bytes, ~323k raw input tokens |
| Actual | 505 LLM calls, 2,256,705 prompt + 1,143,719 completion = 3,400,424 tokens (3.38M served from cache), 6,155 s wall clock |
| Cost | manifest has no pricing table (`cost_usd: null`); at OpenRouter list prices the upper bound is ≈ $4.3 (prompt $0.95/M, completion $1.90/M, cache reads cheaper) — key usage for the day, including one aborted earlier attempt, was $5.62 |
| Result | 88 raw → 29 ranked findings (6 critical / 5 high / 18 medium), 59 dropped, 6 exploit chains, 29/29 verifier TRUE_POSITIVE, 4 verifier false positives dropped upstream, not degraded |

Files: `findings.json` (FinalReport), `nodegoat_report.sarif` (SARIF 2.1.0,
29 results), `run_manifest_20260911T185822Z.json`, and
`scopewise-scan-nodegoat-20260912.zip` (the three files at the zip root,
i.e. what the kit scripts produce — upload this at `/codereview/new`).

Schema facts learned from this run (encoded in the golden test):
`findings[i].finding.vuln_class_label` is `null` (ingest falls back to
`vuln_class`); `findings.json` has no tool version — it lives in the
manifest's `version`; `totals.cost_usd` is `null` without a pricing table.
Secret patterns (AWS/OpenRouter/GitHub/Google/Slack keys) grepped: none;
no local paths or usernames leaked. Findings are AI triage candidates
against a deliberately vulnerable training app, not a security assessment
of anything.
