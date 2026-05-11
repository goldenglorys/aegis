from __future__ import annotations

import json
import os
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
import openai

_MODEL = "gpt-4o-mini"

_VALID_TYPES = Literal[
    "comparative",
    "feature_specific",
    "use_case",
    "trust_signals",
    "how_to",
    "definitional",
]

_SYSTEM_PROMPT = """\
You are a search query decomposition engine. Your job is to simulate how an AI search engine \
decomposes a user's target query into a comprehensive set of sub-queries across different \
intent categories.

OUTPUT RULES — read carefully:
1. Return ONLY a valid JSON object. No markdown, no code fences, no prose before or after.
2. The JSON must have exactly one top-level key: "sub_queries".
3. "sub_queries" must be an array of objects. Each object must have exactly two keys:
   - "type": one of ["comparative", "feature_specific", "use_case", "trust_signals", "how_to", "definitional"]
   - "query": a specific, standalone search query string
4. Include BETWEEN 12 and 15 sub-queries total.
5. Include AT LEAST 2 sub-queries for EACH of the 6 types. This is mandatory.
6. Sub-queries must be diverse, specific, and directly relevant to the target query topic.
7. Do NOT add any other keys to sub-query objects.

TYPE DEFINITIONS:
- comparative: positions the subject against alternatives or competitors
- feature_specific: focuses on a specific capability, feature, or attribute
- use_case: real-world application or scenario
- trust_signals: reviews, case studies, credibility, proof points
- how_to: procedural, instructional, step-by-step
- definitional: conceptual explanation, "what is" framing

EXAMPLE — for target query "best project management software":
{
  "sub_queries": [
    {"type": "comparative", "query": "Asana vs Monday.com vs Notion for project management"},
    {"type": "comparative", "query": "project management software vs spreadsheets for remote teams"},
    {"type": "feature_specific", "query": "project management tool with Gantt charts and time tracking"},
    {"type": "feature_specific", "query": "project management software with automated dependency workflows"},
    {"type": "use_case", "query": "best project management software for marketing agencies"},
    {"type": "use_case", "query": "project management tool for distributed engineering teams"},
    {"type": "trust_signals", "query": "project management software reviews from Fortune 500 companies"},
    {"type": "trust_signals", "query": "top-rated project management platforms case studies 2025"},
    {"type": "how_to", "query": "how to set up a project management workflow from scratch"},
    {"type": "how_to", "query": "how to migrate from Jira to a new project management tool"},
    {"type": "definitional", "query": "what is project management software and how does it work"},
    {"type": "definitional", "query": "what features define enterprise-grade project management tools"}
  ]
}
"""

_USER_TEMPLATE = (
    'Generate 12–15 sub-queries for the following target query: "{target_query}"\n\n'
    "Remember: return ONLY the JSON object."
)


class _SubQueryItem(BaseModel):
    type: _VALID_TYPES
    query: str


class _LLMResponse(BaseModel):
    sub_queries: list[_SubQueryItem]


def _validate_response(raw: str) -> _LLMResponse:
    data = json.loads(raw)
    parsed = _LLMResponse.model_validate(data)
    if len(parsed.sub_queries) < 10:
        raise ValueError(f"Only {len(parsed.sub_queries)} sub-queries returned; expected at least 10.")
    return parsed


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    retry=retry_if_exception_type(
        (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError, ValueError)
    ),
    reraise=True,
)
async def _call_with_retry(client: AsyncOpenAI, target_query: str) -> _LLMResponse:
    response = await client.chat.completions.create(
        model=_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": _USER_TEMPLATE.format(target_query=target_query)},
        ],
        temperature=0.7,
        response_format={"type": "json_object"},
        max_tokens=2048,
    )
    return _validate_response(response.choices[0].message.content)


async def generate_sub_queries(target_query: str) -> tuple[list[dict], str]:
    """
    Return (sub_queries_as_dicts, model_name).
    Raises HTTPException 503 if LLM fails after retries.
    """
    from fastapi import HTTPException

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    try:
        result = await _call_with_retry(client, target_query)
    except (json.JSONDecodeError, ValidationError, ValueError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "llm_unavailable",
                "message": "Fan-out generation failed. The LLM returned an invalid response after 3 retries.",
                "detail": str(exc),
            },
        )
    except (openai.RateLimitError, openai.APITimeoutError, openai.APIConnectionError) as exc:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "llm_unavailable",
                "message": "Fan-out generation failed. The LLM returned an invalid response after 3 retries.",
                "detail": str(exc),
            },
        )

    sub_queries = [item.model_dump() for item in result.sub_queries]
    return sub_queries, _MODEL
