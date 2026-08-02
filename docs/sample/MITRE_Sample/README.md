# MITRE Assessment Sample Test-Data Kit

Populated, upload-ready fixtures that exercise **every path of the MITRE
ATT&CK coverage-assessment module** (there is no real customer data yet).
Richer than the blank templates in `apps/web/public/templates/` — every row
here tests something specific.

All technique IDs are validated against the pinned **ATT&CK v19.1** dataset
(`apps/api/app/mitre/data/attack.json`) and every file round-trips through
the real ingest parsers. Regenerate after any ATT&CK re-pin:

```bash
python scripts/generate_mitre_samples.py
```

(Run with the `apps/api` Python environment. The generator hard-fails if
any ID's status drifts from what the fixtures advertise.)

## Files → features

| File | Exercises |
| --- | --- |
| `usecases_primary.xlsx` | The main 30-row dump: full tagging ladder (customer / keyword / AI / unmapped / invalid / revoked / deprecated), disabled-rule policy, parent+sub rollup, ICS + Mobile coverage, Phase 12 detection-strength contrasts |
| `environment_full.xlsx` | All three domains applicable (ICS gated by OT assets, Mobile by MDM fleet), 10 ATT&CK platforms, present?-flag skip, unmatched-asset assumption, roadmap short/mid-term bucketing inputs |
| `environment_windows_only.xlsx` | The gating contrast: ICS + Mobile whole-domain **N/A with reason**; macOS/Linux/cloud techniques platform-filtered → N/A appendix (derived-domain + derived-platform) |
| `usecases_v2_improved.xlsx` | Second run for Phase 4 trend compare: 4 newly-covered techniques + 1 regression |
| `usecases_messy_headers.xlsx` | Phase 9 column-mapping wizard: tags under "Ref Codes", logic under "Payload" etc. — auto-detection finds only the name column |
| `usecases_primary.csv` | Same rows through the CSV ingest path |
| `usecases_scanned.pdf` | Phase 2 AI text-extraction path (structured parsers reject PDF by design) |

`.xls` is deliberately not provided — no xls **writer** is installed
(`xlrd` reads only); the xls ingest path stays covered by unit tests.

## Key rows in `usecases_primary.xlsx` (sheet row numbers; row 1 = header)

| Row | Tags | Path exercised |
| --- | --- | --- |
| 2 | T1685.005 | Customer-tagged valid → `customer_tagged`, `covered` |
| 3 | T1003.001 | Description **and** logic populated → Phase 7 logic persistence + strongest Phase 12 telemetry match |
| 4 / 5 | T1547.001 ×2 | Same technique with logic vs. without → detection-strength difference (Phase 12) |
| 6 / 7 | T1059 + T1059.001 | Parent + sub-technique → rollup |
| 8 / 9 | T0806, T0809 | ICS techniques → ICS domain coverage (with `environment_full`) |
| 10 / 11 | T1414, T1407 | Mobile techniques → Mobile domain coverage |
| 12 | T1558.003 | Enabled here, **disabled in v2** → shows *regressed* in trend compare |
| 14 | T1059.001, T1105 | Multiple IDs in one cell → multi-tag extraction |
| 15 | T1021.001 | **Status=Disabled** → `partial` under the default disabled-rules policy |
| 16 | T1562.001 | **Revoked** in v19.1 → auto-remap to T1685 + assumption note |
| 17 | T9999, banana | Invalid: T9999 → unknown; `banana` doesn't even match the tag regex (silently dropped at ingest) |
| 18 | T1026 | **Deprecated** in v19.1 → deprecated note |
| 19–28 | *(untagged)* | Keyword pre-pass, no LLM: mimikatz, schtasks, `-enc`/powershell, rundll32, wmic, `vssadmin delete`, `wevtutil cl` (emits remapped T1685.005), certutil, nltest, rclone |
| 29–31 | *(untagged)* | Genuinely non-keywordable (impossible travel, low-jitter callbacks, DLP spike) → AI tagging residue, or `unmapped` if no LLM key is configured — both outcomes are valid |

Round-trip proof (printed by the generator): 30 rows, split
`customer_tagged: 17 / untagged: 13`, tag statuses
`ok: 15, remapped: 1, unknown: 1, deprecated: 1`, keyword pass maps
10 of 13 untagged rows, residue = rows 29–31.

## On-screen intake values (full-coverage run)

- **Industry:** `Healthcare` (has a threat profile in
  `threat_profiles.json`) → exercises Phase 11 threat weighting.
- **Threat actors:** `FIN7`, `Lazarus Group` (both in the actor catalog).
- **Scope exclusion:** `T1200` — *"Hardware Additions — accepted risk,
  physical controls at all sites"* → exercises declared-N/A with reason.
- **Disabled-rules policy:** leave at the default (**No** — disabled rules
  count as partial).

## Playbook

**Pass 1 — everything on:**

1. New assessment → upload `usecases_primary.xlsx` +
   `environment_full.xlsx`, enter the intake values above → run.
2. Check: coverage % per domain (all three applicable), heatmap, gaps list
   (threat-weighted badges from Healthcare/FIN7/Lazarus), roadmap
   (short-term = telemetry already onboarded, mid = ownable via tooling,
   long = rest), assumptions (T1562.001 remap, T9999 invalid, T1026
   deprecated, unmatched `Mainframe z/OS` asset), N/A appendix (declared
   T1200), detection-strength badges (compare rows 4 vs 5, 3 strongest).
3. Download the PDF report, XLSX export, and Navigator layer.

**Pass 2 — trend compare:** upload `usecases_v2_improved.xlsx` (same
environment) → run → compare with pass 1. Expect **newly covered:**
T1021.001 (rule enabled), T1078 + T1071.001 (tags added), T1486 (new
rule); **regressed:** T1558.003 (rule disabled).

**Pass 3 — domain gating:** rerun primary with
`environment_windows_only.xlsx`. Expect ICS and Mobile whole-domain N/A
with reason (rows 8–11 no longer count), macOS/Linux/cloud-only
techniques platform-filtered into the N/A appendix.

**Pass 4 — column wizard:** upload `usecases_messy_headers.xlsx`; only
"Rule Title" is auto-detected. In the wizard map: name→col 1 (Rule
Title), tags→col 2 (Ref Codes), logic→col 3 (Payload), description→col 4
(Meaning), log source→col 5 (Feed), status→col 6 (Mode). Result must
match pass 1.

**Extras:** `usecases_primary.csv` (CSV ingest, same result as pass 1);
`usecases_scanned.pdf` (Phase 2 AI extraction — expect ~3 rules
extracted, one untagged).

The rightmost **"Feature Exercised"** column in every use-case file is
ignored by the parser — it tells a human reader what each row tests.
