<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Specification Quality Checklist: uuid4 convergence

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-29
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

## Notes

One validation pass was run over the written spec. What it found and what changed:

- **Implementation detail (Content Quality item 1) — two failures, both fixed.** A scenario in
  US1 named two document *filenames*, and US2's priority rationale named the identity tool by its
  executable name. Both now name the thing rather than its identifier. Concrete identifiers
  deliberately survive in two places: the **Measured since the planning documents** table, where
  they are evidence and a reader must be able to check them, and **Open questions**, where the
  decision is about a specifically named artifact. Sibling component names (the engine, the
  editor, the node configuration daemon) are treated as domain actors in this ecosystem, not as
  implementation detail.
- **Every other item passed on the first reading.** No rewrite was needed for testability,
  measurability, edge cases, scope bounding, or dependencies.

**On the "no [NEEDS CLARIFICATION] markers" item.** There are none inline, and that is not the
same as there being no open decisions. Three decisions have no defensible default and are carried
in **Open questions for the clarification pass**, each naming the requirements it bears on. They
are written that way rather than as inline markers because the requirements themselves are stated
so that *both* branches of each question remain testable — FR-030 in particular states what must
be recorded if its first branch is declined. The item is marked complete on that basis; a reader
who disagrees should treat the three open questions as the markers.

**Carried into `/speckit.clarify`**: the three open questions, and confirmation — not reopening —
of the four assumptions (5, 6, 7 and the type question in Q2) that answer the consumer's upstream
report.

**One dependency is unresolved and is not this specification's to resolve**: §10.7's hardware
confirmation. Both production machines have been unreachable since 2026-09-23. FR-038 requires the
confirmation before a first real run; it does not block planning.

---

## Post-clarification (2026-09-29)

`/speckit.clarify` ran five questions; all five were answered and integrated. The three questions
this checklist recorded as deferred are **closed**, and two further decisions were taken that the
specification pass had not identified as open at all:

- **Conflict resolution** — what the re-mint does when two nodes share an identity. Researching it
  produced M-l and M-m and changed the answer: a collision is reachable *after* a correct
  migration, chiefly by disk cloning, so the feature closes the routes rather than only refusing
  the case. This amends feature 011's D13 (FR-019d).
- **Performance budget basis** — "a realistic library size" was not measurable and so not a budget.
  Replaced by a throughput figure plus a named fixture, and extended to an operator-facing duration
  estimate before a stop-the-world run (FR-PERF-001, FR-PERF-003).

The specification grew from 38 to 52 functional requirements and from 14 to 18 success criteria.
All checklist items above remain satisfied; re-verified after integration.

---

## Post-analysis (2026-09-30)

`/speckit.analyze` ran over spec, plan and tasks against the constitution. It found **one
constitution violation, three contradictions and two ambiguities**, all now closed. The checklist
items above are re-verified and still satisfied; two of them were passing on a technicality:

- **"Success criteria are measurable" was satisfied in form only.** Every performance criterion
  named a budget and none carried a value — "its stated per-megabyte budget", "a stated
  tolerance", "a named fixture". A criterion no test can fail is not measurable, and this was the
  feature's one Principle IV violation. Closed with 500 MB/s, 1%, `remint_200` at 2.0 s, and
  ±25%. **The lesson for the next feature's checklist pass**: read a measurability item as
  "could a test fail this?", not "does a threshold get mentioned?".
- **"Requirements are testable and unambiguous" missed a direct contradiction.** FR-022a forbade
  a registered conversion while FR-023 required "the registered conversion" to do the detecting.
  Both read as clear requirements in isolation; only reading them together shows one of them
  cannot be built. Pairwise consistency is not what a per-item checklist pass measures, which is
  why the analysis pass exists after it rather than instead of it.

The other four findings — the distribution model, the "converged" vocabulary collision, the
ambiguous sentinel constant, and a requirement with no task (FR-038) — are recorded in the
specification's **Session 2026-09-30** clarifications and in `research.md`'s addendum (R11, R12).
Four requirements and one success criterion were added — FR-011a and FR-011b (the scope split
and the modification-time property), FR-021c (the union as two named definitions), FR-036a (the
guide's collision-routes obligation) and SC-002a — bringing the specification to **56 functional
requirements and 19 success criteria**. Seven tasks were added; the task list is now **93**.
