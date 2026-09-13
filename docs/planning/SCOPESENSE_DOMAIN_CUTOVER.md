# scopesense.in — domain cut-over runbook (dual-run with scopewise.assessiq.in)

**Written:** 2026-09-12. **Status (end of 2026-09-12):** everything is staged and Google OAuth is
done; the ONLY blocker is the registrar's 24-hour hold on nameserver changes
for a newly registered domain (Hostinger message: "Nameserver changes for
this domain are temporarily unavailable. Please try again in 24 hours"). Decision (user, 2026-09-12): **both hosts stay live for
about 30 days** (until ~2026-10-12) because office proxies may block the new
domain; no redirect until then. Product name stays **ScopeWise** (only the
domain changes) unless the user decides otherwise.

## 0. Facts

| Item | Value |
|---|---|
| New domain | `scopesense.in`, registered 2026-09-12 (expires 2027-09-12), registrar = Hostinger (parking NS `atlas`/`hyperion.dns-parking.com`) |
| Cloudflare account | `468b124baae458fb4a8406c829d1e1c9` (same account as assessiq.in) |
| Cloudflare zone | `scopesense.in`, id `b2765bac5878d2750ee2c11b8e05498e`, status **pending** until NS switch |
| Assigned nameservers | `ethan.ns.cloudflare.com`, `nena.ns.cloudflare.com` |
| VPS | `72.61.227.64` (alias `a11yos-vps`), app at `/opt/scopewise`, Caddy at `/opt/ti-platform/caddy/` (container `ti-platform-caddy-1`, host `ssl/` dir maps to `/etc/caddy/ssl`) |
| Old host | `scopewise.assessiq.in` — stays live; Caddy block at Caddyfile line ~118, wildcard `*.assessiq.in` origin cert |
| Google OAuth client | `522377802447…` (needs the new origin added) |
| API token | "ScopeSense.in" custom token: Account Access Policies/Apps Edit, Zone DNS Settings / Zone Settings / SSL and Certificates / DNS Edit, All zones, **IP-filtered to 72.61.227.64** — every API call must be made **from the VPS over IPv4** (`curl -4`); IPv6 or the laptop get "Cannot use the access token from location" / generic 401. Stored in the local repo `.env` (the user saved it under the key `CF_ORIGIN_CA_KEY`; the old `CLOUDFLARE_API_TOKEN` line was removed — restore that name for the SEO tooling). Never committed; never printed. |
| Origin CA Key | **Deprecated by Cloudflare** — not needed; Origin certificates are issued with the API token (Zone → SSL and Certificates → Edit) via `Authorization: Bearer`. |

## 1. Done (2026-09-12)

Cloudflare (via API from the VPS):
- A `scopesense.in` → `72.61.227.64`, proxied (replaced the parking IP `2.57.91.91` the dashboard had auto-created).
- CNAME `www.scopesense.in` → `scopesense.in`, proxied.
- Settings: `ssl=strict` (Full strict), `always_use_https=on`, `min_tls_version=1.2`, `tls_1_3=on`, `automatic_https_rewrites=on`.
- Authenticated Origin Pulls enabled (`origin_tls_client_auth/settings enabled=true`) — matches assessiq.in, which Caddy enforces with `client_auth require_and_verify` against `cf-origin-pull-ca.pem`.

Server (VPS):
- `/root/scopesense-ssl/scopesense.in.key` + `scopesense.in.csr` (RSA 2048, CN scopesense.in) generated for the Origin certificate.
- `/opt/scopewise/deploy/caddy-scopesense.block` — the `scopesense.in` site block (clone of the scopewise.assessiq.in one: AOP mTLS, security headers, `/api/*` → 172.17.0.1:9095, everything else → :9094) plus a `www.scopesense.in` block that 301s to the apex.
- `/opt/scopewise/deploy/cutover-scopesense.sh` — the one-shot cut-over (section 3).

Code (commit `e83f435`, deployed): `apps/web/next.config.js` treats an **empty** `NEXT_PUBLIC_API_URL` as "same-origin" (`??` instead of `||`), so one web build serves both hosts and the browser calls `/api/...` on whichever host loaded the page. All 18 consumers of that variable are client components, so relative URLs are safe. The web Dockerfile passes the value through `ARG`/`ENV`, and compose passes it as a build arg. `CLAUDE.md` "Live deployment" describes the dual-run.

## 2. Pending (in order)

1. **Registrar nameservers** (user; blocked until the hold lifts, ~2026-09-13): set `ethan.ns.cloudflare.com` and `nena.ns.cloudflare.com` at Hostinger. Check: `nslookup -type=NS scopesense.in` shows the Cloudflare NS; zone status becomes `active`.
2. **Origin certificate** (Claude, from the VPS, only once the zone is active — Cloudflare refuses with "Failed to validate requested hostname … not part of your account" while pending):
   ```
   # on the VPS, token read from stdin, IPv4 forced
   cd /root/scopesense-ssl
   python3 -c 'import json;print(json.dumps({"hostnames":["scopesense.in","*.scopesense.in"],"requested_validity":5475,"request_type":"origin-rsa","csr":open("scopesense.in.csr").read()}))' > req.json
   curl -4 -s -X POST -H "Authorization: Bearer $CF" -H "Content-Type: application/json" https://api.cloudflare.com/client/v4/certificates --data @req.json > resp.json
   # write result.certificate -> scopesense.in.pem, then
   install -m 600 scopesense.in.key /opt/ti-platform/caddy/ssl/scopesense.in.key
   install -m 644 scopesense.in.pem /opt/ti-platform/caddy/ssl/scopesense.in.pem
   openssl x509 -in /opt/ti-platform/caddy/ssl/scopesense.in.pem -noout -subject -enddate
   ```
   Fallback if the API keeps refusing: dashboard → SSL/TLS → Origin Server → Create Certificate (`scopesense.in, *.scopesense.in`), paste cert/key into the same two paths.
3. **Cut-over** (Claude): `bash /opt/scopewise/deploy/cutover-scopesense.sh` — see section 3. Old host untouched.
4. **Google OAuth** — DONE 2026-09-12: client `522377802447-o9p935omg2gp4kf42n6hkdnjpat2lokl` (project AutomateEdge) now has origins `https://scopewise.assessiq.in` + `https://scopesense.in` and redirect URIs `…/api/auth/google/cb` for both hosts.
5. **Smoke** (Claude): login page, Google sign-in, one review page, one XLSX download, on the new host; same four on the old host.

## 3. What the cut-over script does

`/opt/scopewise/deploy/cutover-scopesense.sh` (idempotent; refuses to run without the cert files):
1. Caddy: backs up the Caddyfile, appends `deploy/caddy-scopesense.block` if `scopesense.in {` is absent, validates inside the container (`caddy validate --config /tmp/new --adapter caddyfile`), **truncate-writes** the live file (`cat … > Caddyfile`, never `mv` — bind-mount inode trap, see CLAUDE.md), `caddy reload`.
2. `.env`: backup; `NEXT_PUBLIC_API_URL=` (empty → same-origin); appends `https://scopesense.in,https://www.scopesense.in` to `CORS_ORIGINS` and `scopesense.in,www.scopesense.in` to `ALLOWED_HOSTS` if missing.
3. `docker compose … build web` (public URL is baked at build) and `GIT_SHA=$(git rev-parse --short HEAD) … up -d`.
4. Curls `/login` and the unauthenticated `/api/v1/codereview/reviews` on both hosts (expect 200 / 401).

Rollback: restore `Caddyfile.bak.<ts>` by truncate-write + reload; restore `.env.bak.<ts>`; rebuild web. The old host never depended on the new block, so a broken new block only affects `scopesense.in`.

## 4. After ~30 days (target 2026-10-12) — end of dual-run

- Caddy: replace the `scopewise.assessiq.in` block body with `redir https://scopesense.in{uri} 301` (keep its TLS/AOP stanza).
- SEO: `apps/web/app/layout.tsx` `metadataBase`, `app/page.tsx` `baseUrl`, the JSON-LD `item`/`url` fields in `app/product/*` and `app/compare/*`, sitemap and robots → `https://scopesense.in`; resubmit the sitemap in GSC; add the new property in GSC/GA4.
- Docs/kit: CLAUDE.md "Live deployment", `CODE_REVIEW_MODULE_REFERENCE.md` / `MITRE_MODULE_REFERENCE.md` URLs, the scan-kit README upload line, email templates if any mention the host.
- Google OAuth: old origin can be removed after the redirect has been live for a while.
- `.env`: `CORS_ORIGINS` / `ALLOWED_HOSTS` may drop the old host once the redirect is in place.

## 5. Gotchas learned

- Cloudflare zones cannot be created with a token lacking `com.cloudflare.api.account.zone.create`; the user added the site in the dashboard instead.
- Origin CA Key is deprecated; the `/certificates` endpoint works with a Bearer token that has Zone → SSL and Certificates → Edit, but **only for active zones**.
- IP-filtered tokens: force IPv4 on the VPS (`curl -4`); Python `urllib` picks IPv6 and fails with a misleading generic 401.
- The dashboard's "Add site" pre-creates DNS records from the parking page (an A record to `2.57.91.91`); always re-check records after adding a zone.

## Status 2026-09-13 evening: NOT live yet

Registry nameservers now point at Cloudflare (`ethan`/`nena`), but the zone still reports
`pending`, so Cloudflare serves DNS unproxied: `scopesense.in` resolves straight to
72.61.227.64, where Caddy has no `scopesense.in` block or certificate (the cut-over script has
not been run) — browsers get another site's 404, curl a TLS failure. Order to finish: (1) owner
presses **Check nameservers** on the zone overview (the API token cannot call
`activation_check`); (2) once `active`, issue the Origin certificate via the API from the VPS and
place it at `/opt/ti-platform/caddy/ssl/scopesense.in.{pem,key}`; (3) run
`/opt/scopewise/deploy/cutover-scopesense.sh`; (4) smoke with raw `curl --fail -o /dev/null -w
%{http_code}` per host, never trust a summarised table.

## Email: contact@scopesense.in on Hostinger (2026-09-13)

The mailbox was created in Hostinger hPanel. Hostinger's own DNS panel is not authoritative
(nameservers are Cloudflare's), so the records were added to the Cloudflare zone via the API
from the VPS (token over stdin, `curl -4`). All verified at `ethan.ns.cloudflare.com` and on
1.1.1.1 / 8.8.8.8 the same evening:

| Type | Name | Content | Note |
|---|---|---|---|
| MX | `@` | `mx1.hostinger.com` (5), `mx2.hostinger.com` (10) | DNS only |
| TXT | `@` | `v=spf1 include:_spf.mail.hostinger.com ~all` | only SPF on the apex |
| CNAME | `hostingermail-a/b/c._domainkey` | `hostingermail-a/b/c.dkim.mail.hostinger.com` | DNS only; keys resolve |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:contact@scopesense.in` | monitor first; tighten to `quarantine` after a few clean weeks |
| CNAME | `autoconfig`, `autodiscover` | `*.mail.hostinger.com` | mail-client setup |

Zone status was still `pending` in Cloudflare although the public NS already point there
(records are served regardless); the token lacks the `activation_check` permission, Cloudflare
re-checks on its own. If a resolver shows no DKIM/DMARC, it is negative caching from lookups
made before the records existed; query the authoritative NS to confirm. Hostinger hPanel:
Emails > contact@scopesense.in > DNS status should show all green; if its DKIM values ever
differ from the generic `hostingermail-*` ones, replace the three CNAMEs with the shown values.
Cross-checked 2026-09-13 through the Hostinger API (`GET /api/dns/v1/zones/scopesense.in`, key
`Hostinger_API_KEY` in the local `.env`): Hostinger's own zone holds the identical MX, SPF,
DKIM a/b/c, DMARC and autoconfig values, so the Cloudflare copy matches what Hostinger expects.
Its parked `A @ 2.57.91.91` is irrelevant (never move the nameservers back).

