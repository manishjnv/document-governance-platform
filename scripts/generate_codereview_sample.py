"""Generate a synthetic Code Security Review sample set (module reference,
docs/planning/CODE_REVIEW_MODULE_REFERENCE.md sections 2-3).

Writes, deterministically (no randomness), to
docs/sample/CodeReview_Sample/:
  - acme_findings.json     -- a VVAH FinalReport for a fictional Python/
                               FastAPI repo "acme-payments-api"
  - acme_findings.sarif    -- the SARIF 2.1.0 equivalent of the same 12
                               findings
  - acme_run_manifest.json -- a matching run_manifest_*.json
  - README.md

Nothing here resembles real customer data — every name, path, and finding
is invented for this module's tests/demo.

Run from the repo root:

    python scripts/generate_codereview_sample.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs/sample/CodeReview_Sample"

REPO_ROOT = "/work/acme-payments-api"
REPO_NAME = "acme-payments-api"
GIT_SHA = "3f9c2a1"
TOOL_VERSION = "1.3.0"

# (title, severity, vuln_class, vuln_class_label, cwe, cvss_score, cvss_vector,
#  cvss_rating, file, line_start, line_end, confidence, votes, verdict,
#  verdict_confidence, verdict_reason, description, impact, exploit_scenario,
#  preconditions, recommendation, code_snippet, exploitability_notes,
#  verifier_reasoning, offensive_priority, offensive_reason, source_ref,
#  sink_ref, duplicates)
FINDINGS = [
    (
        "SQL injection in payment query builder", "critical", "sql_injection",
        "SQL Injection", "CWE-89", 9.8, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H",
        "CRITICAL", "app/payments/repository.py", 88, 94, 0.95, 2, "TRUE_POSITIVE", 90,
        "Confirmed by tracing the merchant_ref query parameter into a raw SQL string.",
        "User-supplied merchant_ref is string-formatted directly into a raw SQL query "
        "used to look up payment records.",
        "Full compromise of the payments table (read/write), including card-reference "
        "tokens and settlement amounts.",
        "An authenticated merchant sends a crafted merchant_ref (e.g. `' OR '1'='1`) "
        "to /api/payments/search, which is interpolated into the WHERE clause and "
        "returns other merchants' transactions.",
        ["Caller must be able to reach /api/payments/search (any authenticated merchant)."],
        "Use a parameterized query (SQLAlchemy bound parameters) instead of an "
        "f-string; add a regression test asserting the query is never built via "
        "string formatting.",
        'query = f"SELECT * FROM payments WHERE merchant_ref = \'{merchant_ref}\'"',
        "No input validation or allowlisting precedes the query; the exploit path "
        "requires only a valid session, not elevated privileges.",
        "Traced merchant_ref from the FastAPI path operation through to the raw "
        "cursor.execute() call with no sanitization in between.",
        "highest", "Directly reachable by any authenticated user with no additional preconditions.",
        "app/payments/routes.py:41", "app/payments/repository.py:91",
        [],
    ),
    (
        "Hardcoded AWS credentials in settings module", "critical", "hardcoded_secret",
        "Hardcoded Credentials", "CWE-798", 9.1, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:L",
        "CRITICAL", "app/config/settings.py", 22, 23, 0.9, 1, "TRUE_POSITIVE", 85,
        "Key pattern and format match a live AWS access key ID.",
        "A hardcoded AWS access key/secret pair is committed to the settings module "
        "and shipped in every build artifact.",
        "Anyone with repo or artifact access can assume the AWS credentials and "
        "access the S3 buckets and SES sending identity they authorize.",
        "An attacker who obtains the built container image (e.g. from a leaked "
        "internal registry) extracts the key from settings.py and uses it directly "
        "against the AWS API.",
        ["Attacker has read access to the source tree, a build artifact, or a "
         "leaked container image."],
        "Rotate the exposed key immediately, remove it from source control history, "
        "and load credentials from the environment or a secrets manager instead.",
        'AWS_ACCESS_KEY_ID = "AKIA-EXAMPLE-NOT-REAL"\nAWS_SECRET_ACCESS_KEY = "fakeSecretFakeSecretFakeSecretFakeSecret"',
        "Static string in a tracked file — no runtime interaction needed to extract it.",
        "Confirmed the string matches the AKIA prefix format and is read directly "
        "by boto3.client() elsewhere in the module.",
        "highest", "Any party with source or artifact access gets standing AWS credentials.",
        None, None,
        [],
    ),
    (
        "SSRF in webhook URL fetcher", "high", "ssrf",
        "Server-Side Request Forgery", "CWE-918", 8.6, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:L/A:N",
        "HIGH", "app/integrations/webhooks.py", 55, 71, 0.85, 1, "TRUE_POSITIVE", 75,
        "The fetcher follows redirects and has no destination allowlist.",
        "The outbound-webhook test endpoint fetches an arbitrary merchant-supplied "
        "URL server-side with no destination allowlist.",
        "Can be used to reach internal-only services (metadata endpoints, admin "
        "consoles) from the application's network position.",
        "A merchant configures a webhook URL pointing at the cloud metadata "
        "endpoint (169.254.169.254) via the 'test webhook' feature and reads the "
        "response back through the test-result API.",
        ["Merchant-role account needed to reach the webhook test feature."],
        "Resolve and validate the target host against an allowlist (or block "
        "RFC1918/link-local ranges) before issuing the outbound request.",
        "resp = requests.get(webhook_url, timeout=5, allow_redirects=True)",
        "No egress filtering observed in the deployment manifests reviewed.",
        "Verified webhook_url is user-supplied and unfiltered before reaching "
        "requests.get().",
        "high", "Requires only a merchant account, no elevated role.",
        "app/integrations/routes.py:30", "app/integrations/webhooks.py:58",
        [],
    ),
    (
        "JWT signature verification can be bypassed", "high", "broken_auth",
        "Broken Authentication", "CWE-347", 8.1, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N",
        "HIGH", "app/auth/tokens.py", 30, 36, 0.8, 1, "TRUE_POSITIVE", 70,
        "The alg parameter is read from the token header, enabling alg=none.",
        "jwt.decode() is called with algorithms taken from the token's own header "
        "rather than a fixed server-side allowlist, permitting an alg=none token.",
        "An attacker can forge a valid-looking session for any user ID.",
        "An attacker crafts a JWT with header {\"alg\": \"none\"} and an arbitrary "
        "payload, sends it as the bearer token, and is treated as authenticated.",
        ["None — unauthenticated attacker."],
        "Pin the accepted algorithm list to the one the server issues tokens with "
        "(e.g. algorithms=[\"HS256\"]) and reject alg=none explicitly.",
        "payload = jwt.decode(token, key, algorithms=jwt.get_unverified_header(token)[\"alg\"])",
        "No additional network position or credentials required.",
        "Confirmed algorithms= is derived from attacker-controlled input, not a "
        "server-side constant.",
        "highest", "Full authentication bypass, reachable pre-auth.",
        None, None,
        [],
    ),
    (
        "Path traversal in invoice download endpoint", "high", "path_traversal",
        "Path Traversal", "CWE-22", 7.5, "CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:N/A:N",
        "HIGH", "app/invoices/routes.py", 63, 70, 0.82, 1, "TRUE_POSITIVE", 72,
        "The filename query parameter reaches open() with only a naive '..' strip.",
        "The invoice-download endpoint builds a filesystem path from a "
        "user-supplied filename with only a naive '..' string replace, which does "
        "not stop encoded or nested traversal sequences.",
        "Read access to arbitrary files on the API host readable by the service "
        "account.",
        "An authenticated user requests /api/invoices/download?filename=" \
        "..%2f..%2f..%2fetc%2fpasswd and receives the file's contents.",
        ["Any authenticated user account."],
        "Resolve the path with os.path.realpath and verify it stays under the "
        "invoices directory before opening; reject requests that fail the check.",
        'path = os.path.join(INVOICE_DIR, filename.replace("..", ""))',
        "URL-encoding and repeated separators bypass the single-pass replace.",
        "Traced filename from the query string to open() with no realpath/prefix "
        "check in between.",
        "high", "Reachable by any authenticated user.",
        "app/invoices/routes.py:63", "app/invoices/routes.py:69",
        [],
    ),
    (
        "No rate limiting on OTP verification endpoint", "medium", "missing_rate_limit",
        "Missing Rate Limiting", "CWE-799", 5.3, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "MEDIUM", "app/auth/otp.py", 40, 52, 0.7, 1, "TRUE_POSITIVE", 60,
        "No throttle or lockout observed on the verify path.",
        "The OTP verification endpoint has no per-account or per-IP rate limit, "
        "allowing an unbounded number of guesses against a 6-digit code.",
        "Increases the practical odds of a successful OTP brute-force within the "
        "code's validity window.",
        "An attacker scripts repeated POSTs to /api/auth/otp/verify for a known "
        "email, cycling all 10^6 codes before expiry.",
        ["Knowledge of a target email address."],
        "Add a per-account attempt counter with exponential backoff and a hard "
        "cap before requiring a fresh OTP request.",
        "def verify_otp(email: str, code: str): ...  # no attempt tracking",
        "6-digit numeric space is brute-forceable within typical OTP TTLs absent "
        "throttling.",
        "Confirmed no rate-limit decorator or attempt-count check on this route, "
        "unlike /api/auth/login which has one.",
        "medium", "Pre-auth, but requires sustained request volume.",
        None, None,
        [],
    ),
    (
        "Stack traces returned in API error responses", "medium", "info_disclosure",
        "Information Disclosure", "CWE-209", 5.0, "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "MEDIUM", "app/main.py", 18, 27, 0.75, 1, "TRUE_POSITIVE", 65,
        "The debug exception handler is registered unconditionally.",
        "The global exception handler returns the full traceback and local "
        "variable dump in the JSON response body for any unhandled exception.",
        "Discloses internal file paths, library versions, and occasionally "
        "query parameters or partial secrets held in local variables.",
        "An attacker sends a request that triggers an unhandled exception (e.g. "
        "a malformed multipart body) and reads the stack trace from the response.",
        ["None — unauthenticated attacker."],
        "Register the debug traceback handler only when DEBUG=true, and return a "
        "generic 500 body with a correlation ID in production.",
        "app.add_exception_handler(Exception, debug_traceback_handler)",
        "No authentication required to trigger a 500 and read the traceback.",
        "Confirmed debug_traceback_handler is unconditional, not gated on an env "
        "flag.",
        "low", "Aids further exploitation but isn't independently exploitable.",
        None, None,
        [],
    ),
    (
        "CORS allows any origin with credentials", "medium", "insecure_cors",
        "Insecure CORS Configuration", "CWE-942", 4.3, "CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N",
        "MEDIUM", "app/main.py", 33, 39, 0.68, 1, "TRUE_POSITIVE", 55,
        "allow_origins=[\"*\"] paired with allow_credentials=True.",
        "CORSMiddleware is configured with a wildcard origin alongside "
        "allow_credentials=True, which most browsers will reflect as an "
        "always-allowed origin, exposing cookie-authenticated endpoints to any "
        "site.",
        "A malicious site visited by a logged-in user can read authenticated API "
        "responses cross-origin.",
        "A victim with an active session visits an attacker page that issues a "
        "fetch() with credentials: 'include' against the API and reads the JSON "
        "response.",
        ["Victim has an active authenticated session in the same browser."],
        "Replace the wildcard with an explicit allowlist of trusted frontend "
        "origins.",
        'app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True)',
        "Requires a victim to visit an attacker-controlled page while logged in.",
        "Confirmed both allow_origins=\"*\" and allow_credentials=True are set "
        "together, which is the specific insecure combination.",
        "medium", "Needs a logged-in victim to visit a malicious page.",
        None, None,
        [{"file": "app/main.py", "line_start": 33, "line_end": 39}],
    ),
    (
        "Password hashing uses a low bcrypt cost factor", "low", "weak_crypto",
        "Weak Cryptography", "CWE-916", 3.7, "CVSS:3.1/AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:N",
        "LOW", "app/auth/passwords.py", 12, 14, 0.6, 1, "TRUE_POSITIVE", 50,
        "bcrypt.gensalt(rounds=4) is well below the recommended cost factor.",
        "Passwords are hashed with bcrypt at a cost factor of 4, far below the "
        "current recommendation of 12+, making offline brute-force cheaper.",
        "Reduces the cost of cracking a stolen password hash table.",
        "Given a leaked hash table (e.g. via the SQL injection finding above), an "
        "attacker cracks weakly-hashed passwords far faster than at a proper cost "
        "factor.",
        ["Attacker already has the password hash (chained from another finding)."],
        "Raise the bcrypt cost factor to at least 12 and rehash on next login.",
        "salt = bcrypt.gensalt(rounds=4)",
        "Only matters if hashes are already exfiltrated; not independently "
        "reachable.",
        "Confirmed the rounds= literal is 4 versus the library default of 12.",
        "low", "Only relevant after another finding exposes the hash table.",
        None, None,
        [],
    ),
    (
        "Missing HSTS header on API responses", "low", "missing_security_header",
        "Missing Security Header", "CWE-319", 2.6, "CVSS:3.1/AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:N/A:N",
        "LOW", "app/main.py", 44, 44, 0.55, 1, "TRUE_POSITIVE", 45,
        "No Strict-Transport-Security header is set on any response.",
        "The API never sends a Strict-Transport-Security header, so a client's "
        "first plaintext request is not upgraded to HTTPS automatically.",
        "Slightly increases exposure to protocol-downgrade / SSL-stripping "
        "attacks on the first connection.",
        "A user on a hostile network is served a plaintext response before HSTS "
        "would otherwise force HTTPS, giving an on-path attacker one extra window.",
        ["Attacker must be on-path for the victim's first connection."],
        "Add a Strict-Transport-Security response header (e.g. via middleware) "
        "with a sensible max-age.",
        "# no HSTS middleware registered",
        "Only affects the narrow first-connection window; TLS is otherwise "
        "enforced by the load balancer.",
        "Confirmed no HSTS header is present in any response inspected.",
        "low", "Narrow window, on-path attacker only.",
        None, None,
        [{"file": "app/main.py", "line_start": 44, "line_end": 44}],
    ),
    (
        "Dependency with known CVE: requests 2.25.0", "info", "vulnerable_dependency",
        "Vulnerable Dependency", "CWE-1104", None, None,
        None, "requirements.txt", 9, 9, 0.5, 1, None, None,
        "",
        "requirements.txt pins requests==2.25.0, which has a published CVE fixed "
        "in a later 2.x release.",
        "Inherits whatever the upstream CVE allows (varies by advisory).",
        "Not independently exploitable without a code path that exercises the "
        "vulnerable function.",
        [],
        "Bump the pin to the latest 2.x patch release and re-run the dependency "
        "scan.",
        "requests==2.25.0",
        "Informational — flagged by version match against the advisory database, "
        "not by demonstrated exploitation.",
        "Version string matched against the advisory database only.",
        None, "",
        None, None,
        [],
    ),
    (
        "TODO comment references a disabled debug endpoint", "info", "code_hygiene",
        "Code Hygiene", "CWE-489", None, None,
        None, "app/debug/routes.py", 5, 5, 0.4, 1, "FALSE_POSITIVE", 80,
        "The route is registered behind an `if settings.DEBUG` guard that is "
        "False in every deployed environment; not reachable in production.",
        "A TODO comment mentions re-enabling a debug endpoint, but the route "
        "registration itself is already gated behind a DEBUG flag that is off in "
        "all deployed environments.",
        "None in the current deployment configuration.",
        "",
        [],
        "No action required; consider deleting the dead code and comment for "
        "clarity.",
        "# TODO: re-enable /debug/dump-env before demo",
        "Not reachable — confirmed DEBUG=false in every deployment manifest "
        "reviewed.",
        "Verified the guarding conditional evaluates to False in all reviewed "
        "environments.",
        None, "",
        None, None,
        [],
    ),
]

_FIELD_NAMES = [
    "title", "severity", "vuln_class", "vuln_class_label", "cwe", "cvss_score",
    "cvss_vector", "cvss_rating", "file", "line_start", "line_end", "confidence",
    "votes", "verdict", "verdict_confidence", "verdict_reason", "description",
    "impact", "exploit_scenario", "preconditions", "recommendation",
    "code_snippet", "exploitability_notes", "verifier_reasoning",
    "offensive_priority", "offensive_reason", "source_ref", "sink_ref",
    "duplicates",
]

_SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning", "low": "note", "info": "note"}


def _finding_dicts():
    return [dict(zip(_FIELD_NAMES, row)) for row in FINDINGS]


def build_findings_json() -> dict:
    findings = []
    for f in _finding_dicts():
        finding = {k: v for k, v in f.items() if k != "severity" and k != "exploitability_notes"}
        finding["severity"] = f["severity"]
        finding["exploitability_notes"] = f["exploitability_notes"]
        findings.append(
            {
                "finding": finding,
                "severity": f["severity"],
                "exploitability_notes": f["exploitability_notes"],
            }
        )

    chains = [
        {
            "title": "Credential leak to account takeover",
            "steps": [2, 4],
            "severity": "critical",
            "narrative": "The hardcoded AWS credentials (finding 2) grant access to the "
            "deployment's S3 artifact bucket, which contains a build image with the "
            "JWT signing key. Combined with the alg=none bypass (finding 4), an "
            "attacker can forge a session for any account.",
        },
        {
            "title": "Injection to credential exposure",
            "steps": [1, 9],
            "severity": "high",
            "narrative": "The SQL injection (finding 1) exposes the full payments/users "
            "table, including weakly-hashed passwords (finding 9), making offline "
            "cracking of those hashes far cheaper than the cost factor was meant to "
            "guarantee.",
        },
    ]

    dropped = [
        {"file": "tests/test_payments.py", "reason": "test fixture, not application code"},
        {"file": "app/migrations/env.py", "reason": "alembic scaffold, no user input reaches it"},
        {"file": "scripts/seed_dev_db.py", "reason": "dev-only tooling, not part of the deployed service"},
    ]

    return {
        "repo_root": REPO_ROOT,
        "repo_name": REPO_NAME,
        "git_sha": GIT_SHA,
        "tool_version": TOOL_VERSION,
        "summary": (
            "vvaharness scanned acme-payments-api (Python/FastAPI) end to end. Twelve "
            "findings were confirmed across all five severities, including a critical "
            "SQL injection in the payment query builder and hardcoded AWS credentials "
            "in the settings module. Two exploit chains link the credential and "
            "injection findings to broader compromise. One low-confidence finding "
            "(a TODO comment) was verified as a false positive: the referenced route "
            "is dead code behind a disabled debug flag."
        ),
        "degraded": False,
        "degraded_reason": "",
        "findings": findings,
        "chains": chains,
        "dropped": dropped,
        "raw_findings_count": len(findings) + len(dropped),
        "metrics": {
            "duration_sec": 842.5,
            "total_files_in_scope": 118,
            "analyzed_files_unique": 111,
            "loc_scanned_by_language": {"python": 9840, "sql": 240},
            "true_positive_count": 11,
            "false_positive_count": 1,
            "total_tokens": 486213,
        },
    }


def build_sarif(findings_report: dict) -> dict:
    results = []
    for f in _finding_dicts():
        result = {
            "ruleId": f["vuln_class"],
            "level": _SARIF_LEVEL[f["severity"]],
            "message": {"text": f["description"] or f["title"]},
            "properties": {
                "severity": f["severity"],
                "cwe": f["cwe"],
                "cvssScore": f["cvss_score"],
                "cvssVector": f["cvss_vector"],
                "cvssRating": f["cvss_rating"],
                "confidence": f["confidence"],
            },
            "locations": [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": f["file"]},
                        "region": {"startLine": f["line_start"], "endLine": f["line_end"]},
                    }
                }
            ],
        }
        if f["duplicates"]:
            result["relatedLocations"] = [
                {
                    "physicalLocation": {
                        "artifactLocation": {"uri": d["file"]},
                        "region": {"startLine": d["line_start"], "endLine": d["line_end"]},
                    }
                }
                for d in f["duplicates"]
            ]
        results.append(result)

    return {
        "$schema": "https://raw.githubusercontent.com/oasis-tcs/sarif-spec/master/Schemata/sarif-schema-2.1.0.json",
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "vvaharness", "version": TOOL_VERSION}},
                "results": results,
            }
        ],
    }


def build_manifest() -> dict:
    return {
        "tool": "vvaharness",
        "version": TOOL_VERSION,
        "started": "2026-09-10T14:02:11Z",
        "ended": "2026-09-10T14:16:13Z",
        "duration_sec": 842.5,
        "target_git_sha": GIT_SHA,
        "models": {
            "scanner": {"id": "qwen2.5-coder-32b-instruct", "via": "openrouter", "provider": "fireworks"},
            "verifier": {"id": "llama-3.3-70b-instruct", "via": "openrouter", "provider": "together"},
            "reporter": {"id": "qwen2.5-coder-32b-instruct", "via": "openrouter", "provider": "fireworks"},
        },
        "totals": {
            "prompt_tokens": 402118,
            "completion_tokens": 84095,
            "total_tokens": 486213,
            "cost_usd": 1.94,
        },
    }


README = """# Code Security Review sample set

