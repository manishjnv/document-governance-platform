# Inventory — Code Security Review, Admin, Login, cross-cutting (verbatim from the code sweep)

Source files: `apps/web/app/codereview/**`, `apps/web/app/admin/page.tsx`, `apps/web/app/login/page.tsx`,
`apps/web/components/RequestAccessForm.tsx`, `AppShell.tsx`, `install-prompt.tsx`, `service-worker-register.tsx`.

## Baseline

- Tokens today: primary #0066cc, muted-foreground 215 22% 32%, radius 0.5rem. Redesign replaces these with the
  canvas system; keep every label.
- Primitives: button (default/destructive/outline/secondary/ghost/link; h-10/h-9/h-11/icon), dialog (max-w-lg,
  overlay, X close with sr-only "Close"), sheet (right, w-3/4 sm:max-w-sm), tooltip, table, dropdown-menu, card, badge.
- **No toast library.** All messages are inline `role="alert"` / `role="status"` nodes. "Copied" flips back after 1500 ms.

---

# A. Code Security Review

## A1. `/codereview` — Review list (`codereview/page.tsx`)

Purpose: list every imported VVAH scan for the org plus shared demo reviews; search/sort; rename/delete; entry
points to the scanner kit and new-import flow.

Regions top → bottom:
1. Header row: `<h1>` **Code Security Reviews** with Bug icon (text-primary). Button **Get scanner** (sm outline →
   `/codereview/new`). Button **New review** (sm primary, Plus icon → `/codereview/new`).
2. Page error: `role="alert"` destructive panel, text = API detail or **Failed to load reviews**.
3. Filter bar (only when items exist): `<input type="search">` placeholder **Search by name or repo…**,
   aria-label **Search reviews by name or repo**, h-8 w-56; filters on name OR repo_label. `<select>` aria-label
   **Sort reviews**, options **Newest** / **Oldest** / **Most findings** / **Name** (default newest).
4. Action error: `role="alert"` text-xs destructive (rename/delete failures): **Could not rename the review** /
   **Could not delete the review**.
5. Loading skeleton: 3 pulse cards in `grid gap-3 sm:grid-cols-2 xl:grid-cols-3`.
6. Empty state (no items): muted panel, Bug icon 28, copy verbatim:
   "Run the Visa Vulnerability Agentic Harness scan on your repo and upload its findings.json to get a reviewable
   findings register plus client-ready XLSX and PPTX deliverables." then "Built on Visa's open-source Vulnerability
   Agentic Harness (Apache-2.0). ScopeWise is not affiliated with or endorsed by Visa, Inc." then buttons
   **Get scanner** (outline) + **New review**.
7. No-match state: **No reviews match your search.**
8. Card grid: each card `role="link" tabIndex=0` aria-label `Open review {name}`, Enter/Space navigates, hover border.

Card anatomy: title (truncate, semibold); meta line: repo_label, short SHA pill (7 chars, mono, tooltip = full
SHA); **Demo** badge (sky, tooltip **Shared sample review — visible to every signed-in user, read-only**);
kebab (only when editable) aria-label `Actions for {name}`, items **Rename**, **Delete** (destructive); severity bar
(one segment per non-zero severity, tooltip **No findings** or e.g. `3 critical · 5 high`); severity sentence
(counts + lowercase label, `·` separated, or **No findings**); footer: `{total} finding(s)`, source-format pill
(**findings.json** or **SARIF**, tooltip **Import source format**), right-aligned date.

Dialogs: **Rename review** (max-w-sm, autofocused input aria-label **New review name**, Enter submits; footer
**Cancel** / **Save** disabled when blank). **Delete review**: body `Delete "{name}"? This can't be undone.` footer
**Cancel** / **Delete** (destructive).

Severity colours (SEVERITY_META): critical rose, high orange, medium amber, low emerald, info sky.

## A2. `/codereview/new` — New review / get scanner (`codereview/new/page.tsx`)

Layout `max-w-3xl`, `<h1>` **New code security review**, two cards side by side (`md:grid-cols-2`, stacked below).

