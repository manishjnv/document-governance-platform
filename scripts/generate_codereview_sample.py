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
ScopeWise customer's scan. `acme_run_manifest.json` is a matching synthetic
`run_manifest_*.json` (model roles, token/cost totals).

To try the upload path locally: sign in as an admin/reviewer, go to
Code Security Review > New, and drag in `acme_findings.json` (or
`acme_findings.sarif`) plus, optionally, `acme_run_manifest.json` as the
manifest file.
"""


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    report = build_findings_json()
    (OUT / "acme_findings.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    sarif = build_sarif(report)
    (OUT / "acme_findings.sarif").write_text(json.dumps(sarif, indent=2), encoding="utf-8")

    manifest = build_manifest()
    (OUT / "acme_run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    (OUT / "README.md").write_text(README, encoding="utf-8")

    print(f"Wrote sample set to {OUT}")


if __name__ == "__main__":
    main()
