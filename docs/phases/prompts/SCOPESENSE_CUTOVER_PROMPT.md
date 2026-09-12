# Kickoff prompt — finish the scopesense.in cut-over

Paste below the line into a fresh session at `E:\code\DocumentGovernancePlatform`
after the registrar has accepted the Cloudflare nameservers.

---

Finish the scopesense.in cut-over. Read first, in one burst: `CLAUDE.md`,
`docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md` (the runbook — everything is
staged, sections 2–3 are the remaining steps), and the memory
`scopesense-domain-cutover`. Decisions already made: dual-run for ~30 days
(no redirect until ~2026-10-12), product name stays ScopeWise, all
Cloudflare API calls run from the VPS over IPv4 with the token in the local
`.env` (passed via ssh stdin, never printed or committed).

Do, in order, verifying each step:
1. Confirm the zone is active (`nslookup -type=NS scopesense.in` shows
   Cloudflare; API zone status `active`). If still pending, stop and tell me.
2. Issue the Origin certificate with the API token (CSR/key already at
   `/root/scopesense-ssl/` on the VPS), install into
   `/opt/ti-platform/caddy/ssl/scopesense.in.{pem,key}`, verify key/cert match.
3. Run `bash /opt/scopewise/deploy/cutover-scopesense.sh`; confirm both
   hosts answer 200 on `/login` and 401 on the unauthenticated API call.
4. Remind me to add `https://scopesense.in` to the Google OAuth client, then
   smoke Google sign-in + one review + one download on both hosts.
5. Update `docs/planning/SCOPESENSE_DOMAIN_CUTOVER.md` status, CLAUDE.md,
   and add a handoff under `docs/phases/summaries/`. Commit docs by explicit
   path; no `git add docs/`. Set a reminder item for the 30-day end-of-dual-run
   tasks (runbook section 4).