Card 1 — **1 · Get the scanner**
- Primary button **Download scan kit** (Download icon; Loader2 spinner while busy, disabled). Tooltip: **Zip with
  the scanner, setup + run scripts and README (~1 MB). Unzip it, do not pip install it.** Saves
  `scopewise-scan-kit-v1.3.0.zip`. Error **Could not download the scan kit**.
- Version pill **VVAH v1.3.0** (tooltip **Pinned Visa Vulnerability Agentic Harness release inside the kit**).
- Numbered steps (number chips):
  1. "Unzip the kit, then run `.\setup.cmd` (Windows, double-click works) or `setup.sh` (macOS/Linux) — it installs
     the scanner and asks for your OpenRouter key"
  2. "Run `.\scopewise-scan.cmd <repo>` / `scopewise-scan.sh <repo>` — shows the cost estimate, then scans after you
     confirm"
  3. "Upload the `scopewise-scan-*.zip` it produces here"
  (inline code chips). **There are no OS tabs and no repo field.**
- Divider with words **or run VVAH directly**.
- Command block `<pre>`: `vvaharness scan --repo /path/to/repo --stop-after s9`; copy button aria-label
  **Copy command** (Copy icon); transient **Copied** (1500 ms).
- External link **Visa Vulnerability Agentic Harness** → github.com/visa/visa-vulnerability-agentic-harness.
- Footer note (Info icon): **Findings are AI triage candidates from your scan; nothing runs on ScopeWise.**
  (desktop under card 1; on mobile repeated under card 2).

Card 2 — **2 · Upload the results**
- Label **Name (optional)** ("(optional)" muted), input id `review-name`, placeholder **e.g. Q3 backend security scan**.
- Dropzone (when no file): `role="button"`, aria-label **Scan report: choose a file or drag it here**, dashed
  border, drag-active primary tint; contents UploadCloud icon, **Drag & drop or click to select**, and
  **findings.json, .sarif or the scan zip · up to 10 MB**.
- Selected-file row (FileRow): emerald tint, FileJson icon, truncated filename, size (KB/MB), remove button
  aria-label `Remove {file.name}` (X icon).
- Guards: **Scan report: only .json, .sarif, .zip files are supported** / **Run manifest: only .json files are
  supported** / **Scan report: file must be under 10 MB** / **Please add your findings.json, .sarif or scan zip
  file first**. Error paragraph `role="alert"` text-xs destructive under the dropzone.
- Optional manifest: dashed full-width button **+ Add run_manifest_*.json (optional)**; when set, same FileRow.
- Submit **Import and review →** (disabled without file), busy = Loader2 + **Parsing…**. Error fallback **Upload failed**.

## A3. `/codereview/[reviewId]` — Review detail

States: error → single `role="alert"` panel **Failed to load the review** replacing the page. Loading → skeleton:
5 tiles `grid-cols-3 sm:grid-cols-5` + 6 row bars.

Regions:
1. Header: back link **← Reviews**; `<h1>` Bug icon + name; **Demo** pill (tooltip **Shared sample review —
   read-only for everyone**); inline rename button aria-label `Rename {name}` (Pencil) only when editable.
   Rename mode: autofocused input aria-label **New review name**, Enter save, Escape cancel; Check button
   aria-label **Save name** (emerald), X button aria-label **Cancel rename**. Error **Could not rename the review**.
   Meta pill row: source-format pill (tooltip **Original scan output format**), short-SHA pill (tooltip full SHA),
   timestamp (tooltip **When this review was imported**).
   Actions: **XLSX** (outline sm, Download icon, aria-label **Download XLSX register**), **PPTX** (aria-label
   **Download PPTX briefing deck**), kebab aria-label **More actions** → item **Copy link** (Copy icon) → **Copied**.
2. Download error line: **Failed to download the XLSX export** / **Failed to download the PPTX export**.
3. Degraded banner (amber, dismissible X aria-label **Dismiss**): bold **Scan degraded.** + degraded_reason.
4. ReviewBand tiles (`grid-cols-3 sm:grid-cols-5`): **Total findings** (tooltip **All findings reported for this
   scan.**), **Critical** (rose, tooltip **Critical-severity findings. Click to filter the table.**, click filters),
   **High** (orange, same pattern), **Exploit chains** (tooltip **Findings the scanner linked into a multi-step
   attack path.**), **Verifier false positives** (muted, tooltip **Findings the AI verifier marked as false
   positive.**). Headline sentence: **No findings were reported for this scan.** or
   `Confirm the {n} {severity} finding(s) first · {k} of {total} findings sit in {topFile} · {c} exploit chain(s)
   link findings together.`
