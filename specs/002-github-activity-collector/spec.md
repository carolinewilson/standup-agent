# Feature Specification: GitHub Activity Collector

**Feature Branch**: `002-github-activity-collector`

**Created**: 2026-07-13

**Status**: Draft

**Input**: User description: "A config-driven tool that collects GitHub PR activity
across configured repositories since the last working day, classifying current PR
state and capturing movement, review wait times, and Jira ticket references. Produces
a structured JSON payload for downstream synthesis. Runs against personal repos
locally (Claude) and work repos in production (Power Automate / Copilot Studio).
Absorbs and extends the PR classifier library from 001."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 – Collect PR Activity Across Configured Repositories (Priority: P1)

A team lead runs the tool before a stand-up. The tool reads a config file specifying
repositories, a GitHub token, and a primary timezone. It fetches all open PRs across
those repositories — including drafts — and captures what has changed since the
lookback boundary.

**Lookback boundary algorithm:**
1. Set candidate to yesterday (the calendar day before the invocation date).
2. While candidate is not a working day (i.e. candidate is Saturday, Sunday, or in
   `bank_holidays`): decrement candidate by one calendar day.
3. The boundary is 00:00:00 on the final candidate in the primary timezone, converted
   to UTC.

There is no step limit. This single algorithm correctly handles Monday (steps back
over the weekend to Friday), post-holiday (steps back over the holiday and any
preceding weekend), and consecutive bank holidays (steps back until a working day
is found). No special-case rules are needed.

A working day is any day that is not Saturday, not Sunday, and not in `bank_holidays`.

**Authentication:**
The GitHub token is read from `GITHUB_TOKEN` environment variable if set to a
non-empty string, falling back to the `github_token` field in the config file.
The environment variable takes precedence. An empty string `GITHUB_TOKEN` is treated
as not set. The config field is optional when the env var is set.

**Movement events** captured since the boundary:
- `new_pr` — non-draft PR `created_at` >= boundary
- `new_draft_pr` — draft PR `created_at` >= boundary
- `pr_merged` — PR `merged_at` >= boundary
- `review_received` — PR had zero GitHub PR Review objects of any state (APPROVED,
  CHANGES_REQUESTED, COMMENTED, or DISMISSED) submitted before the boundary, and
  has at least one PR Review object submitted after the boundary. Plain issue
  comments do not qualify.
- `changes_addressed` — PR had at least one CHANGES_REQUESTED review submitted
  before the boundary AND `GET /repos/{owner}/{repo}/pulls/{number}/commits`
  contains at least one commit where `author.date` is after the boundary.
  `committer.date` is ignored. Force-pushed commits qualify if `author.date` is
  after the boundary.
- `pr_approved` — walk the PR's full review history chronologically. Find the
  earliest point after the boundary at which the aggregate state first became
  Approved: at least one APPROVED review AND no CHANGES_REQUESTED reviews that
  are not either superseded by a later APPROVED from the same reviewer or DISMISSED.
  DISMISSED CHANGES_REQUESTED reviews do not block Approved state. If that
  transition exists after the boundary and the PR was not already Approved before
  the boundary, emit `pr_approved` with the `submitted_at` of the review that
  caused the transition.
- `draft_converted_to_ready` — `GET /repos/{owner}/{repo}/issues/{number}/timeline`
  returns an event with `event: "ready_for_review"` and `created_at` after the
  boundary.

A PR that receives its first-ever review as an APPROVED review generates both
`review_received` and `pr_approved`. These are not mutually exclusive.

`movement_by_type` in `summary_counts` counts individual event emissions. A single
PR emitting two event types increments two separate counters each by one.

**Timestamp sources per event type:**
- `new_pr`, `new_draft_pr` → PR `created_at`
- `pr_merged` → PR `merged_at`
- `review_received` → `submitted_at` of the first qualifying review after boundary
- `changes_addressed` → `author.date` of the first qualifying commit after boundary
- `pr_approved` → `submitted_at` of the review that caused the Approved transition
- `draft_converted_to_ready` → `created_at` of the `ready_for_review` timeline event

