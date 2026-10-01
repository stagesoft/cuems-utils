<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Tasks: device-class reshape

**Input**: Design documents from `/specs/013-device-class-reshape/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: REQUIRED by the constitution (Principle II) and by SC-TEST-001. Every behaviour
change has a test that fails before the implementation and passes after it, with the
failing-first output recorded.

**Organization**: grouped by user story. Priority order is **not** the whole dependency
order here — the schema axes are forced A → B → C → D ([plan.md](plan.md)), US2's tool
lands in the **same commit** as the first schema edit, and US5's hash pin moves inside
each schema commit rather than in a trailing phase. Axes C and D are the rest of US1:
the story's independent test is the mappings document, and the later phases are what
make "a new class costs nothing" true for settings and scripts too.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable — different files, no dependency on an incomplete task
- **[Story]**: US1–US5, on user-story phases only

## Path Conventions

Single project: `src/cuemsutils/`, `tests/` at repository root.

## Run the suite

```bash
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q
```

`hatch` is not installed on this box and the `hatch test` env lacks `hypothesis` — see
[quickstart.md](quickstart.md).

## Two decisions recorded here

The plan left both of these to this file.

**FR-014 — how an unrecognised class is reported.** One INFO log line, not a
`LoadReport` field and not a new public function (a field would change a signature
`public_api.json` already pins). An unrecognised class is valid (A2, FR-002). The line
satisfies FR-UX-001 — schema, document, path, offending value, and what to do:

```text
project_mappings <file>: /node/devices/device[@class='vidoe'] has no conditional type; decoded as DeviceType. Check the spelling — an unknown class is valid, and this line is the only report.
```

The element path and the type name follow the element that actually fell back (`player`,
`Cue`, `CueOutput` likewise). A typo and a deliberate new class produce the same kind of
line; the operator tells them apart by reading the name. Asserted on the message text.

**SC-016 names three golden changes, not two.** `public_api.json` records console
scripts, so `cuems-reshape-devices` is a name alongside `partition_by_adoption` and
`validate_config_document`. The spec already says so. T035 updates the golden in the
same commit as the entry point; it does not amend the spec afterwards.

---

## Phase 1: Setup

**Purpose**: the four experiments and the snapshot that later phases are measured against.
Nothing in `src/` changes in this phase.

- [x] T001 Run E1 from [quickstart.md](quickstart.md) and record the decoded dict, pass or
      fail, in `specs/013-device-class-reshape/baseline.md`. If the discriminator is absent
      from the item dict, stop and follow the E1 fallback in [research.md](research.md)
      before any schema work — that fallback changes `Mapper._decode_member`
- [x] T002 [P] Run E2 and record the attribute path from which `@class='VALUE'` is
      extractable, in `baseline.md`. Derivation in T012 reads that path and no other. If
      `alternatives` is not exposed, record the `xs:appinfo` fallback and T012 follows it
- [x] T003 [P] Run E3 and record whether `count(d) = count(distinct-values(d/@class))`
      rejects a duplicate, in `baseline.md`. If the assert does not, T022 uses `xs:unique`
      on `class`. That is still a schema constraint, so SC-011 and a writer that only
      validates against the XSD still hold. A T2 rule does not satisfy FR-013: the editor
      would accept a duplicate class and this library would reject it, which is the split
      the clarification exists to prevent. If neither schema construct rejects the
      duplicate, stop. Record that in `baseline.md` and reopen the FR-013 clarification.
      Do not implement a load-path-only check, and do not tell the migration guide that
      XSD-only writers are uncovered
- [x] T004 [P] Run E4 before any `src/` edit. Three full-suite runs, plus the load path for
      `project_mappings`, `settings`, `script` and `hardware_outputs` by the method in
      `tests/integration/test_read_path_regression.py` (best of 3 medians of 5 warm runs).
      Write every denominator into `baseline.md`. SC-PERF-001 is a ratio to this number;
      SC-PERF-002 stays ≤ 18.04 ms/test. On `tests/support/library_fixture.py`'s
      `remint_200`, also time a calibration: read every file and atomically rewrite it
      with no device-class substitution. Write that MB/s range into `baseline.md` as the
      SC-PERF-003 budget (FR-PERF-003). T062 compares against this number and does not
      choose another. Quote ranges — `test_descriptor_laziness` moves the skip count by
      ±1 on an unmodified tree
- [x] T005 Copy one old-shape example of each reshaped document (`project_mappings`,
      `settings`, a script, `hardware_outputs`) into `tests/data/corpus/pre-013/`, with a
      README stating these are the pre-narrowing snapshots and that `pre-008/` is left
      alone (R13). This directory is the migration fixture and the FR-027 fixture. It
      cannot be produced from the tree after T020
- [x] T006 [P] Confirm `spec.md` already records M10–M13, FR-012a, the widened
      FR-030, FR-032, FR-033 and FR-042, and A4's three arms. Do not re-fold research.
      If a site in R7–R10 is missing from the spec, stop and add it before any schema
      edit. The guide (T051) is checked against that text, not against a later amendment

**Checkpoint**: experiments recorded, old-shape corpus exists, `src/` untouched.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the derivation and the single dispatch every reshaped schema decodes through.
No schema is edited in this phase — `FieldSpec.alternatives` defaults to `()` and every
current derivation stays identical.

**⚠️ CRITICAL**: no schema edit until this phase is complete. A narrowed schema the engine
cannot decode is not an intermediate state.

### Tests first

- [x] T007 [P] Failing-first unit test `tests/unit/test_fieldspec_alternatives.py` — a
      conditional element yields `(class value, type)` pairs in schema order; an
      unconditional element yields `()`; a test that is not exactly `@class='VALUE'` is a
      derivation error, not a silently ignored alternative (contracts/schema-conventions.md
      rules 2–3)
- [x] T008 [P] Failing-first unit test `tests/unit/test_alternative_dispatch.py` — a body
      whose `class` matches an alternative decodes to that type's model; an unknown class
      and a missing class both decode through `member.child`
- [x] T009 [P] Contract test `tests/contract/test_class_conditional_convention.py`
      enforcing the five rules in [contracts/schema-conventions.md](contracts/schema-conventions.md)
      against every file in `src/cuemsutils/xml/schemas/`. Passes on today's schemas
      (nothing is conditional yet) and fails when a later edit breaks a rule
- [x] T010 [P] Failing-first test `tests/unit/test_unknown_class_report.py` — decoding a
      class that selects the fallback logs the INFO line in the FR-014 decision above,
      including schema, document, element path, class value and the spelling check.
      Assert the message text. No new field on `LoadReport`

### Implementation

- [x] T011 Add `alternatives: tuple[tuple[str, TypeKey], ...] = ()` to `FieldSpec` in
      `src/cuemsutils/xml/spec.py`. A tuple of pairs, not a dict: `FieldSpec` is frozen
      and hashed, and derivation is `lru_cache`d (data-model §5.1)
- [x] T012 Derive `alternatives` inside `spec.derive` from the schema, using the attribute
      path T002 recorded. Accept only `@class='VALUE'`. Do not map `"video"` to
      `VideoDeviceType` by name — `registry.py`'s docstring records what that cost last time
- [x] T013 Rewrite the counting claim in `_derive_attributes`' docstring
      (`src/cuemsutils/xml/spec.py`, the paragraph that states how many declared attributes
      exist). `class` is the third kind (R4). It is a dict key named `class`; no Python
      `@property` takes that name, and it is not added to `ATTRIBUTES_THE_MODEL_DOES_NOT_OWN`
- [x] T014 Implement `Mapper._alternative_for` and call it from `_decode_member` in
      `src/cuemsutils/xml/mapper.py` — the only decode-side change, because
      `_decode_repeated` and `_decode_wrapper` already funnel through there (R1). The
      discriminator is the bare key `class` (`attr_prefix=""`). Unknown or absent class
      falls back to `member.child`
- [x] T015 On the build side in `src/cuemsutils/xml/mapper.py`, `_tag_for_item` emits the
      declared element name when the field carries alternatives, and `class` is written by
      the existing attribute path (`element.set`) because it is a declared field
- [x] T016 When `_alternative_for` selects the fallback for a class that is present, log
      the INFO line T010 asserts, from `src/cuemsutils/xml/mapper.py`. Include the
      schema, the document, the element path, the class and the decoded type, plus the
      spelling check (FR-UX-001). Do not warn on a class that matched an alternative.
      If the decode has no file path, say so in the line rather than omitting the
      document field

**Checkpoint**: dispatch exists and is unused. Today's documents still decode byte-identical.

---

## Phase 3: User Story 1 — a new class by writing a mappings document (Priority: P1) 🎯 MVP

**Goal**: `<device class="lighting">` validates, decodes and is reported, with no schema
edit and no constant naming that class. `canvas_region` still belongs only to `video`.

**Independent Test**: author a mappings document with an `audio` device, a `video` device
carrying a `canvas_region`, and a `lighting` device. It validates; the decoded node
reports three classes including `lighting`; a `canvas_region` on `lighting` is rejected;
two devices of the same class are rejected by the schema alone.

### Tests for User Story 1

- [x] T017 [P] [US1] Failing-first contract test `tests/contract/test_device_class_open.py`
      — a mappings document with `<device class="lighting">` validates and decodes to a
      device whose `class` is `lighting`, and no name `lighting` exists under
      `src/cuemsutils/` except the test itself (scenario 1, FR-004, SC-001)
- [x] T018 [P] [US1] Failing-first contract test
      `tests/contract/test_class_conditional_fields.py` — `canvas_region` on a device
      whose class is not `video` is rejected; the same element on `video` is accepted
      (scenario 3, FR-003)
- [x] T019 [P] [US1] Failing-first contract test
      `tests/contract/test_device_class_uniqueness.py` — two `audio` devices on one node
      are rejected by `XMLSchema11.is_valid` **with this library's load path not imported**
      (SC-011, FR-013). Uses the mechanism T003 recorded. If T003 stopped because no
      schema construct rejects the duplicate, this test is not rewritten as a T2 test
- [x] T067 [P] [US1] Failing-first contract test
      `tests/contract/test_special_field_class_cost.py` — a class that needs a special
      field costs exactly one `xs:alternative` plus the type it names, in one schema,
      and nowhere else (FR-005, SC-002). Build the fixture from the reshaped
      `project_mappings` convention: the diff from the no-special-field baseline is one
      alternative and one type. A second declaration — another schema, a Python class
      list, a registry table — fails the test. `canvas_region` on `video` is the worked
      example the fixture mirrors, not a second place the cost is allowed to hide

### Implementation for User Story 1

**Same-commit cluster: T020, T021, T022, T023, T024.** A commit that narrows the schema
without the diagnosis is the X13 failure mode FR-027 exists to prevent. The hash pin
moves in that same commit (US5, done here because it cannot lag).

- [x] T020 [US1] Reshape `src/cuemsutils/xml/schemas/project_mappings.xsd` per
      [data-model.md](data-model.md) §2. `NodeMappingType` keeps single `uuid` and `mac`
      children; devices move into `DevicesType`, a container holding only repeated
      `device` (R2 — a type that mixes single children with a repeated one silently drops
      `uuid` and `mac` in `converter.py`). `device` is `DeviceType` with
      `xs:alternative test="@class='video'"` selecting `VideoDeviceType` and an
      unconditional fallback. Both types gain required attribute `class`. The six root
      `default_*` elements become `DefaultsType` of repeated `default` with required
      `class` and `direction` (`input`|`output`). A schema comment states why the
      containers exist, pointing at R2
- [x] T021 [US1] In the same commit: old-shape diagnosis in
      `read_document_versioned` (`src/cuemsutils/xml/documents.py`), after the version
      probe and before `to_dict`. An old-shape `project_mappings` raises a message naming
      the document path, `<audio>/<video>/<dmx> on <node>`, and `cuems-reshape-devices`,
      the wording in [contracts/cli-reshape-devices.md](contracts/cli-reshape-devices.md).
      This task covers `project_mappings` only. The script load path is T047, not a
      leftover to confirm later. Asserted by `tests/integration/test_old_shape_diagnosis.py`
      against `tests/data/corpus/pre-013/`, on the message text (SC-005)
- [x] T022 [US1] In the same commit: the class-uniqueness `xs:assert` on `DevicesType` and
      the class+direction assert on `DefaultsType`, using the mechanism T003 recorded
      (the assert, or `xs:unique` — not a T2 rule; data-model §2.1, §2.2, R5). The
      defaults assert is the same FR-013 rule applied
      to the root pairs, not an extra requirement
- [x] T023 [US1] In the same commit: move `project_mappings`' entry in `CURRENT_SCHEMA_HASHES`
      (`tests/contract/test_schema_scope.py`) to the new file's sha256. If a type name is
      now declared in more than one schema, add it to `KNOWN_IDENTICAL_DUPLICATES`
      (`tests/contract/test_schema_name_overlap.py`). `KNOWN_DIVERGENT_DECLARATIONS` stays
      empty. `CURRENT_VERSION`, the conversion registry and `DELIBERATE_IDENTITY_STEPS`
      are not edited (FR-020, SC-006)
- [x] T024 [US1] In the same commit: the seed and generator side of axis A, so the package
      build still produces a valid `default_mappings.xml` (R14, FR-043's mappings half).
      `src/cuemsutils/defaults/system-defaults.toml` (the six `default_*` keys),
      `TABLE_KEYS` in `src/cuemsutils/xml/seed_values.py`, and whatever
      `src/cuemsutils/xml/make_defaults.py` emits for the mappings document. V1 and V2
      must still pass. `debian/rules` regenerates through the built venv — a broken
      generator fails the build, not a test. In this same commit, migrate every
      current-corpus `project_mappings` document (not `pre-008/`, not `pre-013/`) and
      any golden that this schema invalidates, so each validates against the reshaped
      schema. The schema is the source of truth; the files are updated to match it
      (FR-055, SC-004)
- [x] T025 [US1] Derived legacy keys in `src/cuemsutils/tools/ConfigManager.py`, with no
      class tuple: `node_mappings["audio"]` (and any other class the document carries)
      answers from `devices` (FR-012a, D1, R10 — `NodeEngine.py:508,598` uses `.get` and
      would otherwise configure no ports, silently); `default_audio_output` and its five
      siblings answer from `defaults`. Test
      `tests/integration/test_legacy_mapping_keys.py` asserts each spelling against a
      reshaped document
- [x] T026 [US1] One `HardwareOutputs` definition in `src/cuemsutils/tools/ConfigManager.py`
      replacing the six-key literals at `:159` and `:283` (data-model §5.3, R11). It is
      filled by walking the document's devices, not `_DEVICE_SECTIONS`. `__missing__`
      returns `[]` for a well-formed `{class}_{inputs|outputs}` key and the subscript of
      a typo stays a `KeyError` — `dict.get` does not consult `__missing__`, which is what
      keeps `NodeEngine.py:456` truthful. Test
      `tests/unit/test_hardware_outputs_missing.py` covers the empty answer (scenario 4,
      FR-012), the lighting entry (scenario 2, FR-011) and the typo
- [x] T027 [US1] Retarget `one_custom_template_per_node` in `src/cuemsutils/xml/validators.py`
      off `("NodeMappingType", "video")`. `run_rules` skips a rule whose field is absent
      (`validators.py` around the absent-field continue), so a stale binding does not
      fail — two custom templates would start loading (R12, FR-015). The body filters by
      `class='video'`. Move the pin in `tests/contract/test_rule_targets_resolve.py` in
      the same commit. `validate_custom_templates` (`validators.py`, the `node.get("video")`
      walk) and `check_canvas_region_containment` reach video devices through the class
      (FR-016). The rule keeps its exact wording and `repairable=False`

**Checkpoint**: a greenfield mappings document in the new shape loads, including a class
the library has never named. An old-shape mappings document does not load, and says why.
US2's tool does not exist yet — old documents are diagnosed, not yet migrated.

---

## Phase 4: User Story 2 — one tool migrates every old-shape document (Priority: P2)

**Goal**: `cuems-reshape-devices` rewrites an installation once, backs up first, and
changes nothing on a second run. This phase ships the tool and the axis A
transformation. Axes C and D add their transformations in those phases; the tool must
not claim to migrate a schema that has not narrowed yet.

**Independent Test**: a fixture installation — configuration plus a library of old-shape
mappings and scripts — comes out validating, field-for-field equal to a hand-authored
new-shape equivalent, each file backed up, `doc_version` unchanged, and a second run
changes no bytes.

### Tests for User Story 2

- [x] T028 [P] [US2] Contract test `tests/contract/test_reshape_idempotent.py` — a second
      run reports nothing to do and no file's bytes change (FR-026). Compare bytes, not
      the report
- [x] T029 [P] [US2] Contract test `tests/contract/test_reshape_backup.py` — each rewrite
      is preceded by `<name>.<YYYYMMDDTHHMMSS>.bak` via `shutil.copy2`, and a backup
      failure leaves that document unrewritten while the run continues (FR-025)
- [x] T030 [P] [US2] Integration test `tests/integration/test_reshape_roundtrip.py` — an
      old-shape mappings document and its hand-authored new-shape equivalent decode
      equal field for field (FR-024, scenario 2). No value is computed or dropped
- [x] T031 [P] [US2] Integration test `tests/integration/test_reshape_discovery.py` — with
      no PATH arguments the tool discovers `CUEMS_CONF_PATH` and the library through
      `src/cuemsutils/tools/library_reach.py`; a script not named `script.xml` is found
      by root element (FR-023, scenario 7); an unrecognised root is skipped and named
- [x] T032 [P] [US2] Contract test `tests/contract/test_reshape_leaves_version.py` — a
      rewritten document's `doc_version` equals the value it arrived with (FR-020,
      scenario 6)
- [x] T033 [P] [US2] Integration test `tests/integration/test_reshape_modes.py` — exit 0
      when everything is new-shape, exit 1 when `--check` finds an old-shape document or
      a document was skipped, exit 2 on a usage error or an unresolvable installation.
      `--dry-run` writes nothing and names the backup path each document would get
      ([contracts/cli-reshape-devices.md](contracts/cli-reshape-devices.md))

### Implementation for User Story 2

- [x] T034 [US2] Implement `src/cuemsutils/xml/reshape_devices.py` per the contract.
      Stdlib `ElementTree` only — the document it reads is invalid against the current
      schema, which is the normal case. Schema by root element, the way
      `convert_documents` does. Shape classification: old if a reshaped element name is
      present at its old position, new if the container is present; the two cannot
      coexist under `xs:sequence` (FR-021). Backup, then reshape, then validate against
      the current schema, then `documents.write_tree`. A document that would not
      validate is not written. Per-document `<path>: <verdict>` lines and a closing
      summary. This task ships the **axis A** transformations from
      [data-model.md](data-model.md) §6 only
- [x] T035 [US2] Register the entry point in `pyproject.toml` `[project.scripts]`:
      `cuems-reshape-devices = "cuemsutils.xml.reshape_devices:main"`. Add the name to
      `PUBLIC_SCRIPTS` in `tests/support/public_api.py`. Update
      `tests/golden/api/public_api.json` in **this same commit** for the script entry
      only, with the reason in the commit message. SC-016 already names the script;
      do not leave the golden for a follow-up. FR-035 and FR-036 are a later, separate
      golden event
- [x] T036 [US2] Idempotence and the "not applicable" line for documents this feature
      does not reshape (`network_map.xml`, `project_settings`). The tool never calls
      `cuems-convert-documents`' version gate and never touches feature 012's identity
      surface (`SENTINEL`, `coerce_identity`, `--remint`)

**Checkpoint**: an old-shape mappings installation migrates in one run and is untouched
on the second. Settings and scripts are still old-shape; the tool skips them as not
applicable until their phases add a transformation.

---

## Phase 5: User Story 3 — the library stops enumerating classes (Priority: P3)

**Goal**: no declared list of device-class names remains in `src/cuemsutils/`. The
inventory T026 builds is the only definition, and the video T2 rule still fires.

**Independent Test**: a mappings object carrying a class the library has never seen
answers from every public accessor that reports devices or hardware outputs, and a
contract test — not a grep by hand — asserts that no class list remains.

- [x] T037 [P] [US3] Failing-first: invert `tests/unit/test_mappings_shape.py` (the
      assertion `"_DEVICE_SECTIONS" in source`, around lines 136–141) to assert the name
      is **absent**. Deleting the constant without inverting this test leaves a ratchet
      that stays green while the behaviour it guarded is gone (R13)
- [x] T038 [P] [US3] Contract test `tests/contract/test_no_device_class_list.py` — an AST
      walk of `src/cuemsutils/` (precedent `tests/contract/test_node_field_coercion.py`)
      asserting no tuple, list, set or enum whose members are device-class names.
      Exempt, by name in the test: the schema files, and the migration tool's table of
      **old element names** (those are spellings being deleted, not a vocabulary being
      supported). A new exemption is a review item, not a quiet addition (FR-010, SC-003)
- [x] T039 [US3] Delete `_DEVICE_SECTIONS` from `src/cuemsutils/tools/ConfigManager.py`
      (`:69`) and both loops that iterate it (`:386`, `:659`). T026's walk is the only
      remaining definition (scenario 5, FR-011)
- [x] T040 [US3] Confirm T027's retarget is what `validate_custom_templates` actually
      calls, with a test that two custom video templates are still rejected **on the
      rule's own wording** (scenario 3, FR-015) and that `check_canvas_region_containment`
      still runs on a video output reached by class (scenario 4, FR-016). If T027 left
      a `node.get("video")` walk, this task removes it

**Checkpoint**: `lighting` is visible to every accessor, and the source contains no class
list a test can find.

---

## Phase 6: User Story 1 continued — axis C, the player sections

**Goal**: a new class adds no element to `NodeConfType`. `audiomixer` stays its own
element. The engine's six `node_conf["…player"]` reads keep answering.

**Independent Test**: a settings document with `<player class="video">`,
`<player class="audio">`, `<player class="dmx">` and an unchanged `<audiomixer>`
validates; `node_conf["videoplayer"]` returns the video player; a second player of
class `video` is rejected; `audiomixer` is not inside `<players>`.

- [x] T041 [P] [US1] Failing-first tests in `tests/contract/test_player_sections.py` —
      the reshaped document decodes; `audiomixer` is still a direct child of the node
      configuration (FR-040a); a duplicate player class is rejected (the same assert
      shape as T022); `node_conf["videoplayer"]`, `["audioplayer"]` and `["dmxplayer"]`
      answer with the same nested `path` / `args` / `osc_port` / `output_latency_ms`
      values as before (FR-042)
- [x] T042 [US1] Reshape `src/cuemsutils/xml/schemas/settings.xsd` per
      [data-model.md](data-model.md) §3. The three class-scoped players move into
      `PlayersType` of repeated `player`, with one `xs:alternative` per existing player
      type (`video`, `audio`, `dmx`) and an unconditional fallback. `audiomixer` stays
      exactly where it is. Uniqueness assert on `player/@class`. Same-commit obligations:
      `CURRENT_SCHEMA_HASHES` for `settings`, the old-shape diagnosis naming
      `<videoplayer>/<audioplayer>/<dmxplayer>` (extend T021's check), and the seed side
      — `system-defaults.toml` player tables, `TABLE_KEYS`, and the literals in
      `descriptor.py` that name the four player sections (R14, around lines 550–566).
      The player uniqueness assert is FR-013 applied to players, not a new rule. In
      this same commit, migrate every current-corpus `settings` document (not
      `pre-008/`, not `pre-013/`) and any golden this schema invalidates, so each
      validates against the reshaped schema (FR-055)
- [x] T043 [US1] Derived legacy keys on the decoded node configuration:
      `node_conf["videoplayer"]` and its two siblings project out of `players` by class.
      `node_conf["audiomixer"]` is the element itself, not a projection. No class tuple
- [x] T044 [US2] Add the axis C transformation to `src/cuemsutils/xml/reshape_devices.py`
      (data-model §6): `<videoplayer>` / `<audioplayer>` / `<dmxplayer>` become
      `<players><player class="…">`; `<audiomixer>` is left in place. Extend
      `tests/integration/test_reshape_roundtrip.py` with an old-shape settings document
      from `tests/data/corpus/pre-013/`. The tool's "not applicable" classification must
      now treat old-shape settings as old, not as skipped

**Checkpoint**: settings round-trips, the engine's player spellings still resolve, and
`audiomixer` was not given a device class.

---

## Phase 7: User Story 1 continued — axis D, cues and hardware outputs

**Goal**: `<Cue class="audio">` and `<CueOutput class="audio">` replace the per-class
element names. The Python classes stay. `hardware_outputs.xsd` is the last and the
first to cut.

**Independent Test**: a script of each cue class decodes to the same Python class as
before (`isinstance`, equality, hash unchanged); a cue whose class the registry does
not name decodes to `MediaCue` / `CueOutput`; `ActionCue`, `FadeCue` and `CueList`
keep their own elements; the wire form is `{"Cue": {…, "class": "audio"}}`.

- [x] T045 [P] [US1] Failing-first contract test `tests/contract/test_cue_class_dispatch.py`
      — `AudioCue`, `VideoCue`, `DmxCue` and the three `*CueOutput` classes still import
      and still come back from a class-carrying element; equality, hashing and
      `isinstance` give the same answers; an unknown class decodes to the base model
      rather than failing (FR-050a, FR-052, SC-012). `ActionCue`, `FadeCue` and
      `CueList` are still their own elements
- [x] T046 [P] [US1] Failing-first test `tests/contract/test_cue_wire_key.py` — `to_wire()`
      emits `Cue` / `CueOutput` plus a `class` value, and nothing else about the
      projection changed (FR-052). This is the golden event's oracle; do not regenerate
      goldens to make it pass
- [x] T047 [US1] Reshape the two choices in `src/cuemsutils/xml/schemas/script.xsd` per
      [data-model.md](data-model.md) §4.1. `CueListContentsType` becomes `CueList`,
      `Cue` (alternatives `audio`/`video`/`dmx`, fallback the base media cue), `ActionCue`,
      `FadeCue`. `OutputsType` becomes repeated `CueOutput` with the same three
      alternatives. No new container — both choices are already repeated-only (R2).
      The registry keeps binding the same XSD types; dispatch selects the model
      (FR-050a). Same commit: `CURRENT_SCHEMA_HASHES` for `script`, and the old-shape
      diagnosis naming `<AudioCue>/<VideoCue>/<DmxCue>` and the three cue-output
      elements. If `CuemsScript.load` does not call `read_document_versioned`, raise
      the same message from `src/cuemsutils/cues/CuemsScript.py`. Assert it on a
      `pre-013` script, on the message text — this is the half that used to sit in T021
- [x] T066 [US1] In the same commit as T047: the script example generator in
      `src/cuemsutils/xml/descriptor.py`. `_assert_every_choice_member_has_a_builder`
      keys builders by element name (`AudioCue`, `VideoCue`, `DmxCue` around line 410)
      and raises when a choice member has no builder. After T047 that member is `Cue`.
      Build `Cue` by class (`audio` / `video` / `dmx` still construct `AudioCue` /
      `VideoCue` / `DmxCue`); leave `ActionCue` and `FadeCue` as they are. A generated
      example must validate against the reshaped `script.xsd`
- [x] T048 [US1] Reshape `src/cuemsutils/xml/schemas/hardware_outputs.xsd` per
      data-model §4.2 and FR-053: container `output_groups`, repeated child `outputs`
      with `class`, replacing `video_outputs` and `audio_outputs`. The container and
      the child do not share a name. Same commit: its hash pin and its old-shape
      diagnosis. **This task is the first to drop** if the feature must shrink — feature
      014 replaces the schema outright, and the spec records it as the cheapest item.
      Dropping it leaves a per-class declaration standing; record the SC-003 exception
      in the migration guide rather than pretending the criterion holds
- [x] T049 [US2] Add the axis D transformations to `src/cuemsutils/xml/reshape_devices.py`
      (data-model §6), including compound documents where a cue output sits inside a cue.
      `ActionCue`, `FadeCue` and `CueList` are not rewritten. Extend the round-trip test
      with a `pre-013` script found under a name other than `script.xml`. Element order:
      the new element occupies the position of the first old sibling, so `xs:sequence`
      stays valid without reordering anything else
- [x] T050 [US1] Migrate every corpus or golden file the reshape invalidates, schemas
      as the source of truth (FR-054, FR-055, SC-004). Regenerate goldens from the
      schema-derived writer, as a named event, and update `tests/golden/MANIFEST.sha256`
      for exactly the paths that changed. **Do not regenerate
      `tests/golden/outcomes.json`.** Name these files in the commit, do not sweep them:
      `tests/data/corpus/cuems-utils/fade_showcase.xml`,
      `tests/data/corpus/cuems-utils/unicode_showcase.xml`, every other current-shape
      script, every current-shape `project_mappings` and `settings` document not already
      migrated in T024 and T042, and the corpus `hardware_outputs` documents. Each
      migrated file must validate against its reshaped schema. `pre-013/` stays
      old-shape. `pre-008/` is not touched. Corpus documents are not the canonical form
      of a document until the xml-refactoring is settled

**Checkpoint**: all four axes are new-shape, the tool migrates each, and a cue is still
an `AudioCue` when its class is `audio`.

---

## Phase 8: User Story 4 — the migration guide (Priority: P4)

**Goal**: a maintainer of each consumer repository finds their own files, their own
lines, and one of the three fault classes. Nobody infers the contract from a schema diff.

**Independent Test**: every site in M1–M13 appears with its path, its line at a named
commit, the before shape, the after shape, and a classification of *raises*, *keeps
resolving and becomes wrong*, or *keeps resolving correctly*. Line numbers are checked
against the sibling trees, not transcribed from this spec.

- [ ] T051 [US4] Write `specs/013-device-class-reshape/migration-guide.md`. Required
      sections, each a measured site and not a paraphrase:
      - `cuems-engine` — `NodeEngine.py:456`, `:457`, `:566` (M2; `:566` unguarded),
        plus `:508` and `:598` (M13, `node_mappings`), plus the six `node_conf` player
        reads (M8a). All of these **keep resolving correctly**
      - `cuems-common` — three readers, three classifications (R7, M8a, M10):
        `cuems-extract-video-latency:39` keeps resolving and **becomes wrong** (empty
        `OUTPUT_LATENCY_FLAG`, exit 0, the configured latency discarded);
        `cuems-generate-display-conf` becomes wrong; `cuems-display-setup` raises via
        `sys.exit`. New paths:
        `.//players/player[@class='video']/output_latency_ms` and
        `.//devices/device[@class='video']/outputs/output`. State that a node whose
        `cuems-common` is not re-packaged loses the latency setting with no error, and
        that the port is a dependency of the coordinated tag, not of this branch
      - `cuems-editor` — the keyed sites research R8 measured, including
        `CuemsWsServer.py:439` and the pass-through, and the statement that this site
        is **not** among flow 02's fourteen deprecated-surface call sites (FR-033).
        State the two edge cases the spec already names: a half-migrated library
        produces two shapes in one merge payload, and a load-and-save tool such as
        `repair_durations.py` now fails on an un-migrated document instead of silently
        upgrading it. Both are consequences of there being no conversion on read
      - `cuems-frontend` — the structural mappings interface and every cue-type site
        research R9 measured, in both `sequence.component.ts` files, with the wire
        contract `{"Cue": {…, "class": "audio"}}` written out (FR-032). Flow 05 writes
        its characterization tests once, against this section
