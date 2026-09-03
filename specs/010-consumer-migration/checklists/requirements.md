# Specification Quality Checklist: Consumer migration — one public API, six repositories, one release

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-03
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

**Validation pass 1, 2026-09-03 — all items pass after one clarification round.**

Three items needed judgement rather than a simple pass, and the reasoning is recorded so a
reviewer can disagree with it rather than re-derive it:

1. **"No implementation details" / "written for non-technical stakeholders" — passes, with a
   stated house exception.** This is a migration feature whose deliverable *is* a set of call
   sites. Sibling specs 006-008 in this repository are written the same way: requirements state
   the behaviour that must be true, and the evidence documents carry the file-and-line inventory.
   This spec deliberately names **no** file paths or line numbers in its requirements - it
   describes the surfaces by role ("the private network-map reader", "the five show-parsing call
   sites", "the publisher and the consumer") and leaves the coordinates to
   `xml-rebuild-09-consumer-audit.md` (C1-C12) and the per-repository prompt files, which the
   Planning-context block links. A reviewer can therefore read the requirements without a
   checkout, and an implementer can resolve every one of them to a line through the linked
   evidence. The two exceptions are FR-073's four `dev/` files and FR-072's exempt sites, which
   are named deliberately: an exempt set described by category rather than enumerated is the
   failure C12 exists to prevent.

2. **Success criteria are technology-agnostic - passes with two deliberate strains.** SC-015
   names a package manager refusing an install and SC-018 counts imports. Both are unavoidable:
   the outcome being specified *is* a packaging behaviour and a source-level count. They are
   phrased as observable outcomes ("actually refused", "the measured count is zero") rather than
   as mechanisms, and they are verifiable without knowing how any repository is built.

3. **The three [NEEDS CLARIFICATION] markers are resolved, and one of them changed the
   feature's scope.** Q1 (count reaches shipped sources only; the four `dev/` occurrences are
   enumerated as exempt, with FR-073a requiring the *reason* for each exemption to be recorded so
   "not shipped" is not confused with "exists to detect the retired spelling"), Q2 (the descriptor
   **does** gain a constructible empty instance per complex type) and Q3 (the batch show-document
   conversion runs as an explicit operator command).

   Q2 is the one to review carefully. It is **new library capability inside a feature whose
   FR-026 otherwise forbids any**, so it is recorded as a named exception (FR-022a/FR-022b)
   rather than absorbed, it enlarges `cuems-utils`' own share from "publish what exists" to
   "publish it and add one thing", and Assumption 2 says so explicitly. If a reviewer wants that
   capability out of this feature, FR-086 is where it is consumed and the alternatives Q2
   rejected are recorded in the Clarifications entry.

   Q3's answer creates a consequence the spec must carry rather than hide: an operator-triggered
   conversion means an upgraded library can sit unconverted, so FR-095a makes the
   convert-on-read path - not the batch command - the thing that guarantees an unconverted
   document still opens, and requires it verified rather than assumed.

4. **A `/speckit.clarify` pass on the same day asked five further questions**, all of them in
   categories the first draft left thin, and all five were consumer-side behaviour that features
   007 and 008 deliberately delegated to this feature. Three of the five closed genuine holes
   rather than sharpening wording:

   - **Two of D21's three load outcomes had no consumer-side requirement at all.** The spec said
     the repair report must be surfaced but never said whether the editor writes the repaired
     document back (now FR-048a-c: it does not; a load stays a read), and said nothing whatever
     about the unrepairable outcome (now FR-049-049c: a structured failure on the same channel,
     one document refusing to open rather than a session failing). FR-049c records that this is
     new user-visible behaviour a project owner meets without warning otherwise.
   - **Rollback was missing entirely**, despite the cross-repo checklist in
     `xml-rebuild-07-speckit-prompts.md` §8 asking for it by name. Now FR-100-104, as two
     procedures split at the conversion boundary, with FR-103 requiring that boundary be
     checkable and FR-104 recording the reverse-converter rejection so it is not re-proposed.
   - **The UI sat outside the release gate.** `cuems-frontend` has no `debian/` directory, so it
     cannot hold a package edge, yet it is the surface both payload deltas land on. Now
     FR-105-108, a runtime payload-version handshake, with FR-106 keeping that version explicitly
     distinct from the document-version marker FR-012 excludes from the wire.

   The remaining two sized things the spec had asked for without supplying: the conversion's
   library scale (FR-095c/FR-095d, hundreds of documents, resumable, no batching) and the
   frontend question above.

**Post-clarify status**: 107 functional requirements, 26 success criteria, 10 user stories, 8
recorded clarifications across one session. All 16 checklist items pass. No items remain
incomplete.

**Two structural notes for a reviewer**: the Requirements section gained two `####` groups (UI
compatibility edge, Rollback) alongside the fifteen it already had - consistent with its existing
per-repository/per-theme organisation rather than a restructure. And the Clarifications session
carries two formats: three prose entries from `/speckit.specify` and five `- Q:/A:` bullets from
`/speckit.clarify`. They are one session because they are one day and one feature.

The spec is ready for `/speckit.plan`.
