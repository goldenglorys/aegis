from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel


class AEORequest(BaseModel):
    input_type: Literal["url", "text"]
    input_value: str


class CheckResult(BaseModel):
    check_id: str
    name: str
    passed: bool
    score: int
    max_score: int
    details: dict[str, Any]
    recommendation: Optional[str] = None


class AEOResponse(BaseModel):
    aeo_score: float
    band: str
    checks: list[CheckResult]


class FanOutRequest(BaseModel):
    target_query: str
    existing_content: Optional[str] = None


class SubQuery(BaseModel):
    type: str
    query: str
    covered: Optional[bool] = None
    similarity_score: Optional[float] = None


class GapSummary(BaseModel):
    covered: int
    total: int
    coverage_percent: float
    covered_types: list[str]
    missing_types: list[str]


class FanOutResponse(BaseModel):
    target_query: str
    model_used: str
    total_sub_queries: int
    sub_queries: list[SubQuery]
    gap_summary: Optional[GapSummary] = None