- [ ] T052 [US4] Rollback section (FR-028, scenario 8). The version marker does not
      move, so an older `cuems-utils` gets a raw schema error on a new-shape document,
      not `DocumentTooNewError`. State the point after which the backup stops being a
      usable rollback — the shape of feature 012's guide §9b, answered for a reshape
- [ ] T053 [P] [US4] A test `tests/contract/test_migration_guide_names_sites.py` that
      fails if a site named in M1–M13 is absent from the guide, and that records the
      sibling commit each line number was checked against. Line numbers drift; the
      commit pin is what makes the check repeatable

**Checkpoint**: the guide is the document a consumer maintainer can port from without
opening this repository's schemas.

---

## Phase 9: User Story 5 — pins move with the schemas (Priority: P5)

**Goal**: every schema commit on this branch already carried its hash (T023, T042, T047,
T048). This phase checks that claim instead of repeating the edits, and proves the
feature took no version step.

**Independent Test**: `test_schema_scope.py` and `test_schema_name_overlap.py` pass at
the tip, `KNOWN_DIVERGENT_DECLARATIONS` is empty, and `test_no_version_bump.py` passes.

- [ ] T054 [US5] Check out each commit that edits a schema and run
      `tests/contract/test_schema_scope.py` and `tests/contract/test_schema_name_overlap.py`
      there, not only at the tip (SC-009). Record each commit and its result in
      `baseline.md`. A failure means the hash or the overlap allowlist did not move in
      that commit. Reading the diff is not the check. Fix a hash that landed later by
      rewriting history only if that commit has not been published; otherwise add a
      corrective commit and say so
