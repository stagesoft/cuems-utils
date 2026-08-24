# Contract: the node surface `cuemsutils` exposes

**Feature**: `007-node-model-migration` | **Date**: 2026-08-24

Public surface added or changed by this feature. Under D15 the public configuration objects are
`ConfigManager` / `ConfigBase`; the node types are *configuration-domain objects* reached through
them and importable for direct construction, which discovery requires (FR-004).

Each contract below is stated so that a test can fail on it. `Cn` numbering continues the series
used by features 004 and 006.

---

## C1 — `NodeRole` is the single vocabulary, and it agrees with the schema

```python
from cuemsutils.config import NodeRole

NodeRole.controller.value == "controller"
NodeRole.node.value       == "node"
NodeRole.firstrun.value   == "firstrun"
```

**Asserted**: the set of `NodeRole` member values equals the set of `xs:enumeration` facets on
`network_map.xsd`'s `NodeRoleType`. Not a hand-copied list — read from the loaded schema, so the
two cannot drift.

**Asserted**: no other definition of a node role vocabulary exists in `cuemsutils`,
`cuems-nodeconf` or `cuems-common` source (FR-001, SC-004a).

---

## C2 — A node object is typed, and its types come from the schema

```python
n = cm.network_map["node_list"][0]["node"]

isinstance(n["node_role"], NodeRole)   # not str
isinstance(n["adopted"],   bool)       # not "True"
isinstance(n["online"],    bool)
isinstance(n["uuid"],      Uuid)       # or str, if the document's value is unparseable
isinstance(n["alias"],     str)        # free text is never coerced
```

**Asserted**: for every field, the in-memory type is the one the adapter bound to that field's
XSD type produces — checked against the derived table, not against a literal list.

**Asserted**: this holds for `network_map` **only**. Decoding `settings.xml`,
`project_mappings.xml` and `project_settings.xml` produces values identical to their recorded
`*.config.json` goldens, byte for byte (FR-011a-i, SC-010a).

---

## C3 — Free text survives, structurally

For each of `name`, `ip`, `mac`, `role_id`, `alias`, `hostname`, and each of
`none null n y off on no yes true false 0 1 007 42`: the decoded value equals the document's text
and is a `str`.

**Asserted**: and the mechanism is the derived table — `adapter_for` returns `PASSTHROUGH` for
`NonEmptyString` and `xs:string`. A test asserts that directly, so the guarantee is visible as a
property of the schema rather than as 84 passing cases.

**Asserted**: no name-keyed denylist exists — neither `STRING_TYPED_KEYS` nor
`STRING_TYPED_NODE_FIELDS` — anywhere in the package (FR-012, research R4).

---

## C4 — Round trip is a declared transformation, not byte identity

For every corpus `network_map.xml`:

```
load(doc) -> save(tmp)
diff(doc, tmp) == { <node_type> renamed to <node_role>, its value mapped }
```

**Asserted**: the diff is computed and compared to that exact set. Zero other differing bytes —
whitespace, attribute order, namespace prefix and `xsi:schemaLocation` all unchanged.

**Asserted**: `<node_type>` appears in zero written documents (SC-004).

**Asserted**: the other five schemas' documents remain byte-identical under their existing
byte-identity contracts (FR-010a).

---

## C5 — The write path is first-party, atomic, and validates first

```python
netmap.save(path)          # validate, then write
cm.save_network_map()      # the façade form
```

**Asserted**: a map carrying a role value outside the enumeration raises before any byte is
written, and the target file is left exactly as it was — including not existing.

**Asserted**: the write is atomic (temp file in the same directory, then replace), so a concurrent
reader sees the old document or the new one, never a truncated one.

**Asserted**: no handler class is resolved through a module namespace anywhere in the chain
(FR-016, FR-020).

**Asserted**: writing does not mutate the object it is given — the in-memory `node_role` is still
a `NodeRole` after `save()` returns (FR-015). This is the defect `cuems-nodeconf` worked around by
building a separate serialization copy; the workaround is deleted, so the property must be tested.

---

## C6 — Adoption selection does not mutate its input

```python
adopted, unadopted = NetworkMap.partition_by_adoption(netmap)
```

**Asserted**: every node value in `netmap` is equal, field by field, before and after the call.

**Asserted**: the partition is correct for maps whose `adopted` is `True`, `False`, or absent.

**Asserted**: the retained `get_nodes_by_adoption` still answers correctly when handed
already-typed booleans — the `strtobool(bool)` interaction research R7 measured. This test is
written **before** the typing lands and must fail at that point.

---

## C7 — No registration API, and the 004 break is closed

**Asserted**: `cuemsutils` exposes no public means of registering an external builder or parser
class, and none is added (FR-017).

**Asserted**: `tests/contract/test_declared_break_nodeconf.py` asserts the **repaired** state —
node serialization works through the registry — while still naming FR-026d, so the record of what
was broken and when it was closed survives (FR-019).

**Asserted**: `CuemsNodeDictXmlBuilder` no longer exists (FR-018), and `CuemsNodeDictParser`'s
prior removal stays asserted.

---

## C8 — Errors name the migration

**Asserted**: loading a document that still carries `<node_type>` fails with a message that names
the field and points at the migration — not with a bare structural complaint (FR-011c, FR-UX-001).

**Asserted**: a role value outside the enumeration is rejected at validation with a message naming
the field and the accepted values (FR-014). The previous behaviour — log and silently demote to
slave — exists nowhere after this feature.

---

## C9 — Coherence holds after the rename

**Asserted**: `node.declared_fields()` equals `NodeType`'s derived field names as sets, including
`node_role` and the three identity fields (FR-006). This is the existing coherence test; it fails
until the model follows the schema, which is the point.

**Asserted**: every complex type in `network_map.xsd` is bound to a model class, none to
`GENERIC`.
