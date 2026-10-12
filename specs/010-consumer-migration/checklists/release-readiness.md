# Cross-Repo Release Readiness Checklist: Consumer migration

**Purpose**: Validate that feature 010's **requirements** are complete, unambiguous, measurable and
internally consistent enough to gate a seven-repository release — before anyone tries to satisfy
them. This is a requirements-quality review, not a test plan: every item asks whether something is
*specified well*, never whether it *works*.
**Created**: 2026-09-03
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [contracts/](../contracts/)
**Depth**: formal release gate · **Audience**: reviewer, at the gate · **Scope**: all seven repositories

**Why this checklist is not a test plan.** The request behind it was phrased as verification
("verified end to end", "proven fixed", "counted not sampled"). Each of those concerns is preserved
below, but **translated**: a verification step can only be executed if the requirement behind it is
written well enough to say what passing means. Where the requirement is not, that is the finding.

---

## Requirement Completeness

- [x] CHK001 **RESOLVED 2026-09-04.** FR-070 now names the **discovery four** (`cuems-common`'s Avahi service files) and FR-070a labels both groups so neither substitutes for the other [Resolved, Spec §FR-070, §FR-070a]
- [x] CHK002 **RESOLVED 2026-09-03.** The baseline is this repository's **golden corpus**, not a captured fixture — the goldens were deliberately re-cut during this rebuild and already carry `doc_version="2"` and the wrapped duration, so they are the behaviour consumers must produce rather than a record of what preceded it. A fresh capture would have pinned the wrong side of a deliberate change. Additionally, the payload is **not the interface**: consumers implement object-to-object, the projection appearing once at the UI edge [Resolved, Spec §FR-013a, §FR-013b, §SC-005a, §SC-005b]
- [x] CHK003 **RESOLVED 2026-09-03.** The fixups are **split by responsibility**, on the test of whether a fixup needs anything beyond the document: dangling-reference nulling becomes a **library** semantic rule (repairable, reported) and the editor's copy is deleted; duration-from-database **stays** in the editor as an object-level operation, since the library has no database and must not gain one. FR-043c adds the missing property — both must still detect what they detect today, measured case by case [Resolved, Spec §FR-043–§FR-043d, §SC-010a, §SC-010b]
- [x] CHK004 **RESOLVED 2026-09-04.** FR-088f adds the consumer half — forms checked against **every** enumeration and default across all six schemas, not FR-086's three sites; SC-003 remains the library half and neither substitutes for the other [Resolved, Spec §FR-088f]
- [x] CHK005 **RESOLVED 2026-09-04.** FR-100a specifies the trigger: the decision owner and the observable conditions that qualify [Resolved, Spec §FR-100a]
- [x] CHK006 **RESOLVED 2026-09-04.** **Decided, not specified.** A migration failing mid-flight is **fixed forward**, not rolled back — an unfinished migration has not been released, so there is nothing to roll back to. Recorded in Out of Scope [Resolved, Spec §"Out of Scope"]
- [x] CHK007 **RESOLVED 2026-09-04.** FR-049d specifies the recovery routes: restore from a conversion backup, correct the named field by hand, or remove the document [Resolved, Spec §FR-049d]
- [x] CHK008 **RESOLVED 2026-09-04.** Covered by FR-103's checkable boundary plus SC-017b's partial-state criterion; the conversion's idempotent guard makes a partial library answer correctly per document [Resolved, Spec §FR-103, §SC-017b]
- [x] CHK009 **RESOLVED 2026-09-04.** FR-102a promotes it from a measurement note to a requirement: a converted library approximately doubles on disk until reclaimed, stated **before** the conversion runs [Resolved, Spec §FR-102a]
- [x] CHK010 **RESOLVED 2026-09-04.** FR-036 gains a pass criterion — named as one of three ordering constraints, the safe order stated, and a converted-controller deploy exercised during the cluster verification [Resolved, Spec §FR-036]

## Requirement Clarity & Measurability

- [ ] CHK011 Is **"hundreds"** quantified, or is a design-and-verify target stated as a range a reviewer can check? [Clarity, Spec §FR-095c]
- [x] CHK012 **RESOLVED 2026-09-04.** Replaced with an observable condition: at least one show loaded from the converted library and run to completion on the cluster. Propagated to plan, research, tasks and the release-gate contract [Resolved, Plan, Research §R5, §FR-102]
- [x] CHK013 **RESOLVED 2026-09-04.** SC-007's denominator is now **defined**: every call site named in 007's and 008's migration guides plus anything a fresh search adds, with the search's method and date recorded [Resolved, Spec §SC-007]
- [ ] CHK014 Is **"the editor starts"** defined measurably and distinguished from "the suite is green"? [Measurability, Spec §SC-002]
- [x] CHK015 **RESOLVED 2026-09-04.** Quantified — the public path's per-schema cost must be within **110%** of the internal path's for the same schema [Resolved, Spec §FR-PERF-001]
- [x] CHK016 **RESOLVED 2026-09-04.** FR-070b makes the counting method normative: the exact command and the paths it covers, recorded with the count [Resolved, Spec §FR-070b]
- [x] CHK017 **RESOLVED 2026-09-04.** FR-025 defines "tested": a test asserts the public equivalent returns a result equal to the internal import's for the same input [Resolved, Spec §FR-025]
- [x] CHK018 **RESOLVED 2026-09-04.** FR-047 makes it checkable: after the change the editor has exactly **one** message-dispatch mechanism and the new messages travel it [Resolved, Spec §FR-047]
- [ ] CHK019 Can "**no half-renamed intermediate state shipped**" be objectively evaluated at review time, before a release exists to inspect? [Measurability, Spec §FR-060]
- [ ] CHK020 Is the pass criterion for the discovery check defined — what "discovered **with its role**" requires observing? [Clarity, Spec §FR-062]

## Requirement Consistency & Conflicts

- [x] CHK021 **RESOLVED 2026-09-04.** FR-072 now enumerates all sixteen sites as `<path>:<start_line>[-<end_line>]`, satisfying FR-071. The inherited audit numbers were **stale** and were re-measured 2026-09-04 [Resolved, Spec §FR-072]
- [x] CHK022 **RESOLVED 2026-09-04.** FR-070a requires both groups labelled wherever the count is described [Resolved, Spec §FR-070a]
- [x] CHK023 **RESOLVED 2026-09-04.** Resolved by decision: `cuems-editor` **acquires packaging** in this feature (FR-090a), so FR-091's four are real and now named rather than counted [Resolved, Spec §FR-090a, §FR-091]
- [ ] CHK024 Are the payload constraint's statements consistent **everywhere it appears** — spec, contract and plan — as an enumerated two-delta rather than unconditional byte-identity? [Consistency, Spec §FR-010–FR-013]
- [ ] CHK025 Is the distinction between the **document-version marker** and the **payload version** stated wherever either appears, so a reader cannot merge them? [Consistency, Spec §FR-012, §FR-106]
- [ ] CHK026 Do FR-026's prohibition on descriptor growth and FR-022a's mandated addition read as a **stated exception** rather than a contradiction? [Consistency, Spec §FR-026, §FR-022b]
- [ ] CHK027 Are the three cutover classes' release strategies stated **without collapsing** into one story — two admitting no dual state, one admitting it? [Consistency, Spec §FR-097]
- [ ] CHK028 Is the claim that `cuems-nodeconf`'s node model is "done, confirm not redo" consistent with the prohibition on consumer-side node-model tests? [Consistency, Spec §FR-003, §FR-069]

## Scenario Coverage

- [ ] CHK029 Are requirements defined for all **three load outcomes** as consumer-visible behaviour — clean, repaired, unrepairable — rather than only the repaired one? [Coverage, Spec §FR-048–FR-049c]
- [ ] CHK030 Are requirements defined for the **repeat** case: a repaired-but-unsaved document reporting the same repair on every open? [Coverage, Spec §FR-048c]
- [ ] CHK031 Are requirements defined for both **upgrade orders** — nodes-first and controller-first — including which is prevented and which merely documented? [Coverage, Spec §FR-096]
- [ ] CHK032 Are requirements defined for the **pre-conversion and post-conversion** rollback paths as distinct procedures with a checkable boundary between them? [Coverage, Spec §FR-100–FR-103]
- [ ] CHK033 Are requirements defined for `repair_durations.py`'s primary purpose — reading **deliberately corrupt** documents — surviving the strict read path? [Coverage, Spec §FR-045]
- [ ] CHK034 Are requirements defined for all **five** show-parsing call sites, including the fifth outside the project store that the first audit pass missed? [Coverage, Spec §FR-041]
- [ ] CHK035 Are requirements defined for the config-domain UI's **existing** behaviour surviving the port — adopt, unadopt, and the mixer screens' reads — rather than only for the new form renderer? [Coverage, Spec §FR-088]

## Edge Case Coverage

- [ ] CHK036 Are requirements defined for a **cached UI bundle** — the one way a UI can lag an editor that serves it? [Edge Case, Spec §FR-108]
- [x] CHK037 **RESOLVED 2026-09-04.** FR-029e promotes the re-run from a plan note to a requirement: the census records its own date and the last consumer merge it postdates [Resolved, Spec §FR-029e]
- [ ] CHK038 Are requirements defined for a defect discovered **after backups were reclaimed**, when the post-conversion rollback's only protection is gone? [Edge Case, Spec §FR-102]
- [ ] CHK039 Are requirements defined for the two owning repositories of the discovery vocabulary **merging at different times**? [Edge Case, Spec §FR-060]
- [ ] CHK040 Is the "not shipped" exemption's **different lifetime** from the "detection code" exemption stated, so a future sweep does not treat a stale fixture as permanent? [Edge Case, Spec §FR-073a]

## Non-Functional Requirements

- [ ] CHK041 Is the performance baseline stated as a **per-test** figure with its measurement date and commit, so a grown suite is not read as a regression? [Measurability, Spec §FR-PERF-001]
- [x] CHK042 **RESOLVED 2026-09-04.** **The finding was correct and the spec was wrong.** FR-PERF-001 and SC-PERF-001 both mandated 007's ≤10.20 ms cap, which 008 already recorded as exceeded. Both now measure against 008's post-landing 10.14–10.49 ms and record the position as inherited [Resolved, Spec §FR-PERF-001, §SC-PERF-001]
- [ ] CHK043 Is the requirement that eager descriptor construction is a **design error rather than a budget overrun** stated normatively, not only as commentary? [Clarity, Spec §FR-PERF-001]

## Dependencies & Assumptions

- [ ] CHK044 Is the assumption that the inherited 007/008 surfaces exist stated as something to **verify once** rather than assumed per story? [Assumption, Spec §"Assumptions" 3]
- [ ] CHK045 Is the dependency on an **unmerged sibling branch** (the node-identity work landed but unreleased) documented with its consequence for the release gate? [Dependency, Spec §"Dependencies"]
- [ ] CHK046 Are the two repositories with **no meaningful test coverage** identified as places where "each PR carries its own green suite" currently costs nothing? [Assumption, Spec §"Edge Cases"]
- [ ] CHK047 Is the assumption that a green suite is **not evidence** for the semantically-wrong caller class stated as a normative constraint rather than advice? [Assumption, Spec §FR-004, §SC-QUALITY-001]

## Traceability

- [ ] CHK048 Does every consumer-repository obligation trace to a numbered requirement, so no repository's work exists only in prose? [Traceability, Plan §"Requirement traceability"]
- [ ] CHK049 Are the requirements that discharge in a **different wave** from where they were found marked as such, rather than appearing unassigned? [Traceability, Plan §"Requirement traceability"]
- [ ] CHK050 Is a requirement defined that the migration guide state **which obligation landed in which repository**, given seven flows produce seven task lists and no single view? [Traceability, Spec §FR-UX-004]

---

## Notes

**Status after the 2026-09-04 analysis pass: 21 items resolved, 29 confirmed passing, 0 open.**

The 29 unticked items are **not outstanding work** — they were evaluated against the artifacts and
the requirement each questions was found adequate. They stay unticked because a gate checklist
records what it examined, not only what it changed; ticking them would erase the distinction
between "checked and fine" and "fixed". CHK011 is the one deliberate accept: "hundreds" stays
unquantified, mitigated by FR-095d, which says what happens if a real library proves an order of
magnitude larger.

**Twenty-one items were findings, and all are now closed.** The one that mattered most was found by
this checklist against work the same author had just planned:

| Item | Finding and resolution |
|---|---|
| **CHK042** | 🔴 **The spec mandated a budget that was already unmet.** FR-PERF-001 and SC-PERF-001 both required `network_map` load to stay within 007's ≤10.20 ms cap, while 008 had measured 10.14–10.49 ms and recorded it *exceeded-or-marginal*. The plan had the correction; the spec contradicted it, in the same sentence that correctly cited 008's figure for engine load. A Constitution IV conflict — resolved by measuring against 008's figure and recording the position as inherited |
| CHK001 / CHK022 | Two groups of four in one subsection; FR-070's were never enumerated. FR-070 now names the discovery four, FR-070a requires both groups labelled |
| CHK021 | FR-071 demanded site-by-site; FR-072 described by category. Now enumerated as `<path>:<start_line>[-<end_line>]` — and **the inherited audit line numbers were stale**, re-measured 2026-09-04 |
| CHK023 | FR-091's four edges against an editor with no packaging. Resolved by decision: the editor acquires packaging (FR-090a), and the four are now named rather than counted |
| CHK013 | SC-007's equal-counts test had no denominator. Now defined as 007's and 008's guides plus a fresh search, with method and date recorded |
| CHK004 | Nothing required forms checked against every enumeration and default. FR-088f adds the consumer half; SC-003 remains the library half |
| CHK002 / CHK003 | Resolved 2026-09-03 — the golden-corpus baseline, and the fixup split by responsibility |
| CHK005 / CHK007 | Rollback trigger (FR-100a) and operator recovery action (FR-049d) specified |
| CHK006 | **Decided rather than specified**: a migration failing mid-flight is fixed forward, not rolled back — an unfinished migration has not been released, so there is nothing to roll back to |
| CHK008–012, 015–018, 037 | Pass criteria, thresholds and normative method supplied — FR-036, FR-102a, FR-070b, FR-029e, FR-025, FR-047, FR-PERF-001's 110% threshold, and "one full show cycle" replaced with an observable condition |

**What passes.** The payload two-delta constraint, the three-outcome load model, the census gate,
the discovery cutover's atomicity, the exempt set's two reasons, and the performance budgets'
provenance are all specified to a standard these items only confirm. They are included because a
gate checklist that lists only failures cannot be used as a gate.

**What this checklist deliberately does not do.** It does not check whether any of it works. Every
"verified end to end" concern in the request became a question about whether the requirement behind
it says what passing means — because a verification step whose requirement is vague produces a
green tick and no information.
