# Specification Quality Checklist: Schema-derived XML serialization core

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-11
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Validation Notes

**Iteration 2 — after `/speckit.clarify` (4 questions, 2026-08-11)**

All four clarifications moved the spec toward a stricter, more coherent position:

- **F4 / failure paths** — first answered as "remove the catch-all", then reversed by the
  requester so 004 carries **zero** behaviour changes. FR-015a now preserves the
  swallow-and-log behaviour behind a named compatibility marker; F4 moves to 005. The
  superseded answer is recorded in Clarifications rather than erased, since a reader needs
  to know the reversal was deliberate.
- **Deprecation shims** — one uniform policy (FR-026 to FR-030) replaced the earlier
  clean-break rename. No consumer breaks at this release. Required softening FR-002,
  FR-003, SC-004 and SC-005 from "deleted from the codebase" to "absent from every live
  path", with SC-012 (zero deprecation warnings from the library's own paths) as the
  mechanism that keeps the weaker wording honest.
- **Logging** — the single explicit exclusion from the behaviour guarantee (FR-032 to
  FR-034). Closes F11 here rather than deferring it, and removes show content from log
  files as a side effect.
- **Regression corpus** — settled concretely as a vendored, frozen, four-source corpus
  (FR-022a/FR-022b, Assumption 1). Resolves the one genuinely unactionable phrase in the
  first draft.

Consistency re-checked after integration: no duplicate requirement identifiers; user
story 2's narrative, independent test and scenario 5 realigned with the shim and registry
decisions; F11 removed from the deferred-fixes table; success criteria renumbered into
monotonic order.

**Iteration 1 findings and resolutions**

- *"No implementation details"* — this is a refactor of internal machinery, so the spec
  necessarily names the artifacts being replaced (element ordering, type guessing,
  duplicated mapping rules) in behavioural terms. It deliberately avoids naming the
  library, the module layout and the class shapes; those live in
  `specs/planning/xml-rebuild-06-target-design.md` and belong in `plan.md`. **Pass**, with
  the note that "the schema" and "the wire dict" are domain vocabulary here, not
  implementation leakage.
- *"Written for non-technical stakeholders"* — the audience for this feature is the
  library's consumer components and its maintainers; that is stated explicitly at the head
  of the user scenarios rather than pretending an end-user audience. **Pass**.
- *Scope boundary on module renaming* — raised as a tension between "no public API change"
  and the PEP 8 rename. Initially resolved as a clean break; **superseded in iteration 2**
  by the uniform deprecation-shim policy, under which the rename breaks nothing.
- *Corpus definition* — "every existing XML file on disk" was under-specified; deferred to
  an assumption in iteration 1 and **settled concretely in iteration 2** (FR-022a).
- *Byte-identity vs the audit* — the audit's acceptance list asks only for semantic
  identity; this feature demands byte-identity. Recorded as a deliberate tightening
  (Assumption 2) rather than a contradiction. **Resolved**.

**Open items requiring attention during `/speckit.plan`**

- Re-verify content-model order derivation against the pinned library version
  (Assumption 6) — the one technical premise the whole design rests on.
- Record the exact pre-refactor performance baseline before any code moves (FR-PERF-001).
- Produce the shim → replacement → consumer call-site table (FR-028); it is both a 004
  deliverable and the input to feature 008.
- Enumerate which schema types reach a generic class by silent fallback today, so they can
  be bound to that same generic without changing output (FR-007).
- Confirm corpus coverage of all six schemas before implementation starts (Assumption 1).

## Notes

- Items marked incomplete require spec updates before `/speckit.clarify` or `/speckit.plan`
