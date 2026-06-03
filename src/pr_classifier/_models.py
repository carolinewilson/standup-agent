from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ClassificationState(str, Enum):
    CHANGES_REQUESTED = "changes_requested"
    STALE = "stale"
    APPROVED = "approved"
    WAITING_FOR_REVIEW = "waiting_for_review"


@dataclass
class ReviewEvent:
    reviewer: str
    state: str  # "APPROVED", "CHANGES_REQUESTED", or "COMMENTED"
    submitted_at: datetime  # must be timezone-aware (UTC)

    def __post_init__(self) -> None:
        if self.state not in {"APPROVED", "CHANGES_REQUESTED", "COMMENTED"}:
            raise ValueError(
                f"ReviewEvent.state must be APPROVED, CHANGES_REQUESTED, or COMMENTED; got {self.state!r}"
            )
        if self.submitted_at.tzinfo is None:
            raise ValueError("ReviewEvent.submitted_at must be timezone-aware (UTC)")


@dataclass
class PullRequest:
    repo: str
    number: int
    title: str
    author: str
    url: str
    last_activity_at: datetime  # must be timezone-aware (UTC)
    reviews: list[ReviewEvent] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.number <= 0:
            raise ValueError(f"PullRequest.number must be a positive integer; got {self.number!r}")
        if self.last_activity_at.tzinfo is None:
            raise ValueError("PullRequest.last_activity_at must be timezone-aware (UTC)")


@dataclass
class ClassifiedPR:
    repo: str
    number: int
    title: str
    author: str
    url: str
    last_activity_at: datetime  # must be timezone-aware (UTC)
    reviews: list[ReviewEvent]
    state: ClassificationState


@dataclass
class RepositoryResult:
    repo: str
    prs: list[ClassifiedPR] = field(default_factory=list)
    error: Optional[str] = None

    def __post_init__(self) -> None:
        if self.error is not None and self.prs:
            raise ValueError("RepositoryResult.prs must be empty when error is set")


@dataclass
class ClassificationReport:
    repositories: list[RepositoryResult]
    generated_at: datetime  # must be timezone-aware (UTC)
    staleness_threshold_hours: int
    counts: dict[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.generated_at.tzinfo is None:
            raise ValueError("ClassificationReport.generated_at must be timezone-aware (UTC)")
        if self.staleness_threshold_hours <= 0:
            raise ValueError(
                f"ClassificationReport.staleness_threshold_hours must be a positive integer; got {self.staleness_threshold_hours!r}"
            )
