"""Unit tests for HtagHierarchyCheck."""

from app.services.aeo_checks.htag_hierarchy import HtagHierarchyCheck

_check = HtagHierarchyCheck()


class TestHtagHierarchyCheck:
    def test_perfect_hierarchy_scores_20(self):
        html = "<h1>Title</h1><h2>Section</h2><h3>Subsection</h3><h2>Another</h2>"
        result = _check.run(html, content_is_html=True)
        assert result.score == 20
        assert result.passed is True
        assert result.details["violations"] == []

    def test_missing_h1_scores_0(self):
        html = "<h2>Section</h2><h3>Sub</h3>"
        result = _check.run(html, content_is_html=True)
        assert result.score == 0
        assert result.passed is False
        assert any("H1" in v for v in result.details["violations"])

    def test_skipped_level_h1_to_h3_scores_12(self):
        html = "<h1>Title</h1><h3>Jumped</h3>"
        result = _check.run(html, content_is_html=True)
        assert result.score == 12
        assert len(result.details["violations"]) == 1

    def test_multiple_h1_is_violation(self):
        html = "<h1>First</h1><h2>A</h2><h1>Second</h1>"
        result = _check.run(html, content_is_html=True)
        assert result.score in (0, 12)
        assert any("Multiple H1" in v or "multiple" in v.lower() for v in result.details["violations"])

    def test_tag_before_h1_is_violation(self):
        html = "<h2>Before</h2><h1>Title</h1><h2>After</h2>"
        result = _check.run(html, content_is_html=True)
        assert result.score in (0, 12)
        violation_text = " ".join(result.details["violations"])
        assert "before" in violation_text.lower() or "H2" in violation_text

    def test_three_violations_scores_0(self):
        html = "<h2>Pre-h1</h2><h1>A</h1><h1>B</h1><h3>Skip</h3>"
        result = _check.run(html, content_is_html=True)
        assert result.score == 0

    def test_h_tags_found_preserves_order(self):
        html = "<h1>T</h1><h2>A</h2><h2>B</h2><h3>C</h3>"
        result = _check.run(html, content_is_html=True)
        assert result.details["h_tags_found"] == ["h1", "h2", "h2", "h3"]

    def test_plain_text_returns_zero_with_recommendation(self):
        result = _check.run("Just plain text here.", content_is_html=False)
        assert result.score == 0
        assert result.recommendation is not None
