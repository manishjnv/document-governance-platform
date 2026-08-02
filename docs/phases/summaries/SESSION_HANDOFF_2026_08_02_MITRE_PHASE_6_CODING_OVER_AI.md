# Session handoff — 2026-08-02 — MITRE Phase 6: coding-over-AI

**Headline:** Phase 6 (deterministic keyword-tagging pre-pass + synonym/map
widening) implemented per
`docs/phases/prompts/MITRE_PHASE_6_CODING_OVER_AI_PROMPT.md`. Untagged rules
now hit a pure keyword/alias matcher before any LLM call — on the
quality-gate dump, 14/22 rules (63%) skipped AI with zero false positives.
NOT committed/pushed/deployed — user gate per the kickoff prompt's wrap-up.

**Commits:** none (working tree holds the full change set; see file list).

**Tests:** full suite **686 passed / 7 skipped** (baseline 650 + 36 new,
zero regressions; re-run green after the adversarial fixes);
`tsc --noEmit` clean. Migration 031
applied to edgp_dev + edgp_test (constraint verified via
`pg_get_constraintdef`); **prod still pending** — apply on deploy.

**Adversarial sign-off (Sonnet takeover, codex:rescue still broken):**
**REVISE → fixed same-session → re-verified ACCEPT.** Two blocking finds,
both empirically demonstrated against the real dataset and both fixed:
(V1) MITRE Reconnaissance/Resource-Development names are generic
category words ("Credentials" T1589.001, "DNS Server" T1583.002,
"Databases" T1213.006) — benign ops rules false-mapped at 0.9 and
inflated coverage. Fix: name index now excludes pre-compromise-only
techniques (TA0042/TA0043) AND single-word names (distinctive singles
are curated aliases — `kerberoasting` added); the reviewer's 6 FP rule
names are pinned as a real-dataset regression test, and the re-review
confirmed the whole structural class (email addresses, employee names,
network devices, social media, search engines) now returns nothing.
(V2) The ingest `logic` cell is uncapped (32K legal per XLSX cell) and
the router folded it uncapped into `description` — a 5k-row dump of fat
cells ≈ 50 min of worker-thread scanning. Fix: `_FIELD_CAP=2000` in the
matcher + the router's logic-fallback capped at the root (mirrors
ingest's own description cap); cap-boundary test added. Non-blocking
residuals accepted by design: "private keys"-style governance-rule FPs
(specific term, low frequency), ~30 single-word post-compromise names
now routed to AI instead of auto-tagged (precision over coverage — the
module's stated rule), and the pre-existing dead-logic-column
limitation (below).

**Next action:** on user approval — commit (one unit per task), push, VPS
deploy loop, apply migration 031 to `scopewise_prod`, live smoke.

---

## What was built

### Task A — deterministic keyword/alias tagging pre-pass (main build)

- **`app/mitre/keyword_tag.py`** (new, pure): `keyword_tag_rows(rows,
  index=DEFAULT) -> {row_ref: [mapping]}`, mapping = `{technique_id,
  source: "keyword", confidence: 0.9, rationale}`. Two signal classes:
  1. Exact ATT&CK technique/sub-technique **names** as whole phrases on
     normalized text (ingest-style `_norm`). Precision guards: names < 6
     normalized chars skipped (kills "At"); names carried by >1 technique
     ID across domains dropped as ambiguous (kills "Phishing" =
     T1566/T1660, "Process Injection" = T1055/T1631 — verified live).
  2. **`data/keyword_aliases.json`** (new): 38 curated tool/command
     aliases (mimikatz, psexec, schtasks, `at.exe`, `-enc`, `vssadmin
     delete`, …) matched literally on raw lowercased text with
     `(?<![a-z0-9.])…(?![a-z0-9])` boundaries — punctuation stays
     significant, so `at.exe` never fires on "look at exe files" and
     `-enc` never on "base64-encoded". Header `_meta` cites sources
     (ATT&CK pages, LOLBAS, Red Canary). Deviation from the seed list:
     bare `net user` (ambiguous T1136.001-vs-T1087.001) narrowed to
     `net user /add`.
  - Every emitted ID passes `attack_data.resolve()` — the alias file keeps
    widely-known IDs and remap happens at match time (v19.1 revokes
    T1070.001 → T1685.005; covered by a test).
  - Fields joined with `" | "` so field concatenation can't fake phrase
    adjacency. CPU-bound; service calls it via `asyncio.to_thread`
    (5,060-row cap ≈ 6.5s in-thread; ponytail note: alternation regex if
    that ever hurts).
- **`mapping_status='keyword_tagged'`**, all 5 sync points honored:
  migration `031_mitre_keyword_tagged_status.sql` (idempotent,
  transaction-wrapped, applied to dev+test; prod on deploy) + ORM
  `CheckConstraint` in `app/models/mitre_use_case.py` (lockstep comment) +
  `service.py` counts + no `test_insights_extra` impact (not one of its 5
  tables) + this handoff.
- **`service.py` wiring** (stage 1.5): keyword pass over the
  unmapped/invalid set, residue-only to `agents.tag_untagged_rows`,
  assumption line "N rules matched deterministically … M sent to AI
  tagging", `counts.keyword_tagged`, and the all-AI-batches-failed guard
  now also survives on keyword matches (new E2E test proves an AI-down run
  completes when a keyword match exists). Customer-tags-win and
  AI-degrade-to-unmapped preserved.
- **Frontend:** `lib.ts` gains `SOURCE_META` (customer/keyword/ai);
  `TechniqueDrawer` badge shows "Matched by rule" with a plain-English
  tooltip (was a binary customer/AI ternary).

### Task B — ingest synonym/platform widening (pure code)

`COLUMN_SYNONYMS` (+~60 real-world header variants: "att&ck id",
"mitre_ttp", "correlation search name", "kql query", "deployment status",
"source type", …), `SHEET_SYNONYMS` (+"asset list", "siem sources",
"security products", "high value assets", …), `_PLATFORM_RULES` (+SUSE,
AKS/GKE/EKS/ECS, Duo/ADFS/Keycloak, Palo Alto/FortiGate/F5/VPN, iPadOS,
…), ICS markers (+iiot, modbus), mobile markers (+airwatch, kandji, soti,
maas360, emm). Splunk-style and Sentinel-style messy-header tests added.

### Task C — feasibility keyword maps (pure code)

Deterministic scan found 21 ATT&CK data components with no telemetry
category. Fixed the fixable: new **`mobile`** category (8 mobile-domain
components ← MDM/EMM providers) and **`ot`** category (Device Alarm/Asset
Inventory/Software ← Claroty/Nozomi/Dragos/SCADA) — mobile/ICS gaps now
bucket short/mid instead of a wrong "no standard telemetry"; `Host Status`
→ endpoint; container `Image Creation/Metadata/Modification` → cloud
(guard test: `Image Load` stays endpoint). Recon/threat-intel components
(Response Content, Social Media, Domain Registration, Malware *) left
unmatched **on purpose** — "long" is the honest verdict (comment in
code). Vendor lists widened on both provider tables (substring-safety
comment added: no bare "ot"/"ics" — they hide inside "remote"/
"analytics"; regression test included). `test_deterministic_modules_import_no_ai`
guards ranking + keyword_tag + ingest + coverage + applicability +
attack_data against ever growing an AI import.

### Task D — explicit-MITRE-ID path

Confirmed already pure (`service.build_mappings`); added the missing
regression test (valid + revoked + invalid + duplicate tag in one row;
invalid-only → `invalid`; no tags → `unmapped`).

## Quality gate (hand-verified)

22-rule realistic mixed dump: **14 keyword-tagged / 8 AI-residue (63% of
AI calls eliminated on this dump); every keyword mapping hand-checked
correct; zero false positives.** Near-miss traps all rejected: "Look At
Exe Files…" (no T1053.002), "Base64-Encoded Payload" (no T1059.001),
"Command And Control" (no T1059.003), "ASP.NET User Enumeration" (no
T1136.001). Bonus finds: sub-technique names ("LSASS Memory",
"Kerberoasting", "Exfiltration to Cloud Storage") match as designed, and
the ambiguity rule correctly sent "Process Injection" (T1055 vs mobile
T1631) to AI — precision over coverage, exactly the standing rule.

## Deviations from the kickoff prompt

1. `net user` seed narrowed to `net user /add` (precision-first; noted in
   the alias file `_meta`).
2. "results-page counts" surfacing: the results page renders
   `summary.assumptions` (which now carries the keyword/AI split line) and
   the drawer badge; no new counts panel was added — `summary.counts`
   isn't rendered anywhere today and inventing a panel wasn't in scope.
3. `docs/planning/PROMPT_ENGINEERING_GUIDE.md` not re-read/edited — no LLM
   prompt was touched (the prompt file itself notes prompts live in
   `agents.py` + the guide).

## Files touched

Modified: `apps/api/app/mitre/{ingest,ranking,service}.py`,
`apps/api/app/models/mitre_use_case.py`,
`apps/api/tests/test_mitre_{api,ingest,ranking}.py`,
`apps/web/app/mitre/lib.ts`,
`apps/web/app/mitre/components/TechniqueDrawer.tsx`.
New: `apps/api/app/mitre/keyword_tag.py`,
`apps/api/app/mitre/data/keyword_aliases.json`,
`apps/api/migrations/031_mitre_keyword_tagged_status.sql`,
`apps/api/tests/test_mitre_keyword_tag.py`.

## Agent utilization

- Opus/Fable (main): recon, all implementation + tests, quality gate,
  docs (classifier logic is Tier 0 by the routing matrix; files were hot
  in cache — self-execute beat delegation).
- Sonnet: adversarial review of Task A, REVISE with 2 real blocking
  finds (both empirically verified by the reviewer), then re-verified
  the fixes to ACCEPT · reworked: N (review did its job; fixes were
  main-session).
- Haiku: n/a — no bulk sweeps needed.
- codex:rescue: n/a — companion broken on this account (memory
  2026-07-23); Sonnet takeover per approved fallback.
