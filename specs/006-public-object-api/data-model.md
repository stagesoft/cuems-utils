# Phase 1 data model — the config layer, and where the derived/hand-written line falls

**Feature**: 006-public-object-api · **Date**: 2026-08-18

The target design calls `config/` *"the least-specified part of the design"* and requires the
derived-vs-hand-written line to be settled **before code is written**. This document settles
it per type, and then covers the show-side model changes (runtime declaration, T2 rules,
wire projection).

---

## 1. The rule, stated once

Q11→(c), applied mechanically:

> **Structure is derived. Naming, ergonomics and semantics are hand-written.**
>
> If the XSD states it — fields, types, cardinality, order — it is derived and never
> hand-maintained. If only a human can decide it — what an accessor is called, which mapping
> counts as "video", whether a region fits its canvas — it is hand-written and the schema is
> not consulted.

The failure mode this exists to prevent is measured, not hypothetical: F14's five-level
nested walk and F15's three mutually incompatible shapes for one piece of data — two of them
fossilised in unreachable code behind an unconditional `return super().check_mappings()` —
are what hand-maintained structure decays into.

## 2. Config schema inventory, with the disposition of each

Four schemas, 22 complex types.

### `settings.xsd` — 7 types

`NodeConfType`, `PlayerType`, `VideoPlayerType`, `AudioPlayerType`, `AudioMixerType`,
`DmxPlayerType`, `CTimecodeType`

| Concern | Disposition |
|---|---|
| Field structure of all 7 | **Derived** — bound in the registry, replacing `GENERIC` |
| `ConfigBase`'s ~18 accessors (`library_path`, `tmp_path`, `node_conf`, `node_uuid`, `database_name`, `editor_url`, `templates_path`, …) | **Hand-written, names frozen** (FR-018). Scalar accessors keep returning scalars; only `node_conf` and the player sections start returning objects |
| `gradient_osc_port` (X13 — added required, invalidated older files) | **Untouched.** Recorded as scheduled work under the schema evolution convention; no `.xsd` edit here |

### `project_settings.xsd` — 1 type

`SettingType`. Structure derived. This is the schema behind
`ConfigManager.load_project_settings`, whose hand flattening of a list of single-key dicts
into one dict is **compensation #1** — deleted, because a derived type states the shape.

### `project_mappings.xsd` — 11 types

`NewNodesType`, `NodesType`, `NodeType`, `DeviceType`, `PutGroupType`, `PutType`,
`VideoDeviceType`, `VideoPutGroupType`, `VideoPutType`, `CanvasRegionType`, `MappedToType`

This schema carries all three of F14's compensations and all of F15's shape confusion, so it
is where the derivation earns its keep.

| Concern | Disposition |
|---|---|
| All 11 type structures | **Derived** |
| `load_net_and_node_mappings`'s five-level walk (`content` → `port_type_dict` → `port_types` → `port` → `port_type_content`) — **compensation #2** | **Deleted.** The nesting is real and stays in the document; what goes is *rediscovering it by iteration* at every level. A derived `PutGroupType`/`PutType` names each level |
| `check_project_mappings`'s generic structural walk — **compensation #3** | **Deleted.** It walks generically *because the shape is not stated anywhere*; once stated, it addresses fields |
| `get_video_output_id` / `get_audio_output_id` — which mapping is "video", the `mapped_to`-else-`name` fallback | **Hand-written.** Domain knowledge; no XSD states it |
| `canvas_region` containment, ≤1 custom template per node | **Hand-written**, as T2 rules (§5) |

**F15's resolution is a deletion, not a reconciliation.** The two `check_mappings` bodies in
`VideoCue` and `AudioCue` are unreachable — both methods begin `return super().check_mappings()`.
They are removed rather than corrected: a shape assumption no test can reach is not a
contract, and preserving it would mean choosing between `['video']['outputs']` and
`['video'][0]['outputs']` on no evidence. The one live shape — `ConfigManager`'s — becomes
the derived one.

### `network_map.xsd` — 3 types

`NodeDictType`, `NodeType`, `PutType`

| Concern | Disposition |
|---|---|
| Structure of all 3 | **Derived** |
| `node` / `node_list` model classes | **Hand-written in `cuemsutils/config/network_map.py`** — see the sequencing note below |
| `NodeType` enum vocabulary | **Not in the schema** (typed `NonEmptyString`), so hand-written; the `"NodeType.<name>"` wire format is a cross-repo contract with `cuems-engine` and does **not** change |
| `get_nodes_by_adoption` mutating its input | Non-mutating replacement is **feature 007's** deliverable, not this one |

