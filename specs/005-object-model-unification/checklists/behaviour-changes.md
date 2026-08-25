# Behaviour-Change Evidence Checklist: 005 object model unification

**Purpose**: Validate that the *requirements* for each enumerated behaviour change are complete
enough to implement and review — specifically that each one names the test that proves it was
broken, the outcome that proves it is fixed, and the consumer-visible consequence recorded for
the migration guide.
**Created**: 2026-08-17
**Feature**: [spec.md](../spec.md) — FR-019's seven-row table is the spine of this checklist
**Depth**: Release gate | **Audience**: reviewer at PR time, and author before `/speckit.implement`

**This checklist tests the requirements, not the code.** Every item asks whether something is
*specified*, not whether it *works*. Items are answerable by reading `spec.md`, `plan.md`,
`tasks.md`, `data-model.md` and `contracts/README.md` — no test run required.

**Change shorthand**: BC1 = F18 internal types · BC2 = F12/F19 regions · BC3 = F16 id clearing ·
BC4 = F17 setter swallow · BC5 = F20 defaulting · BC6 = root `items()` / stray keys ·
BC7 = F4 DMX failure path.

**Audited 2026-08-17** — 29 pass, 8 fail; **6 remediated the same day, 2 open** (CHK011, CHK032).
Findings, remediations and the two open items at the bottom.

## Per-Change Evidence Completeness

One item per enumerated behaviour change. Each asks whether all three required artifacts are
specified for that change: the failing test, the passing outcome, and the migration entry.

- [x] CHK001 For BC1, are all three specified — a test required to fail beforehand, its passing
      outcome, and the consumer-visible consequence? [Completeness, Spec §FR-019 row 1, SC-001,
      Tasks T010/T023/T044]
- [x] CHK002 For BC2, are all three specified, including which region supply shapes the evidence
      must cover? [Completeness, Spec §FR-019 row 2, Edge Cases, Tasks T022/T026/T044]
- [x] CHK003 For BC3, are all three specified, including which identifier fields must end up
      empty? [Completeness, Spec §FR-019 row 3, Tasks T034/T037/T044]
- [x] CHK004 For BC4, are all three specified, including the "no such setter" case that must
      remain unchanged? [Completeness, Spec §FR-019 row 4, Tasks T039/T041/T044]
- [x] CHK005 For BC5, are all three specified, including which classes change their bare-construction
      result? [Completeness, Spec §FR-019 row 5, Data-model §2, Tasks T033/T035/T044]
- [x] CHK006 For BC6, are all three specified, including the outcome for stray keys on both the
      root and a cue in both projections? [Completeness, Spec §FR-019 row 6, §FR-015a, Tasks
      T013/T019/T044]
- [x] CHK007 For BC7, are all three specified, including what the raised error must identify?
      [Completeness, Spec §FR-019 row 7, §FR-023, Tasks T040/T042/T044]

## Requirement Completeness

- [x] CHK008 Is the requirement to *search for* code relying on today's empty bare construction
      assigned to a task, or does the spec only note that it "must be found"? [Gap, Spec §Edge
      Cases, BC5]
- [x] CHK009 Are the specific fields whose internal type changes under BC1 enumerated in the spec
      itself, or only in `data-model.md` §4? [Traceability, Spec §FR-019 row 1]
- [x] CHK010 Is `Media.duration`'s exclusion from all coercion changes stated in the spec, or does
      it exist only in `data-model.md` §4 and `tasks.md` T037? [Gap, Consistency]
- [ ] CHK011 Does any requirement define what happens if a behaviour change is found to break a
      consumer *after* merge — revert, forward-fix, or feature-flag? [Gap, Recovery Flow]
- [x] CHK012 Is the required *content* of a migration-guide entry specified (before/after example,
      affected call sites, severity), or only that consequences are "recorded"? [Completeness,
      Spec §FR-UX-001 vs Tasks T044]
- [x] CHK013 Is the set of "consumers" whose visibility matters defined by name — engine, editor,
      nodeconf, UI — so an author can tell whether a consequence is consumer-visible?
      [Clarity, Spec §FR-UX-001]

## Requirement Clarity

- [x] CHK014 For BC7, is "an error naming the scene" defined by identifier — scene id, label, or
      document position? [Ambiguity, Spec §FR-023]
- [x] CHK015 For BC6, is "exactly one log record" scoped — one per dropped key per object, per
      object, or per document? [Ambiguity, Spec §FR-015a, SC-004]
- [x] CHK016 For BC4, is the treatment of exceptions *other than* `AttributeError` raised inside a
      setter stated, or left to inference? [Clarity, Spec §FR-019 row 4]
- [x] CHK017 For BC5, is "that class's declared defaults" unambiguous for classes that had no
      defaults dict, given the `Unset` sentinel? [Clarity, Spec §FR-017, Data-model §1]
