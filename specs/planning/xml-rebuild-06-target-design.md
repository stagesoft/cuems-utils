# XML infrastructure rebuild — Part 3: Target design

**Status:** design for review
**Date:** 2026-08-10
**Supersedes:** the "current architecture" of Part 1. Consumes Parts 2a–2d.

Consumer migration (`cuems-engine`, `cuems-editor`, `cuems-nodeconf`, `cuems-frontend`) is a
**post-spec deliverable**, specified in §12 and executed after this lands.

---

## 1. What this design is required to be

| Decision | Requirement it imposes |
|---|---|
| D1 | Free hand on API; coordinated bump across consumers. |
| D2 | Schema is the single source of truth for structure, type, cardinality, order. |
| D3 | Wire-compatible with every XML currently on disk. No schema edits. |
| D5 | `CMLCuemsConverter` reduced to a thin subclass over stock `xmlschema`. |
| D9 | PEP 8 module names, landed as a separate rename commit. |
| D11 | Node model + serializers move in from `cuems-nodeconf`. |
| D12 | Public surface returns objects, never raw dicts. |
| D13 | `outputs` and `regions` are closed out, not worked around. |
| D14 | `xml → object → json → object → xml` is tested end to end. |
| D15 | Public objects are **`CuemsScript`** (show) and **`ConfigManager`/`ConfigBase`** (config). |
| Q11 → (c) | Derive structure from the schema; hand-write façade and behaviour. |
| Q14 → (i) | `xml/` is internal machinery. `XmlReaderWriter`/`CuemsParser` leave the public API. |

Plus the binding precondition from Part 2d §3.2: **the public object must be able to emit
the schema-faithful wire dict**, so `cuems-editor`'s `project_load` payload stays
byte-identical and the UI is unaffected.

---

## 2. Architecture

```
        ┌──────────────────────── public ────────────────────────┐
        │  CuemsScript              ConfigManager / ConfigBase   │
        │  .load .save .validate    .settings .network_map       │
        │  .from_json .to_json      .mappings .node_mappings     │
        │  .to_wire                 (curated façade accessors)   │
        └───────────────┬────────────────────┬───────────────────┘
                        │                    │
        ┌───────────────▼────────────────────▼───────────────────┐
        │                  model layer  (domain)                 │
        │   cues/  : CuemsScript, Cue…, Media, Region, CueOutput │
        │   config/: node, node_list, NodeType, settings models  │
        │   every one a CuemsDict with declared fields           │
        └───────────────────────┬────────────────────────────────┘
                                │
        ┌───────────────────────▼────────────────────────────────┐
        │              xml/  — INTERNAL MACHINERY                │
        │                                                        │
        │   spec.py      TypeSpec/FieldSpec derived from XSD     │
        │   adapters.py  scalar codecs (CTimecode, Uuid, Bool…)  │
        │   registry.py  per-schema  xsd type  ⇄  model class    │
        │   mapper.py    ONE engine: encode / decode             │
        │   converter.py thin xmlschema converter subclass       │
        │   schema.py    schema loading + caching                │
        │   schemas/     the six .xsd files                      │
        └────────────────────────────────────────────────────────┘
```

Three projections, **one engine**: XML `ElementTree`, wire `dict` (== JSON), and in-memory
objects. Today those are four independent implementations (Part 1 F2, F13).

---

## 3. The core: a field spec derived from the schema

### 3.1 Verified feasible

`xmlschema`'s `content.iter_elements()` resolves `xs:extension` chains **in schema order**,
with type and cardinality attached. Measured on `AudioCueType`:

```
autoload, description, enabled, id, loop, name, offset, post_go, postwait,
prewait, target, timecode, ui_properties,   ← CommonPropertiesType
Media, outputs,                              ← MediaCueType
master_vol,                                  ← AudioCueType
fade_profiles (0..1)                         ← AudioCueType
```

`master_vol` **before** `fade_profiles`, and the sequence is **not alphabetical**. That is
precisely the order the hardcoded hack at `XmlBuilder.py:335-343` exists to fake — obtained
for free, together with types (`PercentType`, `BoolType`, `CTimecodeType`) and cardinality.

### 3.2 The shape