These files are a synthetic scan output for a fictional repo,
"acme-payments-api" (Python/FastAPI). They exist to exercise and demo the
Code Security Review module's upload path (`POST /api/v1/codereview/reviews`)
without needing a real vvaharness run or a real customer's scan results.

Every finding, file path, credential-looking string, and CVSS vector in
`acme_findings.json` / `acme_findings.sarif` is invented for this sample —
none of it resembles or was derived from a real repository or a real
ScopeSense customer's scan. `acme_run_manifest.json` is a matching synthetic
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
"""


# --------------------------------------------------------------------------
# Full-schema fixture: every VVAH 1.3.0 FinalReport/Finding field populated,
# so schema coverage survives without ever re-running a scan. Fictional
# Python/Django repo "acme-billing-portal". See
# apps/api/tests/test_codereview_ingest.py for the pinned field lists this
# fixture is asserted against.
# --------------------------------------------------------------------------

FULL_REPO_ROOT = "/work/acme-billing-portal"
FULL_REPO_NAME = "acme-billing-portal"
FULL_GIT_SHA = "7d1e4b9"

# 8 findings, mixed vuln classes incl. the four the spec calls out by name.
_FULL_FINDINGS = [
    dict(
        title="SQL injection in invoice search filter",
        file="billing/views.py", line_start=88, line_end=93,
        vuln_class="injection", severity="critical",
        cwe="CWE-89", vuln_class_label="SQL Injection",
        chunk_id="chunk-1",
        impact="Full read/write access to the billing database, including "
        "stored card-reference tokens.",
        description="The invoice search view interpolates the `q` query "
        "parameter directly into a raw SQL WHERE clause.",
        exploit_scenario="An authenticated user sends `q=' OR '1'='1` to "
        "/billing/search and receives every tenant's invoices.",
        preconditions=["Caller must reach /billing/search (any authenticated user)."],
        recommendation="Use the ORM's parameterized filter instead of raw SQL.",
        code_snippet='cursor.execute(f"SELECT * FROM invoices WHERE note LIKE \'%{q}%\'")',
        source_ref="billing/views.py:88", sink_ref="billing/db.py:41",
        confidence=0.95, votes=3,
        duplicates=[
            {
                "file": "billing/api/search.py", "line_start": 40, "line_end": 44,
                "vuln_class": "injection", "title": "Same raw-SQL pattern in the API search endpoint",
                "chunk_id": "chunk-2", "source_ref": "billing/api/search.py:40",
                "sink_ref": "billing/db.py:41",
                "reasoning": "Identical string-interpolation call into the same db.py helper.",
            }
        ],
        backfilled_refs=["billing/db.py:41"],
        case_id="vvaf1_0001aaaa",
        exploitability_notes="No input validation precedes the query; reachable by any session.",
        verdict="TRUE_POSITIVE", verdict_confidence=95,
        verdict_reason="Traced q from the view straight into cursor.execute with no sanitization.",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", cvss_score=9.8,
        cvss_rating="CRITICAL",
        verifier_reasoning="Confirmed the WHERE clause is built via an f-string, not a bound parameter.",
        vsvs_vector="VSVS:1.0/AV:N/AC:L/EX:H", vsvs_score=9.5, vsvs_rating="CRITICAL",
        offensive_priority="P1 - exploit now",
        offensive_reason="Directly reachable, no elevated role required, full data exposure.",
    ),
    dict(
        title="Unsafe pickle deserialization of cached report payloads",
        file="billing/reports/cache.py", line_start=51, line_end=55,
        vuln_class="unsafe-deserialization", severity="critical",
        cwe="CWE-502", vuln_class_label="Unsafe Deserialization",
        chunk_id="chunk-3",
        impact="Arbitrary code execution on the worker process that renders reports.",
        description="Cached report payloads are loaded with pickle.loads() from a "
        "Redis key an authenticated user can influence.",
        exploit_scenario="An attacker crafts a malicious pickle, gets it stored under "
        "their own report cache key, then triggers a re-render to execute it.",
        preconditions=["Attacker can write to their own report cache entry."],
        recommendation="Switch to json for the cache payload; never pickle.loads "
        "on anything not fully trusted.",
        code_snippet="payload = pickle.loads(redis_client.get(cache_key))",
        source_ref="billing/reports/cache.py:48", sink_ref="billing/reports/cache.py:51",
        confidence=0.88, votes=2,
        duplicates=[],
        backfilled_refs=["billing/reports/views.py:20"],
        case_id="vvaf1_0002bbbb",
        exploitability_notes="Cache keys are namespaced per user, so the attacker only needs "
        "their own account to control the payload.",
        verdict="TRUE_POSITIVE", verdict_confidence=80,
        verdict_reason="Confirmed pickle.loads is reached with attacker-influenced Redis data.",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H", cvss_score=8.8,
        cvss_rating="HIGH",
        verifier_reasoning="Traced the cache_key back to the report_id path parameter, "
        "which is user-controlled.",
        vsvs_vector="VSVS:1.0/AV:N/AC:L/EX:M", vsvs_score=8.2, vsvs_rating="HIGH",
        offensive_priority="P1 - exploit now",
        offensive_reason="RCE with only a low-privilege account.",
    ),
    dict(
        title="Discount code logic allows unlimited stacking",
        file="billing/discounts.py", line_start=30, line_end=44,
        vuln_class="logic-flaw", severity="high",
        cwe="CWE-840", vuln_class_label="Business Logic Error",
        chunk_id="chunk-4",
        impact="Invoices can be discounted to near-zero by repeating the same code.",
        description="apply_discount() loops over submitted codes without checking "
        "a code was already applied to the same invoice.",
        exploit_scenario="A user submits the same 10%-off code 20 times in one "
        "checkout request and the invoice total drops to a few cents.",
        preconditions=["Any authenticated customer at checkout."],
        recommendation="Track applied codes per invoice and reject duplicates "
        "server-side, not just in the UI.",
        code_snippet="for code in submitted_codes: total = apply_discount(total, code)",
        source_ref="billing/checkout/views.py:15", sink_ref="billing/discounts.py:30",
        confidence=0.82, votes=2,
        duplicates=[],
        backfilled_refs=[],
        case_id="vvaf1_0003cccc",
        exploitability_notes="Server-side loop has no dedup guard; client-side dedup is "
        "trivially bypassed by editing the request body.",
        verdict="TRUE_POSITIVE", verdict_confidence=70,
        verdict_reason="Confirmed no server-side check against already-applied codes.",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:L/UI:N/S:U/C:N/I:H/A:N", cvss_score=6.5,
        cvss_rating="MEDIUM",
        verifier_reasoning="Reproduced the loop mentally against the checkout serializer; "
        "no per-code uniqueness constraint anywhere in the path.",
        vsvs_vector="VSVS:1.0/AV:N/AC:L/EX:L", vsvs_score=5.9, vsvs_rating="MEDIUM",
        offensive_priority="P2 - exploit soon",
        offensive_reason="Direct financial loss but no data exposure or RCE.",
    ),
    dict(
        title="Internal user IDs leaked in invoice PDF metadata",
        file="billing/pdf/render.py", line_start=70, line_end=74,
        vuln_class="info-leak", severity="medium",
        cwe="CWE-200", vuln_class_label="Information Exposure",
        chunk_id="chunk-5",
        impact="Discloses internal numeric user IDs to any recipient of an invoice PDF.",
        description="The PDF author metadata field is set to the raw internal "
        "user.id instead of a display name.",
        exploit_scenario="A customer forwards their invoice PDF; anyone who "
        "inspects its metadata sees the internal user ID, useful for further "
        "enumeration attacks.",
        preconditions=["Access to any generated invoice PDF."],
        recommendation="Set the PDF author field to the tenant's display name, "
        "never the raw internal ID.",
        code_snippet='pdf.set_author(str(user.id))',
        source_ref="billing/pdf/render.py:70", sink_ref="billing/pdf/render.py:70",
        confidence=0.6, votes=1,
        duplicates=[],
        backfilled_refs=[],
        case_id="vvaf1_0004dddd",
        exploitability_notes="Low severity on its own; useful only chained with an "
        "ID-enumeration path elsewhere.",
        verdict="TRUE_POSITIVE", verdict_confidence=55,
        verdict_reason="Confirmed set_author() is called with the raw integer ID.",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:N/A:N", cvss_score=4.3,
        cvss_rating="MEDIUM",
        verifier_reasoning="Inspected the PDF builder call site; no formatting layer "
        "between user.id and set_author.",
        vsvs_vector="VSVS:1.0/AV:N/AC:L/EX:L", vsvs_score=3.8, vsvs_rating="LOW",
        offensive_priority="P3 - exploit if convenient",
        offensive_reason="Only useful as a reconnaissance aid for another attack.",
    ),
    dict(
        title="Race condition in wallet balance deduction",
        file="billing/wallet.py", line_start=18, line_end=27,
        vuln_class="race-condition", severity="high",
        cwe="CWE-362", vuln_class_label="Race Condition",
        chunk_id="chunk-6",
        impact="Concurrent requests can deduct a wallet balance below zero, "
        "letting a customer spend funds they don't have.",
        description="deduct_balance() reads then writes the balance without a "
        "row lock or atomic update, so two concurrent requests both pass the "
        "sufficient-funds check.",
        exploit_scenario="An attacker fires two simultaneous purchase requests "
        "against a wallet with exactly one item's worth of balance; both succeed.",
        preconditions=["Ability to send two concurrent authenticated requests."],
        recommendation="Use `SELECT ... FOR UPDATE` or an atomic `F()` expression "
        "update instead of read-then-write.",
        code_snippet="balance = wallet.balance\nif balance >= amount:\n    wallet.balance = balance - amount\n    wallet.save()",
        source_ref="billing/wallet.py:18", sink_ref="billing/wallet.py:24",
        confidence=0.78, votes=2,
        duplicates=[],
        backfilled_refs=["billing/api/wallet_views.py:12"],
        case_id="vvaf1_0005eeee",
        exploitability_notes="Reliably reproducible by firing two requests within "
        "the same request-handling window.",
        verdict="TRUE_POSITIVE", verdict_confidence=75,
        verdict_reason="Confirmed no row lock or atomic update between read and write.",
        cvss_vector="CVSS:3.1/AV:N/AC:H/PR:L/UI:N/S:U/C:N/I:H/A:N", cvss_score=6.3,
        cvss_rating="MEDIUM",
        verifier_reasoning="Modeled the two-request timing window against the ORM calls; "
        "no locking primitive present.",
        vsvs_vector="VSVS:1.0/AV:N/AC:H/EX:M", vsvs_score=5.5, vsvs_rating="MEDIUM",
        offensive_priority="P2 - exploit soon",
        offensive_reason="Direct financial loss, moderate timing precision required.",
    ),
    dict(
        title="Type confusion in webhook payload amount field",
        file="billing/webhooks/handlers.py", line_start=60, line_end=66,
        vuln_class="type-confusion", severity="medium",
        cwe="CWE-843", vuln_class_label="Type Confusion",
        chunk_id="chunk-7",
        impact="A string amount silently becomes 0 after a failed int() cast is caught.",
        description="The webhook handler casts the vendor-supplied amount field "
        "with `int(amount)` inside a broad try/except that falls back to 0 on "
        "any error, rather than rejecting the payload.",
        exploit_scenario="A malformed webhook amount field of \"free\" is caught "
        "and silently treated as a $0 charge instead of failing the request.",
        preconditions=["Ability to reach the webhook endpoint (signed but replay-checked separately)."],
        recommendation="Reject the payload with a 400 instead of defaulting to "
        "0 when the cast fails.",
        code_snippet="try:\n    amount = int(payload[\"amount\"])\nexcept Exception:\n    amount = 0",
        source_ref="billing/webhooks/handlers.py:60", sink_ref="billing/webhooks/handlers.py:66",
        confidence=0.4, votes=1,
        duplicates=[],
        backfilled_refs=[],
        case_id="vvaf1_0006ffff",
        exploitability_notes="On review, the webhook signature check happens before "
        "this handler runs, and the amount field is server-derived in practice, "
        "not attacker-controlled.",
        verdict="FALSE_POSITIVE", verdict_confidence=65,
        verdict_reason="The upstream signature verification and payload schema check "
        "already reject non-numeric amount fields before this code runs.",
        cvss_vector="CVSS:3.1/AV:N/AC:H/PR:H/UI:N/S:U/C:N/I:L/A:N", cvss_score=3.1,
        cvss_rating="LOW",
        verifier_reasoning="Traced the call chain to webhooks/router.py and found a "
        "pydantic schema that already constrains amount to a positive int.",
        vsvs_vector="VSVS:1.0/AV:N/AC:H/EX:L", vsvs_score=2.4, vsvs_rating="LOW",
        offensive_priority="P4 - not worth pursuing",
        offensive_reason="Upstream validation already closes this path in practice.",
    ),
    dict(
        title="Integer overflow in bulk invoice line-item total",
        file="billing/invoices/totals.py", line_start=12, line_end=16,
        vuln_class="integer-overflow", severity="low",
        cwe="CWE-190", vuln_class_label="Integer Overflow",
        chunk_id="chunk-8",
        impact="A crafted line-item quantity could wrap a fixed-width total in a "
        "downstream export format, though Python ints themselves don't overflow.",
        description="The CSV export path casts the computed total to a C-style "
        "32-bit int for a legacy partner format before writing it out.",
        exploit_scenario="A quantity large enough to push the computed total past "
        "2^31-1 wraps to a negative number in the exported CSV.",
        preconditions=["Ability to create an invoice with an extreme line-item quantity."],
        recommendation="Validate quantity/total against the legacy format's range "
        "before export and reject or clamp instead of silently wrapping.",
        code_snippet="packed_total = struct.pack('i', total)",
        source_ref="billing/invoices/totals.py:12", sink_ref="billing/export/legacy_csv.py:9",
        confidence=0.5, votes=1,
        duplicates=[],
        backfilled_refs=[],
        case_id="vvaf1_0007gggg",
        exploitability_notes="Requires an admin-only bulk-invoice tool to create the "
        "extreme quantity in the first place; not customer-reachable.",
        verdict="FALSE_POSITIVE", verdict_confidence=70,
        verdict_reason="The bulk-invoice tool that could set such a quantity is "
        "admin-only and already has its own range validation.",
        cvss_vector="CVSS:3.1/AV:N/AC:H/PR:H/UI:N/S:U/C:N/I:L/A:N", cvss_score=2.7,
        cvss_rating="LOW",
        verifier_reasoning="Confirmed the only caller of totals.py with attacker-influenced "
        "quantity is gated behind the admin-only bulk import tool's own validator.",
        vsvs_vector="VSVS:1.0/AV:N/AC:H/EX:L", vsvs_score=1.9, vsvs_rating="LOW",
        offensive_priority="P4 - not worth pursuing",
        offensive_reason="Not reachable without admin access that already validates range.",
    ),
    dict(
        title="Dependency with known CVE: Django 4.1.2",
        file="requirements.txt", line_start=3, line_end=3,
        vuln_class="other", severity="info",
        cwe="CWE-1104", vuln_class_label="Vulnerable Dependency",
        chunk_id="chunk-9",
        impact="Inherits whatever the upstream Django advisory allows.",
        description="requirements.txt pins Django==4.1.2, which has a published "
        "CVE fixed in a later 4.1.x release.",
        exploit_scenario="Not independently exploitable without a code path that "
        "exercises the vulnerable Django subsystem.",
        preconditions=["None beyond the dependency being present in the deployed image."],
        recommendation="Bump the pin to the latest patched 4.1.x release.",
        code_snippet="Django==4.1.2",
        source_ref="requirements.txt:3", sink_ref="requirements.txt:3",
        confidence=0.5, votes=1,
        duplicates=[],
        backfilled_refs=[],
        case_id="vvaf1_0008hhhh",
        exploitability_notes="Informational — flagged by version match against the "
        "advisory database, not by demonstrated exploitation.",
        verdict="TRUE_POSITIVE", verdict_confidence=40,
        verdict_reason="Version string matched against the advisory database only.",
        cvss_vector="CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:L", cvss_score=5.0,
        cvss_rating="MEDIUM",
        verifier_reasoning="Confirmed the pinned version string against the public "
        "advisory feed for this package.",
        vsvs_vector="VSVS:1.0/AV:N/AC:L/EX:L", vsvs_score=3.0, vsvs_rating="LOW",
        offensive_priority="P3 - exploit if convenient",
        offensive_reason="Exploitability depends entirely on which CVE is unpatched.",
    ),
]


def build_full_schema_findings_json() -> dict:
    findings = []
    for f in _FULL_FINDINGS:
        finding = dict(f)  # Finding.* — every field above is a real Finding field
        findings.append(
            {
                "finding": finding,
                "severity": f["severity"],
                "exploitability_notes": f["exploitability_notes"],
            }
        )

    chains = [
        {
            "title": "Injection to deserialization RCE",
            "steps": [1, 2],
            "severity": "critical",
            "blocked_by_controls": ["WAF rule blocks common SQLi payloads on /billing/search"],
            "narrative": "The SQL injection (finding 1) exposes cached report keys, "
            "which the unsafe pickle deserialization (finding 2) then executes.",
        },
        {
            "title": "Logic flaw compounds with race condition",
            "steps": [3, 5],
            "severity": "high",
            "blocked_by_controls": [],
            "narrative": "Unlimited discount stacking (finding 3) combined with the "
            "wallet race condition (finding 5) lets an attacker both zero out an "
            "invoice and double-spend the resulting wallet credit.",
        },
        {
            "title": "Info leak aids account enumeration",
            "steps": [4, 1],
            "severity": "medium",
            "blocked_by_controls": ["Rate limiting on /billing/search slows bulk enumeration"],
            "narrative": "The leaked internal user ID (finding 4) gives an attacker a "
            "seed value to target with the SQL injection (finding 1).",
        },
    ]

    dropped = [
        {"file": "billing/legacy/old_search.py", "line": 10, "vuln_class": "injection",
         "title": "String-built query in deprecated search helper", "chunk_id": "chunk-10",
         "reason": "FALSE_POSITIVE", "detail": "Helper is unreachable dead code, never imported.",
         "canonical_idx": 0},
        {"file": "billing/reports/cache.py", "line": 90, "vuln_class": "other",
         "title": "Possible unsafe eval in report template filter", "chunk_id": "chunk-11",
         "reason": "VERIFY_ERROR", "detail": "Verifier LLM call failed after 3 retries; excluded rather than guessed.",
         "canonical_idx": 1},
        {"file": "billing/api/search.py", "line": 40, "vuln_class": "injection",
         "title": "Same raw-SQL pattern in the API search endpoint", "chunk_id": "chunk-2",
         "reason": "DUPLICATE", "detail": "Duplicate of finding 1 (billing/views.py:88); kept as a cross-reference only.",
         "canonical_idx": 0},
        {"file": "billing/tasks/reconcile.py", "line": 22, "vuln_class": "logic-flaw",
         "title": "Reconciliation task may double-count refunds", "chunk_id": "chunk-12",
         "reason": "UNCONFIRMED", "detail": "Scanner flagged a possible double-count but could not construct a concrete trigger.",
         "canonical_idx": 2},
        {"file": "tests/test_billing.py", "line": 5, "vuln_class": "hardcoded_secret",
         "title": "Test fixture contains a fake API key", "chunk_id": "chunk-13",
         "reason": "EXCLUDED", "detail": "Test fixture, not application code, per scan scope rules.",
         "canonical_idx": 3},
        {"file": "billing/admin/bulk_import.py", "line": 77, "vuln_class": "injection",
         "title": "Admin CSV import builds a dynamic query", "chunk_id": "chunk-14",
         "reason": "GUARDRAIL_BLOCKED", "detail": "Finding text tripped the output-safety guardrail and was withheld pending manual review.",
         "canonical_idx": 4},
    ]

    threat_model = {
        "system_context": "acme-billing-portal is a multi-tenant Django billing service "
        "handling invoices, wallets, and payment-provider webhooks.",
        "assets": ["invoice records", "wallet balances", "cached report payloads", "webhook secrets"],
        "trust_boundaries": ["public internet -> Django app", "app -> Postgres", "app -> Redis cache",
                              "payment provider -> webhook endpoint"],
        "threats": ["tenant-boundary bypass via SQL injection", "RCE via cache deserialization",
                    "financial loss via discount/wallet logic flaws"],
        "open_questions": ["Is the webhook endpoint's replay-check window sufficient under load?",
                            "Are report cache keys ever shared across tenants?"],
    }
    app_profile = {
        "application_id": "acme-billing-portal",
        "name": "Acme Billing Portal",
        "externally_facing": True,
        "pci_scoped": True,
        "processes_pan": False,
        "pii": True,
        "source": "manual",
    }

    metrics = {
        "scan_id": "scan-acme-billing-20260912",
        "module_name": "vvaharness-full",
        "start_ts": "2026-09-12T09:00:00Z",
        "end_ts": "2026-09-12T09:22:40Z",
        "duration_sec": 1360.0,
        "total_files_in_scope": 96,
        "analyzed_files_unique": 90,
        "chunks_total": 210,
        "chunks_risk": 60,
        "chunks_catchall": 40,
        "chunks_specialist": 110,
        "chunks_attempted": 205,
        "chunks_failed": 5,
        "errors_by_stage": {"s3_chunking": 2, "s4_verify": 3},
        "errors_log_path": "logs/acme-billing-20260912/errors.log",
        "loc_in_scope_by_language": {"python": 15230, "html": 1200},
        "loc_scanned_by_language": {"python": 14800, "html": 1100},
        "raw_findings_count": 14,
        "true_positive_count": 6,
        "false_positive_count": 2,
        "duplicate_count": 1,
        "prompt_tokens": 610345,
        "completion_tokens": 98211,
        "total_tokens": 708556,
        "tokens_by_phase": {"scan": 420000, "verify": 200000, "report": 88556},
        "folders_scanned": ["billing/", "tests/"],
        "scope": [{"name": "billing", "kind": "app", "files": 80},
                  {"name": "tests", "kind": "tests", "files": 16}],
        "excluded": {"vendor/": "third-party, out of scope", "migrations/": "generated code"},
        "s2_degraded": True,
        "s2_threats_raw": 9,
        "s2_threats_truncated": 1,
        "s2_threats_promoted": 5,
        "s2_baseline_undisposed": ["threat-legacy-search-injection"],
        "s2_repo_kinds": ["web-app", "billing"],
        "s3_output_shape": "cohesion-grouped",
        "s3_unknown_file_ids": ["file-9981"],
        "s3_dropped_paths": ["billing/legacy/__pycache__/old_search.cpython-311.pyc"],
        "s3_relocated_paths": ["billing/old_search.py -> billing/legacy/old_search.py"],
        "s3_dropped_empty_chunks": 3,
        "s3_forced_coverage_files": ["billing/wallet.py"],
        "s3_fallback_chunks_dropped": 1,
        "s3_cohesion_groups": 22,
        "s3_buckets": 6,
        "s4_findings_truncated": False,
        "deepagents_oversize_prompts": 2,
        "llm_truncated_replies": 1,
        "chunks_by_kind": {"risk": 60, "catchall": 40, "specialist": 110},
    }

    return {
        "repo_root": FULL_REPO_ROOT,
        "repo_name": FULL_REPO_NAME,
        "git_sha": FULL_GIT_SHA,
        "summary": (
            "vvaharness scanned acme-billing-portal (Python/Django) end to end. Eight "
            "findings were confirmed or triaged across five vuln classes including SQL "
            "injection, unsafe deserialization, a business-logic flaw, a race condition, "
            "an information leak, a type-confusion false positive, an integer-overflow "
            "false positive, and a known-CVE dependency. The scan degraded partway "
            "through stage 2 threat modeling after a provider timeout."
        ),
        "degraded": True,
        "degraded_reason": "Stage 2 (threat modeling) provider timed out twice; "
        "proceeded with a partial threat model rather than failing the whole scan.",
        "findings": findings,
        "chains": chains,
        "dropped": dropped,
        "raw_findings_count": len(findings) + len(dropped),
        "metrics": metrics,
        "threat_model": threat_model,
        "app_profile": app_profile,
        "unreachable_files": ["billing/legacy/dead_module.py", "scripts/one_off_migration.py"],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    report = build_findings_json()
    (OUT / "acme_findings.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    sarif = build_sarif(report)
    (OUT / "acme_findings.sarif").write_text(json.dumps(sarif, indent=2), encoding="utf-8")

    manifest = build_manifest()
    (OUT / "acme_run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    full_report = build_full_schema_findings_json()
    (OUT / "acme_full_schema.json").write_text(json.dumps(full_report, indent=2), encoding="utf-8")

    (OUT / "README.md").write_text(README, encoding="utf-8")

    print(f"Wrote sample set to {OUT}")


if __name__ == "__main__":
    main()
