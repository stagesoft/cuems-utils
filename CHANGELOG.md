# Changelog

## 0.1.0rc6 — 2026-04-27

CTimecode hardening pass (closes ClickUp 869cyndtv items #1–#7 + audit findings). This release is a coordinated semantic fix to the CTimecode wrapper: `__init__` now produces playhead-semantic frames; arithmetic operators are off-by-one-correct and reject cross-framerate operands; `.milliseconds` is split into precision-explicit accessors; the `format_timecode` `+1` workaround is removed; FadeCalculator's silent ms-as-seconds unit error is fixed.

### Changed (breaking)
- `CTimecode.__init__(start_seconds=...)` now produces playhead-semantic frames (one more than before for the same real-time value). The same real time `T` produces the same `.frames` regardless of which constructor path was used (`start_timecode='HH:MM:SS:FF'` vs `start_seconds=T`). Routes through `tc_to_frames` via an HMSF string so drop-frame correction at 29.97/59.94 DF is handled correctly. Empirically: at 29.97 DF, `start_seconds=600` now produces `frames=17983` (matching `start_timecode='00:10:00:00'`), where the old path produced `18000` (off by 17 frames).
- Arithmetic between CTimecodes of different framerates now raises `CTimecodeError` instead of silently using `other.frames` as if same-framerate. Affected: `__add__`, `__sub__`, `__mul__`, `__truediv__`. Cross-framerate use cases must explicitly call `.return_in_other_framerate()` first.
- `__add__`/`__sub__` now produce playhead-correct results: `(CTimecode(start_seconds=10) + CTimecode(start_seconds=20)).milliseconds_rounded == 30000` (was `29960`); `(CTimecode(start_seconds=30) - CTimecode(start_seconds=10)).milliseconds_rounded == 20000` (was `19960`).
- `__truediv__` now `round()`s the float division result (was passing float to upstream's frames setter, which raised `TypeError`); explicitly rejects zero/negative int divisors with `CTimecodeError`.
- `framerate` getter now returns canonical numeric types — `int` for SMPTE integer rates (was `'25'` string), `float` for fractional, `int 1000` for ms (unchanged). `tc.framerate == 25` now works as expected (Option D).
- `return_in_other_framerate` rewritten in frame domain — the old time-domain round-trip dropped one frame per conversion. Round-trips between framerates now stable.
- `helpers.format_timecode(value)` no longer applies a manual `+1` to `.frames` — that compensation is now redundant since `__init__` canonicalizes itself. The combined effect is identical at the default `'ms'` framerate; differs by one frame at other framerates (and matches the `start_timecode` ctor path now).
- `FadeCalculator.calculate_timeline` no longer silently treats milliseconds as seconds — `start_seconds = ms_value / 1000`. The unit error self-cancelled at framerate `'ms'` (where `1 ms-frame == 1 ms`) but produced wildly wrong values at any other framerate.

### Deprecated
- `CTimecode.milliseconds` (int) — now an alias of `.milliseconds_rounded` that emits `DeprecationWarning`. Migrate to `.milliseconds_rounded` (int, rounded) or `.milliseconds_exact` (float, precise) per intent. Will be removed at the first stable release.

### Added
- `CTimecode.milliseconds_exact: float` — exact-precision milliseconds via `frame_number * 1000 / float(framerate)`. Use for precision-sensitive math (offset calc, scheduler, MTC bias measurement).
- `CTimecode.milliseconds_rounded: int` — `round(milliseconds_exact)`. Use for sleep durations, integer CLI args, polling comparisons, dict/set keys.
- Same-framerate assertion error messages on every arithmetic operator.
- `tests/unit/test_ctimecode.py` expanded with full framerate matrix coverage (`24, 25, 29.97, 30, 'ms'`), DF-boundary parametrization at 29.97, the `TestPrecisionSplit` class anchoring the V2 deprecation contract, and hypothesis property tests for round-trip invariants.
- `tests/unit/test_fade_calculator.py` gained intermediate-values correctness test and a no-DeprecationWarning regression pin.

### Fixed
- `CTimecodeTimer._run_loop` migrated from `.milliseconds` to `.milliseconds_exact` (pre-existing internal consumer).
- `CTimecode.__init__` no longer raises `ValueError` for very small positive `start_seconds` (e.g., `0.03125` at 24fps where upstream's `int(s*ifr)` produced `0` and hit the frames>0 setter guard). The wrapper now bypasses upstream's start_seconds path entirely when canonicalizing.

### Migration: `.milliseconds` precision split

The original `.milliseconds: int` truncated via `int()`, losing up to 1ms per call at fractional framerates and accumulating monotonically. The new API splits this into two explicit accessors, with the original retained as a deprecated alias to ease migration.

| If you currently do | Migrate to | Why |
|---------------------|------------|-----|
| `tc.milliseconds == 30000` (integer fr) | `tc.milliseconds_rounded == 30000` | Behavior identical at integer fr; clarifies rounding intent. |
| `tc.milliseconds == 1001` (29.97fps) | `tc.milliseconds_rounded == 1001` (gets 1001 via `round()`) — OR — `tc.milliseconds_exact == pytest.approx(1001.001, abs=1e-6)` for precision | Old code got 1001 via truncation; rounding may differ by ±1 at certain frames. Audit fractional-framerate `==` checks. |
| `int(tc.milliseconds)` | `tc.milliseconds_rounded` | Silences `DeprecationWarning`; semantically identical (V2 returns int already). |
| `time.sleep(tc.milliseconds / 1000)` | `time.sleep(tc.milliseconds_rounded / 1000)` | Same answer; integer-ms intent clearer. |
| polling: `while mtc.milliseconds < target` | polling: `while mtc.milliseconds_rounded < target` | Int comparison; no silent float contamination. |
| dict/set keyed on `tc.milliseconds` | `tc.milliseconds_rounded` | Float keys are fragile with equality. |
| precision-sensitive math (offset calc, scheduler, MTC bias) | `tc.milliseconds_exact` | Float, no precision loss. |

Run `python -W error::DeprecationWarning pytest tests/` to surface every remaining `.milliseconds` call-site as a hard failure during migration.

### Notes
- All public APIs other than `.milliseconds` itself are source-compatible. Engine and editor migrations land in cuems-engine PR #7 and cuems-editor PR #9 (separate ClickUp items in the 869cyndtv plan).
- The `return_in_other_framerate` method retains a `~5μs` per-call throwaway-construction cost that was deliberately not optimized — see the source docstring for the deferred fix sketch (Option D class-level cache) and revisit triggers.

## 0.1.0rc5 — 2026-04-22

### Added
- `settings.xsd` defines optional `<output_latency_ms>` on
  `AudioPlayerType`, `VideoPlayerType`, and `DmxPlayerType`.
  - Audio and video accept `AutoOrIntLatencyMsType` — a union of
    `xs:nonNegativeInteger` (maxInclusive=500) or the literal
    `"auto"`. Integer is an explicit override in ms; `"auto"` defers
    to the binary's built-in default (JACK query for audioplayer;
    hard-coded 33 ms for videocomposer).
  - Dmx accepts `IntLatencyMsType` (integer only) — no auto-measurement
    path exists for the DMX pipeline; `"auto"` is rejected at
    validation time to avoid implying magic that doesn't exist. Absent
    element defers to dmxplayer's hard-coded 35 ms default.
- Tests for the tri-state (int / `"auto"` / absent) round-trip and a
  negative test for `"auto"` on dmxplayer.

### Notes
- Schema change is strictly additive (`minOccurs="0"`); existing
  `settings.xml` files remain valid with no migration.
- Typing contract: `xmlschema.to_dict()` returns Python `int` for
  integer values and `str` for `"auto"`. `cuems-engine`'s NodeEngine
  arg-building relies on `isinstance(value, int)` to decide whether
  to emit the `--output-latency-ms` CLI flag to each player process.
