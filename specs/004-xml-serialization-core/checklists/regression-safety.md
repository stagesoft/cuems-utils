# Byte-Identity & Regression Safety Checklist: Schema-derived XML serialization core

**Purpose**: Validate that every guarantee in the spec is written precisely enough to be
verified — for a pure refactor whose entire acceptance case rests on byte-equality against
pre-refactor goldens. This is a **requirements-quality** review, not a test plan: each item
asks whether a guarantee is stated well enough that its verification step is unambiguous.
**Created**: 2026-08-11
**Feature**: [spec.md](../spec.md) | **Depth**: release gate | **Audience**: reviewer (PR)
**Scope**: all guarantees in the spec as it now stands, including the four clarified
additions (shims, log exclusion, corpus, failure paths), plus cross-artifact consistency
against [plan.md](../plan.md), [research.md](../research.md), [contracts/byte-identity.md](../contracts/byte-identity.md) and [tasks.md](../tasks.md).

---

## Requirement Completeness — the byte-identity family

- [ ] CHK001 Is "byte-identical written XML" defined with an enumerated list of the properties it covers, rather than left to the reader? [Completeness, Spec §FR-010]
- [x] CHK002 Are requirements defined for how non-ASCII content is encoded on write (literal UTF-8 vs character references), given that byte-equality is sensitive to it? [Gap] ✅ **RESOLVED 2026-08-11**: UTF-8, literal bytes, never character references — FR-010a.
- [ ] CHK003 Is the requirement explicit that the serializer itself is frozen, and is the consequence of changing it stated? [Completeness, Research §R10]
- [ ] CHK004 Are byte-identity requirements stated for **both** reader configurations, including the requirement that their existing differences are preserved? [Completeness, Spec §FR-013]
- [ ] CHK005 Is the requirement clear that the leaked `schemaLocation` key must still be **present** in this feature, rather than removed as an obvious improvement? [Clarity, Spec §FR-011, Contract §C2]
- [ ] CHK006 Are requirements defined for the object-returning read path (`read_to_objects`), or is the guarantee limited to the raw dict? [Gap, Spec §FR-011]
- [ ] CHK007 Is the set of documents the guarantee applies to bounded, with an explicit statement that anything outside it is uncovered? [Completeness, Spec §Assumptions 1]

## Requirement Clarity & Measurability

- [x] CHK008 Is the **comparison method** for read dicts specified, and does the spec state whether **key order** is part of the guarantee? Two dicts with identical keys in different order compare equal but do not serialize identically. [Ambiguity, Spec §FR-011, Contract §C2] ✅ **RESOLVED 2026-08-11**: comparison is `json.dumps` output; key insertion order is inside the guarantee — FR-011a.
- [x] CHK009 Is the dict comparison specified in a way that is well-defined for values that are not JSON-serializable? [Clarity, Contract §C2] ✅ **RESOLVED 2026-08-11**: the dict must remain `json.dumps`-compatible — FR-011a.
- [ ] CHK010 Can "byte-identical" be objectively verified for every corpus document, or does any document require a judgement call? [Measurability, Spec §FR-010]
- [ ] CHK011 Is "provenance" defined with the specific fields required, or left to the implementer? [Clarity, Spec §FR-022a]
- [x] CHK012 Is the "removal release" that deprecation warnings must name specified as an actual version number, rather than as an internal feature id a consumer cannot interpret? [Clarity, Spec §FR-027, §FR-030] ✅ **RESOLVED 2026-08-11**: removal release is `v0.1.1`; `v0.1.0` keeps the warnings — FR-027a.
- [x] CHK013 Is "at most one INFO record per document" unambiguous for nested reads, where one file load may traverse many contained documents? [Clarity, Spec §FR-033] ✅ **RESOLVED 2026-08-11**: INFO is declared at the XML file access level; internal elements/objects log at DEBUG or lower — FR-033.

## Requirement Consistency — within spec.md

