# Phase 0 Research: Schema-derived XML serialization core

**Feature**: `004-xml-serialization-core` | **Date**: 2026-08-11
**Method**: probes run against the pinned `xmlschema==3.4.3` on pyenv **3.11.9**, plus
inspection of library-written and hand-authored XML from the sibling repos. Probe scripts
are in the session scratchpad; the numbers below are measured, not inferred.

> Environment note: this repo's tests run under pyenv 3.11.9. Conda environments are not
> used for this project and must not be used to validate this work.

---

## R1 — The load-bearing premise: schema order derivation. **VERIFIED**

`content.iter_elements()` resolves `xs:extension` chains in declaration order, with type
and cardinality attached, exactly as the target design (§3.1) assumed.

Measured on `AudioCueType`:

```
autoload, description, enabled, id, loop, name, offset, post_go, postwait,
prewait, target, timecode, ui_properties,   <- CommonPropertiesType (13)
Media, outputs,                             <- MediaCueType
master_vol,                                 <- AudioCueType
fade_profiles [0..1]                        <- AudioCueType
```

- Not alphabetical: **confirmed**.
- `master_vol` before `fade_profiles`: **confirmed** — the exact constraint the hardcoded
  hack at `XmlBuilder.py:335-343` exists to fake.
- Types come attached (`PercentType`, `BoolType`, `CTimecodeType`, …) and cardinality is
  exposed as `min_occurs` / `max_occurs`.

**Decision**: proceed with derivation as designed. **Rationale**: the premise holds on the
pinned version. **Alternatives considered**: none — D2 settles this.

---

## R2 — `xs:all` breaks byte-identity if treated as ordered. **BLOCKER, resolved**

This is the most consequential finding of the research phase, and it is not in the target
design.

Two content models in the corpus are `xs:all`, where XSD declares order **irrelevant**:

| Type | Derived (`iter_elements`) | Emitted today |
|---|---|---|
| `CuemsScript` (anonymous root type) | `CueList, description, id, name, created, modified, ui_properties` | `CueList, created, description, id, modified, name, ui_properties` |
| `DmxSceneType` | `id, DmxUniverse` | (alphabetical rule → `DmxUniverse, id`) |

Verified against a real library-written file
(`cuems-editor/tests/fixtures/script_minimal.xml`): the emitted root order **is**
alphabetical and **does not** match declaration order. Naively adopting `iter_elements`
order would rewrite the root element of **every script file on disk** — a direct FR-010
violation, and one that would have surfaced only as a golden-test failure late in
implementation.

**Decision**: the ordering rule is two-branched, and both branches are schema-driven:

- `xs:sequence` (and `xs:choice` content) → **schema declaration order**. Authoritative.
- `xs:all` → the schema explicitly declares order free, so no declaration order exists to
  honour. The engine applies a **documented deterministic tie-break — sorted keys —**
  which is what the current code produces and therefore preserves the bytes.

**Rationale**: "the schema is the source of truth" includes the schema's statement that
order is unconstrained. Inventing an order where the schema declines to specify one is not
fidelity to the schema, it is a behaviour change. **Alternatives considered**: (a) use
`iter_elements` order everywhere — rejected, breaks byte-identity on every script;
(b) special-case the two types by name — rejected, that is F1's hardcoding in a new
costume. The rule keys off the content model, which is data from the schema.

**Spec impact**: FR-001 must be read as "order comes from the schema, including the
schema's declaration that order is free". Flagged for the spec in the plan's Deviations
section.

---

## R3 — The script root types are anonymous. **Design change**

`CuemsProject` and `CuemsScript` both have **anonymous** complex types. There is no
`CuemsScriptType` in the schema, so the target design's illustrative
`SCRIPT.bind('CuemsScriptType', CuemsScript)` cannot work as written.

```
CuemsProject : <ANONYMOUS> (sequence)
    CuemsScript : <ANONYMOUS> (all)
        CueList, description, id, name, created, modified, ui_properties
```

**Decision**: the registry keys on **either** a type qname **or** an element path
(`CuemsProject/CuemsScript`), with anonymous types bound by path. **Rationale**: it is the
minimum change that keeps bindings explicit and total. **Alternatives considered**: naming
the anonymous types in the XSD — rejected outright under D3 (no schema edits).

---

## R4 — `outputs.xsd` collides with `script.xsd` by design. **Explains X11**

Both declare `{https://stagelab.coop/cuems/}OutputsType`, with **different content**:

| Schema | `OutputsType` content |
|---|---|
| `script.xsd` | `AudioCueOutput, VideoCueOutput, DmxCueOutput` |
| `outputs.xsd` | `output` |

Same namespace, same type name, incompatible definitions. This is *why* `outputs.xsd` is
never loaded (X11) — the two cannot coexist in one namespace-aware schema object.
`outputs.xsd` loads cleanly on its own (root `CuemsOutputs`).

