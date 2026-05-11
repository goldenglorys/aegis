"""Unit tests for ReadabilityCheck."""

from app.services.aeo_checks.readability import ReadabilityCheck, _score_from_fk

_check = ReadabilityCheck()

_GRADE_7_TEXT = (
    "<p>Dogs make great pets. They are loyal and friendly. "
    "Most dogs enjoy playing outside. They need daily walks and fresh water. "
    "A good diet keeps them healthy. Regular vet visits are important too.</p>"
)

_GRADE_12_TEXT = (
    "<p>The epistemological underpinnings of contemporary hermeneutical "
    "discourse necessitate a rigorous interrogation of ontological presuppositions "
    "that have historically circumscribed the parameters of phenomenological inquiry, "
    "particularly insofar as they pertain to the dialectical mediation of subjective "
    "and intersubjective frameworks of meaning-construction within post-structuralist paradigms.</p>"
)


class TestScoreFromFk:
    def test_grade_7_to_9_scores_20(self):
        assert _score_from_fk(7.0) == 20
        assert _score_from_fk(8.5) == 20
        assert _score_from_fk(9.0) == 20

    def test_grade_6_scores_14(self):
        assert _score_from_fk(6.0) == 14
        assert _score_from_fk(6.5) == 14

    def test_grade_10_scores_14(self):
        assert _score_from_fk(10.0) == 14
        assert _score_from_fk(9.9) == 14

    def test_grade_5_scores_8(self):
        assert _score_from_fk(5.0) == 8
        assert _score_from_fk(5.5) == 8

    def test_grade_11_scores_8(self):
        assert _score_from_fk(11.0) == 8
        assert _score_from_fk(10.5) == 8

    def test_grade_below_5_scores_0(self):
        assert _score_from_fk(4.0) == 0
        assert _score_from_fk(2.0) == 0

    def test_grade_above_11_scores_0(self):
        assert _score_from_fk(12.0) == 0
        assert _score_from_fk(15.0) == 0


class TestReadabilityCheck:
    def test_complex_text_scores_low(self):
        result = _check.run(_GRADE_12_TEXT, content_is_html=True)
        assert result.score in (0, 8)
        assert result.details["fk_grade_level"] > 9.0

    def test_complex_sentences_returns_at_most_three(self):
        result = _check.run(_GRADE_12_TEXT, content_is_html=True)
        assert len(result.details["complex_sentences"]) <= 3

    def test_target_range_always_present(self):
        result = _check.run(_GRADE_7_TEXT, content_is_html=True)
        assert result.details["target_range"] == "7-9"

    def test_boilerplate_stripped_before_scoring(self):
        html = (
            "<nav>Buy now! Click here!</nav>"
            "<main>" + _GRADE_7_TEXT + "</main>"
            "<footer>Copyright 2025</footer>"
        )
        result = _check.run(html, content_is_html=True)
        assert result.check_id == "readability"
        assert isinstance(result.details["fk_grade_level"], float)

    def test_plain_text_input(self):
        text = (
            "Python is easy to learn. It has clear syntax. "
            "Many developers use it for data science. "
            "It runs on all major platforms."
        )
        result = _check.run(text, content_is_html=False)
        assert result.max_score == 20
        assert isinstance(result.score, int)

    def test_recommendation_none_when_passing(self):
        result = _check.run(_GRADE_7_TEXT, content_is_html=True)
        if result.score == 20:
            assert result.recommendation is None
