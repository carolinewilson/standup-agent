# Public API — models/exceptions populated by T006/T007; implementation by T015
from __future__ import annotations

from pr_classifier._classifier import build_report
from pr_classifier._exceptions import AuthenticationError, PartialResultError
from pr_classifier._fetcher import authenticate, fetch_repository
from pr_classifier._models import (
    ClassificationReport,
    ClassificationState,
    ClassifiedPR,
    RepositoryResult,
)

__all__ = [
    "classify_repositories",
    "ClassificationReport",
    "RepositoryResult",
    "ClassifiedPR",
    "ClassificationState",
    "AuthenticationError",
    "PartialResultError",
]


def classify_repositories(
    repos: list[str],
    token: str,
    staleness_hours: int = 48,
) -> ClassificationReport:
    """Retrieve and classify open GitHub pull requests across one or more repositories.

    Parameters
    ----------
    repos:
        Non-empty list of repository identifiers in ``owner/repo`` format.
    token:
        GitHub personal access token.
    staleness_hours:
        Inactivity threshold in hours for the Stale classification (default 48).

    Raises
    ------
    ValueError
        If ``repos`` is empty or ``staleness_hours`` is not a positive integer.
    AuthenticationError
        If the token is invalid or expired.
    PartialResultError
        If one or more repositories were inaccessible; ``.report`` contains
        partial results with per-repo error messages.
    """
    if not repos:
        raise ValueError("repos must not be empty.")
    if not token:
        raise ValueError("token must not be empty.")
    if staleness_hours <= 0:
        raise ValueError("staleness_hours must be a positive integer.")

    github = authenticate(token)  # raises AuthenticationError on 401/403

    results: list[RepositoryResult] = []
    for repo_id in repos:
        results.append(fetch_repository(github, repo_id, staleness_hours))

    report = build_report(results, staleness_hours)

    if any(r.error is not None for r in results):
        raise PartialResultError(report)

    return report

