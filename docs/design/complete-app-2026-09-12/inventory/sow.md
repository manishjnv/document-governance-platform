# Inventory — SOW & RFP Review screens (verbatim from the code sweep)

Source files: `apps/web/app/dashboard/page.tsx` (992 lines), `upload/page.tsx`, `results/[reviewId]/page.tsx`
(876 lines), `projects/[id]/page.tsx`, `versions/diff/page.tsx`. `/search` is a redirect to the dashboard.
`/projects` and `/versions` index routes do not exist.

---

## 1. `/dashboard` — SOW Review home

Purpose: org documents grouped by project with version history, global full-text search, type filter, per-row
review/view/version/delete actions, version-link suggestions, run-allowance hint, request-access gate.

### 1.1 Header row
- `<h1>` **SOW Review**.
- Runs-remaining hint (only when a number): `{n} run remaining for your organisation` / `{n} runs remaining for
  your organisation`.
- Search box: Search icon; input placeholder **Search all documents...**, aria-label **Search all documents**,
  w-64; clear button (X) aria-label **Clear search** when non-empty.
- Button **Upload Document** (→ /upload).

### 1.2 Search mode (replaces everything below while the query is non-empty; 300 ms debounce)
- Bar: `Search results ({total}) for "{query}"` (total omitted while loading) + spinner (Loader2).
- Error: **Search failed. Please try again.**
- Empty: `No documents match "{query}"`.
- Table columns: **Filename** · **Type** (fallback **Unknown**) · **Relevance** (`{pct}%`) · **Snippet**
  (truncated, highlighted terms bold) · **Uploaded** · **Actions** = **Review** (→ **Reviewing... (~20s)**) ·
  **View**. No pagination.

### 1.3 Version-link suggestion banners (blue tint)
`**{filename}** looks like it could be a new version of **{suggested_filename}** (v{n}) -- link as v{n+1}?`
`({pct}% similar)`. Actions **Link as v{n+1}** · **Dismiss**.

### 1.4 Stats + filter row
- Stats strip: **Total {n}** then **SOW {n}**, **Proposal {n}**, **RFP {n}**, **Other {n}**.
- Label **Filter by Type** + select: **All Types**, **SOW**, **Proposal**, **RFP**, **Other**.

### 1.5 Error banner (red tint)
API detail or: **Failed to fetch documents**, **Failed to update suggestion**, **Failed to assign project**,
**Failed to set document type**, **Failed to trigger review**, **Failed to load review**, **Failed to delete
document**, **No review yet for this document -- click Review first**.

### 1.6 States
- Loading: **Loading documents...**
- Empty: **No documents uploaded yet** + button **Upload Your First Document**.
- Gated: clicking Review with assessments disabled opens the request-access dialog; server 403 texts also appear
  in the red banner.
- Disabled: row actions except New version / Assign project disabled while a review is running.

### 1.7 Main table
Columns: **Filename** · **Type** · **Completeness** · **Accuracy** · **Uploaded** · **Actions**.
Project group band (colSpan row, muted tint): toggle button (ChevronRight rotates 90°, aria-expanded) +
FolderOpen icon + project name + `· {docCount}`; right side `Avg score {n}` · `{n} critical` red pill (only when
>0) · link **View project**. Ungrouped bucket label **No Project** (no stats/link).
Document rows (grouped by document_group_id, newest first): expander (only if >1 version) ChevronRight aria-label
**Collapse versions** / **Expand versions**; chip `v{n} ({count} versions)`. ScoreCell: `-` when null; ≥80 green,
≥50 yellow, else red. TrendIndicator (Accuracy, latest row only, hidden when |delta|<0.5): ArrowUp green /
ArrowDown red, title `+{d} vs previous version`. Uploaded date. Expanded child rows: muted tint, filename
`v{n} -- {original_filename}`.
Row actions (`•` separated links): **Review** (→ **Reviewing... (~20s)**) · **View** · **New version** ·
**Assign project** (only when no project) · **Compare vs v{n}** · **Delete** (destructive).
Inline editors: DocumentTypeCell (click type text, title **Click to change**; select with disabled placeholder
**Select type** + SOW/Proposal/RFP/Other). AssignProjectControl: button **Assign project** → input placeholder
**Project name** backed by a datalist of project names + **Save** / **Cancel**; Enter submits, Escape cancels.

