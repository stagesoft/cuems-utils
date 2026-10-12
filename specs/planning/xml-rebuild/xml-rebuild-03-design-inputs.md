# XML infrastructure rebuild — Part 2b: Design inputs

**Status:** analysis for review — feeds directly into Part 2 (target design)
**Date:** 2026-08-10
**Question:** does the node-model migration affect the `xml/` target design, given that a
proper XML infrastructure must **define** consumer usage rather than be defined by it?

**Answer:** yes, materially — six effects (§3), and one of them (E6) is a design mistake we
would only have discovered after building it. The migration must be settled *before* the
`xml/` design is fixed, which is what the Part 2a §7 sequencing already says.

---

## 1. The principle, stated precisely

> A proper XML infrastructure MUST define consumer usage, not the other way around.

Adopted. It inverts how Part 1 §3 (the consumer contract inventory) should be read: not
*"what the library must preserve"* but *"what the library will offer, and consumers
migrate"*. Under D1 (free hand, coordinated bump) this is available to us.

One distinction has to be kept sharp, or the principle produces an elegant API that cannot
express something real:

**Consumer usage defines *requirements* — the set of things that must be possible.
It does not define *interfaces* — how those things are spelled.**

So `cuems-editor` building cue objects from a schema-less frontend JSON payload is a
**requirement**: the library must be able to ingest a dict that never passed through
`xmlschema`. That it currently does so by calling `CuemsParser(data).parse()` is an
**interface**, and the library is free to replace it. The failure mode to avoid is
mistaking the second for the first — which is exactly what the audit did when it wrote
*"a schema-driven parser must still serve them … or keeping a documented second entry
point"*. That sentence let a consumer's current spelling leak into the design. Corrected
below (§4).

---

## 2. What the migration actually brings in

Not just two classes. It brings a **second document family** into the library's object
model, and that is the load-bearing change.

| | Before migration | After migration |
|---|---|---|
| Document families with an object model | 1 (script) | 2 (script, network map) |
| Document families read to raw dicts | 4 (settings, project_settings, project_mappings, network_map) | 3 |
| Serializable base types | `CuemsDict` | `CuemsDict` (node conforms) |
| Custom scalars | `CTimecode`, `Uuid` | + `NodeType` |
| External registrants of builders/parsers | 1 (`cuems-nodeconf`) | **0** |

The library owns **six** schemas (`script`, `settings`, `project_settings`,
`project_mappings`, `network_map`, `outputs`). Content models are overwhelmingly uniform —
`xs:sequence` in all six; only `script.xsd` uses `xs:all` (3) or `xs:choice` (3). A
schema-driven design generalises across the whole family cleanly.

*(Incidental: `outputs.xsd` is never loaded — no `get_pkg_schema('outputs')` call exists in
any repo. It is a dead schema file; add to Part 1 §6 as X11.)*

---

## 3. The six effects on the target design

### E1 — The serializer must be generic over document families, not specialised to scripts

