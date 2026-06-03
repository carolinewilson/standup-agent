# Public API — models/exceptions populated by T006/T007; implementation by T015
from __future__ import annotations

__all__ = [
    "classify_repositories",
    "ClassificationReport",
    "RepositoryResult",
    "ClassifiedPR",
    "ClassificationState",
    "AuthenticationError",
    "PartialResultError",
]


def __getattr__(name: str):  # noqa: N807
    if name in {
        "ClassificationState",
        "ClassificationReport",
        "RepositoryResult",
        "ClassifiedPR",
    }:
        from pr_classifier._models import (  # noqa: PLC0415
            ClassificationState,
            ClassificationReport,
            RepositoryResult,
            ClassifiedPR,
        )
        return locals()[name]
    if name in {"AuthenticationError", "PartialResultError"}:
        from pr_classifier._exceptions import (  # noqa: PLC0415
            AuthenticationError,
            PartialResultError,
        )
        return locals()[name]
    raise AttributeError(f"module 'pr_classifier' has no attribute {name!r}")


def classify_repositories(
    repos: list[str],
    token: str,
    staleness_hours: int = 48,
):
    """Implemented in T015."""
    raise NotImplementedError("Implemented in T015")
