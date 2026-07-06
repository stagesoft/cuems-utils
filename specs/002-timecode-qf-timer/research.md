# Research: Timecode Quarter-Frame Timer

**Branch**: `002-timecode-qf-timer` | **Date**: 2026-04-07

## Decision Log

### D-001: Timer Loop Mechanism

**Decision**: Daemon `threading.Thread` with a `time.sleep` polling loop.

**Rationale**: The existing `Timeoutloop` uses a blocking `time.sleep` pattern. A daemon thread wrapping the same pattern keeps the implementation minimal, consistent with the codebase, and requires no new dependencies. The primary use case is single-threaded show control; the thread exits automatically when the main process exits (daemon=True).

**Alternatives considered**:
- `asyncio` event loop — rejected; cuems-utils has no async infrastructure and adding it introduces complexity without benefit for this feature.
- `threading.Timer` (one-shot) — rejected; repeated rescheduling accumulates drift. A loop with a reference `start_wall_time` is more accurate.
- Cooperative caller-driven poll — rejected; would require callers to tick the timer explicitly, violating the fire-and-forget contract in FR-002.

---

### D-002: Quarter-Frame Interval Calculation

**Decision**: `qf_interval = 1.0 / (4.0 * float(timecode.framerate))`

**Rationale**: `CTimecode.framerate` is already exposed as a string or numeric value by the parent `Timecode` class. Converting to float handles both integer frame rates (25) and drop-frame variants (29.97). The QF interval is computed once at construction from the provided `CTimecode` and cached.

**Alternatives considered**:
- Deriving from `CTimecode.milliseconds` — rejected; milliseconds-based arithmetic loses precision for non-integer frame rates.

---

### D-003: Seek Detection

**Decision**: Poll the `CTimecode` value on each loop iteration; compare the actual elapsed QF count (from wall clock since start) to the expected count. A discrepancy of more than one QF indicates a seek. Advance the tuple index by the delta.

**Rationale**: `CTimecode` is a plain data object with no event/signal API. The timer cannot be notified of external position changes. Polling at each QF tick is the simplest approach with acceptable overhead (one integer comparison per tick).

**Seek formula**:
```
expected_qf = int((wall_now - wall_start) * 4 * framerate)
actual_qf   = int(timecode.milliseconds / qf_interval_ms)
delta       = actual_qf - prev_actual_qf
if delta != 1: seek detected; advance index by delta (clamped to [0, len(params)])
```

**Backward seek**: if `actual_qf < prev_actual_qf`, delta is negative. Index is clamped to 0 (cannot go negative) — treated as seek back to start of tuple list.

**Seek threshold**: A delta of > 1.5 × QF interval is treated as a seek. This absorbs normal `time.sleep` overshoot jitter (up to ~10% of QF interval) while reliably detecting intentional position jumps of ≥ 2 QFs. Values below 1.5 cause false seeks on jitter; values above 2.0 mask real single-QF seeks.

**Alternatives considered**:
- Hooking into `CTimecode.__setattr__` — rejected; `CTimecode` inherits from `timecode.Timecode` (third-party), patching is fragile.

---

### D-004: State Machine

**Decision**: Four states — `IDLE`, `RUNNING`, `STOPPED`, `EXHAUSTED`.

| State | Meaning | Transitions |
|-------|---------|-------------|
| IDLE | Constructed, not yet started | → RUNNING on `start()` |
| RUNNING | Timer loop active | → STOPPED on `stop()`; → EXHAUSTED on list end |
| STOPPED | Explicitly stopped | → RUNNING on `start()` |
| EXHAUSTED | Tuple list consumed | No further transitions; `start()` is a no-op with warning |

**Rationale**: Distinguishing STOPPED from EXHAUSTED allows `start()` to safely restart a manually stopped timer while correctly blocking restart after exhaustion (FR-005).

---

### D-005: Callback Exception Handling

**Decision**: Wrap each callback invocation in a `try/except`; log the exception via `cuemsutils.log` and continue the loop (FR-006).

**Rationale**: Consistent with existing exception handling patterns in `SignalEngine` and `CommunicatorServices`. The timer must not crash due to caller bugs.

---

### D-006: No New Runtime Dependencies

**Decision**: Use stdlib `threading` and `time` only.

**Rationale**: All required primitives are in the standard library. Adding a dependency (e.g., `schedule`, `apscheduler`) would require maintenance justification per the constitution's engineering standards. The feature is simple enough that stdlib suffices.
