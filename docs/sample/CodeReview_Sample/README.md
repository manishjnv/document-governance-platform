# Code Security Review sample set

These files are a synthetic scan output for a fictional repo,
"acme-payments-api" (Python/FastAPI). They exist to exercise and demo the
Code Security Review module's upload path (`POST /api/v1/codereview/reviews`)
without needing a real vvaharness run or a real customer's scan results.

Every finding, file path, credential-looking string, and CVSS vector in
`acme_findings.json` / `acme_findings.sarif` is invented for this sample —
none of it resembles or was derived from a real repository or a real
ScopeWise customer's scan. `acme_run_manifest.json` is a matching synthetic
`run_manifest_*.json` (model roles, token/cost totals).

To try the upload path locally: sign in as an admin/reviewer, go to
Code Security Review > New, and drag in `acme_findings.json` (or
`acme_findings.sarif`) plus, optionally, `acme_run_manifest.json` as the
manifest file.

`acme_full_schema.json` is a separate synthetic fixture for a fictional
"acme-billing-portal" repo whose sole purpose is schema-coverage: every
field on VVAH 1.3.0's `FinalReport` and `Finding` models (per
`vvaharness/models/_scan.py`) is populated with a realistic, non-empty
value across its 8 findings, 3 exploit chains, and 6 dropped entries (one
per drop reason) — fields the real `acme_findings.json`/`nodegoat`
fixtures happen to leave null or empty. It is asserted against in
`apps/api/tests/test_codereview_ingest.py` so a future VVAH schema bump
that adds/renames a field breaks a test here instead of silently being
dropped by ingest.
