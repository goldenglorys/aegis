"""Tests for fan-out LLM response parsing and gap analysis logic."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.fanout_engine import _LLMResponse, _validate_response


def _make_raw(sub_queries: list[dict]) -> str:
    return json.dumps({"sub_queries": sub_queries})


def _valid_payload(n: int = 12) -> list[dict]:
    types = [
        "comparative",
        "feature_specific",
        "use_case",
        "trust_signals",
        "how_to",
        "definitional",
    ]
    queries = []
    for t in types:
        for j in range(2):
            if len(queries) >= n:
                break
            queries.append({"type": t, "query": f"Sample {t} query {j}"})
    return queries[:n]


class TestValidateResponse:
    def test_valid_payload_parses_correctly(self):
        raw = _make_raw(_valid_payload(12))
        result = _validate_response(raw)
        assert isinstance(result, _LLMResponse)
        assert len(result.sub_queries) == 12

    def test_invalid_json_raises_json_decode_error(self):
        with pytest.raises(json.JSONDecodeError):
            _validate_response("not valid json {{{")

    def test_wrong_type_raises_validation_error(self):
        from pydantic import ValidationError

        bad = _make_raw([{"type": "unknown_type", "query": "something"}] * 12)
        with pytest.raises(ValidationError):
            _validate_response(bad)

    def test_too_few_sub_queries_raises_value_error(self):
        few = _make_raw(_valid_payload(3))
        with pytest.raises(ValueError, match="sub-queries"):
            _validate_response(few)

    def test_missing_sub_queries_key_raises_validation_error(self):
        from pydantic import ValidationError

        raw = json.dumps({"results": []})
        with pytest.raises(ValidationError):
            _validate_response(raw)

    def test_all_six_types_accepted(self):
        raw = _make_raw(_valid_payload(12))
        result = _validate_response(raw)
        found_types = {sq.type for sq in result.sub_queries}
        assert len(found_types) == 6


class TestGapAnalyzer:
    def test_covered_when_high_similarity(self):
        from app.services.gap_analyzer import analyze_gaps

        sub_queries = [{"type": "how_to", "query": "how to use Python for data analysis"}]
        content = "Python is widely used for data analysis with pandas and numpy."

        with patch("app.services.gap_analyzer._get_model") as mock_get_model:
            mock_model = MagicMock()
            mock_model.encode.return_value = np.array([[1.0, 0.0]])
            mock_get_model.return_value = mock_model

            result = analyze_gaps(sub_queries, content, threshold=0.72)

        assert result[0]["covered"] is True
        assert 0.0 <= result[0]["similarity_score"] <= 1.0

    def test_not_covered_when_low_similarity(self):
        from app.services.gap_analyzer import analyze_gaps

        sub_queries = [{"type": "comparative", "query": "Python vs Java performance"}]
        content = "Cats are friendly household pets."

        with patch("app.services.gap_analyzer._get_model") as mock_get_model:
            mock_model = MagicMock()
            # content encoded first, query second — orthogonal vectors → dot product = 0.0
            mock_model.encode.side_effect = [
                np.array([[1.0, 0.0]]),  # content_vecs
                np.array([[0.0, 1.0]]),  # query_vecs
            ]
            mock_get_model.return_value = mock_model

            result = analyze_gaps(sub_queries, content, threshold=0.72)

        assert result[0]["covered"] is False

    def test_empty_content_returns_all_uncovered(self):
        from app.services.gap_analyzer import analyze_gaps

        sub_queries = [{"type": "how_to", "query": "how to do X"}]
        result = analyze_gaps(sub_queries, "", threshold=0.72)
        assert result[0]["covered"] is False
        assert result[0]["similarity_score"] == 0.0

    def test_gap_summary_correct_counts(self):
        from app.services.gap_analyzer import build_gap_summary

        enriched = [
            {"type": "how_to", "query": "q1", "covered": True, "similarity_score": 0.8},
            {"type": "how_to", "query": "q2", "covered": True, "similarity_score": 0.9},
            {"type": "comparative", "query": "q3", "covered": False, "similarity_score": 0.3},
            {"type": "definitional", "query": "q4", "covered": False, "similarity_score": 0.2},
        ]
        summary = build_gap_summary(enriched)
        assert summary["covered"] == 2
        assert summary["total"] == 4
        assert summary["coverage_percent"] == 50.0
        assert "how_to" in summary["covered_types"]
        assert "comparative" in summary["missing_types"]
