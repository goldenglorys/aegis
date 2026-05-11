# Prompt Iteration Log — Fan-Out Engine

## Draft 1 — Minimal Instruction

```
Generate 10-15 sub-queries for the query: "{target_query}".
Types: comparative, feature_specific, use_case, trust_signals, how_to, definitional.
Return JSON.
```

**Problems observed:**
- Model returned markdown-wrapped JSON (```json ... ```) instead of bare JSON — broke `json.loads()` on the first try
- "Return JSON" is ambiguous: model chose its own schema, sometimes returning `{"queries": [...]}`, sometimes `[...]` (bare array), sometimes `{"results": {...}}`
- Type distribution was uneven — `how_to` and `use_case` appeared 5–6 times each; `trust_signals` appeared 0–1 times
- Some sub-queries were too generic ("what is SEO?") regardless of the specific target query
- No example meant the model had to guess field names — it used `"text"` instead of `"query"` in one run

---

## Draft 2 — Schema in System Message, No Example

Added an explicit JSON schema to the system message and banned markdown fences:

```
Return ONLY a valid JSON object — no markdown, no prose.
Schema: {"sub_queries": [{"type": "<one of 6>", "query": "<string>"}]}
Include at least 2 sub-queries per type, 12–15 total.
```

**Improvements:** JSON parse failures dropped to ~1 in 10. Schema was usually correct.

**Remaining problems:**
- Still occasionally returned `{"sub_queries": {"comparative": [...], ...}}` (nested by type) instead of a flat array — model "helpfully" reorganized it
- "At least 2 per type" was sometimes ignored: on abstract queries like `"what is consciousness"`, `comparative` and `trust_signals` would appear only once because the model found them awkward to generate
- No handling for the nested-by-type format meant Pydantic validation would raise on ~10% of calls

---

## Draft 3 — Numbered Rules + Full Example (Final)

Key changes from Draft 2:

1. **Switched to JSON mode** (`response_format: {"type": "json_object"}`) — guarantees syntactically valid JSON from the API, eliminating the parse layer failure entirely
2. **Numbered rules instead of prose** — each constraint is a numbered item, not a paragraph
3. **Added type definitions** — one-line description of each type prevents category confusion
4. **Added a complete worked example** for a different topic (`"best project management software"`) — this anchors the format and demonstrates diversity without leaking the user's actual query into the example
5. **Made the "no extra keys" rule explicit** — prevents the model from adding `"relevance"` or `"priority"` fields

**Result:** After switching to JSON mode + this prompt, 0 JSON parse failures in 20 test runs. Pydantic validation still catches 1–2 responses per 20 where total sub-query count is < 10 (usually when the target query is very narrow), which triggers the retry logic correctly.

## Final Prompt

See `app/services/fanout_engine.py` — `_SYSTEM_PROMPT` and `_USER_TEMPLATE` constants.
