# Specification Quality Checklist: Node model migration

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-21
**Updated**: 2026-08-24 after `/speckit.clarify` (5 questions answered)
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

**On "no implementation details" and "non-technical stakeholders"**: this is a library-internal
migration across three repositories. Its stakeholders are the maintainers of `cuems-utils`,
`cuems-nodeconf`, `cuems-common`, `cuems-engine` and `cuems-editor`, and the artefacts under
discussion — a schema, a wire format, an element name, a declared breaking change — are named
because naming them *is* the requirement. Symbols are cited as contracts to change or preserve,
not as designs to build; no requirement prescribes a class layout, a module name or a call
signature. This matches the convention established by features 004–006.

**All five clarifications resolved (2026-08-24)** — three of them enlarged the feature:

| # | Question | Answer |
|---|---|---|
| 1 | What `node_list` denotes here | Schema container keeps the name; the MAC-keyed working set lands under its own name. `CuemsNode.py` moves in whole |
| 2 | `NodeRoleType` vocabulary | `controller` / `node` / `firstrun` — completes the standardization `cuems-common` already declared |
| 3 | Documents already on disk | Hard cutover; one-shot idempotent conversion owned by `cuems-common`'s package upgrade |
| 4 | In-memory types | Fully typed for `network_map` only — a declared single-schema exception to feature 006's no-adapters rule |
| 5 | Repositories edited | `cuems-utils` + `cuems-nodeconf` + `cuems-common`; engine and editor migrate in 008; no release between the two |

**Two settled constraints were superseded by explicit decision**, and the spec says so where it
would otherwise read as a contradiction of the planning documents:

- **D3** ("no `.xsd` edits; wire-compatible with every XML on disk") is relaxed **for
  `network_map.xsd` only**. The other five schemas remain bound, and SC-010a measures that the
  edit does not leak.
- The incoming instruction **"DO NOT CHANGE the node_type wire format"** is superseded: the
  format change is now required. `cuems-common/CLAUDE.md:83` had already scheduled this exact
  migration as "(serialized enum, XSD migration)", so the decision brings the work forward
  rather than inventing it.

**Residual risk carried into planning**, not a spec gap: the hard cutover has no working
partially-deployed state. FR-030c states the release gate; the plan must sequence the three
repository branches so that no artefact reaches a node without the conversion.

Ready for `/speckit.plan`.
