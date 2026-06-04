"""Tests for src/pr_classifier/_fetcher.py (T010).

These tests FAIL before T014 — _fetcher.py does not exist yet.
All PyGithub objects are mocked via pytest-mock.
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from github import GithubException

# _fetcher is not yet implemented; import will fail until T014
from pr_classifier._fetcher import authenticate, fetch_repository
from pr_classifier._exceptions import AuthenticationError
from pr_classifier._models import ReviewEvent

UTC = timezone.utc
NOW = datetime(2026, 6, 3, 12, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Helpers — build lightweight PyGithub mock objects
# ---------------------------------------------------------------------------


def _mock_review(reviewer: str, state: str, submitted_at: datetime) -> MagicMock:
    rv = MagicMock()
    rv.user.login = reviewer
    rv.state = state
    rv.submitted_at = submitted_at
    return rv


def _mock_pr(
    number: int = 1,
    title: str = "Test PR",
    author: str = "dev",
    url: str = "https://github.com/owner/repo/pull/1",
    updated_at: datetime = NOW,
    draft: bool = False,
    reviews: list[MagicMock] | None = None,
) -> MagicMock:
    pr = MagicMock()
    pr.number = number
    pr.title = title
    pr.user.login = author
    pr.html_url = url
    pr.updated_at = updated_at
    pr.draft = draft
    pr.get_reviews.return_value = reviews or []
    return pr


# ---------------------------------------------------------------------------
# fetch_repository — draft filtering
# ---------------------------------------------------------------------------


def test_fetch_open_prs_excludes_drafts(mocker):
    """get_pulls(state='open') result with one draft and one non-draft → only non-draft returned."""
    draft_pr = _mock_pr(number=1, draft=True)
    real_pr = _mock_pr(number=2, draft=False)

    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [draft_pr, real_pr]

    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    result = fetch_repository(mock_github, "owner/repo", staleness_hours=48)

    assert result.error is None
    assert len(result.prs) == 1
    assert result.prs[0].number == 2


# ---------------------------------------------------------------------------
# fetch_repository — review mapping
# ---------------------------------------------------------------------------


def test_fetch_reviews_maps_state(mocker):
    """Raw PyGithub review objects are correctly mapped to ReviewEvent."""
    review = _mock_review("alice", "APPROVED", NOW)
    pr = _mock_pr(number=1, reviews=[review])

    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [pr]

    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    result = fetch_repository(mock_github, "owner/repo", staleness_hours=48)

    assert result.error is None
    assert len(result.prs) == 1
    classified = result.prs[0]
    assert len(classified.reviews) == 1
    rv = classified.reviews[0]
    assert isinstance(rv, ReviewEvent)
    assert rv.reviewer == "alice"
    assert rv.state == "APPROVED"
    assert rv.submitted_at == NOW


def test_fetch_reviews_filters_pending(mocker):
    """PENDING reviews are excluded from the mapped ReviewEvent list."""
    pending = _mock_review("bob", "PENDING", NOW)
    approved = _mock_review("alice", "APPROVED", NOW)
    pr = _mock_pr(number=1, reviews=[pending, approved])

    mock_repo = MagicMock()
    mock_repo.get_pulls.return_value = [pr]

    mock_github = MagicMock()
    mock_github.get_repo.return_value = mock_repo

    result = fetch_repository(mock_github, "owner/repo", staleness_hours=48)

    assert result.error is None
    reviews = result.prs[0].reviews
    assert all(rv.state != "PENDING" for rv in reviews)
    assert len(reviews) == 1


# ---------------------------------------------------------------------------
# fetch_repository — error handling
# ---------------------------------------------------------------------------


def test_inaccessible_repo_returns_error(mocker):
    """GithubException(404) → RepositoryResult.error set; processing continues (no exception raised)."""
    mock_github = MagicMock()
    mock_github.get_repo.side_effect = GithubException(404, "Not Found", None)

    result = fetch_repository(mock_github, "owner/missing", staleness_hours=48)

    assert result.error is not None
    assert result.prs == []
    assert result.repo == "owner/missing"


def test_forbidden_repo_returns_error(mocker):
    """GithubException(403) → RepositoryResult.error set; processing continues."""
    mock_github = MagicMock()
    mock_github.get_repo.side_effect = GithubException(403, "Forbidden", None)

    result = fetch_repository(mock_github, "owner/private", staleness_hours=48)

    assert result.error is not None
    assert result.prs == []


# ---------------------------------------------------------------------------
# authenticate
# ---------------------------------------------------------------------------


def test_invalid_token_raises_auth_error(mocker):
    """GithubException(401) during credential verification → AuthenticationError raised."""
    mock_github = mocker.patch("pr_classifier._fetcher.Github")
    instance = mock_github.return_value
    instance.get_user.return_value.login  # attribute access
    instance.get_user.side_effect = GithubException(401, "Bad credentials", None)

    with pytest.raises(AuthenticationError):
        authenticate("bad-token")


def test_forbidden_token_raises_auth_error(mocker):
    """GithubException(403) during credential verification → AuthenticationError raised."""
    mock_github = mocker.patch("pr_classifier._fetcher.Github")
    instance = mock_github.return_value
    instance.get_user.side_effect = GithubException(403, "Forbidden", None)

    with pytest.raises(AuthenticationError):
        authenticate("sso-unapproved-token")


def test_valid_token_returns_github_instance(mocker):
    """Valid token → returns a Github instance without raising."""
    mock_github = mocker.patch("pr_classifier._fetcher.Github")
    instance = mock_github.return_value
    instance.get_user.return_value.login = "carol"

    result = authenticate("valid-token")

    assert result is instance