- [x] CHK014 **Do FR-001 and the `xs:all` ordering rule conflict?** FR-001 forbids any path that determines order by "alphabetical sorting", while research R2 requires exactly a sorted-key tie-break for `CuemsScript` and `DmxSceneType` to preserve bytes. [**Conflict**, Spec §FR-001, Research §R2] ✅ **RESOLVED 2026-08-11**: FR-001 amended into two schema-driven branches; sorted-key ordering is permitted only for order-free models — FR-001, FR-001a.
- [x] CHK015 **Does SC-004 restate the same conflict?** It asserts zero live paths determine order by alphabetical sorting, which the `xs:all` branch necessarily does. [**Conflict**, Spec §SC-004, Research §R2] ✅ **RESOLVED 2026-08-11**: SC-004 amended to match the FR-001 branches.
- [x] CHK016 Do FR-033 ("at most one INFO record per document") and SC-014 ("constant, single-digit number of INFO records") state the same budget, or two different ones? [Consistency, Spec §FR-033, §SC-014] ✅ **RESOLVED 2026-08-11**: both now expressed as "INFO scales with files touched, not content" — FR-033, SC-014.
- [x] CHK017 Does FR-029 (no internal caller of a shimmed symbol) hold for `CuemsParser`, which becomes a delegating facade that consumers still call? Is a delegating shim's warning per-import or per-call? [Ambiguity, Spec §FR-029, Tasks §T048] ✅ **RESOLVED 2026-08-11 (analyze)**: two parts. (i) Warnings are per-call with correct `stacklevel` — FR-027b, and T026/T027/T044 were corrected from "warning on import", which cannot satisfy it. (ii) FR-029 holds because `CuemsParser` is **not** a shimmed symbol: measured, it is already library-internal and is `cuems-editor`'s primary JSON→object path at five call sites, so it becomes a **supported, non-warning** delegating facade — Assumption 3a, FR-026d.
- [x] CHK018 Are FR-002 ("MUST NOT exist anywhere in the engine") and Assumption 3a (frozen legacy implementations retained) reconciled, so a reviewer knows which files the prohibition covers? [Consistency, Spec §FR-002, §Assumptions 3a] ✅ **RESOLVED 2026-08-11 (analyze)**: Assumption 3a now names the frozen symbols exhaustively (`GenericParser`, `GenericDict`, `str_to_value`, `STRING_TYPED_KEYS`, `VALUE_TYPES`, the `*Parser` / `*XmlBuilder` families) and names `CuemsParser` as the one exclusion. SC-004 already excludes frozen shim code; T049 cites the ordering hack **by symbol** rather than by line number, since the rename shifts lines.
- [ ] CHK019 Is FR-003's "not reachable from any live path" testable as written, and is "live path" defined? [Measurability, Spec §FR-003]

## Requirement Consistency — across artifacts

- [x] CHK020 **Does SC-003 conflict with contract C3?** SC-003 requires load-save byte-idempotence; research R10 measured `save(load(x)) == x` as false for hand-authored files, and C3 silently substitutes a different property. The spec has not been amended. [**Conflict**, Spec §SC-003, Contract §C3, Research §R10] ✅ **RESOLVED 2026-08-11**: SC-003 restated as byte-stability (true, matches C3) and SC-003a added for semantic round-trip `load(save(x)) == x` (measured, holds). Object equality is additive — it is blind to `xs:all` reordering, so it cannot replace C1.
- [x] CHK021 **Does SC-013 conflict with FR-022b?** SC-013 requires the 12 consumer call sites to work unmodified, while FR-022b requires the suite to pass with no sibling repository present. Is the verification method for SC-013 defined? [**Conflict**, Spec §SC-013, §FR-022b] ✅ **RESOLVED 2026-08-11**: two-layer verification (in-repo shim tests + release-time inventory review) removes the conflict; an unsupportable call site becomes a declared breaking change — FR-030a/b/c.
- [x] CHK022 Does the spec record the plan's four design corrections (R2–R5), or do they exist only in planning artifacts an implementer may not read? [Traceability, Plan §Design corrections] ✅ **RESOLVED 2026-08-11 (analyze)**: R2 is in the spec (FR-001/FR-001a) and R10 is now in both SC-003 and the restated **FR-012**, which had kept the disproved wording. R3/R4/R5 remain design-level in `research.md` / `data-model.md`, and the plan now states why that is sufficient: they constrain implementation, not acceptance. The plan's stale claim that "SC-003 is the one correction not yet written back" is removed.
- [ ] CHK023 Are the registry-totality requirements consistent between FR-007 (explicit generic bindings) and the plan's open item to enumerate them by instrumentation? [Consistency, Spec §FR-007, Plan §Open items]
- [x] CHK024 Is every contract C1–C11 traceable to at least one FR or SC, and every byte-identity FR traceable to a contract? [Traceability, Contract §C1–C11] ✅ **RESOLVED 2026-08-11 (analyze)**: verified in both directions; every FR/SC cited in `tasks.md`, `plan.md` and `byte-identity.md` resolves to a definition in `spec.md`. **C11 added** for the FR-026d declared breaking change (SC-017) — the one contract that asserts a change rather than its absence.

