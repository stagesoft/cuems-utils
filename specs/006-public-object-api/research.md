# Phase 0 research — public object API

**Feature**: 006-public-object-api · **Date**: 2026-08-18
**Inputs**: [spec.md](spec.md), [corpus-sweep.md](corpus-sweep.md),
`specs/planning/xml-rebuild-06-target-design.md` §§8–10,
`specs/planning/xml-rebuild-05-ui-wire-contract.md`

Every decision below is measured against the code as it stands after features 004 and 005,
not against the audit's description of it. Two of the five overturned the reading I started
with.

---

## R1 — How `to_wire()` is produced

**Decision: a direct projection (`Mapper.encode_wire`), with the round-trip through XML kept
as the test oracle.**

### The measurement

[`bench_to_wire.py`](bench_to_wire.py), on the largest corpus document (24 183 bytes,
30 samples, median):

| Step | Time |
|---|---:|
| `read()` — today's whole `project_load` | **16.95 ms** |
| `read_to_objects()` — XML → objects | 17.77 ms |
| `build_xml_from_object()` — objects → tree | **1.09 ms** |
| `schema.to_dict()` on a prebuilt tree | **15.49 ms** |
| Strategy A total (`build` + `to_dict`) | 16.22 ms |

### Why this settles it

Two candidate strategies:

- **A — round-trip**: object → `ElementTree` → `schema.to_dict()`. Byte-identity is free,
  because it *is* the reader's own code path.
- **B — direct**: a `Mapper.encode_wire` mirroring `decode`, walking the object once.

Under Q14 the editor's `project_load` becomes `CuemsScript.load(path).to_wire()`. With
strategy A that is **17.77 + 16.22 ≈ 34 ms against today's 16.95 ms — a 2× regression on the
single hottest path in the system**, and one the UI waits on. The cost is not the tree build
(1.09 ms, negligible) but the **re-decode**: `to_dict` is 15.49 ms of schema validation and
conversion, paid a second time to learn something the object already knows.

Strategy B replaces that with one object walk, which the 1.09 ms tree build bounds from
above — the same traversal, emitting dict nodes instead of elements.

The objection to B is real: it must reproduce the converter's decode shape exactly, and every
deviation is a UI break. **That objection is answered by keeping A as the oracle rather than
as the implementation.** The contract test asserts `encode_wire(obj) == schema.to_dict(
build_document(obj))` across the corpus, so A's guarantee is retained as a *property under
test* while B's cost is what ships. A is also what generates the goldens.

**Alternatives rejected**: shipping A (measured 2× regression on `project_load`); caching the
wire dict on the object (staleness on mutation, and the editor mutates); returning a lazy
proxy (the payload is `json.dumps`ed immediately, so laziness buys nothing).

---

## R2 — The engine is already in place; the legacy tree is not

**Decision: 006 deletes the frozen legacy parser tree; it does not build a new decoder.**

I expected to find decoding still on the old parsers. It is not:
`CuemsParser.parse()` already delegates to `Mapper('script').decode_document()`
(`src/cuemsutils/xml/Parsers.py`), and `XmlReaderWriter.build_xml_from_object` already calls
`build_document`. The comment there names this feature explicitly: *"Everything below this
method is the frozen legacy tree it used to drive… kept only so external callers keep
resolving until feature 006 removes it with the deprecation shims."*

Consequences for scope:

- The decode half of `from_json()` is **already built**. `from_json` is a facade over
  `Mapper.decode_document`, not new machinery.
- What is genuinely new is `encode_wire` (R1), the public methods, the config object layer
  (R4), and the T2 registry (R5).
- `Parsers.py`'s ~430 unreachable lines below `parse()`, plus `Settings.py`/`XmlReaderWriter.py`
  shims and `settings.py`'s dead `data2xml`/`buildxml`, are this feature's deletions.

---

## R3 — `xsi:schemaLocation`: what "relative" means

**Decision: write the bare schema filename (`script.xsd`), not a path.**

The attribute is built at one line — `mapper.build_document`:

```python
root.attrib = {f"{{{SCHEMA_INSTANCE_URI}}}schemaLocation": f"{namespace_uri} {xsd_path}"}
```

where `xsd_path` is the installed package's absolute path. The docstring already flags it as
F24 and defers the fix here.

"Relative" needs a referent, and there is only one defensible choice. The `.xsd` is bundled
*inside the installed package*; a document on disk has no stable relative path to it, and any
directory-walking form (`../../lib/python3.11/site-packages/…`) reintroduces exactly the
machine-dependence being removed. The bare filename is the only form that is identical on
every machine.

This is safe because **nothing resolves the value**. Validation uses the explicitly loaded
schema object, never the attribute. `tests/contract/test_legacy_compatibility.py` already
proves the read side across all three forms — absolute, relative, absent — as 004's FR-035c
and SC-019. That test is the evidence this change is safe; it exists precisely so this
feature could make it.

**Alternatives rejected**: a URL to the schema's canonical location (introduces a network
reference into offline node documents); dropping the attribute entirely (a larger wire change
than needed, and it removes a human-readable hint about which schema a file follows).

---

## R4 — The config module: where the derived/hand-written line falls

**Decision: derive the *structure* into typed objects per schema; keep every existing
accessor hand-written and unchanged in name and meaning. Detailed per-type in
[data-model.md](data-model.md).**

