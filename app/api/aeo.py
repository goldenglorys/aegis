from __future__ import annotations

from fastapi import APIRouter, Body

from app.models.schemas import AEORequest, AEOResponse
from app.services.aeo_checks import DirectAnswerCheck, HtagHierarchyCheck, ReadabilityCheck
from app.services.content_parser import fetch_url, is_html

router = APIRouter()

_MAX_RAW_SCORE = 60

_AEO_EXAMPLES = {
    "Analyze a URL": {
        "summary": "Analyze a URL",
        "value": {
            "input_type": "url",
            "input_value": "https://en.wikipedia.org/wiki/Search_engine_optimization",
        },
    },
    "Analyze pasted HTML": {
        "summary": "Analyze pasted HTML",
        "value": {
            "input_type": "text",
            "input_value": (
                "<h1>What Is SEO?</h1>"
                "<p>SEO is the practice of optimising web content so search engines "
                "rank it higher in results pages.</p>"
                "<h2>Why It Matters</h2>"
                "<p>Higher rankings drive organic traffic without paid advertising.</p>"
                "<h2>Key Techniques</h2>"
                "<h3>On-page SEO</h3>"
                "<p>Optimise titles, headings, and content for target keywords.</p>"
            ),
        },
    },
    "Analyze plain text": {
        "summary": "Analyze plain text",
        "value": {
            "input_type": "text",
            "input_value": (
                "Python is a high-level programming language valued for its clear syntax "
                "and large ecosystem.\n\nIt is widely used in data science, web development, "
                "and automation."
            ),
        },
    },
}


def _band(score: float) -> str:
    if score >= 85:
        return "AEO Optimized"
    if score >= 65:
        return "Needs Improvement"
    if score >= 40:
        return "Significant Gaps"
    return "Not AEO Ready"


@router.post(
    "/analyze",
    response_model=AEOResponse,
    summary="Score content for AEO readiness",
    description="""
Accepts a **URL** or **raw text/HTML** and runs three NLP checks:

| Check | Max Score | What it tests |
|---|---|---|
| **Direct Answer Detection** | 20 | First paragraph ≤ 60 words, declarative, no hedging |
| **H-tag Hierarchy** | 20 | Valid H1→H2→H3 structure, no skipped levels |
| **Snippet Readability** | 20 | Flesch-Kincaid Grade Level 7–9 |

**AEO Readiness Score** = `(sum of checks / 60) × 100`

Score bands: `AEO Optimized` (85–100) · `Needs Improvement` (65–84) · `Significant Gaps` (40–64) · `Not AEO Ready` (0–39)
""",
)
async def analyze(
    request: AEORequest = Body(openapi_examples=_AEO_EXAMPLES),
) -> AEOResponse:
    if request.input_type == "url":
        content = await fetch_url(request.input_value)
        content_is_html = True
    else:
        content = request.input_value
        content_is_html = is_html(content)

    checks = [
        DirectAnswerCheck().run(content, content_is_html),
        HtagHierarchyCheck().run(content, content_is_html),
        ReadabilityCheck().run(content, content_is_html),
    ]

    raw = sum(c.score for c in checks)
    aeo_score = round((raw / _MAX_RAW_SCORE) * 100, 1)

    return AEOResponse(aeo_score=aeo_score, band=_band(aeo_score), checks=checks)
