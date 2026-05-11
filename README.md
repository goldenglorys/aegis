# AEGIS — Answer Engine & Generative Intelligence Suite

Python/FastAPI service implementing two AI-powered content analysis features:
- **AEO Content Scorer** — NLP pipeline scoring content across 3 structured checks
- **Query Fan-Out Engine** — LLM prompt engineering + semantic gap analysis

## Setup

**Prerequisites:** Python 3.11+, [uv](https://docs.astral.sh/uv/getting-started/installation/), an OpenAI API key.

```bash
# Install dependencies
uv sync

# Download spaCy model
uv run python -m spacy download en_core_web_sm

# Configure environment
cp .env.example .env
# Edit .env and set OPENAI_API_KEY=sk-...

# Run the server
uv run uvicorn app.main:app --reload
```

## Interactive Docs (Swagger)

| URL | Description |
| --- | --- |
| `http://localhost:8000/docs` | **Swagger UI** — interactive, try endpoints directly from the browser |
| `http://localhost:8000/redoc` | ReDoc — alternative reference layout |
| `http://localhost:8000/` | Health check — returns `{"service": "AEGIS", "status": "ok", "docs": "/docs"}` |

Both endpoints have pre-filled request examples in Swagger — click the dropdown next to the request body to switch between them.

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes | OpenAI API key for the fan-out engine |

## API

### `POST /api/aeo/analyze`

Scores content for AEO readiness. Accepts a URL or raw text/HTML.

```bash
curl -X POST http://localhost:8000/api/aeo/analyze \
  -H "Content-Type: application/json" \
  -d '{"input_type": "url", "input_value": "https://example.com/article"}'

curl -X POST http://localhost:8000/api/aeo/analyze \
  -H "Content-Type: application/json" \
  -d '{"input_type": "text", "input_value": "<h1>Title</h1><p>Short direct answer here.</p>"}'
```

### `POST /api/fanout/generate`

Generates 12–15 sub-queries from a target query. Provide `existing_content` to enable gap analysis.

```bash
curl -X POST http://localhost:8000/api/fanout/generate \
  -H "Content-Type: application/json" \
  -d '{"target_query": "best AI writing tool for SEO"}'

curl -X POST http://localhost:8000/api/fanout/generate \
  -H "Content-Type: application/json" \
  -d '{"target_query": "best AI writing tool for SEO", "existing_content": "Your article text..."}'
```

## Tests

```bash
uv run pytest
```

The test suite covers all three AEO check functions with passing and failing cases, plus mocked LLM parsing and gap analysis logic. Tests that exercise spaCy and textstat run against real NLP — no mocking of the scoring logic itself.

## What Was Completed

All deliverables are implemented:
- `POST /api/aeo/analyze` with all 3 checks (Direct Answer, H-tag Hierarchy, Snippet Readability)
- `POST /api/fanout/generate` with structured LLM prompt, Pydantic validation, retry logic, and optional gap analysis
- Unit tests for all 3 AEO checks + LLM parsing + gap analysis
- `PROMPT_LOG.md` documenting prompt iteration

## Prompt Design

The fan-out prompt is structured as a system message with explicit rules, type definitions, and a complete worked example. Key choices:

**JSON mode (`response_format: json_object`)** — OpenAI's JSON mode guarantees syntactically valid JSON, eliminating parse failures. This alone removes the most common failure mode. Schema validation (correct types, ≥10 sub-queries) is then handled by Pydantic on the parsed output.

**Explicit rules numbered 1–7** — LLMs follow numbered lists more reliably than prose paragraphs. Each rule is a single, unambiguous constraint.

**Full worked example in the prompt** — showing the exact output structure for a different topic prevents the model from drifting on format while staying generalizable across query domains.

**Type definitions** — brief one-line descriptions of all 6 types prevent the model from guessing what `trust_signals` or `feature_specific` mean and generating off-category queries.

**Minimum 2 per type enforced in prompt AND code** — the prompt requests at least 2 of each type; `_validate_response` checks total ≥ 10 and Pydantic enforces valid type strings. If either fails after 3 retries, a 503 is returned.

## Gap Analysis Threshold

The threshold of **0.72** was kept. Reasoning:

`all-MiniLM-L6-v2` cosine similarities for genuinely topically relevant sentence pairs tend to cluster around 0.65–0.85. At 0.72, a sub-query marked `covered` means the content has at least one sentence that addresses that angle substantively — not just shares vocabulary. Below 0.65 tends to be thematic overlap without direct coverage; above 0.85 is near-paraphrase.

In production I'd tune this with labeled data: sample 50–100 (sub-query, content) pairs, manually label coverage, and pick the threshold that maximises F1 on the labeled set. I'd also consider per-type thresholds — `definitional` queries often match at lower similarity than `trust_signals` because definitional content is broadly phrased.

## Embedding Model Choice

**`all-MiniLM-L6-v2`** over `all-mpnet-base-v2`. At ~22M parameters vs ~110M, MiniLM is ~5× faster at inference and ~5× smaller to load. For a real-time API where gap analysis runs on every request, that latency difference matters. The accuracy gap on semantic similarity tasks is ~3–5 STSB points — meaningful for fine-grained retrieval, acceptable for the binary covered/not-covered classification here.

## Concurrency Model

Endpoints are `async def`. URL fetching and the OpenAI call are I/O-bound and benefit from async. spaCy and sentence-transformers are CPU-bound synchronous libraries called directly inside the async endpoint — this blocks the event loop during processing. For a production service under concurrent load, these should be moved to `asyncio.run_in_executor()` with a thread pool. For this single-tenant assignment context the blocking is acceptable.

## Content Parsing Edge Cases

- **No `<p>` tags** — falls back to `get_text()` split by `\n\n`, treating line-break-separated blocks as paragraphs
- **JavaScript-heavy pages** — `httpx` fetches raw HTML; JS-rendered content will be missing. Production fix: use Playwright or a headless browser
- **Login-walled pages** — HTTP 4xx is caught and returned as a 422 with `url_fetch_failed`
- **Plain text input** — auto-detected via BeautifulSoup parse; H-tag check gracefully returns 0 with a note

## What I'd Improve With More Time

See `TECHNICAL_DECISIONS.md` for the detailed answer. Short version: add a `run_in_executor` wrapper around the CPU-bound NLP calls so the API doesn't block under concurrent load.
