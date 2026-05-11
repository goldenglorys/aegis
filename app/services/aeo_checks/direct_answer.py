from __future__ import annotations

import spacy

from app.models.schemas import CheckResult
from app.services.content_parser import extract_first_paragraph
from app.services.aeo_checks.base import BaseCheck

_nlp = spacy.load("en_core_web_sm")

_HEDGE_PHRASES = frozenset([
    "it depends",
    "may vary",
    "in some cases",
    "this varies",
    "generally speaking",
])


def _is_declarative(text: str) -> bool:
    """Return True if text has a grammatical subject and a root verb."""
    doc = _nlp(text)
    has_subject = any(tok.dep_ in ("nsubj", "nsubjpass") for tok in doc)
    has_root_verb = any(tok.dep_ == "ROOT" and tok.pos_ in ("VERB", "AUX") for tok in doc)
    return has_subject and has_root_verb


class DirectAnswerCheck(BaseCheck):
    """Check A — Direct Answer Detection (max 20 pts)."""

    def run(self, content: str, content_is_html: bool = True) -> CheckResult:
        text = extract_first_paragraph(content, content_is_html)
        word_count = len(text.split())
        has_hedge = any(phrase in text.lower() for phrase in _HEDGE_PHRASES)
        declarative = _is_declarative(text)

        if word_count <= 60 and declarative and not has_hedge:
            score = 20
        elif word_count <= 60:
            score = 12
        elif word_count <= 90:
            score = 8
        else:
            score = 0

        if score == 20:
            recommendation = None
        elif word_count > 90:
            recommendation = (
                f"Opening paragraph is {word_count} words. "
                "Trim to under 60 words with a direct declarative answer."
            )
        elif word_count > 60:
            recommendation = (
                f"Opening paragraph is {word_count} words. "
                "Trim to under 60 words to pass this check."
            )
        elif has_hedge:
            recommendation = (
                "Remove hedging phrases (e.g. 'it depends', 'may vary') "
                "to make your answer more direct."
            )
        else:
            recommendation = (
                "Ensure the opening sentence has a clear subject and verb "
                "to form a declarative statement."
            )

        return CheckResult(
            check_id="direct_answer",
            name="Direct Answer Detection",
            passed=score == 20,
            score=score,
            max_score=20,
            details={
                "word_count": word_count,
                "threshold": 60,
                "is_declarative": declarative,
                "has_hedge_phrase": has_hedge,
            },
            recommendation=recommendation,
        )