**Decision**: registries are **per schema**, each owning its own loaded schema object —
which the target design (§5) already specifies. `outputs.xsd` gets its own registry and
its own root; nothing merges the namespaces. This satisfies D13 (outputs accounted for
structurally) without an XSD edit. **Rationale**: the collision is a schema-level defect
that D3 defers; per-schema isolation routes around it without touching the file.
**Alternatives considered**: merging schemas into one namespace — impossible;
renaming a type — an XSD edit, forbidden.

**Recorded as a new deferred schema item** for the audit's X-series: `outputs.xsd`'s
`OutputsType` should be renamed or namespaced before outputs is ever completed.

---

## R5 — `CTimecodeType` is a complex type, not a simple one

```
CTimecodeType (choice) -> CTimecode : TimecodeType [1..1]
```

The `{"CTimecode": "00:00:00.000"}` wire shape everyone treats as a quirk is **stated by
the schema**. `settings.xsd` declares its own two-field variant.

**Decision**: adapters bind to **type qnames, complex or simple**. `CTimecodeType` gets an
adapter that reads and writes the single-child wrapper and yields a `CTimecode` object.
**Rationale**: keeps one adapter concept rather than splitting scalar and wrapper
handling. **Alternatives considered**: treating the wrapper as ordinary structure and
coercing in the model — rejected, that is exactly the property-setter coercion F18 comes
from.

---

## R6 — Wildcard content, precisely characterised

`UiPropertiesType`: `mixed=True`, one `XsdAnyElement` `[0..unbounded]`, plus an
`anyAttribute`. Nothing about its children is derivable — confirming X10 and the need for
the documented fallback (FR-009): preserve insertion order, pass scalars through untyped.

---

## R7 — Attributes are a two-case problem, one of them a name clash

Across all six schemas only **two** attribute declarations exist:

- `UiPropertiesType` — `anyAttribute` (wildcard, part of R6).
- `DmxUniverseType` — `universe_num`, `xs:byte`, optional.

`DmxUniverseType` also declares an **element** named `universe_num`. With the converter's
`attr_prefix=''`, the decoded dict key `universe_num` is ambiguous between the two.

**Decision**: the field spec records attributes separately from elements and preserves
whatever today's converter produces for this collision; the golden test for the DMX corpus
files is the arbiter. **Rationale**: the ambiguity is pre-existing; 004 must reproduce it,
not resolve it. **Alternatives considered**: disambiguating with a prefix — a wire change,
forbidden here. **Recorded as a deferred schema item.**

---

## R8 — Content models are cyclic; derivation must memoise

`CueListType → CueListContentsType → CueListType` is a genuine cycle (`xs:choice` of six
cue types including `CueList`). Eager recursive derivation does not terminate.

**Decision**: derive lazily per type with a memo keyed `(schema_name, type_key)`; a
`TypeSpec` holds child **references**, resolved on demand. This is the same cache that
satisfies the performance budget. **Rationale**: one mechanism serves correctness and
SC-PERF-002.

---

## R9 — Inventory, for sizing

| Schema | Complex types with content | Other types | Root |
|---|---|---|---|
| `script` | 33 | 20 | `CuemsProject` |
| `settings` | 7 | 7 | `CuemsSettings` |
| `network_map` | 3 | 2 | `CuemsNetworkMap` |
| `project_mappings` | 11 | 3 | `CuemsProjectMappings` |
| `project_settings` | 1 | 1 | `CuemsProjectSettings` |
| `outputs` | 1 | 0 | `CuemsOutputs` |
| **Total** | **56** | **33** | |

Model classes available to bind: ~20 (`Cue`, `CueList`, `AudioCue`, `VideoCue`, `DmxCue`,
`ActionCue`, `FadeCue`, `MediaCue`, `Media`, `Region`, `DmxScene`, `DmxUniverse`,
`DmxChannel`, `CueOutput` ×3, `FadeProfile`, `FadeFunctionParameter`, `CuemsScript`).

So roughly **13 of script.xsd's 33 types have no bespoke class** and reach a generic today
by silent fallback. Per FR-007 each must be bound **explicitly to that same generic**.
Producing the exact list is an implementation task, done by instrumenting the current
`globals()` lookups over the whole corpus and recording every miss — measurement, not
guesswork.

**Adapter surface** (script.xsd simple types): 20 named types over four primitive bases.
Custom handling needed for `BoolType` (enum of `"True"`/`"False"` over `xs:string`),
`UuidType`/`TargetType`, `CTimecodeType` (R5), the six enum types (`PostGoType`,
`ActionType`, `FadeTypeType`, `FadeModeType`, `FadeCurveType`, `FadeFunctionIdType`), the
integer family (`PercentType`, `LoopType`, `ChannelNumberType`, `ChannelValueType`) and
the float family (`UnitFloat`, `PositiveUnitFloat`). Everything else uses `xmlschema`'s
native decoding — confirming the target design's §4 sizing.

