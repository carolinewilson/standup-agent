---
description: "Task list for GitHub PR Classifier implementation"
---

# Tasks: GitHub PR Classifier

**Input**: Design documents from `specs/001-github-pr-classifier/`

**Prerequisites**: plan.md ✅ | spec.md ✅ | research.md ✅ | data-model.md ✅ | contracts/ ✅ | quickstart.md ✅

**Tests**: Included for all behavior-changing work (classification logic, fetcher, CLI wiring) per constitution principle III.

**Organization**: Single user story (P1 MVP). All work maps to US1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[US1]**: Maps to User Story 1 (the only story — full MVP)

---

## Phase 1: Setup

**Purpose**: Project scaffolding and package initialization.

- [x] T001 Create `src/pr_classifier/` and `src/pr_classifier/_cli/` directories
- [x] T002 Create `tests/unit/` and `tests/integration/` directories
- [x] T003 Create `pyproject.toml` with package metadata, `[project.scripts]` entry point `pr-classifier = "pr_classifier._cli.main:app"`, and dependencies: `PyGithub~=2.9`, `typer~=0.12`; dev deps: `pytest`, `pytest-mock`
- [x] T004 [P] Create `src/pr_classifier/__init__.py` exporting `classify_repositories`, `ClassificationReport`, `RepositoryResult`, `ClassifiedPR`, `ClassificationState`, `AuthenticationError`, `PartialResultError`
- [x] T005 [P] Create `src/pr_classifier/_cli/__init__.py` (empty)

**Checkpoint**: `pip install -e .` succeeds; `pr-classifier --help` is callable

---

## Phase 2: Foundational

**Purpose**: Models, exceptions, and package skeleton that all other modules depend on. Must be complete before any library or CLI logic.

- [x] T006 Create `src/pr_classifier/_models.py` with `ClassificationState` enum (`changes_requested`, `approved`, `waiting_for_review`, `stale`), `ReviewEvent` dataclass (fields: `reviewer: str`, `state: str`, `submitted_at: datetime`), `PullRequest` dataclass (fields: `repo`, `number`, `title`, `author`, `url`, `last_activity_at`, `reviews`), `ClassifiedPR` dataclass (all `PullRequest` fields + `state: ClassificationState`), `RepositoryResult` dataclass (`repo`, `prs`, `error`), `ClassificationReport` dataclass (`repositories`, `generated_at`, `staleness_threshold_hours`, `counts`) per `specs/001-github-pr-classifier/data-model.md`
- [x] T007 [P] Create `src/pr_classifier/_exceptions.py` with `AuthenticationError(Exception)` and `PartialResultError(Exception)` carrying a `.report: ClassificationReport` attribute per `specs/001-github-pr-classifier/contracts/library-api.md`
- [x] T008 [P] Create `tests/unit/test_models.py` — write tests that FAIL before T006: validate `ClassificationState` has exactly 4 members; `RepositoryResult.error=None` when `prs` is populated; `RepositoryResult.prs=[]` when `error` is set; `ClassificationReport.counts` keys match enum slugs

**Checkpoint**: `pytest tests/unit/test_models.py` — tests fail (T006 not yet implemented)

After T006: `pytest tests/unit/test_models.py` — all pass

---

## Phase 3: User Story 1 – Retrieve and Classify PRs (Priority: P1) 🎯 MVP

**Goal**: Library function `classify_repositories(repos, token, staleness_hours=48)` fetches open non-draft PRs, classifies each into exactly one of four states, and returns a `ClassificationReport`. CLI wrapper serialises it to JSON on stdout with correct exit codes.

**Independent Test**: `pytest tests/` passes; `pr-classifier --help` works; running against real or mocked repos returns valid JSON with four bucket keys and no duplicate PRs.

### Tests for User Story 1 (behavior-changing)

