# Specification Quality Checklist: Public object API — one surface, internal machinery

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-18
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain — **both resolved 2026-08-18**, see Notes
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

**Both decision stops are resolved.** Five clarification entries were recorded on 2026-08-18,
with the per-rule corpus sweep ([corpus-sweep.md](../corpus-sweep.md)) attached as the
evidence §9.2 required. Outcomes:

| Stop | Sub-question | Outcome |
|---|---|---|
| 2 | symmetry | T2 runs on write and explicit `validate()` only; read stays structural |
| 2 | never-stricter | measured: 0 of 14 setter rules reject anything accepted today; the uuid4 rule would reject live editor traffic and is excluded from T2 |
| 2 | setter fate | setters **delegate** to the registry — one definition, two call sites |
| 2 | failure mode | `validate()` reports all; `save()` raises on first and writes nothing |
| 2 | unit of registration | a **named rule** bound to (type, field) pairs |
| 1 | declared or conventional | **declared** — `RUNTIME_FIELDS`, MRO-accumulated like `REQ_ITEMS` |
| 1 | `save()` mid-show | succeeds, document-only, documented; no refusal |
| 1 | `load()` runnable | runnable; no promotion step |
| 1 | `to_wire()` cleanliness | structural consequence of the declaration |
| 1 | copy/equality | declared fields only; copies get fresh runtime state |

**One evidence gap is recorded rather than closed**: eight of the fifteen rules (all
`FadeCue`/`FadeProfile`) have zero corpus coverage. Keeping the tier off the read path means
this endangers nothing today; FR-024b carries the obligation to add a fade-cue document
before any of them is relied on as proven.

**Historical note — why the markers were left open at `/speckit.specify`.** The target design
(`specs/planning/xml-rebuild/xml-rebuild-06-target-design.md` §8.1 and §9.2) and the prompt set (§5.2)
both name these as **required decision stops that `/speckit.clarify` must resolve**, and
feature 005 deferred them here on purpose:

| Marker | Decision | Why it cannot be answered while drafting |
|---|---|---|
| Stop 1 | Runtime state vs persisted state in the persistence API | Five sub-questions in §8.1. "Convention, documented and tested" is an acceptable answer, but the choice is the user's, and it shapes `save()`, `load()` and equality semantics. |
| Stop 2 | Load/write symmetry of the semantic validation tier | §9.2 requires a **per-rule corpus sweep across all 14 value-rejecting setters**, attached as evidence, *before* deciding — explicitly "not with a judgement call". Guessing here would violate the instruction that produced the stop. |

Both have since been answered; FR-026 and FR-028 now state outcomes rather than dependencies.

**Content-quality note.** This spec names concrete method names (`load`, `save`,
`to_wire`, …), payload names and finding identifiers. That is deliberate: the feature's
deliverable *is* a public API contract, the names were fixed by the settled decisions
(D12/D15, Q14→(i)), and the "non-technical stakeholder" for a shared library is a consumer
maintainer. Structure, mechanism and module layout are left to `/speckit.plan`.

All items pass. The spec is ready for `/speckit.plan`.
