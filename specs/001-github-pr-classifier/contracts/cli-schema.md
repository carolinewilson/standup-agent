# Contract: CLI Interface

**Interface type**: Command-line tool (thin wrapper over library)  
**Entry point**: `pr-classifier` (installed via `pip install .`)  
**Date**: 2026-06-03

---

## Synopsis

```
pr-classifier [OPTIONS] REPOS...
```

---

## Arguments

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `REPOS` | `str` (variadic) | Yes | One or more repository identifiers in `owner/repo` format |

---

## Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--token TEXT` | `str` | `$GITHUB_TOKEN` env var | GitHub personal access token. If omitted, reads `GITHUB_TOKEN` from environment |
| `--staleness-hours INT` | `int` | `48` | Inactivity threshold in hours for Stale classification |
| `--help` | flag | — | Show usage and exit |

---

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Success — all repositories processed |
| `1` | Authentication error (invalid or missing token) |
| `2` | Input validation error (empty repo list, invalid format) |
| `3` | Partial results — one or more repositories inaccessible; JSON output still written to stdout with per-repo errors |

---

## Output

On success (`exit 0`) and partial success (`exit 3`): writes a JSON object to
**stdout** conforming to the output schema (see `output-schema.md`).

On authentication or validation errors (`exit 1`, `exit 2`): writes a plain-text
error message to **stderr**; nothing is written to stdout.

---

## Examples

```bash
# Classify PRs across two repositories
pr-classifier my-org/backend my-org/frontend

# Explicit token, custom staleness threshold
pr-classifier --token ghp_xxx --staleness-hours 24 my-org/backend

# Token from environment variable
export GITHUB_TOKEN=ghp_xxx
pr-classifier my-org/backend my-org/frontend | jq .counts
```

---

## Constraints

- The CLI MUST NOT perform classification, data-shaping, or review-state logic;
  it MUST delegate all such work to the library.
- Input parsing, exit-code mapping, and stdout/stderr routing are the only
  responsibilities of the CLI layer.
