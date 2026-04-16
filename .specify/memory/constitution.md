<!--
Sync Impact Report
- Version change: template -> 1.0.0
- Modified principles:
  - [PRINCIPLE_1_NAME] -> I. Code Quality By Default
  - [PRINCIPLE_2_NAME] -> II. Tests As A Release Gate
  - [PRINCIPLE_3_NAME] -> III. Consistent User Experience
  - [PRINCIPLE_4_NAME] -> IV. Performance Budgets Are Requirements
  - [PRINCIPLE_5_NAME] -> removed
- Added sections:
  - Engineering Standards
  - Delivery Workflow & Quality Gates
- Removed sections:
  - placeholder-only template sections
- Templates requiring updates:
  - ✅ updated: .specify/templates/plan-template.md
  - ✅ updated: .specify/templates/spec-template.md
  - ✅ updated: .specify/templates/tasks-template.md
  - ⚠ pending: .specify/templates/constitution-template.md (left generic as bootstrap template)
- Follow-up TODOs:
  - None
-->
# cuems-utils Constitution

## Core Principles

### I. Code Quality By Default
All production code MUST be readable, small in scope, and maintainable by a new
contributor. Every change MUST pass linting, static checks, and review with no
known warnings introduced. Public APIs and non-trivial logic MUST include
documentation or inline rationale where intent is not obvious.

Rationale: quality debt compounds quickly in utility repositories and reduces
delivery speed over time.

### II. Tests As A Release Gate
Every behavior change MUST include or update automated tests at the correct
level (unit, integration, or contract). A change is not complete until tests
fail before the implementation and pass after it. Merges MUST be blocked if any
relevant test suite fails.

Rationale: deterministic tests are the primary protection against regressions.

### III. Consistent User Experience
User-facing behavior (CLI output, prompts, error messages, docs examples, and
defaults) MUST be consistent across commands and features. New flows MUST follow
existing naming, formatting, and interaction conventions unless a documented
migration plan is approved.

Rationale: consistency reduces cognitive load and support overhead.

### IV. Performance Budgets Are Requirements
Features MUST define measurable performance targets (latency, throughput,
resource usage, or startup time) before implementation. Changes that degrade
agreed budgets MUST be rejected or accompanied by explicit approval and a
mitigation plan.

Rationale: performance regressions are functional regressions for developer
tools and automation pipelines.

## Engineering Standards

- Code MUST compile or run without warnings in default project tooling.
- Refactors MUST preserve behavior unless the spec explicitly states otherwise.
- Dependency additions MUST be justified in the plan with maintenance impact.
- Error handling MUST produce actionable messages for users and maintainers.

## Delivery Workflow & Quality Gates

- Plan documents MUST include a constitution check covering quality, test
  strategy, UX consistency, and performance goals.
- Specifications MUST define testable acceptance scenarios and measurable
  success criteria, including UX and performance outcomes where applicable.
- Task breakdowns MUST include testing work and verification steps per story.
- Pull requests MUST include evidence of lint/test results and any performance
  validation required by the change.

## Governance

This constitution is the highest-priority engineering policy for this
repository. In case of conflict, this document overrides local conventions.

Amendment policy:
- Propose amendments in a pull request that includes rationale, affected
  templates, and migration guidance for in-flight work.
- At least one maintainer approval is required before adoption.
- `LAST_AMENDED_DATE` MUST be updated on every accepted amendment.

Versioning policy:
- MAJOR: incompatible governance or principle removal/redefinition.
- MINOR: new principle/section or materially expanded guidance.
- PATCH: clarifications and wording improvements with no semantic change.

Compliance review expectations:
- Every plan and pull request MUST include an explicit constitution compliance
  check.
- Reviewers MUST block merges that violate mandatory terms ("MUST").
- Exceptions MUST be documented in the plan's complexity tracking section.

**Version**: 1.0.0 | **Ratified**: 2026-03-20 | **Last Amended**: 2026-03-20
