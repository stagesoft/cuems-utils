# Feature Specification: Timecode Quarter-Frame Timer

**Feature Branch**: `002-timecode-qf-timer`
**Created**: 2026-04-07
**Status**: Draft
**Input**: User description: "create a timer that can be hooked to a CTimecode object and emit a function at a quarter frame resolution"

## Clarifications

### Session 2026-04-07

- Q: What are the callback parameters at each quarter-frame interval? → A: The timer accepts a list of tuples as a parameter; at each quarter-frame interval the contents of the corresponding tuple are unpacked and passed as the arguments to the callback.
- Q: When the tuple list is exhausted, what should the timer do? → A: The timer stops automatically if and only if a tuple list was provided. If no tuple list is provided, the timer continues running until explicitly stopped.
- Q: When no tuple list is provided, what arguments does the callback receive at each quarter-frame boundary? → A: The callback is called with no arguments (bare signal).
- Q: Can the tuple list be replaced while the timer is running? → A: No. The tuple list is fixed at construction time. A new timer instance must be created to use a different parameter sequence.
- Q: What happens if start is called again after the timer stopped due to tuple list exhaustion? → A: No-op or warning; the timer cannot be restarted after exhaustion. A new instance must be created.
- Q: When the CTimecode jumps discontinuously (seek), how does the tuple list index advance? → A: The index skips proportionally — tuples corresponding to the skipped quarter-frames are discarded and the index advances to match the new timecode position.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Attach Timer to Timecode and Receive Callbacks (Priority: P1)

A show control developer attaches a timer to a running CTimecode object, provides a list of parameter tuples, and registers a callback function. As the timecode advances, the callback fires at every quarter-frame boundary with the contents of the corresponding tuple unpacked as its arguments, allowing the application to drive parameterised actions at sub-frame precision.

**Why this priority**: This is the core feature — the entire value proposition. Without this, nothing else is meaningful.

**Independent Test**: Can be tested by creating a CTimecode object, attaching the timer with a known list of tuples and a callback, advancing the timecode, and asserting the callback fires with the correct tuple contents at each quarter-frame boundary.

**Acceptance Scenarios**:

1. **Given** a CTimecode running at a standard frame rate and a timer configured with a list of N tuples, **When** the timer is attached and the timecode advances, **Then** the registered callback is called at each quarter-frame boundary with the contents of the next tuple in the list unpacked as arguments.
2. **Given** a tuple list of `[(a1, b1), (a2, b2)]`, **When** the first quarter-frame boundary fires, **Then** the callback is called as `callback(a1, b1)`; on the second boundary it is called as `callback(a2, b2)`.
3. **Given** no callback is registered, **When** the timecode advances, **Then** the timer advances silently without error.

---

### User Story 2 - Start and Stop the Timer (Priority: P2)

A developer needs to start the timer when a cue begins playback and stop it when playback ends, cleanly releasing resources and firing no further callbacks.

**Why this priority**: Without lifecycle control, the timer would have no way to halt, leading to resource leaks and spurious callbacks after playback ends.

**Independent Test**: Can be tested by starting the timer, letting it fire several callbacks, stopping it, and asserting no further callbacks are emitted after stop is called.

**Acceptance Scenarios**:

1. **Given** a running timer, **When** stop is called, **Then** no further callbacks are emitted even if the CTimecode continues to advance.
2. **Given** a stopped timer, **When** start is called again, **Then** the timer resumes emitting callbacks from the current timecode position.
3. **Given** a timer that has never been started, **When** stop is called, **Then** the call completes without error.

---

### User Story 3 - Replace or Remove a Registered Callback (Priority: P3)

A developer needs to swap the callback function during a session — for example, when transitioning between cues — without stopping and restarting the timer.

**Why this priority**: Enables dynamic show control scenarios without the overhead of a full timer restart.

**Independent Test**: Can be tested by registering one callback, replacing it with another while the timer is running, and asserting only the second callback receives subsequent quarter-frame events.

**Acceptance Scenarios**:

1. **Given** a timer with callback A registered, **When** callback B is registered as a replacement, **Then** only callback B fires on subsequent quarter-frame boundaries.
2. **Given** a timer with a callback registered, **When** the callback is removed, **Then** the timer continues running but fires no callbacks.

---

### Edge Cases

