<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Tasks: The consumer-gate closure

**Input**: Design documents from `/specs/015-consumer-gate-closure/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED by the constitution (Principle II) and by **SC-TEST-001** — every requirement
has a test that **fails before** the change and passes after. For G5 the failing test is the
**composition**, not the unit (FR-053).

**Organization**: one phase per user story. Nine stories; five gates (G1–G5) plus four stragglers
(S1–S4). The nine phases are **not** in bare priority order — one hard dependency promotes a P2
story ahead of a P1 one, stated at that phase and in *Dependencies* below.

⚠ **`S1`–`S4` here are the source document's stragglers.** The spec's *settled* items are
**`SET-1`–`SET-13`**, renamed 2026-10-13 because both series used `S*` and "S2" therefore named two
unrelated things — one of them *"no work"*, the other a requirement block.

⚠ **Nine tasks were added and four moved by the `/speckit.analyze` pass (2026-10-13)**, each marked
where it sits: the golden event moved to the polish phase (T026, T088, T089, T092), five consumer
obligations acquired verification tasks (T105a–T105e), and the type gate, the documentation
rendering and three cross-cutting invariants acquired tasks they did not have (T005a, T120a–T120c,
T121a–T121c).

⚠ **A second `/speckit.analyze` pass (2026-10-13) added six more and corrected five**, after the
first pass had closed every identifier-level hole. Added: **T049a** and **T080a**, the two surface
records a public addition must move and does not move by itself; **T090a**, the three pre-state
documents the indenting writer breaks; **T022a**, the `project_settings` accessor's return shape;
**T071a**, G3's contract published at its rendered entry point; **T111a**, the sweep's third
undispositioned document. Corrected: **T026** (two of its four additions depend on T049a/T080a),
**T121b** (three modules, not four), **T121c** (an explicit, reasoned exclusion), **T135** and
**T129**/**T111**'s counts. The pass's own lesson: when an artefact claims *a record will move*,
read the thing that generates the record.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US9, mapping to the spec's user stories
- Exact file paths in every description

## Path Conventions

Single project: `src/cuemsutils/`, `tests/` at the repository root. Four records, each with one
owner and no overlap:

| Record | Holds |
|---|---|
| `baseline.md` | every measured figure, with its interpreter build and load average |
| `migration-guide.md` | cross-repository claims, the golden event, the operator triage question, the planning-folder dispositions |
| `consumers_works.md` | every obligation on another repository, with its measured status (FR-106) |
| `snapshots/` | the before-states later tasks compare against — repairability, union enums, lint, types |

**Run the suite** (quickstart §2): `uvx hatch run test.py3.11:run -- -q` ·
**lint**: `uvx hatch run test.py3.11:lint` · **types**: `uvx hatch run types:check src/cuemsutils`
(the scope arg is required — the script's default pulls in `tests`, where 158 errors are one
unimportable `pytest`) ·
**goldens**: `PYTHONPATH=src $PY -m tests.support.capture_goldens --force`

---

## Phase 1: Setup (measurement preconditions)

**Purpose**: nothing is measured before the instrument is identified. This feature's own figures were
wrong three times (R10) and the two causes were an unrecorded load average and an unrecorded
interpreter build.

- [x] T001 Verify the interpreter build per [quickstart.md](quickstart.md) §1 — `uvx hatch run test.py3.11:python -VV` resolves 3.11.9, and the pyenv build reports both `optimizations` and `lto` in `sysconfig.get_config_var('CONFIG_ARGS')`; record the resolved absolute `$PY` path for every later measurement (FR-PERF-005). Verified 2026-10-13: `3.11.9 [Clang 18.1.8]` via `uvx hatch env find test.py3.11`, `$PY = /home/adria/.local/share/hatch/env/virtual/cuemsutils/KPtCKENL/test.py3.11/bin/python`; `CONFIG_ARGS` reports both `optimizations` and `lto`
- [x] T002 Run the branch-point suite `uvx hatch run test.py3.11:run -- -q` and confirm the five attributed failures and the `3565 passed / 113 skipped / 2 xfailed` counts of [quickstart.md](quickstart.md) §2 — an unequal skip count means dependency parity was lost and must be resolved before any other task. Confirmed 2026-10-13 (second run, load average had dropped from a contended first run that spuriously failed two perf-sensitive tests in `test_descriptor_laziness.py`): `5 failed, 3565 passed, 113 skipped, 2 xfailed in 36.42s` — the exact five named in quickstart §2
- [x] T003 [P] Capture the before-snapshot of the full repairability and per-field default map to `specs/015-consumer-gate-closure/snapshots/repairability-before.txt` with [quickstart.md](quickstart.md) §5's probe over `src/cuemsutils/xml/descriptor.py`, for SC-005a's zero-change comparison — **in the feature directory, not `/tmp`**: T058 and T123 read it many phases later, and a snapshot that does not survive a reboot is a baseline that quietly becomes "trust me". Captured 2026-10-13: 327 rows
- [x] T004 [P] Capture the before-snapshot of the five descriptor sites that report a one-value choice set to `specs/015-consumer-gate-closure/snapshots/union-enums-before.txt` with [quickstart.md](quickstart.md) §5's union probe, for SC-010's 5 → 0 comparison (same durability reason as T003). Captured 2026-10-13: exactly the five sites named in research — `network_map.NodeType.uuid`, `settings.AudioPlayerType.output_latency_ms`, `settings.NodeConfType.uuid`, `settings.VideoPlayerType.output_latency_ms`, `project_mappings.NodeMappingType.uuid`
- [x] T005 [P] Reproduce G5's dead end per [quickstart.md](quickstart.md) §4 against `git -C ../cuems-nodeconf show 4d7c91d:tests/fixtures/etc_cuems/settings.xml`, and record the exact refusal text and exit code — this is the red state US3 must invert. Reproduced 2026-10-13: `skipped (would not validate: ... Unexpected child with tag 'audio_cards' at position 3 ...)`, `nothing to do (1 skipped)`, `exit 1` — matches quickstart exactly
- [x] T005a **The lint baseline is registered**: `specs/015-consumer-gate-closure/snapshots/lint-before.txt`, **606 errors = 316 in `src/` + 290 in `tests/`**, captured 2026-10-13 at `75a958e`. **302 of `src/`'s 316 are mechanical** (267 `W293`, 11 `W291`, 7 `F541`, 17 `I001`) and 14 are judgement; `tests/` is 209 mechanical and 81 judgement. The file carries the two hazards `ruff --fix` walks into — `I001` is not safely bulk-fixable in this package, and `E721`'s correct fix is `is`, not `isinstance` (Constitution I, SC-QUALITY-001, FR-111)
- [x] T005b **The type baseline is registered**: `specs/015-consumer-gate-closure/snapshots/types-before.txt`, **80 errors in 26 files (checked 68)**, captured 2026-10-13 at `75a958e` with mypy 2.4.0 on the interpreter `hatch` resolves. Scope is **`src/cuemsutils` only**, by maintainer decision — `types:check`'s own default adds `tests`, which reports 278, but **158 of those are the single module `pytest` being unimportable** because `[tool.hatch.envs.types]` adds only mypy and none of the test dependencies. That is a defect in the env definition, not a finding about the code, and it is **not this feature's to fix** (Constitution I, SC-QUALITY-001, FR-PERF-005's provenance rule applied to a non-timing instrument)

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the two records every later phase appends to, created once so no phase invents its own
shape for them.

**⚠️ CRITICAL**: no story phase's measurement or cross-repository claim may be recorded anywhere else.

- [x] T006 Create `specs/015-consumer-gate-closure/baseline.md` with the measurement method (best of three medians of five warm runs, one warm call first, fresh process), the interpreter build from T001, the box's load average, and the branch-point reference table — save **14.297 ms**, descriptor derivation **1.060 ms**, suite **8.93 ms/test**, show load band **16.465–17.750 ms** (median 16.864, n=16, three windows) — plus the 115% tolerance and the sampling rule behind it (FR-PERF-001, FR-PERF-002, FR-PERF-005)
- [x] T007 Create `specs/015-consumer-gate-closure/migration-guide.md` with its section skeleton: the sibling obligations (FR-008, FR-046, FR-103), the sanctioned golden event (FR-074), the operator triage question (FR-058), the cross-repository assertion-class split (FR-080), and the planning-folder disposition table (FR-093)
- [x] T007a Create `specs/015-consumer-gate-closure/consumers_works.md` with one row per obligation this feature places on another repository — **ten**, measured 2026-10-13 and already written up in that file — each carrying: the repository, what it must do, the test node or artefact that marks it done, whether it flips on a library change alone, and a status column carrying a **measured** status, never a prediction. The document is already drafted from the measured sites; this task is to carry each row's status forward as the feature lands and to keep it reconciled. The **nine gate items** carry **ten obligations** and are **not** symmetric: four of the obligations complete when the library lands, six have a half this repository cannot write, and the gate list had no column for the difference — which is how three obligations came to exist only as a sentence in a contract document (FR-106, FR-106a, FR-106b, SC-012b)
- [x] T008 [P] Add the before/after repairability comparison helper to `tests/support/` so SC-005a is checkable by one call rather than by hand, reading the T003 snapshot

**Checkpoint**: the instrument and the records exist — story phases can begin. Three records, not
two: `baseline.md` for figures, `migration-guide.md` for cross-repository and golden events, and
`consumers_works.md` for what other repositories must do.

---

## Phase 3: User Story 1 — An operator saves a project's configuration for the first time (Priority: P1) 🎯 MVP

**Goal**: G1. The canonical path of a configuration file that does not exist yet is obtainable, for
both the node-level and the project-level conventions, without any consumer reconstructing
`projects/<uname>/<file>`.

**Independent Test**: ask for the write target of an absent file with existence tolerated; assert the
path is returned rather than refused, that it is canonical, and that a document saved to it reloads
equal.

### Tests for User Story 1 (REQUIRED) ⚠️

> Write these first and watch them fail.

- [x] T009 [P] [US1] Contract test that `ConfigBase.conf_path` and `ConfigManager.project_path` both accept keyword-only `must_exist=False` and return the canonical path for an absent file, in `tests/contract/test_tolerant_write_target.py` (FR-001, FR-004)
- [x] T010 [P] [US1] Contract test in `tests/contract/test_tolerant_write_target.py` that `must_exist=True` is the default and still raises `FileNotFoundError` with today's message for an absent file, and that the tolerance is **not** reachable positionally (FR-002, FR-003)
- [x] T011 [P] [US1] Unit test in `tests/unit/test_tolerant_path_side_effects.py` that resolving a tolerated target creates no file and no directory (FR-005)
- [x] T012 [P] [US1] Integration test in `tests/integration/test_first_save_journey.py` that a configuration document saved to a tolerated target is created and reloads with equal values, and that a target whose **parent directory** is absent still fails at write time (FR-001 acceptance 3 and 4)

### Implementation for User Story 1

- [x] T013 [US1] Add keyword-only `must_exist: bool = True` to `ConfigBase.conf_path` in [src/cuemsutils/tools/ConfigBase.py:147](src/cuemsutils/tools/ConfigBase.py#L147), raising exactly as today when it is `True` (contract C1)
- [x] T014 [US1] Add keyword-only `must_exist: bool = True` to `ConfigManager.project_path` in [src/cuemsutils/tools/ConfigManager.py:907](src/cuemsutils/tools/ConfigManager.py#L907), keeping the single definition of the `projects/<uname>/<file>` convention (FR-004)
- [x] T015 [US1] Document both helpers' missing-file behaviour, and the four save accessors' default-path behaviour for a missing file, in the docstrings of [src/cuemsutils/tools/ConfigBase.py:147](src/cuemsutils/tools/ConfigBase.py#L147) and [src/cuemsutils/tools/ConfigManager.py:907](src/cuemsutils/tools/ConfigManager.py#L907) so the rendered API documentation carries it (FR-006, FR-UX-003, SC-QUALITY-001)
- [x] T016 [US1] Retire the public-method monkeypatch at `tests/integration/test_config_manager_save_accessors.py:77` (FR-007) — the defect's in-repository footprint. ⚠ **Restated by the analyze pass, because `must_exist=False` alone cannot replace it**: that `monkeypatch.setattr(config_manager, "project_path", …)` does **two** jobs, and only one of them is the missing-file tolerance. It also **relocates** the project to `tmp_path/project`, which is outside the fixture's `CUEMS_CONF_PATH` root — the tolerant call returns the canonical `<conf>/projects/<uname>/<file>`, a different directory. So: move the `project_config_manager` fixture's project **inside** the conf root (`conf_dir/projects/test_project/`), drop the monkeypatch, and let `project_path(…, must_exist=False)` answer. The fixture's own docstring names `FileNotFoundError` as the reason it exists, which is the half this feature fixes; the relocation half must be fixed by moving the fixture, not by the new flag
- [x] T017 [US1] Record in `migration-guide.md` that `cuems-editor`'s strict xfail for G1 does **not** flip on this library change alone: that repository must pass the flag on at its own `_config_path` write site (FR-008, contract C1's consumer note)

**Checkpoint**: a write target for a file that does not exist is public, keyword-only, and
side-effect free. The two API goldens are now stale and **stay stale on purpose** until the polish
phase's single golden event (T026, moved there by the analyze pass) — `public_api.json` also records
every public error class, so S1's addition in Phase 9 moves it too, and re-cutting here would mean
re-cutting twice.

---

## Phase 4: User Story 2 — An operator edits a project's settings in the UI (Priority: P1)

**Goal**: G2. `project_settings` becomes publicly readable as a wire-shaped projection, through the
**same** projection body as every other section.

**Independent Test**: load a project whose `settings.xml` exists, project it, feed the projection
back through ingestion, save, reload, compare equal.

**Why this phase follows US1 immediately**: research R6 found they are one user journey — with an
empty document present after a tolerant load, `save_project_settings` works for a project's first
save as soon as G1 supplies the write target. One integration test covers both; both re-cut the same
two API goldens.

### Tests for User Story 2 (REQUIRED) ⚠️

- [x] T018 [P] [US2] Contract test that `'project_settings'` is a member of the public section set and that the error enumerating valid sections names it, extending `tests/contract/test_config_accessor_names.py` (FR-012)
- [x] T019 [P] [US2] Integration test in `tests/integration/test_project_settings_roundtrip.py` that `to_wire('project_settings')` → `from_json(SchemaName.PROJECT_SETTINGS, …)` → `save(path)` → reload compares **equal** (FR-013, contract C2)
- [x] T020 [P] [US2] Contract test in `tests/contract/test_project_settings_read.py` that a load which found **no** file projects `{}` — not `{"setting": []}` and not an error — and that it is identical to the projection of a file that exists and holds no settings (FR-015)
- [x] T021 [P] [US2] Contract test in `tests/contract/test_project_settings_read.py` that a manager whose project configuration was **never loaded** still raises the existing "not loaded" exception, so the two states stay distinguishable (FR-015a)
- [x] T022 [P] [US2] Contract test in `tests/contract/test_project_settings_read.py` that the projection reaches the **same** projection body as every other section — asserted structurally, not by comparing output (FR-011, FR-014)
- [x] T023 [US2] Extend `tests/integration/test_first_save_journey.py` to the full G1+G2 journey: a project with no `settings.xml` is loaded, its empty document projected, edited, saved to the tolerated target, and reloaded carrying the edit (R6's synergy, SC-001, SC-002)

### Implementation for User Story 2

- [x] T022a [P] [US2] Contract test in `tests/contract/test_project_settings_read.py` that the **accessor answers with the document object** (`CuemsProjectSettingsType`) and **not** a raw `dict`, and that the wire dictionary is what projecting the section returns. ⚠ Added by the second analyze pass: only `contracts/public-surface.md` C2 stated the accessor's return type, and the shape is load-bearing twice over — `to_wire` reads the named section off the manager and calls `to_wire()` on what it finds (so a dict raises instead of projecting), and `tests/contract/test_config_object_surface.py` asserts **no** inventoried accessor returns a raw `dict`. That second test reads its accessor set from the recorded inventory, so a dict-returning property would pass this story's own tests and fail only when T026 re-cuts the inventory golden, six phases later (FR-010, contract C2)
- [x] T024 [US2] Set the absent-file branch of `ConfigManager.load_project_settings` ([src/cuemsutils/tools/ConfigManager.py:494](src/cuemsutils/tools/ConfigManager.py#L494)) to an empty `CuemsProjectSettingsType()` instead of leaving the held document `None`, keeping the "never loaded" state untouched (data-model §2, FR-015, FR-015a)
- [x] T025 [US2] Add the public `project_settings` property to `ConfigManager` — **returning the held `CuemsProjectSettingsType`, never a dict** (contract C2; the wire form is `to_wire('project_settings')`) — and `'project_settings'` to `_PROJECTABLE_SECTIONS` ([src/cuemsutils/tools/ConfigManager.py:166](src/cuemsutils/tools/ConfigManager.py#L166)), with no change to `to_wire` itself. While here, extend `to_wire`'s own `section:` docstring list, which already omits the two project sections it accepts (FR-010, FR-011, FR-012, FR-UX-003)
- [x] T027 [US2] Document the property's contract in its docstring in [src/cuemsutils/tools/ConfigManager.py](src/cuemsutils/tools/ConfigManager.py) — what it answers after a load that found the file, after a load that found none, and before any load — and state that existence remains the consumer's own question through G1's existence-checking form, so the projection acquires no existence flag (FR-015b, FR-UX-003, contract C2)
- [x] T027a [US2] Record G2's consumer-side obligation in `consumers_works.md`: `cuems-editor`'s xfail for this gate does **not** flip on a library change alone either — that repository must remove `project_settings` from its refusal set and give it a load step. Symmetric with T017's G1 entry, which was the only such obligation the spec had written down (FR-017, SC-012a)
- [x] T028 [US2] Leave the always-empty **`project_conf`** dictionary alone and mark it in [src/cuemsutils/tools/ConfigManager.py](src/cuemsutils/tools/ConfigManager.py) as a separate latent defect deliberately not repaired here (FR-016)

**Checkpoint**: all four configuration domains are readable and writable from the public surface
where three were. US1 and US2 together close the first-save journey. Both API goldens remain stale
until the polish phase, by design (T026).

---

## Phase 5: User Story 3 — A deployed node's `settings.xml` migrates with the shipped tools (Priority: P1)

**Goal**: G5. The `settings` version step finds and drops the two retired counts whether or not the
document's players have been reshaped — the one item here that is a **defect**, and the one that
makes an ordinary deployed node un-migratable today.

**Independent Test**: point `cuems-reshape-devices` at a document that is **both** pre-013 (flat
players) and pre-F3 (carrying the retired counts) and assert it is reshaped and then loads.

### Tests for User Story 3 (REQUIRED) ⚠️

> **FR-053**: the red test is the **composition**. A unit test on the converter with an
> already-reshaped tree would pass the moment paths are added and would not catch the next instance
> of this class.

- [x] T029 [P] [US3] Add the pre-013 + pre-F3 fixture (flat players carrying `audio_cards` and `universes`) under `tests/data/`, sourced from `../cuems-nodeconf` at `4d7c91d` and recorded with that provenance — the input T030–T033's composition tests need (FR-053, SC-003)
- [x] T030 [US3] Integration test in `tests/integration/test_reshape_pre_f3_composition.py` that the reshape tool **reshapes and writes** the T029 fixture rather than skipping it, and that the result then **loads**, with both retired counts gone and each drop named in the load report (FR-050, FR-057, SC-003)
- [x] T031 [P] [US3] Integration test in `tests/integration/test_reshape_pre_f3_composition.py` that a flat document **without** the retired counts still migrates cleanly — the eight-day window between F3 and the reshape is a real population (FR-055)
- [x] T032 [P] [US3] Integration test in `tests/integration/test_reshape_pre_f3_composition.py` that a second run over an already-migrated document changes no bytes (FR-052)
- [x] T033 [P] [US3] Integration test in `tests/integration/test_reshape_pre_f3_composition.py` that a version-old `script` still completes through both tools in the documented order — reshape, then convert — so the fix does not invert the deadlock 013 resolved deliberately (FR-054)
- [x] T034 [P] [US3] Unit test in `tests/unit/test_settings_version_step_shapes.py` that the step locates the retired counts under **both** the flat path and the reshaped `players/player[@class='…']` predicate path, and is idempotent when neither is present (FR-051, FR-052)

### Implementation for User Story 3

- [x] T035 [US3] Address both player spellings in one loop in `_settings_1_to_2` ([src/cuemsutils/xml/versioning.py:321](src/cuemsutils/xml/versioning.py#L321)), dropping each retired count wherever it is found (FR-050, FR-051, R7)
- [x] T036 [US3] Answer R7's open sub-question in [src/cuemsutils/xml/versioning.py:321](src/cuemsutils/xml/versioning.py#L321): determine from `src/cuemsutils/xml/schemas/settings.xsd` whether a document may carry more than one `<node>` section, and either generalise the singular `Settings/node` lookup or record in the code why singular is correct (data-model §7, research R7)
- [x] T037 [US3] Confirm `cuems-reshape-devices` ([src/cuemsutils/xml/reshape_devices.py](src/cuemsutils/xml/reshape_devices.py)) still refuses to write a document that would not validate — the fix makes more documents valid and must not relax the guarantee (FR-056)
- [x] T038 [US3] Document the operator-facing triage question in `migration-guide.md` as *"does it carry the retired counts?"* with the `grep -cE '<(audio_cards|universes)>'` check, explicitly not *"is it flat-shaped?"* — two different populations (FR-058)
- [x] T039 [US3] Verify SC-003 against the reference population, **restored by the refs located 2026-10-13** rather than by description — the documents exist in no working tree, because 014's gate pass hand-rewrote them, which is the cost SC-004 says stops at two:
  - **9** from `git -C ../cuems-power-bridge show dd1256f^:tests/fixtures/network_map/map-{controller-only,incomplete,mixed,no-self,none-adopted,partial-resolve,pre007,two-adopted,unresolvable}/settings.xml`
  - **2** from `git -C ../cuems-nodeconf show 61c5705^:tests/fixtures/etc_cuems/settings{,_sentinel}.xml`

  Run the fixed tool over restored copies and record **11 of 11** migrating with **one** invocation in `baseline.md`, against the control figure of 0 of 11 at the branch point (SC-003, SC-004)
- [x] T039a [US3] Migrate the **one surviving live** dead-end document and record it separately from the historical eleven: `../cuems-engine/dev/test_xml_files/settings.xml` carries the retired counts at that repository's tip — measured 2026-10-13, the only such document across all seven checkouts, and therefore the one a developer actually hits. Close it in that checkout per FR-105 rather than leaving it for the next gate (SC-003a, FR-105). ⚠ **Measured, and the premise does not hold**: the fixed tool correctly reshapes this document's flat players, but validation then refuses it for an unrelated, pre-existing reason — the **entire** `dev/test_xml_files/` directory in that repository (all ten documents, not only this one) carries a stale pre-rename namespace (`http://stagelab.net/cuems` against this schema's `https://stagelab.coop/cuems/`). No backup was left and no bytes were changed (the tool validates before writing). Patching one file's namespace in isolation would misrepresent a directory-wide defect in a sibling repository as closed; recorded in `consumers_works.md` row 7 as a new finding for that repository rather than forced to a false "done"

