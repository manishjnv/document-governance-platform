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
