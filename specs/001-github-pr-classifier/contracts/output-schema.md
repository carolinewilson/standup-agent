# Contract: JSON Output Schema

**Interface type**: JSON output written to stdout  
**Date**: 2026-06-03

---

## Top-level structure

```json
{
  "generated_at": "<ISO 8601 UTC datetime>",
  "staleness_threshold_hours": 48,
  "counts": {
    "changes_requested": 2,
    "approved": 1,
    "waiting_for_review": 3,
    "stale": 1
  },
  "repositories": [ ... ]
}
```

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `generated_at` | `string` (ISO 8601, UTC) | When the report was generated, e.g. `"2026-06-03T09:00:00Z"` |
| `staleness_threshold_hours` | `integer` | Threshold used for stale classification |
| `counts` | `object` | Aggregate PR counts per bucket across all repositories |
| `repositories` | `array` | Per-repository results (see below) |

---

## `repositories[]` — RepositoryResult

```json
{
  "repo": "my-org/backend",
  "error": null,
  "prs": [ ... ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `repo` | `string` | Repository in `owner/repo` format |
| `error` | `string \| null` | Error message if inaccessible; `null` on success |
| `prs` | `array` | Classified PRs; empty array when `error` is set |

---

## `prs[]` — ClassifiedPR

```json
{
  "number": 42,
  "title": "Add rate limiting to API gateway",
  "author": "jsmith",
  "url": "https://github.com/my-org/backend/pull/42",
  "last_activity_at": "2026-06-01T14:23:00Z",
  "state": "changes_requested"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `number` | `integer` | PR number |
| `title` | `string` | PR title |
| `author` | `string` | GitHub login of PR author |
| `url` | `string` | Full HTML URL |
| `last_activity_at` | `string` (ISO 8601, UTC) | Last activity timestamp |
| `state` | `string` (enum) | One of `changes_requested`, `approved`, `waiting_for_review`, `stale` |

---

## Complete example

```json
{
  "generated_at": "2026-06-03T09:00:00Z",
  "staleness_threshold_hours": 48,
  "counts": {
    "changes_requested": 1,
    "approved": 0,
    "waiting_for_review": 1,
    "stale": 1
  },
  "repositories": [
    {
      "repo": "my-org/backend",
      "error": null,
      "prs": [
        {
          "number": 42,
          "title": "Add rate limiting",
          "author": "jsmith",
          "url": "https://github.com/my-org/backend/pull/42",
          "last_activity_at": "2026-06-01T14:23:00Z",
          "state": "changes_requested"
        },
        {
          "number": 39,
          "title": "Update dependencies",
          "author": "alee",
          "url": "https://github.com/my-org/backend/pull/39",
          "last_activity_at": "2026-05-30T08:00:00Z",
          "state": "stale"
        }
      ]
    },
    {
      "repo": "my-org/frontend",
      "error": null,
      "prs": [
        {
          "number": 11,
          "title": "Dark mode toggle",
          "author": "bchen",
          "url": "https://github.com/my-org/frontend/pull/11",
          "last_activity_at": "2026-06-03T07:00:00Z",
          "state": "waiting_for_review"
        }
      ]
    },
    {
      "repo": "my-org/archived-service",
      "error": "Repository not found or access denied",
      "prs": []
    }
  ]
}
```

---

## Schema invariants

1. The four keys in `counts` are always present, even when a count is `0`.
2. `prs` is always an array (never `null`); it is empty when `error` is set.
3. `state` is always one of the four defined enum values.
4. All datetime strings are UTC and include a `Z` suffix.
5. The sum of all `counts` values equals the total number of PR objects across all
   `prs` arrays.