- [ ] T055 [P] [US5] Confirm `KNOWN_DIVERGENT_DECLARATIONS` in
      `tests/contract/test_schema_name_overlap.py` is still empty, and that any type this
      feature declares in more than one schema is in `KNOWN_IDENTICAL_DUPLICATES` with
      the schemas named (scenarios 2 and 3)
- [ ] T056 [P] [US5] Confirm `tests/contract/test_version_marker.py`'s `EXPECTED_VERSIONS`
      and `DELIBERATE_IDENTITY_STEPS` are unmodified against the branch point, and that
      `tests/packaging/test_no_version_bump.py` still pins `0.1.0rc16` (FR-020, FR-034,
      SC-006, SC-010)

**Checkpoint**: the ratchet history is clean and no version moved.

---

## Phase 10: Publishing — FR-035 and FR-036

**Purpose**: the two upstream findings. No dependency on the axes; this phase may start
as soon as Phase 1 is done.

**Independent Test**: a test module that does not mention `cuemsutils.xml` obtains the
adoption partition, and each of the four configuration schemas validates through
`from cuemsutils.tools import validate_config_document` without constructing a
`ConfigManager`.

### Tests first

- [ ] T058 [P] Failing-first test `tests/contract/test_partition_public.py` — imports
      `partition_by_adoption` from `cuemsutils.tools.NodeList` and **calls** it
      (SC-014). An unused import of the name passes without proving the public
      function works. The map is shaped like `ConfigManager.network_map`:
      `node_list` entries are `{"node": <node>}`. Assert the adopted and
      unadopted results are bare node objects and that the input map is
      unchanged. Both results are tuples, an empty side is `()`, and `"node"
      not in` each element. Do not import `cuemsutils.xml`. Do not import
      `tests/contract/test_adoption_selection.py`. Copy those assertions into
      this file. Do not call them
