# Kickoff prompt — generate MITRE sample test data (covers every module path)

Self-contained kickoff. Paste everything below the line into a fresh
session. Goal: produce populated, upload-ready sample files that exercise
EVERY part of the MITRE module end to end (there is no real customer data
yet). These are richer than the blank templates in
`apps/web/public/templates/` — they are fully populated test fixtures.

---

Generate a MITRE assessment sample-data kit under `docs/sample/MITRE_Sample/`
that a human can upload to test the whole module. Build a repeatable
generator (`scripts/generate_mitre_samples.py`, openpyxl — already
installed) so the kit can be regenerated when ATT&CK is re-pinned.

## Hard correctness rule

**Every MITRE technique ID in the samples must be validated against the
pinned dataset** — import `app.mitre.attack_data` (v19.1
`apps/api/app/mitre/data/attack.json`) and assert each ID resolves before
writing it, EXCEPT the deliberately-bad ones below (which must be chosen to
actually be invalid/revoked/deprecated in v19.1). Pick real ICS and Mobile
technique IDs from the dataset for the ICS/Mobile rows — don't guess.
After writing, round-trip every file back through the real parsers
(`app.mitre.ingest.parse_use_case_file` / `parse_environment_file`) and
print the detected column map + tagged/untagged/invalid split to prove the
kit ingests cleanly.

## Read first

`app/mitre/ingest.py` (COLUMN_SYNONYMS + SHEET_SYNONYMS — match the sample
headers to what auto-detection recognizes), `app/mitre/keyword_tag.py` +
`data/keyword_aliases.json` (so the "keyword-taggable" rows use strings the
pre-pass actually matches), `app/mitre/attack_data.py`,
`docs/planning/MITRE_MODULE_REFERENCE.md`.

## Deliverables (in `docs/sample/MITRE_Sample/`)

### 1. `usecases_primary.xlsx` — the main detection-rule dump

Template-aligned headers (Use Case Name, MITRE Technique IDs, Detection
Logic, Description, Log Source, Status). ~30 rows deliberately spanning
every tagging + coverage path:
- **Customer-tagged, valid IDs, enabled** → `customer_tagged`, `covered`.
- **Customer-tagged but DISABLED** (Status=disabled) → `partial` (default
  policy) — proves the disabled-rules toggle.
- **A revoked ID** (pick one revoked in v19.1, e.g. verify T1562.001's
  status) → remap note in assumptions.
- **A malformed/unknown ID** (`T9999`, `banana`) → `invalid` + note.
- **A deprecated ID** (find one in the dataset) → deprecated note.
- **Untagged, keyword-matchable** rows whose name/logic contain alias
  strings from `keyword_aliases.json` (mimikatz, `schtasks /create`,
  powershell `-enc`, rundll32, wmic, `vssadmin delete`, `wevtutil cl`,
  certutil, nltest, rclone) → `keyword_tagged`, no LLM.
- **Untagged, genuinely non-keywordable** free-text (impossible-travel
  login, UEBA beaconing anomaly, DLP volume spike) → the AI residue path
  (or `unmapped` if the key/LLM is unavailable — note both outcomes).
- **A row with BOTH description and logic populated** → proves Phase 7
  logic persistence + Phase 12 telemetry-match strength.
- **A row with logic present vs one with logic absent** on the same
  technique → shows detection-strength differences (Phase 12).
- **Parent + sub-technique rows** (e.g. T1059 and T1059.001) → sub-technique
  rollup.
- **ICS-technique rows and Mobile-technique rows** (real IDs) → those
  domains show coverage when the environment makes them applicable.
Add a `# feature exercised` note per row in an extra rightmost column the
parser ignores, so a human reading the file sees what each row tests.

### 2. `environment_full.xlsx` — makes all three domains applicable

Sheets Assets / Log Sources / Security Tooling / Crown Jewels
(names matching SHEET_SYNONYMS). Populate so:
- Assets include Windows, Linux, macOS, Entra ID/Azure AD, AWS, M365,
  containers/Kubernetes, **OT/ICS assets** (gates ICS applicable) and a
  **managed mobile fleet + MDM** (gates Mobile applicable).
- Log Sources: Windows Event Logs, Sysmon, EDR telemetry, identity/auth,
  DNS, cloud audit, MDM, OT telemetry — enough that some gaps bucket
  **short-term** (telemetry already onboarded).
- Security Tooling: EDR, email security, NDR, DLP, IAM/PAM — so other gaps
  bucket **mid-term** (ownable telemetry).
- Crown Jewels: a few critical systems.

### 3. `environment_windows_only.xlsx` — the gating contrast

Windows + identity only; NO OT/ICS, NO managed mobile. Uploading this
instead of #2 makes **ICS and Mobile whole-domain N/A with reason**, and
platform-filters macOS/Linux techniques → exercises the applicability
engine and the N/A appendix (derived-domain + derived-platform).

### 4. `usecases_v2_improved.xlsx` — for trend/compare

A second dump ~= primary but with 3–4 more techniques covered (add tags /
enable a disabled rule), so running two assessments and comparing shows
**newly-covered / regressed / delta** (Phase 4 trend).

### 5. `usecases_messy_headers.xlsx` — for the column wizard

Same data as primary but headers auto-detection will miss (tags under
"Ref Codes", name under "Rule Title") → exercises the Phase 9
column-mapping wizard (the user maps columns by hand).

### 6. (Optional) `usecases_primary.csv` and a small `usecases_scanned.pdf`

CSV to exercise the csv ingest path; a short text PDF (reportlab/weasyprint
if available, else skip and note) to exercise Phase 2 extraction mode.
Skip `.xls` — no xls writer is installed; note that.

### 7. `README.md` — the test playbook

A table mapping each file (and the key rows) → the feature it exercises,
PLUS the **on-screen intake values** to enter for a full-coverage run:
- Industry = one with a threat profile (e.g. Healthcare or Financial
  Services — check `app/mitre/data/threat_profiles.json`) → exercises
  Phase 11 threat weighting.
- Threat actors = a couple from the catalog (e.g. FIN7, Lazarus).
- Scope exclusion = e.g. "T1200 Hardware Additions — accepted risk,
  physical controls" (with reason) → exercises declared-N/A.
- Disabled-rules policy = default No.
And a step list: upload primary + environment_full → run → check coverage
%/heatmap/gaps/roadmap/assumptions/N-A/detection-strength → download
PDF + XLSX + Navigator layer → run v2 → compare. Then a second pass with
environment_windows_only to see ICS/Mobile gated, and messy_headers to
test the wizard.

## Acceptance

- Generator runs clean; every ID validated against v19.1 (bad ones
  confirmed actually bad); all files round-trip through the real parsers
  with the expected tagged/untagged/invalid split printed.
- The kit demonstrably touches: customer/keyword/AI/unmapped/invalid/
  revoked/deprecated tagging; covered/partial/not_covered/N-A states;
  domain gating both ways; short/mid/long roadmap; threat weighting;
  detection strength; trend compare; the column wizard; PDF/XLSX/Navigator
  exports.
- Files live in `docs/sample/MITRE_Sample/` (per CLAUDE.md docs/sample is
  the sample-docs home); no app code changed; suite/`tsc` untouched.

## Wrap-up

Don't commit unless the user asks. Report the file list, the round-trip
ingest summary per file, and the README's feature-coverage table so the
user can confirm every part is covered before uploading.