- What happens when the CTimecode framerate is changed while the timer is running?
- How does the timer behave when the CTimecode jumps discontinuously (seek forward or backward)? → Index skips proportionally; tuples for skipped QFs are discarded (resolved, FR-007). Backward seek: index cannot go negative — treated as seek to start (index 0).
- What happens if the registered callback raises an exception — does the timer continue or halt?
- What happens when the CTimecode is at framerate 'ms' (milliseconds) — what constitutes a quarter frame at that resolution?
- What happens if the timer tick interval is slower than a quarter-frame duration (overrun)?
- What happens when the tuple list is exhausted? → Timer stops automatically (resolved, FR-009).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The timer MUST accept a CTimecode object as its timecode source and an optional list of parameter tuples at construction time. The tuple list is immutable for the lifetime of the instance; a new instance must be created to use a different parameter sequence.
- **FR-002**: The timer MUST fire a registered callback once per quarter frame as the timecode advances, where a quarter frame equals one quarter of the duration of one frame at the CTimecode's current framerate.
- **FR-003**: When a parameter tuple list is provided, at each quarter-frame boundary the callback MUST be invoked with the contents of the corresponding tuple unpacked as its arguments (i.e., `callback(*tuple[i])`).
- **FR-003b**: When no parameter tuple list is provided, the callback MUST be invoked with no arguments at each quarter-frame boundary (bare signal).
- **FR-009**: When a parameter tuple list is provided and the last tuple has been consumed, the timer MUST stop automatically and emit no further callbacks. When no tuple list is provided, the timer MUST continue running until explicitly stopped.
- **FR-004**: The timer MUST support registering, replacing, and removing a callback without restarting the timer.
- **FR-005**: The timer MUST provide explicit start and stop controls; it MUST NOT emit callbacks before start is called or after stop is called. If start is called on a timer that has stopped due to tuple list exhaustion, the call MUST be a no-op (or emit a warning) and the timer MUST NOT restart; a new instance is required.
- **FR-006**: The timer MUST continue operating correctly if the registered callback raises an exception, logging the error and proceeding to the next quarter-frame event.
- **FR-007**: The timer MUST handle a discontinuous jump in the CTimecode position (seek) gracefully. On a seek, the tuple list index MUST advance proportionally to the number of quarter-frames skipped, discarding the corresponding tuples. Callbacks MUST resume from the new index position without emitting spurious events for the skipped range. If the seek causes the index to exceed the list length, the timer MUST stop as per FR-009. In bare-signal mode (no tuple list), seek events have no effect on any index state; the timer continues emitting bare-signal callbacks uninterrupted.
- **FR-PERF-001**: The timer MUST fire callbacks with a timing accuracy within ±10% of one quarter-frame duration relative to the timecode's framerate, measurable in automated tests.

### Key Entities

- **CTimecodeTimer**: The timer component that tracks a CTimecode source and dispatches quarter-frame callbacks. Holds a reference to a CTimecode, an immutable parameter tuple list (set at construction), a callback, and its own running state.
- **CTimecode**: The existing timecode object (from `CTimecode.py`) that acts as the time source. The timer reads its current position to determine when quarter-frame boundaries occur.
- **Quarter-Frame Boundary**: A point in time occurring at 1/(4 × framerate) second intervals, derived from the CTimecode's framerate. Four quarter-frame boundaries exist within each frame.
- **Parameter Tuple List**: An ordered list of tuples provided to the timer at configuration time. At each quarter-frame boundary, the next tuple in the list is consumed and its contents are unpacked as the callback arguments.
- **Callback**: A callable registered by the developer that is invoked at each quarter-frame boundary, receiving unpacked tuple contents as its arguments.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For any standard SMPTE frame rate (24, 25, 29.97, 30 fps), advancing the timecode by exactly one frame results in exactly 4 callback invocations — verifiable in automated tests.
- **SC-002**: Callback timing accuracy stays within ±10% of one quarter-frame duration under normal operating conditions — verifiable with automated timing assertions.
- **SC-003**: Stopping the timer halts all callback emission within one quarter-frame interval — verifiable in automated tests.
- **SC-004**: A callback exception does not prevent subsequent quarter-frame callbacks from firing — verifiable in automated tests.
- **SC-005**: Replacing a callback while the timer is running takes effect no later than the next quarter-frame boundary — verifiable in automated tests.
- **SC-006**: Given a known tuple list, each callback invocation receives exactly the arguments from the corresponding tuple in the correct order — verifiable in automated tests.
- **SC-QUALITY-001**: No new lint or type warnings are introduced by the implementation.
- **SC-TEST-001**: Automated unit tests covering all functional requirements exist and fail before the implementation and pass after.

## Assumptions

- The CTimecode object's framerate is a standard SMPTE value (24, 25, 29.97, 30 fps) or 'ms'. For 'ms' framerate, one quarter frame is defined as 0.25 ms; practical use at 'ms' framerate is considered out of scope for precision guarantees.
- The timer drives itself using a real-time clock; it does not require the CTimecode object to be externally advanced — it reads the CTimecode's current value and computes elapsed quarter frames.
- A single callback is supported per timer instance (not a multi-subscriber model); multiple subscribers are out of scope.
- Thread safety for concurrent start/stop/callback-swap calls is a best-effort concern; the primary use case is single-threaded show control loops.
- The tuple list is indexed sequentially from the first quarter-frame event after start; index 0 is used on the first quarter-frame boundary, index 1 on the second, and so on.
