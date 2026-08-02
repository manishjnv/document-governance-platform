# MITRE Phase 14 — UX Clarity for Non-Technical Users (Design)

Status: **design approved-pending** (written 2026-08-02, after the first
full sample-kit run on prod — see `docs/sample/MITRE_Sample/result/`).
No code in this phase doc; sub-phase kickoff prompt:
`docs/phases/prompts/MITRE_PHASE_14_UX_PROMPT.md`.

## Problem

The assessment is correct but reads like an analyst tool. A
non-technical user (CISO's boss, compliance lead, IT manager) sees:

- ~900 red chips with cryptic IDs (`T1027`) and no names — no story,
  no meaning, and "2.2%" with no context reads as a failing grade.
- Numbers everywhere (20 covered, 9 partial, 879 not covered, 47 N/A,
  per-tactic counts) that are **dead text** — nothing is clickable, so
  "what are these 9 partial ones?" has no answer in the UI.
- Gaps say *that* something is missing but not **where the gap is, why
  it exists, or what a good detection would look like**.
- The XLSX export is raw data: no technique names in the register, raw
  `TA0011` tactic IDs, no colors, truncation-prone text, jargon column
  headers ("Strict %").

Three principles for everything below:

1. **Every state answers three questions in plain words:** *what is
   this → why is it a gap → what do we do about it.*
2. **Every number is a door, not a label** — clicking it shows the
   items behind it.
3. **No scoring/pipeline changes.** Everything renders from data the
   results JSONB already contains (states, mapped rules, confidences,
   enabled flags, gap list with via/feasibility, quality scores,
   assumptions, N/A reasons). This phase is frontend + `report.py` +
   one small curated data file.

---

## 14a — Gap drill-down: where, why, and what good looks like

A technique drawer (extend the existing `TechniqueDrawer`) that renders
four plain-language blocks for ANY technique state:

**1. What is this?**
Technique name + a one-sentence plain-English definition + "attackers
use this to …" line. Source: a new curated
`app/mitre/data/technique_plain_language.json` for the ~150 techniques
that realistically surface as top gaps (priority tiers 1–2 + threat
profiles); fall back to the first sentence of the ATT&CK description
(already in `attack.json`) for the long tail. Same get/curate/fallback
pattern as `technique_priorities.json`.

**2. Where is the gap?**

- Domain + tactic in story terms: "This is a *Lateral Movement*
  technique — how attackers spread between systems once inside."
  (12 tactic one-liners, another small curated map, reused by the
  heatmap column headers.)
- Which of **your** onboarded log sources could see it (intersect the
  technique's data sources with the uploaded Log Sources sheet — the
  roadmap bucketing already computes this; surface its result).
- Platforms it applies to in your environment.

**3. Why is it a gap?**
Deterministic reason derived from existing per-technique mapping data,
one sentence each:

- Not covered → "None of your 30 rules maps to this technique."
- Partial (disabled rule) → "Your rule `<name>` covers this but is
  **disabled** in your SIEM."
- Partial (low confidence) → "Rule `<name>` probably covers this
  (AI-tagged at NN% confidence) — confirm the mapping."
- Partial (sub-technique rollup) → "Only N of M sub-techniques are
  covered (list)."
- Covered → show the mapping proof: which rule(s), tag source
  (you / keyword / AI), confidence, detection-strength score.
- N/A → reason verbatim (already exists).

**4. What would good look like?**
A sample detection sketch, deterministic-first (coding-over-AI):

- Template: *"Using `<your matched log source>`, alert when
  `<technique's detection hint>`."* Detection hints come from the same curated
  `technique_plain_language.json` (a `detection_hint` field per curated
  technique, written once, in vendor-neutral words: e.g. T1027 →
  "command lines containing base64/encoded payloads; scripts with
  unusually high entropy").
- The existing AI recommendation text (Gaps tab) stays as the richer
  paragraph below the sketch, with its `AI-written text` badge.
- Plus "closest existing rule" if a sibling sub-technique or same-tactic
  rule exists — gives the SIEM team a starting point to copy.

Acceptance: clicking any chip/row anywhere in the app opens this drawer;
all four blocks render for each of the 6 states using only
existing-result data + the two curated JSON files; the sample kit's rows
4/5 (logic vs no logic) and 15 (disabled) show visibly different "why"
text.

## 14b — Every number is clickable

One reusable drill-down list panel (technique list with name, state
color, plain state phrase, click-through to the 14a drawer), wired to:

| Number | Click shows |
| --- | --- |
| Coverage % / per-domain % tiles | Register filtered to that domain, grouped by state |
| Covered / Partial / Not covered / N/A tiles | Register filtered to that state (Partial rows show their why-phrase inline) |
| Top-gaps chips | The 14a drawer directly |
| Per-tactic counts in Coverage tab headers ("1/20 covered") | That tactic's techniques, filtered |
| Parse-preview tiles (30 / 15 / 13 / 2) | The matching uploaded rows with their mapping status |
| Assumption counts ("10 rules matched deterministically…", "4 rules AI-tagged", "1 rule unmapped") | The affected rules |
| N/A category counts (platform-filtered / deprecated / excluded) | That N/A table section |

Also in 14b (microcopy, same files):

- Pluralization fix: "1 rule remains unmapped".
- Legend items and column headers get hover definitions (Covered,
  Partial, N/A, Priority, Threat match, Feasibility, Strength).
- Headline subtitle: "of the 908 techniques that apply to your
  environment, your rules can detect 20" + an info popover answering
  "is 2.2% bad?" (early SIEM programs typically start under 10%; the
  roadmap is the point, not the grade).

Acceptance: no numeric stat on the assessment page is inert; keyboard
accessible; `tsc` clean.

## 14c — Excel export polish (`report.py` XLSX builder)

Keep the 8-sheet structure; make each sheet self-explanatory:

- **New first sheet "Read Me"** — what each sheet contains in one
  sentence each, the color legend (actual filled cells), the three key
  numbers, and the same "is this % bad?" context line. Simple words
  only.
- **All sheets:** frozen header row, auto-filter, sane column widths,
  wrapped text (no truncation), bold headers.
- **Color coding:** state cells filled green/amber/red/grey (matching
  the UI legend); priority tiers P1/P2/P3 amber-scale; feasibility
  buckets (short/mid/long) green/amber/grey.
- **Technique Register:** add **Name** column (currently missing);
  replace `TA0011` with tactic names; add a "Why" column carrying the
  14a one-sentence reason; plain state words ("No rule detects this"
  alongside "Not covered").
- **Use-Case Mappings:** numeric row sort (currently text-sorted:
  row 10 before row 2); mapping-status in plain words ("You tagged
  this" / "Matched by tool-name keyword" / "AI-suggested — verify" /
  "Could not be mapped"); full untruncated text.
- **Gaps & Recommendations:** grouped with colored section headers by
  feasibility bucket; full recommendation text; add the "via" log
  source in plain words ("Uses logs you already collect: Windows Event
  Logs").
- **Summary:** add plain-language explanation column next to each
  metric; rename "Strict %" → "Coverage %" (keep "Weighted %" with its
  one-line meaning).

Acceptance: openpyxl-styled workbook; existing XLSX tests extended for
the new sheet/columns (goldens on structure, not pixel styling); no
changes to computed numbers.

## 14d — Assessment context: project metadata + "what you uploaded"

**Project metadata.** Optional intake fields alongside the existing
industry/actors/exclusions: organization/project name, department or
scope label, prepared-by, and free-text purpose note. Ride the existing
intake JSONB (verify against the model when implementing — expected: no
migration). Shown on the assessment header, PDF cover, and XLSX Summary
sheet, so a report is self-identifying when it's forwarded around.

**Uploaded-files summary card.** A compact "What this assessment is
based on" block on the assessment page (and report cover):

- Use-case file: filename, rules found, tagged / keyword / AI / invalid
  split, disabled-rule count.
- Environment file: filename, platforms recognized, OT and mobile
  flags, log source / tooling / crown-jewel counts, unmatched entries.

All of this already exists in the parse results and assumptions — this
is presentation, not new parsing. Each number in the card is clickable
per 14b.

Acceptance: an assessment created without the new fields renders
unchanged (all fields optional); the card matches the parse-preview
numbers exactly.

## 14e — PDF report redesign: executive + detailed, visual, data-rich

Rebuild the report template (same WeasyPrint pipeline, HTML/CSS +
inline SVG only — deterministic, no runtime JS/LLM):

**Structure (in order):**

1. **Cover** — project metadata (14d), uploaded-files summary, ATT&CK
   version, run date, coverage headline with its plain-words subtitle.
2. **Executive section (max 2 pages)** — for the non-technical reader:
   - Scorecard: per-domain traffic-light tiles with one-line meaning.
   - "Top 5 things to fix first": technique name, plain definition,
     why it matters to *this* org (threat-profile tie-in), the fix in
     one sentence, effort badge. Reuses 14a's curated content.
   - Roadmap-at-a-glance: short/mid/long counts + the
     effort-to-impact line ("completing short-term raises coverage
     from X% to ~Y%").
   - Trend vs previous run when compare data exists (delta arrows,
     newly covered / regressed counts).
3. **Detailed section** — for the SIEM/SOC reader:
   - Per-tactic stacked horizontal bars (CSS/SVG) instead of
     bare count tables; tactic one-liners under each heading.
   - Gap register grouped by feasibility bucket with colored section
     headers; each entry carries the 14a trio — *why it's a gap*,
     *what good looks like* (detection sketch + via log source), and
     the AI recommendation with its badge.
   - Mini per-domain heatmap grid (colored cells, parent-level).
4. **Appendices** — technique register, N/A tables, assumptions,
   use-case mapping table (plain-words statuses, numeric row order —
   same fixes as 14c).

**Report ergonomics:** table of contents with real page numbers
(WeasyPrint `target-counter`), numbered sections, running header with
project name + page N of M, cross-references from executive items to
their detailed-section pages ("details p. 12").

Acceptance: the prod-only render test still passes; executive section
never exceeds 2 pages regardless of gap count; a reader who stops after
page 3 has the full story (state, top risks, next actions); numbers
match the UI/XLSX exactly.

## 14f — Past-assessment history, easy to find and read

The `/mitre` landing page **already lists past assessments** (status,
coverage %, trend arrow vs previous run, per-domain mini-bars, created
date, row click-through) — 14f makes history discoverable from inside
an assessment and readable at a glance:

- **Run switcher in the assessment header:** a "Past runs" dropdown
  (date + coverage % + delta) to jump between runs without going back
  to the list; "Compare with this run" shortcut straight into the
  Compare tab.
- **List enrichment:** show the 14d project name on each row; search /
  filter by project name and status; a small coverage sparkline across
  all completed runs at the top of the list ("your trend so far").
- **Housekeeping:** rename an assessment after creation; archive (hide
  from the default list, keep for compare) — soft flag only, no
  deletes.

Acceptance: a user inside any assessment can reach any past run in two
clicks; archived runs stay selectable in Compare; list search is
client-side (the list endpoint already returns everything needed).

## 14g — Per-item evidence trail ("prove it, line by line")

Customer-trust requirement: for **each** rule, environment entry, and
intake input, show the evidence chain from what they gave us to what it
changed in the result. Most of this is already persisted and merely
unshown; one gap needs a small parse-output extension.

**Per use case (rule) — the mapping journey.** Clicking any rule
(Use-Case list, drawer "mapped rules", XLSX) shows:

- Source line: file + row number (`row_ref`, already stored) and the
  exact fields read (name / tags / logic / description / status).
- Validation step: tag accepted / remapped ("T1562.001 is retired,
  counted as T1685") / rejected, with reason.
- Mapping step with its stored rationale, verbatim: "You tagged this" /
  "detection logic contains the known attacker tool 'mimikatz'"
  (keyword rationale is already persisted per mapping) / "AI-suggested:
  `<rationale>`, NN% confidence — verify" / "could not be mapped".
- Effect: which technique cells this rule turns green/amber, and its
  detection-strength score with the Phase 12 factor breakdown.

**Per environment entry — how we read your inventory.** An
"interpretations" list (new: the parser computes this per entry today
but only keeps aggregates — extend `parse_environment_file` to also
return a per-entry `[{entry, sheet, interpretation}]` map; additive
output field, no semantic change):

- "'AWS EC2 workloads' → counted as platform IaaS"
- "'OT/SCADA PLC segment' → enabled the ICS/OT matrix"
- "'VMware ESXi estate' → skipped — you marked it Present = No"
- "'Mainframe z/OS' → not recognized; ignored for platform filtering"
- Log sources → which roadmap items they made "short term".

Shown as an expandable section of the 14d upload card, and as a
"How we read your files" appendix in the 14e PDF / a sheet in the 14c
XLSX.

**Per intake input — what your answers changed.**

- Industry / threat actors → list of gaps that received a threat-match
  badge because of them (data exists in the weighting output).
- Each exclusion → the N/A row it produced, reason verbatim (exists).
- Disabled-rules policy → which rules it demoted to partial.

Acceptance: for the sample kit, every one of the 30 rules and every
environment entry shows a correct, human-readable evidence chain;
rows 15/16/17 (disabled / revoked / invalid) and the ESXi/Mainframe
entries read exactly as designed; no coverage numbers change.
Storage note: rule-mapping rationale/confidence and N/A reasons are
already persisted; the only backend additions are the per-entry
environment interpretation map and (if absent) persisting it with
results.

---

## Explicitly deferred (recorded, not in 14)

Maturity bands instead of raw %, copy-as-ticket export, sub-technique
collapse toggle in the heatmap, show-names toggle, threat-profile-only
filter view, guided first-run tour. (The executive scorecard moved into
scope as part of 14e.) Revisit after 14 lands and a real user walks
through it.

## Delivery notes

- Order: 14a → 14b → 14c → 14d → 14e → 14f → 14g. 14b reuses 14a's
  drawer; 14c/14e reuse 14a's why-phrases and plain-language file;
  14e's cover reuses 14d's metadata and upload summary; 14g feeds the
  14d card, the 14c XLSX, and the 14e appendix (run it last, or its
  backend part first if sequencing suits). 14d and 14f are small and
  can run in parallel with 14c.
- No migration expected (14d rides the intake JSONB — verify; 14f's
  rename/archive may need two nullable columns or a JSONB flag —
  decide at implementation, prefer the existing JSONB), no
  pipeline change, no new settings. Two new curated data files under
  `app/mitre/data/` (validated against `attack.json` by a test, same as
  `threat_profiles.json`).
- Curated-content rule: plain-language definitions and detection hints
  are **hand-written once** (deterministic, reviewable), not
  LLM-generated at runtime — consistent with the coding-over-AI
  preference; the existing per-assessment AI recommendation text is
  unchanged.
- Test surface: suite baseline 765/7 + new tests (plain-language file
  validation, why-phrase derivation goldens, XLSX structure); frontend
  `tsc` clean. Verify against the sample kit
  (`docs/sample/MITRE_Sample/`) — it already exercises every state the
  drawer must explain.
