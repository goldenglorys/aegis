from __future__ import annotations

from fastapi import APIRouter, Body

from app.models.schemas import FanOutRequest, FanOutResponse, GapSummary, SubQuery
from app.services.fanout_engine import generate_sub_queries
from app.services.gap_analyzer import analyze_gaps, build_gap_summary

router = APIRouter()

_FANOUT_EXAMPLES = {
    "Sub-queries only": {
        "summary": "Sub-queries only (no gap analysis)",
        "value": {
            "target_query": "best AI writing tool for SEO",
        },
    },
    "With gap analysis": {
        "summary": "Sub-queries + gap analysis against existing content",
        "value": {
            "target_query": "best AI writing tool for SEO",
            "existing_content": (
                "AI writing tools help SEO teams produce content faster. "
                "Top tools include Jasper, Copy.ai, and Surfer SEO. "
                "These tools use large language models to generate drafts "
                "based on target keywords and content briefs. "
                "Jasper is often compared to human writers for blog content. "
                "Surfer SEO integrates keyword clustering directly into the editor."
            ),
        },
    },
}


@router.post(
    "/generate",
    response_model=FanOutResponse,
    response_model_exclude_none=True,
    summary="Generate sub-queries and analyse content gaps",
    description="""
Uses **GPT-4o-mini** to decompose a target query into 12–15 sub-queries across 6 intent types:

| Type | Description |
|---|---|
| `comparative` | Positions subject against alternatives |
| `feature_specific` | Focuses on a specific capability |
| `use_case` | Real-world application scenario |
| `trust_signals` | Reviews, case studies, proof points |
| `how_to` | Procedural / instructional queries |
| `definitional` | Conceptual "what is" framing |

**Gap analysis** is performed when `existing_content` is provided — each sub-query is compared
against sentence-level chunks of your content using `all-MiniLM-L6-v2` embeddings
(cosine similarity threshold: **0.72**).

`covered`, `similarity_score`, and `gap_summary` are omitted when no content is supplied.
""",
)
async def generate(
    request: FanOutRequest = Body(openapi_examples=_FANOUT_EXAMPLES),
) -> FanOutResponse:
    sub_queries_raw, model_used = await generate_sub_queries(request.target_query)

    if request.existing_content:
        enriched = analyze_gaps(sub_queries_raw, request.existing_content)
        sub_queries = [SubQuery(**sq) for sq in enriched]
        summary_data = build_gap_summary(enriched)
        gap_summary = GapSummary(**summary_data)
    else:
        sub_queries = [SubQuery(**sq) for sq in sub_queries_raw]
        gap_summary = None

    return FanOutResponse(
        target_query=request.target_query,
        model_used=model_used,
        total_sub_queries=len(sub_queries),
        sub_queries=sub_queries,
        gap_summary=gap_summary,
    )