**Output structure per repository (RepositorySnapshot):**
- `prs` — open, human-authored, non-draft PRs only
- `draft_prs` — open, human-authored, draft PRs only
- `recently_merged` — human-authored PRs where `merged_at >= boundary`, regardless
  of when they were opened
- `error` — error message if repository was inaccessible, null on success

**Automated PRs:**
Automated PRs (authored by configured `bot_accounts`) are not represented as
PRSnapshot objects. They are counted via a lightweight internal structure and
surfaced only in `automated_pr_counts`. They are excluded from `prs`, `draft_prs`,
`recently_merged`, and all `summary_counts` values. When `bot_accounts` is empty,
`automated_pr_counts` is `{}`.

For `automated_pr_counts`, automated open non-draft PRs are classified by state
using 001's logic for counting purposes only. The inner dict keys are:
`waiting_for_review`, `changes_requested`, `approved`, `stale`, `draft`.
All keys always present when a repo entry exists, zero when no automated PRs in
that state. `merged` is not included — merged automated PRs are not tracked.

**PR state classification errors:**
If the `pr_classifier` library raises an unexpected error for a specific PR, that
PR is included in the output with `current_state: "unknown"`. The error is not
propagated as a per-repo error. The PR is not omitted.

**Time metrics for recently_merged PRs:**
- `hours_open` = `(merged_at - created_at)` in hours
- `hours_since_activity` = `(now_utc - updated_at)` in hours
- `hours_waiting_for_review` = null (merged PRs are not waiting for review)

**Error handling and exit codes:**
- 0 — success; JSON payload written to stdout
- 1 — validation or config error (empty repositories, missing config file,
  missing token, invalid timezone string, malformed repo identifier)
- 2 — authentication failure (401); exits immediately, no output
- 3 — rate limit error; exits immediately, reset time to stderr

A 403 or 404 on a specific repository is a per-repo access error recorded in that
repository's `error` field; processing continues. Rate limit errors cause global
exit (exit code 3) since all subsequent calls would also fail.

**Config validation** (all performed before any API calls):
- `repositories` must be non-empty
- Each repository string must match `^[^/]+/[^/]+$`; invalid format → exit code 1
- Token must be available (env var or config field); absent → exit code 1
- `primary_timezone` must be a valid IANA timezone string; invalid → exit code 1
  with a message naming the invalid value

**Jira reference extraction:**
PR title is scanned first, then branch name. References combined and deduplicated
in order of first appearance across both sources.

The output is a structured JSON payload. All datetime fields are ISO 8601 strings
in UTC, suffixed with `Z` (e.g. `2026-07-11T09:00:00Z`).

**Why this priority**: This is the complete data collection layer. Without it the
synthesis layer has no input and the stand-up brief cannot be generated.

**Independent Test**: Point the tool at two or three repositories with known recent
PR activity using a test config; verify the output contains correct current state
classifications, that movement events since the lookback boundary are captured, that
events before the boundary are excluded, and that Jira references are extracted where
present.

**Acceptance Scenarios**:

1. Valid config → JSON payload, exit code 0.

2. Monday invocation, `Europe/London` → boundary is 00:00:00 Friday London time,
   UTC (candidate starts as Sunday, steps back to Saturday, steps back to Friday).

3. Wednesday invocation, no bank holidays → boundary is 00:00:00 Tuesday.

4. Wednesday invocation following Tuesday bank holiday → boundary is 00:00:00 Monday
   (Tuesday skipped).

5. Monday following Friday bank holiday → candidate starts Sunday, steps to
   Saturday, steps to Friday (bank holiday), steps to Thursday; boundary is
   00:00:00 Thursday.

6. Two consecutive bank holidays (Monday and Tuesday), Wednesday invocation →
   candidate starts Tuesday (bank holiday), steps to Monday (bank holiday),
   steps to Sunday (weekend), steps to Saturday (weekend), steps to Friday;
   boundary is 00:00:00 Friday.

7. `GITHUB_TOKEN` env var set (non-empty) AND `github_token` in config → env var
   takes precedence.