```python
@dataclass(frozen=True)
class FieldSpec:
    name:      str            # 'master_vol'
    xsd_type:  str            # 'PercentType'
    adapter:   Adapter        # resolved from xsd_type
    required:  bool           # min_occurs > 0
    repeated:  bool           # max_occurs != 1
    order:     int            # position in the content model

@dataclass(frozen=True)
class TypeSpec:
    qname:     str            # 'AudioCueType'
    fields:    tuple[FieldSpec, ...]   # in schema order
    wildcard:  bool           # xs:anyType content (ui_properties)
    model:     type           # AudioCue
```

Derived once per (schema, type) at first use and **cached** — schema walking is not on the
hot path.

### 3.3 What each hand-written and derived part owns

| Concern | Owner | Why |
|---|---|---|
| field **order** | derived | schema states it (§3.1) |
| field **type**, cardinality | derived | schema states it |
| field **membership** | `REQ_ITEMS` (hand) + coherence test vs derived | human-facing alphabetical index, per Part 1 §9 |
| field **defaults** | `REQ_ITEMS` (hand) | layered via `super().__init__()`; schemas have no useful defaults here |
| **scalar codecs** | adapter registry (hand, small) | `CTimecode`/`Uuid` are not expressible in XSD |
| **semantic rules** | named validators (hand) | containment, template caps, duration |
| **façade accessors** | `ConfigBase`/`ConfigManager` (hand) | naming and ergonomics; Q11(c) |

`REQ_ITEMS` keeps exactly the two jobs Part 1 §9 established — layered defaults and the
alphabetical developer index — and **loses the third, accidental one** (element order).

### 3.4 The coherence test

Per model class, assert **set equality** (not order) between `REQ_ITEMS` keys accumulated
across the MRO and the derived `TypeSpec` field names. Catches Python↔schema drift, which
nothing catches today — and which produced the missing `role_id`/`alias`/`hostname`
properties on `node` (Part 2a §3.2).

---

## 4. Adapters

Small, closed, explicit. Measured inventory across `script.xsd`: four primitive bases and
20 named simple types, of which only these need custom handling:

| XSD type | Python | Lexical (XML text) | Wire/JSON scalar |
|---|---|---|---|
| `BoolType` | `bool` | `"True"` / `"False"` | `"True"` / `"False"` |
| `UuidType`, `TargetType` | `Uuid` | uuid string | uuid string |
| `CTimecodeType` | `CTimecode` | `{CTimecode: "…"}` | `{CTimecode: "…"}` |
| `PostGoType`, `ActionType`, `Fade*Type` | `Enum` | member name | member name |
| `PercentType`, `LoopType`, `Channel*` | `int` | decimal | `int` |
| `UnitFloat`, `PositiveUnitFloat` | `float` | decimal | `float` |
| everything else | `str` | as-is | as-is |

```python
class Adapter(Protocol):
    def decode(self, raw): ...        # lexical/wire -> Python
    def to_lexical(self, obj): ...    # Python -> XML element text
    def to_wire(self, obj): ...       # Python -> JSON-safe scalar
```

**`to_wire` is why the UI contract holds.** `BoolType.to_wire` returns `"True"` because the
schema says the type is `xs:string` restricted to `True`/`False` (X1) — reproducing today's
`project_load` payload exactly (Part 2d §5). `PercentType.to_wire` returns `int`. Wildcard
content stays `str`. This is measured behaviour, not aspiration.

**This retires `str_to_value` and `STRING_TYPED_KEYS` entirely.** Types come from the
schema; there is nothing left to guess, so the 869cqbpxa defect class becomes
unrepresentable rather than denylisted.

---

## 5. Registry — explicit, per schema

```python
SCRIPT = SchemaRegistry('script', root='CuemsProject')
SCRIPT.bind('CuemsScriptType',  CuemsScript)
SCRIPT.bind('AudioCueType',     AudioCue)
SCRIPT.bind('RegionType',       Region)          # D13
SCRIPT.bind('OutputsType',      Outputs)         # D13
...
NETWORK_MAP = SchemaRegistry('network_map', root='CuemsNetworkMap')
NETWORK_MAP.bind('NodeType',     node)           # D11
NETWORK_MAP.bind('NodeDictType', node_list)
```