## Acceptance Criteria Quality

- [ ] CHK025 Is the "written first, passes unchanged" property of the chain test stated as an objectively checkable condition rather than a procedural intention? [Measurability, Spec §FR-019, §SC-TEST-001]
- [ ] CHK026 Does the spec define what evidence demonstrates the chain test was not edited? [Clarity, Spec §SC-TEST-001]
- [ ] CHK027 Are the fail-before-pass expectations stated for the assertions that are genuinely new, and is it acknowledged that byte-identity contracts pass by construction instead? [Completeness, Plan §Constitution Check II]
- [ ] CHK028 Is the coherence test's reach defined, so its scope cannot be silently over- or under-read? [Clarity, Spec §FR-020]
- [x] CHK029 Are performance budgets stated with a measurement method — run count, machine, tolerance for variance — given that 10% of a ~7.4s suite is within noise? [Measurability, Spec §SC-PERF-001] ✅ **RESOLVED 2026-08-11 (analyze)**: SC-PERF-001 now specifies best-of-5 runs on one recorded machine and interpreter, comparing best-of-5 to best-of-5. It was also **split**, because a 10% rule on the total contradicted SC-TEST-002: the 10% binds the write benchmark and the pre-existing 557 tests re-run as a subset (ids recorded at T001), while the new corpus suite carries an absolute budget fixed at T020.
- [ ] CHK030 Is SC-PERF-002 ("derivations do not grow with object count") expressed as something countable? [Measurability, Spec §SC-PERF-002]

## Scenario Coverage

