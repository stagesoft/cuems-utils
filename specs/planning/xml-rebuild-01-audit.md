# XML infrastructure rebuild — Part 1: Audit

**Status:** draft for review
**Date:** 2026-08-10
**Repo:** `cuems-utils` @ `07a7f9f` (main)
**Scope:** `src/cuemsutils/xml/` primarily; coupled surfaces in `src/cuemsutils/cues/`,
`src/cuemsutils/helpers.py`, and the consumer repos `cuems-engine`, `cuems-editor`,
`cuems-nodeconf`.

This is the diagnosis document. It states what exists, what is wrong with it, with
evidence, and what must keep working. It proposes no solution — that is Part 2.
Findings here double as the regression checklist the rebuild is measured against.

---

## 0. Agreed framing

Four decisions were taken before this audit was written; they constrain everything
downstream.

| # | Decision | Consequence |
|---|----------|-------------|
| D1 | **Free hand, coordinated bump.** No API is frozen. | The rebuild may redesign the public surface. `cuems-engine`, `cuems-editor` and `cuems-nodeconf` get migration notes and land together as a minor-version bump. |
| D2 | **Schema-driven single source.** | Datatypes, cardinality and element order are derived from the XSD rather than re-encoded in Python twice. `str_to_value` heuristics and `STRING_TYPED_KEYS` are targets for removal, not preservation. |
| D3 | **XSDs auditable, changes deferred.** | This audit records schema defects (§6) but the rebuild stays byte-compatible with every `script.xml` / `settings.xml` / `network_map.xml` currently on disk. Schema changes are a separate, later workstream. |
| D4 | **Audit before design.** | This document. |

### Baseline

- `hatch test` — **557 passed in 7.44s**, zero failures, zero skips. Whatever else is
  true, the current system works for the paths it is exercised on.
- `src/cuemsutils/xml/` is **1356 LOC** across 5 modules.
- Pinned deps: `xmlschema==3.4.3`, `lxml==6.1.0`.

---

## 1. Architecture as it stands

### 1.1 The nominal pipeline

```
                    ┌──────────────────────────────────────────┐
   XML file ──read──►  xmlschema.XMLSchema11.to_dict()         │
                    │    └─ converter = CMLCuemsConverter      │
                    └──────────────┬───────────────────────────┘
                                   │  nested dict
                    ┌──────────────▼───────────────────────────┐
                    │  CuemsParser(...).parse()                │
                    │    dispatch: globals()[tag + 'Parser']   │
                    └──────────────┬───────────────────────────┘
                                   │  cue objects (dict subclasses)
                    ┌──────────────▼───────────────────────────┐
                    │  XmlBuilder(...).build()                 │
                    │    dispatch: globals()[cls + 'XmlBuilder']│
                    └──────────────┬───────────────────────────┘
                                   │  ElementTree
   XML file ◄─write─── schema_object.validate() ──► XSD
```

The XSD sits at **both ends as a validator** and nowhere in the middle as a source of
truth. That single fact generates most of what follows.

### 1.2 There are four independent XML writers, not one

