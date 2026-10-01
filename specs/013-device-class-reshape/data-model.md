<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Phase 1 data model — device-class reshape

**Feature**: `013-device-class-reshape` | **Date**: 2026-10-01 | **Spec**: [spec.md](spec.md) |
**Research**: [research.md](research.md)

Four document shapes change, one derived structure changes, and one derivation-layer type gains a
field. Everything below follows from R1–R5: a **container element** holding a repeated
**class-carrying element**, whose type is selected by `xs:alternative`, decoded by a dispatch in one
function, with the class value arriving as a plain dict key.

---

## 1. The shape, in one piece

```xml
<!-- the invariant form, instantiated four times below -->
<containers>                            <!-- a type holding nothing but the repeated child (R2) -->
  <thing class="audio"> ... </thing>    <!-- class is a declared attribute, so it is a model field -->
  <thing class="video"> ... </thing>    <!-- xs:alternative selects this one's type (R3) -->
  <thing class="lighting"> ... </thing> <!-- no alternative: the unconditional fallback type -->
</containers>
```

```xml
<!-- the schema side, once per reshaped element -->
<xs:element name="thing" minOccurs="0" maxOccurs="unbounded" type="cms:ThingType">
  <xs:alternative test="@class='video'" type="cms:VideoThingType"/>
  <xs:alternative type="cms:ThingType"/>
</xs:element>
```

**What a new class costs** (SC-001, SC-002): nothing at all if it needs no special fields — it is a
`class` value the fallback type already accepts. One `xs:alternative` line plus the type it names, in
one schema, if it does. No model class, no constant, no registry entry, no test.

**The authoring convention this depends on** (R3, pinned by a contract test): every conditional test
is exactly `@class='VALUE'`, and every conditional element ends with one unconditional
`xs:alternative` as its fallback.

---

## 2. Axis A — `project_mappings.xsd`

### 2.1 A node's devices

**Before** (`project_mappings.xsd:43-49`) — one element per class, `maxOccurs="1"` each:

```xml
<xs:complexType name="NodeMappingType">
  <xs:sequence>
    <xs:element name="uuid" type="cms:NodeUuidType"/>
    <xs:element name="mac"  type="cms:NonEmptyString"/>
    <xs:element name="audio" minOccurs="0" maxOccurs="1" type="cms:DeviceType"/>
    <xs:element name="video" minOccurs="0" maxOccurs="1" type="cms:VideoDeviceType"/>
    <xs:element name="dmx"   minOccurs="0" maxOccurs="1" type="cms:DeviceType"/>
  </xs:sequence>
</xs:complexType>
```

**After** — `uuid` and `mac` stay single children; the devices move inside a container, because a type
may not mix single children with a repeated one (R2):

```xml
<xs:complexType name="NodeMappingType">
  <xs:sequence>
    <xs:element name="uuid"    type="cms:NodeUuidType"/>
    <xs:element name="mac"     type="cms:NonEmptyString"/>
    <xs:element name="devices" minOccurs="0" maxOccurs="1" type="cms:DevicesType"/>
  </xs:sequence>
</xs:complexType>

<xs:complexType name="DevicesType">
  <xs:sequence>
    <xs:element name="device" minOccurs="0" maxOccurs="unbounded" type="cms:DeviceType">
      <xs:alternative test="@class='video'" type="cms:VideoDeviceType"/>
      <xs:alternative type="cms:DeviceType"/>
    </xs:element>
  </xs:sequence>
  <!-- FR-013: one device per class per node (R5, pending E3) -->
  <xs:assert test="count(device) = count(distinct-values(device/@class))"/>
</xs:complexType>
```

`DeviceType` and `VideoDeviceType` keep their current content (`outputs`/`inputs` groups) and each
gains the discriminator:

```xml
<xs:attribute name="class" type="cms:NonEmptyString" use="required"/>
```

**Document instance, before and after**:

```xml
<node><uuid>…</uuid><mac>…</mac>
  <audio><outputs><output><id>0</id><name>…</name><mappings><mapped_to>…</mapped_to></mappings></output></outputs></audio>
  <video><outputs><output><id>0</id><name>…</name><canvas_region>…</canvas_region><mappings>…</mappings></output></outputs></video>
</node>
```

