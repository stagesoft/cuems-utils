# Contract: byte-identity guarantees

**Feature**: `004-xml-serialization-core`
**Status**: binding. These are the acceptance gates; if one fails, the feature fails.

The library exposes no new public API in this feature (FR-024), so the "contracts" here
are **output contracts**: the exact byte-level promises the refactor must keep. Each is
stated as an executable assertion.

C1–C10 assert that nothing observable changed. **C11 is the single exception**: it pins the
one declared breaking change (FR-026d) so that it is asserted rather than discovered.

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
ElementTree's spelling) followed by a newline, absence of indentation, absence of trailing
newline, and the `xsi:schemaLocation` attribute on the root.

**Encoding**: UTF-8, with non-ASCII written as literal UTF-8 bytes and never as numeric
character references (FR-010a). The corpus contains non-ASCII content, so this is
load-bearing rather than theoretical.

**One normalization, and only one**: the written `xsi:schemaLocation` embeds the writing
machine's **absolute path** to the bundled `.xsd` (measured). That path component is
normalized to a placeholder before comparison so goldens reproduce across machines and CI;
every other byte is compared as-is (FR-010b).

**Serializer is frozen**: stdlib `ElementTree.write(encoding="utf-8",
xml_declaration=True)`. `lxml` must not enter the write path — switching serializers
changes bytes wholesale (R10).

---

## C2 — The read dict is byte-identical

```
for doc in corpus:
    assert json.dumps(new_read(doc)) == json.dumps(golden_read(doc))
```

`json.dumps` is the comparison, not a convenience: it is how the library's own classes and
its consumers serialize this dict (FR-011a). Two consequences are therefore **inside** the
guarantee — the dict must stay `json.dumps`-compatible, and **key insertion order must be
preserved**, since `json.dumps` is order-sensitive and dicts that compare `==` may still
serialize differently.

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
property that is false today (R10). **FR-012 was restated to match** in the analyze
follow-up of 2026-08-11; it had kept the original "idempotent at the byte level" wording
after SC-003 was corrected, leaving the spec asserting a measured falsehood in one place
and denying it in another. C3, SC-003 and FR-012 now state one property.

---

## C3a — Semantic round-trip (object equality)

```
x = load(doc)
assert load(save(x)) == x
```

The durable guarantee, and the one that survives things byte-identity cannot: reformatting,
minification, or a storage layer that rewrites the XML without changing its meaning.
**Measured**: holds today, so it is assertable in this feature.

Scope: **loaded-vs-loaded** objects only. The built-vs-loaded comparison diverges today
(F18) and belongs to feature 005.

**C3a does not replace C1.** Object equality is *blind* to element order within order-free
(`xs:all`) content models — a reordered `CuemsScript` root loads to an equal object, which
is exactly the defect research R2 identified. C1 is the refactor's evidence; C3a is the
format's durability contract. Both are required.

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

Ordering follows FR-001's two schema-driven branches:

