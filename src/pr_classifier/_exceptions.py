from __future__ import annotations

from pr_classifier._models import ClassificationReport


class AuthenticationError(Exception):
    """Raised when the GitHub token is missing, invalid, or expired."""


class PartialResultError(Exception):
    """Raised when one or more repositories were inaccessible.

    The `report` attribute contains a `ClassificationReport` with partial
    results and per-repo error messages for the inaccessible repositories.
    """

    def __init__(self, report: ClassificationReport) -> None:
        self.report = report
        super().__init__(
            f"One or more repositories were inaccessible; "
            f"partial results available on .report"
        )
