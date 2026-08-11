# Changelog

## Unreleased — schema-derived XML serialization core (feature 004)

Replaces four independent implementations of the same mapping rules with one engine driven
by a field specification derived from the XSD. **Observable behaviour does not change**:
written XML and the read dict stay byte-identical, and every pre-existing consumer import
keeps working behind a deprecation shim — with one declared exception, below.

### ⚠️ Breaking — `cuems-nodeconf` handler injection is no longer consulted

`cuems-nodeconf` registers its node handlers by assigning into this library's private
module namespaces (`NodeXmlBuilders.py:105-111`):

```python
XmlBuilderModule.nodeXmlBuilder = nodeXmlBuilder
ParsersModule.nodeParser        = nodeParser
```

`CuemsParser.get_parser_class` and `XmlBuilder.get_builder_class` used to resolve handlers
through `globals()` of their own module, so an injected name was found. Every path now
routes through an explicit registry, and **an injected name is never consulted**.

Note what does *not* break: the imports still resolve and the assignments still execute
without error. Only their effect is gone — the node serializes through a generic instead of
through `nodeXmlBuilder`, silently. That is why the break is pinned by a test
(`tests/contract/test_declared_break_nodeconf.py`) rather than left to be noticed.

No shim can preserve it: honouring an injected name means keeping the implicit `globals()`
lookup that the explicit registry exists to delete.

- **Affected consumer**: `cuems-nodeconf` only. `cuems-editor` and `cuems-engine` need no
  change at this release.
- **The fix is carried by feature 007**, not by this release. It must target an API that is
  internal here, becomes public in feature 006, and absorbs the node model in 007 — written
  now it would be rewritten twice. `cuems-nodeconf` is not shipping against this release.
- **Details**: `specs/004-xml-serialization-core/migration-map.md` §3.

### Deprecated

All of the following keep working and will be **removed in `v0.1.1`**. Importing is silent;
each *call* warns, at the caller's line, naming its replacement. Full table with consumer
call sites: `specs/004-xml-serialization-core/migration-map.md`.

- `cuemsutils.xml.XmlReaderWriter` → `cuemsutils.xml.xml_reader_writer` (the module was
  renamed to snake_case; the class name is unchanged).
- `cuemsutils.xml.Settings` → `cuemsutils.xml.settings`.
- `cuemsutils.xml.Parsers` — the `*Parser` family, `GenericParser`, `GenericDict`,
  `CuemsParser.str_to_value` and `STRING_TYPED_KEYS`.
- `cuemsutils.xml.XmlBuilder` — the `*XmlBuilder` family and `VALUE_TYPES`.

Imports through the **package root** are unaffected and need no change:
`from cuemsutils.xml import XmlReaderWriter, Settings, NetworkMap, ProjectMappings,
ProjectSettings`. Most consumer code falls in this category.

`CuemsParser` itself is **not** deprecated — it becomes the engine's delegating facade and
remains a supported entry point. Its `str_to_value` method is deprecated; the class is not.

`STRING_TYPED_KEYS` and `VALUE_TYPES` are deprecated but **cannot warn**: both are values
read in membership checks, never called, so there is no call for a warning to attach to.

### Changed — the one intentional, non-breaking behaviour difference

Log output. This feature guarantees byte-identical XML and byte-identical read dicts; log
records are explicitly outside that guarantee.

- INFO is now declared at the level of **XML file access** (read, write, validate). Element
  construction and per-cue work drop to DEBUG, so the record count scales with files
  touched rather than with cues — a 1000-cue script no longer emits a thousand INFO lines.
- No record at any level carries a field value or an object repr. As a side effect, show
  content — cue names, file paths — no longer appears in log files.

### Notes

- Element order for order-free (`xs:all`) content models is derived as **arrival order**,
  which is what the current builder produces. An earlier draft specified sorted keys; the
  goldens showed that two of four captured `CuemsScript` roots are not sorted, so a sorted
  rule would have rewritten the root element of every hand-authored script. See FR-001b.
- Two schema defects are recorded and deferred, not fixed: `outputs.xsd` declares an
  `OutputsType` that collides with `script.xsd`'s, and the only `outputs.xml` in existence
  has a namespace missing its trailing slash — between them, nothing has ever validated
  against `outputs.xsd`.
- `gradient_osc_port` was added to `NodeType` as *required* in 0.1.0rc8, which invalidated
  every settings file written before it — including two this project shipped. Recorded as
  X13; the fix is scheduled under feature 006's schema-evolution convention.

## 0.1.0rc11 — 2026-07-28

Free-text fields are no longer type-coerced during parsing (closes ClickUp 869cqbpxa).

### Fixed
- `CuemsParser.str_to_value` no longer coerces values whose key names a string-typed field. It previously ran every scalar through `int` → `float` → `strtobool` → `Uuid` regardless of key, so free text was silently rewritten. Because `strtobool` accepts the truth abbreviations, a cue named `n`/`N`/`f`/`F` was persisted as `False`, `y`/`Y`/`t`/`T` as `True`, and any bare digit as an `int` — 18 of the 62 alphanumeric single characters were corrupted, along with the words `yes`/`no`/`true`/`false`/`on`/`off`. Sergio reported the symptom as "can't name a cue with a single letter"; there was never a length rule, the failing characters were exactly `strtobool`'s vocabulary. The affected keys reachable in practice are `name`, `description` and `file_name`.
- A cue named lowercase `none` or `null` hit the `['none', 'null', '']` → `None` branch, serialised to `<name/>`, and failed `NameStringType`'s `minLength=1` — a hard `XMLSchemaValidationError` at save time rather than silent corruption. The new short-circuit precedes that branch, so both failure modes are fixed together.