- [x] T009 [P] [US1] Create `tests/unit/test_classifier.py` — write tests that FAIL before T013:
  - `test_changes_requested_wins_over_approval`: PR with one CHANGES_REQUESTED and one subsequent APPROVED → `changes_requested`
  - `test_approved_no_changes`: PR with one APPROVED, no CHANGES_REQUESTED, activity within 48 h → `approved`
  - `test_approved_stale`: PR with one APPROVED, no CHANGES_REQUESTED, last activity > 48 h ago → `stale`
  - `test_waiting_for_review`: PR with no reviews, activity within 48 h → `waiting_for_review`
  - `test_waiting_stale`: PR with no reviews, last activity > 48 h ago → `stale`
  - `test_draft_excluded`: draft PR never reaches classifier (confirmed by fetcher contract)
  - `test_counts_sum`: `ClassificationReport.counts` values sum to total PR count
  - `test_empty_repo`: repo with no open PRs → `RepositoryResult.prs == []`, `error is None`

- [x] T010 [P] [US1] Create `tests/unit/test_fetcher.py` — write tests that FAIL before T014 (mock PyGithub via `pytest-mock`):
  - `test_fetch_open_prs_excludes_drafts`: `get_pulls(state="open")` result containing one draft and one non-draft → only non-draft returned
  - `test_fetch_reviews_maps_state`: raw PyGithub review objects correctly mapped to `ReviewEvent`
  - `test_invalid_token_raises_auth_error`: PyGithub raises `GithubException(401)` → `AuthenticationError` raised
  - `test_inaccessible_repo_returns_error`: PyGithub raises `GithubException(404)` → `RepositoryResult.error` set, processing continues

- [x] T011 [P] [US1] Create `tests/integration/test_cli.py` — write tests that FAIL before T016 using Typer `CliRunner`:
  - `test_cli_valid_output_shape`: verify stdout is valid JSON with keys `generated_at`, `staleness_threshold_hours`, `counts`, `repositories`
  - `test_cli_exit_0_on_success`: exit code is 0
  - `test_cli_exit_1_on_auth_error`: `AuthenticationError` from library → exit 1, nothing on stdout
  - `test_cli_exit_2_on_empty_repos`: no REPOS argument → exit 2
  - `test_cli_exit_3_on_partial`: `PartialResultError` from library → exit 3, JSON still on stdout


### Implementation for User Story 1

- [x] T012 [P] [US1] Create `tests/unit/conftest.py` with shared pytest fixtures: `make_review_event(state, hours_ago)`, `make_pull_request(reviews, hours_since_activity, draft=False)`, `staleness_hours=48`

- [x] T013 [US1] Create `src/pr_classifier/_classifier.py` with:
  - `classify_pr(pr: PullRequest, staleness_hours: int, now: datetime) -> ClassificationState` — pure function implementing precedence: Changes Requested → Stale → Approved → Waiting for Review
  - `build_report(repo_results: list[RepositoryResult], staleness_hours: int) -> ClassificationReport` — computes `counts`, `generated_at`, assembles `ClassificationReport`
  (depends on T006, T007)

- [x] T014 [US1] Create `src/pr_classifier/_fetcher.py` with:
  - `fetch_repository(github: Github, repo_id: str, staleness_hours: int) -> RepositoryResult` — calls `github.get_repo(repo_id).get_pulls(state="open")`, filters drafts, maps to `PullRequest` + `ReviewEvent`, calls `classify_pr`, handles `GithubException(404/403)` → `RepositoryResult.error`
  - `authenticate(token: str) -> Github` — creates `Github(auth=Auth.Token(token))`, verifies credentials via `github.get_user().login`, raises `AuthenticationError` on `GithubException(401)`
  (depends on T006, T007, T013)

- [x] T015 [US1] Update `src/pr_classifier/__init__.py` with `classify_repositories(repos, token, staleness_hours=48) -> ClassificationReport` — validates inputs, calls `authenticate`, iterates repos via `fetch_repository`, raises `PartialResultError` if any repo errored, otherwise returns `build_report` result per `specs/001-github-pr-classifier/contracts/library-api.md`
  (depends on T004, T013, T014)

