"""/codereview/[reviewId] — Review detail: header, review band, tabs (Findings / Exploit
chains / Scan details), finding drawer. Source: inventory §A3-A7. Sample data is the
NodeGoat golden scan (VVAH 1.3.0): 29 findings, 6 chains. The exploit-chain graph is lifted
from docs/design/hero-views-2026-09-12/gen.py's CODE_BODY/CODE_SCRIPT (same finding ids),
restyled onto the calm-light token names (dc.py uses --ink2/--ink3, not hero's --ink-2/-3)."""
from dc import T, app_shell, screen, btn, chip, icon, kebab, tabs, panel, sheet, alert, dth, dcell, kpi, esc

STEM = "CodeReviewDetail"
PAGE, TITLE, ORDER = "code", "Code security review · detail", 30

# --------------------------------------------------------------------------- sample data
REVIEW = {"id": "r1", "name": "NodeGoat golden scan (VVAH 1.3.0)", "repo": "target-nodegoat", "sha": "c5cb68a",
          "fullSha": "c5cb68a7084e4ae7dcc60e6a98768720a81841e8", "date": "Sep 12, 2026, 02:25", "demo": True,
          "fmt": "findings.json", "degraded_reason": "Model provider rate-limited during stage s7; findings after that stage may be missing."}