Replaces **three** implicit `globals()` lookups (builder, parser, tag→class) with one
declared binding per schema. A missing binding is an error at registry build time, not a
silent fallback to a generic (Part 1 §1.4).

Per D11 + Q14 there is **no public registration API** — nothing external registers, because
nothing external owns a model any more.

---

## 6. One mapper, three projections

```python
mapper.decode(spec, source) -> model object   # source: parsed dict (from XML or JSON)
mapper.encode_xml(obj)      -> Element
mapper.encode_wire(obj)     -> dict           # == JSON payload
```

- Order comes from `TypeSpec.fields`, never from dict iteration → **F1 closed**.
- The same `Adapter` runs on both sides → encode/decode cannot disagree → **F2, F13 closed**.
- Wildcard types (`ui_properties`, X10) take the documented fallback: preserve insertion
  order, pass scalars through untyped.
- Repeated elements keep `CMLCuemsConverter`'s current decode shape (D5) because that shape
  **is** the UI contract (Part 2d §3.1, F22).

`to_json()` becomes `json.dumps(mapper.encode_wire(self))`, and gains its missing inverse
`from_json()`. The eight hand-written `__json__` methods are deleted.

---

## 7. Object protocol and the single construction path

1. **Every model class is a `CuemsDict`**, including `CuemsScript` (Part 2c §5) — removing
   the duplicated `setter`, the missing `build`, the `isinstance` exception, the divergent
   `items()`, and the `if k.lower() != k` JSON hack.
2. **One construction path.** Coercion moves out of property setters and into the field
   spec's adapters, so it runs regardless of entry point — XML, JSON, or keyword. Property
   setters remain for ergonomics but are no longer the coercion site.
3. Consequently `AudioCue({...})`, `CuemsScript.load(...)` and `from_json(...)` produce
   **identical** internal types. **F18 becomes unrepresentable**; F12, F19 (regions never
   becoming `Region`) close with it, satisfying D13.
4. `items()` is defined once on `CuemsDict`, filtered to declared fields.
5. One defaulting protocol for all classes → **F20 closed**.
6. `setter()`'s blanket `except AttributeError` is narrowed to "no such setter" → **F17**.

---

## 8. Public surface

```python
# ---- show ----------------------------------------------------------------
script = CuemsScript.load(path)          # fully coerced, guaranteed
script = CuemsScript.from_json(payload)  # editor's frontend payload
script.save(path)                        # validates, then writes
script.validate()                        # raises; no file needed
script.to_wire()                         # schema-faithful dict (UI payload)
script.to_json()                         # json.dumps(to_wire())

# ---- config --------------------------------------------------------------
cm = ConfigManager(config_dir)           # constructor unchanged
cm.library_path, cm.node_conf, cm.node_uuid      # curated façade, unchanged
cm.network_map                            # -> node_list objects (D12)
cm.node_mappings, cm.project_mappings     # -> typed objects
```

`schema_name="script"` disappears from every call site — it is a property of `CuemsScript`,
not of callers (six sites across three repos today).

`build` / `validate` / `write` stay separable, preserving `create_script.py`'s
`xmlfile=None` capability as `script.validate()` — the API that first-party consumer
already reaches for.

---

## 9. Validation tiers

| Tier | Source | Runs |
|---|---|---|
| **T1 structural** | derived from XSD — types, cardinality, order, enums, patterns, `xs:assert` | on `load`, `from_json`, `validate`, `save` |
| **T2 semantic** | named, hand-written, registered per type | after T1 |

T2 registry seeds with what exists today: `canvas_region` containment, ≤1 custom template
per node, media `duration`. Explicitly separated so neither tier silently absorbs the other.

---

## 10. Module layout (D9)

```
cuemsutils/xml/          # internal — __init__ exports nothing public
    schema.py  spec.py  adapters.py  registry.py  mapper.py  converter.py  schemas/
cuemsutils/cues/         # show domain; CuemsScript public
cuemsutils/config/       # NEW: node, node_list, NodeType + config models (D11)
cuemsutils/tools/        # ConfigBase, ConfigManager — public config façade
```

Deleted: `XmlBuilder.py`, `Parsers.py`, `CMLCuemsConverter.py` (reduced into
`converter.py`), `XmlReaderWriter.py` (absorbed), `Settings.py`'s dead `data2xml`/`buildxml`/
`process_network_mappings`, the ~50 lines of commented-out parsers, `XmlReader`/`XmlWriter`.