```xml
<node><uuid>…</uuid><mac>…</mac>
  <devices>
    <device class="audio"><outputs><output><id>0</id><name>…</name><mappings><mapped_to>…</mapped_to></mappings></output></outputs></device>
    <device class="video"><outputs><output><id>0</id><name>…</name><canvas_region>…</canvas_region><mappings>…</mappings></output></outputs></device>
  </devices>
</node>
```

### 2.2 The document root's default pairs (FR-006)

**Before** — six elements, two per class (`project_mappings.xsd:14-19`):
`default_audio_input`, `default_audio_output`, `default_video_input`, `default_video_output`,
`default_dmx_input`, `default_dmx_output`, each `minOccurs="1"`.

**After** — one container, one repeated element carrying class and direction, so a new class adds no
root element:

```xml
<xs:element name="defaults" minOccurs="1" maxOccurs="1" type="cms:DefaultsType"/>

<xs:complexType name="DefaultsType">
  <xs:sequence>
    <xs:element name="default" minOccurs="0" maxOccurs="unbounded" type="cms:DefaultPortType"/>
  </xs:sequence>
  <xs:assert test="count(default) = count(distinct-values(default/concat(@class,'/',@direction)))"/>
</xs:complexType>
<!-- DefaultPortType: xs:string content + required @class + required @direction (input|output) -->
```

`direction` is an enumeration of `input`/`output` — a direction is not an open vocabulary the way a
class is, and nothing in the system has a third one.

### 2.3 Decoded form

| | Before | After |
|---|---|---|
| node's devices | `node["audio"]` → list of `{outputs: [...]}` groups | `node["devices"]` → list of device objects, each with `class` |
| legacy key | — | `node_mappings["audio"]` still answers, derived (D1 / R10) |
| root defaults | `mappings["default_audio_output"]` → str | `mappings["defaults"]` → list; legacy key still answers, derived |

`DevicesType` and `DefaultsType` are **wrappers** in the engine's sense (`Mapper._is_wrapper`), so
they exist in the XML and not in the object model: the model field holds the list directly, exactly as
`OutputsType` does today.

---

## 3. Axis C — `settings.xsd`

**Before** (`settings.xsd:79-82`) — three class-named sections plus `audiomixer`, each with its own
`PlayerType` extension (`:93`, `:105`, `:122`):

```xml
<xs:element name="videoplayer" type="cms:VideoPlayerType" minOccurs="0"/>
<xs:element name="audioplayer" type="cms:AudioPlayerType" minOccurs="0"/>
<xs:element name="audiomixer"  type="cms:AudioMixerType"  minOccurs="0"/>
<xs:element name="dmxplayer"   type="cms:DmxPlayerType"   minOccurs="0"/>
```

**After** — the three class-scoped players move into a container; **`audiomixer` stays exactly as it
is** (FR-040a: it has no device class, and folding it in would invent one):

```xml
<xs:element name="players"    minOccurs="0" maxOccurs="1" type="cms:PlayersType"/>
<xs:element name="audiomixer" minOccurs="0" maxOccurs="1" type="cms:AudioMixerType"/>

<xs:complexType name="PlayersType">
  <xs:sequence>
    <xs:element name="player" minOccurs="0" maxOccurs="unbounded" type="cms:PlayerType">
      <xs:alternative test="@class='video'" type="cms:VideoPlayerType"/>
      <xs:alternative test="@class='audio'" type="cms:AudioPlayerType"/>
      <xs:alternative test="@class='dmx'"   type="cms:DmxPlayerType"/>
      <xs:alternative type="cms:PlayerType"/>
    </xs:element>
  </xs:sequence>
  <xs:assert test="count(player) = count(distinct-values(player/@class))"/>
</xs:complexType>
```

Three alternatives remain because all three existing player types genuinely differ —
`VideoPlayerType` adds `outputs`/`osc_port`/`output_latency_ms`, `AudioPlayerType` and `DmxPlayerType`
differ in their latency type. A *fourth* class with no extra fields costs nothing.

