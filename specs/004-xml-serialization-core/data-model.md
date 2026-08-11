# Phase 1 Data Model: derived specification, adapters, registry

**Feature**: `004-xml-serialization-core` | **Date**: 2026-08-11
**Source**: target design §3–§6, corrected by research R2–R8.

These are internal machinery types (Q14). None is public API. All are immutable and
derived; none is hand-maintained per field.

---

## 1. `FieldSpec`

One element (or attribute) of one complex type.

| Field | Type | Derived from | Notes |
|---|---|---|---|
| `name` | `str` | `XsdElement.local_name` | wire/dict key |
| `xsd_type` | `str` | `element.type.local_name` | `None` for anonymous types → falls back to `path_key` |
| `adapter` | `Adapter` | resolved from `xsd_type` | see §3 |
| `required` | `bool` | `min_occurs > 0` | |
| `repeated` | `bool` | `max_occurs != 1` | drives the repeated-element shape (FR-014) |
| `order` | `int` | index within `iter_elements()` | meaningful only when the parent is ordered (§2) |
| `kind` | `enum{element, attribute, wildcard}` | element vs `attributes` vs `XsdAnyElement` | R6, R7 |
| `child_ref` | `TypeKey \| None` | `element.type` | resolved lazily (R8) |

Frozen dataclass. Constructed only by the derivation pass.

---

## 2. `TypeSpec`

The ordered field set for one complex type.

| Field | Type | Derived from | Notes |
|---|---|---|---|
| `key` | `TypeKey` | qname or element path | R3 — anonymous types keyed by path |
| `fields` | `tuple[FieldSpec, ...]` | `content.iter_elements()` | in declaration order |
| `model_group` | `enum{sequence, choice, all}` | `content.model` | **decides the ordering rule** |
| `ordered` | `bool` | `model_group != all` | see below |
| `wildcard` | `bool` | any `XsdAnyElement` present | `UiPropertiesType` |
| `mixed` | `bool` | `type.mixed` | |
| `model` | `type` | registry binding | the Python class |

### 2.1 The ordering rule (R2 — the correction to the target design)

```
if spec.ordered:                      # xs:sequence / xs:choice
    emit in FieldSpec.order            # schema declaration order — authoritative
else:                                  # xs:all — schema declares order irrelevant
    emit in sorted(name) order         # documented deterministic tie-break
```

Both branches are schema-driven: the second honours the schema's statement that no order
is imposed. The tie-break is chosen to reproduce current bytes exactly.

**Affected types (exhaustive, measured)**: `CuemsScript` (anonymous root) and
`DmxSceneType`. Every other type in all six schemas is ordered.

This is the requirement that deletes the `master_vol`/`fade_profiles` hack (FR-002): with
`AudioCueType.ordered == True`, `master_vol` precedes `fade_profiles` because
`FieldSpec.order` says so.

### 2.2 Derivation and caching

```
TypeSpec = derive(schema_name, type_key)      # memoised on (schema_name, type_key)
```

Lazy and memoised (R8): content models are cyclic, so `child_ref` holds a `TypeKey` that
is resolved on demand rather than an inlined `TypeSpec`. The memo is the mechanism behind
SC-PERF-002 — derivation count is bounded by the number of distinct types (56 across all
six schemas), never by the number of objects.

---

## 3. `Adapter`

Scalar and wrapper handling that the schema cannot express by itself. Bound by **type
qname**, complex or simple (R5).

```python
class Adapter(Protocol):
    def decode(self, raw): ...        # lexical text or wire value -> Python
    def to_lexical(self, obj): ...    # Python -> XML element text
    def to_wire(self, obj): ...       # Python -> JSON-safe scalar
```

