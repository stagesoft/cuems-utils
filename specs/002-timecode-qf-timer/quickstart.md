# Quickstart: CTimecodeTimer

**Branch**: `002-timecode-qf-timer` | **Date**: 2026-04-07

## What it does

`CTimecodeTimer` hooks to a `CTimecode` object and fires a callback at every quarter-frame boundary. Optionally, a list of parameter tuples can be provided; the contents of each tuple are unpacked as the callback's arguments at the corresponding quarter-frame.

## Minimal example — bare-signal mode

```python
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.CTimecodeTimer import CTimecodeTimer

tc = CTimecode(start_timecode="00:00:00:00", framerate=25)

timer = CTimecodeTimer(timecode=tc)
timer.callback = lambda: print("quarter-frame tick")
timer.start()

# ... cue runs ...

timer.stop()
```

## Parameterised mode — finite sequence

```python
# 4 tuples = 1 frame worth of quarter-frame callbacks
fade_steps = [(0.0,), (0.33,), (0.66,), (1.0,)]

timer = CTimecodeTimer(timecode=tc, params=fade_steps)
timer.callback = lambda level: set_dimmer(level)
timer.start()
# timer stops automatically after all 4 tuples are consumed
```

## Replacing the callback mid-run

```python
timer.callback = handle_cue_a   # swap immediately; takes effect next QF
timer.callback = None           # silence subsequent QFs without stopping
```

## Lifecycle rules

- A timer in the `EXHAUSTED` state (tuple list consumed) **cannot be restarted** — create a new instance.
- A manually stopped timer **can** be restarted with `start()`.
- The tuple list is **immutable** for the lifetime of an instance.

## Running tests

```bash
hatch run test:run tests/unit/test_ctimecode_timer.py
hatch run test:lint src/cuemsutils/tools/CTimecodeTimer.py
```