**Checkpoint**: the defect is closed and the measured dead-end population migrates. No further hand-
rewrite of a `settings.xml` is required by any repository.

---

## Phase 6: User Story 5 — An operator labels a node and the label persists (Priority: P1)

**Goal**: G4. An in-place `set_alias` on the node index, validating before mutating — the one
`cuems-nodeconf` item inside 015 per D4, and what unblocks that repository's `node_set` action.

**Independent Test**: set a label on an index; assert the node object the document holds is the one
that changed, that the document saves carrying it, and that the signature moved.

### Tests for User Story 5 (REQUIRED) ⚠️

- [x] T040 [P] [US5] Extend `tests/contract/test_node_aliasing.py` to `set_alias`: the mutation is **in place** on the node object the document holds, not a rebound copy (FR-039, FR-040)
- [x] T041 [P] [US5] Unit test in `tests/unit/test_set_alias_validation.py` that an empty or whitespace-only label **raises before anything is touched**, measurable as: the index is unchanged and the document still saves afterwards (FR-036, SC-008)
- [x] T042 [P] [US5] Unit test in `tests/unit/test_set_alias_validation.py` that an unknown identity reports failure and mutates nothing, that a valid label reports success, and that clearing with `None` **removes the key** (FR-037, FR-038)
- [x] T043 [P] [US5] Contract test in `tests/contract/test_node_aliasing.py` that setting a label to the value it already has reports success and does **not** move the index signature, so a write-if-changed caller does not write (FR-038, FR-041)
- [x] T044 [P] [US5] Contract test in `tests/contract/test_node_aliasing.py` that an **offline** node and the controller are both labellable — liveness is not a precondition, unlike adoption (FR-043)
- [x] T045 [P] [US5] Contract test in `tests/contract/test_node_aliasing.py` that a discovery **merge** after a label is set does not clear it, pinned by test rather than argued from the merge's implementation (FR-044, SC-007)
- [x] T046 [P] [US5] Integration test extending `tests/integration/test_network_map_chain.py` that a labelled index saves a document carrying the label, and that the label survives an IP change, an adopt and an un-adopt (SC-007)

