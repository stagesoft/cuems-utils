---
description: "Task list for FadeCue class implementation"
---

# Tasks: FadeCue Class

**Input**: Design documents from `/specs/003-fade-cue/`  
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓

**Tests**: Test tasks are REQUIRED by constitution (fail-before-pass gate).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in any order (no dependency on sibling tasks in the same group)
- **[Story]**: Which user story this task belongs to (US1 / US2 / US3)

---

## Phase 1: Setup

**Purpose**: Baseline health check before touching the codebase.

- [X] T001 Confirm `ruff check .` and `pytest` pass cleanly on the current codebase (zero new warnings / failures before any changes)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared artefacts needed by all user stories — the `action_target` guard in `ActionCue`, the `FadeCurveType` enum, and the two XSD primitive additions. No user story work can begin until this phase is complete.

**⚠️ CRITICAL**: Complete T002–T004 and T037–T038 before any Phase 3+ work.

- [X] T037 Write a failing test `test_action_cue_none_target_raises` in `tests/test_cue.py` that constructs `ActionCue({'action_target': None})` and also assigns `None` to `.action_target` on an existing instance, expecting `ValueError` in both cases
- [X] T038 Override `set_action_target` in `src/cuemsutils/cues/ActionCue.py`: raise `ValueError('action_target is required')` when value is `None`; otherwise delegate to `super().__setitem__('action_target', value)`. Verify existing tests in `tests/test_cue.py` and `tests/test_xml.py` still pass (all existing usages supply a valid UUID)
- [X] T002 Create `src/cuemsutils/cues/FadeCue.py` with the `FadeCurveType` enum (`linear`, `exponential`, `logarithmic`, `sigmoid`) and a `__str__` override that returns the plain `.value` string (so `XmlBuilder` serialises it correctly without a custom builder)
- [X] T003 [P] Add `<xs:enumeration value="fade_action" />` to the `ActionType` simpleType restriction in `src/cuemsutils/xml/schemas/script.xsd`
- [X] T004 [P] Add `FadeCurveType` simpleType with four enumeration values (`linear`, `exponential`, `logarithmic`, `sigmoid`) to `src/cuemsutils/xml/schemas/script.xsd` (place alongside `ActionType`)

**Checkpoint**: `ActionCue` rejects `None` `action_target`; `FadeCurveType` importable from `FadeCue.py`; XSD loads without errors; pre-existing test suite still passes.

---

## Phase 3: User Story 1 — Define a Fade-to-Level Cue (Priority: P1) 🎯 MVP

**Goal**: A fully constructed `FadeCue` object stores all four properties correctly and survives an XML round-trip (serialize → deserialize → compare).

**Independent Test**: `pytest tests/test_fade_cue.py -k "construction or round_trip"` passes after implementation; fails before.

### Tests for User Story 1 ⚠️ Write FIRST — verify they FAIL before implementation

- [X] T005 [US1] Write a failing test `test_fade_cue_default_construction` that creates `FadeCue()` with no arguments and asserts `action_type == 'fade_action'`, `curve_type == FadeCurveType.linear`, `target_value == 0`, and `duration` is a `CTimecode` in `tests/test_fade_cue.py`
- [X] T006 [P] [US1] Write a failing test `test_fade_cue_explicit_construction` that creates `FadeCue({'action_target': uuid, 'curve_type': FadeCurveType.sigmoid, 'duration': '00:00:03.500', 'target_value': 75})` and asserts each property value in `tests/test_fade_cue.py`
- [X] T007 [P] [US1] Write a failing test `test_fade_cue_xml_serialisation` that builds a CuemsScript containing a FadeCue, serialises to XML via `XmlReaderWriter`, and asserts a `<FadeCue>` element exists with child elements `curve_type`, `duration`, `target_value` in `tests/test_fade_cue.py`
- [X] T008 [P] [US1] Write a failing test `test_fade_cue_xml_round_trip` that serialises a FadeCue to XML and deserialises it back, asserting all four properties are restored to their original values in `tests/test_fade_cue.py`

### Implementation for User Story 1