8. `GITHUB_TOKEN` set to empty string → treated as not set, falls back to config.

9. Repo identifier `not-a-valid-format` → exit code 1 before any API calls.

10. Invalid `primary_timezone: "Mars/Olympus"` → exit code 1 with message naming
    the invalid value.

11. PR with CHANGES_REQUESTED before boundary and commit (`author.date` after
    boundary) → `changes_addressed` event, regardless of current state.

12. PR whose first-ever review is APPROVED after boundary → both `review_received`
    and `pr_approved` emitted; both counters incremented in `movement_by_type`.

13. PR with DISMISSED CHANGES_REQUESTED and later APPROVED → aggregate state is
    Approved.

14. PR with DISMISSED review before boundary → counts as prior review;
    `review_received` NOT emitted.

15. PR title `"Fix PROJ-123"`, branch `"feature/PROJ-123-fix"` →
    `jira_references: ["PROJ-123"]` (deduplicated).

16. Inaccessible repo (403/404) → `error` set, processing continues, exit code 0.

17. 401 Unauthorized → exit code 2, no output.

18. Rate limit hit → exit code 3, reset time on stderr.

19. Draft PR opened since boundary → in `draft_prs`, `is_draft: true`, no
    `current_state`, `new_draft_pr` event.

20. PR opened Saturday, Monday invocation `Europe/London` → `new_pr` event
    (boundary is Friday).

21. `dependabot[bot]` PR (in `bot_accounts`) → excluded from all lists and
    `summary_counts`; counted in `automated_pr_counts`.

22. PR opened and merged within window → in `recently_merged`, both `new_pr`
    and `pr_merged` events; both counters incremented independently.

23. Repo with only automated PRs → `prs`, `draft_prs`, `recently_merged` empty;
    `error` null.

24. `bot_accounts` empty → `automated_pr_counts` is `{}`.

25. PR classifier raises unexpected error for one PR → PR in output with
    `current_state: "unknown"`; other PRs unaffected.

---

### Edge Cases

- 401 → exit code 2, no output.
- 403/404 per repo → `error` field, continue, exit code 0.
- Rate limit → exit code 3, global exit, reset time to stderr.
- Empty `repositories` → exit code 1, no API calls.
- Malformed repo string → exit code 1, no API calls.
- Invalid timezone → exit code 1, message naming the value.
- Missing token (no env var, no config field) → exit code 1.
- Empty string `GITHUB_TOKEN` → treated as not set, falls back to config.
- Empty `bank_holidays` → weekend-aware lookback only, no error.
- Same Jira ref in title and branch → deduplicated, appears once.
- Multiple Jira refs in title → all captured, title before branch.
- No `bot_accounts` → `automated_pr_counts` is `{}`.
- `recently_merged`: `hours_open = merged_at - created_at`,
  `hours_since_activity = now_utc - updated_at`.
- Automated draft PR → counted in `automated_pr_counts["draft"]` when that repo
  entry exists; not a PRSnapshot.
- Per-PR classifier error → `current_state: "unknown"`, PR included.
- `draft_converted_to_ready` not in REST timeline → event not emitted. Accepted.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: All configuration read from external config file. No hardcoding.
- **FR-002**: `--config` flag, defaulting to `config.yaml` in current directory.
- **FR-003**: Lookback boundary: set candidate to yesterday; while candidate is not
  a working day, decrement by one calendar day; boundary = 00:00:00 on candidate
  in primary timezone, converted to UTC. Working day = not Saturday, not Sunday,
  not in `bank_holidays`. No step limit.
- **FR-004**: Fetches all open PRs per repo including drafts.
- **FR-004a**: Draft PRs in `draft_prs`, `is_draft: true`, not classified.
  Automated draft PRs excluded from `draft_prs`, counted in
  `automated_pr_counts["draft"]` when that repo entry exists.
  `draft_converted_to_ready` detected via REST Timeline Events
  (`event: "ready_for_review"`, `created_at` after boundary).
- **FR-005**: Non-draft open PRs classified using `pr_classifier` (001). Per-PR
  classifier error → `current_state: "unknown"`, PR included. Not propagated as
  per-repo error.
