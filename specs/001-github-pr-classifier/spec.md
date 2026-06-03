# Feature Specification: GitHub PR Classifier

**Feature Branch**: `001-github-pr-classifier`

**Created**: 2026-06-03

**Status**: Draft

**Input**: User description: "A tool that retrieves and classifies the current state of GitHub pull requests across multiple repositories to support daily engineering stand-ups."

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 – Retrieve and Classify PRs Across Repositories (Priority: P1)

An engineer runs the tool before a stand-up, providing a list of repositories.
The tool fetches all open pull requests from each repository and classifies each
one into exactly one of four states:

- **Changes Requested** – at least one reviewer has requested changes; no
  subsequent approval overrides it
- **Approved** – at least one approval and no outstanding change requests
- **Waiting for Review** – open, no review submitted yet
- **Stale** – open with no activity (commits, comments, or review events) in the
  last 48 hours (configurable). Applies to PRs that are not in Changes Requested
  and would otherwise be Approved or Waiting for Review

The output is structured data (for example JSON) grouping PRs by classification.

**Why this priority**: This is the complete core value of the tool. Without it
nothing else is meaningful.

**Independent Test**: Supply two or three repositories via input; verify the
response contains four classification buckets and that each returned PR appears in
exactly one bucket.

**Acceptance Scenarios**:

1. **Given** a valid list of repository identifiers and valid credentials,
   **When** the tool is invoked,
   **Then** it returns structured data containing all open PRs grouped into the
   four defined classification buckets.

2. **Given** a repository that has no open pull requests,
   **When** the tool is invoked with that repository in the list,
   **Then** the repository still appears in the output with empty classification
   buckets.

3. **Given** a pull request with at least one approval and no outstanding change
   requests but no activity for more than 48 hours,
   **When** classification is applied,
   **Then** the PR appears in the **Stale** bucket.

4. **Given** a pull request where one reviewer requested changes and a second
   subsequently approved,
   **When** classification is applied,
   **Then** the PR appears in **Changes Requested** (unresolved change request is
   not overridden by a later approval from a different reviewer).

---

### Edge Cases

- What happens when credentials are absent or expired? The tool MUST return a clear
  authentication error and exit without partial output.
- What happens when a repository in the list does not exist or is inaccessible?
  The tool MUST report the inaccessible repository distinctly and continue
  processing remaining repositories.
- What is the classification when a PR has both a change request and a stale
  condition? **Changes Requested** takes precedence over Stale. Stale applies to
  PRs that are not in Changes Requested and have had no activity within the
  staleness threshold, including PRs that would otherwise be Approved or Waiting
  for Review.
- What happens when the repositories list is empty? The tool MUST return a
  validation error immediately, before making any external requests.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The tool MUST accept one or more repository identifiers as input.
- **FR-002**: The tool MUST retrieve all currently open pull requests for each
  provided repository.
- **FR-003**: The tool MUST classify each open pull request into exactly one of the
  four states: Waiting for Review, Changes Requested, Approved, Stale.
- **FR-004**: The tool MUST apply classification rules in the following precedence
  order: (1) Changes Requested, (2) Stale (no activity within staleness threshold),
  (3) Approved, (4) Waiting for Review.
- **FR-005**: The tool MUST output structured data (JSON) grouping PRs by
  classification state, including at minimum: repository name, PR number, PR title,
  author, URL, and last activity timestamp.
- **FR-006**: The tool MUST report inaccessible or non-existent repositories as
  distinct errors without stopping processing of other repositories.
- **FR-007**: The tool MUST return a clear error and exit when authentication
  credentials are absent or invalid.
- **FR-008**: The tool MUST validate that the repository list is non-empty before
  making any external requests.
- **FR-009**: The core retrieval and classification logic MUST be structured as a
  reusable library, callable independently of any command-line invocation.
- **FR-010**: The command-line interface MUST be a thin wrapper over the library;
  it MUST NOT contain retrieval, classification, or data-shaping logic.
- **FR-011**: The tool MUST exclude draft pull requests from all classification states.

### Constitution Alignment *(mandatory)*

- Story structure supports independent implementation and validation; User Story 1
  is the complete MVP.
- Success criteria are measurable and technology-agnostic.
- Any added complexity must be justified in the plan.
- Behavior changes must include fail-first validation (tests that fail before
  implementation, pass afterward).

### Key Entities *(include if feature involves data)*

- **PullRequest**: Represents a single open pull request. Key attributes: repository
  name, PR number, title, author, URL, last activity timestamp, list of review
  events.
- **ReviewEvent**: A review action on a PR. Key attributes: reviewer, state
  (approved / changes_requested / commented), timestamp.
- **ClassifiedPR**: A PullRequest enriched with its resolved classification state.
- **RepositoryResult**: Aggregates ClassifiedPRs for a single repository along with
  any error status for that repository.
- **ClassificationReport**: The root output structure; contains a list of
  RepositoryResults and a metadata block (total counts per bucket, generation
  timestamp, staleness threshold used).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-002**: Each open PR appears in exactly one classification bucket; zero PRs
  are duplicated or omitted in the output.
- **SC-004**: Users can identify which PRs require immediate action (changes
  requested or waiting for review) within 30 seconds of invoking the tool.

---

## Assumptions

- The staleness threshold defaults to 48 hours of no activity (commits, comments,
  reviews). This is configurable but 48 hours is the out-of-the-box default.
- Authentication is provided via a pre-configured access token available in the
  execution environment; the tool does not manage credential storage or OAuth flows.
- "No activity" for staleness means no new commits pushed to the PR branch, no
  review comments, no review submissions, and no inline comments after the PR was
  opened or last updated.
- The tool operates on GitHub-hosted repositories. Support for GitHub Enterprise or
  other providers is out of scope for this version.
- Repository identifiers are in `owner/repo` format (for example
  `my-org/backend-service`).
- Draft pull requests are excluded from all classification buckets by default
  (treated as not open for review purposes).
- The tool is invoked from a terminal or CI environment; no GUI is in scope.
- The deliverable is a library-first package: the classification and retrieval
  logic are the primary artifact, and the CLI is a thin consumer of that library.
  Input parsing, output formatting, and process exit handling are confined to the
  CLI layer and do not leak into the library.
