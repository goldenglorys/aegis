# Technical Decisions & Thought Process

---

## Architecture Overview

Two FastAPI routers (`/api/aeo`, `/api/fanout`) backed by a service layer. Each AEO check is an independent class inheriting from `BaseCheck`, making the pipeline addable-to without touching existing code. The gap analyzer and fanout engine are pure functions wrapped in thin async endpoints.

---

## Decisions I'm Confident About

### 1. OpenAI JSON Mode for LLM Reliability

The single biggest reliability risk in the fan-out feature is the LLM returning malformed JSON. The fix is architectural: use `response_format={"type": "json_object"}`, which guarantees syntactically valid JSON at the API level before my code ever sees it. Schema validation (correct field names, valid type strings, minimum sub-query count) is then a clean Pydantic layer on top.

This separation is important: JSON mode handles syntax, Pydantic handles semantics. Without JSON mode, you're writing regex or fallback parsers for malformed output — fragile and untestable. With it, `json.loads()` never fails, and the only failures are schema-level, which retry logic can meaningfully address.

**Confidence: high.** The alternative (prompt the model to produce correct JSON and hope) fails in ~10–15% of runs without JSON mode, more on edge-case queries.

### 2. `all-MiniLM-L6-v2` for Embeddings

Chose speed over accuracy. At 22M parameters, MiniLM loads in ~1s vs ~4s for mpnet and runs inference ~5× faster. The accuracy difference on STSB is ~3–4 points. For a binary covered/not-covered classification at a fixed threshold, this is an acceptable trade. The threshold absorbs some of the accuracy difference — you can compensate for noisier embeddings with a slightly more conservative threshold.

In production, the right answer is to benchmark both models on a labeled dataset of (sub-query, content, covered) triples and pick based on F1, not benchmark scores. MiniLM wins on cost-per-query at scale.

**Confidence: high** for the reasoning; medium on whether the accuracy trade-off matters in practice (depends on the content domain).

### 3. spaCy Dependency Parser for Declarative Check

Using `tok.dep_ in ("nsubj", "nsubjpass")` and `tok.dep_ == "ROOT" and tok.pos_ == "VERB"` is more precise than a regex-based approach. A regex can detect "?" for questions but can't detect sentence fragments or passive constructions without a subject. The dep parser handles these correctly.

The `en_core_web_sm` model is accurate enough for this purpose — it's checking for gross structural properties (does this sentence have a subject? is the root a verb?), not fine-grained parsing. Using `en_core_web_lg` would improve accuracy on edge cases but isn't worth the 500MB model size for this check.

**Confidence: high.**

### 4. Tenacity for Retry Logic

Using `tenacity` with exponential backoff (`wait_exponential(multiplier=1, min=1, max=8)`) on `RateLimitError`, `APITimeoutError`, and `APIConnectionError`, plus retrying on `ValueError` (when sub-query count < 10). Three attempts before raising a 503.

The key insight: retrying on `ValueError` (too few sub-queries) is correct because this is often a transient model behavior on edge-case queries — a second call with the same prompt frequently produces a complete response.

**Confidence: high.**

### 5. Cosine Similarity via Dot Product on L2-Normalized Vectors

`sentence-transformers` encode with `normalize_embeddings=True`, making all vectors unit length. Cosine similarity of unit vectors equals their dot product. A single `np.dot(query_vecs, content_vecs.T)` gives the full similarity matrix in one BLAS call — faster and numerically identical to `sklearn.metrics.pairwise.cosine_similarity` on normalized inputs, without the sklearn dependency.

**Confidence: high.** This is mathematically exact, not an approximation.

---

## Decisions I'm Less Confident About

### 6. 0.72 Similarity Threshold

Kept the provided threshold without empirical tuning. The reasoning is sound — 0.72 sits in a reasonable range for "topically covered" vs "thematically adjacent" — but this is a prior, not a measurement. The honest answer is: this threshold needs labeled data to validate. For a production deployment I'd want 100+ (sub-query, article) pairs labeled by a domain expert before committing to a number.

The concern: MiniLM's similarity distributions differ from mpnet. A threshold calibrated for mpnet may under- or over-cover with MiniLM. I'm effectively inheriting a threshold from a model I didn't use to calibrate it.

**What I'd do with more time:** Create 50 (sub-query, content-chunk, covered?) triples from real content, compute the precision-recall curve, and pick the threshold at the elbow.

### 7. Async Endpoints with Blocking NLP

Both endpoints are `async def`, which is correct for the I/O-bound parts (URL fetching, OpenAI calls). But spaCy and sentence-transformers are synchronous CPU-bound calls made directly in the async context — they block the event loop during processing.

For a single-user assignment context this is fine. For a production service handling 10+ concurrent requests, this would serialize all NLP work behind a single event loop tick and tank throughput. The fix is `asyncio.run_in_executor(pool, check.run, content, is_html)` with a `ThreadPoolExecutor` sized to the CPU count.

I made the pragmatic call to skip this for the assignment — adding run_in_executor introduces complexity (executor lifecycle, error propagation from threads) that obscures the actual NLP logic. But I'd flag this immediately in a code review.

---

## One Thing I'd Improve With Another 2 Hours

**Move the CPU-bound NLP calls off the event loop.**

Concretely: wrap the three `Check.run()` calls in `app/api/aeo.py` and the `SentenceTransformer.encode()` calls in `gap_analyzer.py` with `asyncio.get_event_loop().run_in_executor(executor, ...)`, and create a module-level `ThreadPoolExecutor` in `app/main.py` shared across requests.

This is the change with the highest production-readiness ROI. Everything else (threshold tuning, larger spaCy model, Playwright for JS-heavy pages) requires external data or infrastructure. This is pure code — ~15 lines across 3 files — and it's the difference between the service being usable under load or not.

The secondary benefit: with spaCy and sentence-transformers off the event loop, the gap analysis and AEO checks could run in parallel via `asyncio.gather()`, reducing total request latency by the time of the slowest NLP check instead of summing all three.