### 1.8 Dialogs
- Request-access dialog: title **Request access to run reviews** + RequestAccessForm (heading suppressed).
- Delete: today `window.confirm` **Permanently delete this document, its reviews, and all findings? This cannot
  be undone.** — design a destructive Dialog with this sentence, **Cancel** / **Delete**.

Icons: ArrowDown, ArrowUp, ChevronRight, FolderOpen, Loader2, Search, X. Responsive today: table scrolls
horizontally on phones (design: card rows).

Sample data from prod (12 Sep 2026): projects Acme (1 doc: sample_rfp.docx RFP, not reviewed), ConflictTest (2:
Subtle_Conflicts_Test.docx v2, 2 versions, accuracy 12 ▲), NovaRetail Software Solutions (7: SOC_SOW_Testing.docx
v6 6 versions accuracy 10 ▼ compare vs v5; SOC_SOW_Testing.docx v1 accuracy 12), RFPValidation (1: rfp_sample.pdf
RFP completeness 29 accuracy 25). Avg scores 0 / 8 (2 critical) / 13 (7 critical) / 25 (1 critical).

---

## 2. `/upload`

- Back link ArrowLeft **Back to SOW Review**.
- Card title **Upload Document** (or **Upload New Version** in `?version_of=` mode); description **Upload a SOW,
  Proposal, or other document for review** (or **This file will be linked as the next version of the source
  document.**).
- Project field (hidden in version mode): label **Project** + red `*`. Preset variant: chip row with project name
  (fallback **Selected project**) + **Change**. Free variant: input placeholder **Select existing or type a new
  project name** with datalist; helper **Pick an existing project from the list, or type a new name to create one.**
- Dropzone: dashed, `role="button"`, aria-label **Choose a document to upload, or drag and drop it here**;
  UploadCloud icon; `<h3>` **Drag and drop your document**; **or click to select**; **PDF, DOCX, DOC, XLSX, XLS, or
  CSV • up to 50MB**. Enter/Space opens picker. Drag-active primary tint.
- Selected-file pill (green): `**Selected:** {name} ({MB} MB)`.
- Errors (`role="alert"`): **Only PDF, DOCX, DOC, XLSX, XLS, and CSV files are supported** · **File size must be
  less than 50MB** · **Please select a file** · **Unable to determine your organization -- try refreshing the page**
  · **Choose an existing project or type a new project name** · **Failed to load user info** · **Upload failed**.
- Success (`role="status"`, emerald): `Uploaded as version {n}` or `Document uploaded successfully: {filename}`;
  redirects to /dashboard after 2 s.
- Submit button full width **Upload Document** → **Uploading...**; disabled when no file / uploading / no project.

---

## 3. `/results/[reviewId]` — Review results (AppShell fullWidth)

States: loading **Loading review...**; error panel `{error}` or **Review not found** + link **Back to Dashboard**;
fallbacks **Failed to fetch review**, **Failed to load report**, **Failed to download PDF report**, **Failed to
update finding**.

### 3.1 Header
`<h1>` **Review Results** + right link ArrowLeft **Back to Dashboard**. Meta line: `**{original_filename}** ·
Project: {project_name} · {document_type} · {n} page/pages · Uploaded {date}`.

### 3.2 Actions bar
**Hide Document** / **Show Document** (outline sm, FileText; only when parsed sections exist) · **Download PDF**
(outline sm) · **View Full Report** (primary sm).

### 3.3 Scorecards (2 columns)
- **Overall Score** + HelpCircle tooltip (aria-label **What does this mean?**): *How complete and well-written this
  document is (0-100), across scope, clarity, commercial terms, delivery, and more. Higher is better.* Value
  (`.toFixed(1)`) ≥80 green / ≥60 yellow / else red; progressbar aria-label **Overall score**.
- **Risk Level** + tooltip: *How much this document could hurt you if signed as-is -- combines how severe the
  issues are and how many there are. Higher is worse.* Value `{n}%`; band >70 red **High**, >40 yellow **Medium**,
  else green **Low**.

### 3.4 Risk by Area card
Title **Risk by Area** + tooltip: *The same risk score, split by area (Legal, Commercial, Delivery, etc.) so you
can see what's actually driving it. Click an area to filter the findings below to just that area.* When filtered:
**clear filter** link. Rows sorted desc: toggle buttons (active ring), axis label, bar (>70 red / >40 yellow /
green, width transition), value `{n}%`. Axes: Compliance, Security, Governance, Scope, Legal, Commercial, Delivery.