---

## R10 — Serializer mechanics that byte-identity depends on

`XmlReaderWriter.write` uses **stdlib `ElementTree.write(encoding="utf-8",
xml_declaration=True)`**, not `lxml`. Output is therefore:

- declaration `<?xml version='1.0' encoding='utf-8'?>` — **single quotes**, ElementTree's
  spelling;
- **no indentation**, no trailing newline;
- empty elements as `<tag />`;
- `xsi:schemaLocation` carried on the root.

**Consequence for SC-003 (load-save idempotence).** Hand-authored corpus files are
indented and some declare `version="1.1"`. A first load-save **reformats** them, so
`save(load(x)) != x` for those inputs. Idempotence holds from the first save onward.

**Decision**: SC-003 is verified as **`save(load(save(load(x)))) == save(load(x))`** —
stability under repeated round-trips — rather than `save(load(x)) == x`. **Rationale**:
the latter is false today and is not a property the feature can or should establish.
Flagged to the spec in Deviations.

**Decision**: `lxml` stays out of the write path. **Rationale**: switching serializers
would change bytes wholesale.

---

## R11 — `xmlschema` API surface used, and its stability

| API | Used for | Stability |
|---|---|---|
| `XMLSchema11(path)` | schema loading; XSD 1.1 required by `xs:assert` (X7) | public, stable |
| `schema.types` / `schema.elements` | registry construction | public |
| `xsd_type.content.iter_elements()` | ordered field derivation (R1) | public; **the one real coupling** |
| `content.model` | `sequence` / `choice` / `all` discrimination (R2) | public attribute |
| `XsdElement.local_name/.type/.min_occurs/.max_occurs` | field specs | public |
| `xsd_type.attributes` | R7 | public |
| `XsdAnyElement` | wildcard detection (R6) | public class |
| `schema.to_dict(..., converter=…)` | decode | public |
| `XMLSchemaConverter` subclassing | D5 thin converter | public base |

The current `CMLCuemsConverter` imports `xmlschema.validators.wildcards.Xsd11AnyElement`
— a **non-public** path, and precisely the coupling D5 exists to remove. The new converter
must import only from the public surface.

**Decision**: pin `xmlschema==3.4.3` unchanged; add a test that fails loudly if
`iter_elements` ordering semantics change, so an upgrade cannot silently alter output.
**Rationale**: the whole design rests on R1; it deserves an explicit tripwire.

---

## R12 — Regression corpus, assembled

Per FR-022a, vendored and frozen from four sources:

| Source | Files | Notes |
|---|---|---|
| `cuems-utils/tests/data/` | 5 | settings, network_map, project_mappings, default_mappings, a deliberately-bad settings file |
| `cuems-engine/dev/test_xml_files/` | 17 | per-cue-type samples; one instance of **each** of the six schema types; `complex_test/` and `empty_test/` projects |
| `cuems-editor/tests/fixtures/` | 1 | `script_minimal.xml`, library-written |
| `cuems-common/etc/cuems/` | 1 | deployed `network_map.xml` |

The engine's tree is the only source of an `outputs.xml` instance and of complete project
directories. Generated documents from `create_script.py` cover the remaining cue types.

**Decision**: vendor under `tests/data/corpus/<source>/`, each directory carrying a
`PROVENANCE.md` recording origin, commit and date. **Rationale**: FR-022b — the suite must
pass on a lone checkout.

---

## Summary of decisions

| # | Decision | Drives |
|---|---|---|
| R1 | Derivation via `iter_elements()` proceeds as designed | whole feature |
| R2 | Order rule branches on content model; `xs:all` → sorted tie-break | FR-001, FR-010 |
| R3 | Registry keys on type qname **or** element path | FR-007 |
| R4 | One registry per schema; `outputs.xsd` isolated | FR-016, FR-018, D13 |
| R5 | Adapters bind complex types too (`CTimecodeType`) | FR-008 |
| R6 | Wildcard fallback for `UiPropertiesType` | FR-009 |
| R7 | Attributes modelled separately; `universe_num` clash preserved | FR-010 |
| R8 | Lazy, memoised derivation | FR-006, SC-PERF-002 |
| R9 | ~13 generic bindings enumerated by instrumentation | FR-007 |
| R10 | stdlib ElementTree retained; SC-003 restated as round-trip stability | FR-010, SC-003 |
| R11 | Pin held; upgrade tripwire test added | FR-006 |
| R12 | Corpus vendored with provenance | FR-022a/b |