- [x] CHK018 Is "fails before" defined as failing against a specific baseline — the pre-005 commit —
      rather than against an arbitrary earlier state? [Measurability, Spec §SC-003]

## Requirement Consistency

- [x] CHK019 Does every FR-019 row map to exactly one change contract in `contracts/README.md`
      (C5–C11), with no row unmapped and no contract orphaned? [Consistency, Traceability]
- [x] CHK020 Is BC7 presented as in-scope consistently across spec, plan, tasks and the
      requirements checklist, given the feature input enumerated only six changes? [Consistency,
      Spec §Clarifications 2026-08-12]
- [x] CHK021 Are BC1 and BC2 distinguishable in the evidence, given they share test tasks, so a
      failure attributes to one change rather than "the pair"? [Traceability, Tasks T010/T022/T023]
- [x] CHK022 Do BC6's descriptions agree across FR-019 row 6, FR-014, FR-015 and FR-015a — filter,
      drop, and log — without one implying an error path? [Consistency]
- [x] CHK023 Is the migration-guide carrier named consistently (`migration-map.md` in this feature
      dir) across FR-UX-001, T003 and T044? [Consistency]

## Acceptance Criteria Quality

- [x] CHK024 Is the location and format for recording the seven fail-then-pass pairs specified
      well enough that a reviewer can confirm all seven, rather than trusting a summary?
      [Measurability, Spec §SC-003]
- [x] CHK025 Can "serialized output unchanged for valid input" be checked *per change*, or only in
      aggregate via the goldens — and is per-change attribution required? [Measurability, Spec
      §FR-020, §SC-002]
- [x] CHK026 For BC3, is the expected `initial_template` delta stated precisely enough to be
      diffed — which fields, and what value replaces the random id? [Measurability, Spec §FR-022]
- [x] CHK027 Are the success criteria for BC1 expressed as something countable (zero type
      differences across N documents) rather than as a qualitative claim? [Measurability, Spec
      §SC-001]

## Scenario Coverage

- [x] CHK028 If only the MVP ships (US1 + US2), is it specified which migration entries are
      required and which defer with their changes? [Coverage, Gap, Tasks §Implementation Strategy]
- [x] CHK029 Are requirements defined for interactions *between* changes — for example a field
      that BC5 newly defaults and BC6's rule would then filter? [Coverage, Gap]
- [x] CHK030 Is the behaviour specified when a stray key collides with a runtime attribute name,
      given both are non-declared state? [Edge Case, Spec §Edge Cases, §FR-004a]
- [x] CHK031 For BC2, do the requirements cover a region supplied in a shape none of the four
      enumerated forms match? [Coverage, Spec §Edge Cases]

## Dependencies & Assumptions

- [ ] CHK032 Is Assumption 7 — that the UI tolerates the cleared template identifiers — marked as
      validated or as an open assumption carrying a verification owner? [Assumption, Spec
      §Assumptions]
- [x] CHK033 Is the assumption that nothing relies on today's empty `Cue()` stated as an assumption
      rather than presented as fact? [Assumption, BC5]
- [x] CHK034 Is the dependency on 004's goldens as *the definition* of "unchanged output" stated,
      including what happens if a golden is found to be wrong? [Dependency, Spec §FR-020,
      Contracts C1]

## Deliberate Non-Changes *(delete this section if carry-overs are out of scope)*

These are spec'd decisions *not* to change behaviour. They need the same recording discipline as
the seven changes, because a later reader cannot distinguish "deliberate" from "overlooked".

- [x] CHK035 Is the standing validation asymmetry (setter rules reaching some construction paths
      and not others) required to be recorded in the migration notes as deliberate, with its
      carrier named? [Completeness, Spec §FR-006b]
- [x] CHK036 Is the requirement that no value-rejecting rule may be added *or moved* stated in a
      way a reviewer can check against a diff? [Measurability, Spec §FR-006b]
- [x] CHK037 Are the two pinned legacy rejections identified specifically enough to confirm they
      still fire for the same reason, not merely that two documents still fail? [Clarity, Spec
      §FR-006a, §SC-007]

## Notes

- Check items off as completed: `[x]`
- An unchecked item is a spec defect, not a code defect — fix the requirement, then re-run
- CHK001–CHK007 are the entries the checklist was requested for; the rest test the quality of
  what those seven depend on
- 37 items, 35 carrying a traceability reference (95%)

---

## Audit results — 2026-08-17

**29 pass, 8 fail — 6 remediated, 2 left open by decision.** All seven per-change items
(CHK001–CHK007) pass: every behaviour change names its failing test, its passing outcome and its
migration entry. The failures were all in the supporting layers — evidence recording, one omitted
scope statement, and three unowned obligations.

