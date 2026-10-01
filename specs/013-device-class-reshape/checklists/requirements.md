<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Specification Quality Checklist: Device-class reshape

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-01
**Feature**: [spec.md](../spec.md)
**Validation**: iteration 2, all items passing

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

## Notes

### Iteration 1 → 2: the one marker, resolved

Iteration 1 carried a single `[NEEDS CLARIFICATION]` on axis scope — which of §8.4's four document
axes the feature collapses — left open because the readings differed by roughly 3× in size and
disagreed about whether `cuems-frontend`'s flow 05 is genuinely blocked on 013.

Resolved in the 2026-10-01 clarification session, recorded in the spec's §Clarifications:
**all four axes, and no `doc_version` bump on any schema.** The second half was not asked and is
the more consequential answer; it is recorded below.

### The decision that departs from the brief, and why it is recorded three times

The brief, `CLAUDE.md`'s feature-013 line and the opening prompt all state the Kind as
*"a rule-4 file-format migration — version step **and** conversion"*. The session settled **no
version step and no registered conversion**, on the ground that the whole ecosystem lands together
behind the coordinated `xml-refactor-merge-candidate` tag, so a per-document version negotiation
buys nothing between components.

This is **not** a departure from rule 4. It is rule 4 discharged by **feature 007's** route rather
than feature 008's, and `specs/agreements/schema-evolution-convention.md` already records 007 as a
worked precedent for exactly this: a rename whose marker is *the element's own presence*, migrated
by *"a documented tool that runs once"*. `<audio>` and `<device class="audio">` cannot coexist, so
the shapes are self-identifying — which is the property FR-021 pins.

What the decision does cost is stated in the spec three times — once as prose
(§"What is already settled"), once as requirements (FR-020–FR-029), once as an operator-facing
obligation (FR-028, US2 scenario 8):

1. **Nothing converts on read.** The migration *is* the tool. A document the tool misses does not
   load (FR-027 requires it be diagnosed by name, not by a bare `xs:sequence` complaint — the X13
   failure mode this project vendors two broken files as evidence of).
2. **The marker does not move**, so an older `cuems-utils` reading a new-shape document gets a raw
   schema error rather than `DocumentTooNewError`. D27 covers the shipped set; it does not cover a
   node left un-upgraded, a rollback, or a restored backup.
3. **`cuems-convert-documents` cannot carry this migration unchanged** — it is version-driven and
   there is no step to drive it. FR-029 makes the tool's home a recorded planning decision rather
   than an assumed reuse.

Two things the decision makes *simpler*, recorded so the plan does not re-derive them:
`CURRENT_VERSION` and `DELIBERATE_IDENTITY_STEPS` are both untouched, and
`test_every_schema_past_version_1_has_a_conversion_for_every_step` passes unchanged. The prompt's
instruction — *"013's steps must not go in `DELIBERATE_IDENTITY_STEPS`"* — is satisfied because
013 has no steps.

### On "no implementation details"

This specification names schema files, source files and line numbers throughout. For a library
whose deliverable **is** a file format, those are the subject matter, not implementation leakage —
the same choice features 008, 011 and 012 made, and the reason
`specs/012-uuid4-convergence/consumer-census.md` exists as a blocking precondition. The spec still
states *what* must be true (an open class vocabulary, mutually exclusive shapes, a pure reshape, a
one-shot tool) rather than *how* to build it: no model-class layout, no rewrite algorithm, no
schema text.

### Measured rather than inherited

Nine findings (M1–M9) were measured on this branch on 2026-10-01 rather than carried from the
brief. Four of them correct a document that is still load-bearing elsewhere:

- **M1** — the brief's *"four cue-type unions at `sequence.component.ts:294-304`"* is wrong about
  where to look: five sites of four shapes in `project-edit`, plus a second file
  (`project-show/sequence/sequence.component.ts:141-145`) the brief does not name.
- **M2** — `node_hw_outputs` has three live reads, all in `cuems-engine`, and `NodeEngine.py:566`
  is an **unguarded subscript** that only survives today because the key is pre-seeded. FR-012 and
  SC-008 exist for this one fact.
- **M5** — `cuems-editor`'s `CuemsWsServer.py:439` is a 013 site and is **not** among flow 02's
  fourteen deprecated-surface call sites. This is the condition
  `specs/planning/refactor-sequencing-2026-10-01.md` §5 flagged, arriving one feature early and on
  013 instead of 014. It does not invalidate the editor-first recommendation; it changes when 013
  lands, not when flow 02 does.
- **M7** — two line references in the brief are one off (`node_hw_outputs` is at `:159`, not
  `:160`).

The suite baseline was re-run rather than inherited and came back **identical**: 3247 passed, 115
skipped, 2 xfailed in 53.25 s = 16.40 ms/test.

### Still open, and now assigned

**UR-1 and UR-5** are carried in §"Open items handed to `/speckit.clarify`" with measured gaps and
candidate dispositions, *assigned to the clarification session* rather than left unassigned — the
third unassigned pass the brief explicitly forbids. **The plan must not start until both are
placed** in 013 or in 014's public-surface pass.

### Items requiring spec updates before `/speckit.plan`

1. UR-1 and UR-5 must each be placed.
2. FR-029's question — whether the migration tool extends `cuems-convert-documents` or is a new
   entry point — is deliberately left to planning, but must be *recorded* there, not decided in
   passing.
3. FR-PERF-001's denominator must be measured on this branch across all four axes' load paths
   before any code changes, since the all-four answer widens it beyond the mappings document.
