# Merge-Safety Checklist: Release-line reconciliation before `0.1.1`

**Purpose**: Unit tests for the *requirements* that keep the merge safe. Each item asks whether the
spec and plan **say** enough, unambiguously and checkably, for these properties to hold: no
absorbed hunk dropped, no stray landed, no tag moved, no push, no sibling edited, 016's evidence
untouched, and every retirement recorded. It does not test the implementation.
**Created**: 2026-10-21 · **Reviewed**: 2026-10-21, against the spec, plan, research, data model,
contracts, quickstart and tasks after `/speckit-analyze`'s fixes
**Feature**: [spec.md](../spec.md) · [plan.md](../plan.md) · [research.md](../research.md) · [tasks.md](../tasks.md)
**Depth**: formal gate (run before `/speckit-tasks` and again before `/speckit-implement`)
**Audience**: the maintainer reviewing the spec and plan before any merge is attempted

Each ticked item names the section that satisfies it (→). Items marked **⚠ Finding** were gaps
when this checklist was written. Each records how it was closed.

## Absorbed content: nothing dropped

- [x] CHK001 Is every conflicting hunk (11 files, 25 hunks) assigned exactly one resolution, with a reason, so that no hunk is resolved by default? [Completeness, Spec §FR-010, Plan §5] → Plan §5 has one row per hunk group, with a reason. Counted: 1 + 4 header hunks + 1 + 4 + 2 + 3 + 2 + 1 + 6 + 1 = **25**. Tasks T008–T010 apply them.
- [x] CHK002 Is a per-hunk resolution record required as evidence (file, hunk, side kept, why), so a reviewer can trace each one without re-running the merge? [Measurability, Plan Phase 2 exit evidence] → Plan Phase 2 exit evidence; T012 (`evidence/merge-bookworm.md`, one row per hunk).
- [x] CHK003 Is the prohibition on `-X ours` / `-X theirs` stated as a requirement (an FR), and not only as an edge case and a plan note? [Consistency, Spec §Edge Cases, Plan §5 "Forbidden in M1"] — **⚠ Finding, closed**: promoted into **spec FR-002** (no `-X`, no non-default strategy, M3's `-s ours` the one exception); T007.
- [x] CHK004 Are the clean-merged files (`Parsers.py`, `XmlBuilder.py`, `FadeCue.py`, `tests/test_fade_cue.py`, `CLAUDE.md`, `debian/cuems-utils.links`, the `stop_project` enumeration) listed as "keep as merged", so none is silently overwritten by an "ours" habit? [Completeness, Plan §5 last row, Spec §FR-012] → Plan §5 last row; T008's last sentence.
- [x] CHK005 Is "ours" for `MediaCue` hunks 2–5 and `script.xsd` justified item by item against what rc15 shipped, so that every rc15 behaviour discarded by "ours" is either re-provided by 014 or retired with a record? [Coverage, Spec §FR-010, §FR-012, §FR-027] → The item-by-item check is the **port**: FR-027 ports rc15's 22 tests to the public API (T040). Any red assertion is an adaptation or a recorded retirement, per spec **FR-003a**, and T040 stops ⏸ before any retirement FR-003a doesn't name. The `_get_optional` absent→`None` semantics are pinned by A-6 (FR-029).
- [x] CHK006 Is a single proof required for each of the 14 inventory items, with its kind defined (public-API test, packaging test, history check, changelog test)? [Measurability, Spec §FR-003, §SC-002] → FR-003, SC-002, data-model §4, T045.
- [x] CHK007 Is the rule for the absorbed **root** test files unambiguous: ported by A-3/A-4, not deleted in M1, and not moved by C3? [Clarity, Spec §FR-026, §FR-027, §FR-063, research R17] → Research R17 keeps them in M1; FR-026 and T037/T038 port them and delete the root copies; FR-063's "17 root modules" excludes them.
- [x] CHK008 Is the behaviour of each rc15 legacy-path edit (string md5, schema-ordered media children) required to be proven on the **public** path, with a stated outcome when it already holds ("held", not an invented red)? [Clarity, Spec §FR-012, research R7] → FR-012, research R7, T041 (red-first on M3, "held" if green).
- [x] CHK009 Is "behaving as released wherever the refactor's contract allows" bounded by an explicit list of the places where it does not (md5 case folding, `""` → `None`, target repair, the retired values)? [Clarity, Spec §US2, §FR-023, §FR-027, §FR-029d] → **Added: spec FR-003a**, a closed list of departures (six since T037 added A-1's `None` acceptance), plus the rule for any new one.

## Strays: nothing extra lands

- [x] CHK010 Is the set of 42 stray paths given as an **explicit list** rather than patterns? [Clarity, Spec §FR-011, research R17] — **⚠ Finding, closed**: research R17 enumerates the list, and **spec FR-011 now cites R17 as binding**. Plan §5 and T011 use it.
- [x] CHK011 Is the stray list defined three-way (added on bookworm since the merge-base) and not two-way, so refactor deletions (`create_script.py`, `FadeProfile.py`, `outputs.xsd`) are not mistaken for strays or restored? [Clarity, research R17, Quickstart §4] → FR-011 (three-way, stated), research R17, quickstart §4, T011.
- [x] CHK012 Are the ten kept additions (seven `debian/` sources, three absorbed tests) named, so "delete the strays" cannot remove one? [Completeness, research R17] → Research R17; FR-011; T011.
- [x] CHK013 Is a post-merge requirement stated that no conflict marker and no stray path remains in the merge commit, and is it checkable by a command? [Measurability, Quickstart §4, Spec §FR-011] → T011 (the marker grep, and an empty `--diff-filter=U`); quickstart §4.
- [x] CHK014 Is the outcome defined when the re-derived stray list differs from R17 (a delta under FR-004, never a pattern edit)? [Exception Flow, research R17] → Research R17's last paragraph; FR-011; T002's stop ⏸.

## Merge-commit purity and order

- [x] CHK015 Is "the merge commit contains the §5 resolutions and the stray deletions, and nothing else" checkable, and is it reconciled with FR-030's changelog rebuild happening **in** M1 while FR-031/FR-032's body edits happen in P2? [Consistency, Spec §FR-002, §FR-030–FR-032, Plan §5] → The rebuild **is** `debian/changelog`'s conflict resolution (plan §5 row). T010 keeps the `0.1.1` body unchanged in M1, and T052/T053 make the body edits in P2. The per-hunk record (T012) is what makes "nothing else" checkable.
- [x] CHK016 Is it specified that the planning artefacts and today's `CLAUDE.md` edit (uncommitted on the 017 branch) are committed **before** M1, so the merge commit stays pure? [Gap] — **⚠ Finding, closed**: spec **FR-002** and T001.
- [x] CHK017 Is the order of the three merges (bookworm, then `main` with an empty tree diff, then `-s ours v0.0.9rc7` with an empty tree diff) fixed, with each empty-diff claim checkable? [Clarity, Spec §FR-001, Plan Phases 2–3b] → FR-001; T014 and T015, each with its command.
- [x] CHK018 Is the outcome defined if the `origin/main` merge is **not** empty (main moved, or holds content bookworm lacks)? [Exception Flow, Gap, Spec §FR-001] → T014: stop ⏸ for the maintainer. FR-004 governs the moved case.
- [x] CHK019 Is the outcome defined if re-measurement finds a conflict set different from 11 files and 25 hunks (a new file, or a modify/delete conflict)? [Exception Flow, Gap, Spec §FR-004, §FR-010] → T002 and T007: stop ⏸ and amend research. Research R17 measured no modify/delete today.
- [x] CHK020 Is the requirement that the cleanup runs **after** the final re-merge matched by a defined path for a release-line delta that arrives **after** the cleanup's test moves (rename conflicts)? [Coverage, Gap, Spec §FR-004, §Edge Cases, Plan Phases 8–9] — **⚠ Finding, closed**: T081 (merge the delta, `git mv` new root tests, re-run the layout test and the suite).
- [x] CHK021 Is a recovery path defined for an M1 that is rejected at its stop point (for example a trial merge in a scratch worktree first, or a reset of the unpushed branch), and is it stated which form is permitted? [Recovery, Gap, Plan Phase 2 ⏸] — **⚠ Finding, closed** (maintainer, option A): a trial branch, `017-m1-trial`, in its own worktree. Approval fast-forwards the 017 branch; rejection deletes the trial and redoes it. The 017 branch is never reset or fixed forward (spec Clarifications and FR-002; plan Phase 2; T007/T013; quickstart §4).

## Release safety: no push, no tag, no sibling edit, 016 intact

- [x] CHK022 Are "no push", "no tag created or moved" and "no publication" stated as requirements with **evidence** (as 016 kept `no-push-no-tag.txt`), not only as scope statements? [Measurability, Gap, Spec §Scope, §FR-043] → T003 (baseline) and T082 (end state), in `evidence/release-safety-{start,end}.txt`.
- [x] CHK023 Is "no sibling repository edited" measurable, for example each sibling's `git status` and HEAD recorded at the start and at hand-off? [Measurability, Spec §FR-043] → T003/T082. FR-040's worktrees touch only git's worktree list, never a sibling checkout (T049).
- [x] CHK024 Is "016's evidence is never overwritten" checkable (an empty `git diff --stat <branch point>..HEAD -- specs/016-coordinated-minor-bump`), and does every reuse of 016's tools name an output inside 017's own directory? [Measurability, Spec §FR-082, §FR-035, §FR-040] → T003/T082 compare file hashes. **Measured**: 016's `bookworm-build.sh` writes only to `OUT` (refusing an existing one) and a temporary `WORK`, and `verdicts.py` only reads. **Corrected**: the build tool's real interface (`UTILS=` a clean worktree, `OUT=` a 017 path) is now in FR-035, quickstart §5 and T050. 017's earlier `> evidence/…` form would have failed.
- [x] CHK025 Is GPG signing of **every** commit, merge commits included, an acceptance criterion with a check (signature status of each new commit), and not only a constraint? [Measurability, Spec §FR-002, Plan Technical Context] → FR-002; T082 (`%G?` ∈ {`G`, `U`} for every commit).
- [x] CHK026 Is the only write outside this repository (`../.xml-refactor-tag-messages/cuems-utils.txt`) bounded to that one file? [Clarity, Spec §FR-044] → FR-044; T083 ("touch no other file there"). FR-040's worktrees are temporary and removed afterwards (T049).
- [x] CHK027 Is the tag message's `Tag:` line unambiguous about which commit it names: the 017 head, or the maintainer's not-yet-existing post-merge `feat/xml-refactor` head? [Ambiguity, Spec §FR-044, §SC-010] — **⚠ Finding, closed** (analyze I2, option b): an explicit maintainer placeholder, filled at re-cut after the coordination with siblings (FR-044, SC-010, T083).
- [x] CHK028 Are the maintainer-owned hand-off acts (merge, push, CI dispatch, tag re-cut, publication) listed in one place, with nothing left implicit? [Completeness, Plan §Hand-off, Spec §FR-075] → Plan §Hand-off (five steps); T084 (`evidence/handoff.md`, six steps, including the coordination).

## Retirements and records

- [x] CHK029 Is "retirement" defined so it covers every kind of removal: a retired assertion (md5 case folding), a retired script (`testdev_nng_talk.py`), absorbed root copies replaced by ports, and retired vocabulary (Q13)? [Clarity, Spec §FR-029b, §FR-029d, data-model §6] → **Spec FR-029b now names all four kinds**; data-model §6.
- [x] CHK030 Is the place where each retirement is recorded unambiguous: `evidence/test-retirements.md` for tests and scripts, the handover document for vocabulary? [Consistency, Spec §FR-029b, §FR-053] → **FR-029b**: `test-retirements.md` is the one index, and the vocabulary row points at the handover document (T029).
- [x] CHK031 Is the Q13 removal required to land in the **same** commit as its handover document and the single `script.xsd` hash change, so the vocabulary is never gone without its record? [Consistency, Spec §FR-029d, §FR-053, §FR-025] → FR-029d, FR-053, FR-025; T030 (one commit).
- [x] CHK032 Is the released rc17 `CHANGELOG.md` line ("stay in the enum") explicitly kept verbatim while the `0.1.1` section records the retirement, so the changelog test's byte-identity check and the retirement don't conflict? [Consistency, Spec §FR-029d, §FR-033 (3)] → FR-029d; T053. (The byte-identity check, FR-033 (3), applies to `debian/changelog`, where the retirement is recorded only in the `0.1.1` entry. No conflict.)
- [x] CHK033 Is every superseded clarification (Q2's first answer, Q1's original FR-053 framing) marked superseded where it appears, with no requirement still enforcing the old reading? [Consistency, Spec §Clarifications, §FR-020, §FR-023, §FR-053] → Q2 and Q1 are marked in Clarifications. FR-020, FR-023 and FR-053 are rewritten, and so are research R4/R14, data-model §1 and contract rows 7–8c. A grep for "accept and ignore" / "no new rule" finds only the marked historical lines.

## Changelog and relation integrity

- [x] CHK034 Is "verbatim" defined at byte level, with the exception (never-built `UNRELEASED` entries kept in HEAD's form) stated and its scope bounded? [Clarity, Spec §FR-030, §FR-033 (3), M2] → FR-033 (3) (byte-identical, from the header line through the trailer line); FR-030's exception; M2 (check (4) bounded at rc8).
- [x] CHK035 Are the released-set data (Debian, PyPI, never published) given with their source of truth and a re-measure point, and is the PyPI source the JSON API (which includes yanked files) rather than `pip index`? [Completeness, Spec §FR-032, §FR-033, M1, research R9] → FR-032, FR-033, M1, research R9, the changelog-completeness contract; re-measured in T002, T069 and T081.
- [x] CHK036 Is it stated that 016's relation matrix is **not edited**, and that row 26 lives only in 017's contract and tool? [Consistency, Spec §FR-040, contracts/relation-row-26.md] → FR-040; the relation-row-26 contract.
- [x] CHK037 Is the rule for re-cutting the A-2d schema hash ("once, in A-1's commit") reconciled with every `script.xsd` edit 017 makes: the merge's enumeration, Q13's removal, and FR-051's comment check? [Consistency, Spec §FR-025, §FR-029d, §FR-051] — **⚠ Finding, closed**: **spec FR-025** now requires every `script.xsd` edit in A-1's commit (one hash move after M1); T026.

## Dependencies and assumptions

- [x] CHK038 Is the assumption that the release line holds still between re-measures stated together with what invalidates it (a new tag or head on either line)? [Assumption, Spec §Assumptions, §FR-004] → **Spec Assumptions now defines "moved"**: any sha change on either ref, or a new `debian/*` / `v*` tag, after a fresh fetch.
- [x] CHK039 Is the dependence on the chroot tarball (`CUEMS_CHROOT_TAR`) and on 016's build tool stated with the fallback when either is unavailable (recorded as not met, never skipped silently)? [Dependency, Spec §FR-035, §Assumptions] → **FR-035** (build unavailable → SC-007's build half not met) and **Assumptions** (tarball present, measured; absent → SC-005's `.deb` half not met); T050.
- [x] CHK040 Is arm A (`5e4c637`, not `2318dee`) fixed for every two-armed comparison, with the reason recorded? [Clarity, research R1, Spec §Assumptions] → Research R1 (decision and rationale); spec Assumptions; T004.

## Notes

- **40 of 40 pass.** CHK021 was the last open item, closed by the maintainer's choice of the
  trial-branch form (option A).
- Corrections made during this review (2026-10-21):
  - spec FR-002, FR-003a (new), FR-011, FR-025, FR-029b, FR-035 and Assumptions;
  - quickstart §5 and tasks T029/T040/T050;
  - the build tool's interface, measured from `specs/016-coordinated-minor-bump/tools/bookworm-build.sh`.
- Traceability: every item carries a section reference or a gap marker, and every ticked item names
  the section that satisfies it.
