"""Tests for src/pr_classifier/_models.py (T008)."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from pr_classifier._models import (
    ClassificationReport,
    ClassificationState,
    ClassifiedPR,
    PullRequest,
    RepositoryResult,
    ReviewEvent,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

UTC = timezone.utc
NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC)


def make_review(**kwargs) -> ReviewEvent:
    defaults = dict(reviewer="alice", state="APPROVED", submitted_at=NOW)
    return ReviewEvent(**{**defaults, **kwargs})


def make_pr(**kwargs) -> PullRequest:
    defaults = dict(
        repo="owner/repo",
        number=1,
        title="Fix bug",
        author="bob",
        url="https://github.com/owner/repo/pull/1",
        last_activity_at=NOW,
        reviews=[],
    )
    return PullRequest(**{**defaults, **kwargs})


def make_classified_pr(**kwargs) -> ClassifiedPR:
    defaults = dict(
        repo="owner/repo",
        number=1,
        title="Fix bug",
        author="bob",
        url="https://github.com/owner/repo/pull/1",
        last_activity_at=NOW,
        reviews=[],
        state=ClassificationState.WAITING_FOR_REVIEW,
    )
    return ClassifiedPR(**{**defaults, **kwargs})


# ---------------------------------------------------------------------------
# ClassificationState
# ---------------------------------------------------------------------------


def test_classification_state_has_exactly_four_members():
    assert len(ClassificationState) == 4


def test_classification_state_slugs():
    assert ClassificationState.CHANGES_REQUESTED.value == "changes_requested"
    assert ClassificationState.APPROVED.value == "approved"
    assert ClassificationState.WAITING_FOR_REVIEW.value == "waiting_for_review"
    assert ClassificationState.STALE.value == "stale"


def test_classification_state_is_str_enum():
    assert isinstance(ClassificationState.APPROVED, str)


# ---------------------------------------------------------------------------
# ReviewEvent
# ---------------------------------------------------------------------------


def test_review_event_valid_states():
    for state in ("APPROVED", "CHANGES_REQUESTED", "COMMENTED"):
        rv = make_review(state=state)
        assert rv.state == state


def test_review_event_rejects_invalid_state():
    with pytest.raises(ValueError):
        make_review(state="PENDING")


def test_review_event_rejects_naive_datetime():
    naive = datetime(2026, 6, 3, 12, 0, 0)
    with pytest.raises(ValueError):
        make_review(submitted_at=naive)


# ---------------------------------------------------------------------------
# PullRequest
# ---------------------------------------------------------------------------


def test_pull_request_rejects_zero_number():
    with pytest.raises(ValueError):
        make_pr(number=0)


def test_pull_request_rejects_negative_number():
    with pytest.raises(ValueError):
        make_pr(number=-1)


def test_pull_request_rejects_naive_last_activity_at():
    naive = datetime(2026, 6, 3, 12, 0, 0)
    with pytest.raises(ValueError):
        make_pr(last_activity_at=naive)


def test_pull_request_valid():
    pr = make_pr()
    assert pr.number == 1
    assert pr.last_activity_at.tzinfo is not None


# ---------------------------------------------------------------------------
# RepositoryResult
# ---------------------------------------------------------------------------


def test_repository_result_error_none_when_prs_populated():
    cpr = make_classified_pr()
    result = RepositoryResult(repo="owner/repo", prs=[cpr], error=None)
    assert result.error is None
    assert len(result.prs) == 1


def test_repository_result_prs_empty_when_error_set():
    result = RepositoryResult(repo="owner/repo", prs=[], error="Not found")
    assert result.prs == []
    assert result.error == "Not found"


def test_repository_result_raises_when_error_and_prs_both_set():
    cpr = make_classified_pr()
    with pytest.raises(ValueError):
        RepositoryResult(repo="owner/repo", prs=[cpr], error="oops")


# ---------------------------------------------------------------------------
# ClassificationReport
# ---------------------------------------------------------------------------


def test_classification_report_counts_keys_match_enum_slugs():
    slugs = {m.value for m in ClassificationState}
    counts = {slug: 0 for slug in slugs}
    report = ClassificationReport(
        repositories=[],
        generated_at=NOW,
        staleness_threshold_hours=48,
        counts=counts,
    )
    assert set(report.counts.keys()) == slugs


def test_classification_report_rejects_naive_generated_at():
    naive = datetime(2026, 6, 3, 12, 0, 0)
    with pytest.raises(ValueError):
        ClassificationReport(
            repositories=[],
            generated_at=naive,
            staleness_threshold_hours=48,
            counts={},
        )


def test_classification_report_rejects_zero_staleness_hours():
    with pytest.raises(ValueError):
        ClassificationReport(
            repositories=[],
            generated_at=NOW,
            staleness_threshold_hours=0,
            counts={},
        )


def test_classification_report_rejects_negative_staleness_hours():
    with pytest.raises(ValueError):
        ClassificationReport(
            repositories=[],
            generated_at=NOW,
            staleness_threshold_hours=-1,
            counts={},
        )