### Implementation for User Story 5

- [x] T047 [US5] Implement `NodeIndex.set_alias(node_uuid, alias: str | None) -> bool` in [src/cuemsutils/tools/NodeList.py](src/cuemsutils/tools/NodeList.py) — validate, then mutate in place, then report; scope is `alias` **only** (FR-035, FR-036, FR-042, contract C4)
- [x] T048 [US5] State in the docstrings of the map's save and ingest paths — `CuemsNetworkMapType.save()` in [src/cuemsutils/config/network_map.py](src/cuemsutils/config/network_map.py) and `ConfigManager.save_network_map()` — that the file has exactly **one runtime writer** and that any other writer's changes are reverted at that writer's next write (FR-045, FR-UX-003); two consumers have already read those calls as the way to persist a UI edit
- [x] T049 [US5] Verify `NodeIndex.signature` ([src/cuemsutils/tools/NodeList.py:272](src/cuemsutils/tools/NodeList.py#L272)) already includes `alias` and record it in `baseline.md`, rather than changing the signature (FR-041, verified on this branch)
- [x] T050 [US5] Verify the semantics against `../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4 word for word and record the agreement in `migration-guide.md` — any divergence is a change to a two-repository contract (FR-046, SC-013)

- [x] T049a [US5] **Add `NodeIndex` to the tracked public surface** in `tests/contract/test_public_api_surface.py`'s `PUBLIC_CLASSES` (`("cuemsutils.tools.NodeList", "NodeIndex")`), so `set_alias` acquires a recorded signature and the polish-phase re-cut captures it. ⚠ Added by the second analyze pass, which measured that **`NodeIndex` is in neither API golden**: the tracked classes are `CuemsScript`/`ConfigManager`/`ConfigBase` and the tracked functions are `partition_by_adoption`/`validate_config_document`, so T026's claim to cover `NodeIndex.set_alias` was false and this gate's public addition would have landed with no public-surface record at all. Since feature 007 this module has been *"the only public path to the node model"*, so the gap predates this feature; maintainer decision 2026-10-13 is that it joins (FR-041a, FR-074)
- [x] T050a [US5] Record G4's consumer-side obligation in `consumers_works.md`, and note that it is the **only** gate whose sibling half is in a *second* repository: `cuems-editor`'s xfail flips when this setter lands **and** `cuems-nodeconf` ships the `node_set` handler that calls it. This feature delivers the library half and discharges nodeconf's stated ordering; it ships neither repository's code (FR-047, SC-012a, SC-013)

**Checkpoint**: `cuems-nodeconf`'s `node_set` is implementable and its ordering statement — *"the
library first, then this repository"* — is discharged. `NodeIndex` is now a tracked public class
(T049a), so the polish-phase re-cut records `set_alias`' signature; before that task it recorded
nothing about the node model at all. The editor's G4 xfail does **not** flip yet,
and `consumers_works.md` says so rather than leaving it to be discovered.

---

## Phase 7: User Story 7 — A descriptor-driven form renders an open field as a field (Priority: P2)

**Goal**: S2. A union reports a closed choice set only when **every** member is an enumeration.

**⚠️ This P2 story is promoted ahead of P1's US4 by a hard dependency.** Seeding rule 2 reads a
union's member types directly; before this narrowing a union's merged member enumerations are
reported *as* the type's own enumeration, so rule 1 fires and returns the right value for the wrong
reason — and the test meant to pin rule 2 passes vacuously (plan, *Implementation sequencing*;
contracts/seeding-rules.md, rule 2).

**Independent Test**: derive each schema's descriptor and assert that no field whose type is a union
with a non-enumerated member reports a closed set of choices.

### Tests for User Story 7 (REQUIRED) ⚠️

- [x] T051 [P] [US7] Contract test in `tests/contract/test_union_not_enumeration.py` that **all five** measured sites stop reporting a one-value choice set — `uuid` on `NodeType`, `NodeConfType` and `NodeMappingType`, and `output_latency_ms` on `AudioPlayerType` and `VideoPlayerType` (FR-067, SC-010)
- [x] T052 [P] [US7] Unit test extending `tests/unit/test_descriptor_enums.py` that a union **all** of whose members are enumerations keeps reporting their merged values — the narrowing is conditional, not a removal (FR-066, FR-068)
- [x] T053 [P] [US7] Unit test in `tests/unit/test_descriptor_enums.py` that every **other** descriptor fact for the five affected fields is unchanged (FR-029)

### Implementation for User Story 7

- [x] T054 [US7] Narrow `_enum_values` in [src/cuemsutils/xml/descriptor.py:116](src/cuemsutils/xml/descriptor.py#L116) to report merged member enumerations only when every union member is an enumeration (FR-066, contract C6)
- [x] T055 [US7] Correct the documentation beside `_enum_values` in [src/cuemsutils/xml/descriptor.py:116](src/cuemsutils/xml/descriptor.py#L116) that treats the partial merge as the feature — it names `AutoOrIntLatencyMsType` as the case it handles, which is one of the five sites being fixed (FR-069)

**Checkpoint**: SC-010's 5 becomes 0, verified against T004's snapshot. Seeding rule 2 can now be
pinned non-vacuously.

---

## Phase 8: User Story 4 — A client builds a document from the descriptor and it saves (Priority: P1)

**Goal**: G3, the widest item here. The per-type instance becomes wire-shaped **and saveable**,
produced by projecting a populated value through the **same** encoder `to_wire()` uses — so the wire
shape is structural rather than re-derived (R2).

**Independent Test**: for each schema, take the root instance and each nested type instance the
consumers name, and assert it saves through this library's own write path without hand editing.

### Tests for User Story 4 (REQUIRED) ⚠️

- [x] T056 [P] [US4] Contract test in `tests/contract/test_instance_seeding.py` for the seeding table's **completeness**: every pattern-restricted simple type reachable from any instance in the six schemas has an entry, so a sixth pattern added to any schema fails rather than silently seeding nothing (contracts/seeding-rules.md, guard 1)
- [x] T057 [P] [US4] Contract test in `tests/contract/test_instance_seeding.py` for the table's **validity**: every entry validates against its own declared type (contracts/seeding-rules.md, guard 2)
- [x] T058 [P] [US4] Contract test in `tests/contract/test_repairability_invariance.py` that **zero** fields change repairability classification and **zero** per-field `default` facts change, compared against T003's snapshot through T008's helper (FR-026a, SC-005a)
- [x] T059 [P] [US4] Contract test extending `tests/contract/test_descriptor_instances.py` that a repeated complex field nests as a **list of singly-keyed objects** in every schema — `node_list`, `channels`, `defaults` — not as an object holding a list (FR-020)
- [x] T060 [P] [US4] Contract test in `tests/contract/test_descriptor_instances.py` that a cue-output instance carries the body wrapper the wire carries (FR-021), and that a root whose type has a single anonymous complex child **expands** it rather than reporting `null` — measured today for `CuemsSettings/Settings` and `CuemsProject/CuemsScript` (FR-022)
- [x] T061 [P] [US4] Integration test in `tests/integration/test_instance_saves.py` that **every** schema's root instance saves through this library's own write path unmodified (FR-023, SC-005)
- [x] T062 [P] [US4] Integration test in `tests/integration/test_instance_saves.py` that a cue built from a cue instance saves as part of a script, and that each nested type instance the consumers name saves as part of its containing document (FR-024)
- [x] T063 [P] [US4] Unit test in `tests/unit/test_seeding_rules.py` covering the **eight** ordered rules and the **seven** built-ins — one case per rule, keyed on the **resolved simple type** and never on the field's name (FR-025, FR-026b, FR-028). ⚠ The counts were inverted here and disagreed with `contracts/seeding-rules.md` and T067: there are eight rules (1–6 facet-derived, 7 the five-entry pattern table, 8 the seven-entry built-in table), 30 named simple types of which 25 are facet-derived, and 7 built-ins
- [x] T064 [P] [US4] Unit test in `tests/unit/test_seeding_rules.py` that a field whose default is a **callable** is still seeded `null`, the callable is **not invoked**, and it stays visible on the field (FR-027)
- [x] T065 [P] [US4] Unit test in `tests/unit/test_instance_single_child.py` for the two-shape element lookup that resolves an anonymous single child by path (R1)
- [x] T066 [P] [US4] Contract test in `tests/contract/test_descriptor_instances.py` that nothing non-serialisable enters an instance and that the recursive-type cycle guard still bounds by branch (FR-030, data-model §3 invariant 7)

### Implementation for User Story 4

- [x] T067 [US4] Implement the seeding rules in [src/cuemsutils/xml/descriptor.py](src/cuemsutils/xml/descriptor.py) as one mechanism over the field's resolved simple type — rules 1–6 over facets, rule 7's five-entry type-keyed pattern table, rule 8's seven built-ins — with the model class's declared default taking precedence over any seed (FR-025, FR-028, contracts/seeding-rules.md)
- [x] T068 [US4] Resolve the anonymous single complex child in `_instance_for` ([src/cuemsutils/xml/descriptor.py:218](src/cuemsutils/xml/descriptor.py#L218)) by `derive_path(schema, f"{spec.key.name}/{key}")`, reusing the guard conditions of `Mapper._anonymous_child` and `Mapper._child_spec_for` verbatim — **do not** widen `spec._type_key`, which 27 consumers read, two of them as the definition of a leaf (FR-022, R1)
- [x] T069 [US4] In [src/cuemsutils/xml/descriptor.py](src/cuemsutils/xml/descriptor.py), build the instance as a fully-populated value and project it through `Mapper.encode_wire` — the same call `to_wire()` uses — so the wrapper and the nesting are structural and a later change to the wire shape moves the instance with it (FR-020, FR-021, FR-031, R2)
- [x] T070 [US4] Populate **optional** fields too in [src/cuemsutils/xml/descriptor.py](src/cuemsutils/xml/descriptor.py), so `_encode_wire_value`'s omit-if-optional-and-empty rule has nothing to omit and a nested shape including `canvas_region` survives the projection (R2's consequence, R3 decision 3, data-model §3 invariant 3)
- [x] T071 [US4] Record the FR-026 reversal in `TypeDescriptor.instance`'s docstring in [src/cuemsutils/xml/descriptor.py](src/cuemsutils/xml/descriptor.py), beside the code it reverses — `TypeDescriptor.instance`'s own docstring currently states that an instance is *"not required to be schema-valid… a seed the consumer fills"* — carrying the measurement behind it (64 required-with-no-default scalar fields across 19 types in the show schema alone) and FR-026a's reason for seeding instance-locally rather than through model defaults (FR-026, Constitution I)
- [x] T071a [US4] **Publish G3's contract at its rendered public entry point**: state, in `ConfigManager.get_schema_descriptor`'s docstring ([src/cuemsutils/tools/ConfigManager.py:712](src/cuemsutils/tools/ConfigManager.py#L712)), what a client may now rely on from a `TypeDescriptor.instance` — wire nesting, the cue-output wrapper, the expanded single complex child, that every root instance **saves** unmodified, and that a callable default is still not invoked. ⚠ Added by the second analyze pass, which found that the widest consumer-facing change in this feature would have been stated **only** in `cuemsutils.xml.descriptor` — a module `docs/` renders nowhere. By maintainer decision 2026-10-13 the fix is to document it here, not to publish the module: `cuemsutils.xml` is private by decision (`__all__ == []` since 006) and becomes private in fact with the deprecated-surface release, and `get_schema_descriptor` is the only rendered call that hands a client a descriptor. T071's record beside the reversed code stays — the two are complements (FR-UX-003c, FR-026, FR-020..FR-027)
- [x] T072 [US4] Confirm in [src/cuemsutils/xml/descriptor.py](src/cuemsutils/xml/descriptor.py) that the five pre-existing per-type descriptor facts keep their meaning and that `FieldDescriptor.default` is unchanged (FR-029, contract C3)

**Checkpoint**: a client can build any configuration document, and any cue output, from the
descriptor's instance and save it with zero hand-authored values and zero local reshaping (SC-005).

---

## Phase 9: User Story 6 — A consumer reports a duplicate node identity without parsing prose (Priority: P2)

**Goal**: S1. The colliding identity and the hardware addresses that distinguish the rows become
**data**, in two layers — an internal `ValueError` subclass raised by the rule, promoted to a public
`ValidationError` subclass by the accessor (R4).

**Independent Test**: load a map with one identity on two rows; assert the raised error carries the
identity and its hardware addresses as structured data, and that the consumer's regular expression
becomes unnecessary.

### Tests for User Story 6 (REQUIRED) ⚠️

- [x] T073 [P] [US6] Contract test in `tests/contract/test_collision_structured.py` that loading a colliding map raises a **nameable** `ValidationError` subclass carrying the colliding identity, the hardware addresses, the file path, and a `violation` located as `(identity, "uuid")` (FR-060, FR-060a, FR-060b, FR-061, FR-065)
- [x] T074 [P] [US6] Contract test in `tests/contract/test_collision_structured.py` that the new type is exported from `cuemsutils.errors.__all__` and placed in the module's documented hierarchy (FR-065a)
- [x] T075 [P] [US6] Contract test in `tests/contract/test_collision_structured.py` that the operator-facing **message is unchanged**, including its remedy sentence and the command it names (FR-063, FR-UX-002)
- [x] T076 [P] [US6] Contract test extending `tests/contract/test_node_uuid_unique_rule.py` that the internal exception remains a `ValueError`, so `isinstance(exc, ValueError)` still holds everywhere it holds today and `tests/golden/outcomes.json`'s raw verdicts are unaffected (R4, data-model §6 invariant 1)
- [x] T077 [P] [US6] Contract test in `tests/contract/test_collision_structured.py` that the existing message-shape recognition keeps answering for any caller still on it, recognising exactly the cases it recognises today (FR-064)
- [x] T078 [P] [US6] Integration test extending `tests/integration/test_collision_routes.py` that **two distinct** collisions in one document are distinguishable without re-parsing text, so a consumer can log once per distinct identity (FR-062)

### Implementation for User Story 6

- [x] T079 [US6] Raise an **internal** `ValueError` subclass carrying the collisions as data from `check_node_identities_unique` ([src/cuemsutils/xml/validators.py:860](src/cuemsutils/xml/validators.py#L860)) — it stays a `ValueError` because `xmlschema`'s own validation error is one too, so `isinstance` cannot separate a semantic from a structural failure (R4)
- [x] T080 [US6] Add `NodeIdentityCollisionError(ValidationError)` to [src/cuemsutils/errors.py](src/cuemsutils/errors.py) with `collisions`, `file` and the inherited `violation` slot, its `__all__` entry and its place in the documented hierarchy — the module's first addition since feature 009's (FR-060, FR-065a, contract C5)
- [x] T080a [US6] **Extend the hand-maintained surface record the new class must appear in**, in the same change as T080: `tests/contract/test_public_api_surface.py`'s `PUBLIC_ERRORS` tuple (9 names today) gains `NodeIdentityCollisionError`, with the one-line reason beside it in the shape the existing entries use (008's report types, 009's `DmxChannelDecodeError`). ⚠ Added by the second analyze pass, and it is load-bearing in **both** directions: that list is asserted equal to `cuemsutils.errors.__all__`, so T080 alone turns an existing contract test **red**; and the golden's `errors` section is **generated from the list**, so re-cutting at T026 without this produces a golden that does not contain the new class — which is the premise on which the golden event was scheduled after every public addition (FR-065c, FR-065a, FR-074)
- [x] T081 [US6] Promote the internal exception to the public type in `ConfigBase.load_config_document` ([src/cuemsutils/tools/ConfigBase.py:21](src/cuemsutils/tools/ConfigBase.py#L21)), attaching the file path and populating the violation — placed so the ordered handlers still reach it, since `except ValidationError: raise` precedes the clause that attaches the path (R4, contract C5)
- [x] T082 [US6] Document on the new type in [src/cuemsutils/errors.py](src/cuemsutils/errors.py) that the structured payload is the supported interface and a regular expression over the message is not, so the sentence stops being a load-bearing interface no test on either side declares (FR-065, FR-UX-003, SC-009)
- [x] T082a [US6] Record S1's consumer-side completion marker in `consumers_works.md`: `cuems-editor` removes its anchored pattern over this library's prose **and** the empty-string fallback behind it, and its handler names `NodeIdentityCollisionError`. That removal — not a test passing here — is what SC-009 measures, and it is verified in that checkout by T105d (FR-065b, SC-009)

**Checkpoint**: `cuems-editor`'s anchored pattern and its empty-string fallback can both be removed
and its handler can name the exception type — the library half is in; the removal itself is that
repository's, recorded by T082a and **verified in that checkout by T105d** (SC-009). ⚠ This
checkpoint credited **T103**, which is the candidate-tag documentation task and has nothing to do
with it; SC-009 had no verification task at all until T105d.

---

## Phase 10: User Story 8 — A hand-maintained configuration file stays readable after a UI save (Priority: P2)

**Goal**: S3. Every document this library writes is indented and line-broken, by one code path.

**Why this phase is last of the code changes**: it re-cuts six XML goldens and re-authors two corpus
documents. Landing it earlier means every later change is reviewed against freshly moved goldens
(plan, *Implementation sequencing*).

**Independent Test**: save a configuration document and assert the written bytes carry line breaks
and indentation; then assert the writer is still idempotent and still produces a document that
reloads equal.

### Tests for User Story 8 (REQUIRED) ⚠️

- [x] T083 [P] [US8] Contract test in `tests/contract/test_writer_indentation.py` that any document this library writes is indented and line-broken — the written line count is greater than one and within ±1 line of the equivalent hand-indented form, and a save that changes one element's text produces a diff of at most **3** changed lines against the prior hand edit (FR-070, SC-011, contract C7)
- [x] T084 [P] [US8] Contract test in `tests/contract/test_writer_indentation.py` for **idempotence**: a document this library wrote, reloaded and rewritten, is byte-identical (FR-071)
- [x] T085 [P] [US8] Contract test in `tests/contract/test_writer_indentation.py` that indentation alters no element's text where that text is data, exercised against `script:UiPropertiesType` — the **one** mixed-content type across all six schemas (FR-073, R8)
- [x] T086 [P] [US8] Contract test in `tests/contract/test_writer_indentation.py` that encoding, the XML declaration, the `cms` prefix registration, the preserved target file mode, and the temporary-plus-atomic-replace behaviour are all unchanged — each has a recorded failure behind it, two of them outages (FR-072, contract C7)

### Implementation for User Story 8

- [x] T087 [US8] Call `xml.etree.ElementTree.indent(tree, space="  ")` immediately before `tree.write` inside `write_tree` ([src/cuemsutils/xml/documents.py:289](src/cuemsutils/xml/documents.py#L289)), so one code path indents every document and FR-072's five guarantees stay in one place (FR-070, R8) **Extended 2026-10-14 by maintainer decision**: the call lives in a new `documents.serialize_tree`, the one serialization point; `write_tree`, `cuems-init-node`'s `_serialize` (the `/etc/cuems` documents) and `XmlReaderWriter.write` all go through it, and `test_only_documents_serializes_an_element_tree` guards against a fourth writer. The frozen legacy `XmlBuilder.py` is the only excluded path.
- [x] T090 [US8] Re-author `tests/data/corpus/cuems-utils/fade_showcase.xml` and `tests/data/corpus/cuems-utils/unicode_showcase.xml` by hand in the writer's new output form, so their first-cycle byte-identity claim still holds rather than being quietly reclassified (FR-075)
- [x] T090a [US8] **Re-author the three 007 pre-state documents** in the writer's new output form — `specs/007-node-model-migration/pre-state/network_map.xml`, `pre-state/corpus/cuems-utils/network_map.xml`, `pre-state/corpus/cuems-engine/network_map.xml` — because `tests/contract/test_network_map_roundtrip.py` diffs what `save()` writes against them and asserts the diff is **exactly two lines**, on the stated ground that *"the whole document is one line after normalisation"*. ⚠ Added by the second analyze pass; measured 2026-10-13, all three are one line, so indenting turns that diff into the whole document for all three parametrized cases. Re-authoring rather than comparing parsed trees, by maintainer decision: that test's value is that the `node_type` → `node_role` rename is readable **in a diff**, which a structural comparison would lose. The three files are input data, so this stays in US8 with T090 rather than joining the polish-phase golden event (FR-075a, FR-072)
- [x] T091 [US8] Update `tests/contract/test_roundtrip_stability.py`'s `FIRST_CYCLE_IS_IDENTITY` and `REFORMATTED` sets if a hand-authored document in the second set becomes identity, and record the flip as **this decision** — that test's own docstring requires it to be *"a decision rather than a drift"* (FR-076)
**Checkpoint**: all nine stories' code is in. A hand-maintained `settings.xml` survives a UI save
readable, and the writer is still atomic, mode-preserving and idempotent. **The goldens are now
stale and stay stale** until the polish phase's single event (T026, T088, T089, T092) — moved there
by the analyze pass, because `public_api.json` records every public error class and so S1's Phase-9
addition moves it too. Re-cutting in two places would have made FR-074's *"one reviewable change"*
true of the record and false of the diff. **The five hand-authored documents are *not* part of that
event and are done here**: the two corpus documents (T090) and the three 007 pre-state documents
(T090a) are input data, so they land with the writer change that makes them stale.

---

## Phase 11: User Story 9 — The planning folder and the arc's records tell the truth (Priority: P3) + Polish & cross-cutting

**Goal**: S4, the sweep, the two measured dispositions of FR-079/FR-080, the sibling verification,
and the budgets. By decision D2 this is the polish phase, and **the nine deletions come last of
all** — FR-090 makes the source document deletable only once every row is implemented or declined,
so deleting it earlier removes the checklist against which that is verified.

**Independent Test**: after this phase, every document named for deletion is gone, every stale
statement named for correction is corrected, and no requirement in this spec is left without a
disposition.

### The sanctioned golden event (FR-074) — moved here by the analyze pass

**Why here and not in US2 and US8.** `tests/golden/api/public_api.json` carries an `errors` section
enumerating **every** public error class with its bases and methods, so S1's
`NodeIdentityCollisionError` (T080, Phase 9) moves it exactly as G1's two signatures and G2's
property do. Re-cutting in Phase 4 and again in Phase 10 would have left the golden stale at the end
of the feature and made FR-074's *"one reviewable change"* a property of the record rather than of
the diff. One block, after every public addition and after the writer change.

- [x] T026 [US9] Re-cut the two API goldens `tests/golden/api/public_api.json` and `tests/golden/api/config_accessors.json` with `capture_goldens --force`, covering **all** of this feature's public additions — US1's two `must_exist` signatures, US2's `project_settings` property, US5's `NodeIndex.set_alias` and **US6's `NodeIdentityCollisionError`**. ⚠ **Two of those four only appear if T049a and T080a have landed**, corrected by the second analyze pass: the goldens' scope is a hand-maintained `PUBLIC_CLASSES`/`PUBLIC_FUNCTIONS`/`PUBLIC_ERRORS` in `tests/contract/test_public_api_surface.py`, not the package's exports — `NodeIndex` was in neither golden, and the `errors` section is generated **from** the tuple rather than from `__all__`. Verify after re-cutting that all four additions are present in the diff, rather than assuming the capture found them (FR-074, FR-041a, FR-065c, R5)
- [x] T088 [US9] Re-cut the six XML goldens with `capture_goldens --force` — `xml/cuems-editor__script_minimal.xml`, `xml/cuems-engine__projects__complex_test__script.xml`, `xml/cuems-engine__projects__empty_test__script.xml`, `xml/cuems-utils__fade_showcase.xml`, `xml/cuems-utils__unicode_showcase.xml`, `generated/example_script.xml` — and update `tests/golden/MANIFEST.sha256` for all eight re-cut files (FR-074)
- [x] T089 [US9] Verify the **24** `dict/` goldens, `generated/example_script.reader.json` and `tests/golden/outcomes.json` did **not** move — a wire dict carries no whitespace, and re-authoring the corpus changes bytes, not decoded values (R8, data-model §8 invariant 3). ⚠ Counted on disk 2026-10-13; three artefacts said 20
- [x] T092 [US9] Record the sanctioned golden event in `migration-guide.md` as **one** entry with its reason, covering T026's two API goldens and T088's six XML goldens plus the manifest — the arc's fourth such event, in the shape of its three predecessors; state that it is scheduled after every public addition **because** the API golden records the error hierarchy, so a later feature adding an exception knows why (FR-074)

### S4 — the projection property (FR-078)

- [x] T093 [P] [US9] State **once**, in `to_wire`'s docstring at [src/cuemsutils/helpers.py:372](src/cuemsutils/helpers.py#L372) — the one place the rendered API documentation picks up for the wire projection — that the projection fills a model default for an optional element the document omitted, and that this is a general property of the projection rather than a fact about any one field — the withdrawn `cuems-editor` UR-3's lasting obligation (FR-078, S4, FR-UX-003)

### FR-079 — the straddled budget

- [x] T094 [US9] Replace the straddled **line** in `tests/integration/test_read_path_regression.py::test_the_show_document_load_is_within_its_recorded_budget` with a comparison against the measured **band**, following 012's R14 precedent for this exact pathology — a change of instrument, not a fourth raise of the budget (FR-079, FR-079a)
- [x] T095 [US9] Make the recorded state visible **in the test** `tests/integration/test_read_path_regression.py`: the band `16.465–17.750 ms`, the median, and the sample count `n=16` across three windows, so a later reader cannot mistake "straddled and accepted" for "passing" (FR-079b)
- [x] T096 [P] [US9] Create `specs/planning/show-document-load-drift.md` as the owned follow-up, carrying all 16 measurements, the budget's history (008 → 35.99, 012 → 15.0, 013 → 16.5), R11's interpreter finding, and the fact that the drift **survived a full interpreter migration across two 3.11.9 builds** — which is what makes it real rather than an instrument artefact; against 013's own 14.07–14.96 ms the band is +13% to +19%. It must **not** be investigated inside this feature and is **not** deleted by FR-091 (FR-079c, SC-PERF-005, R12)

### FR-080 — the four stale cross-repository assertions

- [x] T097 [US9] Add one shared tag resolver to `tests/support/` — given a sibling name, resolve its `xml-refactor-merge-candidate` tag; **skip with a reason** when the checkout or the tag is absent; **fail** when the tag resolves and the claim does not hold (FR-080c, FR-080e, contracts/sibling-gates.md §3)
- [x] T098 [US9] Contract test for the resolver itself in `tests/contract/test_sibling_tag_resolver.py`: an absent checkout skips, an absent tag skips with a different reason, a resolving tag whose tree contradicts a claim fails, and a partial tag set yields a partial honest result — four of seven siblings are tagged today (FR-080c, FR-080e, SC-017a)
- [x] T099 [US9] Re-point `tests/contract/test_migration_guide.py` and `tests/contract/test_migration_guide_names_sites.py` at the resolver, splitting the two assertion classes: **provenance** pins become dated statements whose resolution is no longer asserted, **operator instructions** are asserted at the tag (FR-080, FR-080a)
- [x] T100 [US9] Correct the two false operator-facing claims in `specs/012-uuid4-convergence/migration-guide.md` as a documentation defect, not as a rewrite of history: the coupled engine version (the guide requires `0.1.0rc7`; that tree declares `0.1.0-rev1`, a renamed scheme under which "rc7 or later" is unverifiable) and the status signal an operator is told to watch for, absent from that repository's controller source (FR-080b)
- [x] T101 [US9] Mark, in `specs/013-device-class-reshape/migration-guide.md`, its two provenance pins — `cuems-editor 106015c`, `cuems-frontend 3183845` — with the date of their measurement, recording that both are absent from `git log --all` in their siblings and are therefore dead references rather than moved ones (FR-080a)
- [x] T102 [US9] Re-verify every candidate-tag value this repository records against the tag itself rather than transcribing it (R9's mechanism), and correct `CLAUDE.md`'s three moved values — `cuems-common` `e3c9430` → `91b2d25`, `cuems-nodeconf` `b305c1c` → `c29c25c`, `cuems-power-bridge` `399baf7` → `cabbb3e` — plus `cuems-frontend` `531004b`, whose value was never stated (FR-080f, SC-017c)
- [x] T103 [US9] Document in `migration-guide.md` that re-cutting any candidate tag re-runs the validation across the **whole** set, carrying feature 011's recorded lesson — *a candidate tag set is only as current as its least current member, and no packaging relation expresses that* — and that moving a published tag stays maintainer-only (FR-080d, SC-017b)
- [x] T104 [P] [US9] Confirm FR-081 is not regressed: `tests/contract/test_migration_guide.py` and `tests/contract/test_migration_guide_names_sites.py` still skip with a stated reason when a sibling is not checked out, so a developer without the sibling checkouts is never told a guide is wrong (FR-081)

### Sibling verification (FR-103, FR-104, FR-105)

- [x] T105 [US9] Verify `cuems-editor`'s **seven** strict xfails against that repository's checkout rather than predicting them, each through a **per-session `git worktree`** of this repository — never the shared checkout — and record the result per test node in `migration-guide.md`, including G1's and G2's consumer-side halves which do not flip on a library change alone (FR-103, FR-104, SC-012, contracts/sibling-gates.md §1)
- [x] T105a [US9] Verify **G1's** consumer half in `../cuems-editor` and record the measured status in `consumers_works.md`: whether that repository passes `must_exist=False` on at its own `_config_path` write site, and therefore whether its G1 xfail is still xfailing for a reason this feature owns (FR-008, FR-106a, SC-012a)
- [x] T105b [US9] Verify **G2's** consumer half in `../cuems-editor` the same way: whether `project_settings` is still in its refusal set and whether it has a load step (FR-017, FR-106a, SC-012a)
- [x] T105c [US9] Verify **G4's** two halves — `cuems-editor`'s xfail and `cuems-nodeconf`'s `node_set` handler, the only obligation of this feature's that lives in a third repository — and record both in `consumers_works.md`; *unknown action* at the branch point is the control reading (FR-047, FR-106a, SC-012a, SC-013)
- [x] T105d [US9] Verify **S1's** consumer half in `../cuems-editor`: that the anchored pattern over this library's prose and the empty-string fallback behind it are both removable, and that its handler can name `NodeIdentityCollisionError` — **SC-009's only measurable form**, which had no task and whose checkpoint credited an unrelated one (FR-065b, SC-009, FR-106a)
- [x] T105e [US9] Reconcile `consumers_works.md` with `../cuems-editor/specs/002-config-round-trip/tag-readiness.md` row by row — the two are the same set seen from two repositories and must agree; a row in one and not the other is a missed obligation, which is how G2's, G4's and S1's went unwritten (FR-106, SC-012b)
- [x] T106 [US9] Verify `cuems-frontend`'s side of G3 in `../cuems-frontend`: its one named transform (`toWireShape` plus the starting-values table in its descriptor handler) is deletable in **one** edit with no value hand-authored on its side, confirmed there rather than predicted here (FR-031, SC-006)
- [x] T107 [US9] Run each sibling's suite (`../cuems-editor`, `../cuems-engine`, `../cuems-nodeconf`, `../cuems-power-bridge`, `../cuems-frontend`) in **two arms**, recording both in `migration-guide.md` — at this feature's branch point and on this branch — so no failure is attributed to this feature without a control-arm measurement, 014's cross-cutting lesson that otherwise attributed 151 of someone else's failures to the feature under test (FR-103, SC-014)
- [x] T108 [US9] Close in **this** feature any sibling fixture this feature breaks, in that sibling's own checkout under `../<repo>/`, rather than leaving it for the next gate to discover with its own signal buried underneath — 014's finding, paid for by eleven hand-rewritten documents across two repositories (FR-105)

### The sweep (FR-090..FR-095)

- [x] T109 [P] [US9] Correct the execution companion `specs/planning/etc-cuems-first-install-execution.md`: §3.3's flag **F1**, which describes schema annotations as pending when all six schemas carry them, and §5 step 6, which records 014 as 45/46 with one task open when that feature closed at 46/46 (FR-092)
- [x] T110 [US9] Disposition `specs/planning/refactor-sequencing-2026-10-01.md`: its stop-condition is satisfied — the frontend flow it waited for has landed and carries a candidate tag — but its residue, the adoption/liveness UI tier with *"no other home yet"*, must be **re-homed into a destination that exists before the deletion**, namely a new `specs/planning/adoption-liveness-ui-tier.md` carrying that tier's content and its origin. Create the destination, move the content, **then** delete the source — in that order, because "re-homed" recorded as an intention in a disposition table is how the residue is lost (FR-093, FR-093a)
- [x] T111 [US9] Give `specs/planning/xml-rebuild/` a per-document disposition as a table in `migration-guide.md`, one row per file across the **20** files — the **9** `xml-rebuild-0*.md` design documents (expected *kept*, they are the arc's design argument; counted on disk 2026-10-13, the subtree stops at `-09-consumer-audit.md` and three artefacts said ten) and the 11 under `010-consumer-prompts/` (expected *deletable*, one-shot inputs of the same class as §9.3's seven) — using §9.2's three outcomes: kept with a reason, re-homed, or deleted (FR-093, R12)
- [x] T111a [US9] Disposition the **first-install pair** in the same table: `specs/planning/etc-cuems-first-install.md` (1384 lines; its status line reads *"design settled; feature 011 landed 2026-09-28"*) and `etc-cuems-first-install-execution.md`. ⚠ Added by the second analyze pass as the sweep's **third** gap: neither appears in the source document's §9.1, §9.2 or §9.3, and the execution companion is **corrected** by T109 without ever being dispositioned — so SC-016's claim that the folder holds no document whose work is complete had nothing behind it for a 1384-line design document. The expected outcome is *kept until the coordinated tag is cut, then re-assessed as one pair*, since both describe the 011–015 arc and this feature is its last member; write the reason down either way (FR-093b, SC-016)
- [x] T112 [US9] Make every home of the coordinated tag's work order agree — the execution companion, `CLAUDE.md`, and the gate list — so that *"the tag comes after 011–015"* and *"015 is the gates"* are both true at once (FR-094, SC-017)
- [x] T113 [US9] Audit `specs/015-consumer-gate-closure/` and every `src/` and `tests/` file this feature touched for a feature **number** standing in for a **live obligation** described in another document, replacing each with the document's name or the behaviour (FR-095). **The criterion, because the first reading of this task would have rewritten most of the spec**: the test is whether a reader must look the number up to learn *what they must do*. `ConfigManager`'s refusal reading *"…until feature 015"* is the defect class — a live instruction keyed to a number that had moved. A dated provenance citation of landed work in this repository — "008's load path", "012's R14", "013's 14.07–14.96 ms" — refers to a frozen record that cannot be reassigned, is how this repository's specs cite their own history, and is **in scope for neither replacement nor apology**
- [x] T114 [US9] Verify FR-090's condition document by document: every row of `specs/planning/upcoming-feature-requirements-2026-10-02.md` — G1–G5, S1–S4 and the thirteen settled items — is implemented or recorded as declined, with the disposition written down (FR-090, SC-015)
- [x] T115 [US9] **Last of all**, delete the nine documents whose deletion condition T114 has just verified: the seven landed one-shot prompts (`specs/planning/013-specify-prompt.md`, `editor-specify-prompt.md`, `editor-001-amend-after-013-prompt.md`, `feature-014-sibling-gate-prompt.md`, `nodeconf-uuid4-fixture-migration-prompt.md`, `media-pixel-dimensions-for-xml-refactor.md`, `stored-media-values-preimplementation.md`), plus `upcoming-feature-requirements-2026-10-02.md` (this feature's own source) and `settings-reshape-defeats-f3-conversion-defect.md` (G5's record) (FR-091, SC-016)

### Code quality — the descending ratchet (FR-107..FR-112)

**Why these exist**: code quality is a requirement of the coming stable version, so the two static
baselines are a ratchet that **moves down**, not one that holds (FR-109). The first pass specified a
hold, which would have let 80 type findings and 606 lint findings sit unchanged forever provided
nothing new was added.

**Why they are here, last**: **438 of the 606 lint findings are whitespace on blank lines**, touching
nearly every file in `src/`. Landing that before the stories means every story's diff is reviewed
against freshly reformatted files — the same reasoning that puts S3 last. Executes after US1–US9 and
after the golden event; its IDs are higher than the gate tasks below because IDs are append-only,
and **position, not number, gives the order**.

⚠ **Two hazards that no finding list shows, and that `ruff --fix` walks straight into.** Both are
spelled out in `snapshots/lint-before.txt` and in FR-111.

- [x] T126 [US9] Delete the **ten** removable unused `# type: ignore` comments — measured 2026-10-13: `--warn-unused-ignores` reports **all eleven** in `src/` as unused, at `cues/CuemsScript.py:268`, `tools/SignalEngine.py:48,87`, `xml/settings.py:45,112,309`, `helpers.py:499`, `tools/ConfigManager.py:441,578,801`. **Leave the eleventh**, `xml/XmlBuilder.py:98`: it is inside a frozen, lint-excluded module scheduled for deletion with the stable release, and it names a code that does not exist (`attr-union`, for `union-attr`) — which is itself the proof it never suppressed anything (FR-108, SC-QUALITY-005)
- [x] T127 [US9] **Bound both static instruments in `pyproject.toml`**, because a baseline whose tool version floats is not a baseline — the same reasoning FR-PERF-005 applies to the interpreter build, applied to the two tools whose *finding counts* this feature records as gates:
  - `[tool.hatch.envs.types].extra-dependencies`: **`mypy>=1.0.0` → `mypy>=2.4.0,<3`**. The lower bound is the version the 80 was measured on; the upper refuses a major release, where check behaviour changes wholesale and must re-baseline deliberately rather than silently. This is also T126's safety net: **all eleven ignores are unused against 2.4.0 specifically**, and `helpers.py:499`'s `__hash__ = None` is the one most likely to be flagged again by a different version — that assignment is load-bearing, since `CuemsDict.__eq__` sets `__hash__` to `None` and an unhashable cue is a `TypeError` in the engine.
  - `[tool.hatch.envs.test].dependencies`: **`"ruff"` → `"ruff>=0.17.0,<0.18"`** (equivalently `~=0.17.0`). ⚠ **Ruff is the worse of the two and was not the one named**: it is pinned not at all, and at 0.x the **minor** is the breaking unit — 0.17 → 0.18 can add rules and change existing ones, which moves the 606 directly. A tighter bound than mypy's is correct here, not inconsistent.

  Verified safe: no test couples to either pin — `tests/packaging/test_no_version_bump.py` reads only the changelog's first line and `src/cuemsutils/__init__.py`, and nothing in `tests/` greps `extra-dependencies` or the tool versions. **Deliberately not bounded**: `pytest`, `pytest-mock`, `pytest-cov`, `hypothesis`, `coverage` — none of them defines a recorded figure, and a changed test count is visible in the suite line where a changed lint count is not (FR-113, FR-113a, FR-108, SC-QUALITY-007, Constitution I's *"Dependency additions MUST be justified in the plan with maintenance impact"*)
- [x] T128 [US9] Delete the **two stale** `noqa` directives whose rule *is* enabled and whose violation is gone — `tools/NodeList.py:22` and `tools/init_node.py:36`, both `# noqa: F401`, measured with `--extend-select RUF100` (FR-108, SC-QUALITY-005)
- [x] T129 [US9] Convert the **fifteen inert** `noqa` directives in `src/` to plain comments, **keeping every rationale sentence** — ten `BLE001`, two `N801`, one each `C901`/`E501`/`SIM115` (10+2+3 = **15**; three artefacts said sixteen while their own breakdown summed to fifteen, re-measured with `--extend-select RUF100` on ruff 0.17.0), none of which this project selects, so each suppresses nothing. `# noqa: BLE001 - a broken universe must still name itself` becomes `# a broken universe must still name itself`. **The sentence is the valuable half**: it is the only record of why the code is written that way, and losing it while every number improves is the way this task fails (FR-108, SC-QUALITY-005). Do **not** enable any new rule to make them live — that is a project decision, not a sweep's side effect (FR-108a)
- [x] T130 [US9] Fix the **302 mechanical** lint findings in `src/` as **one commit** — 267 `W293` (whitespace on a blank line), 11 `W291` (trailing whitespace), 7 `F541` (f-string with no placeholder), and the 17 `I001` **one file at a time per T131**. Verify with `git diff -w` over the whitespace part coming back **empty** (FR-110, SC-QUALITY-004, SC-QUALITY-006)
- [x] T131 [US9] ⚠ **Sort imports file by file, never with a bulk `--fix`**, running the suite after each file. This package has documented import-order dependencies: `xml/adapters.py:355` calls `_register_enums()` at import time, which imports `NodeRole` back out of `tools/NodeList.py` while that module is still initialising — which is why `NodeList.py:321` is a lazy module `__getattr__` and `:305` carries the comment explaining it — plus three deliberate late imports marked `# noqa: E402` (`xml/descriptor.py:534` and the two frozen modules). A re-sorted import block can turn a working lazy import into an `ImportError` that **neither** static gate would catch (FR-111)
- [x] T132 [US9] Address `src/`'s **14 judgement** lint findings individually — 6 `F401` (several are deliberate re-exports and must stay, with `__all__` or a plain comment carrying the reason), 3 `E722` (bare `except`), 2 `F841`, 2 `E711`, 1 `E721` — each either fixed or carried in `baseline.md` with a one-line reason. Target **zero** in `src/` (FR-107, SC-QUALITY-004)
- [x] T133 [US9] Reduce `tests/`' 290 by at least its **209 mechanical** findings (171 `W293`, 37 `I001` per T131's rule, 1 `W291`), then examine the 81 judgement ones: ⚠ **`E721`'s correct fix is `type(x) is Y`, NEVER `isinstance(x, Y)`** — `type(x) == Y` asserts the **exact** type and this project depends on the distinction (013 keeps the cue classes subclass-dispatchable and puts a bare `MediaCue` in an `isinstance` tuple *because* an unknown class decodes to it), so converting the 24 `E721` findings would silently weaken 24 assertions from "exactly this type" to "this type or any subclass". And ⚠ the 29 `E712` are post-014: booleans are real now, so `== True` may be asserting genuine boolean identity where it once compared strings — `is True` is usually right and sometimes the comparison is the point (FR-111, FR-112)
- [x] T134 [US9] Reduce the **80 type findings** in `src/` wherever reducible without a behaviour change, starting with the mechanically safe classes (13 `var-annotated` want an annotation; 3 `return-value`; 4 `import-untyped`), and leaving each irreducible one **recorded with a one-line reason** — `xml/documents.py`'s `ElementTree[Element[str]]` variance findings at `:145-151` are the likely residue, being a stdlib-stub invariance artefact rather than a defect. **No finding may end this feature unexamined** (FR-107, SC-QUALITY-003)
- [x] T135 [US9] Prove the sweep changed no behaviour rather than asserting it: the eight goldens, the 24 wire-dict goldens and `outcomes.json` are byte-identical across it, the suite is green, and `git diff -w` restricted to the **whitespace findings** (278 of the 302 — 267 `W293` + 11 `W291`) is empty. ⚠ Corrected by the second analyze pass: the mechanical commit also carries 7 `F541` and 17 `I001` fixes, neither of which is whitespace, so `git diff -w` over the **whole** commit cannot be empty and asserting that it is would be a check that can only fail. T130 already stated the scoped form (FR-110, SC-QUALITY-006)
- [x] T136 [US9] Re-register **both** baselines at their new, lower figures in `snapshots/` and `baseline.md`, with the before/after pair stated — type `80 → N`, lint `606 → M` (`src/` `316 → M_src`) — each naming **the tool version it was measured on**, and record that the new figures are the gate from here. State the re-baseline trigger explicitly: **a minor bump of either tool inside T127's bounds may legitimately move the count**, so it re-baselines with the new figure recorded and the delta attributed to the tool rather than to the code — which is the whole reason the bounds exist (FR-109, FR-113, SC-QUALITY-003, SC-QUALITY-004)

