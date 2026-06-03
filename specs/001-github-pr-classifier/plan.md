# Implementation Plan: GitHub PR Classifier

**Branch**: `001-github-pr-classifier` | **Date**: 2026-06-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-github-pr-classifier/spec.md`

---

## Summary

Retrieve all open, non-draft pull requests from one or more GitHub repositories and
classify each into exactly one of four states (Changes Requested → Approved →
Waiting for Review → Stale) using PyGithub 2.9.x. Delivered as a Python
`src`-layout library (`pr_classifier`) with a thin `typer` CLI wrapper
(`pr-classifier`) that serialises a `ClassificationReport` to JSON on stdout.

---

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**:
- `PyGithub ~= 2.9` — GitHub REST API client with automatic pagination
- `typer ~= 0.12` — thin CLI wrapper (argument parsing, help generation, exit codes)

**Storage**: N/A — stateless; no persistence required

**Testing**: `pytest`, `pytest-mock`

**Target Platform**: macOS / Linux terminal and CI environments

**Project Type**: library + CLI tool (src-layout Python package)

**Performance Goals**: No hard target; must complete within a reasonable time for
stand-up use (SC-002 / SC-004 are the binding success criteria)

**Constraints**: Stateless; no credential storage; GitHub.com only (no GHES)

**Scale/Scope**: Up to ~10 repositories, up to ~100 open PRs each, in a single
invocation

---

## Constitution Check

*GATE: Evaluated pre-design (Phase 0) and re-evaluated post-design (Phase 1).*

### Pre-design evaluation

- [x] **Spec-first evidence**: `spec.md` contains one prioritized user story (P1
  MVP), measurable success criteria (SC-002, SC-004), and explicit assumptions.
- [x] **Incremental delivery**: single user story = MVP; no subsequent stories to
  sequence. Plan preserves the single independently testable slice.
- [x] **Verifiable quality**: classification logic is fully unit-testable against
  known review-event fixtures; acceptance scenarios map 1:1 to unit test cases;
  CLI integration tested via subprocess.
- [x] **Hook compliance**: `before_specify` (`speckit.git.feature`) executed —
  branch `001-github-pr-classifier` created. Optional `after_specify` hooks
  (`speckit.git.commit`, `speckit.agent-context.update`) offered to user.
  `before_plan` optional hook (`speckit.git.commit`) offered. No mandatory hooks
  are outstanding.
- [x] **Simplicity and traceability**: single-library, single-CLI package. No
  database, no server, no background workers. Every module maps directly to a
  spec entity or contract. The `_cli/` layer is justified by FR-009/FR-010
  (library-first constraint).

### Post-design re-evaluation

All gates remain passing. No violations introduced during Phase 1 design:
- Data model is minimal (5 dataclasses + 1 enum); no unnecessary abstractions.
- Contract defines a single public function and three output types.
- No new external dependencies introduced beyond those listed above.

---

## Project Structure

### Documentation (this feature)

```text
specs/001-github-pr-classifier/
├── plan.md              # This file
├── research.md          # Phase 0 — technology decisions
├── data-model.md        # Phase 1 — entities and classification state machine
├── quickstart.md        # Phase 1 — install and usage guide
├── contracts/
│   ├── library-api.md   # Phase 1 — Python library public API contract
│   ├── cli-schema.md    # Phase 1 — CLI argument and exit-code contract
│   └── output-schema.md # Phase 1 — JSON output schema and example
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── pr_classifier/
    ├── __init__.py          # Public API: exports classify_repositories + dataclasses
    ├── _classifier.py       # Classification logic (pure functions, no I/O)
    ├── _fetcher.py          # GitHub API calls via PyGithub
    ├── _models.py           # Dataclasses: PullRequest, ReviewEvent, ClassifiedPR,
    │                        #   RepositoryResult, ClassificationReport, ClassificationState
    ├── _exceptions.py       # AuthenticationError, PartialResultError
    └── _cli/
        ├── __init__.py
        └── main.py          # typer app — argument parsing, exit codes, JSON output only

tests/
├── unit/
│   ├── test_classifier.py   # Pure classification logic; no network
│   ├── test_fetcher.py      # PyGithub calls mocked via pytest-mock
│   └── test_models.py       # Dataclass validation and invariants
└── integration/
    └── test_cli.py          # subprocess.run against installed pr-classifier entry point

pyproject.toml               # Package metadata, [project.scripts], dependencies
```

**Structure Decision**: `src`-layout (PyPA recommendation). Prevents accidental
import of un-installed source during development. Private submodules (`_classifier`,
`_fetcher`, `_models`, `_exceptions`, `_cli`) are internal; only symbols re-exported
from `__init__.py` are part of the public contract. The `_cli/` subpackage is
isolated so it can be tested independently and contains zero business logic.
| [e.g., 4th project] | [current need] | [why 3 projects insufficient] |
| [e.g., Repository pattern] | [specific problem] | [why direct DB access insufficient] |