# each: id, sev, title, cls, cwe, cvss, vector, conf, votes, verdict, reason, file, l1, l2, source, sink,
#       wrong, why, fix, exploited, precon[], code[], exploitability, vreason, alsoat[]
FINDINGS = [
 dict(id=3, sev="Critical", title="NoSQL injection in login", cls="Injection", cwe="CWE-943", cvss=9.8,
  vector="AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", conf=92, votes=4, verdict="confirmed",
  reason="Reproduced: an object payload in the username field bypasses the password check.",
  file="app/data/user-dao.js", l1=88, l2=96, source="req.body.userName (login form)", sink="MongoDB $where-style query in User.findOne",
  wrong="The login query builds a MongoDB filter directly from the request body, so a JSON object where a string was expected changes the query's logic instead of its data.",
  why="An attacker signs in as any user, including admin, without knowing a password.",
  fix="Coerce username/password to strings before querying, and reject non-scalar body fields at the validation layer.",
  exploited="Attacker posts {\"userName\":{\"$ne\":null},\"password\":{\"$ne\":null}} to /login and the query matches the first user in the collection.",
  precon=["Login endpoint reachable without prior authentication.", "MongoDB driver accepts nested objects from an unvalidated body."],
  code=["User.findOne({", "  userName: req.body.userName,", "  password: req.body.password", "}, function(err, user) {"],
  exploitability="Low effort, no tooling beyond a browser or curl; the payload is a one-line JSON body.",
  vreason="Replayed the payload against the staging login route and obtained an authenticated session cookie for the seeded admin account.",
  alsoat=["app/routes/contributions.js:22 (same unguarded findOne pattern)"]),
 dict(id=4, sev="Critical", title="Hardcoded session secret", cls="Broken Authentication", cwe="CWE-798", cvss=9.1,
  vector=None, conf=88, votes=3, verdict="confirmed", reason="The literal secret is present verbatim in the shipped config file.",
  file="config/env/all.js", l1=6, l2=9, source="config/env/all.js (checked-in source)", sink="express-session cookie signing key",
  wrong="The session-signing secret is a fixed string committed to the repository instead of coming from an environment variable or secret store.",
  why="Anyone with read access to the source (or the public repo history) can forge valid session cookies for any user.",
  fix="Move the secret to an environment variable injected at deploy time, and rotate the leaked value.",
  exploited="Attacker reads the secret from source control, then signs a cookie claiming an arbitrary userId and session, bypassing login entirely.",
  precon=["Repository or deployed bundle is readable by the attacker.", "Server does not rotate the signing secret."],
  code=["module.exports = {", "  session: { secret: 'keyboardcat' }", "};"],
  exploitability="Trivial once the secret is known; standard cookie-signing libraries do the rest.",
  vreason="Located the exact string in config/env/all.js and confirmed it matches the cookie signature on a live session.",
  alsoat=["config/env/development.js:9 (same fallback constant)"]),
 dict(id=5, sev="Critical", title="No rate limit on login", cls="Broken Authentication", cwe="CWE-307", cvss=9.0,
  vector=None, conf=81, votes=3, verdict="confirmed", reason="Load-tested 500 sequential attempts from one IP with no lockout or backoff.",
  file="app/routes/session.js", l1=53, l2=58, source="POST /login request loop", sink="Password comparison in the login handler",
  wrong="The login route has no attempt counter, lockout or backoff, so credentials can be brute-forced as fast as the network allows.",
  why="Combined with weak or reused passwords, this gives an attacker a practical path into any account.",
  fix="Add per-account and per-IP rate limiting (a sliding window) and a short lockout after repeated failures.",
  exploited="A credential-stuffing script tries thousands of passwords per minute against the same username with no pushback from the server.",
  precon=["Login endpoint has no WAF or reverse-proxy throttling in front of it."],
  code=["router.post('/login', function(req, res) {", "  User.findOne({ userName: req.body.userName }, ...)"],
  exploitability="Commodity credential-stuffing tooling handles this out of the box.",
  vreason="Confirmed 500 consecutive failed attempts returned identical timing and no 429 or lockout response.",
  alsoat=["app/routes/session.js:100 (password reset has the same gap)"]),
 dict(id=1, sev="Critical", title="Unauthenticated MongoDB", cls="Security Misconfiguration", cwe="CWE-306", cvss=9.8,
  vector="AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", conf=95, votes=4, verdict="confirmed",
  reason="Connected to the exposed port with no credentials and listed all collections.",
  file="docker-compose.yml", l1=6, l2=10, source="Public network interface, port 27017", sink="MongoDB data directory (all collections)",
  wrong="The database container publishes its port to the host network with authentication disabled, so anyone who can reach the port has full read/write access.",
  why="Complete compromise of user, session and financial data with no exploit required beyond a network connection.",
  fix="Bind MongoDB to a private network only, enable authentication, and require a connection string with credentials.",
  exploited="Attacker runs a plain mongo client against <host>:27017 from outside and dumps the users collection directly.",
  precon=["Port 27017 reachable from outside the deployment network."],
  code=["  mongodb:", "    image: mongo", "    ports:", "      - \"27017:27017\""],
  exploitability="No authentication to bypass; a standard MongoDB client is sufficient.",
  vreason="Connected with the mongo shell from an unauthenticated network path and ran show dbs successfully.",
  alsoat=["docker-compose.prod.yml:11 (same port mapping)"]),
 dict(id=9, sev="High", title="Authenticated SSRF", cls="Server-Side Request Forgery", cwe="CWE-918", cvss=8.2,
  vector=None, conf=81, votes=3, verdict="confirmed", reason="Fetched an internal-only URL and the response was reflected back to the client.",
  file="app/routes/research.js", l1=14, l2=14, source="req.query.url (research lookup form)", sink="Outbound HTTP request made by the server",
  wrong="The research endpoint fetches whatever URL a signed-in user supplies and returns the response, with no allowlist of destinations.",
  why="An authenticated attacker can use the server as a proxy to reach internal-only services, including the exposed MongoDB port and cloud metadata endpoints.",
  fix="Allowlist outbound destinations (or resolve and block private/internal IP ranges) before making the request.",
  exploited="Attacker submits a query string pointing at the cloud metadata endpoint and the server fetches and returns it.",
  precon=["Attacker holds any authenticated session.", "Outbound network access from the app server to internal ranges is not firewalled."],
  code=["router.get('/research', function(req, res) {", "  request(req.query.url, function(err, r, body) {", "    res.send(body);"],
  exploitability="Requires only a valid login and a crafted query string.",
  vreason="Requested an internal-only test endpoint through the feature and confirmed the response was echoed back.", alsoat=[]),
 dict(id=7, sev="High", title="Eval injection (RCE)", cls="Injection", cwe="CWE-95", cvss=8.8,
  vector="AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H", conf=85, votes=4, verdict="confirmed",
  reason="A crafted payload executed arbitrary Node.js code on the server.",
  file="app/routes/index.js", l1=50, l2=50, source="A memo or contribution field rendered through the benefits calculator", sink="eval() of attacker-influenced input",
  wrong="User-controlled input reaches a JavaScript eval() call used to compute a benefits calculation, so it is executed as code rather than treated as data.",
  why="Any attacker who can reach the calculation feature gets arbitrary code execution on the application server.",
  fix="Remove eval() entirely; replace the calculation with a fixed arithmetic expression or a safe expression parser with no code-execution path.",
  exploited="Attacker submits a payload that closes the expression and appends a shell command, which the server then runs.",
  precon=["The vulnerable calculation endpoint is reachable by the attacker's session tier."],
  code=["var total = eval(req.body.contribution + ' + ' + match);", "res.send(String(total));"],
  exploitability="Well-understood technique; public NodeGoat write-ups already document this exact payload.",
  vreason="Ran a harmless proof-of-concept command via the payload and observed its output reflected in the response.",
  alsoat=["app/routes/contributions.js:48 (same calculation helper reused)"]),
 dict(id=24, sev="Medium", title="Username enumeration", cls="Broken Authentication", cwe="CWE-203", cvss=5.3,
  vector=None, conf=74, votes=3, verdict="unverified", reason=None,
  file="app/routes/session.js", l1=53, l2=58, source="Login error response", sink="HTTP response body/status",
  wrong="The login route returns a different error message (and sometimes status code) for an unknown username than for a wrong password.",
  why="An attacker can build a list of valid usernames before attempting credential stuffing or phishing.",
  fix="Return the same generic message and status for both an unknown user and a wrong password.",
  exploited="Attacker scripts logins across a username wordlist and separates 'no such user' from 'wrong password' responses.",
  precon=["Login endpoint has no per-IP throttling to slow the enumeration."],
  code=["if (!user) return res.status(401).send('No such user');", "if (!valid) return res.status(401).send('Wrong password');"],
  exploitability="Simple scripted timing/response-diff check; no special tooling required.",
  vreason="Flagged for a second pass: the response difference is present but low-impact on its own without the missing rate limit.",
  alsoat=["app/routes/session.js:33 (registration has a similar tell)"]),
 dict(id=21, sev="Medium", title="Outdated marked (XSS)", cls="Cross-Site Scripting (XSS)", cwe="CWE-79", cvss=6.1,
  vector=None, conf=68, votes=3, verdict="unverified", reason=None,
  file="package.json", l1=1, l2=1, source="User-authored memo body (Markdown)", sink="marked() output inserted into the page without sanitisation",
  wrong="The pinned marked version predates fixes for several Markdown-to-HTML sanitisation bugs, and its output is rendered without an additional sanitiser.",
  why="A memo author can smuggle a script tag through Markdown that other users, including admins, will execute when they view the memo.",
  fix="Upgrade marked to a patched release and run its output through a sanitiser (e.g. DOMPurify) before inserting it into the DOM.",
  exploited="Attacker writes a memo containing a crafted Markdown construct that the outdated parser turns into an executable script payload.",
  precon=["Attacker can create or edit a memo.", "A victim with a more privileged session views that memo."],
  code=["\"marked\": \"0.3.6\""],
  exploitability="Depends on finding a still-working bypass for this specific old version; moderate effort.",
  vreason="Dependency confirmed outdated by version compare; did not reproduce a working payload in the time available, so left unverified pending a deep-dive.",
  alsoat=[]),
 dict(id=22, sev="Medium", title="Cookie lacks httpOnly", cls="Sensitive Data Exposure", cwe="CWE-1004", cvss=5.4,
  vector=None, conf=77, votes=3, verdict="confirmed", reason="Inspected the Set-Cookie header in a live response; the flag is absent.",
  file="server.js", l1=58, l2=62, source="Session cookie configuration", sink="document.cookie (any script running on the page)",
  wrong="The session cookie is issued without the HttpOnly flag, so client-side JavaScript can read it.",
  why="Combined with the outdated-marked XSS finding, an attacker can steal session cookies and hijack accounts.",
  fix="Set httpOnly: true (and secure, sameSite) on the session cookie configuration.",
  exploited="An injected script runs document.cookie and exfiltrates the session id to an attacker-controlled endpoint.",
  precon=["A script-injection point (e.g. the marked/XSS finding) exists elsewhere on the same origin."],
  code=["app.use(session({", "  secret: cookieSecret,", "  cookie: { httpOnly: false }", "}));"],
  exploitability="Trivial once any script-injection point exists on the same origin.",
  vreason="Confirmed the Set-Cookie header directly in the browser network panel.",
  alsoat=["server.js:75 (remember-me cookie has the same gap)"]),
 dict(id=2, sev="Critical", title="Weak password hashing (unsalted MD5)", cls="Broken Authentication", cwe="CWE-916", cvss=8.6,
  vector=None, conf=83, votes=3, verdict="confirmed", reason="Recovered a seeded test password from its stored hash in under a second.",
  file="app/data/user-dao.js", l1=45, l2=52, source="User.password at signup/login", sink="MD5 digest stored in MongoDB",
  wrong="Passwords are hashed with a single unsalted MD5 pass instead of a slow, salted algorithm.",
  why="A stolen user collection can be cracked at billions of guesses per second with commodity GPUs.",
  fix="Rehash with bcrypt/argon2 (unique salt per user, high work factor) and migrate existing hashes on next login.",
  exploited="Attacker who obtains the collection runs it through a rainbow table or GPU cracker in minutes.",
  precon=["Attacker has read access to the user collection (e.g. via the unauthenticated MongoDB finding)."],
  code=["var hash = crypto.createHash('md5').update(password).digest('hex');"],
  exploitability="Commodity GPU cracking rigs make this fast for common passwords.",
  vreason="Cracked a known seeded password from its hash using a standard wordlist in under a second.", alsoat=[]),
 dict(id=6, sev="Critical", title="Directory traversal in profile image upload", cls="Path Traversal", cwe="CWE-22", cvss=9.1,
  vector=None, conf=79, votes=3, verdict="confirmed", reason="Wrote a file outside the intended uploads directory using a crafted filename.",
  file="app/routes/profile.js", l1=74, l2=80, source="Uploaded file's original filename field", sink="fs.writeFile path built from that filename",
  wrong="The profile image upload path is built by concatenating the uploads directory with the client-supplied filename, without stripping traversal segments.",
  why="An attacker can write files to arbitrary locations the server process can reach, up to overwriting application code.",
  fix="Generate the stored filename server-side (e.g. a UUID) and never derive a filesystem path from client input.",
  exploited="Attacker uploads a file whose name walks out of the uploads directory to overwrite application code.",
  precon=["Upload endpoint accepts arbitrary filenames.", "The app server's process has write access to its own source tree."],
  code=["var dest = path.join(UPLOAD_DIR, req.file.originalname);", "fs.writeFile(dest, req.file.buffer, cb);"],
  exploitability="Requires only a normal authenticated upload with a crafted filename.",
  vreason="Uploaded a traversal filename in staging and confirmed the file landed outside the uploads directory.", alsoat=[]),
 dict(id=8, sev="High", title="IDOR on allocations endpoint", cls="Broken Access Control", cwe="CWE-639", cvss=7.5,
  vector=None, conf=80, votes=3, verdict="confirmed", reason="Fetched another user's allocation by changing the id in the URL; no ownership check triggered.",
  file="app/routes/allocations.js", l1=20, l2=26, source="req.params.userId in the allocations URL", sink="Allocation lookup with no ownership check",
  wrong="The allocations page loads whatever user id is in the URL without confirming it belongs to the requesting session.",
  why="Any signed-in user can view (and on some routes edit) another user's benefit allocations.",
  fix="Check the record's owner against the session's own user id before returning it.",
  exploited="Attacker changes the numeric id in the allocations URL to walk through other users' data.",
  precon=["Attacker holds any authenticated session.", "Allocation ids are sequential or guessable."],
  code=["Allocations.findOne({ userId: req.params.userId }, cb);"],
  exploitability="Simple URL parameter change; no special tooling needed.",
  vreason="Requested a second seeded account's allocation id while logged in as a different user and received its data.",
  alsoat=["app/routes/memos.js:41 (same missing ownership check)"]),
 dict(id=10, sev="High", title="Reflected XSS in search parameter", cls="Cross-Site Scripting (XSS)", cwe="CWE-79", cvss=7.2,
  vector=None, conf=70, votes=3, verdict="false_positive", reason="The template engine's default auto-escaping neutralised every payload variant tried.",
  file="app/routes/contributions.js", l1=30, l2=36, source="req.query.q (contribution search box)", sink="Search term echoed into the results page",
  wrong="The search term appears to be written back into the page without an explicit encoding call in the route handler.",
  why="If unescaped, an attacker could run script in a victim's session via a shared link.",
  fix="No action required beyond keeping the view layer's auto-escaping enabled; add a regression test pinning this behaviour.",
  exploited="Not reproducible: the verifier could not get a payload to execute.",
  precon=["Would require the view layer's default escaping to be disabled."],
  code=["res.send('<p>Results for ' + req.query.q + '</p>');"], exploitability="Not applicable: recorded as a false positive.",
  vreason="Tried four standard XSS payloads against the live route; the view layer's default escaping rendered all of them inert.", alsoat=[]),
 dict(id=11, sev="High", title="Server-side template injection in memo renderer", cls="Injection", cwe="CWE-1336", cvss=8.1,
  vector=None, conf=76, votes=3, verdict="confirmed", reason="A template-syntax payload in a memo title executed server-side during rendering.",
  file="app/routes/memos.js", l1=16, l2=22, source="Memo title field", sink="Server-side template compile/render step",
  wrong="Memo titles are passed into the template engine's render step rather than treated as plain data, so template syntax in a title is compiled and executed.",
  why="An attacker can run arbitrary logic (and in some engines arbitrary code) on the server just by saving a memo.",
  fix="Never compile user input as a template; pass it only as template data (a variable), never as template source.",
  exploited="Attacker saves a memo titled with the engine's template-injection syntax and the server evaluates it on render.",
  precon=["Attacker can create or edit a memo."],
  code=["var tpl = memo.title + ' - ' + memo.body;", "res.send(swig.render(tpl, {}));"],
  exploitability="Requires knowing the specific template engine's syntax; moderate effort.",
  vreason="Confirmed server-side evaluation using a benign arithmetic template payload that returned a computed value.", alsoat=[]),
 dict(id=12, sev="Medium", title="Missing CSRF token on fund transfer", cls="CSRF", cwe="CWE-352", cvss=6.5,
  vector=None, conf=72, votes=3, verdict="confirmed", reason="Submitted the transfer form cross-origin with no token and it succeeded.",
  file="app/routes/contributions.js", l1=58, l2=64, source="Cross-site auto-submitting form on an attacker page", sink="Fund allocation POST handler",
  wrong="The fund-allocation form has no CSRF token, and the session cookie has no SameSite restriction.",
  why="Visiting a malicious page while logged in can silently reallocate the victim's funds.",
  fix="Add a per-session CSRF token to the form and verify it server-side; set the session cookie's SameSite to Lax or Strict.",
  exploited="Attacker hosts an auto-submitting form pointed at the transfer endpoint; a logged-in victim who opens the page triggers the transfer.",
  precon=["Victim has an active session and visits the attacker's page."],
  code=["router.post('/allocations', function(req, res) { /* no csrf check */ });"],
  exploitability="Well-known technique; only needs a victim to load a page.",
  vreason="Hosted the payload on a test origin and confirmed the transfer executed without the token.", alsoat=[]),
 dict(id=13, sev="Medium", title="Verbose stack trace on 500 errors", cls="Information Exposure", cwe="CWE-209", cvss=5.3,
  vector=None, conf=88, votes=3, verdict="confirmed", reason="Triggered a 500 and received a full stack trace with file paths.",
  file="server.js", l1=108, l2=114, source="Any unhandled route exception", sink="Error page rendered to the client",
  wrong="The default Express error handler is left in development mode, so unhandled exceptions return full stack traces to the client.",
  why="Stack traces reveal file paths, dependency versions and internal logic that help an attacker plan further attacks.",
  fix="Set NODE_ENV=production and use a generic error handler that logs details server-side only.",
  exploited="Attacker sends a malformed request that triggers an exception and reads the returned trace.",
  precon=["An input exists that reaches an unhandled exception path."],
  code=["app.use(function(err, req, res, next) {", "  res.status(500).send(err.stack);", "});"],
  exploitability="Trivial; any crash-inducing input works.",
  vreason="Sent a known malformed request and received a full trace including absolute file paths.", alsoat=[]),
 dict(id=14, sev="Medium", title="Insecure direct object reference on memo id", cls="Broken Access Control", cwe="CWE-639", cvss=6.5,
  vector=None, conf=75, votes=3, verdict="confirmed", reason="Read another user's private memo by incrementing the id.",
  file="app/routes/memos.js", l1=38, l2=44, source="req.params.id on the memo detail route", sink="Memo lookup with no ownership check",
  wrong="Memo detail lookups trust the id in the URL without checking the memo belongs to the requesting user.",
  why="Any user can read (and on some deployments edit) any other user's memos by walking sequential ids.",
  fix="Scope the query to the session's own userId, or check ownership after fetch and 404 on mismatch.",
  exploited="Attacker increments the memo id in the URL and reads memos that belong to other accounts.",
  precon=["Memo ids are sequential or otherwise guessable."],
  code=["Memos.findOne({ _id: req.params.id }, cb);"], exploitability="Trivial URL-parameter walk.",
  vreason="Read a second seeded account's memo while authenticated as a different account.",
  alsoat=["app/routes/allocations.js:22 (same pattern)"]),
 dict(id=15, sev="Medium", title="Missing security headers (no CSP)", cls="Security Misconfiguration", cwe="CWE-693", cvss=4.8,
  vector=None, conf=66, votes=3, verdict="false_positive",
  reason="A CSP is in fact set by the upstream reverse proxy in the deployed environment; the app-level absence is compensated.",
  file="server.js", l1=20, l2=24, source="Not applicable: configuration finding", sink="Not applicable: configuration finding",
  wrong="The Express app itself sets no Content-Security-Policy header.",
  why="Without a CSP, a successful script-injection finding elsewhere has a larger blast radius.",
  fix="No action required in the app; keep the reverse-proxy CSP documented so it is not accidentally removed.",
  exploited="Mitigated upstream; recorded as a false positive at the application layer.",
  precon=["Would require the reverse-proxy CSP to be removed or bypassed."],
  code=["app.use(helmet({ contentSecurityPolicy: false }));"], exploitability="Not applicable: recorded as a false positive.",
  vreason="Confirmed the deployed edge proxy adds a CSP header before requests reach this app, so the app-level gap has no practical effect today.", alsoat=[]),
 dict(id=16, sev="Medium", title="Outdated lodash dependency (prototype pollution)", cls="Vulnerable Dependency", cwe="CWE-1321", cvss=6.5,
  vector=None, conf=60, votes=2, verdict="unverified", reason=None,
  file="package.json", l1=1, l2=1, source="Any object-merge call using the pinned lodash version", sink="Object prototype",
  wrong="The pinned lodash release predates a fix for a prototype-pollution issue in its merge/set helpers.",
  why="If reachable with attacker-controlled keys, this can lead to denial of service or, in some call sites, privilege escalation.",
  fix="Upgrade lodash to a patched release and audit merge/set call sites for attacker-controlled keys.",
  exploited="Attacker supplies a proto-polluting key to a merge call that uses the vulnerable helper.",
  precon=["A reachable call site passes attacker-controlled keys into the affected helper."],
  code=["\"lodash\": \"3.10.1\""], exploitability="Depends on finding a reachable call site; not yet demonstrated in this app.",
  vreason="Version confirmed vulnerable by advisory lookup; no reachable exploitable call site found in the time available, left unverified.", alsoat=[]),
 dict(id=17, sev="Medium", title="Session fixation on login", cls="Broken Authentication", cwe="CWE-384", cvss=6.1,
  vector=None, conf=65, votes=2, verdict="unverified", reason=None,
  file="app/routes/session.js", l1=38, l2=44, source="Pre-login session id set by the server", sink="Session id reused after successful login",
  wrong="The session id issued before login does not appear to be regenerated after a successful login.",
  why="An attacker who can plant a known session id in a victim's browser may be able to reuse it after the victim logs in.",
  fix="Call the session store's regenerate method immediately after successful authentication.",
  exploited="Attacker sends a victim a link carrying a pre-set session id; if the victim logs in, the attacker's copy of that id becomes authenticated.",
  precon=["Attacker can set a session cookie in the victim's browser before login (e.g. via a shared network or subdomain)."],
  code=["req.session.userId = user._id;", "res.redirect('/dashboard');"],
  exploitability="Needs a way to plant the pre-login session id in the victim's browser; moderate effort.",
  vreason="Reviewed the login handler and did not find a regenerate call; did not complete a live victim-session reproduction, left unverified.", alsoat=[]),
 dict(id=18, sev="Medium", title="Cleartext transmission of credentials (no HSTS)", cls="Sensitive Data Exposure", cwe="CWE-319", cvss=5.9,
  vector=None, conf=70, votes=3, verdict="false_positive",
  reason="The deployed load balancer terminates TLS and enforces HSTS; the app-level header is redundant, not missing protection.",
  file="server.js", l1=25, l2=28, source="Not applicable: configuration finding", sink="Not applicable: configuration finding",
  wrong="The Express app does not itself set the Strict-Transport-Security header.",
  why="Without HSTS, a user's first visit over plain HTTP could be downgraded by a network attacker.",
  fix="No app change required; keep HSTS enforced at the load balancer and add the header at the app layer for defence in depth.",
  exploited="Mitigated upstream; recorded as a false positive.", precon=["Would require the load balancer's HSTS enforcement to be removed."],
  code=["app.use(helmet({ hsts: false }));"], exploitability="Not applicable: recorded as a false positive.",
  vreason="Confirmed the production load balancer already enforces HSTS ahead of this app, so the gap has no practical effect today.", alsoat=[]),
 dict(id=19, sev="Medium", title="Open redirect on returnTo parameter", cls="Unvalidated Redirect", cwe="CWE-601", cvss=5.4,
  vector=None, conf=73, votes=3, verdict="confirmed", reason="A crafted returnTo value redirected to an external domain after login.",
  file="app/routes/session.js", l1=66, l2=70, source="req.query.returnTo on the login route", sink="res.redirect() destination",
  wrong="After login, the app redirects to whatever returnTo URL was supplied, without checking it stays on the same origin.",
  why="Attackers can craft a trusted-looking ScopeWise-domain link that redirects victims to a phishing site right after they log in.",
  fix="Only allow relative paths (or an explicit allowlist of hosts) for returnTo.",
  exploited="Attacker sends a login link whose returnTo points off-site, and the victim lands there straight after authenticating.",
  precon=["Victim clicks a crafted login link."], code=["res.redirect(req.query.returnTo || '/dashboard');"],
  exploitability="Trivial; only needs a crafted link and a victim click.",
  vreason="Followed a crafted returnTo link through login and landed on the external test domain.", alsoat=[]),
 dict(id=20, sev="Medium", title="Predictable password reset token", cls="Broken Authentication", cwe="CWE-330", cvss=6.8,
  vector=None, conf=62, votes=2, verdict="unverified", reason=None,
  file="app/routes/session.js", l1=92, l2=98, source="Reset token generation for a given account", sink="Password reset confirmation route",
  wrong="The password reset token appears to be derived from the current timestamp rather than a cryptographically random source.",
  why="If predictable, an attacker could guess or narrow down a valid reset token for a target account without needing their inbox.",
  fix="Generate reset tokens with a CSPRNG, sufficiently long, and invalidate them after first use or a short expiry.",
  exploited="Attacker requests a reset for a target account, then brute-forces the narrow timestamp-derived token space.",
  precon=["Attacker knows roughly when the victim's reset was requested."], code=["var token = Date.now().toString(36);"],
  exploitability="Feasible but requires narrowing the timestamp window; moderate effort.",
  vreason="Generation logic reviewed and looks timestamp-derived; did not complete a full brute-force reproduction, left unverified.", alsoat=[]),
 dict(id=23, sev="Medium", title="Mass assignment on profile update", cls="Improper Input Validation", cwe="CWE-915", cvss=6.3,
  vector=None, conf=71, votes=3, verdict="confirmed", reason="Set an admin-style field through the profile form that the UI never exposes.",
  file="app/routes/profile.js", l1=30, l2=36, source="Full req.body on the profile update form", sink="User document update (all fields)",
  wrong="The profile update handler writes the entire request body onto the user document instead of an explicit allowlist of editable fields.",
  why="A user can add or change fields the form never shows, potentially including privilege flags.",
  fix="Update only an explicit allowlist of fields from the body.",
  exploited="Attacker adds an extra field to the profile update POST body that the server was not meant to let them set.",
  precon=["Attacker holds any authenticated session and can submit a raw HTTP request."],
  code=["User.update({ _id: req.session.userId }, req.body, cb);"], exploitability="Simple request-body edit with any HTTP client.",
  vreason="Added an out-of-form field to a live update request and confirmed it was persisted.", alsoat=[]),
 dict(id=25, sev="Medium", title="Insecure randomness for allocation IDs", cls="Insufficient Entropy", cwe="CWE-330", cvss=4.9,
  vector=None, conf=58, votes=2, verdict="unverified", reason=None,
  file="app/data/allocations-dao.js", l1=16, l2=20, source="Allocation id generation", sink="Allocation lookup URL",
  wrong="Allocation ids appear to be generated from a simple incrementing counter rather than an opaque identifier.",
  why="Sequential, guessable ids make the related IDOR finding easier to exploit at scale.",
  fix="Use an opaque, non-sequential identifier (e.g. a UUID) for anything referenced in a URL.",
  exploited="Attacker enumerates allocation ids sequentially to pair with the IDOR finding on the same endpoint.",
  precon=["The IDOR finding on the same endpoint is also present."], code=["var nextId = lastId + 1;"],
  exploitability="Trivial once combined with the missing ownership check.",
  vreason="Confirmed ids increment sequentially across several test records; did not independently score impact beyond the paired IDOR finding.",
  alsoat=["app/routes/allocations.js:22"]),
 dict(id=26, sev="Medium", title="Excessive data exposure in API response", cls="Information Exposure", cwe="CWE-213", cvss=5.7,
  vector=None, conf=69, votes=3, verdict="false_positive", reason="The extra fields returned are already public read-only reference data, not sensitive.",
  file="app/routes/contributions.js", l1=76, l2=82, source="Not applicable: response-shape finding", sink="Not applicable: response-shape finding",
  wrong="The contributions API returns full internal documents rather than a shaped response for the fields the UI actually uses.",
  why="Over-broad responses can leak fields that later become sensitive as the schema grows, even if today's fields are benign.",
  fix="No urgent action; consider shaping the response to the fields the client needs as a defensive-coding improvement.",
  exploited="Reviewed fields are public reference data (fund names, allocation percentages); recorded as a false positive.",
  precon=["Would require a currently-benign field to later hold sensitive data."], code=["res.json(contribution);"],
  exploitability="Not applicable: recorded as a false positive.",
  vreason="Inspected every extra field in the response and confirmed each is already shown elsewhere in the public UI.", alsoat=[]),
 dict(id=27, sev="Medium", title="Missing rate limit on fund transfer", cls="Broken Access Control", cwe="CWE-307", cvss=5.6,
  vector=None, conf=67, votes=2, verdict="confirmed", reason="Repeated 200 rapid transfer requests with no throttling or anomaly response.",
  file="app/routes/contributions.js", l1=68, l2=72, source="POST /allocations request loop", sink="Fund allocation handler",
  wrong="The fund-allocation endpoint accepts repeated requests with no rate limiting or anomaly detection.",
  why="Combined with the CSRF gap, this allows rapid repeated reallocation attempts with no server-side pushback.",
  fix="Add rate limiting to state-changing financial endpoints and alert on unusual request volume per account.",
  exploited="A scripted client fires allocation changes far faster than a human could, with no server-side pushback.",
  precon=["Attacker has valid or forged session access to the endpoint."],
  code=["router.post('/allocations', function(req, res) { /* no throttle */ });"], exploitability="Simple scripted request loop.",
  vreason="Sent 200 rapid requests in staging with no lockout, delay or error response.", alsoat=[]),
 dict(id=28, sev="Medium", title="Clickjacking (no X-Frame-Options)", cls="Security Misconfiguration", cwe="CWE-1021", cvss=4.3,
  vector=None, conf=64, votes=2, verdict="false_positive", reason="The reverse proxy sets X-Frame-Options: DENY ahead of the app in the deployed environment.",
  file="server.js", l1=20, l2=24, source="Not applicable: configuration finding", sink="Not applicable: configuration finding",
  wrong="The Express app itself sets no X-Frame-Options or frame-ancestors directive.",
  why="Without it, the fund-allocation page could in principle be framed and clickjacked.",
  fix="No app change required; keep the edge proxy's frame-denial documented so it is not accidentally removed.",
  exploited="Mitigated upstream; recorded as a false positive.", precon=["Would require the edge proxy's frame-denial to be removed."],
  code=["app.use(helmet({ frameguard: false }));"], exploitability="Not applicable: recorded as a false positive.",
  vreason="Confirmed the deployed edge proxy already sends X-Frame-Options: DENY ahead of this app.", alsoat=[]),
 dict(id=29, sev="Medium", title="NoSQL injection in research search", cls="Injection", cwe="CWE-943", cvss=6.4,
  vector=None, conf=73, votes=3, verdict="confirmed", reason="A crafted object operator changed the search query's matching logic.",
  file="app/routes/research.js", l1=38, l2=42, source="req.query.q on the research search box", sink="MongoDB find() filter built from the query string",
  wrong="The research search builds its MongoDB filter directly from the query string parameter, the same unguarded pattern as the login finding.",
  why="An attacker can widen or otherwise manipulate the search filter, and on a differently-shaped query could extend this into broader data exposure.",
  fix="Validate that search parameters are scalars before use, or use a query builder that will not interpret operator objects from user input.",
  exploited="Attacker passes an operator object as the query string and the filter matches every record instead of the intended search term.",
  precon=["Research search endpoint accessible to the attacker's session tier."], code=["Research.find({ term: req.query.q }, cb);"],
  exploitability="Low effort; same technique as the login NoSQL injection finding.",
  vreason="Passed an object-operator query string and confirmed the result set matched all records instead of the search term.",
  alsoat=["app/data/user-dao.js:90 (same unguarded query pattern)"]),
]

