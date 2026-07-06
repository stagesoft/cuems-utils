# Data Model: Timecode Quarter-Frame Timer

**Branch**: `002-timecode-qf-timer` | **Date**: 2026-04-07

## Entities

### CTimecodeTimer

The central component. Instantiated once per parameter sequence.

| Attribute | Type | Mutability | Description |
|-----------|------|-----------|-------------|
| `_timecode` | `CTimecode` | Immutable (construction) | Time source; provides `framerate` and current position |
| `_params` | `tuple[tuple, ...] \| None` | Immutable (construction) | Ordered parameter tuples; `None` means bare-signal mode |
| `_callback` | `Callable \| None` | Mutable (any time) | Function invoked at each QF boundary |
| `_index` | `int` | Mutable (runtime) | Current position in `_params`; 0-based; advances each QF |
| `_state` | `Literal['idle','running','stopped','exhausted']` | Mutable (lifecycle) | Timer state machine |
| `_qf_interval` | `float` | Immutable (construction) | Seconds per quarter-frame: `1.0 / (4 × framerate)` |
| `_thread` | `threading.Thread \| None` | Managed internally | Daemon thread running the timer loop |
| `_wall_start` | `float \| None` | Set on `start()` | `time.time()` at last `start()` call |

### State Machine

```
IDLE ──start()──► RUNNING ──stop()──────► STOPPED ──start()──► RUNNING
                     │                       (loop)
                     └──list exhausted──► EXHAUSTED
                                            │
                                     start() = no-op + warning
```

### Quarter-Frame Boundary

Not a stored entity — a computed event.

- **Interval**: `1.0 / (4 × framerate)` seconds
- **Count per frame**: exactly 4
- **Index mapping**: QF boundary N (0-based from `start()`) maps to `_params[N]`
- **Seek adjustment**: if CTimecode position jumps by K QFs, index advances by K (clamped to `[0, len(_params)]`)

### Parameter Tuple List

Immutable sequence set at construction.

| Property | Value |
|----------|-------|
| Type | `list[tuple[Any, ...]]` at construction; stored as `tuple[tuple, ...]` |
| Indexing | 0-based, sequential from first QF after `start()` |
| Exhaustion | When `_index >= len(_params)` → transition to EXHAUSTED |
| Backward seek | `_index` clamped to `0` — never goes negative |
| Absent | `None` — timer runs indefinitely; callback invoked with no args |

### Callback

Not persisted; held by reference.

| Mode | Invocation |
|------|-----------|
| With params | `callback(*_params[_index])` |
| Without params | `callback()` |
| No callback set | No-op (timer loop continues) |
| Callback raises | Exception caught, logged, loop continues |

## Validation Rules

- `CTimecode` must be provided at construction and must not be `None`.
- `params`, if provided, must be a non-empty list of tuples. An empty list is treated as `None` (bare-signal mode).
- `framerate` must be numeric and > 0 (inherited from `CTimecode` validation).
- `_index` must always satisfy `0 ≤ _index ≤ len(_params)` (when params present).
