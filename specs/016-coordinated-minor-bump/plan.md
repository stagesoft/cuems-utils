<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Implementation Plan: Coordinated minor version bump and candidate-tag re-cut preparation

**Branch**: `016-coordinated-minor-bump` | **Date**: 2026-10-15 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `specs/016-coordinated-minor-bump/spec.md`; work order
[`specs/planning/coordinated-release-version-bump.md`](../planning/coordinated-release-version-bump.md)

## Summary

Move all seven CUEMS repositories to their next stable minor in one coordinated, unpushed set:
`cuems-utils 0.1.1`, `cuems-common 1.3.1-1`, `cuems-engine 0.1.1-1`, `cuems-editor 0.1.1-1`,
`cuems-nodeconf 0.1.1-1`, **`cuems-power-bridge 0.4.0-1`** (re-derived twice, research R2, R2a) and
`cuems-frontend 0.2.0` (research R2b), every changelog head `UNRELEASED`. **`cuems-utils` commits its bump
first** (every sibling build resolves `cuemsutils>=0.1.1`, which exists nowhere else), and its record
commit, where its candidate tag goes, and its tag message **last**. All 24 versioned package relations move
in the same commits. Each package is built in a disposable bookworm chroot against a `cuemsutils`
wheel from this checkout. Each suite is compared before and after, on pyenv 3.11.9 for siblings and
hatch for this repository. One candidate-tag message per repository is written to
`../.xml-refactor-tag-messages/` for the maintainer to re-cut from. Implementation stops after each
repository for a go-ahead, and amends corrections into that repository's single bump commit.
Release-line reconciliation is **not** done here and is recorded everywhere as outstanding.

## Technical Context

**Language/Version**: Python 3.11 (siblings on pyenv 3.11.9 LTO; `cuems-utils` on its hatch
3.11/3.12/3.13 matrix), POSIX shell / bash for build and demo scripts, TypeScript/Angular 19 for
`cuems-frontend` (version field only).
**Primary Dependencies**: no new runtime dependency. Tooling: `mmdebstrap`, `uidmap`, `equivs`,
`dpkg-dev`, `debhelper`, `dh-virtualenv`, `fakeroot`, `uv`/`hatch`, `gpg`, Node 20 + Chrome.
All present (research R7; `equivs`/`debhelper` installed by the maintainer 2026-10-15).
**Storage**: files: `debian/changelog`, `debian/control`, `pyproject.toml`, `__init__.py`,
`package.json`/`package-lock.json`; feature records and evidence; tag-message files.
**Testing**: each repository's own suite, two arms (research R8); `dpkg --compare-versions` and
`packaging.specifiers` verdicts (contracts/relation-matrix.md); bookworm build; the two install
demonstrations; `cuems-utils`' rewritten release-matrix test.
**Target Platform**: Debian 12 (bookworm) nodes; built on a Debian 13 host via unprivileged chroot.
**Project Type**: multi-repository release engineering (library + five packaged consumers + one UI).
**Performance Goals**: no runtime path changes; suite per-test time within 115% (FR-PERF-001).
**Constraints**: nothing pushed; no tag created/moved; GPG-signed commits; siblings commit on
`feat/xml-refactor`; no release-line merge/cherry-pick; stop after each repository; amend by default.
**Scale/Scope**: 7 repositories, 25 relation sites (24 moved + 1 declared), ~20 version sites, 13 `v0.1.1` removal-release
sites + 16 rename citations here, ~10 sibling test/demo files pinning literals.