---

## 11. Findings traceability

| Finding | Closed by |
|---|---|
| F1 ordering coincidence | §3.1 derived order; hack deleted |
| F2 duplicated cascades | §6 one mapper |
| F3 inconsistent `build()` returns | §6 single engine |
| F4 `DmxScene` swallows exceptions | catch-all removed |
| F5 converter fork | D5 thin subclass; shape preserved (F22) |
| F6 `str_to_value` guessing | §4 adapters; `STRING_TYPED_KEYS` deleted |
| F7 nodeconf coercion | ✅ shipped (`4b6844e`, `0a3ce37`); permanently prevented by D11 |
| F8 globals monkeypatch | dissolved by D11 — no external registrant |
| F9/F10 dead code, no-op guards | §10 deletions |
| F11 hot INFO logging | logging pass |
| F12/F19 regions never typed | §7.3 single construction path |
| F13 JSON asymmetry | §6 `to_wire` + `from_json` |
| F14/F15 config shape compensations | §3 derived structure + §8 typed façade |
| F16 ids not cleared | fixed with §7's coercion move |
| F17 blanket `except AttributeError` | §7.6 |
| F18 same class, different types | §7.3 — unrepresentable |
| F20 two defaulting protocols | §7.5 |
| F21 two UI encodings | §4 single `to_wire`; `initial_template` aligns to `project_load` |
| F22 converter shape is UI contract | recorded as a constraint; D5 honours it |
| F23 leaked `schemaLocation` | dropped from `to_wire` |
| X1–X12 | deferred per D3; X11/X12 (`outputs`, `regions`) closed structurally per D13 |

---

## 12. Post-spec consumer migration

| Repo | Change |
|---|---|
| `cuems-engine` | `BaseEngine.py:509` → `CuemsScript.load(path)`; `ControllerEngine` network-map access → typed objects; non-mutating replacement for `get_nodes_by_adoption`. |
| `cuems-editor` | `CuemsDBProject.{load_xml,save_xml}` → `CuemsScript.load/save`; `CuemsParser(data).parse()` → `CuemsScript.from_json(data)`; **`load()` must return `script.to_wire()`** so `project_load` stays byte-identical. |
| `cuems-nodeconf` | Delete `NodeXmlBuilders.py` (model + serializers now upstream); drop deprecated `XmlReader`/`XmlWriter`. |
| `cuems-frontend` | **No change required.** Optional follow-up: drop the `=== true \|\| === 'True'` dual-check once `initial_template` aligns. |

---

## 13. Phasing

1. **Rename** (D9) — pure `git mv` + imports, no logic. Separate commit.
2. **Spec + adapters + registry**, with the coherence test. No behaviour change yet.
3. **Mapper**, behind the existing public API; the D14 chain test must pass against
   current behaviour before anything is deleted.
4. **`CuemsScript` → `CuemsDict`**, single construction path.
5. **Public surface** (`load/save/validate/from_json/to_wire`); old API deprecated.
6. **Node model migration** (D11) — after `feat/nodeconf-reenable` lands.
7. **Delete** the old machinery; `xml/` goes internal.
8. **Consumer migration** (§12), coordinated bump.

Step 3's ordering is deliberate: **the chain test is written against today's behaviour
first**, so it can prove the rebuild preserves it.

---

## 14. Risks

| Risk | Mitigation |
|---|---|
| Derived types are harder to grep and statically check | Q11(c): the *public* surface is hand-written and typed; derivation sits behind it |
| Schema walking per object could be slow | `TypeSpec` cached per (schema, type); existing perf test guards it |
| The UI payload changes accidentally | `to_wire` output asserted byte-equal to today's `read()` in the chain test |
| Big-bang refactor risk | §13 phasing; each step independently green |
| `xmlschema` upgrade breaks `iter_elements`/converter | D5 shrinks the coupling; pin and cover with the chain test |

## 15. Deferred (unchanged)

X1 `BoolType` → `xs:boolean` (file-format migration, and the single change that would give
the UI real JSON booleans), X5 `xs:all`, X2/X3/X4 dead and duplicate types, X9 `PutType`.
All remain out of scope under D3.