- [ ] T016 [US1] Create `src/pr_classifier/_cli/main.py` — `typer` app with command `classify(repos: list[str], token: Optional[str], staleness_hours: int = 48)`: reads token from `--token` or `GITHUB_TOKEN` env var; calls `classify_repositories`; serialises `ClassificationReport` to JSON on stdout; maps `ValueError` → exit 2, `AuthenticationError` → exit 1, `PartialResultError` → exit 3 (still writes `.report` JSON to stdout); no business logic per FR-010 and `specs/001-github-pr-classifier/contracts/cli-schema.md`
  (depends on T015)

**Checkpoint**: `pytest tests/` — all tests pass. Run quickstart scenario from `specs/001-github-pr-classifier/quickstart.md` to validate end-to-end.

---

## Phase 4: Polish & Cross-Cutting Concerns

**Purpose**: Package completeness, documentation, and final validation.

- [ ] T017 [P] Create `README.md` at repository root covering: install, `GITHUB_TOKEN` setup, CLI usage examples from `specs/001-github-pr-classifier/quickstart.md`, library import example
- [ ] T018 [P] Create `.gitignore` entries for `__pycache__/`, `*.pyc`, `.venv/`, `dist/`, `*.egg-info/` (extends existing `.gitignore`)
- [ ] T019 Run `pip install -e ".[dev]"` and `pytest tests/ -v` — confirm all tests pass and no warnings
- [ ] T020 Validate quickstart scenarios from `specs/001-github-pr-classifier/quickstart.md` against the installed package: `pr-classifier --help`, JSON output shape, exit code table
- [ ] T021 Run `pr-classifier --help` as a subprocess against the installed entry point and confirm exit code 0
``

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all US1 work
- **User Story 1 (Phase 3)**: Depends on Phase 2 completion
  - Tests (T009–T011) and conftest (T012) can be written in parallel immediately after Phase 2
  - T013 (`_classifier.py`) must precede T014 (`_fetcher.py`)
  - T014 must precede T015 (`__init__.py`)
  - T015 must precede T016 (`_cli/main.py`)
- **Polish (Phase 4)**: Depends on Phase 3 completion

### Within User Story 1

- T009, T010, T011, T012 are all [P] — write all four in parallel as soon as Phase 2 is done; all will FAIL until their respective implementation tasks complete
- T013 → T014 → T015 → T016 (strict sequential — each depends on the prior)
- After T013: `pytest tests/unit/test_classifier.py` must pass before proceeding to T014
- After T014: `pytest tests/unit/test_fetcher.py` must pass before proceeding to T015
- After T016: `pytest tests/integration/test_cli.py` must pass

### Parallel Opportunities

```bash
# Phase 2 — run in parallel:
Task T006: _models.py
Task T007: _exceptions.py
Task T008: test_models.py (write failing tests)

# Phase 3 — run in parallel after Phase 2:
Task T009: test_classifier.py (failing)
Task T010: test_fetcher.py (failing)
Task T011: test_cli.py (failing)
Task T012: conftest.py

# Then sequential:
T013 → pytest unit/test_classifier.py ✅ → T014 → pytest unit/test_fetcher.py ✅ → T015 → T016 → pytest all ✅
```

---

## Implementation Strategy

### MVP (User Story 1 Only)

1. Complete Phase 1: Setup — package installs, entry point callable
2. Complete Phase 2: Foundational — models and exceptions in place; model tests fail then pass
3. Write all Phase 3 tests in parallel (T009–T012) — all fail
4. Implement T013 → verify `test_classifier.py` passes
5. Implement T014 → verify `test_fetcher.py` passes
6. Implement T015 → wire library entry point
7. Implement T016 → verify `test_cli.py` passes
8. **STOP and VALIDATE**: run full `pytest tests/ -v`, run quickstart scenarios
9. Complete Phase 4: Polish

---

## Notes

- All `[P]` tasks operate on different files with no shared dependencies
- Tests MUST be written before implementation (constitution principle III)
- The classifier (`_classifier.py`) takes a `now: datetime` parameter to enable deterministic time-based testing without mocking `datetime.now()`
- Exit code 3 (partial results) still writes JSON to stdout — CLI must handle `PartialResultError.report` correctly
- Verify tests fail BEFORE each implementation task; verify they pass AFTER
