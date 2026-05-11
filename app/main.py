from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from app.api import aeo, fanout

_DESCRIPTION = """
**AEGIS** — Answer Engine & Generative Intelligence Suite.

A content intelligence API that scores and diagnoses content for AEO/GEO readiness,
and simulates how AI search engines decompose queries to surface coverage gaps.

## Endpoints

| Endpoint | Description |
|---|---|
| `POST /api/aeo/analyze` | Score content across 3 NLP checks and return an AEO Readiness Score (0–100) |
| `POST /api/fanout/generate` | Generate 12–15 sub-queries via LLM and optionally map coverage gaps in your content |
"""

_TAGS = [
    {
        "name": "aeo",
        "description": (
            "**AEO Content Scorer** — runs three NLP checks on a URL or pasted content: "
            "Direct Answer Detection, H-tag Hierarchy, and Snippet Readability. "
            "Returns a normalised AEO Readiness Score (0–100) with per-check diagnostics."
        ),
    },
    {
        "name": "fanout",
        "description": (
            "**Query Fan-Out Engine** — uses GPT-4o-mini to decompose a target query into "
            "12–15 sub-queries across 6 intent types. "
            "Optionally computes semantic coverage gaps against your existing content "
            "using sentence-transformer embeddings."
        ),
    },
]

app = FastAPI(
    title="AEGIS",
    description=_DESCRIPTION,
    version="1.0.0",
    openapi_tags=_TAGS,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(aeo.router, prefix="/api/aeo", tags=["aeo"])
app.include_router(fanout.router, prefix="/api/fanout", tags=["fanout"])


@app.get("/", include_in_schema=False)
async def root() -> JSONResponse:
    return JSONResponse({"service": "AEGIS", "status": "ok", "docs": "/docs"})