**Decoded form**: `node_conf["players"]` → list; `node_conf["videoplayer"]`, `["audioplayer"]`,
`["dmxplayer"]` keep answering, derived from the list (FR-042); `node_conf["audiomixer"]` is
untouched. The nested reads the engine makes — `["path"]`, `["args"]`, `["osc_port"]`,
`["output_latency_ms"]` — are inside the player object and therefore unchanged.

**Not shieldable** (R7): `cuems-common`'s three XPath readers address
`.//videoplayer/output_latency_ms` and `.//video/outputs/output` in the files on disk. Their new paths
are `.//players/player[@class='video']/output_latency_ms` and
`.//devices/device[@class='video']/outputs/output`, and they port in their own repository.

---

## 4. Axis D — `script.xsd` and `hardware_outputs.xsd`

### 4.1 Cues and cue outputs

Both choices are **already repeated-only**, so axis D needs no new container (R2):

| | Before | After |
|---|---|---|
| `CueListContentsType` (`:104-106`) | `CueList`, `AudioCue`, `DmxCue`, `VideoCue`, `ActionCue`, `FadeCue` | `CueList`, `Cue class="audio|video|dmx|…"`, `ActionCue`, `FadeCue` |
| `OutputsType` (`:148-153`) | `AudioCueOutput`, `VideoCueOutput`, `DmxCueOutput` | `CueOutput class="audio|video|dmx|…"` |

```xml
<xs:element name="Cue" minOccurs="0" maxOccurs="unbounded" type="cms:MediaCueType">
  <xs:alternative test="@class='audio'" type="cms:AudioCueType"/>
  <xs:alternative test="@class='video'" type="cms:VideoCueType"/>
  <xs:alternative test="@class='dmx'"   type="cms:DmxCueType"/>
  <xs:alternative type="cms:MediaCueType"/>
</xs:element>
```

`ActionCue`, `FadeCue` and `CueList` keep their own elements and their own members: they are cue
*kinds*, not hardware classes, and no new hardware class adds one (FR-050a).

