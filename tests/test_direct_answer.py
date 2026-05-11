"""Unit tests for DirectAnswerCheck."""

from app.services.aeo_checks.direct_answer import DirectAnswerCheck

_check = DirectAnswerCheck()


def _html(paragraph: str) -> str:
    return f"<html><body><p>{paragraph}</p></body></html>"


class TestDirectAnswerCheck:
    def test_perfect_score_short_declarative(self):
        html = _html("Python is a high-level programming language known for its clear syntax.")
        result = _check.run(html, content_is_html=True)
        assert result.score == 20
        assert result.passed is True
        assert result.details["is_declarative"] is True
        assert result.details["has_hedge_phrase"] is False

    def test_hedge_phrase_reduces_score(self):
        html = _html(
            "It depends on your use case, but Python is generally a good choice "
            "for data science tasks."
        )
        result = _check.run(html, content_is_html=True)
        assert result.score == 12
        assert result.passed is False
        assert result.details["has_hedge_phrase"] is True

    def test_word_count_61_to_90_scores_8(self):
        words = " ".join(["word"] * 70)
        html = _html(f"The system processes {words} efficiently.")
        result = _check.run(html, content_is_html=True)
        assert result.score == 8
        assert 61 <= result.details["word_count"] <= 90

    def test_word_count_over_90_scores_0(self):
        long_text = " ".join(["word"] * 95)
        html = _html(f"This document explains {long_text} in great detail.")
        result = _check.run(html, content_is_html=True)
        assert result.score == 0
        assert result.details["word_count"] > 90

    def test_plain_text_fallback(self):
        text = "Machine learning is a subset of artificial intelligence."
        result = _check.run(text, content_is_html=False)
        assert result.score in (12, 20)
        assert result.details["word_count"] <= 60

    def test_no_paragraph_tag_falls_back_to_text(self):
        html = "<html><body><div>SEO is the process of improving search visibility.</div></body></html>"
        result = _check.run(html, content_is_html=True)
        assert result.check_id == "direct_answer"
        assert isinstance(result.score, int)

    def test_recommendation_is_none_on_perfect_score(self):
        html = _html("Cats are obligate carnivores that require meat-based protein in their diet.")
        result = _check.run(html, content_is_html=True)
        if result.score == 20:
            assert result.recommendation is None
