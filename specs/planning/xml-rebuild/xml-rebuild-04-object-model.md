# XML infrastructure rebuild — Part 2c: Object construction and the model root

**Status:** analysis for review
**Date:** 2026-08-10
**Questions:** (1) is `init_dict`-based `Cue` construction correct usage, given how
`read_to_objects` and `validate_template` actually work? (2) how does an internal-only
`xml/` (Q14) affect it? (3) what are the real implications of `CuemsScript` subclassing
`dict` rather than `CuemsDict`?

All findings below were verified by running the code, not by reading it. The probe is in
Appendix A.

---

## 1. There are two construction paths, and they produce different objects

### 1.1 The programmatic path — `init_dict`

`AudioCue({...})` → `ensure_items(init_dict, REQ_ITEMS)` → `self.setter(init_dict)` →
`set_<key>` property setters → coercion runs (`Uuid()`, `format_timecode()`,
`as_cuemsdict()`, `CueList()`, `Region()`).

This is what `create_script.py` uses, and what `cuems-editor` uses on frontend payloads.

### 1.2 The parser path — bypasses the constructor contract

`CuemsScriptParser.__init__` does `self.item_csp = self._class()` — an **empty**
construction — and then `parse()` assigns each key with raw `dict.__setitem__`
([Parsers.py:125,132](../../src/cuemsutils/xml/Parsers.py#L125)). Property setters never
run. The audit already recorded this in passing (F6: *"parsers assign via raw
`dict.__setitem__` and so never hit the property setters"*), but its consequence for the
object model was not drawn out.

### 1.3 What actually differs — measured

A `CuemsScript` built by `create_script()`, written to XML, and read back with
`read_to_objects()`:

| | built (`init_dict`) | loaded (parser) |
|---|---|---|
| `type(script)` | `CuemsScript` | `CuemsScript` |
| `isinstance(script, CuemsDict)` | `False` | `False` |
| `type(contents[0])` | `AudioCue` | `AudioCue` |
| `cue.id` | `Uuid` | `Uuid` |
| `cue.offset` / `prewait` | `CTimecode` | `CTimecode` |
| **`cue.ui_properties`** | **`CuemsDict`** | **`dict`** |
| **`media.regions`** | **`list[Region]`** | **`list[dict]`** |

**Same class name, different internal types.** Any consumer doing `isinstance(r, Region)`,
or calling a `Region`/`CuemsDict` method, works on a constructed script and silently takes
the wrong branch on a loaded one.

These are exactly the two "simple dict" degradations D14 exists to surface — and one of
them is `regions`, the open end flagged in D13.

> **Correction to an assumption.** I expected the parser path to also lose `REQ_ITEMS`
> defaults. It does not: `AudioCue.__init__` begins `if not init_dict: init_dict =
> REQ_ITEMS`, so `self._class()` still applies defaults. But this is **inconsistent across
> the hierarchy** — `Cue.__init__` begins `if init_dict:` and so `Cue()` bare gets *nothing*
> ([Cue.py:37](../../src/cuemsutils/cues/Cue.py#L37) vs
> [AudioCue.py:26-29](../../src/cuemsutils/cues/AudioCue.py#L26-L29)). Two defaulting
> protocols in one hierarchy, distinguishable only by reading each `__init__`.

### 1.4 Why `mediaParser`'s compensation did not save `regions`

`mediaParser` explicitly rebuilds regions as `Region` objects
([Parsers.py:270-277](../../src/cuemsutils/xml/Parsers.py#L270-L277)) — and the measured
result is still `list[dict]`. The compensation is written for one input shape and silently
does nothing for the shape actually produced. A hand-written fix-up that does not fire is
worse than none: it reads as a guarantee.

This compounds **F12** (`Media.set_regions` discards its own coercion). Between them there
are two independent attempts to ensure `regions` are `Region` objects, and neither works on
the path that matters.

---

## 2. So: is `init_dict` construction correct usage?

**As a programmatic constructor, yes. As the model's coercion contract, no — because the
parser does not honour it.**

The design places coercion in **property setters**, which makes correctness depend on
*how* a value was assigned rather than *what* it is. Three call styles coexist in
first-party code, with three different results:

```python
script.id = None                # property  -> Uuid(None) -> a NEW random uuid
script['id'] = new_uuid()       # raw       -> stored verbatim
dict.__setitem__(obj, k, v)     # parser    -> stored verbatim, no coercion
```

`create_script.py` uses all three, and it has a live defect because of it. Lines 184-192
intend *"remove dates and ids so we send it empty"*:

| statement | intent | measured result |
|---|---|---|
| `script.id = None` | clear | **fresh random `Uuid`** — `set_id` calls `Uuid(None)`, and `Uuid.__init__` generates a uuid4 when falsy |
| `script.cuelist.id = None` | clear | **fresh random `Uuid`** |
| `script.cuelist.contents[i]['id'] = None` | clear | `None` ✓ (raw `__setitem__`) |

So the template ships with two randomised ids where it means to ship none — silently, for
as long as this has existed. **F16.**

A related hazard in the same mechanism: `setter()` wraps the setter call in
`except AttributeError: pass` ([helpers.py:32-36](../../src/cuemsutils/helpers.py#L32-L36)).
That is intended to skip keys with no setter, but it also swallows any `AttributeError`
raised *inside* a setter — so a genuine bug in coercion logic silently drops the field.
**F17.**

### Best practice this points at

1. **One construction path.** Coercion must not depend on assignment style. Under D2 the
   natural home is the schema-derived field spec + type-adapter registry (E1/E4): the
   adapter coerces, and it runs whether the value came from XML, JSON, or a keyword.
2. **Named alternative constructors** rather than one `init_dict` that means different
   things: `CuemsScript.from_xml(path)`, `.from_json(payload)`, `CuemsScript(**fields)`.
3. **Validate at the boundary, not at serialization.** Today `AudioCue({...})` accepts
   anything and you learn it is invalid only when something tries to build XML from it.
4. **Never bypass your own setters.** If that is inconvenient — and for a parser it always
   is — the coercion is in the wrong place.

---

## 3. Global picture: `validate_template`, `read_to_objects`, consumers

| Operation | Today | Validation |
|---|---|---|
| Build in memory | `AudioCue({...})`, `CuemsScript({...})` | **none** |
| Validate without writing | `XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(obj)` — [create_script.py:197-200](../../src/cuemsutils/create_script.py#L197-L200) | XSD, via a full build to an in-memory tree |
| Write | `write_from_object(obj)` | XSD, on write |
| Read → objects | `read_to_objects()` | XSD, at `to_dict(validation='strict')` |
| Read → dict | `read()` — what `cuems-editor.load_xml` returns | XSD |

Two asymmetries worth naming:

- **Reading is validated; building is not.** An object is only checked when it leaves the
  process. `validate_template` exists precisely to paper over that, and it has to know the
  schema name and the `xmlfile=None` idiom to do so.
- **`validate_object` is a serializer in disguise.** It builds the whole tree to answer a
  question about an object. That is the only validation the object model has.

`create_script.py` is instructive because it is a **first-party consumer** and it already
wants the API that does not exist: it wants `script.validate()`.

---

## 4. Effect of an internal-only `xml/` (Q14)

Making `xml/` internal **helps this problem rather than complicating it**, because it forces
the single entry point that §2 argues for.

| Today (machinery is public) | Under Q14 = yes |
|---|---|
| `XmlReaderWriter(schema_name="script", xmlfile=f).read_to_objects()` | `CuemsScript.load(f)` |
| `XmlReaderWriter(...).write_from_object(obj)` | `script.save(f)` |
| `XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(obj)` | `script.validate()` |
| `CuemsParser(payload).parse()` | `CuemsScript.from_json(payload)` |
| `reader.read()` → raw dict (editor `load_xml`) | *(internal; editor gets a `CuemsScript`)* |

The decisive argument: **`CuemsScript.load()` can guarantee its return value is fully
coerced. `XmlReaderWriter.read_to_objects()` cannot**, because today the guarantee depends
on which of two construction paths ran, and callers have no way to know. A single public
constructor makes §1.3's divergence *unrepresentable* rather than merely fixed.

It also removes the need for callers to know `schema_name="script"` — a string that
consumers currently pass at six call sites across three repos, and which is really a
property of `CuemsScript`, not of the caller.

Cost, stated plainly: `cuems-engine` `BaseEngine.py:509` and `cuems-editor`
`CuemsDBProject.{load_xml,save_xml}` migrate. Both are small, and the editor's `load_xml`
changes from returning a raw dict to returning a `CuemsScript` — a genuine behavioural
change for its callers, and the largest single item in this migration.

---

## 5. `CuemsScript(dict)` vs `CuemsScript(CuemsDict)`

Every model class in the package is a `CuemsDict` — `Cue`, `CueList`, `MediaCue`,
`AudioCue`, `VideoCue`, `DmxCue`, `ActionCue`, `FadeCue`, `Media`, `Region`, `CueOutput`
and subclasses, `DmxScene`, `DmxUniverse`, `DmxChannel`, `FadeProfile`,
`FadeFunctionParameter`, `UI_properties` — **except `CuemsScript`, the root**
([CuemsScript.py:20](../../src/cuemsutils/cues/CuemsScript.py#L20)).

Five concrete consequences.

### 5.1 `setter()` is duplicated verbatim
`CuemsScript.setter` ([:268-284](../../src/cuemsutils/cues/CuemsScript.py#L268-L284)) is
byte-for-byte the logic of `CuemsDict.setter`
([helpers.py:20-36](../../src/cuemsutils/helpers.py#L20-L36)). The root already needs
`CuemsDict`'s behaviour and copies it — including F17's `except AttributeError: pass`.

### 5.2 No `build()`, so the root is invisible to generic dispatch
`CuemsDict.build(parent)` is what `build_xml_dict` finds via `hasattr(v, 'build')`
([helpers.py:58,62](../../src/cuemsutils/helpers.py#L58)) and what
`GenericCueXmlBuilder`'s `as_cuemsdict` path relies on. `CuemsScript` has neither, and
survives only because `CuemsScriptXmlBuilder` handles it by name.

### 5.3 `isinstance(script, CuemsDict)` is `False` — measured
Nothing keys on that predicate today (there are no `isinstance(..., CuemsDict)` checks in
the package). But **a schema-driven serializer wants exactly that predicate** — "is this a
declared-field model object?" — and under the current hierarchy the root document is the
one object that answers no. Every generic traversal would need a special case for it.

### 5.4 `items()` means different things at root and branch
`Cue.items()` filters to declared fields via `extract_items(..., REQ_ITEMS.keys())`
([Cue.py:321-327](../../src/cuemsutils/cues/Cue.py#L321-L327)). `CuemsScript.items()`
returns **everything** ([:302-309](../../src/cuemsutils/cues/CuemsScript.py#L302-L309)).

Since `XmlBuilder` serializes by iterating `.items()`, a stray key on a cue is silently
dropped, while a stray key on the script goes straight into the XML and fails validation.
Undocumented, asymmetric, and precisely the kind of rule a declared field spec should own.

### 5.5 The `__json__` contract is asymmetric, and the hack proves it
`Cue.__json__` self-wraps: `{type(self).__name__: dict(self.items())}`
([Cue.py:313-319](../../src/cuemsutils/cues/Cue.py#L313-L319)). `CuemsScript.__json__`
returns a **bare** dict, and therefore has to un-wrap its children:

```python
# CuemsScript.py:298-299
if k.lower() != k:
    x[k] = x[k][k]        # undo CueList's self-wrapping
```

Detecting a wrapped child by testing whether its key has uppercase letters. That hack
exists *solely* because the root and its children implement two different JSON contracts —
a direct consequence of them being two different base types. It also means F13's asymmetry
(JSON out, no JSON in) has an inconsistency baked into the "out" side as well.

### Recommendation

**Make `CuemsScript` a `CuemsDict`.** It removes 5.1's duplication, fixes 5.2 and 5.3
structurally, and — once `items()` and `__json__` are aligned with the rest of the model —
retires 5.4's silent asymmetry and 5.5's hack.

One caution, because it is a behavioural change and not pure cleanup: aligning `items()` to
filter by declared fields could drop keys the root currently emits. That must be covered by
D14's chain test before the change lands, not after.

---

## 6. New findings for Part 1

| # | Severity | Finding |
|---|---|---|
| F16 | **HIGH** | `create_script.py:186-187` intends to clear ids; `script.id = None` and `script.cuelist.id = None` instead assign **fresh random `Uuid`s**, because `set_id` calls `Uuid(None)` and `Uuid.__init__` generates a uuid4 when falsy. The sibling lines using `['id'] = None` do clear. Measured. |
| F17 | MEDIUM | `CuemsDict.setter` / `CuemsScript.setter` wrap the setter call in `except AttributeError: pass`, intended to skip keys with no setter — it also swallows `AttributeError` raised *inside* a setter, silently dropping the field. |
| F18 | **HIGH** | `read_to_objects()` and `init_dict` construction produce objects of the same class with different internal types (`ui_properties`: `dict` vs `CuemsDict`; `regions`: `list[dict]` vs `list[Region]`). Measured. |
| F19 | MEDIUM | `mediaParser`'s explicit `Region(...)` reconstruction does not fire for the shape actually produced by the reader — a compensation that reads as a guarantee and is not one. |
| F20 | LOW | Two defaulting protocols in one hierarchy: `Cue()` bare yields an empty object, `AudioCue()` bare yields full `REQ_ITEMS` defaults. |

---

## 7. Bearing on the open questions

- **Q14 (is `xml/` internal?)** — this analysis argues **yes**, on grounds independent of
  D15: it is what makes "a loaded script is fully coerced" a guarantee rather than a hope
  (§4).
- **Q11 (how the typed surface is produced)** — unaffected directly, but §2's conclusion
  (coercion belongs in a declared field spec, not in setters) points the same way as
  option (b)/(c): derive the field spec from the schema, and coercion stops being
  location-dependent everywhere at once.

## Appendix A — probe

`scratchpad/probe_construction.py`. Builds a script via `create_script()`, inspects id
clearing (§2), compares `init_dict` versus raw-`__setitem__` construction of one `AudioCue`
(§1.3), then round-trips a full script through `write_from_object` → `read_to_objects` and
compares internal types at each level. Should be promoted into the D14 chain test.
