# Upload sample — real customer workbook shape

Two files, the **minimum needed for a complete assessment**:

| File | Upload as | Contents |
| --- | --- | --- |
| `acme_sentinel_usecases.xlsx` | Detection rules (required) | 109 Microsoft Sentinel analytics rules in the customer's own "Consolidated Usecase Tracker" layout |
| `acme_environment.xlsx` | Environment workbook (optional but recommended) | Assets / Log Sources / Security Tooling / Crown Jewels sheets from their device-technology inventory |

Regenerate after any ATT&CK re-pin (run from `apps/api`):

```bash
python ../../scripts/generate_uploadsample.py
```

The generator hard-fails if a technique ID stops resolving, if a column
stops auto-detecting, or if the environment gates drift.

## Why these exist

The screenshots in this folder are a live customer export. Unlike the
blank templates in `apps/web/public/templates/`, this reproduces the
**column and sheet layout a real SOC actually sends** — different header
names, MITRE IDs glued to technique names, several sheets per workbook —
so the upload path is exercised the way customers will use it. Content is
anonymized (the customer prefix becomes `ACME`).

## Use-case file columns (auto-detected, no remap needed)

`S.No | Analytical Rule | Description | Datasource Used | Use Case Type |
RuleType | Severity | Query / Conditions | MITRE Tactics | MITRE Techniques |
Validation Result | Status | Implementation Date`

Mapped by the parser to: **Analytical Rule** → name · **MITRE Techniques** →
tags · **Query / Conditions** → logic · **Datasource Used** → log source ·
**Description** → description · **Status** → enabled. The other columns are
ignored. (These header variants were added to `ingest.py`'s synonym lists on
2026-08-02 precisely because of this file — before that, this workbook
needed the column-mapping wizard.)

### What the rows deliberately exercise

- **Tag formats**: IDs glued to names (`T1562 - Impair DefensesT1562.004 -
  Disable or Modify System Firewall`), multiple techniques per cell,
  sub-techniques, and `NA` / `Not Available` cells (→ unmapped).
- **Revoked IDs**: `T1562` / `T1562.001` / `T1562.004` remap to their
  v19.1 successors with an assumption note (5 remaps in this file).
- **Disabled rules** (`Status = Disabled`) → partial credit under the
  default policy.
- **Rule variety**: OOB, Custom, Custom COE, Customer Specific, Qatar
  Framework, Custom Sigma Rule, Recorded Future; Scheduled / NRT /
  Monitoring / Detection types; Informational → High severity.
- **All three matrices**: Enterprise, ICS/OT (`T0836`, `T0883`), Mobile
  (`T1629`).

## Environment file

- **Assets** — Windows/Linux/ESXi estates, Azure, M365, Entra ID, Cisco,
  Fortinet, Nokia/Huawei telco, IOT, an **OT/SCADA PLC segment** (gates the
  ICS matrix), **Intune-enrolled Android/iOS** (gates Mobile), macOS, plus
  a `Mainframe z/OS` row that is *not recognized* and three `Present? = No`
  rows (Solaris, AWS, Zeek) — both appear in the evidence trail.
- **Log Sources** — 23 onboarded sources (AMA, Defender XDR, Entra ID,
  Azure Activity/Diagnostics, CEF, Syslog, OfficeActivity, Cortex XDR,
  CyberArk, Recorded Future, Claroty…). These drive short-term
  feasibility.
- **Security Tooling** — 16 products (Sentinel, Defender suite, Cortex XDR,
  CyberArk, Fortinet, Intune, Claroty, Rubrik).
- **Crown Jewels** — 7 business-critical systems.

## Suggested intake for the demo

Industry **Telecommunications**, threat actors **FIN7** + **Lazarus Group**,
scope exclusion `T1200` — *"Hardware Additions — accepted risk, physical
site controls"*, disabled-rules policy at the default (No).

## Expected result (deterministic dry run, no AI)

109 rules → 105 customer-tagged, 4 unmapped. Coverage **~7.7%**
(70 of 911 applicable): Enterprise 65/690, ICS 4/97, Mobile 1/124.
841 gaps, roadmap ≈ 753 short-term / 88 long-term, 8 threat-profile
matches. The AI tagging pass on a live run may map some of the 4 untagged
rules, nudging these numbers up.
