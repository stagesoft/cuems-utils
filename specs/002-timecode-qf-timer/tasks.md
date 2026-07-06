# Tasks: Timecode Quarter-Frame Timer

**Input**: Design documents from `/specs/002-timecode-qf-timer/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/ ✅

**Tests**: Required by constitution (Principle II). All tests MUST be written and confirmed failing before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Exact file paths included in every description

## Path Conventions

Single-project layout: `src/cuemsutils/tools/`, `tests/unit/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create file skeletons so all story phases can proceed without conflicts.

- [X] T001 Create stub class `CTimecodeTimer` with imports and docstring in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T002 [P] Create test file with imports and shared fixture `make_tc` (returns a 25fps CTimecode at `00:00:00:00`) in `tests/unit/test_ctimecode_timer.py`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Implement `__init__`, state machine, QF interval, and start/stop stubs. These block all user stories because no callback dispatch can be tested without a working timer shell.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Implement `CTimecodeTimer.__init__(timecode, params=None)` — validate `timecode`, freeze `params` as tuple-of-tuples (treating `[]` as `None`), compute and cache `_qf_interval = 1.0 / (4.0 * float(timecode.framerate))`, set `_state = 'idle'` in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T004 Implement state machine constants `IDLE / RUNNING / STOPPED / EXHAUSTED` (module-level or `enum.Enum`) in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T005 [P] Write failing unit tests for `__init__` validation: `timecode=None` raises `ValueError`; `params=[]` is treated as bare-signal; QF interval is computed correctly for 24/25/30 fps in `tests/unit/test_ctimecode_timer.py`
- [X] T006 [P] Write failing tests for `start()`/`stop()` state transitions: IDLE→RUNNING on `start()`; RUNNING→STOPPED on `stop()`; STOPPED→RUNNING on second `start()`; no-op when already RUNNING — in `tests/unit/test_ctimecode_timer.py`
- [X] T007 [P] Write failing test: `_run_loop` exits cleanly within 1× QF interval after stop is signalled (mock `time.sleep`; assert thread is not alive after `stop()`) — in `tests/unit/test_ctimecode_timer.py`
- [X] T008 Implement `_run_loop()` private method — daemon-thread loop that sleeps `_qf_interval` seconds per iteration, reads `_timecode` position each tick, and checks stop-flag (`threading.Event`) to exit in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T009 Implement `start()` — transitions `IDLE→RUNNING` and `STOPPED→RUNNING`, spawns daemon thread running `_run_loop`; no-op if already `RUNNING`; no-op + `Logger.warning("CTimecodeTimer: cannot restart exhausted timer — create a new instance")` if `EXHAUSTED` — import via `from cuemsutils.log import Logger` in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T010 Implement `stop()` — sets `threading.Event` stop-flag checked by `_run_loop` so loop exits within one QF interval, transitions `RUNNING→STOPPED`, joins thread; no-op on any other state in `src/cuemsutils/tools/CTimecodeTimer.py`

**Checkpoint**: Class instantiates, `start()`/`stop()` transition state correctly, thread starts and exits cleanly (all Phase 2 tests pass).

---

## Phase 3: User Story 1 — Attach Timer and Receive Callbacks (Priority: P1) 🎯 MVP

**Goal**: Timer fires the registered callback at every quarter-frame boundary. In parameterised mode each tuple is unpacked as the callback arguments; in bare-signal mode the callback is called with no args. Timer stops automatically when the tuple list is exhausted.

**Independent Test**: Instantiate with a 4-item tuple list + mock callback, call `start()`, advance time by mocking `time.sleep`/`time.time`, assert callback fired exactly 4 times with correct args and that the timer is in `EXHAUSTED` state.

### Tests for User Story 1 (write first — MUST FAIL before implementation) ⚠️

- [X] T011 [US1] Write failing test: parameterised mode — given `params=[(0,),(1,),(2,),(3,)]`, after 4 QF boundaries, `callback` is called with `(0,)` `(1,)` `(2,)` `(3,)` in order in `tests/unit/test_ctimecode_timer.py`
- [X] T012 [P] [US1] Write failing test: bare-signal mode — `callback` is called with no arguments at each QF boundary in `tests/unit/test_ctimecode_timer.py`
- [X] T013 [P] [US1] Write failing test: no callback registered — timer runs 4+ QF cycles without raising in `tests/unit/test_ctimecode_timer.py`
- [X] T014 [P] [US1] Write failing test: timer transitions to `EXHAUSTED` after last tuple is consumed and emits no further callbacks in `tests/unit/test_ctimecode_timer.py`

### Implementation for User Story 1

