# Kickoff prompt — Code Security Review: finish golden scan, commit, deploy

> **Status: completed 2026-09-12** — kept as the record of how the split
> session was resumed. See the scan-kit session handoff for the outcome.

Paste below the line into a fresh session at `E:\code\DocumentGovernancePlatform`.

---

Continue the Code Security Review module (ScopeWise). Read in ONE parallel
burst, then give a Phase 0 plan and wait for approval:

1. `CLAUDE.md`
2. `docs/phases/summaries/SESSION_HANDOFF_2026_09_11_CODE_REVIEW_SCAN_KIT.md`
   ← exact state: everything is built and verified but NOT committed; the
   real VVAH scan of OWASP/NodeGoat was mid-run (S2) when the session
   stopped, with resume instructions and scratchpad paths.
3. `docs/phases/prompts/CODE_REVIEW_SCAN_KIT_PROMPT.md` tasks B.4–B.6 and C
   (the remaining work) and `docs/planning/CODE_REVIEW_MODULE_REFERENCE.md`
   §8–9.
4. Memories `edgp-test-single-runner-rule`, `prod-python-311-fstring-gotcha`,
   `openrouter-key-identity`; `docs/RCA_LOG.md` #3/#11/#12/#13.

Decisions already made (do not re-ask): kit hosted in ScopeWise (done);
one commit for module + UI pass + kit + golden fixture; golden scan gated
on estimate (estimate shown and approved yesterday: ~$3–4, NodeGoat);
ScopeWise never runs the scanner server-side. Ponytail mode, Python 3.11-
compatible, no new dependencies.

Order:
- B: check `<scratchpad>/target-nodegoat/security-scan/` — if
  `findings.json` exists, use it; else resume the scan with `--resume` as
  documented in the handoff. Land `docs/sample/CodeReview_Sample/real/nodegoat/`
  (+ README with sha/licence/models/tokens/cost), secret-scan, golden
  ingest test. Real schema wins over synthetic assumptions.
- C: gates (secrets, TODO, module tests), full suite solo on edgp_test
  (baseline 971/7 + golden), `tsc --noEmit`, `CLAUDE.md` baseline line,
  finalize the handoff (suite numbers, commit sha, footer), ONE explicitly
  staged commit (path list in the scan-kit prompt C.3 + `test_codereview_kit.py`
  + both handoffs + screenshots folder + this prompt; never `git add docs/`
  or `-A`; leave MarketingFooter/privacy/marketplace/sentinel-workbook/
  MITRE UploadSample changes out).
- Then push, VPS deploy loop, apply migration 039 to `scopewise_prod`,
  in-container import smoke (`python -c "import app.codereview.router"`),
  upload the golden zip at https://scopewise.assessiq.in/codereview/new.
  Ask me to confirm push/deploy once before doing it.
- Finally delete `<scratchpad>/kitrun/.env` (holds the project key).

Finish by telling me: tests pass Y/N, commit sha, golden repo + real cost
from the manifest, deployed Y/N.