- **FR-006**: Movement events detected per User Story 1. `review_received` and
  `pr_approved` not mutually exclusive. DISMISSED reviews count as prior reviews
  for `review_received`. DISMISSED CHANGES_REQUESTED does not block Approved state.
  `changes_addressed` uses `author.date`; `committer.date` ignored.
  `movement_by_type` counts individual emissions.
- **FR-007**: `hours_open` and `hours_since_activity` populated for all PRs in
  `prs`, `draft_prs`, and `recently_merged`. For `recently_merged`:
  `hours_open = (merged_at - created_at)`, `hours_since_activity = (now_utc -
  updated_at)`. For open PRs: both calculated from `now_utc`.
- **FR-008**: `hours_waiting_for_review` only for Waiting for Review state.
  Null for all other states, drafts, and merged PRs.
- **FR-009**: Jira refs via `[A-Z]+-\d+`. Title scanned first, then branch.
  Combined, deduplicated, order of first appearance. Absence = `[]`, never null.
  False positives accepted.
- **FR-010**: Per-repo 403/404 recorded as `error`; processing continues.
- **FR-011**: 401 → exit code 2, immediate exit, no output. 403/404 per repo →
  FR-010.
- **FR-012**: Rate limit → exit code 3, reset time to stderr, immediate global exit.
- **FR-013**: JSON to stdout. Exit codes: 0 success, 1 validation/config, 2 auth,
  3 rate limit. All datetimes ISO 8601 UTC with `Z`.
- **FR-014**: Core logic as reusable library.
- **FR-015**: CLI thin wrapper; no business logic.
- **FR-016**: `pr_classifier` (001) used for all state classification.
- **FR-017**: Optional `bot_accounts` list in config (default `[]`).
- **FR-018**: Automated PRs not represented as PRSnapshot. Counted in
  `automated_pr_counts` only. Excluded from all lists and `summary_counts`.
  When `bot_accounts` is empty, `automated_pr_counts` is `{}`.
- **FR-019**: Config validation before any API calls: non-empty `repositories`,
  valid `^[^/]+/[^/]+$` repo format, token present, valid IANA timezone.
  Failures → exit code 1 with descriptive message.

### Constitution Alignment *(mandatory)*

- User Story 1 is the complete MVP; independently testable.
- Success criteria measurable and technology-agnostic.
- Dependency on `pr_classifier` (001) explicit; logic not duplicated.
- Behaviour changes include fail-first validation.

### Key Entities

- **Config**: repositories (list[str], required), github_token (str, optional if
  `GITHUB_TOKEN` env var set), staleness_threshold_hours (int, default 48),
  bank_holidays (list[ISO date str], default []), bot_accounts (list[str],
  default []), primary_timezone (IANA str, default "UTC").
- **PRMovementEvent**: event_type (MovementEventType), pr_number (int), repository
  (str), timestamp (UTC datetime — source per event type in User Story 1).
- **MovementEventType** (enum): `new_pr`, `new_draft_pr`, `pr_merged`,
  `review_received`, `changes_addressed`, `pr_approved`, `draft_converted_to_ready`.
- **PRSnapshot**: repository (str), pr_number (int), title (str), author (str),
  url (str), is_draft (bool), current_state (str|null — null for drafts and merged
  PRs, `"unknown"` on classifier error), opened_at (UTC datetime), hours_open
  (float), hours_since_activity (float), hours_waiting_for_review (float|null),
  jira_references (list[str], never null), movement_events (list[PRMovementEvent]).
- **RepositorySnapshot**: repository (str), prs (list[PRSnapshot] — open,
  human-authored, non-draft), draft_prs (list[PRSnapshot] — open, human-authored,
  draft only), recently_merged (list[PRSnapshot] — `merged_at >= boundary`,
  human-authored), error (str|null).