### Budgets and release gates (cross-cutting — no story label)

**These run after the code-quality sweep above**, so T121/T121a measure the post-sweep state against
T136's re-registered baselines, not against the branch point's.

- [x] T116 [P] Measure the document **write** path by the budget's own method and record it in `baseline.md` against `≤ 16.4 ms` (branch point 14.297 ms worst observed), naming the interpreter build and the box's load average (SC-PERF-001, FR-PERF-003, FR-PERF-005)
- [x] T117 [P] Measure **descriptor derivation** for the show schema and record it in `baseline.md` against `≤ 1.22 ms` (branch point 1.060 ms worst observed) — both G3 and S2 change it (SC-PERF-002, FR-PERF-003)
- [x] T118 [P] Measure the three configuration **load** paths and the show load path and report them in `baseline.md` whether or not they moved — a feature that edits the writer must prove it did not move the reader (SC-PERF-004, FR-PERF-004)
- [x] T119 Record the suite's per-test figure in `baseline.md` against `≤ 10.3 ms/test` (branch point 8.93 ms/test), with the per-test figure binding and never the wall time — a growing corpus reads as a regression otherwise, which this repository has recorded twice (SC-PERF-003)
- [x] T120 Record any exceeded budget **as exceeded** in `baseline.md` rather than restating it as passing, with its mechanism named where one is identified (FR-PERF-001)
- [x] T120a [P] Contract test in `tests/contract/test_additive_surface_invariants.py` that **no schema's `CURRENT_VERSION` moved**, that the conversion registry and `DELIBERATE_IDENTITY_STEPS` are unchanged, and that `SchemaRegistry.runs_adapter_table` is true for **exactly one** configuration schema — the two cross-cutting constraints that had no task at all, both cheap to assert and both silently retirable otherwise (FR-101, FR-102)
- [x] T120b [P] Contract test in `tests/contract/test_additive_surface_invariants.py` that every public call this feature touches keeps its existing signature's meaning, default behaviour and exception type — the API goldens carry the shape, this carries the **intent**, so that "additive" is a checked claim rather than a review note (FR-100)
- [x] T120c [P] Assert `set_alias`'s refusal follows the project's diagnostic shape — it names the document, the locus, the value and the remedy — in `tests/unit/test_set_alias_validation.py`. It is this feature's **one** new operator-facing message; every other message is either unchanged by FR-063 or a docstring (FR-UX-001)
- [x] T121 Run `uvx hatch run test.py3.11:lint` and confirm the figure is **below** T005a's registered baseline of **606** (316 `src/` + 290 `tests/`), not merely equal to it — the ratchet descends (Constitution I, SC-QUALITY-001, FR-109)
- [x] T121a Run `PYENV_VERSION=3.11.9 uvx hatch run types:check src/cuemsutils` and confirm the figure is **below** T005b's registered baseline of **80**, not merely equal to it, recording the before and after counts in `baseline.md` (Constitution I, SC-QUALITY-001). ⚠ Added by the analyze pass: the plan had declined this gate while the constitution requires static checks and SC-QUALITY-001 requires no new **type** warning, and `pyproject.toml:172-177` has defined the `types:check` script all along. **Baseline-compared, never clean-asserted** — there is no `[tool.mypy]` section in this repository and mypy had never run here. **Watch the four files that are at zero**: `errors.py`, `tools/NodeList.py`, `tools/ConfigBase.py` and `helpers.py` — two of them receive brand-new public API (S1's exception class, G4's `set_alias`), so a new finding there has nothing pre-existing to hide in and is the signal this gate exists for
- [x] T121b Add **exactly three** unrendered modules to the published documentation — `cuemsutils.errors` to `docs/api.md`, and `cuemsutils.tools.NodeList` plus `cuemsutils.config.network_map` to `docs/tools.md` — so FR-045's one-runtime-writer warning, FR-065a's exception type and FR-035's setter are actually published. Measured 2026-10-13: `docs/` is mkdocstrings over an **explicit module list**, and three of this feature's four documentation targets were not on it. ⚠ **Two corrections from the second analyze pass**: `cuemsutils.config.settings` is **dropped** — this feature changes a branch inside it but adds no public call there, and publishing an internal module to satisfy a census is not a documentation fix; and `cuemsutils.xml.descriptor` is **deliberately not added** — `cuemsutils.xml` stays private, so G3's contract is published at `ConfigManager.get_schema_descriptor` by T071a instead (FR-UX-003a, FR-UX-003c)
- [x] T121c Contract test in `tests/contract/test_public_docs_coverage.py` that every module carrying a public call this feature **adds** appears in a `docs/*.md` mkdocstrings directive, so the next feature's public addition cannot repeat this silently. Scope it to this feature's four modules — `cuemsutils.helpers`, `cuemsutils.errors`, `cuemsutils.tools.NodeList`, `cuemsutils.config.network_map`, plus the already-rendered `cuemsutils.tools.{ConfigBase,ConfigManager}` — not to every export: a repository-wide assertion would fail on pre-existing gaps and be skipped. **`cuemsutils.xml.descriptor` is explicitly excluded, with the reason in the test**, so a later reader does not add it: `cuemsutils.xml` is private by decision and G3's contract is published at `ConfigManager.get_schema_descriptor` (T071a). An exclusion carrying its reason is the difference between a decision and an oversight (FR-UX-003b, FR-UX-003c, SC-QUALITY-002)
- [x] T122 Run `uvx hatch run test.py3.11:run -- -q` and confirm the suite ends **green**: all five branch-point failures are this feature's to close — FR-079 disposes of one, FR-080 of the other four — so zero may remain and none may be new (SC-TEST-002). ⚠ This asked for "no more than the five, each attributed", which five **new** attributed failures would have satisfied
- [x] T123 Confirm SC-005a from T058's comparison and SC-010 from T004's snapshot, and record both measured deltas in `baseline.md`
- [x] T124 Walk [quickstart.md](quickstart.md) end to end on the finished branch and correct anything it now describes wrongly, including §4's dead-end reproduction, which must now report `reshaped`
- [x] T125 Update `CLAUDE.md`'s *Recent Changes* and *Active Technologies* with this feature's landing, its measured figures with their interpreter build, and the corrected candidate-tag values from T102 — one of the three homes FR-094 requires to agree, and the one a later session reads first (FR-094, SC-017)

