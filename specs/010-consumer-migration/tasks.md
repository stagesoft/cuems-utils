---
description: "Task list for feature 010 — consumer migration"
---

# Tasks: Consumer migration

**Input**: Design documents from `/specs/010-consumer-migration/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED by the constitution (Principle II). Written first, failing before implementation.

**Organization**: grouped by user story. The spec has ten — eleven once US11 was added 2026-09-17,
back to ten once US1 merged into it 2026-09-18 — and **three are this repository's work while the
rest are not**; see the scope boundary immediately below.

## ⚠️ Scope boundary — read before using this file

This feature spans **seven** repositories. It was written for seven, briefly counted eight when
`cuems-power-bridge` was added 2026-09-17 (US11), and returned to seven on **2026-09-18** when
`cuems-power-bridge` was measured to **be** `cuems-wsclient`, renamed in 2026-06 — see
[the identity correction](#the-repository-identity-correction-2026-09-18) below, which merges US1
into US11 and changes three counts in this file. Each repository runs its own spec-kit flow from
`specs/planning/xml-rebuild/010-consumer-prompts/`. **This `tasks.md` is `cuems-utils`' list plus
the cross-repo gates that live in no consumer repository.** The plan settles the split ("What this
repository's `tasks.md` contains"):

| In this file | Not in this file |
|---|---|
| US3 in full (wave 0 — the public descriptor path) | The per-call-site edits in the six consumer repositories |
| US9 in full (wave 4 — rollout, release gate, data migration) | Anything each consumer already tracks in its own `tasks.md` |
| US10 in full (wave 5 — removal, count, migration guide) | |
| For US1/US2/US4/US5/US6/US7/US8/**US11**: **gate references only** — the guide entry each one owes, and the verification that it actually landed | |
| **US11's flow prompt** (T070) — every other flow's prompt lives in this repository, so this one's does too | The bridge's own parser edits, its fixtures and its packaging |

Duplicating a consumer's edits here would create two task lists that drift, and the one in the
wrong repository would win arguments it should lose.

### The repository-identity correction (2026-09-18)

**`cuems-wsclient` and `cuems-power-bridge` are one repository.** Measured, not inferred:
`git merge-base --is-ancestor f78bea6 main` is **true** in `cuems-power-bridge` — `f78bea6` is the
exact commit flow 06 audited US1 against, 30 commits back — the rename is in history
(`83d4f5d refactor: rename package cuems-wsclient -> cuems-power-bridge (v0.2.6)`, 2026-06), and
`/disk/Projects/StageLab/cuems-wsclient` is a **stale checkout** still pointing at the pre-rename
remote `git@github.com:stagesoft/cuems-wsclient.git`. `pyproject.toml:36` and `debian/control:18`
are byte-identical in both checkouts.

What this changes in this file, each corrected in place below rather than only here:

| Claim | Was | Is |
|---|---|---|
| Repository count (scope boundary, T069's D32) | eight | **seven** |
| T049's census denominator | seven consumer checkouts | **six** |
| T038's missing package edges | five | **four** |
| US1 and US11 | two stories | **one story about one file** — `slave_avahi_names`'s single comparison, counted twice |
| T076's premise | `debian/control` declares no `cuems-utils` relation | it declares one at `:18`, plus `cuems-common (>= 1.0.0)` at `:19` |

**The durable lesson is the discovery method, not the corrected number.** The list has now been
wrong three times — `cuems-wsclient` absent (FR-UX-002), `cuems-power-bridge` absent (US11), and
the two counted as separate — and all three came from maintaining it by hand. T062's denominator
must be discovered by its own command and de-duplicated **by git remote, not by directory name**,
which is the only enumeration that would have caught all three.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story from [spec.md](spec.md) this task serves

## Path conventions

`src/cuemsutils/`, `tests/` at this repository's root. Consumer repositories are referenced by
absolute path under `/disk/Projects/StageLab/` where a verification task must read them.

---

## Phase 1: Setup

**Purpose**: the measurement and document scaffolding every later phase writes into.

- [X] T001 Record the measured suite baseline (`hatch test --show`; expect ~2573 passed / 96 skipped / 2 xfailed ≈ 20.73 ms/test) in `specs/010-consumer-migration/baseline.md`
- [X] T002 [P] Create `specs/010-consumer-migration/migration-guide.md` with the section skeleton — it accumulates across the whole feature rather than being written at the end (FR-UX-001)
- [X] T003 [P] Create `specs/010-consumer-migration/import-census.md` carrying the census command and **today's non-zero** result, so the wave-5 gate has a starting measurement to move from (FR-029)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: confirm what this feature *assumes already exists*, so no later task rebuilds it.

**⚠️ CRITICAL**: Assumption 3 of the spec says everything else this feature asks of the library
already landed in 007 and 008. That is a claim to verify once, here — not per story.

- [X] T004 Confirm — do **not** rebuild — the inherited surfaces, recording each with its location in `specs/010-consumer-migration/baseline.md`: `NetworkMap.partition_by_adoption` (`src/cuemsutils/xml/settings.py:209`), the `cuems-convert-documents` entry point (`src/cuemsutils/xml/convert_documents.py` + `pyproject.toml` `[project.scripts]`), the public report types in `src/cuemsutils/errors.py` (`LoadReport`/`Outcome`/`RepairRecord`/`ConversionRecord`), and the strict load path's three outcomes
- [X] T005 [P] Record the six consumer repositories' measured starting state (branch, spec-kit presence, test runner, packaging) in `specs/010-consumer-migration/baseline.md` — five have no spec-kit, two have no `tests/`, two have no `debian/`
- [ ] T005a [P] Record **`cuems-power-bridge`**'s measured starting state in `specs/010-consumer-migration/baseline.md` on the same axes as T005's six — branch, spec-kit presence, test runner, packaging, and its `cuemsutils` pin. **Re-measured 2026-09-18** (the 2026-09-17 reading is corrected on three axes, and it is not the seventh repository — it is T005's sixth under its current name; see the identity correction above):
  - Branch **`feat/xml-refactor` already exists** at `c201405` (= `main`), clean but for untracked planning documents — not `main` as recorded 2026-09-17.
  - **No spec-kit**, no constitution.
  - `pytest` with **15 test files**, and the suite is **RED before this feature touches anything**: `6 failed, 133 passed`, all six `tests/test_install_mjs.py`, all `TypeError: _patched_code() missing 1 required positional argument: 'force'` — unrelated to this migration and blocking under the never-implement-on-a-red-suite rule.
  - `debian/control` **does** declare `cuems-utils (>= 0.1.0rc5)` at `:18` and `cuems-common (>= 1.0.0)` at `:19` — both unbounded floors. The 2026-09-17 reading ("no `cuems-utils` relation at all") is **wrong**; flow 06 read the same file correctly in 2026-09-03.
  - `pyproject.toml:36` `cuemsutils = {version = ">=0.1.0rc5", optional = true}`, `:40` `production = ["cuemsutils"]`, and **imported nowhere** — verified by grep across `src/` and `tests/`. This is not "the same shape as `cuems-wsclient`'s"; it is the same line of the same file.

**Checkpoint**: the inherited surface is confirmed; US3 can begin.

---

## Phase 3: User Story 3 — The schema descriptor has a public path (Priority: P1) 🎯 MVP

**Goal**: a consumer can reach the descriptor for all six schemas through the public configuration
façade, without importing internal machinery.

**Independent Test**: for each of the six schemas, the public result equals the internal one; every
complex type yields a constructible instance that validates; `cuemsutils.xml.__all__` is still `[]`.

**Blocks**: consumer flows 02 (`cuems-editor`) and 05 (`cuems-frontend`).

### Tests for User Story 3 (REQUIRED) ⚠️

> Write these first and confirm they FAIL before implementation.

- [X] T006 [P] [US3] Contract test: the public descriptor equals the internal descriptor for **each of the six schemas** — six assertions, not a sample — in `tests/contract/test_public_descriptor.py` (SC-003)
- [X] T007 [P] [US3] Contract test: every complex type across the six schemas yields a constructible empty instance that **validates against its own schema**, 100% of types counted, in `tests/contract/test_descriptor_instances.py` (FR-022a, SC-003)
- [X] T008 [P] [US3] Contract test: asking for one schema's descriptor does **not** construct the other five, in `tests/contract/test_descriptor_laziness.py` — and this test must not be defeated by T006 building all six first (research R8)
- [X] T009 [P] [US3] Extend the public-surface contract test so `cuemsutils.xml.__all__` staying `[]` is asserted alongside the new accessor, in `tests/contract/test_public_surface.py` (FR-024)

### Implementation for User Story 3

- [X] T009a [P] [US3] Contract test: a show document carrying a dangling `target` or `action_target` loads with the reference cleared and named in the report, and **100% of the cases the editor's current implementation catches** are caught — case by case, not a sample — in `tests/contract/test_dangling_reference_rule.py` (FR-043a, FR-043c, SC-010a)
- [X] T010 [US3] Pin the public accessor's name — **`get_schema_descriptor`** (decided 2026-09-04, matching `ConfigManager`'s `get_*` convention for parameterised lookups) — in `tests/contract/test_config_accessor_names.py` alongside the existing accessor names, and record it in `specs/010-consumer-migration/contracts/descriptor-access.md` (FR-028)
- [X] T010a [P] [US3] Contract test: the public schema-name enum's members and the library's schema registry agree **in both directions** — no registry entry missing from the enum, no enum member absent from the registry — in `tests/contract/test_schema_name_enum.py`. This is the anti-drift contract `NodeRole` already holds against its XSD facets, and it is what stops a seventh schema existing in one place and not the other (FR-028a)
- [X] T010b [US3] Add the public schema-name enum to `src/cuemsutils/tools/ConfigManager.py`, beside the accessor, with members **derived from or asserted against** the schema registry rather than hand-copied, and a name that does not read as the loaded-schema object `get_schema` returns (FR-028a)
- [X] T011 [US3] Add the constructible empty instance per complex type to `src/cuemsutils/xml/descriptor.py` (FR-022a), leaving the five existing facts unrecomputed (FR-022b, FR-027)
- [X] T012 [US3] Add `get_schema_descriptor` to `src/cuemsutils/tools/ConfigManager.py` covering all six schemas including `script`, **lazily per schema**, taking the enum and **not** a bare string (FR-020, FR-022, FR-028a, research R8) — depends on T010, T010b, T011
- [X] T013 [US3] Write FR-021's rationale into that accessor's docstring in `src/cuemsutils/tools/ConfigManager.py`: why a configuration-domain object serves the show schema. A reader who finds it without the reason files it as a mistake
- [X] T014 [US3] Make the example generators (`generate_script_example`, `generate_settings_example`) reachable from the same public path in `src/cuemsutils/tools/ConfigManager.py` (FR-023)
- [X] T015 [US3] For each of `cuems-nodeconf`'s two internal imports — `cuemsutils.xml.mapper`'s `Mapper`/`read_config_document` and `cuemsutils.xml.settings`'s `NetworkMap` — name the public equivalent, add a test per import, and record both in `specs/010-consumer-migration/migration-guide.md`; where an equivalent already exists, **name it rather than adding a synonym** (FR-025)
- [X] T015a [US3] Register the dangling-reference semantic rule in `src/cuemsutils/xml/validators.py` — every `target`/`action_target` resolves to a cue in the same document; a reference that does not is **repairable**, cleared to the field's default and named in the load report (FR-043a). It lands in wave 0, **before** the editor deletes its copy in wave 2a, so no window exists in which neither runs. Measured 2026-09-03 the rule table holds exactly one rule, so this is the second and the first on the show path
- [X] T016 [US3] Measure wave 0's cost against the "no measurable cost" budget and record it in `specs/010-consumer-migration/baseline.md` — eager construction of all six is a design error, not an overrun to accept (FR-PERF-001)
- [X] T017 [US3] Write the descriptor section of `specs/010-consumer-migration/migration-guide.md` at call-site granularity, so flows 02 and 05 can be written against it without reading library source (FR-UX-001)

**Checkpoint**: US3 complete → `cuems-editor` and `cuems-frontend` flows are unblocked.

---

## Phase 4: Consumer-repository gates (US1, US2, US4, US5, US6, US7, US8)

**Goal**: this repository's obligations for the seven stories whose edits live elsewhere — the
migration guide entry each one owes, and the verification that it actually landed rather than
merely merged.

**Independent Test**: each gate task names a consumer artifact and either finds it or does not.

**Note**: every task here is `[P]` against the others — they read different repositories and write
different guide sections — but each is blocked by its own consumer flow completing.

- [ ] T018 [P] [US1] Record **`cuems-power-bridge`**'s migration in `specs/010-consumer-migration/migration-guide.md` — the sixth consumer, absent from 007's guide, 008's guide and the cross-repo plan's repository list, which is why a silently broken shutdown path survived two features (FR-UX-002). **Record it under its current name**, noting the 2026-06 rename from `cuems-wsclient`, so the guide does not preserve the double-count this feature just closed. Merged with **T071**: one repository, one guide entry
- [ ] T019 [P] [US1] Verify the `cuems-power-bridge` gate: its private network-map reader is gone (not re-spelled), and its first test fails against the old string comparison; record in `specs/010-consumer-migration/baseline.md` (FR-050, FR-051, SC-001, SC-007). **Same verification as T072/T073** — do it once, against `/disk/Projects/StageLab/cuems-power-bridge`, and never against the stale `/disk/Projects/StageLab/cuems-wsclient` checkout, which is 30 commits behind and frozen at 2026-06-01
- [ ] T020 [P] [US2] Record the deleted template module and its replacement — the UUID helper re-sourced from `cuemsutils.helpers` — in `specs/010-consumer-migration/migration-guide.md` with before/after (FR-040, FR-UX-001)
- [ ] T021 [P] [US2] Verify `cuems-editor` imports and reaches its listening state against the current library; record in `specs/010-consumer-migration/baseline.md` (SC-002)
- [ ] T022 [P] [US4] Record the engine's role and online retyping and the non-mutating adoption partition in `specs/010-consumer-migration/migration-guide.md` with before/after (FR-031–FR-034)
- [ ] T023 [P] [US4] Verify each of the engine's four "keeps resolving but becomes wrong" sites (`/disk/Projects/StageLab/cuems-engine` `BaseEngine.py:33,410,440,443`) carries a test that **fails against the pre-migration value**; record the four in `specs/010-consumer-migration/baseline.md` (FR-004, SC-007)
- [X] T023a [P] [US5] Label the **two groups of four** wherever the count is described, so neither substitutes for the other: FR-070's **discovery four** (`cuems-common`'s Avahi service files) are counted and fixed; FR-073's **non-shipped four** are exempt (FR-070a)
- [X] T024 [P] [US5] Record the discovery-vocabulary cutover across **both** owning repositories in `specs/010-consumer-migration/migration-guide.md`, including the two template filenames and the packaging entries that place them (FR-060–FR-063)
- [ ] T025 [P] [US5] ⏸ **clause (b) CLEARED 2026-09-17, clause (a) open** (see `baseline.md`): *no half-renamed combination is shippable* is now **observed** — `cuems-nodeconf`'s own demonstration (`evidence/out-of-order-refusal.txt`, real packages both sides, superseding `cuems-common`'s stub-based case C1) refuses both directions, N1/N2, and both single-half upgrades, N5/N6. What remains is the **over-the-wire** check, which needs two hosts: `cuems-nodeconf`'s T050/T051 are both marked NOT PERFORMED for that reason. Verify the end-to-end discovery check ran — a node published by `/disk/Projects/StageLab/cuems-nodeconf`'s migrated publisher, discovered with its role by its migrated listener — and that no half-renamed combination is shippable; record in `specs/010-consumer-migration/baseline.md` (SC-012)
- [ ] T026 [P] [US6] Record the editor's five show-parsing sites, the wire projection, the message family and the **two** payload deltas in `specs/010-consumer-migration/migration-guide.md` (FR-041, FR-042, FR-047–FR-049c)
- [ ] T027 [P] [US6] Verify the payload against the **two-delta** statement — `schemaLocation` absent, duration wrapped, nothing else moved including key order and the string boolean form — never against unconditional byte-identity, and **against this repository's golden corpus** (`tests/golden/`, already carrying `doc_version="2"` and the wrapped duration) rather than a payload captured at migration time; record the goldens used **by checksum** in `specs/010-consumer-migration/baseline.md` (FR-013, FR-013a, SC-005, SC-005a)
- [ ] T027a [P] [US6] Verify the fixup split landed as specified: the editor's dangling-reference code is **deleted** (not ported), the database-sourced duration correction **stays** and operates on the loaded object rather than a dict, and both still detect what they detect today — measured case by case (FR-043–FR-043d, SC-010a, SC-010b)
- [ ] T027b [P] [US6] Verify **zero** consumer code paths manipulate the wire dict to achieve an object-level result — the projection appears once, at the UI boundary, in each consumer that has one; record per repository in `specs/010-consumer-migration/baseline.md` (FR-013b, SC-005b)
- [ ] T028 [P] [US6] Verify `/disk/Projects/StageLab/cuems-editor`'s `repair_durations.py` still reads the corrupt documents it exists to repair, and that exactly **one** document rewriter remains in the ecosystem; record the fixture set and result in `specs/010-consumer-migration/baseline.md` (FR-045, SC-010)
- [ ] T026a [P] [US6] Record the **operator recovery action** for an unrepairable document in `specs/010-consumer-migration/migration-guide.md` — restore from a conversion backup, correct the named field by hand, or remove the document from the library. A failure that says only "this will not open" leaves an operator with a broken project and no next step (FR-049d)
- [ ] T028a [P] [US6] Record in `specs/010-consumer-migration/migration-guide.md` that FR-043a **widens behaviour for every consumer**, not only the editor: a document with a dangling reference now loads with it cleared and reported wherever it is loaded, where previously only documents passing through the editor were corrected — the engine could previously dispatch against a reference to a cue that does not exist (FR-043d)
- [X] T029 [P] [US7] Record the node daemon's network-map swap, the relocated timing helper and the two internal imports in `specs/010-consumer-migration/migration-guide.md` (FR-064–FR-068)
- [X] T030 [P] [US7] Verify 008's characterization tests in `/disk/Projects/StageLab/cuems-nodeconf` pass **unchanged** against the library's object — not edited to accommodate the new API; record the run in `specs/010-consumer-migration/baseline.md` (FR-065, SC-008)
- [ ] T031 [P] [US8] Record the UI's template and configuration-domain port, and the media-duration unwrapping, in `specs/010-consumer-migration/migration-guide.md` (FR-085–FR-088d)
- [ ] T031a [P] [US8] Verify the descriptor-driven forms against **every restricted enumeration and every model-layer default the six schemas declare** — not a hand-picked subset and not only FR-086's three value-reading sites; record the coverage in `specs/010-consumer-migration/baseline.md` (FR-088f)
- [ ] T032 [P] [US8] Verify the characterization tests for `/disk/Projects/StageLab/cuems-frontend`'s `projects.service.ts`, `project-edit/sequence/sequence.component.ts` and `settings.component.ts` were committed **before** the port and are green after it; record both commits in `specs/010-consumer-migration/baseline.md` (FR-084, D35, SC-013)
- [ ] T033 [US6] Verify 008's consumer-impacting changes against **each live call site `specs/008-rebuild-extension/migration-guide.md` named** — the duration type and wire change, the validating load path, and the version marker's presence — and record the per-site results in `specs/010-consumer-migration/baseline.md` (FR-080–FR-083)
- [ ] T034 [US4] Count the "keeps resolving but becomes wrong" callers found and the discriminating tests added, and state the two counts as **equal** in `specs/010-consumer-migration/migration-guide.md` — against the **defined denominator**: every call site named in 007's and 008's migration guides plus anything a fresh ecosystem-wide search adds, with the search's method and date recorded (SC-007)

### Upstream findings from `cuems-nodeconf` (received 2026-09-17)

`cuems-nodeconf`'s feature 001 reports three findings against this library at
`specs/001-network-map-object-adoption/upstream-report.md`, deliberately unpatched from that side
(its constitution forbids a consumer editing the library whose characterization yardstick it
vendors). All three are verified here; the first is a live defect, not a documentation slip.

- [X] T080 [US7] **Preserve the target's mode across an atomic save** in `src/cuemsutils/xml/documents.py:189-195`. `tempfile.mkstemp` creates `0600` by construction and `os.replace` carries the **temporary's** mode onto the target, so every save silently resets the document's permissions. Measured: a file at `0644` comes back `0600`. Stat the target before writing and `chmod` the temporary to match; when the target does not yet exist, fall back to `0644 & ~umask` rather than leaving `mkstemp`'s `0600`. This is **not** a feature-001 regression — the reporter measured it through the pre-feature call path — and it affects **every** `save_document` consumer, not just `network_map`
- [X] T081 [US7] Test T080 in this repository's own suite, since that is where the guarantee belongs (the reporter says so explicitly): a document saved over an existing `0644` file comes back `0644`; a document saved where none existed is group/other-readable; and the atomicity and non-mutation contracts `save_document`'s docstring already claims still hold. Write it **failing first** against today's behaviour
- [X] T082 [P] [US7] Correct the two stale docstrings the report names, neither of which describes current behaviour — documentation only, no behaviour change, yardstick unaffected: (a) `src/cuemsutils/tools/NodeList.py:177`, `set_controller_always_adopted`'s *"on a first run, nothing else is"*, which the method neither does nor has a parameter to do; and (b) `src/cuemsutils/config/network_map.py:156-162`, `refresh`'s **"Not ported … recorded as an open item"** paragraph, which is **closed** and closed in the library's favour — `cuems-nodeconf` deleted the branch rather than asking for the parameter (`91047f4`), having measured it to have no reachable correct effect and one reachable harmful one
- [X] T083 [P] [US7] Correct what made the `CuemsNetworkMapType` question go the wrong way for two readers: `ConfigManager.load_network_map` assigns `netmap.get_dict()`, which **reads as a dict and is not one** — for `network_map` it returns the bound `CuemsNetworkMapType`, `.save`/`.refresh` included. Say so at the assignment, and fix the `network_map` **setter**'s annotation (`value: dict[str, Any]`, `ConfigManager.py:175`), which contradicts the getter's own docstring three lines above it. No behaviour change: the getter is already correct and `save_network_map` already depends on it
- [X] T084 [US7] Record in `specs/010-consumer-migration/migration-guide.md` that `cuems-nodeconf`'s remaining internal import (`cuemsutils.config.network_map.CuemsNetworkMapType`) is **the consumer's to close, not this library's** — `ConfigManager.network_map` is the existing public equivalent and FR-025 says name it rather than add a synonym. This repository adds **no** public alias for that class; the daemon retains the document it already loads and refills its `node_list` instead of constructing a new one. Verified reachable end to end importing only `cuemsutils.tools.*`

### User Story 11 — `cuems-power-bridge` (added 2026-09-17; **merged with US1** 2026-09-18)

**Why it exists**: the wave-1 gate (T023a/T024/T025) measured `cuems-power-bridge` parsing
`<node_type>` and filtering on `"NodeType.slave"` against maps that `cuems-migrate-network-map` has
already converted. It is **shipped** (`rc1_packages/cuems-power-bridge_0.3.0-5_all.deb`) and absent
from D32's six.

**It is not `cuems-wsclient`'s failure mode repeating — it is `cuems-wsclient`'s failure, never
fixed.** Measured 2026-09-18: the two are one repository, renamed in 2026-06 (see the identity
correction at the top of this file). US1 and US11 are therefore **one story about one file**, and
this section is the live one: US1's T018/T019 point here, and the flow is
`specs/planning/xml-rebuild/010-consumer-prompts/07-cuems-power-bridge.md`, which supersedes flow
06. That US11 was ever written proves the point FR-UX-002 makes — a repository this feature had
already found, under a name the list still used, was re-discovered from scratch by a gate.

**The findings document is `/disk/Projects/StageLab/cuems-power-bridge/specs/planning/cuems-power-bridge-node-role-findings.md`**
(under `specs/planning/`, not `dev/planning/` — that directory was renamed 2026-09-18), written
from `cuems-common`'s side on 2026-09-15 and moved into the bridge on 2026-09-17. It is still
**untracked**, and it is **right about the defect and incomplete about its extent** — verified
against the bridge's source 2026-09-17 and re-verified by running it 2026-09-18, neither of which
it could read. Four corrections below are load bearing; T071 records them rather than re-deriving
them later.

- [X] T070 [US11] Write `specs/planning/xml-rebuild/010-consumer-prompts/07-cuems-power-bridge.md` — **this repository's own work**, since all six existing flow prompts live here and a flow with no prompt is a flow nobody runs. It MUST carry the measured starting state (T005a), **all three** defect sites (T072), the two independently-broken features (T075), and the fixture problem (T073) inline — **not** a pointer to the findings document, which is untracked and therefore may never reach the person running the flow. **Done 2026-09-18.** It also carries §0.0, the identity correction that supersedes flow 06, and three preconditions the public path adds that no prior document records (see T071(d)). Flow 06 was marked superseded and the prompts `README.md` index updated in the same pass
- [ ] T070a [P] [US11] Have `cuems-power-bridge` **commit** the findings document, and the vendored bundle beside it. An untracked file is not a deliverable, and it is currently the only written record of a live, silent, physical failure. **Status 2026-09-18**: the document was moved from `dev/planning/` to `specs/planning/` and a self-contained bundle (`specs/planning/cuems-utils-xml-refactor-consumer-migration.md`, the `cuems-common` vendoring pattern) now sits beside it, carrying the corrections and the measurements. **Both are still untracked** — the commit is flow 07 §1a's first step, and this task closes only when it has happened. The findings document is **kept, not consumed**: it is the dated 2026-09-15 primary record, and the bundle cites it rather than replacing it
- [ ] T071 [P] [US11] Record the bridge's migration in `specs/010-consumer-migration/migration-guide.md` with before/after, **and the three corrections to the findings document** (FR-UX-001, FR-UX-002):
  - **(a) The defect has three sites, not one.** The document names only `cuems-common`'s `usr/bin/cuems-cluster-poweroff:275`. The bridge carries two more, in its own parser: `src/cuemspowerbridge/network_map.py:110` (`slave_avahi_names`) and `:141` (`slave_ips`). Fixing the tool alone — the document's option D — would leave both live.
  - **(b) Two independent features are broken, not one.** `slave_ips()` is **not** on the poweroff path: it feeds the bridge's autoload / NNG-hub readiness gate (`tests/test_autoload.py:181`, `debian/changelog:162`). So a converted map silently breaks **show-playback readiness** as well as orderly power-off, and the document's blast-radius section (§3) misses it entirely.
  - **(c) §9's first two unknowns are now measured, and they resolve to the worse branch.** `parse()` calls `_text(el, "node_type")`, which **returns `None` rather than raising**, on a document with no such element. So `None != "NodeType.slave"` is true for every node, every node is skipped, and the target list is empty — §2's **first** row, the silent one. The model was never migrated, so there is no `AttributeError` branch to hope for. **Run 2026-09-18 against a converted map**: `slave_avahi_names -> ([], [])` and `slave_ips -> []`. Note the second element — the **unresolvable list is empty too**, so not even the `ERROR … has no role_id/alias/hostname` path fires. There is no log line anywhere saying anything is wrong.
  - **(d) The public path adds three preconditions the findings document could not know**, all measured 2026-09-18 by running it, and all consequences of choosing to delete the parser rather than migrate it: (i) `/etc/cuems/settings.xml` must exist and be schema-valid, because `ConfigManager.__init__` calls `ConfigBase.load_base_settings` **unconditionally — even with `load_all=False`** — which promotes findings §5 from a secondary fragility to a **hard precondition**, against a file **no package ships**; (ii) this host's own uuid must have an entry in the map, or `load_network_map()` raises `ValueError: Node with uuid … not found`, since `node_network_map` resolves eagerly; (iii) every node entry must be schema-valid (`uuid` canonical, `mac`, `name`, `node_role`, `ip` all `minOccurs="1"`), where `parse()` today requires only `<uuid>` — so every fixture in the repository is rewritten, and an operator-hand-maintained map missing a `<mac>` now raises where it used to yield a partial node. Against that cost: an unconverted map raises a **named, actionable** `SchemaError` naming `cuems-migrate-network-map`, which is the loud failure §2 asks for, already built.
- [ ] T072 [US11] Verify the parser migration landed at **all three** sites from T071(a) — the role filter on `NodeRole`, `node_type` gone — and that `Node`'s other five attributes (`uuid`, `avahi`, `role_id`, `alias`, `hostname`) still behave, since the selection logic uses all of them; record per site in `specs/010-consumer-migration/baseline.md` (FR-070, SC-007). **Settled 2026-09-18: the private parser is deleted, not migrated** — the findings document's **option C**, which is also what flow 06 required of this same file under D32 and D11 before the two were known to be one repository. Options A and B are closed: A leaves the fourth copy of the node model in place (T079's root cause) and B keeps two vocabularies alive in the repository the ecosystem is retiring them from. What survives is a **thin adapter** over `ConfigManager.network_map` preserving both field-learned resolution policies — avahi ignores `<ip>`; `slave_ips` deliberately trusts it — verbatim
- [ ] T073 [US11] Verify the regression guard is **discriminating**, which is the FR-030a-ii discipline this class of caller demands: the bridge's current `tests/test_network_map_ips.py:13-19` fixtures are written in the **retired** vocabulary, so the suite is green *because* it certifies the defect. Two fixtures must exist — pre-007 (`<node_type>NodeType.slave</node_type>`) and post-007 (`<node_role>node</node_role>`) — and the post-007 one MUST **fail against the pre-migration parser**. A passing suite is not evidence here; record both fixtures and the failing run in `specs/010-consumer-migration/baseline.md` (SC-007)
- [ ] T074 [US11] Verify the **empty-selection invariant** the findings document asks for in §2: a stage-2 run that selects zero targets is an **error**, not a success. This is the check that would have made the original failure loud, and it is the only item here that survives the vocabulary question entirely — a future field rename breaks the selection the same silent way. Record where it landed (the tool, the bridge, or both) in `specs/010-consumer-migration/baseline.md`
- [ ] T075 [US11] Verify **both** broken features recover, separately measured, because they fail and recover independently (T071(b)): (i) orderly cluster power-off selects the expected nodes from a converted map, and (ii) the autoload / NNG-hub readiness gate does too. Record both in `specs/010-consumer-migration/baseline.md`; a single "the bridge works now" is not this task's answer
- [ ] T076 [US11] Verify the bridge's `cuemsutils` dependency is **non-optional and bounded**: `pyproject.toml:36` moved out of `[tool.poetry.extras]` and bounded like `cuems-nodeconf`'s (`>=0.1.0rc16,<0.1.1`), and `debian/control:18`'s floor raised and bounded. **Corrected 2026-09-18 on two points.** First, FR-053's "`cuems-wsclient`'s identical pin" is not an analogy — it is the *same line of the same file*, since the two names are one repository. Second, this task's premise that `debian/control` has **no** `cuems-utils` relation is **wrong**: `:18` declares `cuems-utils (>= 0.1.0rc5)` and `:19` declares `cuems-common (>= 1.0.0)`. The defect is a stale, unbounded floor, not an absent edge — which changes the fix from *add a relation* to *raise and bound one*. Record in `specs/010-consumer-migration/contracts/release-gate.md` as that table's **sixth** row, not a seventh — depends on T038
- [ ] T077 [US11] Decide and record the `cuems-common` ↔ `cuems-power-bridge` packaging edge (findings §8): `Suggests:` carries no version, so nothing today refuses a new tool beside an old bridge or the reverse. Whichever side changes first acquires a `Breaks:` against the versions of the other that cannot work with it. **`Suggests:` MUST be preserved as-is** — it is deliberately not `Depends:`/`Recommends:` so `cuems-common` stays functional on a host with no bridge, and both scripts already log one ERROR and exit 0 when the venv interpreter is absent. Record in `specs/010-consumer-migration/contracts/release-gate.md` (FR-091's pattern, applied to an edge FR-091 did not enumerate)
- [ ] T078 [P] [US11] Record the two secondary findings so they are decided rather than inherited (findings §5): (i) `own_uuid()` reads `/etc/cuems/settings.xml`, which **no package ships** — it swallows every exception and returns `None`, silently disabling uuid-based self-exclusion on any host lacking it; and (ii) `cuems-cluster-poweroff:240`'s docstring still says "matches the network_map `NodeType.master` entry" — stale prose in the same family as the defect. Record in `specs/010-consumer-migration/migration-guide.md`; (i) is a **decision**, not a bug to fix silently
- [ ] T079 [US11] Record the **root cause** in `specs/010-consumer-migration/migration-guide.md`, because it outlives this defect: the bridge carries a **parallel implementation of the node-identity model** — `role_id → alias → hostname → uuid`, the same resolution `cuemsutils` owns and `cuems-common`'s `cuems-logs` performs. It uses bare `ElementTree` with namespace-agnostic local-name matching and **validates against no schema** (verified 2026-09-17), so a vocabulary change cannot fail loudly there by construction. The vocabulary break is the symptom; the fourth copy of the model is the cause, and 007 FR-030a-i's "the node model lives in `cuemsutils` only" is the rule it violates. **Updated 2026-09-18**: the findings document names option C as the *direction of travel*, but T072 now **schedules** it — the copy is deleted by this feature, so what T079 records is no longer a deferred intention. Record instead **why a fourth copy existed at all**: the repository was absent from the list for two features under one name and re-discovered under another, so nothing ever told it that `cuemsutils` owned the model. That cause outlives this defect; the copy does not

**Checkpoint**: every consumer flow has landed and is recorded. Wave 4 can begin.

---

## Phase 5: User Story 9 — An operator upgrades a cluster and it comes back whole (Priority: P3)

**Goal**: packages refuse combinations that cannot work; the document library converts with its
backups retained; and both rollback procedures are executed rather than written.

**Independent Test**: an out-of-order install is actually refused; a controller-plus-node upgrade
returns with topology intact.

**Depends on**: Phase 4 complete (all consumer flows merged).

### Tests for User Story 9 (REQUIRED) ⚠️

- [ ] T035 [P] [US9] Test that the conversion's check mode reports per-document versions and **writes nothing**, in `tests/contract/test_convert_documents_check.py` (FR-103)
- [ ] T036 [P] [US9] Test that re-running the conversion over a partly converted library converts only the remainder, writes no second backup and corrupts nothing, in `tests/integration/test_conversion_resume.py` — this **verifies a property 008's design already provides** rather than driving new code (FR-095c, SC-017b, research R3)

### Implementation for User Story 9

- [ ] T037 [US9] Add the no-write check mode to `src/cuemsutils/xml/convert_documents.py` — per-document versions plus a library-level summary, in the reporting style the tool already uses (FR-103, research R4). Recorded in the plan as this repository's third scope enlargement
- [ ] T037a [US9] Verify **convert-on-read**: a library the operator has not converted still opens — every document loads, older ones converted in memory, disk untouched. This is what makes FR-095's operator-triggered conversion safe rather than merely convenient, and FR-095a requires it **verified, not assumed**; record in `specs/010-consumer-migration/baseline.md` (FR-095a)
- [ ] T037b [US9] Confirm `cuems-editor` has acquired Debian packaging, so it can declare a package relation at all — it has no `debian/` directory today, and FR-091's four edges presume it does. This is a **precondition** of T038, not a parallel task (FR-090a)
- [ ] T038 [US9] Supply the **four** missing package edges — `cuems-engine`, `cuems-editor`, `cuems-nodeconf` and `cuems-power-bridge`, named rather than counted — and reconcile `cuems-engine`'s two disagreeing floors; record the result in `specs/010-consumer-migration/contracts/release-gate.md` (FR-091, FR-092). **Corrected 2026-09-18 from five back to four**: the fifth was `cuems-wsclient`, which is `cuems-power-bridge` under its pre-2026-06 name, so the edge was listed twice. FR-091's original four stand — the enumeration was right and the growth was the error. A count that silently grows *or shrinks* is the failure this task exists to prevent, so both movements are recorded rather than quietly reconciled. Depends on T037b
- [ ] T038a [US9] Record the rollback **trigger** — the decision owner and the observable conditions that qualify — in `specs/010-consumer-migration/migration-guide.md` (FR-100a)
- [ ] T038b [US9] Record the conversion's **storage cost** in `specs/010-consumer-migration/migration-guide.md` before the conversion runs: backups double a library's on-disk size until reclaimed, so a volume too small to hold both is a foreseeable failure (FR-102a)
- [ ] T039 [US9] Run 007's deferred mechanical demonstration — install an out-of-order combination and record the package manager's **refusal** — in a disposable container; record in `specs/010-consumer-migration/baseline.md` (FR-093, SC-015)
- [ ] T040 [US9] Decide and record the `postinst` ordering of the configuration conversion against the service restart, in `specs/010-consumer-migration/migration-guide.md` (FR-094)
- [ ] T041 [US9] Record in `specs/010-consumer-migration/migration-guide.md` the show-conversion trigger (an explicit operator command), the deploy-path exposure, and the safe upgrade order — **nodes first** (FR-095, FR-095b, FR-096, FR-036)
- [ ] T042 [US9] Run the conversion against a real library of **hundreds** of documents and record in `specs/010-consumer-migration/baseline.md`: documents converted (counted, not sampled), backups retained, elapsed time, and the **disk-space delta** — backups sit beside the documents and are never reclaimed automatically (SC-017, research R5)
- [ ] T043 [US9] Execute rollback drill A — pre-conversion, package downgrade only, no document touched — and record the procedure and outcome in `specs/010-consumer-migration/migration-guide.md` (FR-101, SC-017a)
- [ ] T044 [US9] Execute rollback drill B — post-conversion, downgrade plus restore from the retained backups — and record the procedure and outcome in `specs/010-consumer-migration/migration-guide.md` (FR-102, SC-017a)
- [ ] T045 [US9] Record the backup retention rule in `specs/010-consumer-migration/migration-guide.md`: retained indefinitely, reclaimed only by explicit operator action, no earlier than after the post-upgrade verification passes **and** the observable condition is met — at least one show has been loaded from the converted library and run to completion on the cluster (FR-102, research R5)
- [ ] T046 [US9] Run the cluster upgrade — controller plus at least one node, nodes first — and confirm every node discovered, adoption preserved and a show loadable on each; record in `specs/010-consumer-migration/baseline.md` (SC-016). **Also exercise the orderly power-off on that cluster** (US11/T075): it reads the converted map through `cuems-power-bridge`, it is the one path whose failure is silent *and* physical, and this is the only task in the feature that has a real cluster to run it on
- [ ] T047 [US9] Run the end-to-end check from `specs/010-consumer-migration/quickstart.md`: a project saved by the editor loads in the engine and renders in the UI, differing from today in exactly the two enumerated ways; record in `specs/010-consumer-migration/baseline.md` (SC-005)
- [ ] T048 [US9] Verify the payload-version handshake defined in `specs/010-consumer-migration/contracts/editor-ui-messages.md` refuses a deliberately **stale** UI bundle and says why; record in `specs/010-consumer-migration/baseline.md` (FR-105, SC-015a)

**Checkpoint**: the release gate is mechanical and demonstrated; the data migration is proven at scale.

---

## Phase 6: User Story 10 — The deprecated surface comes out and the guide records what moved (Priority: P3)

**Goal**: delete the deprecated surface, move to the promised release, and hand over a guide that
maps every removed or changed entry point to its replacement.

**Independent Test**: the measured import census across six consumer checkouts is zero; the
deletions land; the suite is green and faster.

**Depends on**: **a measured zero**, not on "Phase 5 is merged".

### 🛑 GATE — T049 and T050 block every deletion below

FR-090 requires this ordering to be structural. **T051–T061 must not start** until T050 records a
zero. "The consumer flows are merged" is a different claim from "the imports are gone", and the
difference is a broken daemon.

- [ ] T049 [US10] Re-run the import census across all **six** consumer checkouts under `/disk/Projects/StageLab/` — **corrected 2026-09-18 from seven**: `cuems-power-bridge` is the sixth under its current name, not a seventh beside `cuems-wsclient`. Census the **live** checkout; `/disk/Projects/StageLab/cuems-wsclient` is a stale clone of the same remote, 30 commits behind, and censusing it would both double-count and measure a tree nobody ships from — and write the result — per repository, per path, with the command that produced it — to `specs/010-consumer-migration/import-census.md`. **Required value: zero** (FR-029). Note the census greps **deprecated** paths, not **internal** ones, so a zero here does not carry the claim "reaches the library through public paths only" — that gap is recorded against `cuems-nodeconf` in `migration-guide.md` §4a and is not T049's to close
- [ ] T050 [US10] Confirm T049's census is dated **after** the last consumer merge, and re-run it immediately before T051, updating `specs/010-consumer-migration/import-census.md` with its own date and the merge it postdates — a repository can regress between merge and removal (FR-029, FR-029e, FR-090)

### Implementation for User Story 10

- [ ] T051 [P] [US10] Delete `src/cuemsutils/xml/Settings.py` (FR-029a) — blocked by T050
- [ ] T052 [P] [US10] Delete `src/cuemsutils/xml/XmlReaderWriter.py` (FR-029a) — blocked by T050
- [ ] T053 [US10] Delete `src/cuemsutils/xml/Parsers.py` (FR-029a) — **first** distinguish the retired `cuemsutils.xml.CuemsParser` alias from the delegating façade that is contractually required to stay silent; they are two different symbols (FR-029d) — blocked by T050
- [ ] T054 [P] [US10] Delete `src/cuemsutils/xml/CMLCuemsConverter.py` (FR-029a) — blocked by T050
- [ ] T055 [P] [US10] Delete `src/cuemsutils/timeoutloop.py` (FR-029a) — blocked by T050
- [ ] T056 [US10] Remove the seven aliases at `src/cuemsutils/xml/__init__.py:81-91`, keeping `__all__ = []` (FR-029a, FR-024) — depends on T051–T055
- [ ] T057 [P] [US10] Remove the deprecated-symbol site at `src/cuemsutils/xml/settings.py:170` (FR-029a)
- [ ] T058 [P] [US10] Remove the deprecated-symbol site at `src/cuemsutils/xml/XmlBuilder.py:362` (FR-029a)
- [ ] T059 [US10] Retire `tests/contract/test_deprecation_shims.py` **deliberately**, recording in `specs/010-consumer-migration/migration-guide.md` what replaces it and why deleting a contract test alongside the contract it guards is correct here (FR-029b)
- [ ] T060 [US10] Move `__version__` in `src/cuemsutils/__init__.py` to the release `_deprecation.REMOVAL_RELEASE` has promised since feature 006 — or record the divergence, because otherwise every warning this library emitted for two features was wrong (FR-029c)
- [ ] T061 [US10] Record the post-removal suite time in `specs/010-consumer-migration/baseline.md` — 22 contract tests retire, so it should be **faster**; if it is not, something else changed and must be explained (FR-PERF-001)

### The count and the guide

- [ ] T062 [US10] Run the ecosystem-wide count — **with a denominator the command discovers rather than a fixed list of checkouts**, because the list was wrong **three times** (`cuems-wsclient` absent, FR-UX-002; `cuems-power-bridge` absent, US11; the two counted as separate repositories, 2026-09-18) and three is a pattern, not an accident; the paths it covers MUST therefore be "every repository under `/disk/Projects/StageLab/` that reads `network_map.xml`", enumerated by the command itself **and de-duplicated by git remote rather than by directory name** — name-based de-duplication is exactly what missed the third error, since the two checkouts differ in directory name, package name and import name while sharing a history — and record it in `specs/010-consumer-migration/migration-guide.md` **with the counting method (the exact command and the paths it covers) recorded alongside it** (FR-070b), **with its exempt set enumerated as `<path>:<start_line>[-<end_line>]`** — line numbers **re-measured at the time of the count, not copied**, since the inherited audit numbers were already stale by 2026-09-04 (FR-072) — **and the two exemption reasons stated separately** — "exists to detect or convert the retired spelling" (permanent) and "not shipped" (removable at any time). Merging them is how a working migration diagnostic gets deleted by the next person to run the count (FR-070–FR-073a, SC-006)
- [ ] T063 [P] [US10] Correct the three stale documents that are this feature's own inputs (FR-005): this repository's `CLAUDE.md` (which describes a sibling's node-identity work as not started when it has been on a branch since 2026-08-24), `cuems-common`'s `CLAUDE.md:88` (which assigns a role-constant migration to a closed feature number), and `cuems-nodeconf`'s `AvahiTool.py:12` / `CuemsAvahiListener.py:19-24` (which defer the discovery key to a closed feature)
- [ ] T064 [US10] Complete `specs/010-consumer-migration/migration-guide.md`: every removed or changed entry point mapped to its replacement with before/after examples (FR-UX-001), `cuems-power-bridge` listed as a consumer under its current name, with the 2026-06 rename from `cuems-wsclient` noted so the entry is findable by both (FR-UX-002), the count with its exempt set (FR-UX-003), and one section stating **which obligation landed in which repository** — seven flows produce seven task lists and no single view of the whole (FR-UX-004)

**Checkpoint**: the release gate is closed and the ecosystem can ship.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T065 Validate every performance budget and record each in `specs/010-consumer-migration/baseline.md`, including any that is **exceeded — recorded as exceeded rather than restated as passing** (FR-PERF-001, SC-PERF-001)
- [ ] T066 [P] Record `network_map` config load against **008's post-landing 10.14–10.49 ms**, noting explicitly that this feature inherits an already-marginal position rather than 007's ≤10.20 ms cap, in `specs/010-consumer-migration/baseline.md` (research R6)
- [ ] T067 Run `specs/010-consumer-migration/quickstart.md` end to end and correct anything it gets wrong
- [ ] T068 [P] UX consistency pass over the new message family (`specs/010-consumer-migration/contracts/editor-ui-messages.md`) and `src/cuemsutils/xml/convert_documents.py`'s output — one reporting idiom, not two (Constitution III)
- [ ] T069 Compile the durable material out of `specs/planning/xml-rebuild/` into a new binding reference at `specs/agreements/xml-architecture-invariants.md`, following the house shape of that folder (title, adopted-by line, applies-to, `Status: binding`). It MUST carry, in the reader's terms rather than as a decision log: the settled decisions that still **bind** (D2 schema as the single source of truth; D12 public surface returns objects; D15 the two public objects; D17/D18 every time-carrying element typed and canonical; D19/D21 the three load outcomes; D22 where network-map logic lives; D25 descriptor-derived generation; D32 the consumer repositories — recorded as **seven, and as a list that was wrong three times**, since the durable lesson is the discovery method, not the number: `cuems-wsclient` was absent (FR-UX-002), `cuems-power-bridge` was absent (US11), and then the two were counted as separate repositories when they are one, renamed (2026-09-18). Each error was found by a gate reading the filesystem rather than by the list, and a silent failure shipped in the meantime. Record the de-duplication rule — **by git remote, not by directory name** — as part of the decision, because that is the part that would have caught all three; D33 the discovery vocabulary's two owners; D34 the descriptor's single public path; Q11→(c) and Q14→(i)); the standing rules from `xml-rebuild-07-speckit-prompts.md` §10; the editor→UI payload's **two-delta** constraint (never restated as unconditional byte-identity); the node model's exclusivity to `cuemsutils` (007 FR-030a-i); the "keeps resolving but becomes wrong" caller class and the discipline it demands (007 FR-030a-ii); and the retired-vocabulary count's **enumerated exempt set with its two distinct reasons** (D36/C12). It MUST link to `specs/agreements/schema-evolution-convention.md` rather than restating it. It MUST **exclude** the decisions that were about *how to land this work* and are now spent history — D28's item ordering, D30's two-phase split of 008, D31's deliberate stop, D27's release gate once the release has happened — because a binding reference that carries expired scheduling teaches the next reader to follow it (`CLAUDE.md`'s "promoted into `specs/agreements/`" clause)
- [ ] T069b Assess each `specs/planning/xml-rebuild/` document against `CLAUDE.md`'s deletion policy and record the verdict **per document** in `specs/010-consumer-migration/migration-guide.md` — **blocked by T069**, and it **deletes nothing**: this task decides, T069c executes. A document is dischargeable only when all three hold: its durable content has landed in T069's agreement file, its executed content is captured in `specs/NNN-*/`, and it carries **no scheduled-but-unexecuted residue** (see T069c). Record the three verdicts separately rather than as one yes/no, because a document can fail on residue alone while being otherwise spent. Note explicitly that the ~65 references from the frozen specs `004`–`009` are **not** a blocker: `CLAUDE.md` sanctions those dangling, since a landed spec's cross-references are not retroactively rewritten
- [ ] T069c Clear the two things that make deletion safe, then delete only the documents T069b cleared. **(a) Residue**: relocate scheduled-but-unexecuted content to a home that outlives the folder — the known instance is `xml-rebuild-01-audit.md` §6's **X13–X17** schema debt, whose natural home is `specs/agreements/schema-evolution-convention.md`, where X13 (`gradient_osc_port`) is *already* recorded as scheduled work. Deleting the folder with that residue in it would destroy the only detailed record of open work, which is the failure `CLAUDE.md`'s "made and acted on" test exists to prevent. **(b) Active referrers**: update, in the same commit, the four documents that are not frozen and would otherwise point at nothing — `CLAUDE.md:12` (cites `xml-rebuild-09` as the corrector of a claim; T063 already edits this line), `CHANGELOG.md:116` (cites `xml-rebuild-01` §6 for exactly the X13–X17 debt (a) relocates), `tests/data/corpus/negative/README.md:59` (cites `xml-rebuild-07` §5.1/§9 for why the negative corpus exists), and `specs/planning/nodeconf-atomization.md:10` (cites `xml-rebuild-08` §4/E11 as provenance — it already reproduced that table into itself, which is the pattern T069 generalises, so this is a citation fix, not a content rescue). Only then delete. If a document survives because its residue could not be relocated, that is the **correct** outcome and is recorded as such — an empty folder earned document by document, never asserted

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (Foundational)**: after Phase 1 — blocks US3
- **Phase 3 (US3)**: after Phase 2 — **blocks consumer flows 02 and 05**, so it is first in wall-clock terms as well as priority
- **Phase 4 (consumer gates)**: each task blocked by its own consumer flow; the four wave-1 tracks are independent of US3 and of each other
- **Phase 5 (US9)**: after Phase 4 complete — **including US11**, whose T076/T077 feed T038's package edges and whose T075 is re-run on real hardware by T046
- **Phase 6 (US10)**: after **T050 records a zero** — not after Phase 5 merges
- **Phase 7 (Polish)**: after Phase 6. One ordering inside it is not cosmetic: **T069 → T069b → T069c**. The durable material is compiled into `specs/agreements/` first, the per-document verdict is recorded second, and only the third task deletes anything — after relocating scheduled-but-unexecuted residue and fixing the four active referrers. Reversed, the deletion destroys exactly what the compilation exists to preserve, and git history is not a substitute for a document an active file still cites. T069b deliberately holds no destructive step: the decision and the irreversible action are separate tasks so the decision can be reviewed before it is executed

### Story dependencies

| Story | Depends on | Note |
|---|---|---|
| ~~US1 `cuems-wsclient`~~ | — | **Merged into US11 2026-09-18** — same repository, renamed 2026-06. Its T018/T019 now point at `cuems-power-bridge` and duplicate T071/T072/T073 |
| US2 editor start-up | nothing | blocks US6 |
| US3 descriptor path | Phase 2 | **blocks US6 and US8** |
| US4 `cuems-engine` | nothing | |
| US5 discovery cutover | nothing | two repositories, **merged simultaneously** |
| US6 `cuems-editor` | US2, US3 | |
| US7 `cuems-nodeconf` | US3 | |
| US8 `cuems-frontend` | US3, US6 | characterization tests **before** the port |
| **US11 `cuems-power-bridge`** | nothing | **added 2026-09-17; absorbed US1 2026-09-18.** Independent of every other story — it neither imports the library's deprecated surface nor touches the descriptor. **Run it first**: it is a live silent failure, the failure is *physical*, and it has now gone unfixed across two features and two names. Its one coupling is that `cuems-common`'s `cuems-cluster-poweroff` must merge **simultaneously**, the way US5's two halves do — that tool calls this repository's parser directly |
| US9 rollout and gate | US2–US8, **US11** (which absorbed US1) | |
| US10 removal and guide | a **measured** zero | |

### Within each story

- Tests written and failing before implementation
- For the FR-030a-ii class, a passing suite is **not** evidence — each caller needs a test that fails against the old value
- Guide sections written as the work lands, not retrofitted at the end

---

## Parallel Opportunities

**Phase 3 (US3) — the four contract tests are independent files:**

```bash
Task: "Public == internal per schema in tests/contract/test_public_descriptor.py"
Task: "Constructible instances validate in tests/contract/test_descriptor_instances.py"
Task: "Laziness holds in tests/contract/test_descriptor_laziness.py"
Task: "__all__ stays [] in tests/contract/test_public_surface.py"
```

**Phase 4 — every gate task reads a different repository and writes a different guide section**, so
T018–T032 are fully parallel once their consumer flows land. **US11's T070–T079 are parallel with
all of them**, since no other story touches `cuems-power-bridge`; inside US11, T070 gates the flow
itself, T072–T075 wait on that flow landing, and T076 waits on T038.

**Phase 6 — the deletions are separate files** once the gate opens: T051, T052, T054, T055 in
parallel; T053 needs the symbol distinction first; T056 needs all five deleted.

**Across repositories**: the four wave-1 tracks (`cuems-power-bridge`, editor start-up, `cuems-engine`,
the discovery cutover) run in parallel with each other **and** with US3, since none depends on the
descriptor. The first of those four **is** US11 — it was briefly listed as a fifth track under the
name `cuems-wsclient` (US1) before the two were measured to be one repository on 2026-09-18. It
depends on neither the descriptor nor any other consumer, and its defect is already in the field.
Its only simultaneity constraint is outward: `cuems-common`'s `cuems-cluster-poweroff` merges with
it.

---

## Implementation Strategy

### MVP for this repository (US3 only)

1. Phase 1 → Phase 2 → Phase 3
2. **STOP and VALIDATE**: six schemas answer publicly and identically; instances validate; laziness
   holds; `__all__` is still `[]`
3. That unblocks two consumer flows — which is the entire reason US3 is P1 despite being neither the
   most urgent defect nor the largest work

### Incremental delivery

Wave 1's four tracks proceed in parallel with US3 in their own repositories. Phase 4 accumulates the
guide as they land. Nothing ships until Phase 6 closes — D27 holds across the whole feature.

### The one thing this strategy must not permit

An early Phase 6. T049/T050 exist so the possibility is absent from the file rather than avoided by
care (FR-090). If a deletion task is ever reached without a zero-valued census dated after the last
consumer merge, the correct action is to stop, not to check by hand.
