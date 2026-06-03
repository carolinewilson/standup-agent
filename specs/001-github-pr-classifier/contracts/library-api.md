# Contract: Library Public API

**Interface type**: Python importable library  
**Package**: `pr_classifier` (installed via `pip install .`)  
**Date**: 2026-06-03

---

## Public Entry Point

```python
from pr_classifier import classify_repositories
```

---

## `classify_repositories`

The single primary function exposed by the library.

```python
def classify_repositories(
    repos: list[str],
    token: str,
    staleness_hours: int = 48,
) -> ClassificationReport:
    ...
```

### Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `repos` | `list[str]` | Yes | Non-empty list of `owner/repo` identifiers |
| `token` | `str` | Yes | GitHub personal access token |
| `staleness_hours` | `int` | No | Inactivity threshold for Stale classification (default `48`) |

### Return value

Returns a `ClassificationReport` (see data-model.md). Never returns `None`.

### Exceptions

| Exception | Raised when |
|-----------|-------------|
| `ValueError` | `repos` is empty, or `staleness_hours` is not a positive integer |
| `AuthenticationError` | `token` is missing, invalid, or expired |
| `PartialResultError` | One or more repositories were inaccessible; the exception carries a `ClassificationReport` with partial results and per-repo errors |

`PartialResultError` is a subclass of `Exception` and exposes a `.report`
attribute containing the partial `ClassificationReport`. Callers that want partial
results on failure should catch `PartialResultError`.

### Behaviour contract

1. `repos` is validated before any network call; `ValueError` is raised immediately
   if it is empty.
2. Authentication is verified before fetching any repository; `AuthenticationError`
   is raised immediately if credentials are invalid.
3. Draft pull requests are excluded and never appear in the returned report.
4. Each open, non-draft PR appears in exactly one classification bucket.
5. The returned `ClassificationReport.counts` sums correctly to the total number of
   classified PRs.
6. The function is stateless and thread-safe; callers may invoke it concurrently.

---

## `ClassificationReport` (dataclass)

```python
@dataclass
class ClassificationReport:
    repositories: list[RepositoryResult]
    generated_at: datetime          # UTC, timezone-aware
    staleness_threshold_hours: int
    counts: dict[str, int]          # keys: see ClassificationState slugs
```

## `RepositoryResult` (dataclass)

```python
@dataclass
class RepositoryResult:
    repo: str
    prs: list[ClassifiedPR]
    error: str | None
```

## `ClassifiedPR` (dataclass)

```python
@dataclass
class ClassifiedPR:
    repo: str
    number: int
    title: str
    author: str
    url: str
    last_activity_at: datetime      # UTC, timezone-aware
    reviews: list[ReviewEvent]
    state: ClassificationState
```

## `ClassificationState` (enum)

```python
class ClassificationState(str, Enum):
    CHANGES_REQUESTED = "changes_requested"
    STALE             = "stale"
    APPROVED          = "approved"
    WAITING_FOR_REVIEW = "waiting_for_review"
```

---

## Stability guarantee

All symbols listed above are part of the public API and must not be removed or
renamed in a patch or minor release. Internal symbols (prefixed with `_`) are
not part of this contract.