- **ActivityPayload**: generated_at (UTC datetime), lookback_from (UTC datetime),
  staleness_threshold_hours (int), repositories (list[RepositorySnapshot]),
  summary_counts (dict), automated_pr_counts (dict[repo: dict[state: int]] or
  `{}` when `bot_accounts` is empty).

  `summary_counts` (all keys always present, zero when none; automated PRs excluded):
  ```json
  {
    "open_by_state": {
      "waiting_for_review": 0,
      "changes_requested": 0,
      "approved": 0,
      "stale": 0,
      "draft": 0
    },
    "movement_by_type": {
      "new_pr": 0,
      "new_draft_pr": 0,
      "pr_merged": 0,
      "review_received": 0,
      "changes_addressed": 0,
      "pr_approved": 0,
      "draft_converted_to_ready": 0
    }
  }
  ```
  `open_by_state.draft` = sum of `len(repo.draft_prs)` across all repos.
  `movement_by_type` counts individual event emissions; one PR emitting two event
  types increments two counters each by one.

  `automated_pr_counts` inner dict keys (all present when repo entry exists, zero
  when none): `waiting_for_review`, `changes_requested`, `approved`, `stale`,
  `draft`. `merged` is not included.

---

## Success Criteria *(mandatory)*

- **SC-001**: Every open PR in exactly one of `prs` or `draft_prs`; none duplicated.
- **SC-002**: Every movement event since boundary captured; none missed.
- **SC-003**: Lookback boundary correct for all cases; weekend and holiday activity
  never dropped.
- **SC-004**: JSON payload consumed by synthesis layer without transformation.
- **SC-005**: Switching config files requires no code changes.

---

## Assumptions

- `pr_classifier` (001) installed as local dependency; not vendored.
- GitHub token: `GITHUB_TOKEN` env var (non-empty) takes precedence over config
  field. Empty string env var treated as not set.
- Repository identifiers in `owner/repo` format. Validated before API calls.
- GitHub.com only; no GHES.
- Bank holidays configured per environment; tool does not fetch externally.
- Working day = not Saturday, not Sunday, not in `bank_holidays`. Consistent throughout.
- Lookback boundary = 00:00:00 on candidate working day in primary timezone, UTC.
  Candidate = yesterday, decremented until working day found. No special Monday rule.
- Invalid IANA timezone → exit code 1.
- Draft PRs included (unlike 001 which excludes them).
- `hours_since_activity` uses `updated_at`. Label changes reset the clock. Accepted.
- `hours_open` for `recently_merged` = `merged_at - created_at`.
- `hours_since_activity` for `recently_merged` = `now_utc - updated_at`.
- Jira pattern `[A-Z]+-\d+`. False positives accepted. Title before branch.
  Deduplicated across both sources.
- Automated PRs never become PRSnapshot objects. `automated_pr_counts` is `{}`
  when `bot_accounts` is empty.
- `automated_pr_counts` does not include a `merged` key.
- DISMISSED reviews count as prior reviews for `review_received`.
- DISMISSED CHANGES_REQUESTED does not block Approved aggregate state.
- `changes_addressed` uses `author.date`; `committer.date` ignored.
- `movement_by_type` counts individual emissions.
- Per-PR classifier error → `current_state: "unknown"`; not a per-repo error.
- `recently_merged` = `merged_at >= boundary`, regardless of when opened.
- `draft_converted_to_ready` uses REST Timeline Events API. If not surfaced, not
  emitted. Accepted limitation.
- `hours_waiting_for_review` null for merged PRs and all states except Waiting
  for Review.
- All output datetimes UTC ISO 8601 with `Z` suffix.
- Output to stdout; file output via shell redirection.
- `config.example.yaml` must contain every supported config key (`repositories`,
  `github_token`, `staleness_threshold_hours`, `bank_holidays`, `bot_accounts`,
  `primary_timezone`) with placeholder values and inline comments explaining each.
- Two configs in practice: `config.local.yaml` and `config.work.yaml`. Neither
  committed. `config.example.yaml` IS committed.
- No GUI. Terminal or scheduled job only.
- 002 uses PyGithub for GitHub API access, consistent with 001. The pr_classifier library expects PullRequest dataclass objects from 001's _models.py; 002 maps PyGithub objects to these before calling classify_pr."