CHAINS = [
 {"title": "NoSQLi login bypass → RCE", "steps": [3, 7],
  "narrative": "The login NoSQL injection (finding #3) grants an authenticated session without credentials; from there the eval-injection benefits calculator (finding #7) gives full remote code execution on the application server."},
 {"title": "Hardcoded secret → forged session → RCE", "steps": [4, 7],
  "narrative": "The hardcoded session secret (finding #4) lets an attacker forge a valid session cookie for any account; combined with the eval-injection calculator (finding #7), that forged session reaches full remote code execution."},
 {"title": "Enumeration + brute force → RCE", "steps": [24, 5, 7],
  "narrative": "Username enumeration (finding #24) narrows the target account, the missing login rate limit (finding #5) makes brute-forcing its password practical, and the eval-injection calculator (finding #7) turns that authenticated session into remote code execution."},
 {"title": "SSRF → open MongoDB", "steps": [9, 1],
  "narrative": "The authenticated SSRF in the research endpoint (finding #9) lets an attacker make the server issue requests on their behalf, reaching the unauthenticated MongoDB instance (finding #1) that should only be visible on the internal network."},
 {"title": "Stored XSS → cookie theft → RCE", "steps": [21, 22, 7],
  "narrative": "The outdated, unsanitised Markdown renderer (finding #21) lets an attacker plant a script in a memo; because the session cookie lacks HttpOnly (finding #22) that script can steal a victim's session, and from an authenticated session the eval-injection calculator (finding #7) gives remote code execution."},
 {"title": "Weak password policy → brute force → RCE", "steps": [5, 7],
  "narrative": "The missing login rate limit (finding #5) makes brute-forcing a weak password practical, and the eval-injection calculator (finding #7) turns that authenticated session into remote code execution."},
]

