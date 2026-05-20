# cuems-utils

**Shared data models, timecode utilities, XML tooling, and configuration primitives for the CueMS system.**

[![PyPI - Version](https://img.shields.io/pypi/v/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Tests](https://github.com/stagesoft/cuems-utils/actions/workflows/tests.yml/badge.svg)](https://github.com/stagesoft/cuems-utils/actions/workflows/tests.yml)
[![Coverage](https://codecov.io/gh/stagesoft/cuems-utils/graph/badge.svg)](https://codecov.io/gh/stagesoft/cuems-utils)

!!! note "Project README"
    For installation instructions, release history, and licensing, see the
    [project README](https://github.com/stagesoft/cuems-utils#readme) on GitHub.

---

## What is cuems-utils?

`cuems-utils` is the shared library at the base of the **CueMS** (Cue Management System).
It provides the data models, timecode primitives, XML tooling, and runtime configuration
helpers consumed by every other component in the system — `cuems-engine`, `cuems-editor`,
and their player subprocesses.

The library is organized into three submodules plus a small set of root-level utilities:

| Submodule | Role |
|---|---|
| `cues/` | The full cue data-model hierarchy (audio, video, DMX, fade, action) |
| `tools/` | Runtime utilities: timecode, fade calculation, NNG communications, systemd integration, configuration management |
| `xml/` | XML schema validation, project-file serialization, and settings parsing |

---

## How data flows through the system

```
Editor (authoring)
    │
    │  CuemsScript (JSON / XML)
    ▼
cuems-utils ──► XmlReaderWriter ──► schema validation ──► CuemsScript / CueList / Cue objects
    │
    │  shared via pip / deb dependency
    ▼
cuems-engine (runtime)
    │
    │  CTimecode (MTC position)
    │  ConfigManager (settings.xml)
    │  CommunicatorServices (NNG)
    ▼
Node Engine ──► Player subprocesses (audio, video, DMX)
```

`cuems-utils` never runs as a daemon. It is a pure-Python import — processes that need the
data models or utilities add it as a dependency and import the relevant classes.

---

## Architecture

### Cues layer

[`cues/`](cues.md) — the unit of show control. All classes serialize to/from XML and JSON.

- **`Cue`** — abstract base; owns `id`, `name`, `pre_wait`, `post_wait`, `enabled`, `ui_properties`.
- **`MediaCue`** — extends `Cue` with a media file reference, `autoload`, and a `CueOutput` list.
- **`AudioCue`** — audio playback cue; JACK routing, level, loop count. MTC-polling uses `.milliseconds_rounded` / `.milliseconds_exact`.
- **`VideoCue`** — video playback cue; monitor alias or normalized-float canvas region. MTC-polling uses `.milliseconds_rounded`.
- **`DmxCue`** — DMX playback cue; universe, channel, and level mapping. Offset math uses `.milliseconds_exact` for drift safety.
- **`FadeCue`** — fade action cue; `curve_type` (`linear`, `exponential`, `logarithmic`, `sigmoid`), `duration`, `target_value`. Inherits `ActionCue`.
- **`ActionCue`** — action cue base; `action_type` and `action_target` (id of the cue to act on).
- **`FadeProfile`** — reusable fade envelope data class with named curve and amplitude samples.
- **`CueOutput`** — per-output routing descriptor. `VideoCueOutput` additionally carries an optional `canvas_region` (normalized `[0,1]` rectangle).
- **`CueList`** — ordered cue container; owns `get_next_cue`, `get_cue_by_id`, `get_media`. Skips disabled cues in traversal.
- **`CuemsScript`** — top-level project model; wraps a `CueList` with script-level metadata and a `to_json()` serializer.

### Tools layer

[`tools/`](tools.md) — runtime utilities shared by all CueMS processes.

- **`CTimecode`** — SMPTE timecode wrapper with *playhead semantics*. At MTC position T,
  `.milliseconds_exact == T * 1000`. Monotonic past 24 h (`"24:00:00:01"` rather than
  wrapping). Arithmetic operators raise `CTimecodeError` on cross-framerate operands.
  The `.milliseconds` / `.milliseconds_exact` / `.milliseconds_rounded` precision split
  makes rounding intent visible at every call site.
- **`CTimecodeTimer`** — quarter-frame timer that fires a callback at every quarter-frame
  boundary. Thread-safe state machine (`IDLE → RUNNING → STOPPED/EXHAUSTED`); accepts
  an optional parameter-tuple list and stops automatically when exhausted.
- **`FadeCalculator`** — stateless calculator producing `(timecode, value)` pairs between
  two `CTimecode` endpoints at quarter-frame resolution. Supports named curve names or
  any callable; correct unit handling (`start_seconds = ms / 1000`) after the 0.1.0rc6
  unit-error fix.
- **`ConfigManager`** — singleton loader for `settings.xml`, `network_map.xml`, and
  `project_mappings.xml`. Conditional file loading at init; typed accessors.
- **`CommunicatorServices`** — NNG request/response and bus-hub transport wrappers
  (`NngRequestResponse`, `NngBusHub`).
- **`HubServices`** — fan-out to multiple dialer endpoints; used by the controller engine.
- **`SignalEngine`** — systemd `sd_notify` and watchdog keepalive wrapper.
- **`Uuid`**, **`StringSanitizer`**, **`CopyMoveVersioned`** — UUID generation, input
  sanitization, and atomic versioned file management.

### XML layer

[`xml/`](xml.md) — project file I/O, validation, and settings loading.

- **`XmlReaderWriter`** — validates against bundled XSD on read and write; supersedes the
  deprecated `XmlReader` / `XmlWriter` pair.
- **`XmlBuilder`** — low-level element construction from Python dicts.
- **`Settings`** — base class for XML-backed config; `xmlschema.to_dict()` returns `int`
  for integer elements, `str` for `"auto"`, `None` for absent optional elements.
- **`CMLCuemsConverter`** — converts legacy CML project files to `CuemsScript`.
- **`Parsers`** — XML parsing helpers.

**Bundled schemas (`xml/schemas/`):**

| Schema | Validates |
|---|---|
| `script.xsd` | Full project cuelists — `CuemsScript` / `CueList` / all cue types |
| `settings.xsd` | Per-node settings including player types, `output_latency_ms`, and `gradient_osc_port` |
| `project_mappings.xsd` | Output routing — node UUIDs, monitor aliases, custom canvas templates |
| `network_map.xsd` | Node fleet topology |

---

## Key design decisions

### Playhead-semantic timecode

Upstream `timecode` 1.5.1 ships *exposure-window* semantics — `00:00:00:00` is the
end of the first frame's exposure window, not the start. cuems-utils overrides `__init__`
to route `start_seconds=` through `tc_to_frames` (via an HMSF string), which applies
drop-frame correction at 29.97/59.94 DF. The result: at any MTC position T,
`CTimecode(start_seconds=T).milliseconds_exact == T * 1000`.

### Precision split (`.milliseconds_exact` / `.milliseconds_rounded`)

The original `.milliseconds: int` truncated via `int()`, losing up to 1 ms per call at
fractional framerates and accumulating monotonically in long-running installations. The v2
API splits this into two explicit accessors — the deprecated `.milliseconds` is retained
as an alias and will be removed at the first stable release. Migration guide:

| Old | New | Reason |
|---|---|---|
| `tc.milliseconds == 30000` | `tc.milliseconds_rounded == 30000` | Integer comparison, rounding intent clear |
| `time.sleep(tc.milliseconds / 1000)` | `time.sleep(tc.milliseconds_rounded / 1000)` | Integer sleep duration |
| `while mtc.milliseconds < target` | `while mtc.milliseconds_rounded < target` | Polling loop, int comparison |
| Offset / scheduler / MTC-bias math | `tc.milliseconds_exact` | Float, no precision loss |

### Monotonic 24h timecode for long-running installs

Museum and exhibit installations may run more than 24 h on a single MTC timeline.
Upstream's `frames_to_tc` applies `% frames_per_24h` when rendering, causing `__str__`
to wrap from `"23:59:59:24"` back to `"00:00:00:00"`. `CTimecode.__str__` passes
`skip_rollover=True` to keep the string representation monotonic past 24 h.
Layer 2 (MTC listener wrap detection and hour-offset accumulation on MIDI input)
lives in `cuems-engine`.

### Canvas region: two distinct roles

`canvas_region` in `project_mappings.xsd` is a **UI template slot** — it marks a node
output entry as a custom slot that the editor lists alongside monitor aliases and uses as
a default rect when the user places a cue. `canvas_region` in `script.xsd`
(`VideoCueOutput`) is the **per-cue instance** rect the user drew. The two elements share
the same `CanvasRegionType` XSD definition but have distinct semantics; see
[Canvas Region](canvas_region.md) for the full specification.

### XSD as authoritative contract

Python validation is secondary to the XSD. `XmlReaderWriter` validates against the
bundled schema on every read and write. Schema changes require corresponding Python model
changes in the same commit (the `settings.xml` template and `settings.xsd` live here
for exactly this reason).

---

## API reference

Each module's public API is generated directly from docstrings:

- [Cues](cues.md) — `Cue`, `MediaCue`, `AudioCue`, `VideoCue`, `DmxCue`, `FadeCue`, `ActionCue`, `FadeProfile`, `CueOutput`, `CueList`, `CuemsScript`
- [Tools](tools.md) — `CTimecode`, `CTimecodeTimer`, `FadeCalculator`, `ConfigManager`, `CommunicatorServices`, `HubServices`, `SignalEngine`, `Uuid`
- [XML](xml.md) — `XmlReaderWriter`, `XmlBuilder`, `Settings`, `CMLCuemsConverter`, `Parsers`
- [API (root modules)](api.md) — `create_script`, `helpers`, `log`, `timeoutloop`
- [Canvas Region](canvas_region.md) — coordinate model, validation rules, V1 caps, and deferred work