5. SeverityStrip chips: **All {n}** (tooltip **Show every severity.**), **Critical**, **High**, **Medium**,
   **Low**, **Info** each with count and tooltip `Show only {label}-severity findings.`; inactive opacity-70;
   active ring; clicking active clears.
6. Tabs `role="tablist"`: **Findings**, **Exploit chains ({n})**, **Scan details**.
7. Footer attribution: **Findings produced by Visa Vulnerability Agentic Harness (Apache-2.0). AI-generated triage
   candidates — confirm before acting.**

Sort model: keys idx | severity | title | vuln_class | cwe | cvss_score | confidence | file; default severity asc
(severity order then CVSS desc); clicking active header flips; new header resets asc.

## A4. Findings tab (`FindingsTable.tsx`)

Filter bar: search input placeholder **Search title, file, or CWE…** aria-label **Search findings by title, file,
or CWE**; class select aria-label **Filter by vulnerability class** (first **All classes**, then classes);
verdict select aria-label **Filter by verdict**: **All verdicts** / **Confirmed** / **False positive** / **Unverified**.

Desktop table (sortable headers with ArrowUp/ArrowDown/ArrowUpDown, sticky):
`#` | `Severity` (dot + label) | `Title` (line-clamp-2) | `Class` | `CWE` (link to cwe.mitre.org when CWE-n) |
`CVSS` (right, mono) | `Confidence` (bar, aria-label `{pct}% confidence`, tooltip `{pct}% · {votes} vote(s)`) |
`File:lines` (mono, tooltip same) | `Verdict` (not sortable: chip **Confirmed** tooltip **Verifier: true
positive** / **False positive** tooltip **Verifier: false positive** / `—`).
Row: `role="button"`, aria-label `Open finding {idx}: {title}`, click/Enter/Space opens drawer; **ArrowDown /
ArrowUp move focus between rows**. Zebra `bg-muted/30` on odd rows (design: drop zebra, keep hover).
Empty: **No findings match your search or filter.** Mobile card rows: title + severity dot/label, `file:start-end`.
Footer: `Showing {rows} of {total} finding(s)`.

## A5. Finding drawer (`FindingDrawer.tsx`)

Right sheet, default 560/`sm:max-w-xl` (576), resizable: grip `role="separator" aria-orientation="vertical"`
aria-label **Resize panel (drag, or use arrow keys)**, title **Drag to resize**; ArrowLeft widens 40px,
ArrowRight narrows; min 380, max 95vw. Deep link `?finding=N`.
Header: `#{idx}` mono + severity chip (tooltip `{Label} severity (scanner-assigned)`) + title; sub-line class label.
Quick-fact chips (2 cols, 3 on sm), label uppercase 10px:
`CWE` (link + ExternalLink icon, tooltip **Common Weakness Enumeration entry — opens the MITRE definition.**) ·
`CVSS` (`{score} · {rating}`, tone ≥9 rose, ≥7 orange, ≥4 amber, else emerald; tooltip `Vector: {cvss_vector}` or
**CVSS 3.1 base score**) · `Confidence` (bar + pct, tooltip `{pct}% from {votes} model vote(s)`) · `Verdict`
(chip or `—`, tooltip **Verifier: true positive (n/10)** / **…false positive** / **Not reviewed by the
verifier**) · `File` (col-span-2, tooltip `{file} lines {start}–{end}`) · `Source → Sink` (source sky, arrow
muted, sink rose, tooltip **Where attacker-controlled data enters (source) and where it does damage (sink).**).
Verdict reason callout (emerald left border) when present.
Sections in order (each: colour swatch, uppercase 11px heading, hint tooltip): **What is wrong** (rose; hint
**The weakness the scanner found, in plain words.**) · **Why it matters** (orange; **What an attacker gains if
this is real.**) · **How to fix** (emerald; **Suggested remediation — verify before applying.**) · **How it is
exploited** (amber; **A concrete attack path the scanner reasoned about.**) · **Preconditions** (slate; **What
must already be true for the attack to work.**; bulleted) · **Code** (slate-700; hint `{file}, starting at line
{n}`; `<pre>` with line-number gutter) · **Exploitability** (amber-300; **How easy the scanner thinks this is to
exploit in practice.**) · **Verifier reasoning** (emerald-300; **The second-pass model's reasoning for its
verdict.**) · **Also at** (slate-300; **Other locations with the same pattern.**; mono list).
Rich text: sentences become bullets when >1; inline code chips; keyword highlighting (risk words rose semibold:
unauthenticated, attacker, injection, bypass, hard-coded, plaintext…; fix words emerald semibold: rate-limit,
sanitize, validate, encrypt, HttpOnly, least privilege…).
Sticky footer: **Prev** (ChevronLeft, tooltip **Previous finding in the current list**), counter
`{position} of {n}`, **Copy link** / **Copied** (tooltip **Copy a link that opens this finding directly**),
**Next** (tooltip **Next finding in the current list**).