- [X] T015 [US1] Implement callback dispatch in `_run_loop`: if `_callback` is set and `_params` present, call `_callback(*_params[_index])`; if no `_params`, call `_callback()`; advance `_index` after each call in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T016 [US1] Implement exhaustion check in `_run_loop`: when `_index >= len(_params)`, transition to `EXHAUSTED` and exit loop in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T017 [US1] Write timing smoke test: at 25 fps, across 4 consecutive QF callbacks, no single interval deviates by more than ±1 ms from the expected 10 ms QF duration — use mocked `time.time` (fast, no real sleep) — in `tests/unit/test_ctimecode_timer.py`
- [X] T018 [US1] Verify all Phase 3 tests now pass: `hatch run test:run tests/unit/test_ctimecode_timer.py -k "us1 or story1 or param or signal or exhaust"`

**Checkpoint**: User Story 1 is fully functional. `CTimecodeTimer` with a tuple list fires callbacks and stops automatically.

---

## Phase 4: User Story 2 — Start and Stop the Timer (Priority: P2)

**Goal**: Explicit lifecycle control — `start()` begins emission, `stop()` halts it cleanly. A stopped timer can restart; an exhausted timer cannot.

**Independent Test**: Instantiate without a tuple list, register callback, call `start()`, let several QF cycles fire, call `stop()`, advance time further, assert no more callbacks fired.

### Tests for User Story 2 (write first — MUST FAIL before implementation) ⚠️

- [X] T019 [US2] Write failing test: `stop()` halts callbacks — after `stop()` no further invocations occur even if time continues advancing in `tests/unit/test_ctimecode_timer.py`
- [X] T020 [P] [US2] Write failing test: `start()` after explicit `stop()` resumes callback emission from the next QF boundary in `tests/unit/test_ctimecode_timer.py`
- [X] T021 [P] [US2] Write failing test: `stop()` on a timer that was never started completes without error in `tests/unit/test_ctimecode_timer.py`
- [X] T022 [P] [US2] Write failing test: `start()` on an `EXHAUSTED` timer is a no-op and a warning is logged in `tests/unit/test_ctimecode_timer.py`

### Implementation for User Story 2

- [X] T023 [US2] Harden `start()`: ensure IDLE/STOPPED→RUNNING transition is thread-safe (use `threading.Lock` around state read/write); ensure the previous thread is fully joined before spawning a new one on restart in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T024 [US2] Harden `stop()`: confirm `threading.Event` stop-flag is cleared on restart so `_run_loop` does not exit immediately on the next `start()` call in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T025 [US2] Harden EXHAUSTED guard in `start()`: confirm `Logger.warning(...)` fires (use `from cuemsutils.log import Logger`) and state remains `EXHAUSTED` in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T026 [US2] Verify all Phase 4 tests now pass: `hatch run test:run tests/unit/test_ctimecode_timer.py -k "us2 or story2 or stop or restart or exhaust"`

**Checkpoint**: User Stories 1 and 2 both work independently. Lifecycle is fully controlled.

---

## Phase 5: User Story 3 — Replace or Remove Callback (Priority: P3)

**Goal**: The callback can be swapped or cleared while the timer is running without restarting it. The replacement takes effect on the next QF boundary.

**Independent Test**: Start the timer in bare-signal mode, let it fire with callback A, swap to callback B mid-run, assert only B fires on subsequent boundaries.

### Tests for User Story 3 (write first — MUST FAIL before implementation) ⚠️

- [X] T027 [US3] Write failing test: replacing callback while running — after swap, the new callback fires on the very next QF boundary (not merely at some later point), and the old callback receives no further calls in `tests/unit/test_ctimecode_timer.py`
- [X] T028 [P] [US3] Write failing test: setting `callback = None` while running — subsequent QF boundaries emit nothing in `tests/unit/test_ctimecode_timer.py`

### Implementation for User Story 3

- [X] T029 [US3] Implement `callback` as a property with a `threading.Lock`-protected setter: `_callback` is read under the lock each QF iteration so replacements are visible no later than the next boundary in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T030 [US3] Guard dispatch in `_run_loop`: read `_callback` under lock once per iteration; if `None`, skip invocation silently in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T031 [US3] Verify all Phase 5 tests now pass: `hatch run test:run tests/unit/test_ctimecode_timer.py -k "us3 or story3 or replace or remove or swap"`

**Checkpoint**: All three user stories are independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Exception resilience, seek handling, exports, lint, and timing validation.