| XSD type | Python | XML text | Wire scalar | Note |
|---|---|---|---|---|
| `BoolType` | `bool` | `"True"` / `"False"` | **`"True"` / `"False"`** | string in the schema (X1); **this is what keeps the UI contract** |
| `UuidType`, `TargetType` | `Uuid` | uuid string | uuid string | `TargetType` also permits empty |
| `CTimecodeType` | `CTimecode` | `{CTimecode: "…"}` wrapper | same | **complex type** (R5) |
| `PostGoType`, `ActionType`, `FadeTypeType`, `FadeModeType`, `FadeCurveType`, `FadeFunctionIdType` | `Enum` | member name | member name | 6 enum types |
| `PercentType`, `LoopType`, `ChannelNumberType`, `ChannelValueType` | `int` | decimal | `int` | |
| `UnitFloat`, `PositiveUnitFloat` | `float` | decimal | `float` | |
| `DateType` | `str` | ISO datetime | `str` | `xs:dateTime`; unchanged today |
| everything else | `str` | as-is | as-is | native `xmlschema` decoding |

`to_wire` is a distinct direction from `to_lexical` precisely because the UI payload is
JSON, and it is what makes booleans stay `"True"` rather than becoming `true` — the
hard constraint from Part 2d.

**This retires `str_to_value` and `STRING_TYPED_KEYS` from every live path** (FR-003):
types are declared, so there is nothing left to guess and the 869cqbpxa defect class
becomes unrepresentable rather than denylisted.

---

## 4. `SchemaRegistry`

One per schema (R4 — mandatory, not stylistic: `script.xsd` and `outputs.xsd` both declare
`OutputsType` in the same namespace with different content).

```python
SCRIPT = SchemaRegistry('script', root='CuemsProject')
SCRIPT.bind('CueListType',   CueList)
SCRIPT.bind('AudioCueType',  AudioCue)
SCRIPT.bind_path('CuemsProject/CuemsScript', CuemsScript)   # anonymous type (R3)
SCRIPT.bind('RegionType',    Region)      # D13
SCRIPT.bind('RegionsType',   GenericDict) # explicit generic, preserves today's output
...
```

Rules:

1. Binding is by **type qname** or, for anonymous types, by **element path**.
2. Every complex type in the schema must be bound. Unbound → error at registry build
   time, naming the type (FR-007).
3. Types that reach a generic today by silent fallback are bound **explicitly to that same
   generic**. Registry completeness means *accounted for*, not *given a bespoke class*.
   ~13 of `script.xsd`'s 33 types are in this category (R9); the exact list is produced by
   instrumenting the current `globals()` lookups across the corpus.
4. No public registration API (D11 + Q14) — nothing external owns a model.

Replaces three implicit `globals()` name-manglings (builder, parser, tag→class), each of
which currently misses silently.

---

## 5. `Mapper`

```python
mapper.decode(spec, source) -> model object   # source: parsed dict, from XML or JSON
mapper.encode_xml(obj)      -> Element
mapper.encode_wire(obj)     -> dict           # == the JSON payload
```

- Order from `TypeSpec` per §2.1 — never from dict iteration (**F1 closed**).
- One `Adapter` on both sides, so encode and decode cannot disagree (**F2, F13 closed**).
- Wildcards take the documented fallback (FR-009).
- Repeated elements keep the converter's current decode shape — it *is* the UI contract
  (F22, FR-014).
- Failure inside DMX scene serialization keeps today's swallow-and-log, behind a single
  named compatibility behaviour carrying its removal target (FR-015a). It is **not** an
  ambient `except Exception` in the general path.

---

## 6. Coherence check (FR-020)

Per registry binding, assert **set equality** between `REQ_ITEMS` keys accumulated across
the MRO and `TypeSpec` field names. Sets, not order — order is the engine's job now.

Reach: classes bound in the registry, which today means the show-document classes.
Configuration documents have no model classes until feature 006.

`REQ_ITEMS` keeps exactly the two jobs the audit established — layered defaults and the
alphabetical developer index — and loses the accidental third one, element order.

---

## 7. What stays hand-written (Q11(c))

| Concern | Owner |
|---|---|
| field order, type, cardinality | derived |
| field membership | `REQ_ITEMS` + coherence test against derived |
| field defaults | `REQ_ITEMS` |
| scalar codecs | adapter registry — small, closed, explicit |
| semantic rules (T2) | named validators: canvas-region containment, ≤1 custom template per node, media duration |
| façade and ergonomics | the public classes (feature 006) |
