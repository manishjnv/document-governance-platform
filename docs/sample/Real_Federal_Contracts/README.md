# Real Federal Contracts — sourced 2026-07-20

Real, awarded, publicly-published US federal contract documents — not
templates. Sourced from USCIS's public contracts reading room
(`https://www.uscis.gov/sites/default/files/document/contracts/`),
published there under federal transparency/FOIA-adjacent disclosure
requirements. Each has a real vendor name, real contract number, real
dollar/pricing structure, and a real Statement of Work / Performance
Work Statement section — genuine content, not placeholder text.

This exists because `docs/sample/SOW_Template/*` and `docs/sample/RFP_template/*`
turned out to be mostly blank fill-in-the-blank templates (Lorem Ipsum,
"DESCRIPTION HERE") when assembling a real-document test set for AI
accuracy measurement — see `docs/planning/PROMPT_ENGINEERING_GUIDE.md`'s
"Real test set" section. These are a genuine real-document supplement.

| File | Type | Pages | Notes |
|---|---|---|---|
| `USCIS_70SBUR18C00000017.pdf` | Award/Contract (SF-26 style) | 46 | Vendor: Vertical Applications Inc. Work Statement pp. 3-14. |
| `USCIS_70SBUR19P00000128.pdf` | Award/Contract | 36 | |
| `USCIS_HSSCCG-05-Q-0020.pdf` | Request for Quotation (RFQ) | 89 | RFP-type document -- vendors respond to this, not a signed SOW |
| `USCIS_HSHQDC-13-D-E2075.pdf` | IDIQ/Unified Services contract | 60 | Larger, multi-part contract vehicle |

All 4 verified to extract real substantive text via
`apps/api/app/parser.py::PdfParser` (100k-220k chars each, not empty).

**Caveat:** these are real US federal contracts with real government
formatting/clause conventions (FAR references, SF-26 forms) — not
representative of a typical commercial SOW/RFP a ScopeWise customer would
upload. Useful for real-document accuracy testing (proves the pipeline
handles genuine complex documents, not toy inputs), but don't treat
findings against these as fully representative of commercial-engagement
accuracy without also testing against real commercial documents.
