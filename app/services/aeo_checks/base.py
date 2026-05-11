from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.schemas import CheckResult


class BaseCheck(ABC):
    @abstractmethod
    def run(self, content: str, content_is_html: bool = True) -> CheckResult:
        """Run the check and return a CheckResult."""
        ...
