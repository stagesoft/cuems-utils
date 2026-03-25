---

description: "Task list for MediaCue Parametric Fades"
---

# Tasks: MediaCue Parametric Fades

**Input**: Design documents from `/specs/001-mediacue-fading-function/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Include test tasks for each user story. Tests are REQUIRED by constitution.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create test directory structure for this feature

- [ ] T001 Create test directories `tests/unit/`, `tests/integration/`, `tests/contract/` if they do not exist
- [ ] T002 [P] Verify pytest discovers tests from `tests/` by running `pytest --collect-only`

**Checkpoint**: Test infrastructure ready

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Define shared model classes that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 Implement `FadeFunctionParameter` class (fields: `parameter_name`, `parameter_value`) in `src/cuemsutils/cues/FadeProfile.py`
- [ ] T004 Implement `FadeProfile` class (fields: `type` enum `in|out`, `mode` enum `preset|parametric`, `function_id`, optional `parameters` list) in `src/cuemsutils/cues/FadeProfile.py`
- [ ] T005 Add `FADE_PROFILE_REQ_ITEMS` defaults dict for `FadeProfile` in `src/cuemsutils/cues/FadeProfile.py`

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Define Fade Behavior in a Media Cue (Priority: P1) 🎯 MVP

**Goal**: MediaCue stores zero, one, or two typed fade profiles and preserves them through save/load roundtrip

**Independent Test**: Create a MediaCue with fade profiles (preset and parametric, type `in` and `out`), serialize, deserialize, and confirm data integrity

### Tests for User Story 1 (REQUIRED) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T006 [P] [US1] Unit test: MediaCue accepts and stores a single fade profile (type `in`, mode `preset`) in `tests/unit/test_mediacue_fade_profile.py`
- [ ] T007 [P] [US1] Unit test: MediaCue accepts two fade profiles (one `in`, one `out`) in `tests/unit/test_mediacue_fade_profile.py`
- [ ] T008 [P] [US1] Unit test: MediaCue rejects duplicate fade profiles with same `type` in `tests/unit/test_mediacue_fade_profile.py`
- [ ] T009 [P] [US1] Unit test: preset mode allows empty parameters, parametric mode requires parameters in `tests/unit/test_mediacue_fade_profile.py`
- [ ] T009A [P] [US1] Unit test: retrieve correct fade profile by direction — given both `in` and `out` profiles, selecting by type returns matching profile in `tests/unit/test_mediacue_fade_profile.py`
- [ ] T009B [P] [US1] Unit test: `FadeFunctionParameter` rejects non-numeric `parameter_value` and validates `parameter_name` uniqueness within a profile in `tests/unit/test_mediacue_fade_profile.py`
- [ ] T010 [P] [US1] Integration test: MediaCue with fade profiles roundtrips through XML serialize/deserialize in `tests/integration/test_mediacue_fade_roundtrip.py`

### Implementation for User Story 1

- [ ] T011 [US1] Extend `MediaCue` with `fade_profiles` property and setter (stores list of `FadeProfile`, enforces max-one-per-type) in `src/cuemsutils/cues/MediaCue.py`
- [ ] T011A [US1] Add `MediaCue.get_fade_profile(direction)` method that returns the `FadeProfile` matching `type` or `None` in `src/cuemsutils/cues/MediaCue.py` (FR-003)
- [ ] T012 [US1] Update `MediaCue.items()` to include `fade_profiles` in serialized output in `src/cuemsutils/cues/MediaCue.py`
- [ ] T013 [US1] Update `REQ_ITEMS` in `src/cuemsutils/cues/MediaCue.py` to include optional `fade_profiles` key with `None` default
- [ ] T014 [US1] Add `fade_profile` parsing support in `src/cuemsutils/xml/Parsers.py` (handle nested `fade_profile` elements under MediaCue)
- [ ] T015 [US1] Ensure `XmlBuilder` serializes `fade_profiles` list as repeatable `fade_profile` XML elements in `src/cuemsutils/xml/XmlBuilder.py`
- [ ] T016 [US1] Verify `AudioCue` and `VideoCue` inherit fade-profile support without changes in `src/cuemsutils/cues/AudioCue.py` and `src/cuemsutils/cues/VideoCue.py`

**Checkpoint**: User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Validate Fade Data Through XML Schema (Priority: P2)

**Goal**: XML schema enforces required fade-profile structure and rejects invalid payloads

**Independent Test**: Validate XML samples with correct fade data (pass) and missing/invalid fields (fail) against updated schema

### Tests for User Story 2 (REQUIRED) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T017 [P] [US2] Contract test: valid fade_profile with type `in`, mode `preset` passes schema validation in `tests/contract/test_mediacue_fade_schema_contract.py`
- [ ] T018 [P] [US2] Contract test: valid fade_profile with type `out`, mode `parametric` and parameters passes schema validation in `tests/contract/test_mediacue_fade_schema_contract.py`
- [ ] T019 [P] [US2] Contract test: fade_profile missing required `type` field fails schema validation in `tests/contract/test_mediacue_fade_schema_contract.py`
- [ ] T020 [P] [US2] Contract test: fade_profile with invalid `mode` value fails schema validation in `tests/contract/test_mediacue_fade_schema_contract.py`
- [ ] T021 [P] [US2] Contract test: fade_profile with empty `function_id` fails schema validation in `tests/contract/test_mediacue_fade_schema_contract.py`

### Implementation for User Story 2

- [ ] T022 [US2] Add `FadeTypeType` simple type (enum `in`, `out`) in `src/cuemsutils/xml/schemas/script.xsd`
- [ ] T023 [US2] Add `FadeModeType` simple type (enum `preset`, `parametric`) in `src/cuemsutils/xml/schemas/script.xsd`
- [ ] T024 [US2] Add `FadeParameterType` complex type (`parameter_name` string, `parameter_value` float) in `src/cuemsutils/xml/schemas/script.xsd`
- [ ] T025 [US2] Add `FadeParametersType` complex type (sequence of `parameter` elements of `FadeParameterType`) in `src/cuemsutils/xml/schemas/script.xsd`
- [ ] T026 [US2] Add `FadeProfileType` complex type (`type`, `mode`, `function_id`, optional `parameters`) in `src/cuemsutils/xml/schemas/script.xsd`
- [ ] T027 [US2] Extend `MediaCueType` with optional repeatable `fade_profile` element of `FadeProfileType` (`minOccurs="0" maxOccurs="2"`) in `src/cuemsutils/xml/schemas/script.xsd`

**Checkpoint**: User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Preserve Backward Compatibility (Priority: P3)

**Goal**: Legacy scripts without fade-profile data remain valid and executable

**Independent Test**: Load a pre-feature script, validate against updated schema, run media cues, confirm unchanged behavior

### Tests for User Story 3 (REQUIRED) ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T028 [P] [US3] Regression test: legacy MediaCue without fade_profiles loads without error in `tests/integration/test_mediacue_fade_roundtrip.py`
- [ ] T029 [P] [US3] Regression test: legacy script XML validates against updated schema in `tests/contract/test_mediacue_fade_schema_contract.py`
- [ ] T030 [P] [US3] Regression test: `create_script()` template validates against updated schema in `tests/integration/test_mediacue_fade_roundtrip.py`

### Implementation for User Story 3

- [ ] T031 [US3] Verify `MediaCue.__init__` defaults `fade_profiles` to `None` when not provided in `src/cuemsutils/cues/MediaCue.py`
- [ ] T032 [US3] Verify parser gracefully handles missing `fade_profile` elements in `src/cuemsutils/xml/Parsers.py`
- [ ] T033 [US3] Verify `create_script()` template still validates after schema changes in `src/cuemsutils/create_script.py`

**Checkpoint**: All user stories should now be independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T034 [P] Performance benchmark: measure parse/serialize overhead with and without fade profiles against <=5% budget
- [ ] T035 UX consistency pass: verify XML element/attribute naming follows existing conventions in `src/cuemsutils/xml/schemas/script.xsd`
- [ ] T036 [P] Run full test suite (`pytest`) and confirm no regressions
- [ ] T037 Run quickstart.md validation flow end-to-end
- [ ] T038 Code cleanup and lint check on all modified files

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - XSD types are self-contained; integration with US1 for full roundtrip but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Validates existing behavior against new code; best done after US1+US2 but independently testable

### Within Each User Story

- Tests MUST be written and FAIL before implementation
- Model classes before property accessors
- Property accessors before parser/serializer updates
- Core implementation before integration verification
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks (T003-T005) are sequential (same file: `FadeProfile.py`)
- Once Foundational phase completes, all user stories can start in parallel
- All tests for a user story marked [P] can run in parallel
- T006-T010 (US1 tests) can all be written in parallel
- T017-T021 (US2 tests) can all be written in parallel
- T028-T030 (US3 tests) can all be written in parallel

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test: MediaCue accepts single fade profile in tests/unit/test_mediacue_fade_profile.py"
Task: "Unit test: MediaCue accepts two fade profiles in tests/unit/test_mediacue_fade_profile.py"
Task: "Integration test: roundtrip in tests/integration/test_mediacue_fade_roundtrip.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1
   - Developer B: User Story 2
   - Developer C: User Story 3
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
