# Implementation Plan: Timecode Quarter-Frame Timer

**Branch**: `002-timecode-qf-timer` | **Date**: 2026-04-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/002-timecode-qf-timer/spec.md`

## Summary

Add `CTimecodeTimer` — a component that hooks to a `CTimecode` object and fires a registered callback at every quarter-frame boundary. Optionally accepts an immutable list of parameter tuples at construction; each tuple's contents are unpacked as callback arguments at the corresponding quarter-frame. When a tuple list is provided the timer stops automatically after the last tuple is consumed; without one it runs indefinitely until explicitly stopped. Research confirmed no new runtime dependencies are required.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: stdlib only (`threading`, `time`) — `timecode` already present via `CTimecode`
**Storage**: N/A
**Testing**: pytest + ruff (lint) + mypy (types) via `hatch run test:run` / `hatch run test:lint`
**Target Platform**: Linux (same as rest of cuems-utils)
**Project Type**: Library
**Performance Goals**: Callback timing accuracy within ±10% of one quarter-frame duration (e.g., ≤1 ms jitter at 25 fps where QF = 10 ms)
**Constraints**: No new runtime dependencies; no warnings introduced; single-threaded primary use case
**Scale/Scope**: Single timer instance per cue; no multi-subscriber requirement

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

- **Code Quality** (Principle I): `CTimecodeTimer` MUST pass `ruff check` with no new warnings. Public class, methods, and non-obvious logic MUST include docstrings or inline rationale. Gate: `hatch run test:lint src/ tests/`.
- **Testing Standards** (Principle II): Unit tests MUST cover all FRs (FR-001 through FR-009, FR-PERF-001). Tests MUST fail before implementation and pass after. Gate: `hatch run test:run tests/unit/test_ctimecode_timer.py`. Timing tests MUST use controlled mocking of `time.sleep` / `time.time` — no real-time sleeps in unit tests.
- **UX Consistency** (Principle III): No user-facing CLI surface for this feature. Error messages from the timer (logged on callback exception) MUST follow existing log patterns (`src/cuemsutils/log.py`). Class naming MUST follow the existing `C`-prefix convention (`CTimecodeTimer`, matching `CTimecode`).
- **Performance Requirements** (Principle IV): QF callback jitter ≤ ±10% of QF duration. For 25 fps this is ±1 ms. Validated via unit test with mocked clock; real-time integration test optional and marked `@pytest.mark.slow`.

*Post-Phase-1 re-check*: No constitution violations introduced. Complexity tracking not required.

## Project Structure

### Documentation (this feature)

```text
specs/002-timecode-qf-timer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── CTimecodeTimer.md  # Python API contract
└── tasks.md             # Phase 2 output (/speckit.tasks — not created here)
```

### Source Code (repository root)

```text
src/cuemsutils/tools/
├── CTimecode.py          # existing — unchanged
├── CTimecodeTimer.py     # NEW — CTimecodeTimer class

tests/unit/
└── test_ctimecode_timer.py  # NEW — unit tests for all FRs
```

**Structure Decision**: Single-project layout, consistent with all other tools in `src/cuemsutils/tools/`. No new package or submodule required.

## Complexity Tracking

No constitution violations. Table omitted.