**The Python classes survive** (FR-050a, FR-052). `AudioCue`, `VideoCue`, `DmxCue`,
`AudioCueOutput`, `VideoCueOutput`, `DmxCueOutput` keep their names, their fields, their equality and
their hashing; the registry binds the same XSD types it binds today, and the dispatch picks among them
by class. An unknown class decodes to `MediaCue`/`CueOutput`. Every `isinstance` and `singledispatch`
registration in `cuems-engine` therefore keeps working unchanged — measured: 30-odd sites, all
class-based, none parsing element names (R7's engine half).

**What does change is the wire key**, and only that: `{"AudioCue": {...}}` becomes
`{"Cue": {..., "class": "audio"}}`. That is the whole of FR-032's contract to `cuems-frontend` and the
reason R8's editor sites and R9's frontend sites move.

### 4.2 `hardware_outputs.xsd`

**Before**: two flat lists, `video_outputs` and `audio_outputs`, both `HardwareOutputsType`.
**After**: one container of class-carrying lists.

```xml
<xs:element name="outputs" type="cms:HardwareOutputsSetType"/>
<!-- HardwareOutputsSetType: repeated <outputs class="…"> of HardwareOutputsType -->
```

Recorded, as the spec does, as the cheapest and least valuable item in the feature: the schema has no
instance anywhere in the ecosystem (M9) and feature 014 replaces its structure outright. It is the
first thing to cut.

---

## 5. The derivation layer

### 5.1 `FieldSpec` gains one field

```python
@dataclass(frozen=True)
class FieldSpec:
    name: str
    xsd_type: str | None
    required: bool
    repeated: bool
    order: int
    kind: FieldKind
    child: TypeKey | None = None
    alternatives: tuple[tuple[str, TypeKey], ...] = ()   # NEW: (class value, type), schema order
```

A tuple of pairs rather than a dict, because `FieldSpec` is `frozen=True` and hashable, and
derivation is memoised by `lru_cache`. Empty for every element in the schemas as they stand today, so
the change is additive and every existing derivation is byte-identical.

### 5.2 The dispatch, in one function

```python
def _decode_member(self, body, member):
    spec_key = self._alternative_for(body, member)      # NEW: member.alternatives, by @class
    if spec_key.name in self.OPAQUE_TYPES:
        model = self._model_for_spec(derive(spec_key))
        return model(body) if model is not None else body
    return self.decode(body, derive(spec_key))
```

`_alternative_for` reads the discriminator out of `body` — available because the converter is
configured `attr_prefix=""` (R4) — and falls back to `member.child` when the class is absent or
unknown. Both the repeated path (`_decode_repeated`) and the wrapper path (`_decode_wrapper`) already
funnel through here, so this is the only decode-side change.

**The build side** needs the uniform tag and the attribute. `_tag_for_item` must prefer the declared
element name over the model's class name when the field is conditional, and `class` is emitted by the
existing attribute path (`element.set`) because it is a declared field.

### 5.3 The hardware-output inventory

```python
class HardwareOutputs(dict):
    """Per class, per direction, derived from the document (FR-011).

    ``__missing__`` answers ``[]`` for a well-formed key naming a class the node
    does not carry (FR-012): ``NodeEngine.py:566`` subscripts it unguarded.
    """
    def __missing__(self, key: str) -> list:
        ...
```

One definition replacing the two six-key literals at `ConfigManager.py:159` and `:283`, filled by one
walk that iterates the document's devices instead of a declared triple. No class name appears in the
library (FR-010, SC-003), and the three legacy spellings still answer (A4).

---

## 6. Migration — the transformation, per axis

The tool ([contracts/cli-reshape-devices.md](contracts/cli-reshape-devices.md)) applies these and
nothing else. Each is a pure reshape: no value is read, computed or dropped (FR-024).

| Axis | Old shape | New shape | Values touched |
|---|---|---|---|
| A | `<audio>`, `<video>`, `<dmx>` children of `<node>` | `<devices>` + `<device class="…">`, class from the old element name | none |
| A | six `default_X_Y` root elements | `<defaults>` + `<default class="X" direction="Y">`, text preserved | none |
| C | `<videoplayer>`, `<audioplayer>`, `<dmxplayer>` | `<players>` + `<player class="…">` | none; `<audiomixer>` left in place |
| D | `<AudioCue>`, `<VideoCue>`, `<DmxCue>` | `<Cue class="…">` | none; `ActionCue`/`FadeCue`/`CueList` untouched |
| D | `<AudioCueOutput>`, `<VideoCueOutput>`, `<DmxCueOutput>` | `<CueOutput class="…">` | none |
| D | `<video_outputs>`, `<audio_outputs>` | `<outputs>` + `<outputs class="…">` | none |

**Element order**: the new child is inserted at the position the first old sibling occupied, so
`xs:sequence` validity is preserved without re-ordering anything else. `CuemsScript`'s root is
`xs:all` and order-free, and the sorted-key emission feature 004 pinned is unaffected because no root
child is renamed.

**Detection** (FR-021, FR-027): a document is old-shape iff it carries any of the old element names at
its reshaped position, and new-shape iff it carries the container. The two cannot coexist under
`xs:sequence`, which is what makes the version marker unnecessary (FR-020) and the diagnosis exact.

**No `doc_version` moves.** Not in `CURRENT_VERSION`, not in the registry, not in
`DELIBERATE_IDENTITY_STEPS` (SC-006).

---

## 7. Entities, mapped to their implementation

| Spec entity | Where it lives after this feature |
|---|---|
| Device class | an attribute value; declared nowhere in Python; named in a schema only when it needs special fields |
| Device | `<device class="…">`, typed `DeviceType` or an alternative; model `DeviceType`/`VideoDeviceType`, unchanged |
| Class-conditional type | `xs:alternative` + `FieldSpec.alternatives` + `Mapper._alternative_for` |
| Hardware-output inventory | `HardwareOutputs`, derived, one definition, `__missing__` → `[]` |
| Version step | none (FR-020); M6 records what they would have been |
| Migration tool | `cuems-reshape-devices` (R6), `src/cuemsutils/xml/reshape_devices.py` + `tools/` discovery already shared |
| Consumer contract | `migration-guide.md`, naming R7/R8/R9's measured sites |