**Engine inputs (resolved 2026-10-15, second analyze)**: FR-020 — the engine's dev group pins the
real `pyossia` `cuems3` wheel; FR-010a — re-measured at `7d0bda3`; FR-022 — the engine lock stays
unrelocked behind a strict-xfail `poetry check --lock` test; FR-023 — `libmtcmaster (>= 0.0.2-0)`
declared, libossia an independent input. Source:
`../cuems-engine/specs/planning/coordinated-release-inputs-pyossia-and-engine-ci.md`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Code Quality** ✅. The only code edits are version constants and the removal-release constant.
  Gates: `cuems-utils` ruff **0** and mypy **≤ 72** (015's ratchet), unchanged; each sibling's
  existing lint, if configured, has no new findings. No new warnings: the deprecation warnings change
  text only.
- **Testing Standards** ✅:
  - Fail-before/pass-after: `cuems-utils`' rewritten release-matrix test fails at `b83d5c2` and
    passes at the bump. The siblings' tag-based half is `xfail(strict)` until the re-cut (R11).
  - `cuems-common`'s `test_version_bounds.py` lists move with its bound (R9).
  - Every relation has an admit/refuse verdict (24 sites).
  - Sibling suites are compared by test id across both arms.
  - The install demonstrations are updated in the same commit as the relations they test.
- **UX Consistency** ✅. User-facing surfaces: the changelog entries (each repository's existing
  `debian/changelog` style), the deprecation warning text (`v0.1.1` → `v0.1.2` from one constant),
  and the tag messages (the existing tags' house style, contracts/tag-message.md). No CLI output,
  prompt or default changes.
- **Performance Requirements** ✅. N/A for runtime, since no runtime code changes. The suite budget
  is 115% per test, interleaved A/B with 3 samples per arm (R14).

No violations, so Complexity Tracking stays empty. The **scope exception** (writing to sibling
repositories) is a spec-level decision taken by the maintainer, not a constitution violation; it is
recorded in spec.md.

**Post-design re-check (after Phase 1)**: still ✅. The design adds one feature-local script
(`tools/bookworm-build.sh`) and no dependency. The rename of `test_no_version_bump.py` keeps its
guard function (R11). Two deviations from the planning document are recorded as research
decisions, not silent changes: R2 (power-bridge `0.3.2-1` + its `Breaks:`), and R11 (014/015 kept
frozen against §8).

## Project Structure

### Documentation (this feature)

```text
specs/016-coordinated-minor-bump/
├── spec.md
├── plan.md                    # this file
├── research.md                # R1–R14, measured 2026-10-15
├── data-model.md              # repository record, preflight record, evidence
├── quickstart.md              # the commands, by hand
├── contracts/
│   ├── relation-matrix.md     # 24 sites, targets, admit/refuse verdicts
│   └── tag-message.md         # required fields + verification
├── checklists/requirements.md
├── tools/bookworm-build.sh    # created by tasks (R7)
├── records/                   # preflight.md + one <repo>.md each (created by tasks)
├── evidence/                  # relation verdicts, per-repo suites/builds/demos (created by tasks)
└── tasks.md                   # /speckit-tasks
```

### Source code touched (seven repositories)

```text
cuems-common/        debian/changelog, debian/control,
                     tests/test_version_bounds.py (+ R9 files), tests/packaging/release-gate-demo.sh, stubs/
cuems-nodeconf/      pyproject.toml, debian/changelog, debian/control,
                     tests/packaging/release-gate-demo.sh, stubs/ (+ R9 files)
cuems-power-bridge/  pyproject.toml, src/cuemspowerbridge/__init__.py, debian/changelog, debian/control
cuems-engine/        pyproject.toml, src/cuemsengine/__init__.py, debian/changelog, debian/control
cuems-editor/        pyproject.toml, src/cuemseditor/__init__.py, debian/changelog, debian/control,
                     tests/packaging/bookworm-build.sh (comment)
cuems-frontend/      package.json, package-lock.json
cuems-utils/         src/cuemsutils/{__init__,_deprecation,timeoutloop}.py, tools/CTimecode.py,
                     xml/{__init__,xml_reader_writer,XmlReaderWriter,Settings,CMLCuemsConverter,settings}.py,
                     tests/packaging/test_no_version_bump.py → test_release_matrix.py,
                     tests/contract/{test_deprecation_shims,test_validate_advice_per_schema}.py,
                     tests/unit/test_ctimecode.py, debian/{changelog,control}, CHANGELOG.md,
                     README.md, docs/index.md, CLAUDE.md, specs/planning/* (rename + corrections),
                     specs/010-consumer-migration/* (open feature)
../.xml-refactor-tag-messages/   README.md + seven <repo>.txt
```

**Structure Decision**: no new source module anywhere. Each sibling gets exactly one bump commit on
`feat/xml-refactor`. `cuems-utils` gets a bump commit and a record commit on
`016-coordinated-minor-bump` (R13); the bump commit is made **first** and the record commit
**last**. The candidate tag goes on the head of `feat/xml-refactor` once 016 is merged into it (2026-10-16; originally the record commit). Builds and demos use a clean worktree of
the bump (`.016-utils-bump`). `.venv/` is excluded through `.git/info/exclude`, never `.gitignore`
(R8).

## Phases

- **Phase 0 — research** ✅ `research.md`. No NEEDS CLARIFICATION remains. FR-020 and FR-010a were
  resolved by the engine's own work (second analyze, research R16).
- **Phase 1 — design** ✅ `data-model.md`, `contracts/`, `quickstart.md`, agent context.
- **Phase 2 — tasks**: `/speckit-tasks`. Expected shape:
  1. Setup/preflight (FR-018, FR-020 gate, worktrees, `tools/bookworm-build.sh`, verdict evidence).
  2. `cuems-utils` bump (first), with its stop.
  3. One phase per sibling in FR-016's order, each with the request's seven steps and its stop.
  4. `cuems-utils`' record commit and tag message (last), with its stop.
  5. The final checks (SC-005/006).
- **Analyze (2026-10-15)**: one CRITICAL (C1, the commit order) and five HIGH findings, all applied
  to spec, research, contracts and tasks; maintainer decisions recorded in spec Clarifications.
- Then `/speckit-checklist` (release safety) and `/speckit-analyze` before `/speckit-implement`.

## Complexity Tracking

*No constitution violations.*