MODEL_ROLES = [("chain", "deepseek-v4-pro"), ("dedup", "deepseek-v4-pro"), ("verify", "deepseek-v4-pro"),
               ("deepdive", "deepseek-v4-pro"), ("validate", "deepseek-v4-pro"), ("decompose", "deepseek-v4-pro"),
               ("remediate", "deepseek-v4-pro"), ("preprocess", "deepseek-v4-pro"), ("threatmodel", "deepseek-v4-pro"),
               ("autoexclude", "deepseek-v4-flash"), ("graph_annotate", "deepseek-v4-flash")]

SCAN = {"files_scope": 69, "files_analyzed": 66, "duration": 6104, "tokens": 3400424, "verifier_tp": 20, "verifier_fp": 4,
        "dropped": 59, "raw_before_dedup": 88, "manifest_sha": REVIEW["fullSha"], "vvah": "1.3.0",
        "cost": "$4.87", "notes": ["4 low-confidence findings auto-excluded by the pre-verify triage.",
                                    "Chain analysis limited to steps within the same OWASP Top 10 category boundary."],
        "summary": ("NodeGoat (OWASP's intentionally vulnerable Node.js/Express/MongoDB app) was scanned end-to-end "
                     "across 69 files. The harness surfaced injection, authentication and access-control weaknesses "
                     "concentrated in app/routes and app/data, chained six of them into full compromise paths, and "
                     "flagged four low-signal findings as likely false positives after the verifier pass.")}

CLASSES = sorted(set(f["cls"] for f in FINDINGS))

DATA = {"review": REVIEW, "findings": FINDINGS, "chains": CHAINS, "scan": SCAN,
        "model_roles": MODEL_ROLES, "classes": CLASSES}


# --------------------------------------------------------------------------- markup helpers
def qf(label, value_html, tip=None, span2=False):
    t = ' data-tip="%s"' % esc(tip) if tip else ""
    cls = "card tip" if tip else "card"
    return ('<div class="%s" style="padding:8px 10px;box-shadow:none;%s"%s>'
            '<div class="lbl" style="font-size:10px">%s</div><div style="font-size:13px;margin-top:2px;overflow:hidden;text-overflow:ellipsis">%s</div></div>'
            ) % (cls, "grid-column:span 2" if span2 else "", t, label, value_html)


def section(title, color, tip, body_html):
    t = ' class="tip" data-tip="%s"' % esc(tip) if tip else ""
    return ('<div style="margin-top:16px"><div class="row" style="gap:7px;margin-bottom:6px">'
            '<span style="width:8px;height:8px;border-radius:2px;background:var(--%s);flex:none"></span>'
            '<span%s class="lbl" style="font-size:11px">%s</span></div>'
            '<div style="font-size:13px;line-height:1.65;color:var(--ink2);padding-left:15px">%s</div></div>'
            ) % (color, t, title, body_html)