### Added
- `STRING_TYPED_KEYS` in `xml/Parsers.py` — the set of keys exempt from coercion. `name`, `description` and `file_name` are the ones reachable today; `output_name`, `parameter_name`, `icon`, `color` and `unix_name` are defensive entries, currently shielded by unrelated bypasses in `outputsParser`, `_normalize_fade_parameters` and the `GenericDict` fallback, listed so that fixing any of those bypasses cannot silently reintroduce this bug.
- `str_to_value` takes an optional `key` argument, threaded through all four call sites (`CuemsScriptParser`, `CueListParser`, `GenericParser`, `fade_profileParser`). The argument is optional, so existing single-argument callers are unaffected.
- `tests/test_name_coercion.py` — exhaustive sweep over all 62 alphanumeric single characters for each reachable key, the boolean/nullish word set, a full XML round-trip, and negative tests pinning that `enabled`/`autoload`/`timecode`/`loop` still coerce and that `id` still parses to a `Uuid`.

### Notes
- `id` is deliberately **not** in the allowlist: the `Uuid()` branch inside `str_to_value` is the only thing that produces `Uuid` objects on parse (the parsers assign via raw `dict.__setitem__` and never reach the property setters), so adding it would downgrade every cue, script and media id to a plain `str`. The consequence is that `DmxSceneType.id` (`script.xsd:403`, declared `xs:string`) cannot be protected by this mechanism — accepted, since DMX scene ids are system-assigned rather than operator-typed.
- Projects saved before this release have the corrupted name baked into their `cue_script.xml`; the original text is unrecoverable (`n`, `no`, `N`, `off` all collapse to `False`) and must be renamed by hand.
- `cuems-nodeconf` calls the inherited `str_to_value` without a key (`NodeXmlBuilders.py:80`), so node names remain exposed to the identical bug. Tracked separately.

## 0.1.0rc8 — 2026-05-20

Production call-site migration to the `CTimecode` v2 API, removal of a long-deprecated method, and a new required settings field for `gradient-motiond` integration.

### Fixed
- `AudioCue`, `VideoCue`, `DmxCue`: migrated three remaining `.milliseconds` call-sites to the v2 API. `AudioCue.py:100` and `VideoCue.py:84` polling loops now use `.milliseconds_rounded` (int comparison, no silent float contamination). `AudioCue.py:106` and `DmxCue.py:195` offset calculations now use `.milliseconds_exact` (float, precision-sensitive). These production consumers still emitted `DeprecationWarning` at runtime even after 0.1.0rc6 completed the library-level migration.

### Removed
- `VideoCue.video_media_loop` — deprecated since 0.0.9rc5 (`"Use loop_cue from CueHandler instead"`). Confirmed zero callers across cuems-engine, cuems-editor, and cuems-utils. Superseded by `loop_videoCue` in `cuems-engine/cues/loop_cue.py`. Also drops now-unused imports `time.sleep` and `deprecated.deprecated` from `VideoCue.py`.

### Added
- `gradient_osc_port` element added as a required field on `NodeType` in `settings.xsd`. This is the UDP port number that `gradient-motiond` listens on for incoming OSC commands; the engine's `GradientClient` reads it from `ConfigManager` when building the datagram endpoint. The field is propagated to `templates/settings.xml` (with a placeholder value and operator guidance) and all test XML fixtures so schema validation stays aligned.

### Notes
- After this release, `python -W error::DeprecationWarning pytest tests/` should produce zero `DeprecationWarning` from `.milliseconds` in the cuems-utils test suite. Run it before merging any future change that touches `CTimecode` consumers.

## 0.1.0rc7 — 2026-04-27

24h SMPTE rollover fix (closes ClickUp 869cpdbzy). Layer 1 of a two-layer fix; Layer 2 lives in cuems-engine's MtcListener (PR #10 there).

### Fixed
- `CTimecode.__str__` now passes `skip_rollover=True` to upstream's `frames_to_tc`, keeping the string representation monotonic past 24h. `frames=2_160_002` at 25fps now renders as `"24:00:00:01"` instead of wrapping to `"00:00:00:01"`. Sergio reported the symptom: long-running install (>24h continuous MTC) where audio cues + sequence stop while video keeps looping. The underlying `.frames`, `.milliseconds_exact`, and `.milliseconds_rounded` accessors were already monotonic post-`0.1.0rc6` (PR #6) — this completes the coverage so any consumer that round-trips through `str()` also stays correct.

### Added
- `TestRollover` class in `tests/unit/test_ctimecode.py` pinning the 24h-immune contract: `.milliseconds_exact`/`.milliseconds_rounded` monotonic at the boundary, `__add__` advances correctly across 24h, `__str__` shows `24:00:00:01`, the loop-rebase pattern from `loop_cue.py:107,224` survives 5+ iterations past 24h, polling comparisons (`<`) work past the boundary.

### Notes
- Implementation is one method override (`__str__`) — well below the escalation trigger from the 869cyndtv plan (>2-3 upstream method overrides would have signalled "self-maintain CTimecode" instead). The `frames_to_tc` itself is left untouched (it's used internally by upstream's `next_frame_str` and rate accessors with `skip_rollover=True` already where needed).
- Layer 2 (cuems-engine MtcListener wrap detection + 24h offset accumulation) is required to fully close 869cpdbzy: MIDI MTC encodes hours in a 5-bit field (max 23) and real SMPTE senders reset to `00:00:00:00` after 24h, so the listener must detect the wrap and accumulate offset before constructing CTimecodes. Without Layer 2, `mtc.main_tc` resets to ~frames=1 every 24h regardless of CTimecode's internal monotonicity.

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