- **ordered** content models (`xs:sequence`, `xs:choice`) emit in declaration order;
- **order-free** (`xs:all`) models — `CuemsScript` and `DmxSceneType`, the only two across
  all six schemas — emit in **arrival order** (the source document's order when loaded,
  the model's key order when built), matching today's bytes, because their schema declares
  order irrelevant.

Dictionary-order emission appearing anywhere outside that second branch is a defect
(FR-001a).

**Corrected 2026-08-11 at T010 — this contract said "sorted-key order".** The captured
goldens show two of the four `xs:all` roots are not sorted; today's builder iterates the
object's items, so it preserves insertion order rather than sorting. Asserting sorted order
here would have made C1 fail on `complex_test/script.xml` and `empty_test/script.xml` after
the swap — the goldens caught the design error before a line of engine code existed, which
is what the phase ordering is for. See spec **FR-001b**.

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

`run_full_corpus_through_public_entry_points()` **includes `CuemsParser`**, the editor's
JSON→object path. That is not an oversight: `CuemsParser` is a supported entry point, not a
deprecated one (Assumption 3a), so it must stay silent here. It was already
library-internal before this feature — `XmlReaderWriter.write_from_dict` and
`read_to_objects` both call it — so exercising it is exercising the library's own path.

---

## C9 — Consumer imports still resolve

```
import cuemsutils.xml.XmlReaderWriter     # -> warns, works
import cuemsutils.xml.Parsers             # -> warns, works
import cuemsutils.xml.XmlBuilder          # -> warns, works
```

Each old path imports successfully. Every deprecated symbol emits a `DeprecationWarning`
**on each call** — not once per import — naming its replacement and **`v0.1.1`** as the
removal release, with a `stacklevel` that reports the **caller's** line rather than the
shim's (FR-027a, FR-027b). `v0.1.0` ships the shims with warnings intact.

Per-call is testable and must be tested as such: call the symbol **twice** under
`warnings.simplefilter("always")` and expect **two** records. A module-level re-export
cannot satisfy this, so the shims wrap each symbol rather than merely rebinding it.

**`CuemsParser` is the one symbol that must emit nothing.** It is a supported entry point
delegating to the engine, not a retired one (Assumption 3a), and C8 depends on its silence.

Of the 12 known consumer call sites, all of `cuems-editor`'s and `cuems-engine`'s work
unmodified against this release (FR-026, SC-013). `cuems-nodeconf`'s handler-injection
sites do not — see C11. Compatibility is gated in two layers (FR-030c): in-repo tests over
every shimmed path, which need no sibling checkout, plus a release-time review of the
migration map's call-site inventory against each sibling repository.

**If a call site cannot be kept working**, that is an acceptable outcome but never a silent
one: it MUST be declared a breaking change naming the symbol, the affected call sites and
the reason, flagged in the release notes, and shipped together with the corresponding
sibling-repository modifications (FR-030a, FR-030b). Exactly one such case exists, and it
is C11.

Per-call emission is deliberate: a consumer still routing production traffic through a
deprecated entry point keeps being told. Note that Python's default warning filter may
collapse repeats at a given call site — the contract binds what the library **emits**,
which is the part the library controls.

---

## C10 — Upgrade tripwire

A test asserts that `content.iter_elements()` still yields `AudioCueType` in the measured
order. The entire design rests on this behaviour of `xmlschema==3.4.3`; an upgrade that
changes it must fail loudly here rather than silently alter output (R11).

---

## C11 — The one declared breaking change is pinned, not incidental

```
import cuemsutils.xml.Parsers as ParsersModule
ParsersModule.nodeParser = SomeInjectedParser        # nodeconf's F8 pattern
obj = engine_load(document_containing_a_node)

assert not SomeInjectedParser.was_used               # injection is NOT consulted
assert type(obj) is registry.binding_for('nodeType') # registry resolves it instead
```

Every other contract here asserts that something did **not** change. This one asserts that
something **did**, and that it changed exactly as declared.

`CuemsParser.get_parser_class` and `XmlBuilder.get_builder_class` resolve handlers through
`globals()` of their own module, and `cuems-nodeconf` writes into those globals to register
its node handlers (`NodeXmlBuilders.py:96-99`). Once every path routes through the explicit
registry (FR-007), an injected name is never consulted.

**No shim can preserve it.** The injection point is a private module namespace, and
honouring an injected name means keeping the implicit lookup FR-007 exists to delete — so
the choice is between this break and abandoning the feature's premise. It is therefore
declared under **FR-026d / FR-030a**: named in the spec, recorded in `migration-map.md`,
flagged in `CHANGELOG.md`, and asserted by this contract — all of it inside this
repository. **The `cuems-nodeconf` fix is carried by feature 007**, under FR-030b's
scheduling clause: it must target an API that is internal in 004, public in 006 and
absorbing the node model in 007, so writing it against 004's intermediate shape would be
rewritten twice, and `cuems-nodeconf` is not shipping against this release. It lands on
`feat/nodeconf-reenable`, which feature 007 works from rather than being gated on.

Note what does **not** break: the imports still resolve and the assignment still executes
without error. Only its effect is gone. That silence is exactly why the break has to be
asserted by a test rather than left to be noticed.
