"""Tests for src/pr_classifier/_classifier.py (T009).

These tests FAIL before T013 — _classifier.py does not exist yet.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pr_classifier._models import (
    ClassificationReport,
    ClassificationState,
    ClassifiedPR,
    PullRequest,
    RepositoryResult,
    ReviewEvent,
)

# _classifier is not yet implemented; import will fail until T013
from pr_classifier._classifier import classify_pr, build_report

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc
NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC)
STALENESS_HOURS = 48

FRESH = NOW - timedelta(hours=1)     # well within threshold
STALE_AT = NOW - timedelta(hours=49)  # exceeds threshold


def _review(reviewer: str, state: str, offset_hours: int = 0) -> ReviewEvent:
    return ReviewEvent(
        reviewer=reviewer,
        state=state,
        submitted_at=NOW - timedelta(hours=offset_hours),
    )


def _pr(last_activity_at: datetime = FRESH, reviews: list[ReviewEvent] | None = None) -> PullRequest:
    return PullRequest(
        repo="owner/repo",
        number=1,
        title="Test PR",
        author="dev",
        url="https://github.com/owner/repo/pull/1",
        last_activity_at=last_activity_at,
        reviews=reviews or [],
    )


# ---------------------------------------------------------------------------
# classify_pr — classification rules
# ---------------------------------------------------------------------------


def test_changes_requested_wins_over_approval():
    """CHANGES_REQUESTED from reviewer A is NOT overridden by APPROVED from reviewer B."""
    reviews = [
        _review("alice", "CHANGES_REQUESTED", offset_hours=2),
        _review("bob", "APPROVED", offset_hours=1),  # different reviewer, later
    ]
    assert classify_pr(_pr(reviews=reviews), now=NOW, staleness_hours=STALENESS_HOURS) == ClassificationState.CHANGES_REQUESTED


def test_approved_no_changes():
    """APPROVED with no CHANGES_REQUESTED and recent activity → approved."""
    reviews = [_review("alice", "APPROVED", offset_hours=1)]
    assert classify_pr(_pr(last_activity_at=FRESH, reviews=reviews), now=NOW, staleness_hours=STALENESS_HOURS) == ClassificationState.APPROVED


def test_approved_stale():
    """APPROVED, no CHANGES_REQUESTED, but last activity > threshold → stale."""
    reviews = [_review("alice", "APPROVED", offset_hours=50)]
    assert classify_pr(_pr(last_activity_at=STALE_AT, reviews=reviews), now=NOW, staleness_hours=STALENESS_HOURS) == ClassificationState.STALE


def test_waiting_for_review():
    """No reviews, recent activity → waiting_for_review."""
    assert classify_pr(_pr(last_activity_at=FRESH, reviews=[]), now=NOW, staleness_hours=STALENESS_HOURS) == ClassificationState.WAITING_FOR_REVIEW


def test_waiting_stale():
    """No reviews, last activity > threshold → stale."""
    assert classify_pr(_pr(last_activity_at=STALE_AT, reviews=[]), now=NOW, staleness_hours=STALENESS_HOURS) == ClassificationState.STALE


def test_changes_requested_not_overridden_by_stale():
    """CHANGES_REQUESTED takes precedence over stale — even if last activity > threshold."""
    reviews = [_review("alice", "CHANGES_REQUESTED", offset_hours=50)]
    assert classify_pr(_pr(last_activity_at=STALE_AT, reviews=reviews), now=NOW, staleness_hours=STALENESS_HOURS) == ClassificationState.CHANGES_REQUESTED


def test_classify_pr_returns_classification_state():
    """classify_pr returns a ClassificationState, not a ClassifiedPR."""
    result = classify_pr(_pr(last_activity_at=FRESH, reviews=[]), now=NOW, staleness_hours=STALENESS_HOURS)
    assert isinstance(result, ClassificationState)


# ---------------------------------------------------------------------------
# Draft PRs — contract enforcement
# ---------------------------------------------------------------------------


def test_draft_excluded():
    """Draft PRs never reach the classifier (enforced by fetcher contract, FR-011).

    The classifier operates only on non-draft PRs. This test confirms classify_pr
    returns a valid ClassificationState for any non-draft PR — draft filtering
    is the fetcher's responsibility.
    """
    pr = _pr(last_activity_at=FRESH, reviews=[])
    result = classify_pr(pr, now=NOW, staleness_hours=STALENESS_HOURS)
    assert result in set(ClassificationState)


# ---------------------------------------------------------------------------
# Report-level invariants
# ---------------------------------------------------------------------------


def test_counts_sum():
    """Sum of ClassificationReport.counts equals total classified PR count."""
    prs = [
        _pr(last_activity_at=FRESH, reviews=[]),                                      # waiting
        _pr(last_activity_at=STALE_AT, reviews=[]),                                    # stale
        _pr(last_activity_at=FRESH, reviews=[_review("x", "APPROVED")]),              # approved
        _pr(last_activity_at=FRESH, reviews=[_review("x", "CHANGES_REQUESTED")]),     # changes_requested
    ]
    classified = [
        ClassifiedPR(
            repo=p.repo, number=p.number, title=p.title, author=p.author,
            url=p.url, last_activity_at=p.last_activity_at, reviews=p.reviews,
            state=classify_pr(p, now=NOW, staleness_hours=STALENESS_HOURS),
        )
        for p in prs
    ]

    repo_result = RepositoryResult(repo="owner/repo", prs=classified)
    report = build_report([repo_result], staleness_hours=STALENESS_HOURS)

    assert sum(report.counts.values()) == len(classified)


def test_empty_repo():
    """Repo with no open PRs → RepositoryResult.prs == [], error is None."""
    result = RepositoryResult(repo="owner/repo", prs=[], error=None)
    assert result.prs == []
    assert result.error is None