- [X] T009 [US1] Implement `FadeCue.__init__` in `src/cuemsutils/cues/FadeCue.py`: define `REQ_ITEMS` (`action_target`, `action_type='fade_action'`, `curve_type=FadeCurveType.linear`, `duration=None`, `target_value=0`), call `ensure_items`, delegate to `ActionCue.__init__`
- [X] T010 [P] [US1] Implement `get_curve_type` / `set_curve_type` property in `src/cuemsutils/cues/FadeCue.py`: setter stores a `FadeCurveType` member (coerce from string if possible, else store as-is for now — validation added in US2)
- [X] T011 [P] [US1] Implement `get_duration` / `set_duration` property in `src/cuemsutils/cues/FadeCue.py`: setter calls `format_timecode(value)` from `cuemsutils.helpers` and stores the resulting `CTimecode` (zero guard added in US2)
- [X] T012 [P] [US1] Implement `get_target_value` / `set_target_value` property in `src/cuemsutils/cues/FadeCue.py`: getter/setter reading from/writing to the underlying dict (bounds guard added in US2)
- [X] T013 [US1] Implement `FadeCue.items()` in `src/cuemsutils/cues/FadeCue.py`: start from `super().items()` dict, then append own `REQ_ITEMS` keys in XSD sequence order (`action_target`, `action_type`, `curve_type`, `duration`, `target_value`) and return `.items()`
- [X] T014 [US1] Add `FadeCueType` complexType to `src/cuemsutils/xml/schemas/script.xsd` extending `ActionCueType` with a sequence of `curve_type` (`FadeCurveType`), `duration` (`CTimecodeType`), `target_value` (`PercentType`) — place after `ActionCueType`
- [X] T015 [US1] Add `<xs:element name="FadeCue" type="cms:FadeCueType" />` inside the `<xs:choice>` of `CueListContentsType` in `src/cuemsutils/xml/schemas/script.xsd`
- [X] T016 [US1] Export `FadeCue` from `src/cuemsutils/cues/__init__.py` (add import line and entry to `__all__`)

**Checkpoint**: `pytest tests/test_fade_cue.py -k "construction or round_trip"` passes. XML round-trip is verified.

---

## Phase 4: User Story 2 — Validate Fade Parameters at Definition Time (Priority: P2)

**Goal**: Assigning any invalid value — including a `None` `action_target` — raises a descriptive `ValueError` immediately, before the object is used by the engine.

**Independent Test**: `pytest tests/test_fade_cue.py -k "invalid or boundary"` passes after implementation; fails before.

### Tests for User Story 2 ⚠️ Write FIRST — verify they FAIL before implementation

- [X] T017 [US2] Write a failing test `test_invalid_action_type_raises` that calls `FadeCue({'action_type': 'play'})` and expects `ValueError` in `tests/test_fade_cue.py`
- [X] T018 [P] [US2] Write a failing test `test_invalid_curve_type_raises` that assigns an unknown string to `fade_cue.curve_type` and expects `ValueError` in `tests/test_fade_cue.py`
- [X] T019 [P] [US2] Write a failing test `test_zero_duration_raises` that assigns `'00:00:00.000'` to `fade_cue.duration` and expects `ValueError` in `tests/test_fade_cue.py`
- [X] T020 [P] [US2] Write failing tests `test_negative_target_value_raises` and `test_over_100_target_value_raises` for out-of-range integers in `tests/test_fade_cue.py`
- [X] T021 [P] [US2] Write passing boundary tests `test_boundary_target_value_zero_accepted` and `test_boundary_target_value_100_accepted` asserting 0 and 100 are valid in `tests/test_fade_cue.py`
- [X] T034 [P] [US2] Write a test `test_fade_cue_inherits_none_target_guard` in `tests/test_fade_cue.py` confirming that `FadeCue({'action_target': None})` raises `ValueError` — verifying the guard defined in `ActionCue` (T038) propagates correctly through the inheritance chain. No FadeCue-specific implementation required.

### Implementation for User Story 2

- [X] T022 [US2] Override `set_action_type` in `src/cuemsutils/cues/FadeCue.py`: raise `ValueError` for any value other than `'fade_action'`; write `'fade_action'` only when the correct value is supplied (the `REQ_ITEMS` default ensures the no-args construction path is always valid)
- [X] T023 [P] [US2] Add enum guard to `set_curve_type` in `src/cuemsutils/cues/FadeCue.py`: attempt `FadeCurveType(value)` coercion; raise `ValueError` with descriptive message listing valid values if coercion fails
- [X] T024 [P] [US2] Add positive/non-zero guard to `set_duration` in `src/cuemsutils/cues/FadeCue.py`: after `format_timecode()`, check zero using `float(result) <= 0` (`CTimecode` supports `__float__` via the underlying `timecode` package — confirmed by `FadeCalculator` usage); raise `ValueError('duration must be positive and non-zero')`
- [X] T025 [P] [US2] Add bounds check to `set_target_value` in `src/cuemsutils/cues/FadeCue.py`: if `not (0 <= int(value) <= 100)` raise `ValueError('target_value must be between 0 and 100')`

**Checkpoint**: `pytest tests/test_fade_cue.py -k "invalid or boundary"` passes. All four FadeCue-specific validators (action_type, curve_type, duration, target_value) plus the inherited action_target guard all reject bad input with descriptive errors.

---