# --------------------------------------------------------------------------- header
HEADER = T("""
<div class="row" style="gap:10px;margin-bottom:2px">
  <a href="#" class="row" style="gap:6px;font-size:13px;color:var(--ink2)">[[back]]Reviews</a>
</div>
<div class="pagehead" style="margin-bottom:10px">
  <div class="grow">
    <sc-if value="{{rn.off}}" hint-placeholder-val="{{true}}">
      <div class="row" style="gap:8px;flex-wrap:wrap">
        <span style="color:var(--accent)">[[bug]]</span><h1 style="overflow-wrap:anywhere">{{review.name}}</h1>
        <sc-if value="{{review.demo}}" hint-placeholder-val="{{true}}">[[demo]]</sc-if>
        <button class="btn ghost icon sm" aria-label="{{rn.startAria}}" onClick="{{rn.start}}">[[pencil]]</button>
      </div>
    </sc-if>
    <sc-if value="{{rn.on}}" hint-placeholder-val="{{false}}">
      <div class="row" style="gap:8px">
        <input class="input" style="width:320px;font-size:16px;height:40px" aria-label="New review name" value="{{rn.value}}" onChange="{{rn.set}}" onKeyDown="{{rn.key}}" autoFocus>
        <button class="btn icon sm" style="color:var(--ok)" aria-label="Save name" onClick="{{rn.commit}}">[[check]]</button>
        <button class="btn ghost icon sm" aria-label="Cancel rename" onClick="{{rn.cancel}}">[[x]]</button>
      </div>
    </sc-if>
    <sc-if value="{{is.error}}" hint-placeholder-val="{{false}}"><p class="err-line" role="alert" style="margin-top:4px">Could not rename the review</p></sc-if>
    <div class="row wrap" style="gap:6px;margin-top:8px">[[p1]][[p2]][[p3]]</div>
  </div>
  <div class="actions">
    <button class="btn sm" aria-label="Download XLSX register" onClick="{{dlXlsx}}">[[xlsx]] XLSX</button>
    <button class="btn sm" aria-label="Download PPTX briefing deck" onClick="{{dlPptx}}">[[pptx]] PPTX</button>
    [[kebab]]
  </div>
</div>
<sc-if value="{{is.error}}" hint-placeholder-val="{{false}}">
  <p class="err-line" role="alert" style="margin-bottom:8px">Failed to download the XLSX export</p>
  <p class="err-line" role="alert" style="margin-bottom:8px">Failed to download the PPTX export</p>
</sc-if>
<sc-if value="{{degraded}}" hint-placeholder-val="{{true}}"><div style="margin-bottom:12px">[[degradedAlert]]</div></sc-if>
""", back=icon("arrow-left", 14), bug=icon("bug", 20), pencil=icon("pencil", 13),
   check=icon("check", 14), x=icon("x", 14), xlsx=icon("file-spreadsheet", 14), pptx=icon("presentation", 14),
   demo=chip("Demo", "info", tip="Shared sample review — read-only for everyone", xs=True),
   p1='<span class="chip outline xs tip" data-tip="Original scan output format">{{review.fmt}}</span>',
   p2='<span class="chip outline xs mono tip" data-tip="{{review.fullSha}}">{{review.sha}}</span>',
   p3='<span class="chip outline xs tip" data-tip="When this review was imported">{{review.date}}</span>',
   kebab=kebab("kb", [("Copy link", "{{copyLink}}", "", "link")], aria="More actions"),
   degradedAlert=alert("warn", "<b>Scan degraded.</b> {{review.degraded_reason}}", "dismissDegraded"))

# --------------------------------------------------------------------------- review band + severity strip
BAND = T("""
<div class="grid g5">
  [[t1]][[t2]][[t3]][[t4]][[t5]]
</div>
<p class="sub" style="font-size:13px;margin-top:10px">{{headline}}</p>
<div class="pillbar" style="margin-top:10px">[[sevchips]]</div>
""", t1=kpi("Total findings", "{{band.total}}", "", tip="All findings reported for this scan."),
   t2=kpi("Critical", "{{band.crit}}", "confirm these first", "crit", tip="Critical-severity findings. Click to filter the table.", click=True, attrs='onClick="{{filterCrit}}"'),
   t3=kpi("High", "{{band.high}}", "", "high", tip="High-severity findings. Click to filter the table.", click=True, attrs='onClick="{{filterHigh}}"'),
   t4=kpi("Exploit chains", "{{band.chains}}", "steps that link together", tip="Findings the scanner linked into a multi-step attack path."),
   t5=kpi("Verifier false positives", "{{band.fp}}", "", "grey", tip="Findings the AI verifier marked as false positive."),
   sevchips='<sc-for list="{{sevChips}}" as="sc" hint-placeholder-count="6"><span class="chip {{sc.cls}} tip" data-tip="{{sc.tip}}" onClick="{{sc.pick}}" style="cursor:pointer;box-shadow:{{sc.ring}}">{{sc.label}}</span></sc-for>')

TABS_HTML = tabs("t", [("find", "Findings"), ("chains", "{{chainsTabLabel}}"), ("scan", "Scan details")])

FOOTER_NOTE = ('<p class="faint" style="font-size:11.5px;margin-top:22px;border-top:1px solid var(--line);padding-top:12px">'
               "Findings produced by Visa Vulnerability Agentic Harness (Apache-2.0). AI-generated triage candidates — confirm before acting.</p>")

# --------------------------------------------------------------------------- findings tab
COLS = "48px 92px minmax(0,2.1fr) 152px 88px 60px 130px minmax(0,1.4fr) 118px"

VERDICT_CELL = ('<sc-if value="{{r.vConfirmed}}" hint-placeholder-val="{{false}}"><span class="chip ok xs tip" data-tip="Verifier: true positive">Confirmed</span></sc-if>'
                '<sc-if value="{{r.vFalsePos}}" hint-placeholder-val="{{false}}"><span class="chip grey xs tip" data-tip="Verifier: false positive">False positive</span></sc-if>'
                '<sc-if value="{{r.vNone}}" hint-placeholder-val="{{true}}">—</sc-if>')

FINDROW = T("""<div class="dr link" role="button" tabindex="0" aria-label="{{r.aria}}" style="grid-template-columns:[[cols]]" onClick="{{r.open}}" onKeyDown="{{r.key}}">
  [[c1]][[c2]][[c3]][[c4]][[c5]][[c6]][[c7]][[c8]][[c9]]
</div>""", cols=COLS,
  c1=dcell("#", '<span class="mono faint">{{r.id}}</span>'),
  c2=dcell("Severity", '<span class="row" style="gap:6px;white-space:nowrap"><i class="dot" style="background:{{r.sevColor}}"></i>{{r.sev}}</span>'),
  c3=dcell("Title", '<span style="display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden">{{r.title}}</span>'),
  c4=dcell("Class", '<span class="sub">{{r.cls}}</span>'),
  c5=dcell("CWE", '<a href="{{r.cweHref}}" target="_blank" rel="noopener" class="mono" onClick="{{stop}}">{{r.cwe}}</a>'),
  c6=dcell("CVSS", '<span class="mono num">{{r.cvss}}</span>', "r"),
  c7=dcell("Confidence", '<span class="row tip" data-tip="{{r.confTip}}" aria-label="{{r.confAria}}" style="gap:6px"><span class="bar" style="width:42px"><i style="width:{{r.conf}}%;background:var(--accent)"></i></span><span class="num" style="font-size:12px">{{r.conf}}%</span></span>'),
  c8=dcell("File:lines", '<span class="mono tip" data-tip="{{r.fileLines}}" style="font-size:12px;display:block;min-width:0;overflow-wrap:anywhere">{{r.fileLines}}</span>'),
  c9=dcell("Verdict", VERDICT_CELL))

FILTERBAR = T("""<div class="row wrap" style="gap:8px;margin-bottom:12px">
  <div class="search" style="width:280px">[[search]]<input class="input sm" type="search" placeholder="Search title, file, or CWE…" aria-label="Search findings by title, file, or CWE" value="{{fq}}" onChange="{{setFq}}"></div>
  <select class="select sm" aria-label="Filter by vulnerability class" value="{{classF}}" onChange="{{setClassF}}"><option value="">All classes</option><sc-for list="{{classOptions}}" as="c" hint-placeholder-count="4"><option value="{{c}}">{{c}}</option></sc-for></select>
  <select class="select sm" aria-label="Filter by verdict" value="{{verdictF}}" onChange="{{setVerdictF}}"><option value="">All verdicts</option><option value="confirmed">Confirmed</option><option value="false_positive">False positive</option><option value="unverified">Unverified</option></select>
</div>""", search=icon("search", 15))

FINDTABLE = T("""<div class="dt">
  <div class="dr dh" style="grid-template-columns:[[cols]]">[[h1]][[h2]][[h3]][[h4]][[h5]][[h6]][[h7]][[h8]][[h9]]</div>
  <sc-for list="{{tbl.rows}}" as="r" hint-placeholder-count="6">[[row]]</sc-for>
</div>
<sc-if value="{{noRows}}" hint-placeholder-val="{{false}}"><p class="empty" style="padding:24px;margin-top:10px">No findings match your search or filter.</p></sc-if>
<p class="faint" style="font-size:12px;margin-top:8px">Showing {{shownCount}} of {{totalCount}} {{findWord}}</p>""", cols=COLS,
  h1=dth("tbl", "idx", "#"), h2=dth("tbl", "severity", "Severity"), h3=dth("tbl", "title", "Title"),
  h4=dth("tbl", "cls", "Class"), h5=dth("tbl", "cwe", "CWE"), h6=dth("tbl", "cvss", "CVSS", "r"),
  h7=dth("tbl", "confidence", "Confidence"), h8=dth("tbl", "file", "File:lines"),
  h9=dth("tbl", "verdict", "Verdict", sortable=False), row=FINDROW)

FINDINGS_TAB = FILTERBAR + FINDTABLE

# --------------------------------------------------------------------------- exploit chains tab
# NOTE: dc.py's runtime resolves {{hole}} inside presentation attrs (fill/stroke/stroke-width/
# stroke-dasharray/class/style) fine, but NOT inside plain geometry attrs (x/y/d/width) -- verified
# empirically via harness (leak + "Expected moveto path command" / "Expected length" console errors
# when d/x/y were holes). All 9 node positions and 8 edge paths are fixed (only fill/stroke/text
# change when a step is marked fixed), so geometry is precomputed in Python and only the
# presentation attrs + text content are holes, keyed by nodeState.n<id> / edgeState.e<i>.
NODE_POS = {3: (30, 48), 4: (30, 120), 24: (30, 192), 9: (30, 264), 21: (30, 336),
            5: (390, 120), 22: (390, 264), 7: (750, 120), 1: (750, 264)}
NODE_ORDER = [3, 4, 24, 9, 21, 5, 22, 7, 1]
EDGE_DEFS = [(0, 3, 7), (1, 4, 7), (2, 24, 5), (2, 5, 7), (3, 9, 1), (4, 21, 22), (4, 22, 7), (5, 5, 7)]  # (chainIndex, fromId, toId)