Code claims spot-checked against the branch while auditing, all confirmed: `CueOutput.py:146`
(`_initialized = False`) and `:154` (`_classify_output_name` before `super().__init__`),
`helpers.py:33-35` (the blanket `except AttributeError`), `helpers.py:102` (`extract_items`),
`registry.py:162-163` (`MediaType`/`RegionType` already bound — FR-011's re-verification holds),
`mapper._spec_for_model:386-391` (the O(bindings) scan T004a extracts), `mapper.py:443`
(`REMOVAL_TARGET = "005"`), and exactly **10** `items()` overrides in `cues/` as R5 states.
`tools/CTimecode.py:451` and `tools/Uuid.py:47` also define `items()`; they are value types and
out of scope — T014's assertion is correctly scoped to `cues/` + `helpers.py` and must not be
widened to all of `src/`.

### Remediated 2026-08-17

| # | Finding | Fix applied |
|---|---|---|
| CHK010 | `Media.duration`'s exclusion from every coercion change was **not in spec.md** — only in `data-model.md` §4's warning box, T037 and T048's hazard note. A reader of FR-007 alone would conclude it should be coerced. (No contradiction: it is already `str` on both paths, so FR-007 was satisfied — but the exclusion is load-bearing and was unstated at the normative level.) | **FR-009b added** to spec.md, stating the exclusion, the `TimecodeType` vs `CTimecodeType` distinction, and why coercing it would change the emitted element for every media document. |
| CHK031 | The four region supply shapes are asserted exhaustive ("every shape they occur in"), but no fallback was specified for a shape matching none of them. An unrecognised shape passed through unchanged is a plain-dict region — **the exact defect BC2 fixes, returning silently and invisibly to the goldens**. | **FR-009a added**: an unrecognised region shape MUST raise, naming the shape received. **T022** gains a fifth test case. |
| CHK024 | SC-003 requires seven demonstrated fail-then-pass pairs "evidenced in the pull request" — a location, but no format. A reviewer could not confirm all seven without trusting a summary, which is what the criterion exists to prevent. | **T044** now carries a fail-then-pass evidence table: one row per landed change — change, test id, before-run output, after-run output. |
| CHK018 | "Fails before" was anchored to "pre-005 code", not to a named commit; `baseline.md` recorded numbers but no SHA. | **T001** now records the pre-005 commit SHA alongside the suite numbers. |
| CHK028 | Under an MVP-only ship (Phases 1–4), T044 as written demanded all seven migration entries when only changes 1, 2 and 6 had landed. | **T044** scoped to one entry per **landed** change, naming the MVP subset (1, 2, 6) explicitly. |
| CHK034 | FR-020/C1 state the no-regeneration rule absolutely, but the "a golden is found to be genuinely wrong" branch had no procedure. | **C1** gains the branch: a golden believed wrong halts the feature and is corrected in its own change, never inside 005. |

### Open — deliberately not remediated

| # | Finding | Severity | Why open |
|---|---|---|---|
| CHK032 | Assumption 7 (the Angular UI tolerates cleared template identifiers) is unvalidated and carries no owner. FR-022 requires the delta be "confirmed harmless to the UI", but **no task owns that confirmation** and no method is given. This is the one change that alters a payload a consumer renders. | **High** | Resolving it needs a decision this repo cannot make alone: either someone verifies against the Angular UI, or FR-022 softens to "measured and recorded" with the assumption inherited by feature 009. **Carry into the PR.** BC3's other evidence (T034, T038, SC-009) is unaffected — the delta will be measured; only the *confirmation* is unowned. |
| CHK011 | No requirement defines post-merge recovery if a behaviour change breaks a consumer. plan.md's commit discipline makes Phase 4 independently revertible, which is a mechanism, not a policy. | **Low** | Arguably out of scope for a feature spec, and FR-027 forbids consumer edits here in any case. Left as-is by decision. |

### Notes on items that pass but are worth a reviewer's attention

- **CHK012** — plan §III and T044 specify before/after plus the consumer-visible consequence,
  which clears the item's bar. But FR-UX-001 says "in the same form 004 established", and 004's
  `migration-map.md` enumerates **consumer call sites by grep across three sibling checkouts**.
  No 005 task owns an equivalent sweep. If the phrase is meant literally, T044 is under-specified.
- **CHK021** — Tasks §Notes attributes "T022/T023 (change 1, 2)" as a pair. The underlying tests
  do separate cleanly (T022 is BC2-only; T023's `ui_properties` per-field-path assertion is
  BC1-only), so attribution survives — but the note's wording invites the conflation the item warns of.
- **CHK017** — the *protocol* is unambiguous (`Unset` = key absent). The per-field `Unset`-or-value
  choices are deliberately deferred to T036's audit with output-neutrality (C1) as the objective
  gate. That is a sound design, not a gap, but it means six classes' defaults are not knowable
  from the spec alone.
- **CHK030** — the invariant is stated (Edge Cases, FR-004a) and the outcome follows determinately
  from FR-015a, since any undeclared key is dropped whatever its name. No test explicitly covers a
  stray key *named* like a runtime attribute; a cheap addition to T013.
