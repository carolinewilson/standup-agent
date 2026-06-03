<!--
Sync Impact Report
- Version change: template-unset -> 1.0.0
- Modified principles:
	- Principle slot 1 -> I. Spec-First Delivery
	- Principle slot 2 -> II. Independently Valuable Increments
	- Principle slot 3 -> III. Verifiable Quality Gates
	- Principle slot 4 -> IV. Automation and Hook Compliance
	- Principle slot 5 -> V. Clarity, Simplicity, and Traceability
- Added sections:
	- Operational Constraints
	- Delivery Workflow and Quality Gates
- Removed sections:
	- None
- Templates requiring updates:
	- ✅ updated: .specify/templates/plan-template.md
	- ✅ updated: .specify/templates/spec-template.md
	- ✅ updated: .specify/templates/tasks-template.md
	- ⚠ pending review: .specify/templates/commands/*.md (directory not present in this repository)
- Follow-up TODOs:
	- None
-->

# Standup Agent Constitution

## Core Principles

### I. Spec-First Delivery
Every feature MUST begin with a written specification in `spec.md` before
implementation begins. The specification MUST include independently testable user
stories, measurable success criteria, and explicit assumptions.
Rationale: A shared source of truth reduces rework and prevents implementation
drift from user intent.

### II. Independently Valuable Increments
Work MUST be organized so User Story 1 is a viable MVP, and each subsequent story
adds value without requiring unfinished later stories. Plans and tasks MUST preserve
independent testability per story.
Rationale: Incremental delivery shortens feedback loops and lowers release risk.

### III. Verifiable Quality Gates
Behavior-changing work MUST include tests that fail before implementation and pass
afterwards. Plans MUST define constitution checks up front and revalidate them after
design. Tasks MUST include validation activities tied to acceptance scenarios.
Rationale: Quality must be evidenced, not assumed.

### IV. Automation and Hook Compliance
Registered lifecycle hooks MUST be honored unless explicitly disabled in
`.specify/extensions.yml`. When hooks are optional, execution decisions MUST be
recorded in workflow output.
Rationale: Automation enforces repeatable process and catches omissions early.

### V. Clarity, Simplicity, and Traceability
Artifacts MUST favor the simplest design that satisfies requirements, and every task
MUST map to a user story or cross-cutting objective. Complexity exceptions MUST be
explicitly justified in the plan.
Rationale: Simplicity improves maintainability and traceability improves auditability.

## Operational Constraints

- Integration selection MUST remain compatible with configured Spec Kit integrations.
- Generated artifacts MUST use repository templates unless a justified deviation is
	documented in the plan.
- Runtime guidance in `.github/copilot-instructions.md` MUST remain aligned with plan
	and workflow expectations.

## Delivery Workflow and Quality Gates

1. Specify: create or update `spec.md` with prioritized stories, requirements, and
	 measurable success criteria.
2. Plan: complete technical context and constitution checks before design execution.
3. Tasks: produce dependency-ordered tasks grouped by story, including required
	 validation tasks for behavior changes.
4. Implement: execute tasks in priority order while preserving independent story
	 validation checkpoints.
5. Review: verify constitution compliance before merge or release.

## Governance

This constitution is authoritative for workflow, planning, and execution practices
in this repository. Amendments require: (1) a documented change proposal,
(2) explicit update of impacted templates and guidance files, and
(3) version bump according to policy below.

Versioning policy:
- MAJOR: Removal or incompatible redefinition of a core principle or governance rule.
- MINOR: Addition of a principle/section or materially expanded mandatory guidance.
- PATCH: Clarifications, wording refinements, or non-semantic edits.

Compliance review expectations:
- Every plan MUST include a constitution check.
- Every task list MUST preserve story traceability and required validation work.
- Reviewers MUST block approval when mandatory rules are violated without
	documented justification.

**Version**: 1.0.0 | **Ratified**: 2026-06-03 | **Last Amended**: 2026-06-03
