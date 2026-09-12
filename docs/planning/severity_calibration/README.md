# Legal severity calibration pack

Everything a legal SME needs to complete §3 of
`docs/planning/LEGAL_SEVERITY_CALIBRATION.md` in one sitting, plus the script
that turns their answers into the §4 findings.

## Status

**2026-09-12: pack NOT yet generated.** The harvest run (`--run`) was
attempted at git `19ed616` and every LegalReviewer call returned HTTP 403
from OpenRouter, *"Key limit exceeded (total limit)"*, before any model in the
fallback chain answered. The ScopeWise key configured on the VPS reports
`limit: 2, limit_remaining: 0, usage: 8.14` (account credits 25.00, used
17.15). Zero documents were reviewed and nothing was spent. The same key
serves production reviews, so the next customer review will fail the same
way until the key limit is raised (or a new key is issued) in the OpenRouter
dashboard — no dashboard access from here. Re-run the two commands below
once that is done; nothing else needs to change.

## How the pack is produced

```
# 1. harvest (calls OpenRouter; inject the ScopeWise key per-process, never the personal tooling key)
OPENROUTER_API_KEY="$(ssh a11yos-vps "grep '^OPENROUTER_API_KEY=' /opt/scopewise/.env | cut -d= -f2-")" \
  python scripts/severity_calibration_run.py --run
# 2. build the XLSX from raw/*.legal.json
python scripts/severity_calibration_run.py --build
```

`scripts/severity_calibration_run.py`:

- Document set (real, public, non-customer; nothing under `docs/sample/project/`):
  the four USCIS federal contracts in `docs/sample/Real_Federal_Contracts/`
  (three as SOW, the HSSCCG RFQ as RFP so the RFP prompt branch is exercised),
  `docs/sample/SOW_Sample/SOC_SOW_Testing.docx` (commercial-style SOC SOW with
  the 29-row ground truth) and `docs/sample/SOW_Sample/aws_examples_sows.pdf`
  (public AWS example SOWs). Six documents.
- Parses each with the product parser (`app.parser.parse_document`) and runs
  the unmodified `LegalReviewer` (`app.ai.agent`) exactly as production does
  (same prompt, same primary + fallback model chain from `app.config`). The
  agent's OpenRouter adapter is wrapped at runtime only to capture each
  response's usage and generation id; cost is then read from OpenRouter's
  `GET /api/v1/generation?id=` so spend is reported per document from the
  audit trail, not estimated. No product code is modified.
- Anchors each finding's quoted evidence to the parsed section heading and
  page (falls back to a position-estimated page marked `~N`, or "not
  located" when the model paraphrased instead of quoting).
- Writes `raw/<document>.legal.json` (model used, calls, cost, git SHA,
  timestamp, findings) and then
  `LEGAL_SEVERITY_SME_PACK_<date>.xlsx` with four sheets:
  - **Read Me** — the 30-minute procedure, the "Finding Severity" section of
    `SCORING_METHODOLOGY.md` verbatim, the operational point penalties, and
    two free-text questions (RFP down-weighting; per-level definitions —
    the repo has none, the SME is asked to supply them).
  - **Documents** — provenance, pages, chars, findings, model, cost per doc.
  - **Findings** — one row per finding: ID, document, type, system severity,
    confidence, quoted evidence, description, recommendation, section, page,
    then the three SME columns (severity dropdown, Agree? dropdown with
    "Not a finding", comment). Formula-injection guarded via the MITRE
    module's `_guard`; header style mirrors the MITRE XLSX.
  - **Summary** — severity distribution per document and per finding type
    (with the observed mode, which replaces the "typical severity" column in
    the calibration doc's §3 table).

## Ingesting the SME's answers

```
python scripts/severity_calibration_ingest.py docs/planning/severity_calibration/LEGAL_SEVERITY_SME_PACK_<date>.xlsx
python scripts/severity_calibration_ingest.py --self-check
```

Prints, per finding type: rated count, agreement %, how often the system was
over- or under-severe, "not a finding" count, mean tier delta, and a pattern
verdict (calibrated / mixed / SYSTEMATICALLY OVER- or UNDER-SEVERE). That is
the input for §4's "systematic over/under-severity pattern gets a prompt fix".
Reads the Findings sheet by header name; unrated rows are counted and
excluded. The self-check runs the analysis on a fixed six-row sample and
asserts the expected counts and verdicts.

## What the SME does

Open the XLSX, work the Findings sheet top to bottom (about 30 minutes for
a set this size), answer the two questions on Read Me, save with the same
file name, send it back. Then run the ingest script and record its output
in `LEGAL_SEVERITY_CALIBRATION.md` §4.