- [ ] T069 [P] Failing-first test `tests/contract/test_validate_advice_per_schema.py`
      — the deprecation message names the right target for all six schemas, on the
      message text (FR-036, first half, SC-015). A configuration document is not sent
      at `CuemsScript.validate`
- [ ] T070 [P] Failing-first test `tests/contract/test_validate_config_document.py`
      — imports `validate_config_document` from `cuemsutils.tools`, not from
      `cuemsutils.tools.config_validate` (FR-036, SC-015). For each of the four
      configuration schemas: a valid document, an invalid one that names the field,
      and the assertion that no `ConfigManager` was constructed. The test's source
      does not import `cuemsutils.xml`. Assert also that `tools/__init__.py` has no
      top-level import of `config_validate` or `cuemsutils.xml` — the façade re-export
      is lazy, so `import cuemsutils.tools.CTimecode` does not pull the schema stack

### Implementation

- [ ] T057 [P] Publish `partition_by_adoption` from `src/cuemsutils/tools/NodeList.py`.
      The body stays `NetworkMap.partition_by_adoption` in `xml/settings.py`:
      same function, same signature, same behaviour (FR-035). Do not import
      `xml.settings` at module scope, and do not place the binding next to the
      `node` import at `NodeList.py:22`. That import is `from ..config.network_map
      import node` and does not load `xml.settings`. `from ..xml.settings import
      NetworkMap` loads `mapper`, which loads `adapters`, and `adapters`
      calls `_register_enums()` at import time. That function does
      `from ..tools.NodeList import NodeRole` while `NodeList` is still
      initializing. Placed before the `NodeRole` class statement, it raises
      `ImportError` on a partially initialized module. After `NodeRole` and
      `NodeIndex` are defined, publish the name with a module `__getattr__`
      that imports `NetworkMap` on first access and returns
      `NetworkMap.partition_by_adoption` itself, not a wrapper. Add the name
      to `__all__`. `import cuemsutils.tools.NodeList` must not load
      `xml.settings`. `from cuemsutils.tools.NodeList import partition_by_adoption`
      must return that same function. Leave `get_nodes_by_adoption` where it
      is. T058 fails before this lands and passes after. The golden signature
      for this name lands in this same commit (T061)
