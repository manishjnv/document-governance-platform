# AI Model Routing (OpenRouter)

Status: active as of 2026-07-19
Files: `apps/api/app/config.py`, `apps/api/app/ai/agent.py`

## Why OpenRouter instead of Anthropic/OpenAI/Google directly

Cost. The document review pipeline runs up to 6 agents per document
(Scope, Delivery, Commercial, Security, PMO, Legal — see
`4_AI_AGENT_SPECS.md`), each a separate LLM call against a full document.
At Claude/GPT/Gemini flagship pricing that's expensive per review at
scale. OpenRouter gives access to non-US-flagship models (Chinese-lab
frontier models: Zhipu/Z.ai, MiniMax, Alibaba/Qwen, Moonshot) at a
fraction of the cost, some of them now competitive with Opus-tier
quality on structured-extraction tasks.

`ReviewAgent.initialize()` (`apps/api/app/ai/agent.py`) uses OpenRouter
automatically when `OPENROUTER_API_KEY` is set; otherwise it falls back
to the direct Anthropic client. `_OpenRouterClient` /
`_OpenRouterMessages` wrap OpenRouter's OpenAI-compatible endpoint to
mimic the Anthropic SDK's `client.messages.create` surface, so
`ReviewAgent.review()` doesn't need to branch on provider.

## Current chain

```
primary:   z-ai/glm-5.2
fallback:  minimax/minimax-m3 -> qwen/qwen3.7-plus -> deepseek/deepseek-chat
```

Defined in `Settings.openrouter_model` /
`Settings.openrouter_fallback_models` (`apps/api/app/config.py`).
`ReviewAgent.review()` (`apps/api/app/ai/agent.py`) tries each model in
order and only raises if every model in the chain fails — a single
provider hiccup or 429 shouldn't fail a customer-facing review.

## How the chain was chosen

Tested 2026-07-19 against `docs/sample/SOW_Template/statement-of-work-template-09.docx`
(a blank SOW template — deliberately missing liability cap,
indemnification, IP ownership, termination clause, governing law, and
warranty language), run through `LegalReviewer` — the reviewer type most
sensitive to hallucination and omission.

### Round 1 — `max_tokens=2000` (the original Claude-3.5-era setting)

| Model | Result |
|---|---|
| DeepSeek (`deepseek/deepseek-chat`) | Valid JSON, 6/6 findings, confidence 0.95, 17.9s |
| Qwen3.7-Plus (`qwen/qwen3.7-plus`) | Valid JSON, 6/6 findings, confidence 0.98, 71.9s |
| GLM-5.2 (`z-ai/glm-5.2`) | **Truncated mid-JSON, parse failed** |
| MiniMax M3 (`minimax/minimax-m3`) | **Truncated mid-JSON, parse failed** |
| Kimi K3 (`moonshotai/kimi-k3`) | **`content: None`**, `finish_reason: "length"` |

### Root cause

Not a model-quality problem. GLM-5.2, MiniMax M3, and Kimi K3 all run
"always-on thinking" / hidden-reasoning modes — they spend completion
tokens on internal reasoning before emitting the visible answer.
`max_tokens=2000` was inherited from the original Claude 3.5 Sonnet
integration and is too small for these models. Direct inspection of the
Kimi K3 response confirmed it: `reasoning_tokens: 1997` out of a 2000
token budget, leaving 0 tokens for actual output.

### Round 2 — `max_tokens=4000`

| Model | Result |
|---|---|
| GLM-5.2 | Fixed. Valid JSON, 6/6 findings, confidence 1.0, 31.6s |
| MiniMax M3 | Fixed. Valid JSON, **10 findings** (most thorough of all 5), confidence 0.97, 30.3s |
| Qwen3.7-Plus | Valid JSON, 6/6 findings, confidence 1.0, 51.3s |
| DeepSeek | Valid JSON, 6/6 findings, confidence 0.95, 17.9s |
| Kimi K3 | Still failed — reasoning overhead scales with the budget, not fixed cost |

### Kimi K3 at `max_tokens=8000`

Succeeded (`finish_reason: "stop"`) but at real cost:
`reasoning_tokens: 3724`, `completion_tokens: 5746` total, **$0.086 for a
single agent call** (OpenRouter pricing: $3/$15 per M tokens). Also the
slowest response observed (82-134s per call across trials).

At 6 agent calls per document review, Kimi K3 in the chain would add
roughly **$0.52/review** on this one model alone — 10-15x the cost of
GLM-5.2 or DeepSeek for the same task, plus meaningfully worse latency.
**Dropped from the chain** on cost/latency grounds, not quality — its
output (once it completes) was not inspected further.

## Decision

- `max_tokens` raised from 2000 to 4000 in `agent.py` — this was the
  actual bug fix; without it, 3 of 5 candidate models fail with no
  usable output on every request.
- Chain ordered by (a) reliability at 4000 tokens, (b) thoroughness,
  (c) cost/latency: GLM-5.2 primary, MiniMax M3 first fallback (found
  the most findings), Qwen3.7-Plus second fallback, DeepSeek last
  resort (cheapest, fastest, but least thorough — 6 vs MiniMax's 10).
- Kimi K3 excluded — real quality, wrong cost/latency shape for a
  fallback slot in a 6-agents-per-review pipeline.

## Known gaps / not yet done

- Only `LegalReviewer` was benchmarked, on one document. The other 5
  reviewer types (Scope, Delivery, Commercial, Security, PMO) have
  different output schemas and were not tested — assumed to behave
  similarly since they share the same `ReviewAgent.review()` path, but
  unverified.
- Only one sample document was used. No sweep across RFP vs SOW,
  short vs long documents, or documents with clauses present (positive
  cases, not just gap-detection).
- `max_tokens=4000` was chosen because it fixed the observed truncation
  at the tested document length (3.7K chars); longer real-world
  documents may need a higher ceiling — no scaling test was done.
- No per-model timeout override — all models in the chain share
  `ai_timeout_seconds`. A model that hangs (rather than erroring
  cleanly) will hold up the full timeout before falling back.

## Environment

`OPENROUTER_API_KEY` must be set (VPS: `/opt/scopewise/.env`) or the
agent silently falls back to the direct Anthropic client path per
`ReviewAgent.initialize()`.