**Checkpoint**: the five gates are closed, the coordinated `xml-refactor-merge-candidate` tag is
cuttable, and `specs/planning/` holds no document whose work is complete.

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (Phase 1)**: no dependencies — starts immediately. T002 gates everything: an unexpected
  branch-point count means the environment, not the feature, is being measured.
- **Foundational (Phase 2)**: depends on Phase 1. Blocks every story's *recording*, not its coding.
- **US1 (Phase 3) → US2 (Phase 4)**: soft. One user journey (R6); T023 needs both halves.
- **US3 (Phase 5), US5 (Phase 6)**: independent of everything above and of each other.
- **US7 (Phase 7) → US4 (Phase 8)**: **hard**. Seeding rule 2 reads a union's member types; before
  S2's narrowing the rule-1 path fires and the test meant to pin rule 2 passes vacuously.
- **US6 (Phase 9)**: independent of all of the above.
- **US8 (Phase 10)**: last of the code changes, so later work is not reviewed against freshly moved
  goldens. Independent of US1/US2 now that the golden event has moved out of it.
- **Polish (Phase 11)**: depends on every story being complete. **The golden event (T026, T088,
  T089, T092) depends on US1, US2, US4, US5, US6 and US8** — every public addition and the writer
  change — which is why it lives here and not in the two phases that produce its inputs.
  **T026 additionally depends on T049a and T080a**: the API goldens are generated from the
  hand-maintained surface records in `tests/contract/test_public_api_surface.py`, so without those
  two the re-cut silently omits `NodeIndex.set_alias` and `NodeIdentityCollisionError`.
  T114 precedes T115; T115 is last of all. T105–T108 need all five gates landed.