- [ ] T059 Per-schema deprecation advice (FR-036, first half). The test is T069; this
      task makes it pass. The single replacement string in
      `src/cuemsutils/xml/__init__.py` (`_READER_WRITER_METHODS`,
      `validate_object` → `CuemsScript.validate`) sends every schema at the script
      validator, which cannot validate a configuration document. Change the advice so a
      `settings`, `network_map`, `project_mappings` or `project_settings` document is
      sent at `validate_config_document`, and a script at `CuemsScript.validate`. The
      alias is one class for every schema, so the schema-specific text has to come from
      `schema_name` at the call, not from a second alias
- [ ] T060 Public validator `validate_config_document(path)` in
      `src/cuemsutils/tools/config_validate.py`, returning the existing `LoadReport`
      (FR-036, second half, [contracts/library-surface.md](contracts/library-surface.md)
      §4.2). The test is T070; this task makes it pass. It validates without
      constructing a `ConfigManager` and without requiring `/etc/cuems`. Re-export the
      name lazily from `src/cuemsutils/tools/__init__.py` via `__getattr__`, and add it
      to `__all__`. No top-level import of `config_validate`: the package body stays
      eager only for `SENTINEL` and `coerce_identity`, which do not pull schemas.
      Update that module's docstring, which currently says the body stays otherwise
      empty. Consumers write `from cuemsutils.tools import validate_config_document`.
      They do not name `config_validate`
