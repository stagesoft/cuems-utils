<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract — the public surface after 013

**Feature**: `013-device-class-reshape` | **Requirements**: FR-011, FR-012, FR-035, FR-036, FR-042,
FR-050a, FR-052 | **Golden**: `tests/golden/api/public_api.json` changes by exactly three names (SC-016):
`partition_by_adoption`, `validate_config_document`, and the console script
`cuems-reshape-devices`

Three kinds of change: one shape that moves, two names that are published, and a long list of things
that deliberately do not move.

---

## 1. `ConfigManager.node_hw_outputs` — derived, with `[]` for an absent class

```python
cm = ConfigManager()
cm.node_hw_outputs["video_outputs"]   # -> list, as today
cm.node_hw_outputs["audio"]           # -> [] for a class this node does not carry (FR-012)
```

The value is a `dict` subclass whose `__missing__` returns `[]` (research R11). This satisfies three
requirements at once: the keys come from the document rather than from a declared triple (FR-011), the
three legacy spellings keep answering (A4), and `NodeEngine.py:566`'s unguarded subscript keeps working
(FR-012, R10).

**`__missing__` answers only for a well-formed class key.** A typo is still a `KeyError` — a silent
`[]` for `"vdieo"` is the failure mode FR-012 is trying to avoid, not the one it is buying.

## 2. `node_mappings` and `node_conf` keep their legacy keys, derived

| Call | After |
|---|---|
| `node_mappings["audio"]` (`NodeEngine.py:508,598`) | answers, derived from `devices` (FR-012a, D1, R10) |
| `node_conf["videoplayer"]`, `["audioplayer"]`, `["dmxplayer"]` (six engine sites) | answer, derived from `players` (FR-042) |
| `node_conf["audiomixer"]` | untouched — it has no device class (FR-040a) |
| `mappings["default_video_output"]` and its five siblings | answer, derived from `defaults` |

Each of these is a **compatibility surface with an end date**, named in the migration guide with the
new access beside it. They exist so that 013 can land without a same-day consumer release, not as the
permanent interface.

**Not shieldable, and the guide says so**: `cuems-common`'s three XPath readers (R7) address the files
on disk. One of them exits 0 having written an empty flag (`cuems-extract-video-latency:39`), one
computes a wrong display configuration (`cuems-generate-display-conf:66-84`), and one raises via
`sys.exit` (`cuems-display-setup:527-571`). No library-side shim reaches any of them.

## 3. `partition_by_adoption`, published (FR-035)

```python
from cuemsutils.tools.NodeList import partition_by_adoption
adopted, unadopted = partition_by_adoption(network_map)
```

A re-export, not a relocation — the implementation stays at `xml/settings.py:247`, with its signature,
its behaviour and its home unchanged. `NodeList.__all__` grows by one name. It is **not** imported
the way `node` is. The `node` import at `NodeList.py:22` is `from ..config.network_map import node`
and does not load `xml.settings`. A module-level `from ..xml.settings import NetworkMap` loads
`mapper`, then `adapters`, and `adapters._register_enums()` imports `NodeRole` from `NodeList`
while that module is still initializing. Placed next to the `node` import, before the `NodeRole`
class statement, that raises `ImportError`. After `NodeRole` and `NodeIndex` are defined, a module
`__getattr__` imports `NetworkMap` on first access and returns `NetworkMap.partition_by_adoption`
itself, not a wrapper. `import cuemsutils.tools.NodeList` does not load `xml.settings`.

**Asserted** (SC-014) by importing it from `cuemsutils.tools.NodeList` and calling it, in a test
whose only `cuemsutils` import is under `cuemsutils.tools`, with no `cuemsutils.xml` import. The
map is shaped like `ConfigManager.network_map`. The deprecated, mutating `get_nodes_by_adoption`
is untouched.

## 4. Validating a configuration document (FR-036)

### 4.1 The advice becomes per schema

`XmlReaderWriter.validate`'s deprecation warning currently sends every caller to
`CuemsScript.validate`, which cannot validate a `settings`, `network_map`, `project_mappings` or
`project_settings` document. After this feature the message names the right target **per schema**,
asserted per schema on the message text for all six.

### 4.2 A public stand-alone validator

```python
from cuemsutils.tools import validate_config_document

report = validate_config_document(path)
report.outcome        # the same Outcome vocabulary a show document reports
report.repairs        # RepairRecord list
report.conversions    # ConversionRecord list
```

Reporting through `LoadReport`/`Outcome`/`RepairRecord`/`ConversionRecord` — feature 008's existing
public report types in `cuemsutils.errors` — rather than a second vocabulary, so a caller learns *what*
is wrong and not only *that* something is. No new exception type. The body lives in
`cuemsutils.tools.config_validate`; the consumer imports the façade, which is the package
`__init__` docstring's stated reason for existing. The re-export is lazy (`__getattr__`): a
top-level import would make `import cuemsutils.tools.CTimecode` pull the schema stack, and the
empty-body rule exists to prevent that. The name is on the façade; the cost is paid when the
name is used.

It **validates without loading**: no `ConfigManager` instance, no `/etc/cuems` requirement, no write.
That is the whole gap §5b of feature 010's guide identified, and the reason it lands with the feature
that changes what a configuration document is.

---

## 5. What does not move

| | Guarantee |
|---|---|
| `AudioCue`, `VideoCue`, `DmxCue`, `*CueOutput` | same names, same fields, same equality, same hashing, same `isinstance` behaviour (FR-050a, FR-052) |
| `ActionCue`, `FadeCue`, `CueList` | keep their own elements and their own members |
| `Cue.__hash__` | restated, not inherited — `CuemsDict.__eq__` sets it to `None` otherwise, and an unhashable cue is a `TypeError` in the engine |
| `CuemsScript.load/save/validate/from_json/to_json/to_wire` | signatures unchanged; `load_with_report` unchanged |
| `cuemsutils.errors` | no new type |
| `cuemsutils.xml.__all__` | stays `[]` |
| `doc_version`, the conversion registry, `cuems-convert-documents` | untouched (FR-020, SC-006) |
| feature 012's identity surface | untouched — `SENTINEL`, `coerce_identity`, `node_uuid`, `--remint` (A8) |

**The one wire change**: a cue arrives as `{"Cue": {..., "class": "audio"}}` instead of
`{"AudioCue": {...}}`, and a cue output likewise. That is the entire observable difference in
`to_wire()`, and it is FR-032's contract to `cuems-editor` (R8) and `cuems-frontend` (R9).
