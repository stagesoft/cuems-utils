# Specification Quality Checklist: Rebuild extension

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-08-27
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

### The one question that was asked, and its answer

**FR-043 / Q1** — for a field whose descriptor default would *change meaning* rather than restore
it (a reference to an object that is no longer present), does D21's second outcome apply or its
third? This sets the boundary between repair-and-notify and raise, so it was not resolvable by an
informed guess and was put to the repo owner during `/speckit.specify`.

**Answered: the descriptor carries a per-field repairability classification** (FR-031a). Both
outcomes stay reachable, and the choice between them stays schema-derived rather than becoming the
hand-written per-field table FR-045 exists to prohibit. Recorded in the spec's Clarifications
section; FR-031a, FR-035, FR-043, FR-044, SC-011a, SC-013 and SC-020/SC-020a carry the consequences.

One structural note worth flagging for `/speckit.plan`: FR-031a is a **Phase 1 deliverable whose
only consumer is in Phase 2**. That is the phase gate working as intended — ITEM E reads a landed
classification instead of negotiating one mid-implementation — but it means ITEM D's acceptance
criteria have to judge the classification on its own terms (US4 scenario 4a, SC-011a), since nothing
in Phase 1 exercises it end to end.

### The three §7.1 questions answered without asking

Each had a defensible default, so each is recorded in the spec rather than left open: the version
marker's *representation* is deferred to `/speckit.plan` by E10's explicit designation while its
*behaviour* is fully specified (FR-048 – FR-053); the repair report's shape is specified
behaviourally (FR-046); and the overlap between ITEM A's conversion and the editor's duration-repair
tool is settled by E21's split (FR-042, Assumption 9). `/speckit.clarify` remains not-skippable per
§7.1 and may reopen any of them.

### Interpretation notes for the three items above that could be read as failing

- **"No implementation details" / "technology-agnostic"** — the spec names schema types
  (`cms:CTimecodeType`), element shapes (`<duration><CTimecode>…</CTimecode></duration>`) and the
  canonical lexical form (`HH:MM:SS.mmm`). These are the **domain vocabulary and the wire contract**
  of this product, not implementation choices: they are what consumers across four repositories
  read and write. This matches the register of features 004–007's specs. No Python module paths,
  class names, function signatures or library choices appear in requirements or success criteria.
- **"Written for non-technical stakeholders"** — the stakeholders for a serialization library are
  maintainers, integrators and operators. Each user story is framed from one of those perspectives
  and states the outcome before the mechanism; the deliberately technical material is confined to
  "Why this feature exists" and the evidence references.

### `/speckit.clarify` — run 2026-08-27, five questions

Session (b) in the spec's Clarifications. What changed, in one line each:

1. **Version marker** → optional attribute on each root type, versioned per schema. This is **D3's
   fourth relaxation** (FR-048a) and standing rule 6 requires its own decision record, which the
   Clarifications section now is. Driven by a measured fact: no schema declares `anyAttribute`, so
   the marker had to be declared rather than merely written.
2. **Performance** → three budgets set before implementation (FR-PERF-002), closing a Principle IV
   gap: the spec had required measurement but set a threshold only for the suite.
3. **Backup on unwritable media** → the obligation attaches to persisting an upgrade, not to
   converting (FR-041a). Scopes D21's literal wording; recorded as a refinement, not applied quietly.
4. **Repairability source** → the registered semantic-rule surface (FR-031b), 15 declarations rather
   than ~200 field annotations. Driven by a measured fact: the schemas declare no `xs:keyref`, so the
   motivating case cannot be derived structurally.
5. **Backup retention** → backups on schema upgrade only; a repaired file overwrites on save,
   operator-validated (FR-041b, FR-041c). This **removed** a requirement this spec had invented —
   backup-on-every-config-save — that neither D21 nor D24 asked for.

Items 3 and 5 both narrowed obligations the spec had over-generalised. Item 5's tradeoff is recorded
at FR-041c rather than buried: saving a repaired document destroys the corrupt original, which rests
on the repair report being surfaced first — now an explicit 009 precondition (FR-053a).

### Scope addition, 2026-08-27 — superseded fade actions (session (c))

`fade_in` and `fade_out` are removed from `script.xsd`'s `ActionType`, superseded by `fade_action`
since feature 003. Placed in **ITEM D** by the repo owner's direction, on the rationale that ITEM D
is where the schema becomes authoritative, so the enumerations the descriptor publishes must first be
true (FR-029a — FR-029c).

Two consequences necessarily land outside ITEM D, and are recorded there rather than forced into it:
D3 bookkeeping (FR-012, now a **fifth** exception) and the document conversion (FR-051a, ITEM E,
`fade_in` → `play` / `fade_out` → `stop`).

