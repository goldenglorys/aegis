from __future__ import annotations

from bs4 import BeautifulSoup

from app.models.schemas import CheckResult
from app.services.aeo_checks.base import BaseCheck

_HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]
_LEVEL = {f"h{i}": i for i in range(1, 7)}


class HtagHierarchyCheck(BaseCheck):
    """Check B — H-tag Hierarchy Checker (max 20 pts)."""

    def run(self, content: str, content_is_html: bool = True) -> CheckResult:
        if not content_is_html:
            return CheckResult(
                check_id="htag_hierarchy",
                name="H-tag Hierarchy",
                passed=False,
                score=0,
                max_score=20,
                details={"violations": ["No HTML content to parse headings from"], "h_tags_found": []},
                recommendation="Provide HTML content to enable heading structure analysis.",
            )

        soup = BeautifulSoup(content, "html.parser")
        h_tags = [tag.name for tag in soup.find_all(_HEADING_TAGS)]

        violations: list[str] = []
        h1_count = h_tags.count("h1")

        if h1_count == 0:
            violations.append("No H1 tag found")
        elif h1_count > 1:
            violations.append(f"Multiple H1 tags found ({h1_count})")

        if h1_count > 0:
            h1_index = h_tags.index("h1")
            if h1_index > 0:
                pre = ", ".join(t.upper() for t in h_tags[:h1_index])
                violations.append(f"Heading(s) appear before H1: {pre}")

        for i in range(1, len(h_tags)):
            prev_level = _LEVEL[h_tags[i - 1]]
            curr_level = _LEVEL[h_tags[i]]
            if curr_level > prev_level + 1:
                violations.append(
                    f"Heading level skipped: {h_tags[i - 1].upper()} → {h_tags[i].upper()}"
                )

        n = len(violations)
        if h1_count == 0 or n >= 3:
            score = 0
        elif n == 0:
            score = 20
        else:
            score = 12

        recommendation = (
            f"Fix heading hierarchy: {'; '.join(violations)}."
            if violations
            else None
        )

        return CheckResult(
            check_id="htag_hierarchy",
            name="H-tag Hierarchy",
            passed=score == 20,
            score=score,
            max_score=20,
            details={"violations": violations, "h_tags_found": h_tags},
            recommendation=recommendation,
        )
