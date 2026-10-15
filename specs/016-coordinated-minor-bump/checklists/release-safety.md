# Release-Safety Checklist: Coordinated minor version bump

**Purpose**: Test whether the *requirements* for 016 are complete, clear and consistent enough to
run safely across seven repositories: version uniqueness, the relation matrix, no push / no tag,
evidence integrity, the deferred release-line reconciliation, the stop/amend protocol. This checks
the spec, plan and tasks as written. It does not check the implementation.
**Created**: 2026-10-15
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [tasks.md](../tasks.md)
**Depth / audience / timing**: formal gate, read by the maintainer before `/speckit-implement`,
after `/speckit-analyze`.

## Version uniqueness

- [x] CHK001 Is "the target sorts strictly above every released version" defined against **all** release branches (`release/*`, `rc_1`, `debian/bookworm`, `main`), not just the one release line named per repository? [Clarity, Spec §FR-002, US1 scenario 2] — ✅ FR-002
- [x] CHK002 Is the rule for re-deriving a target, when a parallel line has released above the planned one, stated as a requirement, not only applied in research (R2)? [Gap, Spec §Assumptions, §FR-002] — ✅ FR-002
- [x] CHK003 Does FR-003's fold rule cover a head entry that is **not** `UNRELEASED` but was never shipped (`cuems-power-bridge 0.3.1-1 unstable`)? Does it also cover a head entry that **was** shipped (`cuems-engine 0.1.0rc2-3`), which research R6 treats differently? [Conflict, Spec §FR-003 vs research R6] — ✅ FR-003
- [x] CHK004 Is it specified what happens if a parallel line releases **during** the feature, above a target already committed in an earlier repository? [Coverage, Gap, Spec §Edge Cases] — ✅ FR-002
- [x] CHK005 Is the version format for `cuems-utils` (native `0.1.1`, no Debian revision) distinguished from the six `-1` revisions in the requirements, not only in the contract? [Clarity, Spec §US1] — ✅ FR-003 → contract § Targets

## Relation matrix

- [x] CHK006 Do FR-005 ("the planning document's §4 matrix") and SC-002 ("24 sites of `contracts/relation-matrix.md`") name the same authoritative source? [Conflict, Spec §FR-005, §SC-002] — ✅ FR-005
- [x] CHK007 Is the change to `cuems-common`'s `Breaks: cuems-power-bridge` (`<< 0.3.2~`) traceable to a requirement or a recorded decision visible in the spec, given that planning document §4.4 says "unchanged"? [Traceability, Spec §US2 scenario 4] — ✅ FR-005, US2-4
- [x] CHK008 Are the relations deliberately left unchanged (`Suggests: cuems-power-bridge`, `python3-pyossia`) listed in the requirements, so that "every relation moved" cannot be read as including them? [Completeness, Gap] — ✅ FR-005, contract § Unchanged
- [x] CHK009 Are the Python dependency bounds (`pyproject.toml`) held to the same admit/refuse expectations as the `debian/control` relations, including PEP 440's pre-release semantics? [Consistency, Spec §FR-005] — ✅ FR-005, contract § Verdicts
- [x] CHK010 Is "relations last in the commit" (planning document §10.3) a requirement, or only a task convention? Is its purpose still valid now that no merge happens in this feature? [Clarity, Assumption, Spec §FR-010] — ✅ FR-005
- [x] CHK011 Is a "fail-before" state required for the relation verdicts (old bounds must fail the new verdicts), as SC-TEST-001 requires for the version-pin test? [Acceptance Criteria, Gap, Spec §SC-002] — ✅ SC-002

## No push, no tag, local only

- [x] CHK012 Does SC-006 define how "0 pushed" and "0 tags moved" are measured (against which remote refs, and recorded tag commits from when)? [Measurability, Spec §SC-006] — ✅ SC-006
- [x] CHK013 Is it specified that the build and demo scripts must not create tags or push, for example that `npm version` runs without git tagging? [Coverage, Gap, Spec §FR-014] — ✅ FR-008, FR-014, SC-006
- [x] CHK014 Is a requirement defined for the case where `origin/feat/xml-refactor` advances in a sibling **during** the feature (someone else pushes), after FR-001's start check passed? [Edge Case, Gap, Spec §FR-001] — ✅ FR-001
- [x] CHK015 Are the local-only artefacts (worktrees, `.venv`s, `.git/info/exclude` entries) required to leave no tracked change in any repository? Is their clean-up specified? [Completeness, Spec §FR-009] — ✅ FR-009

## Stop / amend protocol

- [x] CHK016 When an amend changes a repository's hash **after** later repositories consumed it (`cuems-nodeconf`'s demo builds `cuems-common` at its bump hash), are the dependent re-runs required, or only the tag message rewrite? [Gap, Spec §FR-021] — ✅ FR-021
- [x] CHK017 Is it defined which commit an amend targets in `cuems-utils`, which has a bump commit **and** a record commit? [Ambiguity, Spec §FR-021 vs research R13] — ✅ FR-021
- [x] CHK018 Is "explicit go-ahead" defined (who, in what form, where recorded)? [Clarity, Spec §FR-021] — ✅ FR-021
- [x] CHK019 Is the reordering allowance (editor/frontend ahead of engine while FR-020 is open) consistent with FR-016's mandatory order, or is it a conflict that needs a spec amendment? [Conflict, Spec §FR-016 vs tasks *Dependencies*] — ✅ FR-016