| # | Writer | Location | Used by | Status |
|---|--------|----------|---------|--------|
| 1 | `*XmlBuilder` class family | [XmlBuilder.py](../../src/cuemsutils/xml/XmlBuilder.py) | `XmlReaderWriter.write_from_object` | **live** |
| 2 | `build_xml_dict` / `CuemsDict.build` | [helpers.py:49-66](../../src/cuemsutils/helpers.py#L49-L66) | reached from `GenericCueXmlBuilder.build` [XmlBuilder.py:104-108](../../src/cuemsutils/xml/XmlBuilder.py#L104-L108) | **live**, and a *different* algorithm from #1 |
| 3 | `Settings.data2xml` / `Settings.buildxml` | [Settings.py:66-100](../../src/cuemsutils/xml/Settings.py#L66-L100) | **nobody** | **dead** |
| 4 | `ProjectMappings.process_network_mappings` (reshaper, not writer, but a third dict-shape authority) | [Settings.py:245-271](../../src/cuemsutils/xml/Settings.py#L245-L271) | **nobody** | **dead** |

Verified by grep across all sibling repos: #3 and #4 have zero call sites anywhere.
`CuemsNodeDictXmlBuilder` [XmlBuilder.py:73](../../src/cuemsutils/xml/XmlBuilder.py#L73)
and `CuemsNodeDictParser` [Parsers.py:313](../../src/cuemsutils/xml/Parsers.py#L313) are
likewise unreferenced — `cuems-nodeconf` ships its own `node_listXmlBuilder`/
`node_listParser` instead.

### 1.3 There are two readers with different decode settings

| Reader | `strip_namespaces` | `dict_class`/`list_class` | `attr_prefix` |
|--------|--------------------|---------------------------|---------------|
| `XmlReaderWriter.read` [XmlReaderWriter.py:89-95](../../src/cuemsutils/xml/XmlReaderWriter.py#L89-L95) | `False` | converter defaults | converter default (`''`) |
| `Settings.read` [Settings.py:53-61](../../src/cuemsutils/xml/Settings.py#L53-L61) | `True` | explicit `dict`/`list` | `''` |

Same converter class, two configurations, no documented reason. Anything reasoning about
"the shape `to_dict` returns" is right for at most one of them.

### 1.4 Dispatch is `globals()` name-mangling, twice, plus a third registry

- Builders: `globals()[type(obj).__name__ + 'XmlBuilder']`
  [XmlBuilder.py:29-37](../../src/cuemsutils/xml/XmlBuilder.py#L29-L37)
- Parsers: `globals()[tag + 'Parser']`
  [Parsers.py:56-65](../../src/cuemsutils/xml/Parsers.py#L56-L65)
- Tag → cue class: `globals()[tag]`
  [Parsers.py:67-73](../../src/cuemsutils/xml/Parsers.py#L67-L73), fed by
  `from ..cues import *` [Parsers.py:1](../../src/cuemsutils/xml/Parsers.py#L1)

All three miss silently and fall back to a generic. A typo in a class name is not an
error; it is a change in output shape discovered later, at validation time or in the
field.

---

## 2. Findings — structural

### F1 · **CRITICAL** · Element order is an emergent property of three unrelated files

`script.xsd` types are `xs:sequence`, so element order is **mandatory**.
`CommonPropertiesType` [script.xsd:52-73](../../src/cuemsutils/xml/schemas/script.xsd#L52-L73)
declares: `autoload, description, enabled, id, loop, name, offset, post_go, postwait,
prewait, target, timecode, ui_properties` — strictly alphabetical.

Nothing in the builder sorts or orders anything. `GenericCueXmlBuilder.build` simply
iterates `self._object.items()`. The order that reaches the XML comes from:

1. the **literal declaration order** of `REQ_ITEMS` in
   [cues/Cue.py:7-21](../../src/cuemsutils/cues/Cue.py#L7-L21), which happens to be
   alphabetical, replayed by `Cue.items()`
   [cues/Cue.py:321-327](../../src/cuemsutils/cues/Cue.py#L321-L327); and
2. `ensure_items`, which ends with `x = {k: x[k] for k in sorted(x.keys())}`
   [helpers.py:98](../../src/cuemsutils/helpers.py#L98); and
3. `sorted(REQ_ITEMS.keys())` in the subclass `items()` overrides
   ([AudioCue.py:60](../../src/cuemsutils/cues/AudioCue.py#L60),
   [VideoCue.py:65](../../src/cuemsutils/cues/VideoCue.py#L65)).

So: **XSD element order is satisfied by an alphabetical-sort coincidence, maintained by
hand, in files that never mention the XSD.** No test asserts the correspondence. Adding a
field whose name sorts into the wrong position produces a save-time validation failure
with no compile-time or review-time signal.

**And the coincidence already broke once.** `AudioCueType`
[script.xsd:277-286](../../src/cuemsutils/xml/schemas/script.xsd#L277-L286) requires
`master_vol` **then** `fade_profiles` — not alphabetical (`f` < `m`). The fix was to
hardcode the emit into the middle of the builder's key loop:

```python
# XmlBuilder.py:335-343
cls_name = type(self._object).__name__
if key == 'master_vol' or (key == 'opacity' and cls_name == 'VideoCue'):
    fps = self._object.get('fade_profiles')
    ...
```

An ordering constraint from the schema, expressed as a string comparison against a field
name, inside a loop, in the serializer. This is the clearest single argument for D2.

### F2 · **HIGH** · Builder and parser encode the same rules twice, in different idioms

The identical `isinstance` cascade — `VALUE_TYPES` → `None` → `list` → `GenericDict` →
else-recurse — is copy-pasted **seven times** with quiet divergences:

| Class | Line | `None` → | `list` → | `dict` → |
|-------|------|----------|----------|----------|
| `CuemsScriptXmlBuilder` | [56](../../src/cuemsutils/xml/XmlBuilder.py#L56) | skipped entirely | *(no branch)* | flattened one level |
| `CueListXmlBuilder` | [85](../../src/cuemsutils/xml/XmlBuilder.py#L85) | empty element | recurse per item | recurse |
| `GenericCueXmlBuilder` | [110](../../src/cuemsutils/xml/XmlBuilder.py#L110) | empty element | recurse per item | flattened one level |
| `GenericComplexSubObjectXmlBuilder` | [141](../../src/cuemsutils/xml/XmlBuilder.py#L141) | empty element | `self.recurser` | `self.recurser` |
| `MediaXmlBuilder` | [176](../../src/cuemsutils/xml/XmlBuilder.py#L176) | empty element | builder per item | `self.recurser` |
| `OutputsXmlBuilder` | [197](../../src/cuemsutils/xml/XmlBuilder.py#L197) | empty element | `recurser` per item | `self.recurser` |
| `CueOutputsXmlBuilder` | [245](../../src/cuemsutils/xml/XmlBuilder.py#L245) | empty element | `self.recurser` | `self.recurser` |
| `MediaCueXmlBuilder` | [313](../../src/cuemsutils/xml/XmlBuilder.py#L313) | empty element | builder per item | flattened one level |

Plus `nodeXmlBuilder` in `cuems-nodeconf`
([NodeXmlBuilders.py:29-48](../../../cuems-nodeconf/NodeXmlBuilders.py)) — a ninth copy,
in another repo.

`OutputsXmlBuilder.recurser` and `GenericComplexSubObjectXmlBuilder.recurser` are two
further near-duplicates of each other that differ in list handling
([XmlBuilder.py:154-168](../../src/cuemsutils/xml/XmlBuilder.py#L154-L168) vs
[213-235](../../src/cuemsutils/xml/XmlBuilder.py#L213-L235)).

The parser side re-derives the same tree shape independently
([Parsers.py:127-219](../../src/cuemsutils/xml/Parsers.py#L127-L219)), with its own
`dict`/`list`/scalar trichotomy and its own fallback rules. **Nothing checks that the two
agree.** Round-trip fidelity is currently guaranteed only by the tests that happen to
exercise a given field.

**Cost per new field: three edits** (cue class `REQ_ITEMS` + property, XSD, and usually a
builder or parser special case), with correctness confirmed only at runtime.

### F3 · **HIGH** · Six of fourteen builders return `None`; the top-level dispatch assumes otherwise

`XmlBuilder.build` assigns the return value:

```python
# XmlBuilder.py:44-46
self.xml_tree = builder_class(self._object, xml_tree = xml_root).build()
self.xml_tree = ElementTree(self.xml_tree)
```

But these builders have no `return` statement at all — they return `None`:
`GenericCueXmlBuilder` ([100](../../src/cuemsutils/xml/XmlBuilder.py#L100), which also has
a bare `return` at [108](../../src/cuemsutils/xml/XmlBuilder.py#L108)),
`GenericSimpleSubObjectXmlBuilder` ([133](../../src/cuemsutils/xml/XmlBuilder.py#L133)),
`GenericComplexSubObjectXmlBuilder` ([138](../../src/cuemsutils/xml/XmlBuilder.py#L138)),
`MediaXmlBuilder` ([173](../../src/cuemsutils/xml/XmlBuilder.py#L173)),
`CueOutputsXmlBuilder` ([237](../../src/cuemsutils/xml/XmlBuilder.py#L237)),
`DmxSceneXmlBuilder` ([268](../../src/cuemsutils/xml/XmlBuilder.py#L268)).

Nested calls discard the result (`sub_object_element = ...build()` — assigned, never
read), so this is invisible in practice. But any root object that dispatches to one of
them yields `ElementTree(None)`. The top-level entry point is only safe for the object
types that happen to have a returning builder. It is a latent crash gated on a
coincidence, and it makes the `build()` contract unstatable.

### F4 · **HIGH** · `DmxSceneXmlBuilder` swallows all exceptions — silent data loss on write

```python
# XmlBuilder.py:270-287
def build(self):
    try:
        ...
    except Exception as e:
        Logger.error(f"Error building DmxSceneXmlBuilder: {str(e)} {type(e)}")
```

A failure mid-scene leaves a partially-built subtree, returns `None`, and the write
proceeds. Depending on what was already emitted, the result either fails XSD validation
with a message pointing nowhere near the cause, or **validates while missing DMX channel
data**. A serializer must not have a catch-all.

### F5 · **MEDIUM** · `CMLCuemsConverter` is a fork pinned to `xmlschema` internals, with stale provenance

[CMLCuemsConverter.py](../../src/cuemsutils/xml/CMLCuemsConverter.py) is a copy of
`xmlschema`'s converter with edits. It imports non-public internals
(`xmlschema.validators.wildcards.Xsd11AnyElement`) and reimplements `element_decode` /
`element_encode` against `map_content` / `map_attributes` / `unmap_qname` semantics.

- The file header says *"works with pip3 install xmlschema==1.2.2"*
  ([XmlReaderWriter.py:1-2](../../src/cuemsutils/xml/XmlReaderWriter.py#L1-L2) says the
  same; `Settings.py:1-2` says **1.1.2**). The pin is actually **3.4.3**. Three
  statements, all wrong, none load-bearing but all misleading.
- `__init__` accepts `namespaces` and then passes `namespaces=None` to `super()`
  ([:26](../../src/cuemsutils/xml/CMLCuemsConverter.py#L26)) — caller-supplied namespaces
  are **silently discarded**.
- `indent` is stored and never used.

**The one substantive behavioural change is the root cause of several downstream
workarounds.** For repeated elements, `element_decode` replaces the parent dict with a
*list of single-key dicts*:

```python
# CMLCuemsConverter.py:83-86
if xsd_child is not None and not xsd_child.is_single():
    result_dict = [{name:value}]
```

So `<node_list><node/><node/></node_list>` decodes to `[{'node': {...}}, {'node': {...}}]`
rather than `{'node': [{...}, {...}]}`. Every consumer then has to unwrap it by hand:

- `CuemsNodeDictParser` [Parsers.py:313-321](../../src/cuemsutils/xml/Parsers.py#L313-L321)
- `node_listParser` in `cuems-nodeconf`
- `mediaParser` regions unwrapping via `get_contained_dict`
  [Parsers.py:270-277](../../src/cuemsutils/xml/Parsers.py#L270-L277)
- `NetworkMap.get_nodes_by_adoption` [Settings.py:139-149](../../src/cuemsutils/xml/Settings.py#L139-L149)
- `ProjectMappings._validate_custom_templates`, which unwraps `output_wrap.get('output')`
  [Settings.py:215-218](../../src/cuemsutils/xml/Settings.py#L215-L218)
- `ProjectMappings.process_network_mappings`, whose own comment says it plainly:
  *"the converter is not getting what we really intended but we'll correct it here by the
  moment"* [Settings.py:247-249](../../src/cuemsutils/xml/Settings.py#L247-L249)

One converter decision, six hand-written compensations, one of them dead.

### F6 · **MEDIUM** · `str_to_value` guesses types the XSD already declares

[Parsers.py:81-108](../../src/cuemsutils/xml/Parsers.py#L81-L108) decides a value's Python
type by trying, in order: `STRING_TYPED_KEYS` denylist → `'none'/'null'/''` → `isdigit()`
→ `float` → `strtobool` → `Uuid` → give up and return the string.

Meanwhile `script.xsd` already states the type of every one of those elements —
`cms:PercentType` is `xs:integer` 0..100, `cms:LoopType` is `xs:integer` ≥ -1,
`cms:UuidType` is a pattern-restricted string, and so on (§6 has the inventory). The
information is present and ignored.

Consequences, all of them real:

- The ClickUp **869cqbpxa** class of bug: a cue named `"n"` became `False`, `"1"` became
  `int 1`, `"none"` became `None` → empty `<name/>` → XSD `minLength` violation → hard
  save error. Fixed by a denylist whose own comment explains that most of its entries are
  "defensive only" and shielded by accidental bypasses elsewhere
  ([Parsers.py:16-36](../../src/cuemsutils/xml/Parsers.py#L16-L36)).
- The denylist is **key-name-based and global**. It cannot express "`name` is free text on
  a cue but an enum on an output" — the schema can.
- `isdigit()` loses leading zeros: `"007"` → `7`.
- `float()` accepts `"nan"`, `"inf"`, `"-inf"` — any such text silently becomes a float
  special value.
- `'id'` is deliberately absent from the denylist because the `Uuid()` attempt is *the
  only thing* that constructs `Uuid` objects on parse — parsers assign via raw
  `dict.__setitem__` and never hit the property setters. So a type-guessing heuristic is
  load-bearing for object identity.

### F7 · **HIGH — CONFIRMED BY REPRODUCTION** · `cuems-nodeconf` calls `str_to_value` without a key; the 869cqbpxa fix does not protect node data

```python
# cuems-nodeconf/NodeXmlBuilders.py:78
dict_value = self.str_to_value(dict_value)     # no key= argument
```

`STRING_TYPED_KEYS` is only consulted when `key` is passed. Every field of every node in
`network_map.xml` is therefore parsed with the **unpatched** heuristic — including `name`,
and the identity fields `alias` and `hostname` added in `feat/node-identity`
([network_map.xsd:28-31](../../src/cuemsutils/xml/schemas/network_map.xsd)).

**Reproduced** (scripts in Appendix C). Feeding one schema-valid node through the real
`nodeParser`:

| field | in | out | type | verdict |
|-------|-----|-----|------|---------|
| `uuid` | `'3f25…3301'` | `3f25…3301` | `Uuid` | ok |
| `mac` | `'aa:bb:cc:dd:ee:ff'` | unchanged | `str` | ok |
| `name` | `'none'` | `None` | `NoneType` | **coerced** |
| `node_type` | `'slave'` | unchanged | `str` | ok |
| `ip` | `'10.0.0.7'` | unchanged | `str` | ok |
| `adopted` | `'True'` | `True` | `bool` | coerced *(intended)* |
| `online` | `'True'` | `True` | `bool` | coerced *(intended)* |
| `role_id` | `'n'` | `False` | `bool` | **coerced** |
| `alias` | `'off'` | `False` | `bool` | **coerced** |
| `hostname` | `'007'` | `7` | `int` | **coerced** |

Control: the same values through `cuems-utils`' own `CuemsParser` survive intact
(`name='none'`, `description='off'`) — confirming the cause is the missing `key=`, not the
heuristic itself. The `adopted`/`online` coercions are deliberate and relied upon
(`CuemsNodeConf.py:452`: *"Boolean fields are already parsed by CuemsParser using
strtobool"*); the other four are not.

**Two severities, and the silent one is worse.** Writing the parsed node back:

- `name` → `<name/>` → **hard failure**, `XMLSchemaValidationError` on
  `NonEmptyString`'s `.*[^\s].*` pattern. A node named `"none"` cannot be persisted at all.
- `role_id`, `alias`, `hostname` → `False`, `False`, `7` — all **schema-valid**. They
  validate, write to disk, and **silently replace operator data**. `role_id` is assigned
  by nodeconf during adoption and `alias` is operator-defined free text, so both are
  squarely in strtobool's blast radius (`n`, `y`, `t`, `f`, `on`, `off`, `no`, `yes`, `0`,
  `1`). `hostname` loses leading zeros.

These are exactly the `feat/node-identity` fields. This is a **live cross-repo bug**: the
defect fixed in `cuems-utils` is still open on the `cuems-nodeconf` path, and it is still
present on the in-flight `feat/nodeconf-reenable` branch
(`cuemsnodeconf/NodeXmlBuilders.py:80`).

### F8 · **MEDIUM** · `cuems-nodeconf` extends the system by monkeypatching module globals

```python
# cuems-nodeconf/NodeXmlBuilders.py:83-89
XmlBuilderModule.node_listXmlBuilder = node_listXmlBuilder
XmlBuilderModule.nodeXmlBuilder      = nodeXmlBuilder
ParsersModule.node_listParser        = node_listParser
ParsersModule.nodeParser             = nodeParser
```

This works *only* because dispatch reads `globals()`. It is the de-facto extension API and
it is entirely undocumented on the `cuems-utils` side — nothing in this repo indicates that
another repo writes into these module namespaces. Import order is load-bearing
(`import NodeXmlBuilders` must precede any read/write; see the module docstring and
[CuemsNodeConf.py:18](../../../cuems-nodeconf/CuemsNodeConf.py)).

Under D1 this becomes a real registration API and `cuems-nodeconf` migrates in the same
bump. It is the single largest external migration item.

### F9 · **LOW–MEDIUM** · Defensive code that cannot fire, and guards that do nothing

- `CuemsParser.__init__` catches `KeyError` but `next(iter(init_dict))` on an **empty
  dict** raises `StopIteration`, which is uncaught
  [Parsers.py:43-53](../../src/cuemsutils/xml/Parsers.py#L43-L53).
- `mediaParser.parse`: `if not self.init_dict: pass` — a no-op that reads as a guard
  [Parsers.py:261-262](../../src/cuemsutils/xml/Parsers.py#L261-L262). Followed by a bare
  `except:` that converts *any* `Media()` failure into a misleading
  `KeyError("Media key not found in dictionary")`
  [Parsers.py:263-267](../../src/cuemsutils/xml/Parsers.py#L263-L267).
- `outputsParser.__init__` accepts `class_string` and `parent_class` and **assigns
  neither** [Parsers.py:284-285](../../src/cuemsutils/xml/Parsers.py#L284-L285). It never
  initialises `self.item_op`, so an empty `init_dict` raises `AttributeError` on the
  `return`. With multiple keys, the last one silently wins
  [Parsers.py:287-297](../../src/cuemsutils/xml/Parsers.py#L287-L297).
- `NoneTypeXmlBuilder` carries its own `# TODO: clean, not need anymore?`
  [XmlBuilder.py:355](../../src/cuemsutils/xml/XmlBuilder.py#L355).

### F10 · **LOW** · Dead code and stale scaffolding

- ~50 lines of commented-out parsers: `CTimecodeKeyParser`, `offsetParser`,
  `prewaitParser`, `postwaitParser`, `in_timeParser`, `out_timeParser`, `regionsParser`
  [Parsers.py:234-256](../../src/cuemsutils/xml/Parsers.py#L234-L256),
  [299-311](../../src/cuemsutils/xml/Parsers.py#L299-L311).
- Dead-on-arrival members listed in §1.2: `Settings.data2xml`, `Settings.buildxml`,
  `ProjectMappings.process_network_mappings`, `CuemsNodeDictXmlBuilder`,
  `CuemsNodeDictParser`.
- Commented-out alternative at [XmlBuilder.py:13](../../src/cuemsutils/xml/XmlBuilder.py#L13)
  and [40](../../src/cuemsutils/xml/XmlBuilder.py#L40); a stray ad-hoc comment describing
  target/uuid shapes at [16](../../src/cuemsutils/xml/XmlBuilder.py#L16).
- `XmlReader` / `XmlWriter` deprecated since **0.0.7**
  [XmlReaderWriter.py:101-113](../../src/cuemsutils/xml/XmlReaderWriter.py#L101-L113) yet
  still used in `cuems-nodeconf` **production** code (`CuemsNodeConf.py:20`,
  `CuemsHwDiscovery.py:17`) and in this repo's own `tests/test_xml.py:201`.
- Module naming is PascalCase (`XmlBuilder.py`, `Parsers.py`, `Settings.py`) against
  PEP 8. Cosmetic, but D1 makes this the only cheap moment to change it.

### F12 · **HIGH** · `Media.set_regions` silently discards its own coercion

```python
# cues/MediaCue.py:231-236
if not isinstance(regions, list):
    regions = [regions]
for r in regions:
    if not isinstance(r, Region):
        r = Region(r)          # rebinds the loop-local; result is thrown away
super().__setitem__('regions', regions)
```

`r = Region(r)` rebinds a loop variable and is never written back, so `regions` is stored
exactly as received. The docstring promises *"If not already Region objects, they will be
converted"* — the conversion is dead code. A caller passing plain dicts gets plain dicts
stored, and every downstream `isinstance(x, Region)` check silently takes the wrong branch.

This is the canonical instance of the failure the whole-chain round-trip requirement (D14)
exists to surface: a "simple dict" surviving where a typed object was expected, invisible
because the XML layer's `isinstance` cascades treat `dict` and `CuemsDict` as
interchangeable anyway. Note that `mediaParser` compensates on the *parse* side by building
`Region(...)` explicitly [Parsers.py:270-277](../../src/cuemsutils/xml/Parsers.py#L270-L277)
— which is why the XML path works and hides the setter defect.

### F13 · **HIGH** · JSON is a fourth serialization format, and it is asymmetric too

`__json__` is implemented independently on `Cue`, `CuemsScript`, `MediaCue`, `DmxCue`,
`FadeCue`, `FadeProfile`, `CueOutput` and `Uuid` — eight hand-written projections of the
object model. There is no inverse: JSON *ingestion* is `CuemsParser`, which is the XML
parser. So the JSON leg of the chain crosses **two more independent implementations** of
the same mapping, with nothing checking they agree — the exact F2 asymmetry, in a third
format.

`CuemsScript.__json__` [CuemsScript.py:286-295](../../src/cuemsutils/cues/CuemsScript.py#L286-L295)
walks children calling `v.__json__()`, so a type missing the method degrades silently to
its `dict` repr. Combined with F12, this is how a `Region` becomes a bare dict and stays
one across a full editor save cycle.

### F11 · **LOW** · Logging is inconsistent and occasionally hot

`GenericCueXmlBuilder.build` and `MediaCueXmlBuilder.build` log at **INFO** on every
single cue ([XmlBuilder.py:102-103](../../src/cuemsutils/xml/XmlBuilder.py#L102-L103),
[310-311](../../src/cuemsutils/xml/XmlBuilder.py#L310-L311)), including the full object
repr. `DmxSceneXmlBuilder` logs at DEBUG per key. `get_builder_class` has its debug line
commented out [XmlBuilder.py:35](../../src/cuemsutils/xml/XmlBuilder.py#L35) while its
parser twin logs [Parsers.py:61-63](../../src/cuemsutils/xml/Parsers.py#L61-L63). A
1000-cue script writes 2000 INFO lines containing every field value.

---

## 3. Consumer contract inventory

What the rebuild must either preserve or explicitly migrate. Grepped across all sibling
repos; test-only usages omitted except where they encode a contract.

### 3.1 `cuems-engine` — light coupling

| Site | Uses |
|------|------|
| `core/BaseEngine.py:17,509` | `XmlReaderWriter(schema_name="script", xmlfile=...)` → `.read_to_objects()` |
| `ControllerEngine.py:12` | `cuemsutils.xml.Settings.NetworkMap` |
| `dev/CuemsEngine_old.py:13` | deprecated `XmlReader` — dev/ only, ignorable |

**Contract:** `XmlReaderWriter(schema_name, xmlfile)` constructor + `read_to_objects()`
returning live cue objects. Nothing else. Cheapest consumer to keep working.

### 3.2 `cuems-editor` — the heaviest reader/writer

| Site | Uses |
|------|------|
| `CuemsDBProject.py:8-9` | `CuemsParser`, `XmlReaderWriter` |
| `CuemsDBProject.py:280,408,487,724` | `CuemsParser(data).parse()` on **frontend JSON payloads**, not XML-derived dicts |
| `CuemsDBProject.py:799,811` | `XmlReaderWriter(...).write_from_object()` / `.read()` |
| `repair_durations.py:39-40,204,230-231` | `read()` → `CuemsParser(...).parse()` → `write_from_object()` |

**Critical contract:** `CuemsParser` is used as a **JSON→objects** converter on data that
never went through `xmlschema`. It must accept dicts whose scalars are already native
Python types (the `not isinstance(_string, str)` passthrough at
[Parsers.py:97](../../src/cuemsutils/xml/Parsers.py#L97) exists for this). Any
schema-driven redesign has to keep a documented non-XML entry point, or the editor's whole
save path breaks. `tests/test_name_coercion.py:157` already flags this:
*"CuemsParser is what CuemsDBProject.update() runs on the frontend payload."*

### 3.3 `cuems-nodeconf` — deep coupling, must migrate

| Site | Uses |
|------|------|
| `NodeXmlBuilders.py:7-10` | imports `XmlBuilder`/`Parsers` **modules** to monkeypatch |
| `NodeXmlBuilders.py:14,25` | subclasses `CuemsScriptXmlBuilder`, `GenericCueXmlBuilder` |
| `NodeXmlBuilders.py:8` | imports `VALUE_TYPES` constant |
| `NodeXmlBuilders.py:10` | imports `GenericDict`, `GenericParser` |
| `NodeXmlBuilders.py:83-89` | writes four names into module globals (F8) |
| `CuemsNodeConf.py:20`, `CuemsHwDiscovery.py:17` | deprecated `XmlReader`/`XmlWriter` |

Depends on **internal** classes and a **private constant**, and mutates module namespaces.
Every one of these is a migration item.

### 3.4 In-repo

`create_script.py:12,198` — `XmlReaderWriter(schema_name="script", xmlfile=None)`. Note
`xmlfile=None` as a valid "build but don't write" mode; `validate_object` and
`build_xml_from_object` support it.

---

## 4. Behaviour that must survive the rebuild

Derived from the current test suite plus code that exists only to preserve a behaviour.
This is the acceptance checklist for Part 3.

**Round-trip fidelity**

1. `write_from_object` → `read_to_objects` preserves every cue type: `CueList`,
   `AudioCue`, `VideoCue`, `DmxCue`, `ActionCue`, `FadeCue` (`test_xml.py`,
   `test_fade_cue.py`).
2. Nested `CueList` recursion to arbitrary depth (`CueListContentsType` is a recursive
   `xs:choice`).
3. `CTimecode` fields (`offset`, `prewait`, `postwait`) survive object → XML → object
   (`unit/test_ctimecode.py`).
4. `Uuid` fields stay `Uuid` instances, not `str` — see F6 on why this is fragile.
5. `canvas_region` normalized floats round-trip within `_CONTAINMENT_EPS = 1e-6`
   (`test_canvas_region_roundtrip.py`).
6. `fade_profiles` round-trip on both `AudioCue.master_vol` and `VideoCue.opacity`, with
   correct XSD element ordering (`integration/test_mediacue_fade_roundtrip.py`,
   `contract/test_mediacue_fade_schema_contract.py`).
7. Media `duration` validation on write (`unit/test_media_duration.py`).

**Type-coercion guarantees (869cqbpxa)**

8. Every one of the 44+ `test_name_coercion.py` cases: names/descriptions/file names that
   look like numbers, booleans or `none` stay strings, through both the XML path and the
   direct-`CuemsParser` (editor JSON) path.

**Cross-format**

9. `Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings` continue to read their
   schemas (`test_project_mappings.py`, `test_configmanager.py`,
   `integration/test_default_mappings_valid.py`).
10. `ProjectMappings` semantic validation the XSD cannot express: canvas_region
    containment, ≤1 custom template per node (`Settings.py:186-243`).
11. `create_script.py` completeness (`integration/test_create_script_completeness.py`).

**Compatibility**

12. **Every existing on-disk XML file parses unchanged** (D3). Byte-identical output is
    *not* required; schema-valid and semantically-identical output is.
13. Write performance does not regress (`integration/test_mediacue_fade_performance.py`).

---

## 5. Why the current design costs what it costs

Consolidating the findings into the causal chain:

```
XSD used only as a validator, never as a source of truth   (root)
   │
   ├─► shape rules re-encoded independently in builder and parser      → F2
   │     └─► 9 copies of one cascade across 2 repos; no agreement check
   │
   ├─► element order re-encoded as alphabetical REQ_ITEMS + sorted()   → F1
   │     └─► breaks where XSD is non-alphabetical → hardcoded key hack
   │
   ├─► datatypes re-encoded as runtime guessing                        → F6
   │     └─► 869cqbpxa → key-name denylist → still unpatched in nodeconf → F7
   │
   └─► dispatch by globals() name-mangling, silent fallback            → F8
         └─► external repo extends by monkeypatching module namespaces

CMLCuemsConverter's repeated-element decode shape                      → F5
   └─► 6 hand-written unwrapping compensations across 2 repos
```

Every arrow is a place where adding one field costs more than one edit, and where a
mistake is invisible until runtime.

---

## 6. XSD audit — findings recorded, changes deferred (D3)

The schemas are in noticeably better shape than the Python. `script.xsd` defines **20
named simple types** and uses them consistently; almost every element has a declared type.
This is what makes D2 feasible — see §7.

Defects found, **all deferred**:

| # | Finding | Impact if fixed later |
|---|---------|-----------------------|
| X1 | `BoolType` is `xs:string` restricted to `"True"`/`"False"` (Python `repr` spelling), not `xs:boolean` — in both [script.xsd:450-455](../../src/cuemsutils/xml/schemas/script.xsd#L450-L455) and [network_map.xsd](../../src/cuemsutils/xml/schemas/network_map.xsd). This is *why* `strtobool` exists on the read side. | File-format migration: `xs:boolean` accepts `true`/`false`/`1`/`0`, not `True`/`False`. Breaks every existing file. Genuinely deferred. |
| X2 | `TimecodeType` (`HH:MM:SS.mmm` pattern) is declared but **never used** — all six timecode elements use `CTimecodeType`. Dead type. | Trivially removable. |
| X3 | `EmptyStringType` defined, never referenced. Dead type. | Trivially removable. |
| X4 | `TargetType` permits the empty string via `\|()` in its pattern *and* `minLength=0`, while `UuidType` requires exactly 36 chars. Two spellings of "uuid or nothing". | Consolidation opportunity. |
| X5 | `CommonPropertiesType` uses `xs:sequence` (order-enforcing) while the `CuemsScript` root uses `xs:all` (order-free) [script.xsd:22-36](../../src/cuemsutils/xml/schemas/script.xsd#L22-L36). Inconsistent, and the `xs:sequence` choice is what creates F1. | Switching cue types to `xs:all` would eliminate F1 at the schema level. **Superseded** — the §9 proposal removes F1 without touching the schemas, so this stays deferred. |
| X6 | ~~Commented-out `xs:all` at script.xsd:214-220 is a prior attempt at X5.~~ **CORRECTED — this claim was wrong.** | See correction below. |
| X10 | `UiPropertiesType` is `xs:anyType` [script.xsd:210-213](../../src/cuemsutils/xml/schemas/script.xsd#L210-L213) — deliberately schema-free, so the frontend can store arbitrary keys. | **Constrains D2**: no type, order or cardinality can be derived for `ui_properties` content. The schema-driven design needs a defined "wildcard" fallback. This is also why `get_class('ui_properties')` misses and lands on `GenericDict` — the bypass the `STRING_TYPED_KEYS` comment describes. |
| X11 | `outputs.xsd` is **never loaded**. No `get_pkg_schema('outputs')` call exists in this repo or any sibling; output types are defined inline in `script.xsd` instead. | **Not dead — an open end.** Per review: outputs is an unfinished concept that must be accounted for in the target structure rather than deleted. See D13. |
| X12 | `regions` is likewise unfinished. `RegionsType`/`RegionType` exist in `script.xsd` [183-206](../../src/cuemsutils/xml/schemas/script.xsd#L195-L206), `Region` exists in `cues/MediaCue.py:22`, `regionsParser` is **commented out** [Parsers.py:299-311](../../src/cuemsutils/xml/Parsers.py#L299-L311), and `mediaParser` unwraps regions by hand [Parsers.py:270-277](../../src/cuemsutils/xml/Parsers.py#L270-L277). | Same disposition as X11 — account for it in the target structure. See D13 and F12. |

### Added by feature 004 (2026-08-11) — measured during implementation

Five further schema-level findings, all **recorded and deferred** under D3. Each was found
by measurement against the frozen corpus rather than by reading the schemas.

| # | Finding | Impact if fixed later |
|---|---------|-----------------------|
| X13 | `gradient_osc_port` was added to `NodeConfType` in `settings.xsd` as **required** (no `minOccurs="0"`) in 0.1.0rc8. Every settings file written before it became invalid — including the ones this project itself shipped at `v0.1.0rc2` and `v0.1.0rc7`, both vendored under `tests/data/corpus/negative/`. | One-attribute fix (`minOccurs="0"` plus a default), but it changes what the library **accepts**, so it is a behaviour change. Scheduled under the schema-evolution convention adopted in feature 006 — `specs/planning/xml-rebuild-07-speckit-prompts.md` §5.1 and §9 rules 7–8, whose whole point is that a new required element is a breaking schema change. Two shipped releases are the evidence that convention is worth having. |
| X14 | **`outputs.xsd` declares an `OutputsType` that collides with `script.xsd`'s** — same namespace, same name, different content (`output` vs `AudioCueOutput, VideoCueOutput, DmxCueOutput`). Research R4. | The two cannot coexist in one namespace-aware schema object, which is the structural half of why X11 was never loadable. Feature 004 routes around it with per-schema registries and no XSD edit. A rename or re-namespacing is required before outputs is ever completed. |
| X15 | **The only `outputs.xml` in existence has a namespace typo.** `cuems-engine/dev/test_xml_files/outputs.xml` declares `https://stagelab.coop/cuems` — no trailing slash — against a `targetNamespace` of `https://stagelab.coop/cuems/`, so it fails with `the namespace … is not loaded`. | A second, **independent** reason nothing has ever validated against `outputs.xsd`, and it is in the instance rather than the schema. Feature 004 vendors a namespace-corrected copy so the sixth schema has a loadable instance at all (`tests/data/corpus/cuems-utils/outputs.xml`); the original stays vendored with its rejection pinned. Fixing the engine's file is a sibling-repo edit, deferred. |
| X16 | `DmxUniverseType` declares an **attribute and an element both named `universe_num`**. With the converter's `attr_prefix=''` the decoded dict key is ambiguous between the two. Research R7. | Disambiguating with a prefix is a wire change. Preserved as-is by 004; the DMX corpus goldens are the arbiter. |
| X17 | **`MediaCueType` does not declare `fade_profiles`**; `AudioCueType` and `VideoCueType` each declare it separately. The Python `MediaCue` class declared it on the base, so the two disagreed. | Found by the coherence test (FR-020) on its **first run** — the drift class that test exists for. Resolved in 004 on the **Python** side per T059 (the field moved to `AudioCue` and `VideoCue`), never by editing the XSD. Whether the schema should hoist it into `MediaCueType` is a separate question, deferred. |

Two further findings are recorded outside the X-series because they are code, not schema:

- **F24 — the written `xsi:schemaLocation` embeds the writing machine's absolute path** to
  the bundled `.xsd`, so documents are not portable and goldens are machine-dependent.
  Normalized for comparison only in 004 (FR-010b); the relative-path fix belongs to feature
  006. `tests/contract/test_legacy_compatibility.py` supplies the evidence that change is
  safe on the read side, by loading all three attribute forms — absolute, relative, absent —
  and asserting equal results (FR-035c, SC-019).
- **`mediaParser` has never been reached.** It exists at `Parsers.py:258`, and the lookup
  builds `'Media' + 'Parser'` = `MediaParser` while the class is spelled `mediaParser`.
  Thirteen hits across the corpus, no error, no log line. The same case-mangling failure
  hides `UI_properties` behind the lowercase `ui_properties` tag, and leaves `regions` as
  raw `{'Region': …}` wrappers (X12's practical consequence). All three are preserved by
  004 — binding them would start running code that has never run — and belong to feature
  005. Measured in `specs/004-xml-serialization-core/generic-bindings.md`.

#### Correction to X6

The audit originally read the commented-out `xs:all` block at
[script.xsd:214-220](../../src/cuemsutils/xml/schemas/script.xsd#L214-L220) as an
abandoned attempt to relax **cue element ordering**. That was wrong. `git log -L` shows the
block belongs to **`UiPropertiesType`**, and it was commented out in
`5c9ca40 feat: ui_properties as anyType and added to CuemsScript` — a deliberate widening
of `ui_properties` from a closed `xs:all` list (`id`, `icon`, `color`,
`timeline_position`, `warning`) to open `xs:anyType`, so the editor could store arbitrary
UI state.

It has nothing to do with F1, and **there is no prior abandoned attempt at X5**. The
"someone already tried this" argument for promoting X5 does not exist. The block is
recovered history for X10, not X5.
| X7 | `xs:assert test="modified >= created"` on the script root [script.xsd:38](../../src/cuemsutils/xml/schemas/script.xsd#L38) is an XSD 1.1 feature; it hard-requires `XMLSchema11` and blocks any move to a 1.0 toolchain. | Constraint to note, not a defect. |
| X8 | `script.xsd` declares `<?xml version="1.1"?>` — unusual and not required by anything in the file. | Cosmetic; low risk. |
| X9 | `network_map.xsd` `PutType` appears unreferenced within the schema. | Verify against `cuems-common`'s mirrored copy before touching — this file is mirrored to `/etc/cuems/network_map.xsd`. |

**Hard constraint on all of the above:** `network_map.xsd` is mirrored outside this repo by
`cuems-common`. Any change to it is a multi-repo deployment event, not a library release.

---

## 7. Feasibility of D2 (schema-driven single source)

The audit's verdict: **feasible, and better-supported than expected.**

**In favour**

- `script.xsd` is thoroughly typed — 20 named simple types, near-universal `type=`
  attributes. Datatype, range, enumeration, pattern, cardinality and order are all already
  declared. F1 and F6 exist because that information is *unused*, not because it is
  *absent*.
- `xmlschema` 3.4.3 exposes the full schema model at runtime (`XsdElement`, `.type`,
  `.is_single()`, content-model iteration) — `CMLCuemsConverter` already navigates it.
  Deriving a mapping table from a loaded schema needs no new dependency.
- Enumerated types (`PostGoType`, `ActionType`, `FadeTypeType`, `FadeModeType`,
  `FadeCurveType`, `FadeFunctionIdType`) map cleanly onto the existing `enum.Enum` usage.

**Against / needs a decision**

- **Not everything is expressible in XSD.** The `ProjectMappings` semantic rules
  (containment, ≤1 template per node) and media `duration` validation must remain
  hand-written alongside whatever is derived. The design needs a defined seam for
  "schema-derived" vs "hand-written semantic" validation.
- **The editor's JSON path (§3.2) has no schema attached.** Frontend payloads are not XML
  and never touch `xmlschema`. A schema-driven parser must still serve them — either by
  driving the same derived mapping from a dict source, or by keeping a documented
  second entry point.
- **`CuemsDict`-based objects are dicts with properties**, and parsers currently bypass the
  property setters via raw `__setitem__` ([Parsers.py:132](../../src/cuemsutils/xml/Parsers.py#L132),
  and see the `'id'` note in F6). Whether the rebuild routes through setters is a real
  behavioural decision with knock-on effects on defaults and coercion.
- **`CTimecode` and `Uuid` are custom scalars** whose XSD types are plain restricted
  strings. They need an explicit type-adapter registry; the schema alone cannot infer them.

---

## 8. Decisions taken in review

| # | Decision | Effect |
|---|----------|--------|
| D5 | **`CMLCuemsConverter` → thin subclass over stock.** | Keep only the repeated-element decode override (F5); delegate everything else upstream. Drops ~150 LOC and nearly all internals coupling. The dict shape consumers expect is preserved, so the six compensations stay valid and no consumer code changes. Fix the three stale version comments. |
| D6 | **X5 investigated → stays deferred.** | The archaeology disproved the "someone already tried" premise (see the X6 correction). Combined with the §9 proposal, which removes F1 without schema changes, there is no remaining reason to promote it. D3 holds intact. |
| D7 | **F7 reproduced and confirmed.** | `cuems-nodeconf` `main` verified in sync with `origin/main` (0/0, clean tree). Bug confirmed on `main` *and* on the in-flight `feat/nodeconf-reenable` branch. Severity raised to HIGH: one hard-failure field, three silent-corruption fields. Fix sequencing is Q6 below. |

### Cross-repo coordination note

`cuems-nodeconf` has an active branch, `feat/nodeconf-reenable`, that **restructures the
repo into a `cuemsnodeconf/` package** — `NodeXmlBuilders.py` moves to
`cuemsnodeconf/NodeXmlBuilders.py`. That is precisely the file the F8 migration must
rewrite. The migration target is moving underneath us; Part 3 sequencing needs to know
whether that branch lands before or after the rebuild.

---

## 9. Proposal — `REQ_ITEMS` keeps its jobs, loses the accidental one

*Answering the review note: "`REQ_ITEMS` is an important part of the Cue constructions,
since it contains the layered defaults through class inheritance (`super().__init__()`).
Alphabetical order in `REQ_ITEMS` is enforced to ease finding for developers."*

### The distinction that resolves F1

`REQ_ITEMS` currently carries **three** jobs. Two are deliberate and valuable; the third
was never intended and is the entire content of F1.

| | Job | Status |
|---|-----|--------|
| 1 | **Layered defaults.** Each class declares only its own new fields and their defaults; `ensure_items(init_dict, REQ_ITEMS)` fills them and `super().__init__(init_dict)` walks the chain applying each level. | **Deliberate. Keep unchanged.** |
| 2 | **Alphabetical index for developers.** A human-facing convention so a field is findable in a long list. | **Deliberate. Keep unchanged.** |
| 3 | **XML element order.** Dict iteration order reaches the serializer untouched and must happen to satisfy an `xs:sequence`. | **Accidental. Remove.** |

Job 3 is not a property of `REQ_ITEMS` — it is a property of *the serializer reading dict
order*. The fix belongs in the serializer, not in `cues/`.

### The layering is already isomorphic

Worth making explicit, because it is what makes this cheap: the XSD extension chain
already mirrors the Python inheritance chain, with the same semantics.

```
Python                          XSD
──────                          ───
Cue(CuemsDict)          ↔       CommonPropertiesType
  └ MediaCue            ↔         MediaCueType    extends CueType
      └ AudioCue        ↔           AudioCueType  extends MediaCueType
      └ VideoCue        ↔           VideoCueType  extends MediaCueType
```

`xs:extension` means "base particles first, then derived particles" — exactly what
`super().__init__()` does with defaults. The two hierarchies agree on layering already.
The only disagreement is *within* a layer: Python orders alphabetically for humans, the XSD
orders by declaration. Those coincide everywhere except `AudioCueType`
(`master_vol`, `fade_profiles`) and `VideoCueType` — which is precisely where the
hardcoded hack at [XmlBuilder.py:335-343](../../src/cuemsutils/xml/XmlBuilder.py#L335-L343)
had to be inserted.

### Proposal

1. **`REQ_ITEMS` is untouched.** Same alphabetical convention, same layered-defaults
   mechanism, same `super().__init__()` chain. It remains the single source of truth for
   *field membership* and *default values*. No cue class changes shape.

2. **The serializer takes element order from the schema, not from dict iteration.**
   Before writing a type, it asks the loaded XSD for that type's content model — which
   already resolves the extension chain in the correct order — and emits fields in that
   order. Dict order becomes irrelevant to correctness.

   Consequences:
   - the `master_vol` / `opacity` / `fade_profiles` hack is **deleted**, not relocated;
   - `sorted()` in `ensure_items` stops being load-bearing (it stays, for determinism and
     job 2, but nothing breaks if it changes);
   - a field added out of alphabetical order can no longer produce invalid XML;
   - adding a field is a **two-place edit** (`REQ_ITEMS` + XSD), never three.

3. **`ui_properties` keeps dict order.** Its type is `xs:anyType` (X10) so there is no
   schema order to honour and no constraint to violate. This is the documented wildcard
   fallback: *no content model → preserve insertion order*.

4. **Add a coherence test — set equality, not order.** Per cue class, assert that the
   union of `REQ_ITEMS` keys accumulated across the MRO equals the set of elements the
   corresponding XSD type declares. Class→type mapping by convention (`AudioCue` →
   `cms:AudioCueType`) with an explicit override table for exceptions.

   This catches the error that actually matters and that **nothing catches today**: a field
   present in Python but absent from the schema, or vice versa. Ordering, having ceased to
   be a correctness property, needs no test.

### What this buys

- F1 is removed at its root, with **zero changes to `cues/`, `helpers.py`, or any XSD**.
- Blast radius stays inside `src/cuemsutils/xml/`, honouring the stated scope preference.
- Both deliberate jobs of `REQ_ITEMS` are preserved exactly as designed.
- X5 becomes unnecessary, so D3 holds without exception.
- The one silent failure mode in this area (Python/schema field drift) gains a guard.

---

## 10. Further decisions

| # | Decision | Effect |
|---|----------|--------|
| D8 | **F7 patched on both branches, independently.** ✅ **DONE** | `cuems-nodeconf` `4b6844e` (main) and `0a3ce37` (`feat/nodeconf-reenable`), each carrying `tests/test_node_field_coercion.py` (106 cases). Guards the fields `network_map.xsd` types as strings and passes `key=` through; `uuid`/`adopted`/`online` keep their intended coercion. Verified: 106 pass with the fix, 101 fail without it. **Committed locally, not pushed.** |
| D9 | **Module renaming: yes, in a separate commit.** | Pure `git mv` + import updates, no logic changes, so the rename reviews independently and the rebuild diff stays readable. Consumers already need import updates under D1, so marginal migration cost is ~zero. |
| D10 | **Q8 escalated to a full analysis.** | See [Part 2a — node model ownership](xml-rebuild-02-node-model-ownership.md). Conclusion: F8 is not a constraint to design around but a symptom of misplaced ownership; if the node model moves into `cuems-utils`, **F7 and F8 both dissolve**. Pending decision Q9 there. |

### Remaining questions

**Q9** — adopt the Part 2a recommendation (move the persistence-facing node model into
`cuems-utils`)? See [Part 2a §9](xml-rebuild-02-node-model-ownership.md).

---

## Appendix A — file inventory

| File | LOC | Role | Verdict |
|------|-----|------|---------|
| `Parsers.py` | 409 | XML dict → objects | rebuild; ~50 LOC dead |
| `XmlBuilder.py` | 356 | objects → ElementTree | rebuild; 14 classes → far fewer |
| `Settings.py` | 285 | config file classes | keep; strip dead `buildxml`/`process_network_mappings`, unify `read()` with `XmlReaderWriter.read()` |
| `CMLCuemsConverter.py` | 183 | forked `xmlschema` converter | see Q2 |
| `XmlReaderWriter.py` | 113 | public facade | keep shape; the least-broken file |
| `schemas/*.xsd` | — | 6 schemas | audited (§6); changes deferred |

## Appendix B — evidence commands

```bash
# baseline
PYENV_VERSION=3.11.9 hatch test          # 557 passed in 7.44s

# consumers
grep -rn "cuemsutils.xml\|XmlReaderWriter\|CuemsParser\|XmlBuilder" --include="*.py" \
     cuems-engine cuems-editor cuems-nodeconf

# dead code confirmation (zero hits outside definitions)
grep -rn "data2xml\|buildxml\|process_network_mappings\|CuemsNodeDict" --include="*.py" .

# schema type inventory
grep -o 'type="[^"]*"' src/cuemsutils/xml/schemas/script.xsd | sort | uniq -c | sort -rn

# X6 correction — what the commented-out xs:all block actually was
git log -L 210,221:src/cuemsutils/xml/schemas/script.xsd --oneline

# nodeconf sync state (verified: clean tree, main 0/0 vs origin/main)
cd ../cuems-nodeconf && git fetch --all && git status --short \
  && git rev-list --left-right --count main...origin/main
```

## Appendix C — F7 reproduction

Two scripts, run under `PYENV_VERSION=3.11.9 hatch run python`. Both prepend
`cuems-utils/src` and `cuems-nodeconf` to `sys.path` and drive the **real** nodeconf
`nodeParser` / `nodeXmlBuilder` — no stubs.

1. **`repro_f7.py`** — feeds one schema-valid node dict through `nodeParser` and tabulates
   input vs output value and type, with a control run through `cuemsutils`' own
   `CuemsParser` (which passes `key=`). Produces the table in F7.
2. **`repro_f7_write.py`** — takes the parsed result, emits it via `nodeXmlBuilder` under a
   `CuemsNetworkMap` root, and validates against `network_map.xsd`. Establishes the two
   severities: `<name/>` fails `NonEmptyString`'s pattern facet, while
   `<role_id>False</role_id>`, `<alias>False</alias>` and `<hostname>7</hostname>` all
   validate and would persist.

Both live in the session scratchpad; they should be promoted to a regression test in
whichever repo takes the fix (Q6).
