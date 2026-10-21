<!--
***
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
***
-->

# cuems-utils

**Next release: v0.1.1** (unreleased; the first stable release) — see [CHANGELOG.md](./CHANGELOG.md).

**Shared data models, timecode utilities, XML tooling, and configuration primitives for the CueMS system.**

[![PyPI - Version](https://img.shields.io/pypi/v/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cuemsutils.svg)](https://pypi.org/project/cuemsutils)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Tests](https://github.com/stagesoft/cuems-utils/actions/workflows/tests.yml/badge.svg)](https://github.com/stagesoft/cuems-utils/actions/workflows/tests.yml)
[![codecov](https://codecov.io/gh/stagesoft/cuems-utils/graph/badge.svg?token=GFR1L3S807)](https://codecov.io/gh/stagesoft/cuems-utils)
[![Deploy MkDocs site](https://github.com/stagesoft/cuems-utils/actions/workflows/gh-pages.yml/badge.svg)](https://github.com/stagesoft/cuems-utils/actions/workflows/gh-pages.yml)
[![Upload Python Package](https://github.com/stagesoft/cuems-utils/actions/workflows/pypi-publish.yml/badge.svg)](https://github.com/stagesoft/cuems-utils/actions/workflows/pypi-publish.yml)

* **Source / issues:** [stagesoft/cuems-utils](https://github.com/stagesoft/cuems-utils) on GitHub
* **API reference (HTML):** [stagesoft.github.io/cuems-utils](https://stagesoft.github.io/cuems-utils/)

`cuems-utils` is the shared library at the base of the **CueMS** (Cue Management System). It provides the data models, timecode primitives, XML tooling, and runtime configuration helpers consumed by every other component in the system — `cuems-engine`, `cuems-editor`, and their player subprocesses.

It is composed of:

* **`cuemsutils.cues`** — the full cue data model hierarchy (audio, video, DMX, fade, action) used by both the engine and the editor
* **`cuemsutils.tools`** — runtime utilities: timecode (`CTimecode`, `CTimecodeTimer`), fade calculation, NNG communications, systemd integration, configuration management
* **`cuemsutils.errors`** — the one public error and report module (`SchemaError`, `ValidationError`, `IngestError`, `LoadReport`, …)
* the bundled **XSD schemas** and three console tools (`cuems-convert-documents`, `cuems-reshape-devices`, `cuems-init-node`). `cuemsutils.xml` is internal and exports nothing; documents are read and written through `CuemsScript` and `ConfigManager`

---

## Overview

`cuems-utils` is a dependency, not a runtime. It defines the contract that all CueMS components share:

```text
┌─────────────────────────────────────────────────────────────────────┐
│                          cuems-utils                                │
│                                                                     │
│  cues/          tools/                  schemas/  (+ errors)        │
│  ──────         ──────────────────      ──────────────────────      │
│  Cue            CTimecode               script.xsd                  │
│  MediaCue       CTimecodeTimer          settings.xsd                │
│  AudioCue       FadeCalculator          network_map.xsd             │
│  VideoCue       ConfigManager           project_mappings.xsd        │
│  DmxCue         NodeList (NodeIndex)    project_settings.xsd        │
│  FadeCue        CommunicatorServices    hardware_outputs.xsd        │
│  ActionCue      HubServices                                         │
│  CueList        SignalEngine            cuemsutils.errors           │
│  CuemsScript    Uuid, Logger, …         (LoadReport, SchemaError…)  │
│  CueOutput                                                          │
└─────────────────────────────────────────────────────────────────────┘
         ↓                    ↓
   cuems-engine          cuems-editor
```

* **Cue models** travel as serialized XML or JSON between the editor (authoring) and the engine (playback). Both sides parse and construct them through the same `CuemsScript` / `CueList` / `MediaCue` hierarchy defined here.
* **CTimecode** is the authoritative SMPTE timecode wrapper used for all scheduling, boundary evaluation, and MTC-to-millisecond conversion throughout the system.
* **Documents** are read and written through the public object API: `CuemsScript.load` / `save` for a show, `ConfigManager` for a node's configuration. Every read validates the schema (T1) and the semantic rules (T2), converts a version-old document in memory, and reports what it did.
* **Configuration** (`ConfigManager`) abstracts over `/etc/cuems/` paths (`CUEMS_CONF_PATH`), and loads and saves `settings.xml`, `network_map.xml` and the project documents as objects.

---

## Architecture

### Cues: `cues/`

The cue data model — the unit of show control. A show is read and written as XML through `CuemsScript.load` / `save`, and as JSON through `to_json` / `from_json`.

* **`Cue`** — abstract base cue; owns `id`, `name`, `description`, `pre_wait`, `post_wait`, `enabled`, `ui_properties`.
* **`MediaCue`** — extends `Cue` with media file reference, `autoload`, and `CueOutput` list. Base for all media-playing cues.
* **`AudioCue`** — audio playback cue; owns JACK routing, level, and loop count. Contains MTC-polling loop using `.milliseconds_rounded` / `.milliseconds_exact`.
* **`VideoCue`** — video playback cue; canvas region routing (monitor alias or custom normalized-float rectangle), level. Uses `.milliseconds_rounded` for MTC polling.
* **`DmxCue`** — DMX playback cue; universe, channel, and level mapping. Offset calculations use `.milliseconds_exact` for drift-safe float math.
* **`FadeCue`** — fade action cue; owns `curve_type` (`FadeCurveType` enum: `linear`, `exponential`, `logarithmic`, `sigmoid`, `ease_in`, `ease_out`), `duration`, `target_value`. Inherits from `ActionCue`.
* **`ActionCue`** — action cue base; owns `action_type` and `action_target` (the id of the cue to act on). `stop_project`, the authored end of an unattended show, acts on the whole project and takes no target.
* **`CueOutput`** — per-output routing descriptor on `MediaCue`. `VideoCueOutput` additionally carries an optional `canvas_region` (normalized `[0,1]` rectangle) for custom video placement.
* **`CueList`** — ordered list of cues; owns `get_next_cue`, `get_cue_by_id`, `get_media`, and `get_all_output_names`. Skips disabled cues in traversal.
* **`CuemsScript`** — top-level project model wrapping a `CueList`. The public entry points: `CuemsScript.load(path)`, `CuemsScript.load_with_report(path)` (returns the script and a `LoadReport`), `script.save(path)` (validates, then writes atomically), `script.validate()`, `CuemsScript.from_json(payload)`, `script.to_json()` and `script.to_wire()`.

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

* **`ConfigManager`** — loads and caches a node's configuration (`settings.xml`, `network_map.xml`, `project_mappings.xml`, `project_settings.xml`) from `CUEMS_CONF_PATH` (default `/etc/cuems`), answering with objects (`load_*`), and writes them back (`save_settings`, `save_network_map`, `save_project_mappings`, `save_project_settings`). `ConfigManager.from_json(schema, payload)` builds a configuration document from JSON, `to_wire(section)` projects one, and `get_schema_descriptor()` describes every schema for a UI. `cuemsutils.tools.validate_config_document(path)` validates one without an installation.

* **`CommunicatorServices`** — NNG-based request/response communicator (wraps `pynng`). Exposes `NngRequestResponse` and `NngBusHub` for inter-process messaging between engine and node processes.

* **`HubServices`** — extends `CommunicatorServices` for fan-out to multiple dialer endpoints; used by the controller engine to broadcast to the node fleet.

* **`SignalEngine`** — systemd watchdog and notify wrapper (`systemd-python`). Used by long-running CueMS services to send `sd_notify(READY=1)` and periodic keepalive pings.

* **`StringSanitizer`** — input sanitization for user-supplied name strings.

* **`Uuid`** — UUID generation helper with a `CuemsDict`-compatible `__json__` hook.

* **`CopyMoveVersioned`** — atomic versioned file copy/move for project file management.

* **`TimeoutLoop`** — iterator-based bounded polling loop; raises `TimeoutError` once elapsed time exceeds `timeout`. Formerly `timeoutloop.Timeoutloop` at the package root; that path still resolves but is deprecated (removed in `v0.1.2`).

---

### Documents: the public object API, the schemas and the tools

`cuemsutils.xml` is internal and exports nothing. Read and write documents through the objects:

```python
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import SchemaError, ValidationError

script, report = CuemsScript.load_with_report("project/script.xml")
print(report.outcome)            # Outcome.CLEAN, CONVERTED or REPAIRED; report.repairs says what
script.save("project/script.xml")  # T1 + T2 first; nothing is written if either fails
```

* **Every read is strict.** The schema (T1) and the semantic rules (T2) run on every load. A
  version-old document is converted **in memory** (the file is untouched). A repairable violation is
  repaired to the field's declared default and reported. An unrepairable one raises
  `ValidationError`, and a structural one raises `SchemaError`.
* **Every write validates first** and replaces the file atomically.
* The deprecated `XmlReaderWriter`, `XmlBuilder` and `Parsers` still import in `0.1.1`, with a
  warning, and are **removed in `v0.1.2`**.

**Bundled schemas (`src/cuemsutils/xml/schemas/`, installed to `/usr/share/cuems/schemas/`):**

| Schema | Validates |
|---|---|
| `script.xsd` | A show: `CuemsScript` / `CueList` / cue hierarchy |
| `settings.xsd` | A node's settings (`/etc/cuems/settings.xml`): players, OSC ports (including `gradient_osc_port` on `NodeConfType`), output latency |
| `network_map.xsd` | The node fleet: identities, roles (`controller` / `node` / `firstrun`), adoption |
| `project_mappings.xsd` | Output routing: devices by class, monitor aliases, custom canvas templates |
| `project_settings.xsd` | Per-project settings |
| `hardware_outputs.xsd` | A node's hardware outputs |

**Console tools** (installed into the shared venv and `/usr/bin`):

* `cuems-reshape-devices` — rewrites documents in the pre-013 device shape into the current one (backup first).
* `cuems-convert-documents` — upgrades version-old documents to the current schema version (backup first). Run it **after** `cuems-reshape-devices`.
* `cuems-init-node` — provisions a node's identity and its three configuration documents.

Both migration tools report every document the loader would refuse after they wrote it, and accept `--check`.

---

### Root modules

* **`helpers`** — `format_timecode(value)` converts arbitrary values to canonical CTimecode string form. `ensure_items` validates required dict keys against a defaults spec.
* **`log`** — `Logger` wrapper that captures caller module and class name in every log record.

---

## Core Concepts

* **CTimecode** — the authoritative temporal reference for all playback scheduling. Wraps upstream `timecode` 1.5.1 with *playhead semantics* and 24h-monotonic string representation.
* **Cue** — a discrete show event (audio, video, DMX, fade, or action) with pre/post-wait offsets, arming state, and output routing.
* **CuemsScript** — the top-level project model; a serializable tree of `CueList` and cues that travels between editor, engine, and nodes.
* **Canvas Region** — a normalized `[0,1]` rectangle (top-left origin) used to place video cues on a node canvas without referencing physical pixel coordinates. Distinct roles in `project_mappings.xsd` (UI template slot) and `script.xsd` (per-cue instance).
* **Settings** — the runtime configuration of each node (`settings.xml`): player binary paths, OSC ports, output latency overrides and `gradient_osc_port`. Read and written through `ConfigManager`.

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

The package is `cuems-utils`, built from `debian/` on the working branch, inside a bookworm
environment (the venv's interpreter must be bookworm's `/usr/bin/python3`):

```bash
dpkg-buildpackage -us -uc -b
sudo dpkg -i ../cuems-utils_*.deb
```

It installs the library into the shared venv `/usr/lib/cuems`, the schemas into
`/usr/share/cuems/schemas`, and, on first install, the node's documents into `/etc/cuems`.
`cuems-engine`, `cuems-editor` and the other CueMS packages depend on it.

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
uvx hatch run test.py3.11:run -- -q     # the suite on 3.11 (as CI gates)
```

Useful invocations:

```bash
pytest -m "not slow"                          # skip long-running tests
pytest --cov=cuemsutils                       # with coverage report
pytest -W error::DeprecationWarning           # surface remaining .milliseconds call-sites
uvx hatch run test:run -- -q                  # the 3.11/3.12/3.13 matrix
uvx hatch run test:run-cov                    # with coverage
```

### Code style

```bash
ruff check .
```

---

## Release notes

See [CHANGELOG.md](./CHANGELOG.md) for every release from `0.1.0rc5` on, and git tags and PyPI
for the earlier ones.

**v0.1.1** (unreleased) is the first stable release:
* one public object API (`CuemsScript`, `ConfigManager`, `cuemsutils.errors`);
* strict, reporting reads, with versioned documents;
* the device-class document shape;
* `xs:boolean`;
* uuid4 node identities;
* `/etc/cuems` first install.

It also absorbs everything the release line shipped up to `0.1.0rc17`.

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