- [ ] CHK031 Are requirements defined for the primary flow (XML load and save) **and** the alternate flow (the editor's JSON payload path, which never touches a schema)? [Coverage, Spec §FR-005]
- [ ] CHK032 Are exception-flow requirements defined for documents the current code rejects, including at least one invalid document in the corpus? [Coverage, Spec §FR-015]
- [ ] CHK033 Is the preservation requirement for swallowed serialization failures specific about **what** is preserved — that it does not raise, that surrounding data is unaffected, and whether log text is in or out of scope given FR-032? [Ambiguity, Spec §FR-015a, §FR-032]
- [ ] CHK034 Are requirements stated for swallowed failures **other** than the known DMX case, should the implementation uncover them? [Coverage, Spec §Edge Cases]
- [ ] CHK035 Are recovery requirements defined — what happens if the swap lands and a byte-identity failure is found later? Is reverting the only stated path? [Gap, Recovery Flow]
- [x] CHK036 Are requirements defined for legitimately **adding** a corpus document after goldens exist, given FR-021's absolute prohibition on regeneration? [Gap, Spec §FR-021] ✅ **RESOLVED 2026-08-11**: new corpus documents are permitted and auto-recognised; the rule binds existing goldens only — FR-021, SC-016.

## Edge Case Coverage

- [ ] CHK037 Are requirements defined for the two order-free (`xs:all`) content models, and are both instances named so neither is missed? [Coverage, Research §R2]
- [ ] CHK038 Are requirements defined for the anonymous root types, which cannot be bound by type name? [Coverage, Research §R3]
- [ ] CHK039 Are requirements defined for the schema-type name collision between `script.xsd` and `outputs.xsd`, and is the resulting constraint stated as mandatory rather than stylistic? [Coverage, Research §R4]
- [ ] CHK040 Are requirements defined for the element/attribute name collision on `universe_num`, including that the current ambiguous behaviour is preserved rather than resolved? [Coverage, Research §R7]
- [ ] CHK041 Are requirements defined for cyclic content models terminating during derivation? [Coverage, Research §R8]
- [ ] CHK042 Are requirements defined for optional elements — absent when unset, present when set — matching pre-refactor output in both states? [Coverage, Spec §Edge Cases]
- [ ] CHK043 Are wildcard-content requirements specific enough to be verified, given that no type, order or cardinality is derivable for them? [Measurability, Spec §FR-009]

## Non-Functional Requirements

- [ ] CHK044 Is the log-output exclusion stated as a deliberate, bounded carve-out, with its own positive requirements rather than merely an absence of guarantee? [Completeness, Spec §FR-032–§FR-034]
- [ ] CHK045 Is the requirement that log records carry no field values stated in a verifiable form, and is its side effect on show content in log files acknowledged? [Measurability, Spec §FR-033]
- [ ] CHK046 Are the deprecation-warning requirements specific enough that a consumer can act on a warning without reading the source? [Clarity, Spec §FR-028]

## Dependencies & Assumptions

- [ ] CHK047 Is the dependency on `xmlschema`'s content-model ordering behaviour documented as an assumption with a stated protection against silent change on upgrade? [Assumption, Research §R11, Contract §C10]
- [ ] CHK048 Is the one-time cross-repo read access for corpus vendoring recorded as a dependency, distinct from the ongoing self-containment requirement? [Dependency, Plan §Dependencies]
- [ ] CHK049 Is the assumption that the pre-refactor baseline is green stated as a precondition, with the baseline itself recorded somewhere durable? [Assumption, Plan §Technical Context]
- [ ] CHK050 Are the deferred behaviour-changing fixes enumerated with the reason each cannot land here, so scope creep during implementation is detectable? [Completeness, Spec §Out of Scope]

---

## Notes

- Check items off as `[x]`; record findings inline.
- **Resolved 2026-08-11**: CHK002, CHK008, CHK009, CHK012, CHK017 and CHK036 were answered
  and the answers written back into `spec.md` (FR-010a, FR-011a, FR-021, FR-027a, FR-027b,
  SC-016), `contracts/byte-identity.md` (C1, C2, C9) and `tasks.md` (T008, T009, T013,
  T014, T025, T030).
- **Round 2, 2026-08-11**: FR-001 amended (CHK014/CHK015), the breaking-change declaration
  rule added (CHK021), and INFO logging altitude settled (CHK013/CHK016). Written back into
  `spec.md`, `contracts/byte-identity.md` (C6, C9) and `tasks.md` (T031a, T031b, T039, T060,
  T061).
- **Round 3, 2026-08-11**: CHK020 closed. SC-003 restated as byte-stability; **SC-003a**
  added for the semantic round-trip. All four flagged conflicts are now resolved.
- **New defect found while measuring**: written `xsi:schemaLocation` embeds the writing
  machine's **absolute path** to the `.xsd`, so goldens are machine-dependent. Recorded as
  **F24**, normalized for comparison only (FR-010b), fix deferred to 006.
- **Round 4, 2026-08-11 — `/speckit.analyze`**: CHK017, CHK018, CHK022, CHK024 and CHK029
  closed. Two conflicts the earlier rounds missed were found and fixed in `spec.md`:
  **FR-012** still asserted the `save(load(x)) == x` idempotence that R10 disproved and
  CHK020 had corrected only in SC-003; and **FR-023a–d** (read compatibility) collided
  with **FR-023** (no `.xsd` edits), so they were renumbered **FR-035/FR-035a–d**.
  **SC-PERF-001** was split, since a 10% wall-time rule on the whole suite could not
  coexist with SC-TEST-002's requirement that the suite grow. Four coverage gaps closed
  with new tasks: SC-010 (T036a), FR-024/SC-018 (T019a), FR-035c/SC-019 (T066b), and the
  new SC-017 (T049a).
- **One breaking change accepted in round 4**: `cuems-nodeconf`'s F8 module-globals
  handler injection cannot survive FR-007's explicit registry, and no shim can preserve it.
  Declared as **FR-026d** and asserted by the new contract **C11**. **The fix is carried
  by feature 007**, not by 004, under FR-030b's new scheduling clause: it must target an API
  that is internal in 004, public in 006 and absorbing the node model in 007, so writing it
  now would be rewritten twice — and `cuems-nodeconf` is not shipping against this release.
  004 therefore edits no repository but this one, which keeps FR-022b and SC-015 true
  without qualification. `feat/nodeconf-reenable` now feeds feature 007 instead of gating
  it. This is the
  first item in this feature that is a deliberate behaviour change rather than a
  preservation, so it is pinned by a test precisely because nothing else would catch it:
  the imports still resolve and the injection still executes, only its effect is gone.
- **Flagged conflicts are findings**, not open questions — each is a
  place where two documents in this feature currently disagree. They should be resolved by
  amending `spec.md` before `/speckit.implement`, not during it.
- Items referencing `Research §Rn` check whether a measured finding made it into the
  *requirements*. A finding that lives only in `research.md` is not a requirement, and an
  implementer following `spec.md` alone will not honour it.
