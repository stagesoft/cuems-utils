<!--
***
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
***
-->

# cuems-utils

**Current release: v0.1.0rc8** — see [CHANGELOG.md](./CHANGELOG.md).

**Shared data models, timecode utilities, XML tooling, and configuration primitives for the CueMS system.**

[![PyPI - Version](https://img.shields.io/pypi/v/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Deploy MkDocs site](https://github.com/stagesoft/cuems-utils/actions/workflows/gh-pages.yml/badge.svg)](https://github.com/stagesoft/cuems-utils/actions/workflows/gh-pages.yml)
[![Upload Python Package](https://github.com/stagesoft/cuems-utils/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/stagesoft/cuems-utils/actions/workflows/pypi-publish.yml)

* **Source / issues:** [stagesoft/cuems-utils](https://github.com/stagesoft/cuems-utils) on GitHub
* **API reference (HTML):** [stagesoft.github.io/cuems-utils](https://stagesoft.github.io/cuems-utils/)

`cuems-utils` is the shared library at the base of the **CueMS** (Cue Management System). It provides the data models, timecode primitives, XML tooling, and runtime configuration helpers consumed by every other component in the system — `cuems-engine`, `cuems-editor`, and their player subprocesses.

It is composed of:

* **`cuemsutils.cues`** — the full cue data model hierarchy (audio, video, DMX, fade, action) used by both the engine and the editor
* **`cuemsutils.tools`** — runtime utilities: timecode (`CTimecode`, `CTimecodeTimer`), fade calculation, NNG communications, systemd integration, configuration management
* **`cuemsutils.xml`** — XML schema validation, project-file serialization, and settings parsing built on `xmlschema` and `lxml`

---

## Overview

`cuems-utils` is a dependency, not a runtime. It defines the contract that all CueMS components share:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          cuems-utils                                │
│                                                                     │
│  cues/          tools/                  xml/                        │
│  ──────         ──────────────────      ──────────────────────      │
│  Cue            CTimecode               XmlReaderWriter             │
│  MediaCue       CTimecodeTimer          XmlBuilder                  │
│  AudioCue       FadeCalculator          Settings                    │
│  VideoCue       FadeProfile             CMLCuemsConverter           │
│  DmxCue         ConfigManager          (schemas/)                   │
│  FadeCue        CommunicatorServices    script.xsd                  │
│  ActionCue      HubServices             settings.xsd                │
│  CueList        SignalEngine            project_mappings.xsd        │
│  CuemsScript    CTimecodeTimer          network_map.xsd             │
│  CueOutput      Uuid, Logger, …                                     │
└─────────────────────────────────────────────────────────────────────┘
         ↓                    ↓
   cuems-engine          cuems-editor
```

* **Cue models** travel as serialized XML or JSON between the editor (authoring) and the engine (playback). Both sides parse and construct them through the same `CuemsScript` / `CueList` / `MediaCue` hierarchy defined here.
* **CTimecode** is the authoritative SMPTE timecode wrapper used for all scheduling, boundary evaluation, and MTC-to-millisecond conversion throughout the system.
* **XML tooling** validates project files against XSD schemas, reads and writes them, and exposes the decoded data as typed Python objects.
* **Configuration tools** (`ConfigManager`, `Settings`) abstract over `/etc/cuems/` paths, environment overrides, and settings.xml loading.

---

## Architecture

### Cues: `cues/`

The cue data model — the unit of show control. All classes are serializable to/from XML (via `XmlReaderWriter`) and JSON (via `CuemsScript.to_json()`).

* **`Cue`** — abstract base cue; owns `id`, `name`, `description`, `pre_wait`, `post_wait`, `enabled`, `ui_properties`.
* **`MediaCue`** — extends `Cue` with media file reference, `autoload`, and `CueOutput` list. Base for all media-playing cues.
* **`AudioCue`** — audio playback cue; owns JACK routing, level, and loop count. Contains MTC-polling loop using `.milliseconds_rounded` / `.milliseconds_exact`.
* **`VideoCue`** — video playback cue; canvas region routing (monitor alias or custom normalized-float rectangle), level. Uses `.milliseconds_rounded` for MTC polling.
* **`DmxCue`** — DMX playback cue; universe, channel, and level mapping. Offset calculations use `.milliseconds_exact` for drift-safe float math.
* **`FadeCue`** — fade action cue; owns `curve_type` (`FadeCurveType` enum: `linear`, `exponential`, `logarithmic`, `sigmoid`), `duration`, `target_value`. Inherits from `ActionCue`.
* **`ActionCue`** — action cue base; owns `action_type` and `action_target` (the id of the cue to act on).
* **`FadeProfile`** — reusable fade envelope data class; holds a named fade curve with amplitude samples.
* **`CueOutput`** — per-output routing descriptor on `MediaCue`. `VideoCueOutput` additionally carries an optional `canvas_region` (normalized `[0,1]` rectangle) for custom video placement.
* **`CueList`** — ordered list of cues; owns `get_next_cue`, `get_cue_by_id`, `get_media`, and `get_all_output_names`. Skips disabled cues in traversal.
* **`CuemsScript`** — top-level project model wrapping a `CueList`; owns `to_json()`, `get_media()`, and script-level metadata.

---

### Tools: `tools/`

Runtime utilities shared by all CueMS processes.

* **`CTimecode`** — SMPTE timecode wrapper over upstream `timecode` 1.5.1 with *playhead semantics*. At MTC position T, `.milliseconds_exact == T * 1000`. Key API:
  * `.milliseconds_exact: float` — exact precision; use for offset calc, scheduler, MTC-bias math.
  * `.milliseconds_rounded: int` — `round(milliseconds_exact)`; use for sleep durations, polling comparisons, dict/set keys.
  * `.milliseconds: int` — **deprecated**, alias of `.milliseconds_rounded`; removed at first stable release.
  * `.__str__` — monotonic past 24h (`"24:00:00:01"` rather than wrapping to `"00:00:00:01"`).
  * All arithmetic operators (`+`, `-`, `*`, `/`) raise `CTimecodeError` on cross-framerate operands.
  * `.framerate` returns canonical numeric types (`int` for SMPTE integer rates, `float` for fractional).

* **`CTimecodeTimer`** — quarter-frame timer that drives a callback at every quarter-frame boundary of a `CTimecode`. Accepts an optional immutable list of parameter tuples; stops automatically after the last tuple is consumed. Thread-safe state machine (`IDLE → RUNNING → STOPPED/EXHAUSTED`).

* **`FadeCalculator`** — stateless calculator that produces a `zip` of `(timecode, value)` pairs between `start_time` and `end_time` at quarter-frame resolution. Supports named fade functions (`linear`, `exponential`, `logarithmic`, `sigmoid`) or any callable. Unit: start/end are `CTimecode` instances; intermediate values are milliseconds (fixed division by 1000 after 0.1.0rc6 unit-error fix).

* **`ConfigManager`** — singleton that loads and caches `settings.xml`, `network_map.xml`, and `project_mappings.xml` from configurable paths. Exposes typed accessors (`get_video_output_id`, `get_nng_hub_port`, …). Conditional file loading at init — absent optional files are silently skipped.

* **`CommunicatorServices`** — NNG-based request/response communicator (wraps `pynng`). Exposes `NngRequestResponse` and `NngBusHub` for inter-process messaging between engine and node processes.

* **`HubServices`** — extends `CommunicatorServices` for fan-out to multiple dialer endpoints; used by the controller engine to broadcast to the node fleet.

* **`SignalEngine`** — systemd watchdog and notify wrapper (`systemd-python`). Used by long-running CueMS services to send `sd_notify(READY=1)` and periodic keepalive pings.

* **`StringSanitizer`** — input sanitization for user-supplied name strings.

* **`Uuid`** — UUID generation helper with a `CuemsDict`-compatible `__json__` hook.

* **`CopyMoveVersioned`** — atomic versioned file copy/move for project file management.

---

### XML: `xml/`

Project file I/O, validation, and settings loading, built on `xmlschema` 3.x and `lxml` 5.x.

* **`XmlReaderWriter`** — unified reader/writer for CueMS XML project files. Validates against the bundled XSD on read and write. Supersedes the deprecated `XmlReader` / `XmlWriter` split.
* **`XmlBuilder`** — low-level XML element construction from Python dicts; used internally by `XmlReaderWriter`.
* **`Settings`** — base class for XML-backed configuration files. `xmlschema.to_dict()` decodes to typed Python: `int` for integer elements, `str` for `"auto"`, `None` for absent optional elements.
* **`CMLCuemsConverter`** — converter from the legacy CML format to `CuemsScript` objects.
* **`Parsers`** — XML parsing helpers.

**Bundled schemas (`xml/schemas/`):**

| Schema | Validates |
|---|---|
| `script.xsd` | Project cuelists — full `CuemsScript` / `CueList` / cue hierarchy |
| `settings.xsd` | Node settings files (`/etc/cuems/settings.xml`) including player types, output latency, and `gradient_osc_port` |
| `project_mappings.xsd` | Output routing — node UUIDs, monitor aliases, and custom canvas templates |
| `network_map.xsd` | Node fleet topology |

---

### Root modules

* **`helpers`** — `format_timecode(value)` converts arbitrary values to canonical CTimecode string form. `ensure_items` validates required dict keys against a defaults spec.
* **`create_script`** — scripted `CuemsScript` factory that emits a schema-valid XML project file covering every cue subclass; used in script template creation and completeness integration tests.
* **`log`** — `Logger` wrapper that captures caller module and class name in every log record.
* **`timeoutloop`** — `TimeoutLoop` utility that runs a callable with a configurable deadline; raises on timeout.

---

## Core Concepts

* **CTimecode** — the authoritative temporal reference for all playback scheduling. Wraps upstream `timecode` 1.5.1 with *playhead semantics* and 24h-monotonic string representation.
* **Cue** — a discrete show event (audio, video, DMX, fade, or action) with pre/post-wait offsets, arming state, and output routing.
* **CuemsScript** — the top-level project model; a serializable tree of `CueList` and cues that travels between editor, engine, and nodes.
* **Canvas Region** — a normalized `[0,1]` rectangle (top-left origin) used to place video cues on a node canvas without referencing physical pixel coordinates. Distinct roles in `project_mappings.xsd` (UI template slot) and `script.xsd` (per-cue instance).
* **Settings** — the XML-backed runtime configuration for each node (`settings.xml`), including player binary paths, OSC ports, output latency overrides, and `gradient_osc_port`.

---

## Design Goals

* **Contract-first** — XSD schemas are the authoritative contract; Python models validate against them on read and write.
* **Playhead-semantic timecode** — at MTC position T, `CTimecode.milliseconds_exact == T * 1000`. Identical inputs produce identical scheduling across all framerates, including drop-frame.
* **Precision-explicit** — the `.milliseconds` precision split (`_exact` / `_rounded`) makes rounding intent visible at every call site.
* **Monotonic past 24h** — `CTimecode.__str__` and all accessors remain monotonic past 24h for installations with continuous MTC (museum/exhibit soak scenarios).
* **Embeddable** — `cuemsutils` is a pure-Python library with no process or network dependencies; it can be imported and driven programmatically in tests, scripts, or GUI applications.
* **TDD-disciplined** — every production code path is covered by tests; hypothesis property tests guard round-trip invariants.

---

## Installation

### PyPI

```bash
pip install cuemsutils
```

Optional extras:

```bash
pip install "cuemsutils[systemd]"   # systemd watchdog integration (linux only)
pip install "cuemsutils[all]"       # all optional dependencies
```

### Debian package

The `debian/bookworm` branch carries the packaging metadata for building a native `.deb`:

```bash
git clone --branch debian/bookworm https://github.com/stagesoft/cuems-utils.git
cd cuems-utils
dpkg-buildpackage -us -uc
sudo dpkg -i ../python3-cuemsutils_*.deb
```

The `cuems-engine` Debian package declares `cuems-utils` as a system dependency; installing `cuems-engine` via apt will pull in `cuemsutils` automatically.

---

## Development

### Prerequisites

* Python 3.11+ (managed via pyenv or system Python)
* [hatch](https://hatch.pypa.io/) for environment and test matrix management

### Editable install

```bash
# From the repo root
pip install -e ".[all]"
```

### Run tests

```bash
cd src
pytest
```

Useful invocations:

```bash
pytest -m "not slow"                          # skip long-running tests
pytest --cov=cuemsutils                       # with coverage report
pytest -W error::DeprecationWarning           # surface remaining .milliseconds call-sites
hatch test                                    # run full 3.11/3.12/3.13 matrix
hatch test --cover                            # matrix with coverage
```

### Code style

```bash
ruff check .
```

---

## Release notes

See [CHANGELOG.md](./CHANGELOG.md) for the full history.

### v0.1.0rc8 — 2026-05-20

Production call-site migration to `CTimecode` v2 API, deprecated method removal, and new `gradient_osc_port` settings field.

**Fixed**
- `AudioCue`, `VideoCue`, `DmxCue`: migrated remaining `.milliseconds` call-sites to `.milliseconds_rounded` (MTC polling loops) and `.milliseconds_exact` (drift-sensitive offset calculations). These three consumers still emitted `DeprecationWarning` at runtime after the 0.1.0rc6 library-level migration.

**Removed**
- `VideoCue.video_media_loop` — deprecated since 0.0.9rc5. Zero callers confirmed across cuems-engine, cuems-editor, and cuems-utils. Superseded by `loop_videoCue` in `cuems-engine`.

**Added**
- `gradient_osc_port` added as a required field on `NodeType` in `settings.xsd`. This is the UDP port `gradient-motiond` listens on for OSC commands from `GradientClient`. Propagated to `templates/settings.xml` and all test fixtures.

### v0.1.0rc7 — 2026-04-27

24h SMPTE rollover fix for `CTimecode.__str__` (closes ClickUp 869cpdbzy, Layer 1). `frames=2_160_002` at 25 fps now renders as `"24:00:00:01"` rather than wrapping to `"00:00:00:01"`. Layer 2 (MTC listener wrap detection) lives in `cuems-engine`.

### v0.1.0rc6 — 2026-04-27

`CTimecode` hardening pass (closes ClickUp 869cyndtv items #1–#7). Playhead-semantic `__init__`, correct arithmetic operators, `.milliseconds` precision split (`_exact` / `_rounded`), `framerate` canonical types, `FadeCalculator` ms-unit fix, `format_timecode +1` workaround removed.

### v0.1.0rc5 — 2026-04-22

`settings.xsd`: optional `output_latency_ms` on all three player types (`AudioPlayerType`, `VideoPlayerType`, `DmxPlayerType`). Strictly additive; existing `settings.xml` files remain valid.

### v0.1.0rc4

`FadeCue` class with XSD schema integration and full test suite. `FadeProfile` and `FadeCalculator` base. `CTimecodeTimer` quarter-frame timer. Canvas region (normalized `[0,1]` floats) for custom video placement.

### v0.1.0

First stable release. Python 3.13 compatibility. `localize_cue`, `get_video_output_id` rename, `nng_hub_port` settings field, `Logger` caller attribution.

---

## Copyright notice

Copyright © 2026 Stagelab Coop SCCL. Authors: Adrià Masip (`adria@stagelab.coop`) and Ion Reguera (`ion@stagelab.coop`).

This work is part of **cuems-utils**. It is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License** as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but **without any warranty**; without even the implied warranty of **merchantability** or **fitness for a particular purpose**. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see [https://www.gnu.org/licenses/](https://www.gnu.org/licenses/).

The SPDX short form of this notice is: `SPDX-License-Identifier: GPL-3.0-or-later`.

---

## License

This project is licensed under the terms of the **GNU General Public License v3.0 or later (GPL-3.0-or-later)**.

You are free to use, modify, and redistribute this software under the conditions set by the license. Any derivative work must also be distributed under the same license terms.

See the [LICENSE](./LICENSE) file for the full license text.

---

### Summary of Terms

* **Permissions**:

  * Use for any purpose
  * Study and modify the source code
  * Redistribute original or modified versions

* **Conditions**:

  * Source code must be made available when distributing
  * Modifications must be licensed under GPL v3 or later
  * Include a copy of the license and preserve notices

* **Limitations**:

  * Provided *without warranty*
  * No liability for damages or misuse

---