## Phase 5: User Story 3 — Include FadeCue in Sample Script (Priority: P3)

**Goal**: `create_script()` returns a valid script containing at least one `FadeCue` element, and the full script passes schema validation with no regressions.

**Independent Test**: `pytest tests/test_fade_cue.py -k "create_script"` passes after implementation; fails before.

### Tests for User Story 3 ⚠️ Write FIRST — verify they FAIL before implementation

- [X] T026 [US3] Write a failing test `test_create_script_contains_fade_cue` that calls `create_script()`, serialises the result to XML, and asserts a `<FadeCue>` element is present in `tests/test_fade_cue.py`
- [X] T027 [P] [US3] Write a failing test `test_create_script_validates_with_fade_cue` that calls `validate_template(create_script())` and asserts no `XMLSchemaValidationError` is raised in `tests/test_fade_cue.py`

### Implementation for User Story 3

- [X] T028 [US3] Add `FadeCue` and `FadeCurveType` to the import line at the top of `src/cuemsutils/create_script.py`
- [X] T029 [US3] Instantiate a `FadeCue` with `action_target=target_uuid`, `curve_type=FadeCurveType.linear`, `duration='00:00:02.000'`, `target_value=0`, `ui_properties={'warning': None}` and append it to `custom_cue_list` in `src/cuemsutils/create_script.py`
- [X] T030 [US3] Update the index-based `id` assignments (in both the assignment and the cleanup `finally` block) in `src/cuemsutils/create_script.py` to cover index 4 (the new FadeCue)

**Checkpoint**: `pytest tests/test_fade_cue.py` passes fully. `create_script()` produces a schema-valid XML containing `<FadeCue>`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final quality gate across all modified files.

- [X] T031 [P] Run `ruff check .` from `src/` and fix any warnings introduced in `FadeCue.py`, `create_script.py`, `__init__.py`, `script.xsd`
- [X] T032 Run the full `pytest` suite and confirm all pre-existing tests still pass (zero regressions)
- [X] T033 [P] Review `FadeCue.py` docstrings — ensure `__init__`, each getter/setter, and `items()` have docstrings consistent with the style used in `ActionCue.py`
- [X] T036 [P] Add a timing assertion test `test_fade_cue_construction_performance` in `tests/test_fade_cue.py` that constructs 10 000 `FadeCue` instances and asserts total wall time is under 1 second (validating FR-PERF-001: same order of magnitude as `ActionCue`, which performs only dict operations and no I/O)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — tests written first, then implementation
- **Phase 4 (US2)**: Depends on Phase 3 being complete (validation is added to the existing class)
- **Phase 5 (US3)**: Depends on Phase 3 (FadeCue must exist and export correctly) — independent of Phase 4
- **Phase 6 (Polish)**: Depends on Phases 3–5 all complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — no dependency on US2 or US3
- **US2 (P2)**: Depends on US1 (modifies setters defined in US1)
- **US3 (P3)**: Depends on US1 (needs the FadeCue class) — independent of US2

### Within Each User Story

1. Write tests first — confirm they **fail** before implementation
2. Implement class/XSD changes
3. Confirm tests **pass**
4. Advance to next story

### Parallel Opportunities

Within Phase 2: T037 (test) must precede T038 (implementation); T002, T003, T004 can then be done in any order alongside T038 (different files).  
Within Phase 3 tests: T006, T007, T008 can be done in any order (appending to same file, but independent scenarios).  
Within Phase 3 implementation: T010, T011, T012 can be done in any order (independent properties).  
Within Phase 4 tests: T018, T019, T020, T021, T034 can be done in any order.  
Within Phase 4 implementation: T022, T023, T024, T025 can be done in any order (independent setters in the same file).  
T026 and T027 can be done in any order.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `pytest tests/test_fade_cue.py -k "construction or round_trip"` passes
5. FadeCue is usable by any consumer that needs to construct and store a fade command

### Incremental Delivery

1. Phase 1 + 2 → foundation ready
2. Phase 3 (US1) → FadeCue constructable and serialisable (MVP)
3. Phase 4 (US2) → all bad inputs safely rejected
4. Phase 5 (US3) → wired into the project sample/demo script
5. Phase 6 → clean, documented, no regressions

---

## Notes

- `[P]` tasks within a group have no ordering dependency on each other; a solo developer may do them in any sequence
- Each user story produces an independently testable, committable increment
- `FadeCurveType.__str__` returning `.value` is critical — without it, `GenericCueXmlBuilder` will write `'FadeCurveType.linear'` instead of `'linear'` into XML
- The `items()` order must match the XSD element sequence exactly or schema validation will fail
- The `create_script` index-based cleanup (lines 157–162) must be kept in sync with the cue count — FadeCue adds index 4