### Story dependencies

| Story | Gate | Depends on | Independently testable |
|---|---|---|---|
| US1 | G1 | — | yes |
| US2 | G2 | US1 for the joint journey test only | yes |
| US3 | G5 | — | yes |
| US4 | G3 | **US7 (hard)** | yes |
| US5 | G4 | — | yes |
| US6 | S1 | — | yes |
| US7 | S2 | — | yes |
| US8 | S3 | — | yes |
| US9 | S4 + sweep | all of the above | yes |

### Within each story

Tests are written and seen to fail first (SC-TEST-001). For US3 the failing test is the
**composition**, never the unit (FR-053).

### Parallel opportunities

- T003, T004 in Setup (T005a and T005b are already registered); T008 in Foundational
- Every test task inside a story phase is `[P]` — they are separate files
- **US3, US5, US6 and US7 can be worked entirely in parallel** by four people once Phase 2 closes
- US1+US2 is a fifth parallel track; US4 waits on US7; US8 waits on all code
- In polish: T093, T096, T104, T109, T116, T117, T118, T120a, T120b, T120c are `[P]`
- **T049a and T080a are not `[P]` with each other** — both edit
  `tests/contract/test_public_api_surface.py` — and both must precede T026. They *are* `[P]` with
  everything else in their own phases, since no other task touches that file