def _node_block(fid):
    # Text inside SVG <text> must be static: the runtime renders holes as HTML spans, which SVG
    # does not draw (labels came out zero-width). Only presentation attributes stay dynamic.
    f = next(x for x in FINDINGS if x["id"] == fid)
    x, y = NODE_POS[fid]
    tx, ty1, ty2 = x + 12, y + 18, y + 35
    return T("""<g onClick="{{nodeState.[[k]].toggle}}" style="cursor:pointer">
        <rect x="[[x]]" y="[[y]]" width="150" height="46" rx="9" fill="{{nodeState.[[k]].fill}}" stroke="{{nodeState.[[k]].stroke}}" stroke-width="1.5" style="transition:fill .35s,stroke .35s"></rect>
        <text x="[[tx]]" y="[[ty1]]" font-size="11" font-family="IBM Plex Mono" fill="{{nodeState.[[k]].idFill}}">#[[id]] &middot; [[sev]]</text>
        <text x="[[tx]]" y="[[ty2]]" font-size="12" font-family="IBM Plex Sans" font-weight="600" fill="{{nodeState.[[k]].tFill}}" style="text-decoration:{{nodeState.[[k]].deco}}">[[title]]</text>
        <title>#[[id]] [[title]]
[[file]]
Click to mark fixed or reopen</title>
      </g>""", k="n%d" % fid, x=x, y=y, tx=tx, ty1=ty1, ty2=ty2, id=fid, sev=esc(f["sev"]), title=esc(f["title"]), file=esc(f["file"]))


def _edge_path(idx, a, b):
    x1, y1 = NODE_POS[a][0] + 150, NODE_POS[a][1] + 23
    x2, y2 = NODE_POS[b][0], NODE_POS[b][1] + 23
    mx = (x1 + x2) / 2
    d = "M%g %g C %g %g, %g %g, %g %g" % (x1, y1, mx, y1, mx, y2, x2, y2)
    return T("""<path d="[[d]]" fill="none" stroke="{{edgeState.[[k]].stroke}}" stroke-width="{{edgeState.[[k]].w}}" stroke-dasharray="{{edgeState.[[k]].dash}}" marker-end="url(#arr)" style="transition:stroke .4s,stroke-width .3s"></path>""",
             d=d, k="e%d" % idx)


NODES_MARKUP = "".join(_node_block(fid) for fid in NODE_ORDER)
EDGES_MARKUP = "".join(_edge_path(i, a, b) for i, (_, a, b) in enumerate(EDGE_DEFS))

GRAPH_SVG = T("""<div class="card reveal" style="padding:16px;overflow:hidden">
  <div class="row between wrap" style="margin-bottom:10px;gap:8px">
    <span style="font-size:13px;font-weight:600">Attack graph</span>
    <span class="row" style="gap:10px;flex-wrap:wrap">
      <span style="font-size:12px;color:var(--ink2)"><span class="num" style="font-weight:600;color:{{brokenColor}}">{{broken}}</span> of 6 chains broken &middot; {{fixedN}} fixes applied</span>
      <button class="btn sm" onClick="{{suggestFix}}">Fewest fixes</button><button class="btn sm" onClick="{{resetFix}}">Reset</button>
    </span>
  </div>
  <svg viewBox="0 0 900 420" style="width:100%;height:auto;display:block" aria-label="Exploit chain graph">
    <defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="context-stroke"/></marker></defs>
    <text x="20" y="24" font-size="11" fill="var(--ink3)" font-family="IBM Plex Sans" letter-spacing=".06em">ENTRY</text>
    <text x="380" y="24" font-size="11" fill="var(--ink3)" font-family="IBM Plex Sans" letter-spacing=".06em">PIVOT</text>
    <text x="740" y="24" font-size="11" fill="var(--ink3)" font-family="IBM Plex Sans" letter-spacing=".06em">IMPACT</text>
    [[edges]]
    [[nodes]]
  </svg>
</div>""", edges=EDGES_MARKUP, nodes=NODES_MARKUP)

CHAINCARD = T("""<div class="card" style="padding:12px 14px;border-left:3px solid {{c.edge}};opacity:{{c.op}};transition:opacity .3s">
  <div class="row wrap" style="gap:8px;align-items:center">
    <span class="chip {{c.tone}} tip" data-tip="Chain severity (highest step)">{{c.sevLabel}}</span>
    <span style="font-weight:600;font-size:13px;text-decoration:{{c.deco}}">{{c.title}}</span>
    <span class="{{c.stateCls}}" style="margin-left:auto">{{c.state}}</span>
  </div>
  <div class="row wrap" style="gap:4px;margin-top:8px;align-items:center">
    <sc-for list="{{c.steps}}" as="s" hint-placeholder-count="3"><button class="chip xs mono tip" data-tip="{{s.tip}}" onClick="{{s.open}}" style="background:{{s.bg}};color:{{s.fg}};border:0;cursor:pointer">#{{s.id}}</button><sc-if value="{{s.hasArrow}}" hint-placeholder-val="{{true}}"><span class="faint" style="margin:0 2px">&rarr;</span></sc-if></sc-for>
  </div>
  <p class="sub" style="font-size:12.5px;margin-top:8px;line-height:1.55">{{c.narrative}}</p>
</div>""")

CHAINS_TAB = T("""[[graph]]
<div class="row between" style="margin-top:18px;margin-bottom:2px"><span style="font-size:13px;font-weight:600">Chains</span><span class="faint" style="font-size:12px">a chain breaks when any step is fixed</span></div>
<div class="stack" style="gap:10px;margin-top:8px">
  <sc-if value="{{noChains}}" hint-placeholder-val="{{false}}"><p class="empty">The scanner did not link any findings into an exploit chain.</p></sc-if>
  <sc-for list="{{chains}}" as="c" hint-placeholder-count="6">[[card]]</sc-for>
</div>""", graph=GRAPH_SVG, card=CHAINCARD)

# --------------------------------------------------------------------------- scan details tab
def _dlrow(label, value):
    return '<div class="row between" style="font-size:13px;gap:12px"><span class="sub">%s</span><span style="font-weight:500;text-align:right" class="num">%s</span></div>' % (label, value)


def _deflist(title, rows_html):
    return '<div class="card" style="padding:14px 16px"><h3 style="font-size:13px;margin-bottom:10px">%s</h3><div class="stack" style="gap:8px">%s</div></div>' % (title, rows_html)


_METRICS_ROWS = "".join([
    _dlrow("Files in scope", str(SCAN["files_scope"])), _dlrow("Files analyzed", str(SCAN["files_analyzed"])),
    _dlrow("Duration", "%ds" % SCAN["duration"]), _dlrow("Tokens", "{:,}".format(SCAN["tokens"])),
    _dlrow("Verifier true positives", str(SCAN["verifier_tp"])), _dlrow("Verifier false positives", str(SCAN["verifier_fp"])),
    _dlrow("Degraded reason", esc(REVIEW["degraded_reason"])), _dlrow("Dropped findings", str(SCAN["dropped"])),
    _dlrow("Raw findings before dedup", str(SCAN["raw_before_dedup"])),
])

_MANIFEST_ROWS = "".join(
    [_dlrow("Target git sha", '<span class="mono tip" data-tip="%s">%s</span>' % (SCAN["manifest_sha"], SCAN["manifest_sha"][:7])),
     _dlrow("VVAH version", SCAN["vvah"])]
    + [_dlrow(esc(role) + " model", "%s (deepseek)" % model) for role, model in MODEL_ROLES]
    + [_dlrow("Total cost", SCAN["cost"]), _dlrow("Total tokens", "{:,}".format(SCAN["tokens"]))])

_NOTES_HTML = "<ul style='margin:0;padding-left:18px;font-size:13px;color:var(--ink2)'>" + "".join(
    "<li style='margin-bottom:4px'>%s</li>" % esc(n) for n in SCAN["notes"]) + "</ul>"

_SUMMARY_CARD = ('<div class="card" style="padding:14px 16px;grid-column:1/-1"><h3 style="font-size:13px;margin-bottom:8px">Scanner summary</h3>'
                  '<p style="font-size:13px;color:var(--ink2);line-height:1.6">%s</p></div>') % esc(SCAN["summary"])

SCANDETAILS_TAB = T("""<div class="grid g2" style="gap:14px">
  [[metrics]][[manifest]][[notes]][[summary]]
</div>""", metrics=_deflist("Scan metrics", _METRICS_ROWS), manifest=_deflist("Run manifest", _MANIFEST_ROWS),
   notes=_deflist("Ingest notes", _NOTES_HTML), summary=_SUMMARY_CARD)

# --------------------------------------------------------------------------- finding drawer
DRAWER_CHIPS = T("""<div class="grid g2" style="gap:8px">
  [[cwe]][[cvss]][[conf]][[verdict]][[file]][[srcsink]]
</div>""",
  cwe=qf("CWE", '<a href="{{cur.cweHref}}" target="_blank" rel="noopener" class="row" style="gap:4px;display:inline-flex">{{cur.cwe}}%s</a>' % icon("external", 12),
         tip="Common Weakness Enumeration entry — opens the MITRE definition."),
  cvss=qf("CVSS", '<span class="chip {{cur.cvssTone}} xs">{{cur.cvss}} &middot; {{cur.cvssRating}}</span>', tip="{{cur.cvssTip}}"),
  conf=qf("Confidence", '<span class="row" style="gap:6px"><span class="bar" style="width:50px"><i style="width:{{cur.conf}}%;background:var(--accent)"></i></span><span class="num">{{cur.conf}}%</span></span>', tip="{{cur.confTip}}"),
  verdict=qf("Verdict", ('<sc-if value="{{cur.vConfirmed}}" hint-placeholder-val="{{false}}"><span class="chip ok xs">Confirmed</span></sc-if>'
                          '<sc-if value="{{cur.vFalsePos}}" hint-placeholder-val="{{false}}"><span class="chip grey xs">False positive</span></sc-if>'
                          '<sc-if value="{{cur.vNone}}" hint-placeholder-val="{{true}}">—</sc-if>'), tip="{{cur.verdictTip}}"),
  file=qf("File", '<span class="mono">{{cur.fileLines}}</span>', tip="{{cur.fileTip}}", span2=True),
  srcsink=qf("Source &rarr; Sink", '<span style="color:var(--info)">{{cur.source}}</span> <span class="faint">&rarr;</span> <span style="color:var(--crit)">{{cur.sink}}</span>',
             tip="Where attacker-controlled data enters (source) and where it does damage (sink).", span2=True))

REASON_CALLOUT = '<sc-if value="{{cur.hasReason}}" hint-placeholder-val="{{false}}"><div class="alert ok" style="margin-top:14px;font-size:13px">{{cur.reason}}</div></sc-if>'