## A6. Exploit chains tab (`ChainsTab.tsx`)

Empty: **The scanner did not link any findings into an exploit chain.** Card per chain: title + severity chip
(tooltip **Chain severity (highest step)**); step pills `#{idx}` (buttons → drawer) separated by `→`; narrative
paragraph. (Design adds the interactive attack graph from the hero canvas above the cards.)

## A7. Scan details tab (`ScanDetailsTab.tsx`)

Two columns of definition lists. **Scan metrics**: Files in scope · Files analyzed · Duration (`{n}s`) · Tokens ·
Verifier true positives · Verifier false positives · Degraded reason (**Not degraded**) · Dropped findings · Raw
findings before dedup. **Run manifest**: **not uploaded** or Target git sha · VVAH version · `{role} model` rows
(`{id} ({provider})`) · Total cost · Total tokens. **Ingest notes**: bullet list or **none**. **Scanner summary**:
pre-wrapped text when present. Headings 11px uppercase.

---

# B. Admin (`/admin`)

Gating: platform admin only (else redirect). Auto-refresh every 60 s while visible.
1. Header `<h1>` **Admin** with ShieldCheck; right: `Last updated {timeAgo}` (**Never** / **Just now** / `{n} min
   ago` / `{n} hour(s) ago` / `{n} day(s) ago` / `{n} month(s) ago`) + **Refresh** (sm outline, RefreshCw spins
   while loading).
2. Page error `role="alert"`: **Could not load the admin overview.** / **Something went wrong.**
3. Loading: **Loading…**
4. KPI tiles (`grid-cols-2 sm:grid-cols-3 lg:grid-cols-5`): **Members** (sub `{n} active`), **Sign-ins this week**
   (sub `{n} in the last 30 days`), **Documents** (sub `{n} added this week`), **AI reviews** (sub `{n} this
   week`), **Issues found** (sub **across all reviews**).
5. **Organisations** card. Blurb verbatim: "Free-tier organisations can upload and configure but cannot start
   reviews or MITRE assessments. Grant a number of runs, or set pro/enterprise for unlimited. Requests arrive by
   email with source assessment_request / review_request." Org errors: **Could not load organisations.** /
   **Could not update the tier.** / **Could not update the run allowance.** States **Loading…** / **No
   organisations yet.** Table columns: **Organisation** | **Tier** (pill: free plain border; pro/enterprise
   primary tint, uppercase 10px) | **Runs** (free: number input min 0 max 1000 aria-label **Runs to grant** +
   **Set** button; else **Unlimited**) | **Members** (right) | **Created** (dd/mm/yyyy) | **Actions** (select
   aria-label `Tier for {org.name}`: free / pro / enterprise).
6. **People** card: search box placeholder + aria-label **Search people…**. Columns: **Name** | **Email** |
   **Role** | **Workspace** | **Status** (pill **Active** green / **Suspended** grey) | **Joined** | **Last
   sign-in** | **Documents** (right) | **Reviews** (right) | **Last active**. (No empty state today — design one:
   **No people match your search.**)
