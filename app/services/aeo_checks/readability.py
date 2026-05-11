from __future__ import annotations

import re

import textstat

from app.models.schemas import CheckResult
from app.services.content_parser import extract_plain_text
from app.services.aeo_checks.base import BaseCheck

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _syllable_density(sentence: str) -> float:
    """Return syllables per word — used to rank sentence complexity."""
    words = sentence.split()
    if not words:
        return 0.0
    return textstat.syllable_count(sentence) / len(words)


def _score_from_fk(fk: float) -> int:
    if 7.0 <= fk <= 9.0:
        return 20
    if (6.0 <= fk < 7.0) or (9.0 < fk <= 10.0):
        return 14
    if (5.0 <= fk < 6.0) or (10.0 < fk <= 11.0):
        return 8
    return 0


class ReadabilityCheck(BaseCheck):
    """Check C — Snippet Readability Scorer (max 20 pts)."""

    def run(self, content: str, content_is_html: bool = True) -> CheckResult:
        text = extract_plain_text(content, content_is_html)

        fk = textstat.flesch_kincaid_grade(text)
        score = _score_from_fk(fk)

        sentences = [s.strip() for s in _SENTENCE_SPLIT.split(text) if len(s.split()) > 3]
        complex_sentences = sorted(sentences, key=_syllable_density, reverse=True)[:3]

        if score == 20:
            recommendation = None
        elif fk > 9.0:
            recommendation = (
                f"Content reads at Grade {fk:.1f}. Shorten sentences and replace "
                "technical jargon with plain language to reach Grade 7–9."
            )
        else:
            recommendation = (
                f"Content reads at Grade {fk:.1f}. Add more substance and complete "
                "sentences to reach Grade 7–9."
            )

        return CheckResult(
            check_id="readability",
            name="Snippet Readability",
            passed=score == 20,
            score=score,
            max_score=20,
            details={
                "fk_grade_level": round(fk, 1),
                "target_range": "7-9",
                "complex_sentences": complex_sentences,
            },
            recommendation=recommendation,
        )