- [ ] T061 Extend the public-api snapshot and update
      `tests/golden/api/public_api.json` (SC-016). `NodeList` is not in
      `PUBLIC_CLASSES`. `_members()` only records methods of classes: a function
      becomes `{"kind": "function", "bases": []}` with no signature, so growing
      the snapshot by the name alone does not pin `(network_map)`. Record
      `partition_by_adoption` with the signature `inspect.signature` returns,
      `(network_map) -> tuple[tuple, tuple]`. That golden change is this name's
      change, and it lands in the same commit as the re-export (T057).
      `validate_config_document` stays the separate golden event it already is.
      The script name already moved in T035

**Checkpoint**: UR-1 and UR-5 are closed by publishing, and the golden names exactly the
symbols this feature added.

---

## Phase 11: Polish

- [ ] T062 Measure SC-PERF-001, SC-PERF-002 and SC-PERF-003 against the numbers T004
      wrote into `baseline.md`, as ranges. The tool's throughput is measured on
      `remint_200` and compared with the calibration budget T004 recorded. Do not
      choose a budget in this task. An exceedance is recorded as exceeded, with the
      mechanism named — never restated as passing. Timing tests go in
      `tests/integration/`; do not create `tests/performance/`
- [ ] T063 [P] Run `make_defaults` and confirm the three generated documents validate
      against the reshaped schemas (R14). This is the check `debian/rules` will run at
      package build
