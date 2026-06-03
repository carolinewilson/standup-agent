# Data Model: GitHub PR Classifier

**Phase 1 output** | **Date**: 2026-06-03

---

## Entities

### ClassificationState (enum)

Represents the four mutually exclusive PR states. Applied in this precedence order:

| Order | State | Slug |
|-------|-------|------|
| 1 | Changes Requested | `changes_requested` |
| 2 | Stale | `stale` |
| 2 | Approved | `approved` |
| 4 | Waiting for Review | `waiting_for_review` |

**Classification rules**:
- `changes_requested`: at least one review with state `CHANGES_REQUESTED` exists;
  a later `APPROVED` review by a different reviewer does NOT override it.
- `stale`: the PR is not in `changes_requested` and `last_activity_at` is older
  than the configured staleness threshold (default 48 hours). This applies even if
  the PR would otherwise be `approved` or `waiting_for_review`.
- `approved`: at least one review with state `APPROVED`, no unresolved
  `CHANGES_REQUESTED` reviews, and not stale.
- `waiting_for_review`: open, non-draft, no reviews submitted, and not stale.

---

### ReviewEvent

A single review submission on a pull request.

| Field | Type | Description |
|-------|------|-------------|
| `reviewer` | `str` | GitHub login of the reviewer |
| `state` | `str` | `APPROVED`, `CHANGES_REQUESTED`, or `COMMENTED` |
| `submitted_at` | `datetime` | UTC timestamp of review submission |

**Validation rules**:
- `state` MUST be one of the three values above; `PENDING` reviews are ignored.
- `submitted_at` MUST be timezone-aware (UTC).

---

### PullRequest

A single open, non-draft GitHub pull request.

| Field | Type | Description |
|-------|------|-------------|
| `repo` | `str` | Repository in `owner/repo` format |
| `number` | `int` | PR number within the repository |
| `title` | `str` | PR title |
| `author` | `str` | GitHub login of the PR author |
| `url` | `str` | HTML URL of the PR |
| `last_activity_at` | `datetime` | UTC timestamp of last activity (`updated_at`) |
| `reviews` | `list[ReviewEvent]` | All non-pending review events, oldest first |

**Validation rules**:
- `number` MUST be a positive integer.
- `last_activity_at` MUST be timezone-aware (UTC).
- Draft PRs MUST NOT be represented; they are filtered at fetch time.

---

### ClassifiedPR

A `PullRequest` enriched with its resolved classification state.

| Field | Type | Description |
|-------|------|-------------|
| *(all PullRequest fields)* | | Inherited from PullRequest |
| `state` | `ClassificationState` | Resolved classification |

**Invariants**:
- `state` is derived deterministically from `reviews`, `last_activity_at`, and the
  staleness threshold; it is never set externally.

---

### RepositoryResult

Aggregated result for a single repository.

| Field | Type | Description |
|-------|------|-------------|
| `repo` | `str` | Repository in `owner/repo` format |
| `prs` | `list[ClassifiedPR]` | All classified open PRs (may be empty) |
| `error` | `str \| None` | Error message if repository was inaccessible; `None` on success |

**Validation rules**:
- If `error` is set, `prs` MUST be an empty list.
- If `error` is `None`, `prs` contains zero or more entries.

---

### ClassificationReport

Root output structure returned by the library and serialised to JSON by the CLI.

| Field | Type | Description |
|-------|------|-------------|
| `repositories` | `list[RepositoryResult]` | One entry per requested repository |
| `generated_at` | `datetime` | UTC timestamp when the report was produced |
| `staleness_threshold_hours` | `int` | Threshold used for stale classification |
| `counts` | `dict[str, int]` | Aggregate counts per bucket across all repos |

**`counts` keys**: `changes_requested`, `approved`, `waiting_for_review`, `stale`.

**Validation rules**:
- `generated_at` MUST be timezone-aware (UTC).
- `staleness_threshold_hours` MUST be a positive integer.
- Sum of `counts` values MUST equal total number of `ClassifiedPR` entries across
  all `RepositoryResult.prs` lists.

---

## State Transitions

```
Open PR fetched
      │
      ▼
  Draft? ──yes──► excluded (not represented)
      │
      no
      ▼
  Any CHANGES_REQUESTED review? ──yes──► changes_requested
      │
      no
      ▼
  last_activity > threshold? ──yes──► stale
      │
      no
      ▼
  Any APPROVED review? ──yes──► approved
      │
      no
      ▼
  waiting_for_review
```
