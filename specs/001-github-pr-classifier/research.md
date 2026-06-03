# Research: GitHub PR Classifier

**Phase 0 output for plan.md** | **Date**: 2026-06-03

---

## Decision 1: Programming Language

**Decision**: Python 3.11+

**Rationale**: The repository is named `standup-agent` inside a parent directory
`ai-agents`, strongly suggesting a Python AI/automation tooling context. Python is
the dominant language for GitHub API tooling and AI agent scaffolding. No existing
source files constrain the choice.

**Alternatives considered**:
- TypeScript/Node.js: viable but heavier for a CLI tool; less idiomatic for the
  AI agents context evident from the repo name.
- Go: excellent for CLI tools but the ecosystem has fewer GitHub API wrappers with
  the ergonomics required here.

---

## Decision 2: GitHub API Library

**Decision**: `PyGithub` 2.9.x (PyPI: `PyGithub`)

**Rationale**:
- Provides a Pythonic ORM-style interface for PRs and reviews (`repo.get_pulls()`,
  `pr.get_reviews()`).
- Built-in transparent pagination via `PaginatedList` — no manual `?page=` handling.
- PAT authentication via `Auth.Token("token")` in two lines.
- Actively maintained (v2.9.1 released April 2026, 7 700+ stars, 70 900+
  dependents).
- Works as a plain library module; no CLI context required.

**Alternatives considered**:
- `ghapi` 1.0.x: auto-generated from OpenAPI spec, always up to date, but smaller
  ecosystem (681 stars) and less intuitive review-state access.
- Direct `requests`/`httpx`: full control but requires manual pagination, retry
  logic, and rate-limit handling — disproportionate boilerplate for this scope.
- GitHub GraphQL via `gql` 4.x: efficient for complex nested queries but cursor-
  based pagination is more complex; overkill when REST covers the use case cleanly.

---

## Decision 3: Package Structure

**Decision**: `src`-layout, library-first, thin CLI via `typer`

**Rationale**:
- `src`-layout (PyPA recommended) prevents accidental import of un-installed source
  during development and enforces testing the installed package.
- Separates library public API (exported from `__init__.py`) from CLI concerns
  (isolated in `_cli/` private submodule).
- `typer` generates `--help` from type hints, minimises wrapper boilerplate, and
  keeps the CLI thin without sacrificing UX.
- Testing: `pytest` unit tests target library functions directly; integration tests
  invoke the CLI via `subprocess` to verify argument wiring end-to-end.

**Alternatives considered**:
- Flat layout: simpler but risks import confusion and is discouraged for
  distributable packages.
- `click` instead of `typer`: more mature plugin ecosystem but more verbose for a
  thin wrapper; `typer` is a strict superset for simple CLIs.
- `argparse`: zero extra dependency but verbose; ruled out in favour of `typer`
  which stays thin while improving DX.

---

## Decision 4: Staleness Detection Strategy

**Decision**: Compare PR `updated_at` timestamp against current UTC time minus the
configured threshold (default 48 hours). Stale applies only after Changes Requested
and Approved have already been ruled out (precedence order: Changes Requested →
Approved → Waiting for Review → Stale).

**Rationale**: `updated_at` on the GitHub PR object reflects the most recent
modification to the PR (commits, comments, reviews, label changes). This is the
single most reliable signal available without additional API calls and maps exactly
to the spec's definition of "no activity".

**Alternatives considered**:
- Fetching timeline events per PR: more precise but doubles API calls per PR.
- Using `pushed_at` on the head branch: only captures commits, not comments or
  reviews — would miss review activity.

---

## Decision 5: Testing Framework

**Decision**: `pytest` with `pytest-mock` for unit tests; `subprocess.run` for
CLI integration tests.

**Rationale**: `pytest` is the de facto standard for Python projects. `pytest-mock`
provides clean mock/patch support for isolating the GitHub API client in unit tests.
Subprocess CLI tests confirm the installed entry point wires arguments correctly
without duplicating business-logic tests.

**Alternatives considered**:
- `unittest`: built-in but verbose; `pytest` has better output and fixture support.
- `responses` or `pytest-responses` for HTTP mocking: useful but `pytest-mock`
  patching at the PyGithub object level is simpler for this project.