- [X] T032 Write failing test: callback that raises an exception does not halt the timer — subsequent QF boundaries still fire in `tests/unit/test_ctimecode_timer.py`
- [X] T033 Implement try/except around callback invocation in `_run_loop`: log exception via `Logger.error(...)` using `from cuemsutils.log import Logger` at module top and continue loop in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T034 [P] Write failing tests: (a) forward seek — if CTimecode position jumps by K QFs, `_index` advances by K using a threshold of 1.5× `_qf_interval` to distinguish jitter from a genuine seek; (b) backward seek in parameterised mode — `_index` clamps to 0; (c) backward seek in bare-signal mode — timer continues firing with no args (no index to clamp) in `tests/unit/test_ctimecode_timer.py`
- [X] T035 Implement seek detection in `_run_loop`: initialise `_prev_tc_ms` to the CTimecode's millisecond value at `start()` time before entering the loop; each iteration compute `delta_ms = current_tc_ms - _prev_tc_ms` then update `_prev_tc_ms`; treat as seek if `delta_ms > 1.5 * qf_interval_ms` (forward skip) **or** `delta_ms < 0.5 * qf_interval_ms` (backward jump or stall); on seek, advance `_index` by `round(delta_ms / qf_interval_ms) - 1` (clamped to `[0, len(_params)]`); if resulting index causes exhaustion, transition to `EXHAUSTED`; in bare-signal mode skip all index logic entirely in `src/cuemsutils/tools/CTimecodeTimer.py`
- [X] T036 [P] Export `CTimecodeTimer` from `src/cuemsutils/tools/__init__.py` — file is currently empty; add the single line: `from cuemsutils.tools.CTimecodeTimer import CTimecodeTimer`
- [X] T037 [P] Run lint and fix all warnings: `hatch run test:lint src/cuemsutils/tools/CTimecodeTimer.py tests/unit/test_ctimecode_timer.py`
- [X] T038 Run full test suite and confirm all pass: `hatch run test:run tests/unit/test_ctimecode_timer.py`
- [X] T039 [P] Full real-time integration test (marked `@pytest.mark.slow`): run the timer for 1 second at 25 fps and assert callback jitter stays within ±1 ms across all QF boundaries in `tests/unit/test_ctimecode_timer.py`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user story phases
- **User Stories (Phases 3–5)**: All depend on Phase 2 completion; proceed sequentially in priority order
- **Polish (Phase 6)**: Depends on Phases 3–5 being complete

### User Story Dependencies

- **US1 (P1)**: Depends on Phase 2 only. No dependency on US2 or US3.
- **US2 (P2)**: Depends on Phase 2. Hardens Phase 2 stubs; independently testable in bare-signal mode.
- **US3 (P3)**: Depends on Phase 2. No dependency on US1 or US2.

### Within Each Phase

1. Write test tasks (MUST FAIL before implementation)
2. Implement to make tests pass
3. Run verification task to confirm
4. Commit before moving to next phase

### Parallel Opportunities

- T002, T005, T006, T007 can run in parallel with T003/T004 during Phase 2 (different file: tests/ vs src/) — note: T005/T006/T007 must be executed sequentially among themselves as they all write to the same test file
- T012, T013, T014 can run in parallel with T011 during Phase 3 tests
- T020, T021, T022 can run in parallel with T019 during Phase 4 tests
- T028 can run in parallel with T027 during Phase 5 tests
- T034, T036, T037, T039 can run in parallel during Phase 6

---

## Parallel Example: User Story 1 Tests

```text
Run in parallel (different test functions, same file — no conflict):
  Task T012: bare-signal mode test
  Task T013: no-callback no-error test
  Task T014: exhaustion + EXHAUSTED state test
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (includes start/stop tests T006, T007)
3. Complete Phase 3: User Story 1 (includes timing smoke test T017)
4. **STOP and VALIDATE**: `hatch run test:run tests/unit/test_ctimecode_timer.py`
5. Parameterised QF timer is usable as delivered

### Incremental Delivery

1. Phase 1 + 2 → skeleton + lifecycle ready (fully tested)
2. Phase 3 → parameterised callbacks work (MVP)
3. Phase 4 → lifecycle hardened
4. Phase 5 → callback hot-swap enabled
5. Phase 6 → exception resilience, seek handling, lint clean

---

## Notes

- All time-based tests MUST mock `time.sleep` and `time.time` — no real sleeps in unit tests
- `@pytest.mark.slow` for the real-time integration test in T039
- `[P]` tasks = different files or non-overlapping functions, safe to run in parallel
- Commit after each phase checkpoint
- The `_run_loop` uses a `threading.Event` stop flag (not a raw boolean) to ensure thread-safe exit signalling
- Logging: use `from cuemsutils.log import Logger` then `Logger.warning(...)` / `Logger.error(...)` — no module-level `logger` object exists