Three findings worth carrying into planning:

- **They are live, not dead.** `cuems-engine`'s `ActionHandler` dispatches both as never-implemented
  stubs — `fade_in` "treated as play", `fade_out` "treated as stop". The removal therefore has
  consumer impact (FR-053b, 009's) and the conversion mapping is behaviour-preserving by construction.
- **A live schema/rule contradiction was found.** `ActionType` offers both values to `FadeCueType`
  while the `fade_action_type` rule forbids them there. FR-029b generalises the check across every
  enumeration in all six schemas rather than fixing only the instance that was reported.
- **A naming collision makes textual removal unsafe**, and it is wider than it first looks. The whole
  fade-profile surface — `FadeProfile`, `FadeFunctionParameter`, three schema types, the
  `fade_profiles` element on Audio and Video cues, and **five** registered T2 rules — is live and
  load-bearing, and shares only a word with `FadeCue`. `FadeProfile.type` is `'in'`/`'out'` and
  `MediaCue.get_fade_profile` also accepts `'fade_in'`/`'fade_out'` for those directions: the same two
  strings FR-029a deletes from a different enumeration in a different type. Explicitly out of scope
  (FR-029c, SC-012c).

  **This was checked, not assumed** — `FadeProfile.py` was proposed for deletion as a suspected orphan
  on 2026-08-27 and the check showed it fully live *within this repository*. That finding held; what
  changed is the question. See session (d) below.

### Scope addition, 2026-08-27 — the fade-profile surface is deleted (session (d))

Session (c)'s name collision led to a proposed rename (`FadeProfile` → `Envelope`); the decision
landed on **deletion** (FR-007a — FR-007c), D3's **sixth** exception.

- **Measured basis**: zero references to `fade_profile`, `FadeProfile` or `function_id` across all
  three consumer repositories. The surface is live inside `cuemsutils` — five rules, two classes, a
  registry binding — and dead everywhere else. The feature was never implemented end to end.
- **Why delete rather than rename**: renaming would enshrine a shape already known to be wrong. A
  `FadeProfile` has no `duration` and no `target_value`, so it cannot produce the `FadeCue` its
  replacement is meant to expand into, and `mode`/`function_id` duplicates `FadeCurveType`. Deletion
  lets the replacement arrive later as a **new type**, the convention's non-breaking path.
- **Justification recorded as distinct** (FR-007b): `settings.xsd`'s dead pair is *unreachable from any
  element*; this surface **is** reachable and is removed on the weaker "unconsumed externally"
  argument. Only one of the two generalises, so the spec says which was used.
- **The two fade removals are independently revertible** (FR-029c, SC-012c) — the test of whether
  FR-007a and FR-029a were kept as two decisions rather than one search-and-replace.
- **ITEM E now carries three conversions at one version step** (FR-051b/c, SC-016d), including a
  reported element **drop** — permitted only because it is reported (SC-016e).

Design inputs preserved in `specs/planning/envelope-feature.md`, including the two gaps, the
expansion-placement decision, and an unrelated engine gap found on the way (nothing reconciles a cue's
declared fade shape with a `FadeCue` targeting it).

**D3 now stands relaxed five times in this feature** — two files, five changes, plus the version-marker
attribute on all six roots. Three of the five are deletions of things nothing honours. Flagged for
explicit sign-off rather than assumed.

**Confirmed non-imminent** (repo owner, 2026-08-27): Envelope is expected to land with the Crossover
feature in the further future, so delete-then-re-add carries no churn risk. That closes the one
condition that would have reversed the deletion.

**FR-051d and SC-016f added as a consequence.** Discussing how Envelope would return surfaced an
assumption in the version machinery: a purely additive change needs **no** conversion in the
old-document direction, but still warrants a version step so a *new* document meeting an *older*
library gets FR-052's "newer than this library" diagnostic instead of a bare "unexpected element"
failure — no schema declares a wildcard. So the machinery must support a version step whose conversion
is the **identity**, writing no backup and reporting no repair. None of this feature's own three
transformations exercises that path, so it needs its own test rather than being left to the first
feature that relies on it.

Also added: FR-051b and SC-016d, requiring the version marker to carry **both** of this feature's
`script` transformations at **one** version step. Two independent conversions in one schema is
stronger evidence for FR-048's "systemic, not a per-change tell" than one conversion could be.

### Status

**All items pass**, and clarification is complete.

Remember the deliberate stop at §7.2: `/speckit.plan` does **not** run straight into
`/speckit.tasks` for this feature. The plan is cut at the A–D / E seam first (D31).
