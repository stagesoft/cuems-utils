# CTimecode hardening — briefing for fade-engine maintainer

**Branch:** `feat/faders` (fast-forwarded to include all fixes as of 2026-04-27)
**Version:** `cuemsutils 0.1.0rc6`
**Task:** ClickUp 869cyndtv

This document covers everything that changed in `CTimecode` (and adjacent tools) that is relevant to fade-engine and the ongoing faders integration in cuems-utils.

---

## TL;DR

- **`.milliseconds` is deprecated.** Use `.milliseconds_rounded` (int) or `.milliseconds_exact` (float).
- **`CTimecodeTimer` is already migrated** — no action needed there.
- **`FadeCalculator` has a bug fix** that makes `calculate_timeline` correct at all framerates (was silently broken at anything other than `'ms'`).
- **`__add__` / `__sub__` arithmetic was off by one frame.** Now correct. This affects `position + duration` and `out_time - in_time` operations.
- **Cross-framerate arithmetic now raises** instead of silently computing garbage. Use `.return_in_other_framerate()` explicitly before mixing rates.
- **`framerate` getter returns a proper type** (`int` 25, not `str` `'25'`).

---

## 1. `.milliseconds` precision split

The old `.milliseconds` property truncated with `int()`, losing up to ~1ms per call at fractional framerates (29.97, 23.976). It is now a `DeprecationWarning`-emitting alias.

### New API

| Property | Type | When to use |
|---|---|---|
| `.milliseconds_exact` | `float` | Precision-sensitive math: offset calc, MTC bias, scheduler drift, anywhere you accumulate across many frames at 29.97/23.976 |
| `.milliseconds_rounded` | `int` | Sleep durations, CLI args, polling loops, dict/set keys, int arithmetic |
| `.milliseconds` | `int` *(deprecated)* | Only during migration — it emits `DeprecationWarning` and delegates to `_rounded` |

### Migration pattern

```python
# Old
if tc.milliseconds >= threshold:          # → tc.milliseconds_rounded >= threshold
    time.sleep(wait.milliseconds / 1000)  # → time.sleep(wait.milliseconds_rounded / 1000)
    offset = -start.milliseconds          # → -start.milliseconds_exact  (float, no drift)
```

### How to find remaining uses

```bash
python -W error::DeprecationWarning pytest tests/
# every .milliseconds call-site becomes a hard failure
```

---

## 2. `CTimecodeTimer` — already migrated

Lines 115 and 124 previously did `float(self._timecode.milliseconds)`.
Now correctly use `self._timecode.milliseconds_exact` — no truncation drift in the
quarter-frame seek-detection delta calculation. **Nothing to do here.**

---

## 3. `FadeCalculator.calculate_timeline` — bug fix at non-ms framerates

**Old code** (broken):
```python
CTimecode(start_seconds=(start_time.milliseconds + i * 20))
```
This passed a **milliseconds** value into `start_seconds` (which expects **seconds**).
At `framerate='ms'` this happened to work because 1 ms-frame == 1 ms. At 25fps or 29.97fps it produced timecodes that were 1000× too large.

**New code** (correct):
```python
CTimecode(start_seconds=(start_time.milliseconds_rounded + i * 20) / 1000)
```

The `/1000` converts ms → seconds before the CTimecode constructor sees it.

If fade-engine has its own copy of timeline generation using `start_seconds=ms_value`, apply the same fix.

---

## 4. `__add__` / `__sub__` arithmetic — one-frame correction

The old arithmetic mixed 0-indexed `frame_number` (what `.milliseconds` computed from) with 1-indexed `frames` (what upstream stores). For two CTimecodes:

```
old: result.frames = a.frames + b.frames      # double-counted the +1 base offset
new: result.frames = a.frames + b.frames - 1  # correct

old: result.frames = a.frames - b.frames      # one frame short
new: result.frames = a.frames - b.frames + 1  # correct
```

**Practical impact for faders:**

```python
duration = out_time - in_time   # was 1 frame short; now correct
end_tc   = start + duration     # was 1 frame long; now correct
```

If fade-engine computed durations or end positions from CTimecode arithmetic, the results shift by 1 frame. At 25fps this is 40ms — invisible in most contexts but worth verifying against any hardcoded expected values in tests.

---

## 5. Cross-framerate arithmetic now raises `CTimecodeError`

Previously `tc_at_25fps + tc_at_30fps` silently used the wrong frame counts and produced garbage. Now it raises:

```python
CTimecodeError: Arithmetic between CTimecodes of different framerates (25 vs 30);
use .return_in_other_framerate() first.
```

For fade-engine, if you mix MTC framerate (e.g., 25fps) with media framerate (e.g., 29.97fps), always convert first:

```python
duration_in_mtc_rate = media_duration.return_in_other_framerate(mtc.main_tc.framerate)
end_tc = start_tc + duration_in_mtc_rate
```

---

## 6. `framerate` getter — returns numeric type, not string

Upstream `timecode` 1.5.1 stores integer SMPTE rates as strings internally (`'25'`, `'30'`), so `tc.framerate == 25` was silently `False` (it returned `'25'`).

Now the getter normalizes: `int` for SMPTE integers, `float` for fractional, `int 1000` for `'ms'`.

```python
CTimecode(framerate=25).framerate == 25   # True (was False)
CTimecode(framerate=29.97).framerate == 29.97   # True
CTimecode().framerate == 1000             # True (ms default)
```

If fade-engine checks `tc.framerate` against a literal, it now works as expected.

---

## 7. `start_seconds=` constructor — playhead semantics

Upstream's `float_to_tc(s)` returns `int(s * fps)` (exposure-window semantics, off by one from `start_timecode`). This caused `CTimecode(framerate=25, start_seconds=30.0)` and `CTimecode(framerate=25, start_timecode='00:00:30:00')` to disagree by 1 frame.

Now both paths agree. The wrapper routes `start_seconds` through `tc_to_frames` (HMSF string), which handles drop-frame correctly at 29.97 DF.

**For FadeCue / fade-engine:** `format_timecode(value)` (the cuems-utils helper) previously manually added `+1` to compensate. That compensation is removed. If fade-engine has its own `+1` patch on top of `CTimecode(start_seconds=...)`, remove it — it is now a double-correction.

---

## 8. `__str__` past 24h — monotonic display

`str(tc)` at frames > 24h used to wrap back to `00:00:00:01`. Now shows `24:00:00:01`. Relevant for any log output or debug display in long-running fade sequences.

---

## 9. FadeCue — no code changes needed

`FadeCue` itself uses `format_timecode` and CTimecode constructors but no direct `.milliseconds` calls. It is clean. The `feat/faders` branch is fully up to date with all fixes.

---

## 10. Running the audit

```bash
cd /path/to/cuems-utils   # or fade-engine
python -W error::DeprecationWarning pytest tests/
```

Any remaining `.milliseconds` call-site (in your code or any dependency that forwards it) will turn into a hard failure. Fix each site by choosing `_rounded` or `_exact` per intent.

---

## Branch topology

```
main (721db82)
  └── feat/faders (05f78bb)  ← you are here
       ├── FadeCue + CTimecodeTimer (original faders work)
       ├── settings.xsd / output_latency_ms (infrastructure)
       ├── CTimecode hardening (PR #2, #4, #5, #6, #10)
       └── cue .milliseconds migrations (AudioCue, VideoCue, DmxCue)
```

Pre-merge snapshot tag: `pre-ctimecode-merge` @ `main` — safe rollback point.