SEC_WRONG = section("What is wrong", "crit", "The weakness the scanner found, in plain words.", "{{cur.wrong}}")
SEC_WHY = section("Why it matters", "high", "What an attacker gains if this is real.", "{{cur.why}}")
SEC_FIX = section("How to fix", "ok", "Suggested remediation — verify before applying.", "{{cur.fix}}")
SEC_EXPLOITED = section("How it is exploited", "med", "A concrete attack path the scanner reasoned about.", "{{cur.exploited}}")
SEC_PRECON = section("Preconditions", "ink3", "What must already be true for the attack to work.",
  '<ul style="margin:0;padding-left:16px"><sc-for list="{{cur.precon}}" as="p" hint-placeholder-count="2"><li style="margin-bottom:3px">{{p}}</li></sc-for></ul>')
SEC_CODE = T("""<div style="margin-top:16px"><div class="row" style="gap:7px;margin-bottom:6px"><span style="width:8px;height:8px;border-radius:2px;background:var(--ink2);flex:none"></span><span class="lbl tip" data-tip="{{cur.codeTip}}" style="font-size:11px">Code</span></div>
<pre class="block mono" style="padding:8px 10px;line-height:1.7;margin-left:15px;margin-top:0"><sc-for list="{{cur.codeLines}}" as="cl" hint-placeholder-count="4"><div class="row" style="gap:10px"><span class="faint" style="width:24px;text-align:right;flex:none;user-select:none">{{cl.n}}</span><span style="white-space:pre">{{cl.t}}</span></div></sc-for></pre></div>""")
SEC_EXPLOITABILITY = section("Exploitability", "med-fill", "How easy the scanner thinks this is to exploit in practice.", "{{cur.exploitability}}")
SEC_VREASON = section("Verifier reasoning", "low-fill", "The second-pass model's reasoning for its verdict.", "{{cur.vreason}}")
SEC_ALSOAT = section("Also at", "line2", "Other locations with the same pattern.",
  ('<sc-if value="{{cur.hasAlso}}" hint-placeholder-val="{{true}}"><ul class="mono" style="margin:0;padding-left:16px;font-size:12px">'
   '<sc-for list="{{cur.alsoat}}" as="a" hint-placeholder-count="1"><li style="margin-bottom:3px">{{a}}</li></sc-for></ul></sc-if>'
   '<sc-if value="{{cur.noAlso}}" hint-placeholder-val="{{false}}"><span class="faint" style="font-size:12.5px">None known.</span></sc-if>'))

DRAWER_HEAD = """<div class="row" style="gap:8px;align-items:flex-start">
  <span class="mono faint" style="margin-top:2px">#{{cur.id}}</span>
  <div class="grow">
    <div class="row wrap" style="gap:8px;align-items:center">
      <span class="chip {{cur.sevTone}} tip" data-tip="{{cur.sevTip}}">{{cur.sev}}</span>
      <h2 style="font-size:15px;line-height:1.3">{{cur.title}}</h2>
    </div>
    <div class="sub" style="font-size:12.5px;margin-top:3px">{{cur.cls}}</div>
  </div>
</div>"""

DRAWER_BODY = DRAWER_CHIPS + REASON_CALLOUT + SEC_WRONG + SEC_WHY + SEC_FIX + SEC_EXPLOITED + SEC_PRECON + SEC_CODE + SEC_EXPLOITABILITY + SEC_VREASON + SEC_ALSOAT

DRAWER_FOOT = T("""<button class="btn sm tip" data-tip="Previous finding in the current list" onClick="{{drawerPrev}}">[[chl]] Prev</button>
<span class="num faint" style="font-size:12px">{{drawerPos}} of {{drawerTotal}}</span>
<button class="btn sm tip" aria-label="Copy finding link" data-tip="Copy a link that opens this finding directly" onClick="{{copyFindingLink}}"><sc-if value="{{findingCopied}}" hint-placeholder-val="{{false}}">Copied</sc-if><sc-if value="{{findingNotCopied}}" hint-placeholder-val="{{true}}">Copy link</sc-if></button>
<button class="btn sm tip" data-tip="Next finding in the current list" onClick="{{drawerNext}}">Next [[chr]]</button>""", chl=icon("chevron-left", 14), chr=icon("chevron-right", 14))

DRAWER = sheet("finding", DRAWER_HEAD, DRAWER_BODY, DRAWER_FOOT, aria="Finding details")

# --------------------------------------------------------------------------- body assembly
BODY = T("""[[header]]
<div class="card" style="padding:14px 16px;margin-bottom:14px">[[band]]</div>
[[tabshtml]]
<div style="padding-top:14px">[[findp]][[chainsp]][[scanp]]</div>
[[footer]]
[[drawer]]""", header=HEADER, band=BAND, tabshtml=TABS_HTML,
   findp=panel("t", "find", FINDINGS_TAB), chainsp=panel("t", "chains", CHAINS_TAB), scanp=panel("t", "scan", SCANDETAILS_TAB),
   footer=FOOTER_NOTE, drawer=DRAWER)