- **The golden event is not `[P]` with anything** — T026 and T088 both write
  `tests/golden/MANIFEST.sha256`, and T089's verification is only meaningful once both have run
- **T105a–T105e are not `[P]` with each other**: all five write `consumers_works.md`. They *are*
  `[P]` with T106 and T107, which write elsewhere
- **T126–T136 are not `[P]` with anything, and barely with each other.** The sweep touches nearly
  every file in `src/`; T131 is explicitly serial (file by file, suite after each), and T135's
  byte-identity proof is meaningless unless everything before it has landed
- **FR-104**: any sibling verification run in parallel uses a **per-session `git worktree`** of this
  repository, never the shared checkout

---

## Parallel Example: four independent gates after Phase 2

```bash
# Four tracks, no shared file between them:
Track A (US1+US2):  ConfigBase.py, ConfigManager.py, config/settings.py
Track B (US3):      xml/versioning.py
Track C (US5):      tools/NodeList.py, config/network_map.py
Track D (US6):      errors.py, xml/validators.py, tools/ConfigBase.py*

# * Track A and Track D both touch ConfigBase.py — different methods, but
#   sequence T081 after T013 to keep the diff reviewable.
```

```bash
# Launch US4's test tasks together once US7 has landed:
Task: "Seeding table completeness in tests/contract/test_instance_seeding.py"
Task: "Repairability invariance in tests/contract/test_repairability_invariance.py"
Task: "Wire nesting and wrapper in tests/contract/test_descriptor_instances.py"
Task: "Root instances save in tests/integration/test_instance_saves.py"
Task: "Facet rules in tests/unit/test_seeding_rules.py"
```