Today the type registry is `from ..cues import *` plus `globals()[tag]`
([Parsers.py:1,67-73](../../src/cuemsutils/xml/Parsers.py#L67-L73)). That is not a
registry; it is a namespace that happens to contain cue classes. It cannot express "these
classes belong to `script.xsd`, those to `network_map.xsd`", so a `node` class and a cue
class named `Media` would sit in one flat namespace and collide silently.

**Design consequence:** the type registry must be **per-schema and explicit** — a mapping
from (schema, element/type name) → Python class, declared rather than scavenged. This was
already implied by D5/F8; the migration makes it non-optional, because a second family
with its own vocabulary now exists.

### E2 — One object protocol, uniformly

`node` is already a `dict` subclass with property getters/setters — structurally identical
to `Cue`. Migrating it should make that formal: it becomes a `CuemsDict` with
`REQ_ITEMS`-style layered defaults, gaining the three identity fields it is currently
missing (Part 2a §3.2).

**Design consequence:** the serializer has exactly **one** object protocol to support —
"a `CuemsDict` whose fields are declared" — instead of "cues, plus whatever an external
repo hands us". Every `isinstance` branch in the current cascade that exists to cope with
unknown shapes (`GenericDict`, bare `dict`, `None`, the `as_cuemsdict` detour at
[XmlBuilder.py:104-108](../../src/cuemsutils/xml/XmlBuilder.py#L104-L108)) loses its
justification.

### E3 — The read contract must be uniform across families

Today it is inconsistent, and the inconsistency is invisible while only one family has
objects:

| Family | `read()` | objects? |
|--------|----------|----------|
| script | dict | ✅ `read_to_objects()` |
| network_map | dict | ❌ — objects live in nodeconf |
| settings / project_settings / project_mappings | dict | ❌ |

Once `node`/`node_list` are in the library, `NetworkMap` *can* return objects — and the
design has to decide whether it does. Leaving it dict-only would mean the library owns the
model but declines to use it in its own reader.

**Design consequence:** define **one** read contract for all six schemas — a raw-dict form
and an object form — with document families that have no object model simply not offering
the second. This is precisely a case of the infrastructure defining usage: `cuems-engine`
and `cuems-editor` currently hand-walk raw network-map dicts (`node_wrap.get('node')`,
`get_nodes_by_adoption`), and under the new contract they receive typed objects instead.

It also retires a wart the engine already works around:
`ControllerEngine.py:1155` — *"We avoid `NetworkMap.get_nodes_by_adoption()` because it
mutates the dict"*. A defined API does not mutate its input.

### E4 — `NodeType` forces the type-adapter registry to be explicit, which fixes a live wart for free

`CTimecode` and `Uuid` are custom scalars whose XSD types are plain restricted strings; the
design already needs a type-adapter registry for them. `NodeType` joins them — and it
arrives carrying the `str()`/`__repr__` defect from Part 2a §3.5, where
`str(NodeType.slave)` yields `"NodeType.slave"` because `__repr__` was overridden but
`__str__` was not, and the permissive schema accepted it silently until it became a
cross-repo contract.

**Design consequence:** in an explicit adapter registry, that serialization becomes a
**declared** rule — "`NodeType` serialises as `NodeType.<name>`" — rather than an accident
of which dunder the builder happened to call. The wire format does not change (Part 2a §7
is explicit about that), but it stops being a latent bug and becomes a stated contract with
one place to change it later. Whereas keeping `str(value)` as the universal fallback, as
the current builder does, is precisely what let the accident happen.

### E5 — The schema-driven ordering mechanism is validated across families

The Part 1 §9 proposal — the serializer takes element order from the schema's content
model, `REQ_ITEMS` keeps its two deliberate jobs — was derived from `script.xsd`. All six
schemas are `xs:sequence`-dominant, so the same mechanism covers `network_map.xsd` without
special-casing. The migration is a **confirmation**, not a complication.

Corollary: the coherence test proposed there (MRO-accumulated `REQ_ITEMS` keys ≡ XSD type's
declared elements, as **set equality**) generalises to `node` too — and would have caught
the missing `role_id`/`alias`/`hostname` properties that Part 2a §3.2 found by hand.

### E6 — The registration API would have been built, then thrown away

This is the effect that justifies the sequencing, and the one we could only have found by
asking the question in this order.

Had `xml/` been designed first, F8 ("`cuems-nodeconf` extends by monkeypatching module
globals") would have been treated as a requirement, and the design would have specified a
**public builder/parser registration API** — a documented extension point, with a stable
contract, tests, and a `str_to_value`-equivalent safe for external callers to invoke.

After the migration there are **zero** external registrants. That API would be
dead-on-arrival public surface: permanent, supported, unused. And under the principle it is
doubly wrong — it would be an interface designed *around* one consumer's accidental
technique rather than defining what the infrastructure offers.

**This is the concrete answer to "does the migration affect the design": it removes a whole
subsystem from it.**

---

## 4. Part 1 §3 re-read under the principle

Each consumer contract, reclassified as *requirement the library must cover* versus
*interface the library defines and the consumer migrates to*.

| Consumer usage | Requirement? | Disposition |
|---|---|---|
| `cuems-engine`: read a script file → live cue objects | **Yes** | Library defines the reader API; engine migrates its two call sites. |
| `cuems-editor`: build cue objects from **schema-less frontend JSON** | **Yes — genuine, and easy to miss** | Ingestion must be source-agnostic: a validated model built from a dict, whether or not it came from `xmlschema`. The library defines how; the editor migrates. Not a "second entry point kept for the editor". |
| `cuems-editor`: write objects → validated XML | **Yes** | Library defines; editor migrates. |
| `cuems-editor` / `cuems-engine`: read network map → node data | **Yes** | Now served with **objects** (E3) rather than hand-walked dicts. |
| `create_script.py`: build + validate without writing (`xmlfile=None`) | **Yes** | A real capability — build/validate/write must be separable. Keep the capability; the spelling is the library's. |
| `cuems-nodeconf`: register custom builders/parsers via module globals | **No** | Dissolved by the migration (E6). |
| `cuems-nodeconf`: `XmlReader`/`XmlWriter` (deprecated since 0.0.7) | **No** | Delete; nodeconf migrates. |
| `cuems-engine`: tolerate `get_nodes_by_adoption` mutating its input | **No** | An artefact to remove, not preserve (E3). |
| External callers of `str_to_value` | **No** | Internal to the parser. Not public surface. |

Net: the library's public surface **shrinks** while covering every real requirement.

---

## 5. Revised constraints for Part 2

Consolidating, the target design must:

1. Be **generic over the six schemas**, with a per-schema explicit type registry (E1).
2. Support exactly **one object protocol** — declared-field `CuemsDict` (E2).
3. Define **one read/write/validate contract** across families, with the object form
   optional per family (E3).
4. Carry an **explicit type-adapter registry** for `CTimecode`, `Uuid`, `NodeType`, and the
   `BoolType` `"True"/"False"` spelling shared by `script.xsd` and `network_map.xsd` (E4).
5. Take **element order from the schema content model**, never from dict iteration order
   (E5), with a documented wildcard fallback for `xs:anyType` (`ui_properties`, X10).
6. Specify **no external registration API** (E6).
7. Provide **source-agnostic ingestion** so the editor's JSON payloads are a first-class
   input, not an exception (§4).
8. Separate **build / validate / write** so `xmlfile=None` remains expressible (§4).

Constraints 1–4 and 6 are new or materially changed by the migration. That is the answer to
the question: the migration does not merely add classes — it changes five of the eight
design constraints, and removes a subsystem.

---

## 6. Sequencing consequence

Part 2a §7 put the model move (step 3) before the `xml/` rebuild (step 4) on grounds of
blast radius. E6 gives a second, stronger reason: **designing `xml/` first would produce a
public extension API that the migration then makes dead.** The ordering is not just
cheaper, it is the difference between designing for a real consumer set and designing for
an accident.

Unchanged: F7 is already fixed on both nodeconf branches (Part 1 D8), independent of all of
this.

---

## 7. Decisions from review

| # | Decision | Effect |
|---|----------|--------|
| D12 | **Q10 resolved: objects, uniformly.** The public surface follows the configuration-tooling pattern already in use — Settings-like classes — and **every** public-facing class of the `xml` module returns objects, `NetworkMap` included. | E3 is settled in its coherent form. `cuems-engine` `ControllerEngine.py:249`, `cuems-editor` `CuemsWsServer.py:470` and `ConfigManager.node_network_map` migrate to typed objects. The raw-dict `read()` becomes an internal detail, not the public contract. Raises **Q11**. |
| D13 | **`outputs` and `regions` are open ends, not dead code.** Neither is deleted; both are accounted for in the target structure. | Retracts the "deletable" disposition on X11. `regions` gets the same treatment (X12): the commented-out `regionsParser`, the hand-rolled unwrapping in `mediaParser`, and the broken `Media.set_regions` coercion (**F12**) are all one unfinished concept to be closed out by the design, not worked around again. |
| D14 | **The whole chain must be tested: `xml → object → [json → object] → xml`.** | Any point where a typed object silently degrades to a "simple dict" surfaces as a test failure rather than as field behaviour. This is a first-class acceptance criterion for Part 2, not a nice-to-have — and it immediately implicates **F12** and **F13**. |

### Why D14 is sharper than it looks

The chain crosses **four independent implementations** of what should be one mapping:

```
XML ──xmlschema+converter──► dict ──CuemsParser──► objects
                                                      │
                                        __json__ ◄────┤ (8 hand-written projections)
                                            │         │
                                          JSON        │
                                            │         │
                                     CuemsParser ─────┤ (no inverse of __json__ exists)
                                                      │
                                                      ▼
                                              XmlBuilder ──► XML
```

Nothing checks that the four agree. F12 and F13 were both found while grounding this
decision, and both are exactly the class of defect the chain test exists to catch: a
`Region` that never gets constructed on the setter path (F12), degrading to a bare dict in
`__json__` (F13), and surviving a full editor save cycle as a dict because every
`isinstance` cascade in the XML layer treats `dict` and `CuemsDict` alike.

Consequence for the design: **JSON is not a side concern.** If the schema-driven mapping is
the single source of truth, the JSON projection should be derived from it too, rather than
remaining eight hand-written `__json__` methods plus a parser that has no idea they exist.
See **Q12**.

---

## 8. D15 — the real public surface, and what it collapses

Per review, the consumer-facing objects are **not** the `xml` module's classes:

| Domain | Public object | Consumers touch |
|--------|---------------|-----------------|
| All configuration files | **`tools/ConfigManager`** (+ parent `tools/ConfigBase`) | `ConfigManager` only |
| Show data | **`cues/CuemsScript`** — cues, outputs, regions all live inside | `CuemsScript` only |

`Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings`, `XmlReaderWriter`,
`CuemsParser` and `XmlBuilder` are **machinery** that these two compose. This is the
strongest form of "infrastructure defines usage": the `xml` package is an implementation
detail, not an API.

### What this collapses

**Q11 shrinks dramatically.** `ConfigBase` **already is** a partial, hand-written object
model over `settings.xsd` — twelve typed accessors (`library_path`, `tmp_path`,
`node_conf`, `node_uuid`, `database_name`, `editor_url`, …) each wrapping
`self.settings['<key>']` [ConfigBase.py:78-136](../../src/cuemsutils/tools/ConfigBase.py#L78-L136).
The question was never "should we create object models for 28 XSD types". It is: **how is
`ConfigManager`'s typed surface produced — extended by hand, or derived from the schema?**

**Q12 resolves.** `to_json()` and `__json__` already live on `CuemsScript`
[CuemsScript.py:260-300](../../src/cuemsutils/cues/CuemsScript.py#L260-L300) — the public
object. JSON is therefore owned, not merely tested. What is missing is the **inverse**:
`to_json` has no `from_json`, and no consumer calls `to_json` at all. D14's chain requires
that inverse to exist.

**Q13 resolves.** Object models belong in **domain modules** (`cues/` for show,
config-side for nodes); `xml/` holds serialization machinery only. The migrated node model
is config-domain, since `NetworkMap` is a reader `ConfigManager` composes.

### New evidence: the raw-dict contract is unverifiable in practice

**F14 — `ConfigManager` is where F5's converter shape leaks out of `xml/`.** Three
compensations, all in the public config object:

- `load_project_settings` flattens a list of single-key dicts by hand
  [ConfigManager.py:207-212](../../src/cuemsutils/tools/ConfigManager.py#L207-L212)
- `load_net_and_node_mappings` walks **five** nested levels
  (`content` → `port_type_dict` → `port_types` → `port` → `port_type_content`)
  [ConfigManager.py:153-164](../../src/cuemsutils/tools/ConfigManager.py#L153-L164)
- `check_project_mappings` walks the structure generically because its shape is not stated
  anywhere [ConfigManager.py:277-287](../../src/cuemsutils/tools/ConfigManager.py#L277-L287)

**F15 — three incompatible shapes are recorded for the same mappings data.** For
`project_node_mappings['video']`:

| Site | Shape assumed |
|------|---------------|
| `ConfigManager.get_video_output_id` [:248](../../src/cuemsutils/tools/ConfigManager.py#L248) | `['video']['outputs']` — dict-keyed, calls `.keys()` |
| `VideoCue.check_mappings` [:111](../../src/cuemsutils/cues/VideoCue.py#L111) | `['video'][0]['outputs']` — list-indexed |
| `AudioCue.check_mappings` [:158](../../src/cuemsutils/cues/AudioCue.py#L158) | `['audio'][0]['outputs']` — list-indexed |
| `ConfigManager.get_audio_output_id` [:263](../../src/cuemsutils/tools/ConfigManager.py#L263) | `project_mappings['audio']['outputs']`, then `each_out[0]['mappings']` — different source object, `[0]` at a different depth |

`.keys()` and `[0]` cannot both be right. They coexist because the two `check_mappings`
bodies are **unreachable** — both begin `return super().check_mappings()`
([VideoCue.py:101](../../src/cuemsutils/cues/VideoCue.py#L101)), so the code below is dead
and its shape assumption fossilised. The comment directly above it is explicit about the
cause: *"DEV: List first index is an artifact of the way the mappings are parsed."*

This is the case for D12/D15 stated by the codebase itself: a raw-dict contract cannot be
checked, so shape assumptions drift, fossilise, and are preserved forever in dead code that
no test can fail.

### Consumers currently bypass the public objects

Under D15 these become migration items, not contracts:

- `cuems-engine` `BaseEngine.py:509` constructs `XmlReaderWriter` directly to obtain
  `self.script`, rather than asking `CuemsScript` to load itself.
- `cuems-editor` `CuemsDBProject.load_xml` returns `reader.read()` — a **raw dict**, not a
  `CuemsScript` — and `save_xml` constructs `XmlReaderWriter` directly.

---

## 9. Remaining questions

Q12 and Q13 are resolved by D15 (§8). Two remain, restated below against all evidence
gathered since they were first posed (F12–F23, Parts 2c and 2d).

---

### Q11 — how is `ConfigManager`'s typed surface produced?

Not "should config get object models". `ConfigBase` **already has** twelve hand-written
typed accessors over `settings.xsd` (`library_path`, `tmp_path`, `node_conf`, `node_uuid`,
…). The choice is how to complete and extend that pattern across `settings.xsd`,
`project_settings.xsd`, `project_mappings.xsd` and `network_map.xsd`.

**Evidence bearing on it**

- **F14** — three shape compensations live in the public config object, including a
  **five-level** nested unwrap in `load_net_and_node_mappings`.
- **F15** — three mutually incompatible shapes recorded for the same mappings data, two
  fossilised in unreachable dead code, with a comment naming the cause: *"List first index
  is an artifact of the way the mappings are parsed."*
- **F18/F19** (Part 2c) — when coercion is location-dependent, objects of the same class
  end up with different internal types, and hand-written compensations silently fail to
  fire. Hand-maintained shape knowledge decays; this is what the decay looks like.
- **D11 already commits to hand-written classes** — `node`, `node_list`, `NodeType` move
  in as real classes. So a pure-derivation answer already has an exception.
- **`ProjectMappings` carries semantics no schema can express** — canvas_region
  containment, ≤1 custom template per node. Likewise media duration on the script side.
- **X10** — `ui_properties` is `xs:anyType`; wildcard content has no derivable model.

**Options**

- **(a) Extend by hand.** More accessors and `CuemsDict` subclasses in the established
  style. Explicit, greppable, statically checkable — but `project_mappings.xsd` alone has
  14 named types, and F14/F15 are the documented failure mode of this approach.
- **(b) Derive everything from the XSD.** Strongest single-source guarantee; retires F14's
  unwrap structurally. But it cannot express D11's hand-written node classes, the
  `ProjectMappings` semantic rules, or X10's wildcard — so it needs escape hatches anyway,
  and it costs dynamic types that are harder to grep and statically check.
- **(c) Hybrid — derived model, curated façade.** Derive the field spec and structure from
  the schema; hand-write (i) the ergonomic accessors that form the public API, (ii) the
  behaviour schemas cannot express, (iii) domain classes like `node`/`node_list`.

**Recommendation: (c).** It is the only option that survives contact with all six pieces of
evidence. Derivation kills the class of defect F14/F15 exemplify — structure is never
hand-maintained — while the hand-written layer keeps what generation is bad at: naming,
ergonomics, and semantics. It also matches what `ConfigBase` already is: a *curated façade*
over a data structure, not a mechanical mirror of it.

Best practices this rests on:

1. **Derive structure, hand-write behaviour.** Never hand-maintain what the schema already
   states; never generate what only a human can decide.
2. **Public API ≠ full model.** The façade exposes what consumers need, named for the
   domain, not one accessor per XSD element.
3. **Two validation tiers, explicitly separated** — schema-derived structural validation,
   then named semantic validators (containment, duration, template caps) that run after it.
4. **Wildcards are a declared fallback, not an accident** (X10).

---

### Q14 — does `xml/` stop being public API entirely?

**Evidence bearing on it**

- **Part 2c §4** — `CuemsScript.load()` can *guarantee* its result is fully coerced;
  `read_to_objects()` cannot, because the guarantee depends on which of two construction
  paths ran and callers cannot tell. **F18** measures the divergence (`ui_properties`:
  `dict` vs `CuemsDict`; `regions`: `list[dict]` vs `list[Region]`).
- **F16, F17, F19, F20** — the construction duality is already producing real defects,
  including a template that ships two randomised ids where it means to ship none.
- **`schema_name="script"`** is passed at six call sites across three repos. It is a
  property of `CuemsScript`, not of the caller.
- **`create_script.py`** — a first-party consumer — already reaches for the API that does
  not exist: it wants `script.validate()`.
- **Part 2d §3.2 — the binding constraint.** `project_load` transmits the converter's dict
  **verbatim to the UI** (F21/F22). If `load_xml` returns a `CuemsScript` and the editor
  serialises the object, every boolean on the wire flips `"True"` → `true`.

**Options**

- **(i) Fully internal.** `CuemsScript.load/save/validate/from_json`; `ConfigManager` for
  config; `XmlReaderWriter` and `CuemsParser` leave `__all__`.
- **(ii) Keep it public** as a supported low-level escape hatch. No consumer churn;
  weakens D15 and leaves F18's divergence representable forever.
- **(iii) Internal by default, documented escape hatch** for genuinely low-level needs.

**Recommendation: (i), with a hard precondition.** The public object must expose the
schema-faithful wire projection (Part 2d §5) **before** the editor migrates, so
`project_load` stays byte-identical. With that in place, (i) is what makes "a loaded script
is fully coerced" a guarantee rather than a hope — it makes F18's divergence
*unrepresentable* rather than merely fixed.

(ii) is the honest fallback if the migration cost is unacceptable, but it keeps two
construction paths alive and therefore keeps F16–F20 reachable. (iii) tends to collapse
into (ii) in practice, because a documented escape hatch is a supported one.

Best practices this rests on:

1. **Make invalid states unrepresentable.** A single public constructor is why the
   divergence cannot recur, rather than being fixed once.
2. **Narrow the public surface; machinery stays internal.**
3. **Do not make callers carry configuration that belongs to the type** (`schema_name`).
4. **Ship the replacement before removing the old path** — the precondition above is an
   instance of this, and it is what keeps the UI contract intact.

**Migration cost, stated plainly:** `cuems-engine` `BaseEngine.py:509`; `cuems-editor`
`CuemsDBProject.{load_xml,save_xml}`. The largest single item is `load_xml` changing from a
raw dict to a `CuemsScript` — which is exactly where the Part 2d precondition applies.