**The 006/007 boundary, stated explicitly because it is the one place this plan could
overreach.** D11 moves the node model in from `cuems-nodeconf`, but that is feature 007 — and
FR-014 requires `network_map` to return typed objects *here*. Both hold only if:

- **006** defines `node` and `node_list` in `cuemsutils/config/network_map.py` as
  `CuemsDict`-based containers with declared fields derived from `network_map.xsd`, and binds
  them in the registry so `NetworkMap` returns objects.
- **007** fills in the migrated behaviour — the Avahi-adjacent helpers, the identity fields
  `role_id`/`alias`/`hostname` the current nodeconf model omits, the 106-case coercion
  regression test — and deletes `cuems-nodeconf`'s copies.

006 must **not** implement the node behaviour: its evidence (that regression test) lives in
the other repository and 007 owns bringing it across. Building the containers here and the
behaviour there is what lets both features be independently green.

## 3. Config object protocol

Every config model is a `CuemsDict` with declared fields — the **one** object protocol the
serializer already supports (design-inputs E2). No second protocol is introduced for config.

```
ConfigManager / ConfigBase          hand-written facade — names frozen (FR-018)
        │  .settings .network_map .mappings .node_mappings .node_conf …
        ▼
cuemsutils/config/                  derived structure, CuemsDict models
        │  network_map.py  settings.py  mappings.py
        ▼
xml/ registry                       binds xsd type → model class, per schema
        │                           (replaces the four GENERIC bindings)
        ▼
xml/mapper.py                       the one decode/encode engine
```

