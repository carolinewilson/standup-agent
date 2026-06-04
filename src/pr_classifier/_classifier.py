from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pr_classifier._models import (
    ClassificationReport,
    ClassificationState,
    PullRequest,
    RepositoryResult,
)


def classify_pr(pr: PullRequest, staleness_hours: int, now: datetime) -> ClassificationState:
    """Classify a single pull request, returning its ClassificationState.

    Precedence (highest to lowest):
    1. changes_requested  — any CHANGES_REQUESTED review exists
    2. stale              — last_activity_at older than staleness_hours
    3. approved           — at least one APPROVED, no CHANGES_REQUESTED
    4. waiting_for_review — no reviews at all

    Parameters
    ----------
    pr:
        A non-draft PullRequest with reviews already fetched.
    staleness_hours:
        Inactivity threshold in hours.
    now:
        Current UTC datetime (injected for deterministic testing).
    """
    has_changes_requested = any(
        rv.state == "CHANGES_REQUESTED" for rv in pr.reviews
    )
    if has_changes_requested:
        return ClassificationState.CHANGES_REQUESTED

    threshold = now - timedelta(hours=staleness_hours)
    if pr.last_activity_at < threshold:
        return ClassificationState.STALE

    if any(rv.state == "APPROVED" for rv in pr.reviews):
        return ClassificationState.APPROVED

    return ClassificationState.WAITING_FOR_REVIEW


def build_report(
    repo_results: list[RepositoryResult],
    staleness_hours: int,
) -> ClassificationReport:
    """Assemble a ClassificationReport from a list of RepositoryResult objects.

    Computes aggregate counts across all classified PRs and stamps generated_at
    with the current UTC time.
    """
    counts: dict[str, int] = {s.value: 0 for s in ClassificationState}
    for repo_result in repo_results:
        for cpr in repo_result.prs:
            counts[cpr.state.value] += 1

    return ClassificationReport(
        repositories=repo_results,
        generated_at=datetime.now(tz=timezone.utc),
        staleness_threshold_hours=staleness_hours,
        counts=counts,
    )