Q11→(c) settles the principle; the question is where the line lands in this code. Measured
starting point:

| Piece | Lines | Today |
|---|---:|---|
| `xml/settings.py` — `Settings`, `NetworkMap`, `ProjectMappings`, `ProjectSettings` | 258 | Readers returning raw dicts; registry bindings all `GENERIC` |
| `tools/ConfigBase.py` | 136 | ~18 hand-written scalar accessors over `self.settings[...]` |
| `tools/ConfigManager.py` | 307 | 4 properties, 3 shape compensations (F14), 2 output-id lookups |
| `xml/validators.py` | — | T2 seeds already extracted by 004 |

`settings.py`'s own docstring names the gap: *"What these classes do **not** yet have is a
model layer — the four of them hand back raw dicts, which is why their registry bindings are
all `GENERIC`. Giving configuration documents real objects is feature 006."*

The line:

- **Derived**: the field structure of each config document type, exactly as show types get it
  — `TypeSpec`/`FieldSpec` from the XSD, bound in the per-schema registry instead of
  `GENERIC`. This is what removes F14's three compensations, because a five-level nested walk
  is only necessary when the shape is unstated.
- **Hand-written**: every accessor on `ConfigBase`/`ConfigManager` (names and meanings are a
  consumer contract — FR-018), the semantic rules in `validators.py`, and the domain classes
  the node migration will bring in (D11, feature 007).

**The `network_map` ordering trap.** D11 moves `node`/`node_list` in from `cuems-nodeconf`,
but that is **feature 007**, and FR-014 requires `network_map` to return typed objects
**here**. These do not conflict only if 006 binds the network-map types to model classes it
defines in `cuemsutils/config/` and 007 *fills them in* with the migrated behaviour. Building
them in 006 as generic-but-typed containers, and letting 007 replace the bodies, is the
sequencing that satisfies both; building nothing here would leave FR-014 unmet, and building
the full node model here would do 007's work without its evidence (the 106-case coercion
regression test lives in the other repo).

**Alternatives rejected**: generating accessors from the schema (Q11(b), already settled
against — and F15 shows the accessors encode *domain* knowledge like which mapping is
"video", which no XSD states); leaving `network_map` on raw dicts until 007 (violates FR-014
and D12, and the editor and engine both hand-walk those dicts today).

---

## R5 — Where the T2 registry lives and how setters reach it

**Decision: extend `xml/validators.py` into the registry; setters call the named rule.**

The clarification settled the semantics (write + `validate()` only; setters delegate; one
definition per rule; `validate()` reports, `save()` raises first). The placement question
that remains is mechanical, and 004 already chose the module: `xml/validators.py` holds
`check_canvas_region_containment`, `check_one_custom_template_per_node` and
`validate_custom_templates`, described in `ProjectMappings._validate_custom_templates` as
*"a tier kept explicitly separate from schema-derived T1 validation… anything in that module
is a rule XSD cannot express."*

So the registry is not a new concept to introduce — it is the existing module gaining a
lookup and the remaining rules moving into it. Two constraints from measurement:

1. **`_initialized` must keep gating the setter path.** Three classes (`ActionCue`,
   `FadeCue`, `VideoCueOutput`) hold it false during population precisely so their rules stay
   off the decode path, and `helpers.py:236-247` documents that the resulting failure is
   *arrival-order dependent*. Delegation must not move the gate, only the rule body.
2. **`VideoCueOutput.__init__` calls `_classify_output_name` before `super().__init__`**, and
   that call — not the setter — is what pins the two legacy corpus documents as
   `to_objects: error`. FR-024d's "outcomes unchanged" therefore constrains the
   **constructor**, not the setter, which 005 had to correct in-flight once already.

**Alternative rejected**: a separate `validation/` package. It would split a tier that is
currently one 100-line module across two locations for no gain, and `validators.py` is already
the name the code and its tests use.

---

## R6 — Deprecation mechanism

**Decision: reuse `xml/_deprecation.py` unchanged; add shims, not schemes.**

Already present and already solving this: `deprecated==1.2.18` with one message template,
`REMOVAL_RELEASE = "v0.1.1"`, warning per call rather than per import, and correct
`stacklevel`. Its docstring is explicit that it *"must not grow into a second warning
system."*

The `xml/__init__.py` import-ordering hazard is also already solved and commented at length:
`Settings.py` and `XmlReaderWriter.py` are real submodules whose first import would otherwise
clobber the same-named classes. The two `from . import … as _shim` lines must survive this
feature's rewrite of that file — deleting them while emptying `__all__` would resurrect a
`TypeError: 'module' object is not callable` that has already been fixed once.

---

## R7 — Baselines carried into the plan

Measured on this branch, 2026-08-18, pyenv 3.11.9:

| Metric | Value |
|---|---|
| Suite | **1485 passed, 47 skipped, 2 xfailed, 44.57 s** |
| `read()`, largest corpus doc (24 KB) | 16.95 ms |
| `read_to_objects()` | 17.77 ms |
| `build_xml_from_object()` | 1.09 ms |
| Decode warm (005's inherited figure) | 18.0 ms |

Note: `CLAUDE.md` and the prompt set both quote "557 passed in ~7.4 s" as the baseline. That
figure predates features 004 and 005 and is stale by a factor of nearly three; the numbers
above supersede it, and `CLAUDE.md` should be corrected when this feature lands.