## Evidence integrity

- [x] CHK020 Does SC-004 ("every checkout at its committed `feat/xml-refactor` head") account for `cuems-utils` being on `016-coordinated-minor-bump`, with untracked records, while the sibling demos run? The demo scripts flag `(+ uncommitted changes)` in that state. [Conflict, Spec §SC-004, US2 scenario 5] — ✅ FR-006, SC-004
- [x] CHK021 Is "evidence written to a new file, never over a previous feature's evidence" extended to reruns within this feature (suffixing), as a requirement rather than only a task convention? [Consistency, Spec §US2 scenario 5] — ✅ Key Entities § Evidence
- [x] CHK022 Does SC-005 ("each naming a commit that is its repository's committed head") agree with research R13, under which `cuems-utils`' message names the **bump** commit while the head is the record commit? [Conflict, Spec §SC-005] — ✅ FR-016, SC-005
- [x] CHK023 Is "the set composes" defined measurably: every `Pairs with` commit equals that repository's `Tag:` line? [Measurability, Spec §US4 scenario 2] — ✅ SC-005
- [x] CHK024 Is the explicit labelling of non-validation evidence required everywhere it applies (a mock `pyossia`, demos not on re-cut tags, `dpkg --compare-versions`-only edges for engine, editor, power-bridge and utils)? [Completeness, Spec §Edge Cases, planning document §11.1] — ✅ FR-011

## Deferred reconciliation (rule 4)

- [x] CHK025 Is the content gap from `0.1.0rc17` (`stop_project`: an rc17-saved project is refused by `0.1.1`) stated in the **spec**, not only in research R3? This is the most user-visible consequence of deferring rule 4. [Completeness, Gap, Spec §FR-010] — ✅ FR-010
- [x] CHK026 Is "MUST NOT be published until reconciled" placed where a publisher will read it (tag messages, changelogs, `CHANGELOG.md`)? Is every one of those locations enumerated? [Coverage, Spec §FR-010] — ✅ FR-010
- [x] CHK027 Is the engine's release-line gap (114 behind, measured; planning document says none) reflected in the requirements' list of repositories with a gap? [Consistency, Spec §Clarifications Q2, research R1] — ✅ FR-010a
- [x] CHK028 Is the post-reconciliation obligation (re-verify relations after the later merge) stated as a requirement for the **future** work, with an owner? [Gap, Spec §Edge Cases] — ✅ FR-010

## Build and test

- [x] CHK029 Is "a Debian 12 environment that does not alter the host" (FR-006) specific enough to exclude a host build, and does it name the interpreter-home check's expected value? [Clarity, Spec §FR-006, §SC-003] — ✅ FR-006, SC-003
- [x] CHK030 Is the expected set of built binary packages per repository specified (for example `cuems-engine` **and** `cuems-engine-mock`)? [Completeness, Gap, Spec §US3] — ✅ SC-003, US3
- [x] CHK031 Is the two-arm comparison's library pinned in the requirements, so that both arms of a sibling suite run against the same `cuemsutils`? [Clarity, Spec §FR-007, research R8] — ✅ FR-007
- [x] CHK032 Is the FR-PERF-001 tolerance (115%) given a sampling rule (samples, windows), given 015's lesson that one window is not evidence? [Measurability, Spec §FR-PERF-001] — ✅ FR-PERF-001
- [x] CHK033 Are `cuems-frontend`'s build and suite requirements stated with the same two-arm rule as the Python siblings? [Consistency, Spec §FR-014, §FR-007] — ✅ FR-014

## Scope boundaries and dependencies

- [x] CHK034 Is merging `016-coordinated-minor-bump` into `cuems-utils`' `feat/xml-refactor` explicitly in or out of scope? (The siblings commit on `feat/xml-refactor`; this repository does not.) [Gap, Spec §Scope exception] — ✅ Assumptions
- [x] CHK035 Is the FR-020 gate's failure mode defined: what may proceed and what may not, and for how long? [Clarity, Spec §FR-020] — ✅ FR-020 (resolved)
- [x] CHK036 Are the frozen-record boundaries for the `v0.1.1` → `v0.1.2` sweep (014/015 kept, 010 edited) stated in the spec, given that SC-007 depends on what "non-frozen" means? [Ambiguity, Spec §FR-012, §SC-007] — ✅ FR-012
- [x] CHK037 Is an abandonment/rollback path specified, for example a mid-feature decision to drop the bump with some repositories already committed? [Recovery, Gap] — ✅ Assumptions
- [x] CHK038 Is the GPG signing failure mode (CLAUDE.md: retry, never `--no-gpg-sign`) carried into the requirements for sibling commits? [Coverage, Spec §FR-009] — ✅ FR-009

## Notes

- **Reviewed 2026-10-15 before `/speckit-implement`**, after both analyze passes: 35 items are
  answered by the requirement named after each ✅. CHK010, CHK015 and CHK024 were closed by spec edits to FR-005, FR-009 and FR-011 the same day.

- 38 items; 38 carry a traceability reference or a gap/conflict/assumption marker.
- Most of the **[Conflict]** items (CHK003, CHK006, CHK019, CHK020, CHK022) come from research
  decisions made after the spec was written. `/speckit-analyze` should confirm them and fold them
  back into the spec.
