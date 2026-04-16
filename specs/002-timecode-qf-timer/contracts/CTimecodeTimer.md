# Python API Contract: CTimecodeTimer

**Module**: `cuemsutils.tools.CTimecodeTimer`
**Class**: `CTimecodeTimer`
**Contract version**: 1.0 | **Date**: 2026-04-07

## Constructor

```python
CTimecodeTimer(
    timecode: CTimecode,
    params: list[tuple] | None = None,
)
```

| Parameter | Required | Description |
|-----------|----------|-------------|
| `timecode` | Yes | `CTimecode` instance providing framerate and current position |
| `params` | No | Ordered list of tuples; each tuple is unpacked as callback args at the corresponding QF. `None` or `[]` → bare-signal mode (callback called with no args) |

**Post-conditions**:
- Timer is in `IDLE` state.
- `params` is frozen; passing a new list requires a new instance.
- `qf_interval = 1.0 / (4 × float(timecode.framerate))` is cached.

---

## Methods

### `start() -> None`

Starts the timer loop in a daemon thread.

- If state is `IDLE` or `STOPPED`: transitions to `RUNNING`; begins emitting QF callbacks.
- If state is `RUNNING`: no-op.
- If state is `EXHAUSTED`: no-op; emits a warning log. A new instance is required.

### `stop() -> None`

Stops the timer loop.

- If state is `RUNNING`: signals loop to exit; transitions to `STOPPED`. Any in-progress callback invocation completes before the thread joins.
- If state is `IDLE`, `STOPPED`, or `EXHAUSTED`: no-op.

---

## Properties

### `callback` *(read/write)*

```python
@property
def callback(self) -> Callable | None: ...

@callback.setter
def callback(self, fn: Callable | None) -> None: ...
```

- Can be set at any time, including while the timer is `RUNNING`.
- Setting to `None` removes the callback; subsequent QF boundaries are silent.
- Takes effect no later than the next QF boundary.

---

## Callback Invocation Signatures

| Mode | Invocation |
|------|-----------|
| With `params` | `callback(*params[index])` — tuple contents unpacked |
| Without `params` | `callback()` — no arguments |

---

## Exceptions & Errors

| Situation | Behaviour |
|-----------|-----------|
| `timecode` is `None` | Raises `ValueError` at construction |
| Callback raises an exception | Exception is caught, logged via `cuemsutils.log`; loop continues |
| `start()` called on exhausted timer | No-op; warning logged (`log.warning`) |

---

## State Transitions Summary

```
IDLE ──start()──► RUNNING ──stop()──► STOPPED ──start()──► RUNNING
                     └──exhausted──► EXHAUSTED  (start() is a no-op here)
```

---

## Usage Examples

### Bare-signal mode (no params)

```python
timer = CTimecodeTimer(timecode=my_tc)
timer.callback = lambda: print("QF tick")
timer.start()
# ... later ...
timer.stop()
```

### Parameterised mode

```python
params = [(0.0,), (0.25,), (0.5,), (0.75,)]  # 4 QFs = 1 frame of fade steps
timer = CTimecodeTimer(timecode=my_tc, params=params)
timer.callback = apply_fade_level
timer.start()
# Timer stops automatically after 4 QF callbacks
```

### Replacing callback at runtime

```python
timer.callback = new_handler   # takes effect on next QF boundary
timer.callback = None          # remove; subsequent QFs are silent
```
