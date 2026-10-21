<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Implementation Plan: Release-line reconciliation before `0.1.1`, then the first-stable-release cleanup

**Branch**: `017-release-line-reconciliation` | **Date**: 2026-10-21 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/017-release-line-reconciliation/spec.md`. Work order:
`specs/planning/release-line-reconciliation-0.1.1.md` at `2318dee`, deleted by this feature's last
task (FR-060).

## Summary

Absorb `origin/debian/bookworm` (`398a9cf`, `0.1.0rc17`) and `origin/main` (`23e4752`, tag
`v0.1.0rc17`) into the refactor with **three merges**: bookworm, main, and an empty-tree
`-s ours` merge of `v0.0.9rc7`. The conflicts are resolved by the work order's §5 rules (below).
Then the absorbed content is made to obey the refactor's contract through **red→green
adaptations**. The headline is **A-1**: one named set, `TARGETLESS_ACTION_TYPES =
frozenset({"stop_project"})`, consulted by the T2 rule `action_target_required`, by
`ActionCue.__init__` and through the setter's existing `enforce` call, so that a `stop_project`
cue with no target saves, loads and decodes from JSON. In the same commit, **`pause_project` and
`resume_project` are retired** from `ActionType`. Project pause/resume is deferred to a future
release (Q13), and the commit carries the handover document
`specs/planning/project-pause-resume-deferred.md`. The count goes 12 → 13 (merge) → **11**.

Research measured that **the writer already emits `<action_target />` for `None` and T1 accepts
it** (R4), so A-1 needs no I/O change. Per Q2 revisited, A-1 also adds one **repairable** rule,
`project_action_takes_no_target`. On load it repairs a leftover target on `stop_project` to
`None` and reports the repair; on save it refuses. It needs two companion edits:
`action_target_resolves` skips targetless types, and the descriptor's repairability map becomes
order-independent (R16). The other adaptations:
- port the absorbed tests to the public API;
- pin the packaging fixes;
- make the migration tools report T2 refusals after writing (Q3);
- extend the public-API snapshot to `MediaCue` (Q8).

The changelogs are rebuilt around the released entries, and a permanent completeness test guards
them. Then come the docs, the upstream reports and the tag message. The feature ends with the
first-stable-release cleanup (§14) and a restructured CI workflow whose green run is a
**hand-off item** (clarify). Nothing is pushed, tagged or published, and no sibling is edited.

## Technical Context

**Language/Version**: Python ≥ 3.11 (bookworm's interpreter). Measured with the hatch
`test.py3.11` environment: uv-managed CPython **3.11.9**, Clang build, interpreter
`~/.local/share/hatch/env/virtual/cuemsutils/KPtCKENL/test.py3.11/bin/python`. 3.12 and 3.13 run
once each (SC-003).
**Primary Dependencies**: runtime unchanged (`xmlschema==3.4.3`, `lxml==6.1.0`, stdlib
`ElementTree`; `pynng`, `websockets`). **Test-only addition: `pyyaml`** in the hatch `test`
environment, for the CI-workflow static check (R11, Complexity Tracking).
**Storage**: files: XML documents under `tests/data/corpus/`, `tests/golden/`, `debian/`, the
changelogs and the workflow YAML.
**Testing**: pytest through hatch (`uvx hatch run test.py3.11:run -- -q`). The bookworm chroot
lifecycle tests use `CUEMS_CHROOT_TAR=/home/adria/.cache/cuems-lifecycle/bookworm-deps.tar`
(present). Builds use `specs/016-coordinated-minor-bump/tools/bookworm-build.sh` with its output
redirected into 017's `evidence/`.
**Target Platform**: Debian 12 bookworm nodes (`.deb` via dh-virtualenv into `/usr/lib/cuems`).
The dev host is Debian 13.
**Project Type**: a shared library plus three console tools (`cuems-convert-documents`,
`cuems-reshape-devices`, `cuems-init-node`) and its Debian packaging.
**Performance Goals**: FR-PERF-001, as bands with interleaved A/B against `5e4c637` and 115%
tolerance:
- the show-document load inside 16.465–17.750 ms, or no worse than arm A;
- suite ms/test ≤ 115% of arm A;
- the `script` descriptor warm call ≤ 115% of arm A.

The tools' extra post-write check (FR-029c) is measured and recorded, not budgeted.
**Constraints**:
- no push, no tag, no publication, no sibling edit;
- every commit GPG-signed (retry on failure, never `--no-gpg-sign`);
- 016's evidence is read-only;
- `script` stays at version 2 (no version step);
- no `-X ours/theirs`;
- the cleanup runs after the final re-merge.
**Scale/Scope**: 77 + 11 commits absorbed; 11 conflicting files with 25 hunks; 42 stray paths;
14 inventory items; 6 merged-only red tests; ~46 absorbed tests ported (7 + 17 + 22); 17 root test
modules moved; 126 relation verdicts.

No `NEEDS CLARIFICATION` remains (clarify closed Q1–Q12; research R1–R14).

## Constitution Check

*GATE: checked before Phase 0, and re-checked after Phase 1 (below).*

| Principle | How 017 meets it | Verdict |
|---|---|---|
| **I. Code quality** | ruff stays **0** on both arms (SC-QUALITY-001). The mypy error set does not grow under the same command on both arms; the disputed absolute figure is not the measure. The new constant and rule edit carry inline rationale. The frozen `Parsers.py`/`XmlBuilder.py` stay excluded from ruff, and their rc15 edits are kept, not reformatted | ✅ |
| **II. Tests as a release gate** | Every adaptation is a red→green pair, recorded (FR-080): A-1 (FR-021, FR-023), A-2a–d, A-3, A-4, A-5, A-6, S-3, S-4, FR-012's public-path checks and FR-026a. Two **permanent** guards are added: changelog completeness (FR-033) and directory markers (FR-063). The workflow gets a static contract test (FR-075). A check that is already green on the merge commit is recorded as "held", never given an invented red (R7) | ✅ |
| **III. Consistent UX** | A-1 reuses `action_target_required`'s exact message for the types outside the set. The tools' new WARNING follows their existing logger and summary convention (R6). Changelog sections keep `## <version> — <date>`. `stop_project` is spelled the same everywhere. No new shorthand. The README and docs move to the public API (FR-062) | ✅ |
| **IV. Performance budgets** | Three budgets as bands, interleaved A/B, 115% (FR-PERF-001). `scaling_cur_freq` is checked, and the interpreter build is recorded with each figure. An exceeded budget is recorded as exceeded. The tool cost (FR-029c) is measured, without a budget (013's precedent) | ✅ |
| Engineering standards | **No new runtime dependency.** One test-only dependency (`pyyaml`), justified below. Refactors preserve behaviour: the cleanup is pure moves, deletes and rewires, with the pass set compared before and after. Errors stay actionable (FR-081) | ✅ (one recorded addition) |
| Delivery workflow | Tasks carry test and verification steps per story. Evidence of the lint, test and performance runs goes to `evidence/` | ✅ |

**Gate result: PASS.** Two items are recorded in Complexity Tracking: one test-only dependency,
and one departure from the work order that clarify decided.

## Project Structure

### Documentation (this feature)

```text
specs/017-release-line-reconciliation/
├── spec.md                     # /speckit-specify + clarify (Q1–Q12, gate, M1)
├── plan.md                     # this file
├── research.md                 # R1–R14: re-measurement, design decisions, carried §2/§4.1/§6/§12
├── data-model.md               # the entities 017 adds or changes (targetless set, released sets, …)
├── quickstart.md               # the work order's §13 recipe: worktrees, probes, builds, A/B runs
├── contracts/
│   ├── targetless-actions.md   # A-1: behaviour at construct / JSON / save / load
│   ├── migration-tool-report.md# FR-029c: the post-write T2 report
│   ├── changelog-completeness.md # FR-033: the six checks and their data
│   ├── relation-row-26.md      # FR-040: the Replaces edge and its five verdicts
│   ├── test-layout.md          # FR-063: directory markers and the root rule
│   └── ci-workflow.md          # FR-070–FR-076: jobs, needs graph, blocking set, conditions
├── checklists/
│   └── requirements.md         # spec quality (done)
├── tools/
│   ├── capture_rc17_fixture.py # R5: runs inside a 398a9cf worktree
│   ├── probes.py               # S-1/S-1′/S-2/X-4/control probes, both arms
│   └── verdicts-017.sh         # 016's 121 verdicts + row 26's five
├── evidence/                   # red→green pairs, suites, perf, builds, inventory table,
│   │                           #   test-retirements.md, ci-gate.md (template)
├── upstream-reports/           # cuems-editor, cuems-frontend, cuems-power-bridge, release-line-hygiene
└── tasks.md                    # /speckit-tasks
```

### Source code touched (this repository only)

```text
src/cuemsutils/
├── cues/ActionCue.py           # A-1: TARGETLESS_ACTION_TYPES, __init__ guard; FR-051 docstring
├── cues/CueList.py, MediaCue.py, CuemsScript.py   # merge resolutions (§5), no adaptation
├── xml/validators.py           # A-1: action_target_required consults the set
├── xml/schemas/script.xsd      # merge: stop_project enumeration (clean); FR-051 comment check
├── xml/convert_documents.py    # FR-029c: post-write T1+T2 report
├── xml/reshape_devices.py      # FR-029c report; FR-029a __main__ guard
└── __init__.py                 # merge: __version__ = "0.1.1" kept
tests/
├── unit/                       # ported: stop_project (7), media guards (17), media values (22);
│                               #   A-6; FR-012 public-path checks; + 12 root modules moved
├── integration/                # A-1 rc17 migration test; FR-029c/FR-029a tool tests; + 4 moved
├── contract/                   # A-2a–c, A-2d hash, FR-026a snapshot, test_test_layout.py,
│                               #   test_ci_workflow.py; + test_version moved
├── packaging/                  # A-5 (Replaces, CACHEDIR.TAG strip, built .deb), changelog completeness
├── data/corpus/rc17/           # FR-022 fixture + control twin + PROVENANCE.md
├── golden/api/public_api.json  # FR-026a, one surgical re-hash (+ MANIFEST.sha256)
└── conftest.py                 # FR-063 collection hook
debian/  changelog, control, rules, README.Debian   # §5 + §7
CHANGELOG.md, README.md, docs/*.md, mkdocs.yml, CONTRIBUTORS.md, CLAUDE.md, ToDo.md (deleted),
dev/ (deleted), .gitignore, .claude/settings.local.json (untracked), pyproject.toml,
.github/workflows/{tests,gh-pages}.yml
specs/planning/  coordinated-release-version-bump.md (FR-052), project-pause-resume-deferred.md (FR-053, new),
                 release-line-reconciliation-0.1.1.md (deleted, FR-060), + any ToDo.md survivors
../.xml-refactor-tag-messages/cuems-utils.txt       # FR-044 (text only, not a sibling repository)
```

**Structure decision.** The existing single-library layout is kept. The test tree's four kind
directories become the only place a test may live (FR-063). The FR-053 document is
`specs/planning/project-pause-resume-deferred.md`: it is the handover for vocabulary 017 retires
(Q13), and the name says both what it covers and that the work is deferred.

## Phases

The work order's §11, in order. **One commit per row** unless stated, GPG-signed. **Stop points**
(⏸) are where implementation pauses and shows evidence before going on.

| Phase | Work order | What | Commit(s) | Exit evidence |
|---|---|---|---|---|
| **0 Re-measure** | §11.1 | fetch; §2 counts; the released sets (R9); PyPI JSON; §4.1 sweep (R2) | none | `evidence/remeasure-start.md` |
| **1 Baseline** | §11.2 | arm A `5e4c637` worktree; suite ×1 on 3.11; perf baselines (show load, ms/test, descriptor warm); mypy set; ruff | none | `evidence/suite-A-1.txt`, `evidence/perf.md` (arm A) |
| **2 Merge bookworm** | §11.3 | **on the trial branch `017-m1-trial`** (own worktree, from the 017 head; fast-forwarded into 017 on approval, deleted and redone on rejection; FR-002, CHK021): `git merge --no-ff --no-commit origin/debian/bookworm`; apply **§5 table below** exactly; `git rm` the 42 strays; `debian/changelog` rebuilt per FR-030; verify the merged-only red set | **M1** (merge commit: resolutions + deletions only) | `evidence/merge-bookworm.md` (conflict list, hunk-by-hunk resolution, stray list, suite B-1 red set = §6.1's six) ⏸ |
| **3 Merge main** | §11.4 | `git merge --no-ff origin/main`; confirm empty tree diff | **M2** | `git diff M1 M2 --stat` empty |
| **3b Ancestry** | Q9 | `git merge -s ours v0.0.9rc7`, message citing the rc8 equivalence | **M3** | empty tree diff; `v0.0.9rc7` ancestor |
| **4 Adaptations** | §11.5 | each red→green; see the table below | **A-1+A-2d**, **A-2a–c**, **A-3**, **A-4**, **A-6**, **S-4**, **S-3**, FR-012 ports (only if red), **FR-026a** (last of this phase) | `evidence/red-green.md` (each pair: test id, red output on its base, green output) ⏸ after A-1 |
| **5 Packaging** | §11.6 | A-5 pins; `debian/control` comment rewording; changelogs (FR-030–FR-032, M1); completeness test (FR-033); bookworm build + FR-035 checks; `tools/verdicts-017.sh` → 126/126 | **P1** (A-5), **P2** (changelogs + completeness test) | `evidence/bookworm-build.txt`, `evidence/verdicts-017.txt` ⏸ |
| **6 Docs + reports** | §11.7 | FR-050–FR-052 (CLAUDE.md, ActionCue docstring, xsd comment check, coordinated-bump owed list); five upstream reports (editor, frontend, **engine**, power-bridge, hygiene). FR-053's document is **not** here: it lands with the removal in A-1 | **D1** (docs), **D3** (reports) | — |
| **7 Verify** | §11.8 | suite 3.11 ×3 interleaved A/B; 3.12, 3.13 once; perf bands; ruff; mypy set; tool cost (FR-029c) | **V1** (records) | `evidence/suite-*.txt`, `evidence/perf.md`, `evidence/inventory.md` (14 rows) ⏸ |
| **8 Re-fetch** | §11.9 | if a line moved, loop phases 2–7 for the delta (FR-004: new release → inventory row, verbatim changelog entry, public-API test, released-set data) | per delta | `evidence/remeasure-handoff.md` |
| **9 Cleanup** | §11.10, §14.1–14.4 | one commit per sub-section; suite after each, pass set compared | **C1** root/`dev/`/`ToDo.md`/settings, **C2** README/docs/mkdocs, **C3** tests layout + markers + `--strict-markers` + contract test, **C4** gh-pages gate | `evidence/cleanup-pass-set.md` (before/after diff = retirements only) |
| **10 CI** | §11.11, §14.5 | `tests.yml` restructure, `siblings_ref`, Codecov gate; `pyyaml` test dep; static workflow test; `evidence/ci-gate.md` template; CONTRIBUTORS.md lines | **C5** | static test green; template present |
| **11 Hand-off** | §11.12 | tag message rewrite (FR-044); hand-off list: `--no-ff` merge, push, CI dispatch run, tag re-cut — all maintainer | **H1** (records) | `evidence/handoff.md` ⏸ |
| **12 Delete work order** | §11.13 | traceability verified; `git grep` clean outside `specs/017-*`; `git rm` | **Z1** (last) | grep output in commit message |

### §5 — conflict resolutions, per hunk (binding; carried from the work order)

| File / hunk | Resolution | Reason |
|---|---|---|
| `src/cuemsutils/__init__.py` | **ours** `__version__ = "0.1.1"` **plus theirs'** `SPDX-FileContributor: Ion Reguera` line | D6; `test_this_repository_is_at_0_1_1` |
| `ActionCue.py`, `CuemsScript.py`, `MediaCue.py` hunk 1, `CueList.py` hunk 1 | **theirs' three SPDX lines, then ours' imports** | bookworm added SPDX headers; HEAD's imports (`typing`, `re`, `Mapping`) are the refactor's |
| `CueList.py` hunk 2 (`get_media`) | **theirs** (869fej07m `media_status()` branches) | item 2; HEAD's `hasattr(cue.media, 'file_name')` never catches the `KeyError` |
| `MediaCue.py` hunks 2–5 (`_set_positive_int`, pixel/file accessors, `file_md5`) | **ours** | 014 is the re-implementation, same element names; theirs' `_get_optional`/lowercasing `set_file_md5` contradict 014 (D4, A-4) |
| `script.xsd` hunk 1 (media-block comment) | **ours** | same elements; 014's comment is the contract |
| `script.xsd` hunk 2 (`Md5Type` vs `CueOutputClassType`) | **ours**, drop theirs' `Md5Type` | HEAD declares `Md5Type` once by design; a second is a schema error |
| `debian/control` hunk 1 | **theirs** (SPDX header) | — |
| `debian/control` hunk 2 | **ours** (`debhelper-compat (= 13)`, `Standards-Version: 4.6.2`) | 011 hygiene |
| `debian/control` hunk 3 | **both**: ours' `Breaks: cuems-common (<< 1.3.1~)` with its comment, then theirs' `Replaces: cuems-engine (<< 0.1.0rc6-2~)` | row 1 + item 4; comment reworded in P1 (A-5) |
| `debian/rules` hunk 1 | **theirs** (SPDX) | — |
| `debian/rules` hunk 2 | **theirs first** (`rm -f …/CACHEDIR.TAG` directly after `dh_virtualenv`, inside `override_dh_virtualenv`), **then ours** (011's schema/defaults install, `override_dh_installdeb`) | item 5 |
| `debian/README.Debian` | **ours, whole file** — `git checkout --ours debian/README.Debian`, **never** a marker-splitting script (its `======` underline reads as a separator) | 011's operator README |
| `debian/changelog` (6 hunks) | **rebuilt** per FR-030 (order by dpkg version; rc15–rc17 verbatim from bookworm; HEAD's retrospective rc15 body → `0.1.1`; old UNRELEASED entries in HEAD's form) | §7.1 |
| `CHANGELOG.md` | ours' `0.1.1` section on top, theirs' `0.1.0rc17`/`0.1.0rc16` sections kept; the rest in P2 | §7.2 |
| 42 stray paths | **`git rm`** in M1, **exactly the list in research R17** (21 build outputs including `debian/compat`; 21 root files including `.python-version`), re-derived three-way from the merge-base and compared; the ten kept additions (seven `debian/` sources, three absorbed test files) are never in it | never shipped; `debian/compat` breaks the build |
| clean merges: `Parsers.py`, `XmlBuilder.py`, `FadeCue.py`, `tests/test_fade_cue.py`, `CLAUDE.md`, `debian/cuems-utils.links`, `script.xsd` `stop_project` enumeration | **keep as merged** (Q5) | rule 4 |

**Forbidden in M1**: `-X ours`/`-X theirs`; any edit not in this table; any adaptation.

### Phase 4 — the adaptations, red→green

| Id | Red test (written or observed red first) | Base it is red on | Change | Commit |
|---|---|---|---|---|
| **A-1** | `tests/unit/test_targetless_actions.py`: construct `stop_project` with `None`/`""`/absent target; `from_json` with `null`; `stop` + `None` still refused at construct/save/load; unknown type refused by T1. **Leftover target (Q2 revisited):** a resolving and a dangling uuid each load REPAIRED → `None` with exactly one `RepairRecord` naming `project_action_takes_no_target`; save refused with its message; `validate()` reports it. **Descriptor (FR-023a):** `ActionCue.action_target` stays UNREPAIRABLE; the map does not depend on registration order. `tests/integration/test_rc17_migration.py`: fixture → reshape → convert → `load_with_report` CLEAN; control twin CLEAN | M3 | `TARGETLESS_ACTION_TYPES`; `action_target_required` passes the set; `action_target_resolves` skips the set; **new** `project_action_takes_no_target` (repairable); `__init__` guard; descriptor map → conservative (R3, R4, R16); fixture + PROVENANCE (R5); the closed-rule-list tests updated for one new rule | **A-1** (with A-2d's hash and the Q13 retirement) |
| **Q13 retirement** | `tests/contract/test_retired_action_types.py`: `pause_project`/`resume_project` refused by T1 at `save` and `load`, and through `from_json`; absent from the descriptor (all red on M3) | M3 | remove both `<xs:enumeration>`s; `ActionType` comment points at the handover; **write `specs/planning/project-pause-resume-deferred.md` in the same commit** (FR-053, R15) | in **A-1** |
| A-2d | `test_every_schema_matches_its_recorded_hash` (observed red on M1) | M1 | `CURRENT_SCHEMA_HASHES['script.xsd']`, after both A-1's and the retirement's xsd edits: **one** hash change | in **A-1** |
| A-2a–c | the three contract tests (observed red on M1) | M1 | **eleven** by name (tests renamed `…_exactly_eleven_values`); retained set gains `stop_project` and loses the two retired values; rationale in `evidence/enum-audit-017.md` | **A-2** |
| A-3 | rc17's 7 and rc16's 17 tests, ported to the public API under `tests/unit/` (A-3a re-expressed by A-1) | M3 | delete the root copies; no deprecated imports | **A-3** |
| A-4 | rc15's 22, ported next to `test_media_block.py`; `test_stored_lowercase` **retired** → `evidence/test-retirements.md` | M3 | — | **A-4** |
| FR-012 | public-path: all-digit md5 is `str`; `<Media>` children in XSD order | M3 | port only if red (R7) | **A-7** if needed, else recorded "held" |
| A-6 | X-4 pin (`None` absent, `int/int/int/str` present, `to_wire` omits) | M3 (expected green: record "held" if so, it is a pin) | — | **A-6** |
| S-4 | `python -m cuemsutils.xml.reshape_devices <file>` reports a verdict | M3 | `if __name__ == "__main__": sys.exit(main())` | **A-8** |
| S-3 | tool writes **and** warns + summary entry for the control twin with an emptied `stop` target; clean document → no entry; exit status and bytes unchanged | M3 | post-write check in both tools (R6) | **A-9** |
| FR-026a | `test_public_api_matches_the_snapshot` with `MediaCue` in `PUBLIC_CLASSES` (red before the golden block) | after A-9 | surgical golden insert; MANIFEST; immutability docstring | **A-10** (last) |

**Commit order of the adaptations.** `tasks.md` groups them by user story, so S-4 (A-8) and S-3
(A-9) land in US1, **before** A-2a–c (US2), rather than after A-6 as the row order above suggests.
Nothing depends on that order: S-3 and S-4 touch only the two tools and their tests. The binding
constraints are three: A-1, A-2d and the Q13 retirement in one commit; FR-012's checks red-first
on **M3**; FR-026a last.

## Hand-off (owed by the maintainer, listed in `evidence/handoff.md`)

1. Review, then `git merge --no-ff 017-release-line-reconciliation` into `feat/xml-refactor`.
2. Push `feat/xml-refactor` (and, optionally, the 017 branch).
3. Dispatch `tests.yml` on the pushed head with `siblings_ref` at the current candidate tags; fill
   `evidence/ci-gate.md` (SC-013's after-hand-off half).
4. Fill the tag message's `Tag:` placeholder (the only edit; analyze I2). This comes after 017's
   merge, coordinated with the siblings' landings and any later upstream requests. Then re-cut
   `xml-refactor-merge-candidate` from `../.xml-refactor-tag-messages/cuems-utils.txt`.
5. Rule 4 for the other repositories; publication (PyPI, the archive) only after the
   pre-publication gate (FR-076).

## Constitution Check — after Phase 1 design

Re-checked against `data-model.md`, `contracts/` and `quickstart.md`. Nothing in the design adds a
runtime dependency, a schema version step or a writer/reader change. It adds **one** T2 rule,
`project_action_takes_no_target` (repairable, Q2 revisited). It is test-first, its message is
actionable, and its companion edit to the descriptor's repairability map is a measured no-op for
every existing field (R16). The Q13
retirement narrows `ActionType` inside the unreleased version-2 step. It is justified by the
measured absence of producers and documents, and it is test-first (T1 refusal, red on M3). A-1 changes
**one predicate** and **one guard**; the tools gain a **report**, not a decision. The design's only
dependency addition is test-only. **PASS**, unchanged.

## Complexity Tracking

| Item | Why needed | Simpler alternative rejected because |
|---|---|---|
| **`pyyaml` added to the hatch `test` environment** (test-only; not in `[project.dependencies]`, not in the `.deb`) | FR-075's static check must parse `tests.yml`/`gh-pages.yml` to assert the jobs, `needs:` graph, blocking set and `main`-only conditions; `yaml` is absent from the test env (R11, measured) | a hand-written line parser is fragile on YAML block scalars and would itself need tests; skipping when absent means the gate never checks itself |
| **The CI green run moves after hand-off** (departs from work order §14.5–§14.6) | a dispatch needs a pushed ref, and pushing is a maintainer act (clarify, gate question) | an agent push breaks "agents never push"; a local `act` run is not the hosted environment the gate exists to prove |
| **A vocabulary removal inside a reconciliation** (Q13: `pause_project`, `resume_project`) | the values are unimplemented everywhere and authored nowhere (measured), and `0.1.1` is the last point where removing them costs no version step. After it ships, `script` 2 is released and any narrowing needs a 2 → 3 step | keeping them leaves two values every consumer must treat as "valid but does nothing", for a feature deferred to a later release |
| **A third, ancestry-only merge** (`-s ours v0.0.9rc7`, Q9) | stops every future stray sweep from flagging a released tag whose content rc8 already carries | pointer-only leaves a permanent false positive in a check FR-004 runs twice per feature |