- [ ] T064 [P] Confirm the suite introduces no new lint finding and no new deprecation
      warning beyond the 215 the baseline run reports (SC-QUALITY-001)
- [ ] T068 Run `cuems-engine`'s suite against this branch and against the branch point,
      and record both results in
      `specs/013-device-class-reshape/sibling-repository-updates.md` (SC-008, SC-013).
      The run must include a node carrying no video device, so `NodeEngine.py:566`'s
      unguarded subscript is exercised, and the six `node_conf` player reads must
      resolve to the same values in both arms. This is the instrument feature 012
      measured to be stronger than a call-site census. Do not infer the result
- [ ] T065 Write the feature's entry in `CLAUDE.md` "Recent Changes" in the commit that
      marks the feature landed, on the pattern of features 011 and 012: what reshaped,
      the container-element reason, the new entry point, the two published names, and
      that nothing ships until the coordinated tag (D27). Do not hand-edit
      `.cursor/rules/specify-rules.mdc`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T005 blocks every schema edit. T001 and T002
  block T012. T003 blocks T022. T004 blocks T062
- **Foundational (Phase 2)**: depends on Phase 1. Blocks every schema edit
- **US1 axis A (Phase 3)**: depends on Phase 2. The same-commit cluster is T020–T024
- **US2 (Phase 4)**: depends on Phase 3 — the tool's axis A transformation is only
  testable once the schema has narrowed and the diagnosis exists. Tests T028–T033 can
  be written against Phase 2, failing
