# Session handoff — 2026-07-24: accuracy improvement sweep

**Headline:** all 6 dependency-free accuracy items executed, deployed, and
verified live: scoring harness, word-count investigation (no-fix), fuzzy
evidence anchoring (2→38 of 62 findings located), 4-model accuracy
comparison + fallback reorder + parse-failure chain advance, subtle-conflict
validation (4/4, 0 false), and OCR for scanned PDFs (validated in prod).

## Commits (this sweep)

- `1d50c71`+`e441db9` accuracy harness (`scripts/accuracy_harness.py`) + tests
- `80c4909` fuzzy evidence matching + #7 word-count investigation note
- `d04e313` model comparison, fallback order DeepSeek>MiniMax>Qwen,
  unparseable JSON advances the model chain
- `65f3ebf..` (in `d04e313` docs) AI_MODEL_ROUTING.md measured table
- conflict validation doc + `Subtle_Conflicts_Test.docx` checked in
- `c0a34c1` OCR fallback (tesseract in prod image), scanned PDFs fail
  loudly when OCR unavailable

## Key measured results

- Model comparison (all 6 agents, harness-scored): GLM-5.2 28/29 (6/6
  agents) >> MiniMax 24/29 (4/6) > DeepSeek 21/29 (6/6) > Qwen 19/29 (3/6).
  MiniMax/Qwen silently lose agents to unparseable JSON — now fixed by
  advancing the chain on parse failure.
- Conflict detector: 4/4 true subtle contradictions, 0 false; law/forum
  mismatch correctly routed to LegalReviewer as ambiguity instead.
- Evidence anchoring: 38/62 agent findings carry section+page (was ~2).
- OCR: sample-statement-work.pdf (image-only, 6pg) → 8,312 chars, detected
  SOW, in the prod container.

## State

- Tests: 583 passed / 6 skipped. `tsc --noEmit` clean. Deployed through
  `c0a34c1`; prod smoke-tested.
- Prod hygiene: ModelComparison test docs deleted; ConflictTest project
  keeps the two conflict demo docs.
- Remaining accuracy work is dependency-blocked: ≥10-doc ground truth
  (human labeling), calibration tuning (needs that set), RFP labels,
  legal SME severity sign-off.

## UI / admin work (same day, earlier)

- **Super-admin page** (`/admin`, manishjnvk@gmail.com only via
  `settings.platform_admin_emails` → `is_platform_admin` on /auth/me):
  platform-wide people/sign-ins (device+IP)/activity/AI usage across all
  workspaces, search boxes on each list, 60s auto-refresh. Ordinary
  workspace admins get 403 + no nav link. Login endpoints capture
  IP (Cloudflare-aware) + user-agent into the audit trail.
- **Dashboard** flattened to one table with project band rows (no
  box-in-box). **Findings**: "Section N"/"Appendix X" mentions in
  description/document text/recommendation are jump links into the
  document panel. **DOCX page numbers** real (Word page markers +
  chars-per-page fallback). **Login**: blank OTP box
  (autocomplete=one-time-code), inline wrong-code message, Google button
  placeholder, plain-language wording.
- RCA #19 added (unreadable-PDF review produced 28 bogus findings —
  fixed at both parser and trigger layers; closes RCA #16's open
  prevention item).

## How to test on prod as a user

1. Sign in at scopewise.assessiq.in (Google, manishjnvk@gmail.com) →
   sidebar **Admin**: all 4 users with workspaces, searchable sign-ins/
   activity; auto-refreshes.
2. Dashboard: single flat table, collapsible project bands.
3. ConflictTest project → open a review → red "Contradiction" findings;
   expand any finding → click blue "Section N" pin-links → document
   scrolls + highlights; section (p.N) tags on findings.
4. Upload `docs/sample/SOW_Template/sample-statement-work.pdf` (scanned)
   → parses + reviews via OCR now.
5. Log out → code box blank, "Email me a sign-in code" wording; wrong
   code → inline message.

## Next action

Hand-label ground truth for ≥10 real documents (the only remaining blocker
to a trustworthy launch-gate accuracy pass); then rerun
`scripts/accuracy_harness.py` per document.

## Agent utilization

- Opus (Fable): all design, code, review, measurement, deploys
- Sonnet: n/a — no delegation this sweep (edits small + hot context)
- Haiku: n/a
- codex:rescue: n/a — companion broken (see memory); no security-adjacent
  diff in this sweep required an adversarial gate
