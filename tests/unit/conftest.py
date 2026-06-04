"""Shared pytest fixtures for unit tests (T012)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from pr_classifier._models import PullRequest, ReviewEvent

UTC = timezone.utc
_NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def staleness_hours() -> int:
    return 48


@pytest.fixture
def now() -> datetime:
    """Fixed UTC datetime used as the reference point for staleness checks."""
    return _NOW


@pytest.fixture
def make_review_event():
    """Factory fixture: make_review_event(state, hours_ago) -> ReviewEvent."""

    def _factory(state: str, hours_ago: int = 1) -> ReviewEvent:
        return ReviewEvent(
            reviewer="reviewer",
            state=state,
            submitted_at=_NOW - timedelta(hours=hours_ago),
        )

    return _factory


@pytest.fixture
def make_pull_request():
    """Factory fixture: make_pull_request(reviews, hours_since_activity, draft=False) -> PullRequest."""

    def _factory(
        reviews: list[ReviewEvent] | None = None,
        hours_since_activity: int = 1,
        draft: bool = False,
    ) -> PullRequest:
        # draft=False enforced: draft PRs are excluded before reaching any classifier logic
        if draft:
            raise ValueError(
                "Draft PRs must not be passed to the classifier; filter them at fetch time (FR-011)."
            )
        return PullRequest(
            repo="owner/repo",
            number=1,
            title="Test PR",
            author="dev",
            url="https://github.com/owner/repo/pull/1",
            last_activity_at=_NOW - timedelta(hours=hours_since_activity),
            reviews=reviews or [],
        )

    return _factory
