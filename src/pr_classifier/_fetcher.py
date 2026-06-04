from __future__ import annotations

from datetime import datetime, timezone

from github import Auth, Github, GithubException
from github.PullRequest import PullRequest as GithubPullRequest

from pr_classifier._classifier import classify_pr
from pr_classifier._exceptions import AuthenticationError
from pr_classifier._models import ClassifiedPR, PullRequest, RepositoryResult, ReviewEvent

_IGNORED_REVIEW_STATES = {"PENDING"}


def authenticate(token: str) -> Github:
    """Create and verify a Github client using a personal access token.

    Raises
    ------
    AuthenticationError
        If the token is invalid, expired, or missing.
    """
    github = Github(auth=Auth.Token(token))
    try:
        github.get_user().login
    except GithubException as exc:
        if exc.status in {401, 403}:
            raise AuthenticationError(
                f"GitHub authentication failed (HTTP {exc.status})."
            ) from exc
        raise
    return github


def fetch_repository(
    github: Github,
    repo_id: str,
    staleness_hours: int,
) -> RepositoryResult:
    """Fetch all open, non-draft PRs for a single repository and classify them.

    Returns a RepositoryResult with classified PRs on success, or with
    `error` set and an empty `prs` list if the repository is inaccessible.
    """
    now = datetime.now(tz=timezone.utc)
    try:
        repo = github.get_repo(repo_id)
        raw_prs = repo.get_pulls(state="open")
    except GithubException as exc:
        return RepositoryResult(repo=repo_id, prs=[], error=str(exc))

    classified: list[ClassifiedPR] = []
    for raw_pr in raw_prs:
        if raw_pr.draft:
            continue

        reviews = _map_reviews(raw_pr)
        pr = PullRequest(
            repo=repo_id,
            number=raw_pr.number,
            title=raw_pr.title,
            author=raw_pr.user.login,
            url=raw_pr.html_url,
            last_activity_at=_ensure_utc(raw_pr.updated_at),
            reviews=reviews,
        )
        state = classify_pr(pr, staleness_hours=staleness_hours, now=now)
        classified.append(
            ClassifiedPR(
                repo=pr.repo,
                number=pr.number,
                title=pr.title,
                author=pr.author,
                url=pr.url,
                last_activity_at=pr.last_activity_at,
                reviews=pr.reviews,
                state=state,
            )
        )

    return RepositoryResult(repo=repo_id, prs=classified, error=None)


def _map_reviews(raw_pr: GithubPullRequest) -> list[ReviewEvent]:
    """Map raw PyGithub review objects to ReviewEvent, filtering PENDING."""
    events: list[ReviewEvent] = []
    for rv in raw_pr.get_reviews():
        if rv.state in _IGNORED_REVIEW_STATES:
            continue
        events.append(
            ReviewEvent(
                reviewer=rv.user.login,
                state=rv.state,
                submitted_at=_ensure_utc(rv.submitted_at),
            )
        )
    return events


def _ensure_utc(dt: datetime) -> datetime:
    """Return a timezone-aware UTC datetime, attaching UTC if naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt
