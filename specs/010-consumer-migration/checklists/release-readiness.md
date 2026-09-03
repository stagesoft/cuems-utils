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

- [ ] CHK001 Are the **four files feature 007 excluded from its own count** enumerated anywhere in the spec? FR-073's four non-shipped files are named individually; FR-070's four are referenced but never listed [Completeness, Spec §FR-070]
- [x] CHK002 **RESOLVED 2026-09-03.** The baseline is this repository's **golden corpus**, not a captured fixture — the goldens were deliberately re-cut during this rebuild and already carry `doc_version="2"` and the wrapped duration, so they are the behaviour consumers must produce rather than a record of what preceded it. A fresh capture would have pinned the wrong side of a deliberate change. Additionally, the payload is **not the interface**: consumers implement object-to-object, the projection appearing once at the UI edge [Resolved, Spec §FR-013a, §FR-013b, §SC-005a, §SC-005b]
- [x] CHK003 **RESOLVED 2026-09-03.** The fixups are **split by responsibility**, on the test of whether a fixup needs anything beyond the document: dangling-reference nulling becomes a **library** semantic rule (repairable, reported) and the editor's copy is deleted; duration-from-database **stays** in the editor as an object-level operation, since the library has no database and must not gain one. FR-043c adds the missing property — both must still detect what they detect today, measured case by case [Resolved, Spec §FR-043–§FR-043d, §SC-010a, §SC-010b]
- [ ] CHK004 Are requirements defined for checking descriptor-driven forms against **every enumeration and every default the six schemas declare**, or only against the three named value-reading sites? [Gap, Spec §FR-086, §SC-003]
- [ ] CHK005 Is a requirement defined for **who decides a rollback is needed**, and on what signal? FR-100–FR-104 specify the procedures but not the trigger [Gap, Recovery]
- [ ] CHK006 Are requirements defined for the case where a **wave-4 verification itself fails** — the cluster does not come back, or the conversion aborts mid-library? [Gap, Exception Flow]
- [ ] CHK007 Is an operator's **recovery action** specified for meeting an unrepairable document, beyond the guide recording that the outcome exists? [Gap, Spec §FR-049c]
- [ ] CHK008 Are requirements defined for what a **partially converted** library reports when the rollback boundary is queried? [Coverage, Spec §FR-103]
- [ ] CHK009 Are the **backup storage implications** of conversion specified as a requirement, given backups sit beside documents and are never auto-reclaimed? [Completeness, Spec §FR-102]
- [ ] CHK010 Is the deploy-path version exposure stated as a **requirement with a pass criterion**, or only as something the rollout plan must mention? [Measurability, Spec §FR-036, §FR-096]

## Requirement Clarity & Measurability

- [ ] CHK011 Is **"hundreds"** quantified, or is a design-and-verify target stated as a range a reviewer can check? [Clarity, Spec §FR-095c]
- [ ] CHK012 Is **"one full show cycle"** — the earliest backup-reclamation moment — defined in terms a reader outside the domain can apply? [Ambiguity, Plan §"Data migration and rollout"]
- [ ] CHK013 Does SC-007 define a **completeness criterion for callers *found***? Equal counts of callers-found and tests-added is satisfiable by finding one caller and writing one test [Measurability, Spec §SC-007]
- [ ] CHK014 Is **"the editor starts"** defined measurably and distinguished from "the suite is green"? [Measurability, Spec §SC-002]
- [ ] CHK015 Is **"no measurable cost"** for publishing the descriptor expressed as a threshold, or left to a reviewer's judgement? [Measurability, Spec §FR-PERF-001]
- [ ] CHK016 Is **"counted rather than reviewed"** operationalised — is the counting command or method specified, so two people counting get the same number? [Clarity, Spec §FR-070]
- [ ] CHK017 Are the criteria for a "**named, tested public equivalent**" defined, so an equivalent that merely resolves is distinguishable from one that preserves behaviour? [Clarity, Spec §FR-025]
- [ ] CHK018 Is **"generalising the existing message pair rather than inventing an unrelated one"** stated in checkable terms? [Measurability, Spec §FR-047, §FR-088b]
- [ ] CHK019 Can "**no half-renamed intermediate state shipped**" be objectively evaluated at review time, before a release exists to inspect? [Measurability, Spec §FR-060]
- [ ] CHK020 Is the pass criterion for the discovery check defined — what "discovered **with its role**" requires observing? [Clarity, Spec §FR-062]

## Requirement Consistency & Conflicts

- [ ] CHK021 Does FR-071's demand for an exempt set "**listed site by site rather than described by category**" conflict with FR-072, which describes this repository's sixteen occurrences by category and module rather than by file and line? [Conflict, Spec §FR-071, §FR-072]
- [ ] CHK022 Do the **two groups of four** in one subsection risk conflation — FR-070's four (counted, in scope) and FR-073's four (exempt, out of scope) — given neither is labelled to distinguish it from the other? [Ambiguity, Spec §FR-070, §FR-073]
- [ ] CHK023 Is FR-091's "**four package edges**" consistent with the measured fact that `cuems-editor` has no packaging at all? Either the editor is one of the four and needs packaging first, or the count names a different set [Conflict, Spec §FR-091, §FR-108, Plan §"Technical Context"]
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
- [ ] CHK037 Are requirements defined for a consumer that **regresses between merge and removal**, reintroducing a deprecated import after the census passed? [Edge Case, Spec §FR-029]
- [ ] CHK038 Are requirements defined for a defect discovered **after backups were reclaimed**, when the post-conversion rollback's only protection is gone? [Edge Case, Spec §FR-102]
- [ ] CHK039 Are requirements defined for the two owning repositories of the discovery vocabulary **merging at different times**? [Edge Case, Spec §FR-060]
- [ ] CHK040 Is the "not shipped" exemption's **different lifetime** from the "detection code" exemption stated, so a future sweep does not treat a stale fixture as permanent? [Edge Case, Spec §FR-073a]

## Non-Functional Requirements

- [ ] CHK041 Is the performance baseline stated as a **per-test** figure with its measurement date and commit, so a grown suite is not read as a regression? [Measurability, Spec §FR-PERF-001]
- [ ] CHK042 Is the `network_map` budget stated against **008's post-landing figure** rather than 007's cap, and is its already-marginal position recorded rather than restated as passing? [Consistency, Spec §FR-PERF-001, Research §R6]
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

**Ten items are known findings, not open questions.** They were surfaced by grounding this
checklist against the spec text rather than against memory, and each names a specific weakness:

| Item | Finding |
|---|---|
| CHK001 / CHK022 | **Two different groups of four** sit in one subsection — FR-070's (counted, in scope: the files 007 excluded) and FR-073's (exempt: non-shipped `dev/` fixtures). Only the second group is enumerated. A reader who conflates them either counts exempt files or exempts counted ones |
| CHK002 | ✅ **Resolved.** The baseline is the golden corpus — already re-cut, reviewed, versioned and checksummed. The finding was right that no baseline was named; the fix was not the one the item proposed, because capturing "today's payload" would have pinned the pre-rebuild shape, which is precisely what 008 changed on purpose |
| CHK003 | ✅ **Resolved.** FR-043c now requires detection equivalence, measured case by case. The split that came with it is the part worth noting: "make the fixups the library's responsibility" turns out to move only one of the two — dangling references need just the document, while the duration correction needs the editor's database, which the library must not acquire |
| CHK004 | Nothing requires the UI's descriptor-driven forms be checked against **every** enumeration and default; FR-086 reaches only the three named value-reading sites |
| CHK013 | SC-007's equal-counts test has **no completeness criterion for the denominator**. Find one caller, write one test, counts are equal |
| CHK021 | FR-071 demands site-by-site enumeration; FR-072 then describes this repository's sixteen occurrences **by category** |
| CHK023 | FR-091 says four package edges; `cuems-editor` has **no `debian/` directory**, so the set of four is either wrong or presumes packaging that does not exist |
| CHK005 / CHK006 / CHK007 | Three **recovery-path gaps**: no rollback trigger, no requirement for a failed wave-4 verification, no operator recovery action for an unrepairable document |

**What passes.** The payload two-delta constraint, the three-outcome load model, the census gate,
the discovery cutover's atomicity, the exempt set's two reasons, and the performance budgets'
provenance are all specified to a standard these items only confirm. They are included because a
gate checklist that lists only failures cannot be used as a gate.

**What this checklist deliberately does not do.** It does not check whether any of it works. Every
"verified end to end" concern in the request became a question about whether the requirement behind
it says what passing means — because a verification step whose requirement is vague produces a
green tick and no information.