---

## Implementation Strategy

### MVP first (US1 + US2)

1. Phase 1 Setup, Phase 2 Foundational
2. Phase 3 US1, Phase 4 US2 — the first-save journey
3. **STOP and VALIDATE**: a project that has never been saved can be saved, and all four
   configuration domains round-trip (SC-001, SC-002)

That is the smallest increment with standalone value: it delivers the **library halves** of two of
`cuems-editor`'s seven gate xfails and makes the configuration round trip reachable for a new
project. Neither of those two xfails **flips** on it — both need a change in that repository as well
(FR-008, FR-017), which `consumers_works.md` records and T105a/T105b measure. The API goldens are
stale from here until the polish phase, by design.

### Incremental delivery

1. US1 + US2 → the first-save journey (**MVP**)
2. US3 → the defect closes; 11 of 11 dead-end documents migrate (SC-003, SC-004)
3. US5 → `cuems-nodeconf`'s `node_set` unblocks (SC-013)
4. US7 → 5 one-value choice sets become 0 (SC-010)
5. US4 → the descriptor's instance saves (SC-005), four more xfails flip
6. US6 → the collision carries its identity (SC-009)
7. US8 → documents stay readable (SC-011); the golden event lands as one reviewable change
8. US9 → the records tell the truth, the budgets are recorded, the tag is cuttable

Each step adds value without breaking the previous ones.

### Parallel team strategy

Phase 2 closes, then: A on US1+US2, B on US3, C on US5, D on US7 → US4, E on US6. US8 is taken by
whoever finishes first, after the others' code is in. US9 is the whole team's, and T115 is nobody's
until T114 passes. **The golden event is one person's**, start to finish — it is one commit across
eight files and a manifest, and splitting it is how an arc ends up with two golden events it meant
to have one of.

---

## Notes

- `[P]` = different files, no dependency on an incomplete task
- Commit after each task or logical group; **commits are GPG-signed** — retry on
  "gpg failed to sign", never `--no-gpg-sign`
- **Every figure names its interpreter build**, not only "3.11.9" — two builds exist on this box and
  they differed by 32–72% until pyenv's was rebuilt with PGO+LTO (FR-PERF-005)
- **Check `/proc/loadavg` before measuring.** Skipping this produced a phantom 2× regression
- **Sample in more than one window.** Consistency within a window is not evidence — it is what makes
  a bad measurement persuasive (FR-PERF-002)
- The thirteen settled items in spec.md's *What is already settled* are **inputs, not questions**. A
  task that re-derives one is doing work this feature has already paid for (D1)
- `hatch` is used through `uvx`; the box's `/etc/cuems/settings.xml` is in the pre-013 device shape,
  so point tools at a fixture `CUEMS_CONF_PATH` rather than the host configuration
- **Both static gates are baseline-compared and the baselines must come DOWN** — registered at
  type **80** (`src/`) and lint **606**; T121/T121a assert *below*, not *equal* (T005a, T005b, T136)
- **`ruff --fix` is not safe to run in bulk here.** `I001` can break a documented lazy-import
  contract, and `E721`'s plausible-looking `isinstance` fix would weaken 24 test assertions (T131,
  T133, FR-111)
- **A suppression's sentence is worth more than the suppression.** Fifteen `noqa` directives in
  `src/` suppress rules this project does not select; converting them must keep every reason (T129)
- **A docstring in an unrendered module is not documentation.** `docs/` is mkdocstrings over an
  explicit module list; three of this feature's four documentation targets were not on it (T121b)
- **Snapshots live in `specs/015-consumer-gate-closure/snapshots/`, not `/tmp`** — they are read
  many phases after they are written
- **The public-surface goldens are generated from hand-maintained lists, not from the package.**
  `PUBLIC_CLASSES`, `PUBLIC_FUNCTIONS` and `PUBLIC_ERRORS` in
  `tests/contract/test_public_api_surface.py` decide what `api/public_api.json` records; `__all__`
  is asserted *against* `PUBLIC_ERRORS`, not read into it. A public addition therefore moves a
  golden only if its list moved first (T049a, T080a)
- **S3's byte-level reach is eight goldens *and* five hand-authored documents** — the two corpus
  documents (T090) and the three 007 pre-state documents (T090a). The second group was missed by the
  first enumeration because the test that reads them asserts a two-line diff rather than a hash
