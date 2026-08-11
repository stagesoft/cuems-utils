# Contract: byte-identity guarantees

**Feature**: `004-xml-serialization-core`
**Status**: binding. These are the acceptance gates; if one fails, the feature fails.

The library exposes no new public API in this feature (FR-024), so the "contracts" here
are **output contracts**: the exact byte-level promises the refactor must keep. Each is
stated as an executable assertion.

---

## C1 — Written XML is byte-identical

```
for doc in corpus:
    obj   = pre_refactor_load(doc)
    golden = pre_refactor_write(obj)          # captured once, never regenerated
    assert new_write(new_load(doc)) == golden # byte-for-byte
```

Covers: element order, attribute order, empty-element spelling (`<tag />`), the XML
declaration (`<?xml version='1.0' encoding='utf-8'?>`, single quotes — stdlib
ElementTree's spelling), absence of indentation, absence of trailing newline, and the
`xsi:schemaLocation` attribute on the root.

**Serializer is frozen**: stdlib `ElementTree.write(encoding="utf-8",
xml_declaration=True)`. `lxml` must not enter the write path — switching serializers
changes bytes wholesale (R10).

---

## C2 — The read dict is byte-identical

```
for doc in corpus:
    assert json.dumps(new_read(doc), sort_keys=False) \
        == json.dumps(golden_read(doc), sort_keys=False)
```

Covers the repeated-element shape, every key currently present, and scalar container
types. **Includes the `{…XMLSchema-instance}schemaLocation` key**: it is leaked (F23) but
removing it is a wire change deferred to feature 006, so it must still be present here.

Both current reader configurations are covered separately (FR-013): `XmlReaderWriter.read`
(`strip_namespaces=False`) and `Settings.read` (`strip_namespaces=True`, explicit
`dict`/`list` classes). Their outputs differ today; both differences are preserved.

---

## C3 — Round-trip stability, not input fidelity

```
once  = new_write(new_load(doc))
twice = new_write(new_load(once))
assert once == twice
```

**Not** `new_write(new_load(doc)) == doc`. Hand-authored corpus files are indented and
some declare `version="1.1"`; the library's serializer normalizes both. Idempotence holds
from the first save onward — this restates SC-003, which as originally worded asserts a
property that is false today (R10).

---

## C4 — The D14 chain

```
xml -> object -> json -> object -> xml
```

Every intermediate is compared against its captured golden, not just the endpoints. Written
and committed **against pre-refactor code**, green at that commit, and green after the swap
**without being edited** — provable from `git log`. This is the feature's primary gate
(constitution II).

---

## C5 — The UI payload is untouched

The dict from C2 is what `cuems-editor` transmits verbatim to the Angular UI on
`project_load`. Therefore:

- booleans stay the **strings** `"True"` / `"False"` (`cms:BoolType` is `xs:string`);
- `ui_properties` scalars stay strings;
- `{"CTimecode": "…"}` wrappers keep their shape;
- the repeated-element shape is unchanged.

No frontend change is required by this feature, and none is permitted to become necessary.

---

## C6 — Ordering provenance

```
assert AudioCueType.field_order.index('master_vol') \
     < AudioCueType.field_order.index('fade_profiles')
assert no source file compares a field name to a string literal to order output
```

Plus the `xs:all` branch (R2): `CuemsScript` and `DmxSceneType` emit in sorted-key order,
matching today's bytes, because their schema declares order irrelevant.

---

## C7 — Registry totality

```
for schema in six_schemas:
    for complex_type in schema:
        assert registry.binding_for(complex_type) is not None   # error at build time
```

Types that reach a generic today are bound explicitly to that same generic — completeness
without output change (FR-007).

---

## C8 — No internal caller of deprecated symbols

```
with warnings.catch_warnings(record=True) as w:
    warnings.simplefilter("always", DeprecationWarning)
    run_full_corpus_through_public_entry_points()
    assert [x for x in w if issubclass(x.category, DeprecationWarning)] == []
```

This is what keeps the softened wording of FR-002/FR-003 honest: the old ordering hack and
type-guessing helper still exist as frozen shims, and this assertion proves nothing live
reaches them.

---

## C9 — Consumer imports still resolve

```
import cuemsutils.xml.XmlReaderWriter     # -> warns, works
import cuemsutils.xml.Parsers             # -> warns, works
import cuemsutils.xml.XmlBuilder          # -> warns, works
```

Each old path imports successfully and emits exactly one `DeprecationWarning` naming its
replacement and removal release. The 12 known consumer call sites across `cuems-editor`,
`cuems-engine` and `cuems-nodeconf` work unmodified against this release (FR-026, SC-013).

---

## C10 — Upgrade tripwire

A test asserts that `content.iter_elements()` still yields `AudioCueType` in the measured
order. The entire design rests on this behaviour of `xmlschema==3.4.3`; an upgrade that
changes it must fail loudly here rather than silently alter output (R11).