7. Two-up: **Recent sign-ins** (search **Search sign-ins…**; empty **No sign-ins recorded yet.**; lines
   `**{who}** · {how} · {device} · from {ip}` + timeAgo right, scroll cap) · **Recent activity** (search
   **Search activity…**; empty **Nothing yet.**; lines `**{who}** — {what}`).
8. **AI usage** card tiles: **Reviews finished**, **Reviews failed**, **Checks per review**, **AI calls
   (approx.)** (sub **finished reviews × checks**), **Average review time** (`{n}s` or `—`), **Last review**
   (timeAgo). Below: `AI models in use: {list}`.

Prod sample data (real org list, 12 Sep 2026): Default Org (manishjnvk@gmail.com, platform admin); starshrishail's
Workspace; manishkumarjnvk's Workspace; manishjnvk1's Workspace; veena9jan's Workspace; urdineshnaidu's Workspace;
hemantsawant48's Workspace; talk2maq's Workspace; rajendra19sep's Workspace — all free, allowance 0.

---

# C. Login (`/login`)

Centred card (max-w-md) on muted background, no AppShell. Header: ShieldCheck + **ScopeWise**; description
**Catch contract risk before you sign.** Error panel `role="alert"` destructive tint.
Google sign-in button (rendered by Google, outline, large, 336px); placeholder **Loading Google sign-in…**
(pulse, 44px). Divider chip **Or sign in with a code**.
Step 1: sr-only label **Your email address**; input placeholder **you@example.com**; button **Email me a sign-in
code** → busy **Sending your code...**; helper **We'll email you a 4-digit code — no password needed.** Error
fallback **Failed to send code**.
Step 2: copy `Enter the 4-digit code sent to **{email}**.`; 4-char input (tracking wide, centred, numeric,
maxLength 4, autoFocus, **auto-submits on the 4th digit**); eye toggle aria-label **Show code** / **Hide code**;
**Verifying...**; error **That code didn't match. Please try again.**; link **Use a different email**.

---

# D. Cross-cutting

- **RequestAccessForm**: heading **Request access to run assessments** (suppressed inside the dashboard dialog
  whose title is **Request access to run reviews**); copy **Running a review or assessment is switched on per
  organisation. Send us your details and we will enable it.**; fields **Name**, **Work email**; hidden honeypot
  **Website**; button **Request access** → **Sending...**; success `role="status"` **Thanks. We will enable
  assessments for your organisation and email you.**; error **Could not submit -- please try again.**
- Gate copy from the API (403): **Assessments are not enabled for your organisation yet. Use the request-access
  form to contact us and we will switch it on.** / **Your organisation has used all of its granted runs. Use the
  request-access form to ask for more.**
- Runs remaining hint: `{n} run remaining for your organisation` / `{n} runs remaining for your organisation`.
- Demo badge: **Demo**, sky tint; tooltips vary per page (list: **Shared sample review — visible to every
  signed-in user, read-only**; detail: **Shared sample review — read-only for everyone**; MITRE: **Shared sample
  assessment — visible to every signed-in user, read-only** / **Shared sample assessment — read-only for
  everyone**). Demo/uneditable rows hide rename/delete/archive controls.
- App bars: service worker **A new version is available.** + **Reload** (top, primary); PWA install card
  **Install ScopeWise for offline access** + **Install** / **Dismiss** (bottom centre). Skip link **Skip to main
  content**.
- AppShell: brand FileText + **ScopeWise**, tagline **Catch contract risk before you sign.**, nav **SOW Review**
  (LayoutDashboard, /dashboard), **MITRE Assessment** (Target, /mitre), **Code Security Review** (Bug,
  /codereview), **Admin** (ShieldCheck, platform admin only). Collapsed 56px / expanded 224 (drag 180–400);
  toggle aria-label **Expand sidebar** / **Collapse sidebar**; **Log out**. Mobile: top bar + Menu button
  aria-label **Open navigation menu** → left sheet with the same nav, close X sr-only **Close**.
- Keyboard: Enter/Space activate cards, rows, dropzones; ArrowUp/Down row focus in the findings table;
  ArrowLeft/Right resize drawers; Enter save / Escape cancel on renames; Radix Escape closes dialogs/sheets.