# --------------------------------------------------------------------------- VALS
VALS = r"""
const sevRank = { Critical: 0, High: 1, Medium: 2, Low: 3, Info: 4 };
const sevTone = { Critical: 'crit', High: 'high', Medium: 'med', Low: 'low', Info: 'info' };
const review = Object.assign({}, D.review, { name: S.reviewName || D.review.name });
const total = D.findings.length;
const bandCrit = D.findings.filter(f => f.sev === 'Critical').length;
const bandHigh = D.findings.filter(f => f.sev === 'High').length;
const bandFp = D.findings.filter(f => f.verdict === 'false_positive').length;
const fileCounts = {}; D.findings.forEach(f => { fileCounts[f.file] = (fileCounts[f.file] || 0) + 1; });
let topFile = null, topK = 0; Object.keys(fileCounts).forEach(k => { if (fileCounts[k] > topK) { topK = fileCounts[k]; topFile = k; } });
const headline = total === 0 ? 'No findings were reported for this scan.' :
  'Confirm the ' + bandCrit + ' critical finding(s) first · ' + topK + ' of ' + total + ' findings sit in ' + topFile + ' · ' + D.chains.length + ' exploit chain(s) link findings together.';

const sevFilter = S.sevFilter || null;
const SEVS = ['Critical', 'High', 'Medium', 'Low', 'Info'];
const sevCounts = {}; SEVS.forEach(s => { sevCounts[s] = D.findings.filter(f => f.sev === s).length; });
const sevChips = [{ label: 'All ' + total, tip: 'Show every severity.', cls: !sevFilter ? 'blue' : 'outline', ring: !sevFilter ? '0 0 0 2px var(--accent-soft)' : 'none',
    pick: () => self.setIn(['sevFilter'], null) }]
  .concat(SEVS.map(s => { const on = sevFilter === s; return { label: s + ' ' + sevCounts[s], tip: 'Show only ' + s.toLowerCase() + '-severity findings.',
    cls: on ? sevTone[s] : 'outline', ring: on ? '0 0 0 2px var(--accent-soft)' : 'none', pick: () => self.setIn(['sevFilter'], on ? null : s) }; }));

const fq = (S.fq || '').toLowerCase(), classF = S.classF || '', verdictF = S.verdictF || '';
let filtered = D.findings.filter(f => {
  if (sevFilter && f.sev !== sevFilter) return false;
  if (classF && f.cls !== classF) return false;
  if (verdictF && f.verdict !== verdictF) return false;
  if (fq && !((f.title + ' ' + f.file + ' ' + f.cwe).toLowerCase().includes(fq))) return false;
  return true;
});
filtered = filtered.slice().sort((a, b) => (sevRank[a.sev] - sevRank[b.sev]) || (b.cvss - a.cvss));
const cvssTone = v => v >= 9 ? 'crit' : v >= 7 ? 'high' : v >= 4 ? 'med' : 'low';
const fileLinesOf = f => f.file + ':' + f.l1 + (f.l2 && f.l2 !== f.l1 ? ('-' + f.l2) : '');
const displayRows = filtered.map(f => ({ id: f.id, sev: f.sev, sevColor: 'var(--' + sevTone[f.sev] + ')', title: f.title, cls: f.cls, cwe: f.cwe,
  cweHref: 'https://cwe.mitre.org/data/definitions/' + (f.cwe || 'CWE-0').replace(/\D/g, '') + '.html', cvss: f.cvss, confidence: f.conf, conf: f.conf,
  confTip: f.conf + '% · ' + f.votes + ' vote(s)', confAria: f.conf + '% confidence', file: f.file, fileLines: fileLinesOf(f),
  vConfirmed: f.verdict === 'confirmed', vFalsePos: f.verdict === 'false_positive', vNone: f.verdict === 'unverified',
  aria: 'Open finding ' + f.id + ': ' + f.title,
  open: () => self.openSheet('finding', f.id, 576), key: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); self.openSheet('finding', f.id, 576); } } }));
const tbl = self.sortVals('tbl', displayRows, [
  { key: 'idx', get: r => r.id }, { key: 'severity', get: r => sevRank[r.sev] }, { key: 'title' }, { key: 'cls' },
  { key: 'cwe', get: r => parseInt((r.cwe || 'CWE-0').slice(4)) || 0 }, { key: 'cvss' }, { key: 'confidence' }, { key: 'file' },
], 'severity', 'asc');
const shownCount = tbl.rows.length, totalCount = total, noRows = shownCount === 0;

// ---- chain graph (lifted from hero-views CODE_BODY/CODE_SCRIPT; --ink-2/--ink-3 -> --ink2/--ink3 for
// dc.py; node/edge geometry is static markup now -- see NODE_POS/EDGE_DEFS in the Python module --
// only presentation attrs + text are holes here, keyed nodeState.n<id> / edgeState.e<i>) ----
const chainFixed = S.chainFixed || {};
const isBroken = c => c.steps.some(s => chainFixed[s]);
const toggleFix = id => (e) => { e && e.stopPropagation && e.stopPropagation(); const nx = Object.assign({}, chainFixed); if (nx[id]) delete nx[id]; else nx[id] = true; self.setState({ chainFixed: nx }); };
const sevFill = { Critical: 'var(--crit-soft)', High: 'var(--high-soft)', Medium: 'var(--med-soft)' };
const sevStroke = { Critical: '#E7A79F', High: '#EBC59A', Medium: '#E4D38F' };
const sevText = { Critical: 'var(--crit)', High: 'var(--high)', Medium: 'var(--med)' };
const NODE_IDS = [3, 4, 24, 9, 21, 5, 22, 7, 1];
const nodeState = {};
NODE_IDS.forEach(id => { const f = D.findings.find(x => x.id === id), fx = !!chainFixed[id];
  nodeState['n' + id] = { sevLabel: f.sev, title: f.title,
    fill: fx ? 'var(--ok-soft)' : sevFill[f.sev], stroke: fx ? 'var(--ok)' : sevStroke[f.sev], idFill: fx ? 'var(--ok)' : sevText[f.sev],
    tFill: fx ? 'var(--ink3)' : 'var(--ink)', deco: fx ? 'line-through' : 'none',
    tip: (fx ? 'FIXED · ' : '') + '#' + id + ' ' + f.title + '\n' + f.file + '\nClick to ' + (fx ? 'reopen' : 'mark fixed'), toggle: toggleFix(id) }; });
const EDGE_CHAIN_IDX = [0, 1, 2, 2, 3, 4, 4, 5];
const edgeState = {};
EDGE_CHAIN_IDX.forEach((ci, i) => { const broken = isBroken(D.chains[ci]);
  edgeState['e' + i] = { stroke: broken ? 'var(--line2)' : 'var(--ink)', w: broken ? 1.2 : 2, dash: broken ? '4 5' : '0' }; });
const brokenN = D.chains.filter(isBroken).length;
const chains = D.chains.map(c => { const b = isBroken(c); const stepSevs = c.steps.map(s => D.findings.find(f => f.id === s).sev);
  const worst = stepSevs.reduce((w, s) => sevRank[s] < sevRank[w] ? s : w, stepSevs[0]);
  return { title: c.title, narrative: c.narrative, sevLabel: worst, tone: sevTone[worst], state: b ? 'Broken' : 'Open',
    stateCls: 'chip ' + (b ? 'ok' : 'crit'), edge: b ? 'var(--ok)' : 'var(--crit)', op: b ? .7 : 1, deco: b ? 'line-through' : 'none',
    steps: c.steps.map((s, i) => { const fx = !!chainFixed[s], f = D.findings.find(x => x.id === s);
      return { id: s, bg: fx ? 'var(--ok-soft)' : 'var(--na)', fg: fx ? 'var(--ok)' : 'var(--ink2)', tip: '#' + s + ' ' + f.title + '\n' + f.file,
        open: () => self.openSheet('finding', s, 576), hasArrow: i < c.steps.length - 1 }; }) }; });

// ---- finding drawer ----
const openId = S.sheets && S.sheets.finding && S.sheets.finding.id != null ? S.sheets.finding.id : (tbl.rows[0] ? tbl.rows[0].id : D.findings[0].id);
const curRaw = D.findings.find(f => f.id === openId) || D.findings[0];
const cweNum = (curRaw.cwe || 'CWE-0').replace(/\D/g, '');
const cvssRating = curRaw.cvss >= 9 ? 'Critical' : curRaw.cvss >= 7 ? 'High' : curRaw.cvss >= 4 ? 'Medium' : 'Low';
const codeLines = (curRaw.code || []).map((t, i) => ({ n: (curRaw.l1 || 1) + i, t }));
const cur = Object.assign({}, curRaw, {
  sevTone: sevTone[curRaw.sev], sevTip: curRaw.sev + ' severity (scanner-assigned)',
  cweHref: 'https://cwe.mitre.org/data/definitions/' + cweNum + '.html',
  cvssTone: cvssTone(curRaw.cvss), cvssRating, cvssTip: curRaw.vector ? ('Vector: ' + curRaw.vector) : 'CVSS 3.1 base score',
  confTip: curRaw.conf + '% from ' + curRaw.votes + ' model vote(s)',
  vConfirmed: curRaw.verdict === 'confirmed', vFalsePos: curRaw.verdict === 'false_positive', vNone: curRaw.verdict === 'unverified',
  verdictTip: curRaw.verdict === 'confirmed' ? ('Verifier: true positive (' + Math.round(curRaw.conf / 10) + '/10)') :
    curRaw.verdict === 'false_positive' ? 'Verifier: false positive' : 'Not reviewed by the verifier',
  fileLines: fileLinesOf(curRaw), fileTip: curRaw.file + ' lines ' + curRaw.l1 + '–' + curRaw.l2,
  hasReason: !!curRaw.reason, codeLines, codeTip: curRaw.file + ', starting at line ' + curRaw.l1,
  hasAlso: (curRaw.alsoat || []).length > 0, noAlso: (curRaw.alsoat || []).length === 0,
});
const drawerIdx = tbl.rows.findIndex(r => r.id === curRaw.id);
const drawerPos = drawerIdx >= 0 ? drawerIdx + 1 : 1, drawerTotal = tbl.rows.length || 1;
const stepTo = (delta) => { if (!tbl.rows.length) return; const i = drawerIdx >= 0 ? drawerIdx : 0; const ni = (i + delta + tbl.rows.length) % tbl.rows.length; self.openSheet('finding', tbl.rows[ni].id, 576); };

// ---- header / rename / kebab / degraded ----
const rn = Object.assign(self.renameVals('review', review.name, (v) => self.setIn(['reviewName'], v)), { startAria: 'Rename ' + review.name });

return {
  sheets: { finding: self.sheetVals('finding', 576) },
  review, band: { total: String(total), crit: String(bandCrit), high: String(bandHigh), chains: String(D.chains.length), fp: String(bandFp) },
  headline, sevChips, rn,
  filterCrit: () => { self.setIn(['sevFilter'], 'Critical'); self.setIn(['tab', 't'], 'find'); },
  filterHigh: () => { self.setIn(['sevFilter'], 'High'); self.setIn(['tab', 't'], 'find'); },
  degraded: !!review.degraded_reason && !S.degradedDismissed, dismissDegraded: () => self.setState({ degradedDismissed: true }),
  dlXlsx: () => {}, dlPptx: () => {},
  kb: self.menuVals('review-actions'),
  copyLink: (e) => { e.stopPropagation(); self.setState({ menu: null }); self.runBusy('copyLink', 1500); },
  copiedTag: self.busy('copyLink'),
  t: self.tabVals('t', ['find', 'chains', 'scan']), chainsTabLabel: 'Exploit chains (' + D.chains.length + ')',
  fq: S.fq || '', setFq: e => self.setState({ fq: e.target.value }),
  classF, setClassF: e => self.setState({ classF: e.target.value }), classOptions: D.classes,
  verdictF, setVerdictF: e => self.setState({ verdictF: e.target.value }),
  tbl, noRows, shownCount: String(shownCount), totalCount: String(totalCount), findWord: totalCount === 1 ? 'finding' : 'findings',
  broken: String(brokenN), brokenColor: brokenN === 6 ? 'var(--ok)' : brokenN ? 'var(--high)' : 'var(--crit)', fixedN: String(Object.keys(chainFixed).length),
  nodeState, edgeState, chains, noChains: D.chains.length === 0,
  suggestFix: () => self.setState({ chainFixed: { 7: true, 1: true } }), resetFix: () => self.setState({ chainFixed: {} }),
  cur, drawerPos: String(drawerPos), drawerTotal: String(drawerTotal),
  drawerPrev: () => stepTo(-1), drawerNext: () => stepTo(1),
  copyFindingLink: (e) => { e.stopPropagation(); self.runBusy('copyFindingLink', 1500); },
  findingCopied: self.busy('copyFindingLink'), findingNotCopied: !self.busy('copyFindingLink'),
};
"""

# --------------------------------------------------------------------------- harness clicks
SHEET_OPEN = "document.querySelector('aside.sheet').style.transform.startsWith('translateX(0')"
CLICKS = [
    {"css": '.tab:has-text("Scan details")', "check": "document.querySelector('.tab.on').textContent.includes('Scan details')"},
    {"css": '.tab:has-text("Exploit chains")', "check": "document.querySelector('.tab.on').textContent.includes('Exploit chains')"},
    {"text": "Eval injection (RCE)", "check": "document.body.textContent.includes('5 of 6 chains broken')"},
    {"text": "Fewest fixes", "check": "document.body.textContent.includes('6 of 6 chains broken')"},
    {"text": "Reset", "check": "document.body.textContent.includes('0 of 6 chains broken')"},
    {"css": '.tab:has-text("Findings")', "check": "document.querySelector('.tab.on').textContent.includes('Findings')"},
    {"css": '.dt .dh button:has-text("Title")', "desktop_only": True,
     "check": "Array.from(document.querySelectorAll('.dt .dh .dc')).find(d => d.textContent.includes('Title')).getAttribute('aria-sort') === 'ascending'"},
    {"css": '.pillbar .chip:has-text("Critical")', "check": "document.querySelectorAll('.dt .dr:not(.dh)').length === 6"},
    {"css": '.kpi:has-text("High")', "check": "document.querySelectorAll('.dt .dr:not(.dh)').length === 5"},
    {"css": '.dt .dr.link .dc[data-th="Title"]', "check": SHEET_OPEN, "note": "Row opens the drawer; the CWE link cell stops propagation on purpose"},
    {"text": "Next", "check": "document.body.textContent.includes('2 of 5')"},
    {"css": "aside.sheet .sheet-h .xbtn", "check": "!(" + SHEET_OPEN + ")"},
    {"label": "Rename NodeGoat golden scan (VVAH 1.3.0)", "check": "document.querySelector('input[aria-label=\"New review name\"]') !== null"},
    {"label": "Save name", "check": "document.querySelector('input[aria-label=\"New review name\"]') === null"},
    {"label": "More actions", "check": "document.querySelector('.menu.open') !== null"},
    {"css": '.menu.open button:has-text("Copy link")', "check": "document.body.textContent.includes('Copied')"},
    {"label": "Dismiss", "check": "document.querySelector('.alert.warn') === null"},
]


def build(phone=False):
    stem = STEM + ("Phone" if phone else "")
    props = {"view": {"editor": "enum", "options": ["default", "error"], "default": "default", "section": "State"}}
    html = screen(stem, app_shell("codereview", BODY), VALS, DATA, {"tab": {"t": "find"}}, props=props, phone=phone)
    return [(stem, html)]