### 3.5 Document X-Ray card
Title **Document X-Ray** + tooltip: *A quick scan of the document itself: which sections it has, and which required
sections/checks are missing.* Two columns: **Sections Found ({n})** (headings with ` (p.{n})`) and **Gaps Detected
({n})** (red items, or **None -- passes all rule checks.**).

### 3.6 Findings Summary card
Title **Findings Summary** + tooltip: *Every issue found, grouped by how serious it is. Click a number to filter
the list below to just that severity.* + **clear filter**. Five tiles (toggle filters): **Critical** (red),
**Major** (orange), **Medium** (yellow), **Low** (blue), **Info** (grey).

### 3.7 Findings card
Title **Findings** + `({visible} of {total})` when filtered. Empty: **No findings in this filter.**
Finding row (collapsed header button, aria-expanded): severity-tinted container (critical red / major orange /
medium yellow / low blue / info grey), resolved rows opacity-60. Contents: severity badge (uppercase 9px, solid
colour, text = severity), risk-area chip, **Fixed** pill (green, Check icon) + strikethrough title when resolved,
evidence-type chip (evidence_type with spaces), title (fallback category or **Finding**), section-jump button
MapPin + `{section_ref}` (stopPropagation, scrolls the document pane), chevron rotates when expanded.
Expanded body sub-headings (uppercase): **Description** · **Document Text** (blockquote, only if matched_text) ·
**Recommendation** · **Confidence** (`{n}%`) · status button **Mark Fixed** (Check) ↔ **Reopen** (RotateCcw).
Inline section links inside text: `Section 4.2`, `§4.2`, `Appendix B` become MapPin buttons with title
`Jump to "{heading}" in the document`.
Evidence highlight: jumping scrolls the section into view (smooth, centred), tints it yellow for 2 s.

### 3.8 Audit footer
`Models: {list} · Rules {rules_version} · Doc SHA-256 {12 chars}… · Build {8 chars}` (11px muted).

### 3.9 Split pane
Left pane width `{splitPercent}%` (default 33), divider (mouse drag, clamp 20–80%, hover/active primary tint),
right pane sticky card titled **Document** with sections `{heading}` + `p.{n}` and pre-wrapped content. Stacks on
phone; divider hidden.

Sample data from the SOW hero canvas: SOC_SOW_Testing.docx v6, NovaRetail Software Solutions; findings §4.1
Deliverables lack acceptance criteria (Major, Scope), §4.2 Unlimited change requests at no cost (Critical,
Commercial), §4.3 Timeline uses "approximately" (Medium, Delivery), §4.4 No liability cap referenced (Major, Legal),
§4.5 Reporting cadence unspecified (Low, Governance), §4.6 Data handling clause is silent on residency (Medium,
Security); clause texts for §4.1–§4.6 as in `docs/design/hero-views-2026-09-12/Main.dc.html`.

---

## 4. `/projects/[id]` — Project detail

- Loading **Loading project...**; error `{error}` / **Project not found** / **Failed to load project**.
- Header: back link **← Dashboard**; `<h1>{project.name}</h1>`; right button **Upload to this project**.
- Metric tiles: **Documents** · **Average score** (`-` when null) · **Open critical findings**.
- Table: **Filename** · **Type** (fallback **Unknown**) · **Score** (`-` when null) · **Uploaded**. (No empty state
  today — design one: **No documents in this project yet.** + **Upload to this project**.)

---

## 5. `/versions/diff` — Version comparison

- Header: **← Dashboard** link; `<h1>` **Version Comparison**; subtitle `v{older} → v{newer}`.
- Loading **Loading...**; errors **Missing doc_id or other_version in the URL** / **Failed to load version diff**.
- Three columns (stack on phone): **Resolved ({n})** green — empty **Nothing resolved.** · **New ({n})** blue —
  empty **No new findings.** · **Persisted ({n})** red — empty **Nothing persisted.**
- FindingCard: severity-tinted border/background (critical red, major orange, medium yellow, default muted);
  `{title}` bold; `{category} -- {section_ref}` small.

---

## 6. Cross-cutting inconsistencies the design unifies
- Three severity palettes (results row tint, results badge, diff card) → one ramp.
- Score thresholds ≥80/≥50 (dashboard) vs ≥80/≥60 (results) → one band set.
- Three resize implementations → the `useSheetResize` behaviour everywhere.
- `window.confirm` deletes → destructive Dialog with the same sentence.
- Tables scroll on phones → card rows everywhere.
