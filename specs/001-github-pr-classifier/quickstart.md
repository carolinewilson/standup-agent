# Quickstart: GitHub PR Classifier

**Date**: 2026-06-03

---

## Prerequisites

- Python 3.11 or later
- A GitHub personal access token with `repo` scope (read access to target
  repositories)

---

## Install

```bash
# From repository root
pip install -e .
```

---

## Configure authentication

```bash
export GITHUB_TOKEN=ghp_your_token_here
```

Or pass the token explicitly via `--token`.

---

## Classify PRs across repositories

```bash
pr-classifier my-org/backend my-org/frontend
```

The tool writes a JSON report to stdout:

```json
{
  "generated_at": "2026-06-03T09:00:00Z",
  "staleness_threshold_hours": 48,
  "counts": { "changes_requested": 2, "approved": 0, "waiting_for_review": 3, "stale": 1 },
  "repositories": [ ... ]
}
```

---

## Adjust staleness threshold

Default is 48 hours. Override per invocation:

```bash
pr-classifier --staleness-hours 24 my-org/backend
```

---

## Use as a library

```python
from pr_classifier import classify_repositories

report = classify_repositories(
    repos=["my-org/backend", "my-org/frontend"],
    token="ghp_your_token_here",
    staleness_hours=48,
)

for repo_result in report.repositories:
    if repo_result.error:
        print(f"{repo_result.repo}: ERROR — {repo_result.error}")
        continue
    for pr in repo_result.prs:
        print(f"[{pr.state.value}] #{pr.number} {pr.title} (@{pr.author})")
```

---

## Pipe to jq

```bash
# Show only counts
pr-classifier my-org/backend | jq .counts

# Show PRs waiting for review
pr-classifier my-org/backend | jq '[.repositories[].prs[] | select(.state == "waiting_for_review")]'
```

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | All repositories processed successfully |
| `1` | Authentication failed |
| `2` | Input validation error |
| `3` | Partial results (some repositories inaccessible — JSON still emitted) |

---

## Run tests

```bash
pytest tests/
```