The coherence test (004's FR-020) extends to config classes unchanged: set equality between
MRO-accumulated declared fields and the XSD type's elements. That test found `X17` on its
first run; pointing it at config is what stops the node model's missing identity fields from
recurring.

## 4. Show-side: runtime state becomes declared

Per the clarification, runtime attributes move from imperative `_init_runtime()` bodies to a
declared mapping, accumulated across the MRO exactly as `REQ_ITEMS` already is.

| Class | Runtime fields declared |
|---|---|
| `Cue` | `_target_object`, `_conf`, `_armed_list`, `_start_mtc`, `_end_mtc`, `_end_reached`, `_go_thread`, `_stop_requested`, `_local` |
| `AudioCue` | `_player`, `_osc_route` |
| `VideoCue` | (its current additions) |
| `DmxCue` | (its current additions) |
| `ActionCue` | `_action_target_object` |

Two constraints that are not negotiable, both from measured behaviour:

1. **Defaults are factories, not values.** `_start_mtc`/`_end_mtc` are fresh `CTimecode()`
   instances per object; a shared default would alias playback marks across every cue in a
   show.
2. **`_initialized` is declared as NOT initialized by the hook.** It gates value-rejecting
   rules in `ActionCue`, `FadeCue` and `VideoCueOutput`, each of which holds it false *during
   population* so those rules stay off the decode path. `helpers.py:236-247` records that the
   resulting failure is **arrival-order dependent** — a `custom` `output_name` arriving before
   `canvas_region` raises, the reverse order does not — so the corpus would catch a mistake
   here only by luck. It is a named exception in the declaration, not an omission.

Consequences fixed by construction: `to_wire()` projects declared fields only, so no runtime
attribute can reach the UI; equality compares declared fields, so `load(save(x)) == load(x)`
holds regardless of playback state; copying yields fresh runtime state rather than shared
thread handles.

## 5. The T2 rule registry

Lives in `xml/validators.py`, which 004 already established as the tier's home. Each rule is
a **named unit bound to the (type, field) pairs it applies to**, with exactly one definition
invoked from two call sites: the property setter (immediate, programmatic) and the
write/validate tier.

| Rule | Applies to | Seeded from |
|---|---|---|
| `canvas_region_containment` | `VideoCueOutput.canvas_region`, `project_mappings` canvas regions | existing `check_canvas_region_containment` |
| `one_custom_template_per_node` | `project_mappings` nodes | existing `check_one_custom_template_per_node` |
| `media_duration` | `Media.duration` | `Media.set_duration` |
| `output_name_shape` | `VideoCueOutput.output_name` | `_classify_output_name` |
| `action_target_required` | `ActionCue.action_target` | `ActionCue.set_action_target` |
| `cuelist_shape` | `CuemsScript.CueList` | `CuemsScript.set_CueList` |
| `fade_*` (4 rules) | `FadeCue` | its four setters |
| `fade_profile_*` (4 rules) | `FadeProfile` | its four setters |
| `fade_profile_caps` | `MediaCue.fade_profiles` | `MediaCue.set_fade_profiles` |

**Not in the registry**: the uuid4 shape check. It stays a coercion concern — `_UuidAdapter`
keeps an unparseable identifier as its raw string, which is what lets the editor's nil
`Media.id` (three occurrences in one ordinary payload, measured) keep loading.

**The constructor constraint.** `VideoCueOutput.__init__` calls the module-level
`_classify_output_name` *before* `super().__init__`, and that call — not the setter — is what
pins two legacy corpus documents as `to_objects: error` in the golden outcomes. Delegation
must preserve the **constructor call**, not merely setter invocation. Feature 005 had to
correct this same misreading in flight; it is written down here so 006 does not repeat it.

**The existing closed list is derived from the registry, not maintained beside it.**
`validators.py` already holds `SEMANTIC_RULES` — a hand-written tuple of three human-readable
names (`"canvas_region containment"`, `"at most one custom template per node"`,
`"media duration"`) that `test_config_parity` and the coherence test read to assert the tier
has not grown silently. Once `RULES` exists, keeping both is two inventories of one thing —
the same drift FR-024c forbids one level up. So `SEMANTIC_RULES` is **derived from `RULES`**
(or deleted and its two readers pointed at the registry). Note the name *form* also changes,
from prose with spaces to identifiers (`canvas_region_containment`); the two tests that read
the list must be updated with it, and the rule messages — which are what users see — are
preserved unchanged.

**Execution**: never on `load()`/`from_json()`; all rules on `save()` (raising at the first,
writing nothing) and on `validate()` (collecting every violation into a report). The seam
(`run_rules`) is built when `save()`/`validate()` first need it, wrapping the rules
`validators.py` already holds; the registry then **fills** that seam rather than introducing
it. Nothing calls a function that does not yet exist.

## 6. The wire projection

**Signature, pinned** (so the two call sites cannot drift):

```python
class Mapper:
    def __init__(self, schema_name: str) -> None: ...
    def encode_wire(self, obj, spec=None) -> dict: ...
```

The schema is bound at **construction** — `Mapper('script')`, `Mapper('settings')` — exactly as
it already is for `decode_document`. `spec` is an **optional** parameter naming the type spec to
project *within* that schema; omitted, it is resolved from the object's class through the
registry, which is what every call site in this feature does. It exists because the recursive
descent needs to pass the child spec down, not because callers supply one.

The consequence that matters for FR-014a: `CuemsScript.to_wire()` and a config object's
`to_wire()` differ **only in which `Mapper` they hold**, which is what makes "one projection
implementation" (SC-017) true of the code and not merely of the intent. The shared method lives
on the `CuemsDict` base in `src/cuemsutils/helpers.py` — defined there when `CuemsScript` first
needs it and *relocated* rather than duplicated when config does. Placing it on the base means
every `CuemsDict` subclass exposes `to_wire()`/`to_json()`; that is intended, and it is counted
in the enumerated API-surface diff rather than discovered when the golden fails.

Mirrors `decode`, sharing the same `Adapter` instances so encode and decode cannot disagree by
construction.

| Element | Wire form | Why |
|---|---|---|
| `BoolType` | `"True"` / `"False"` **strings** | `cms:BoolType` is `xs:string` in the XSD. Not a bug; changing it is deferred item X1 |
| `PercentType`, `LoopType` | `int` | schema-declared |
| `CTimecodeType` | `{"CTimecode": "…"}` | matches today's converter output |
| Enum types | member name | |
| Wildcard (`ui_properties`, `xs:anyType`) | scalars pass through as **strings** | X10's documented fallback; this is what aligns `initial_template` with `project_load` |
| Repeated elements | today's `CMLCuemsConverter` shape, unchanged | it **is** the UI contract (F22) |
| `schemaLocation` | **absent** | F23 — an XML artifact with no meaning to the UI |
| Runtime attributes | **absent by construction** | §4 |

`to_json()` is `json.dumps(to_wire())`, and `from_json()` is `Mapper.decode_document` — which
already exists. The eight hand-written `__json__` methods are deleted.

## 7. Entity summary

| Entity | Kind | Notes |
|---|---|---|
| `CuemsScript` | public, show | gains `load`/`save`/`validate`/`from_json`/`to_json`/`to_wire` |
| `ConfigManager` / `ConfigBase` | public, config | accessor names frozen; return types become objects |
| `node`, `node_list`, `NodeType` | config domain | containers here (006), behaviour in 007 |
| settings / project_settings / mappings models | config domain | derived structure, `CuemsDict` |
| `RuntimeFields` declaration | model metadata | per class, MRO-accumulated, factory defaults |
| T2 rule | validation | named, (type, field)-bound, one definition, two call sites |
| Wire dict | projection | schema-faithful; no artifacts, no runtime state |
| Deprecation shim | compatibility | one release, existing message template |