- **US3 (Phase 5)**: depends on T026. T027 already did the T2 retarget because it could
  not wait
- **Axis C (Phase 6)**: depends on Phases 3 and 4. Independent of US3's deletion, but
  sequenced after it so the legacy-key work follows one pattern
- **Axis D (Phase 7)**: depends on Phase 6. T066 is the same commit as T047.
  Independently cuttable — dropping T048 (hardware outputs) is the cheap cut;
  dropping T047, T066 and T050 leaves SC-001 unmet and must be recorded as a scope
  reduction, not done silently
- **US4 (Phase 8)**: depends on Phases 6 and 7, because the guide states shapes that
  those phases can still change. T006 confirms the widened requirements are already in
  the spec, so the guide is written against that text
- **US5 (Phase 9)**: the pins themselves land inside Phases 3, 6 and 7. This phase is
  the audit
- **Publishing (Phase 10)**: depends only on Phase 1. May run in parallel with
  Phases 3–7. Tests T058, T069 and T070 are written before T057, T059 and T060
- **Polish (Phase 11)**: depends on everything that is in scope. T068 needs Phases 3
  through 7, because SC-008's unguarded read and SC-013's player reads are both in
  that run

### User Story Dependencies

- **US1 (P1)**: after Foundational. Delivers the mappings half on its own; axes C and D
  extend it and are not required for the story's own independent test
- **US2 (P2)**: after US1's schema commit. The diagnosis (T021) is US1's; the repair
  (T034) is US2's. They are split across phases and joined by the commit rule
- **US3 (P3)**: after T026. Not required for US2
- **US4 (P4)**: after the axes it documents
- **US5 (P5)**: continuous, audited last

### Parallel Opportunities

- Phase 1: T002, T003, T004, T006 in parallel; T001 before T012; T005 before T020
- Phase 2: T007–T010 in parallel, then T011–T016
- Phase 3 tests T017–T019 and T067 in parallel
- Phase 4 tests T028–T033 in parallel
- Phase 10 in parallel with Phases 3–7
- Phase 5 tests T037–T038 in parallel with each other, after T026

---

## Parallel Example: User Story 1

```bash
# Tests, together, before the schema:
# T017 tests/contract/test_device_class_open.py
# T018 tests/contract/test_class_conditional_fields.py
# T019 tests/contract/test_device_class_uniqueness.py
# T067 tests/contract/test_special_field_class_cost.py

# Then one commit:
# T020 project_mappings.xsd
# T021 the old-shape diagnosis
# T022 the uniqueness asserts
# T023 CURRENT_SCHEMA_HASHES
# T024 seeds and make_defaults
```

---

## Implementation Strategy

### MVP First (User Story 1, mappings only)

1. Phase 1 and Phase 2
2. Phase 3 — stop here to validate the independent test
3. An old mappings document is diagnosed and not yet migrated. That is acceptable for
   the MVP demonstration and not acceptable to merge: Phase 4 is what makes the schema
   edit shippable

### Incremental Delivery

1. Setup + foundation → dispatch exists, no document changed
2. US1 axis A + US2 → mappings migrate, lighting works (the mergeable MVP)
3. US3 → the class list is gone
4. Axis C → settings migrate; the engine's player reads still resolve
5. Axis D → scripts migrate; the wire key is the frontend's contract
6. Guide, pin audit, publishing, measurements

### Cut order, if the feature must shrink

1. T048 — `hardware_outputs.xsd`. Record the SC-003 exception
2. Phase 7 entire — axis D. A new class still costs the script edit; SC-001 is then
   unmet and the guide must say so. Do not cut Phase 7 and leave the guide claiming it
3. Nothing earlier. Axis A without the tool, or the tool without the diagnosis, is the
   failure mode the plan's commit rule exists to prevent

---

## Notes

- [P] tasks = different files, no incomplete-task dependency
- The same-commit clusters are requirements, not a suggestion: T020–T024, and each later
  schema edit with its hash pin and its diagnosis line
- Commit after each task or cluster. Commits are GPG-signed; on `gpg failed to sign`,
  retry — never `--no-gpg-sign`
- Do not move the library version off `0.1.0rc16`
- Do not ship from this branch alone (D27)
