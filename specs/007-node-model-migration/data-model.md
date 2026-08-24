# Phase 1 — Data model: node identity in `cuemsutils`

**Feature**: `007-node-model-migration` | **Date**: 2026-08-24
**Derives from**: [research.md](research.md), [spec.md](spec.md) Key Entities.

The rule this feature inherits from feature 004 (data-model §1) still holds: **structure, type,
cardinality and order are derived from the schema; names and behaviour are written by a human.**
What follows states both halves and marks which is which.

---

## 1. `network_map.xsd` after this feature

Derived-side changes. Everything not listed is byte-identical to the current schema.

```xml
<xs:complexType name="NodeType">
    <xs:sequence>
        <xs:element name="uuid"      minOccurs="1" maxOccurs="1" type="cms:UuidType"/>      <!-- was NonEmptyString -->
        <xs:element name="mac"       minOccurs="1" maxOccurs="1" type="cms:NonEmptyString"/>
        <xs:element name="name"      minOccurs="1" maxOccurs="1" type="cms:NonEmptyString"/>
        <xs:element name="node_role" minOccurs="1" maxOccurs="1" type="cms:NodeRoleType"/>  <!-- was node_type / NonEmptyString -->
        <xs:element name="ip"        minOccurs="1" maxOccurs="1" type="cms:NonEmptyString"/>
        <xs:element name="adopted"   minOccurs="0" maxOccurs="1" type="cms:BoolType"/>
        <xs:element name="online"    minOccurs="0" maxOccurs="1" type="cms:BoolType"/>
        <xs:element name="role_id"   minOccurs="0" maxOccurs="1" type="cms:NonEmptyString"/>
        <xs:element name="alias"     minOccurs="0" maxOccurs="1" type="cms:NonEmptyString"/>
        <xs:element name="hostname"  minOccurs="0" maxOccurs="1" type="xs:string"/>
    </xs:sequence>
</xs:complexType>

<xs:simpleType name="NodeRoleType">
    <xs:restriction base="xs:string">
        <xs:enumeration value="controller"/>
        <xs:enumeration value="node"/>
        <xs:enumeration value="firstrun"/>
    </xs:restriction>
</xs:simpleType>

<xs:simpleType name="UuidType">
    <xs:restriction base="xs:string">
        <xs:pattern value="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"/>
    </xs:restriction>
</xs:simpleType>
```

**Position matters and is preserved**: `node_role` sits where `node_type` sat — fourth, between
`name` and `ip`. Element order is derived from the content model (feature 004, FR-001), so moving
it would reorder every written document and enlarge the FR-010 diff beyond the two permitted
differences.

**Not changed**: `NodeDictType`, the `CuemsNetworkMap` root, `BoolType`, `NonEmptyString`.
`PutType` is addressed under FR-029 as schema item X9 — resolved or re-deferred with a stated
reason, not silently carried.

---

## 2. Adapter bindings

Bound by **type qname**, in the existing global table. Two entries are added; nothing is removed.

| XSD type | Adapter | Python | XML lexical | Wire scalar |
|---|---|---|---|---|
| `NodeRoleType` | `_EnumAdapter(NodeRole)` | `NodeRole` | `controller` \| `node` \| `firstrun` | same text |
| `UuidType` | `_UuidAdapter` *(already registered)* | `Uuid`, or raw text if unparseable | canonical hex | canonical hex |
| `BoolType` | `_Bool` *(already registered)* | `bool` | `True` / `False` | `"True"` / `"False"` |
| `NonEmptyString` | *(none)* → `PASSTHROUGH` | `str` | as-is | as-is |
| `xs:string` (`hostname`) | *(none)* → `PASSTHROUGH` | `str` | as-is | as-is |

**The fourth and fifth rows are the coercion guarantee.** `name`, `ip`, `mac`, `role_id`, `alias`
and `hostname` cannot be type-guessed because no codec is bound to their types — not because a
list of key names says to leave them alone (research R4). `STRING_TYPED_NODE_FIELDS` does not
migrate.

**`BoolType` is already bound and always was**; what changes is that the network-map decode path
now *runs* the table (R1). The show path has run it since feature 004.

---

## 3. Python model

All in `cuemsutils/config/network_map.py` — the module feature 006 created and reserved for this
work. Names below are the hand-written half.

### 3.1 `NodeRole` — the vocabulary (new)

```
NodeRole.controller  value "controller"
NodeRole.node        value "node"
NodeRole.firstrun    value "firstrun"
```

One definition, replacing three: `cuems-nodeconf`'s `CuemsNode.node.NodeType`, its
`AvahiTool.NodeType`, and the vocabulary that existed only as string literals in `cuems-engine`
and three `cuems-common` tools. Member **values** are the schema's enumeration verbatim — that
identity is what lets `_EnumAdapter` serialize without a mapping table, and a test asserts the
enum's values and the schema's `xs:enumeration` facets are the same set.

**Migration of meaning** (not of storage — nothing stores the old names after conversion):
`master` → `controller`, `slave` → `node`, `firstrun` → `firstrun`.

### 3.2 `node` — one machine (exists; gains typing and behaviour)

| Field | Type in memory | Required | Source |
|---|---|---|---|
| `uuid` | `Uuid` | yes | schema |
| `mac` | `str` | yes | schema |
| `name` | `str` | yes | schema |
| `node_role` | `NodeRole` | yes | schema |
| `ip` | `str` | yes | schema |
| `adopted` | `bool` | no | schema |
| `online` | `bool` | no | schema |
| `role_id` | `str` | no | schema |
| `alias` | `str` | no | schema |
| `hostname` | `str` | no | schema |

Declared as `Unset` defaults, so a document that omits an optional field yields an object without
that key rather than one carrying an empty string — the schema evolution convention, unchanged
from feature 006.

**`uuid` is the primary key.** `role_id`, `alias`, `hostname` and `node_role` are mutable
projections; any historical correlation goes through `uuid` (cuems-common's node-identity
contract). Nothing in this model enforces uniqueness — the schema does not, and inventing it here
would reject documents that load today.

**Constructible directly** (FR-004): `node(uuid=..., node_role=NodeRole.firstrun, ...)`. The Avahi
listener builds nodes that never reach a file, and that path must not require a document.

### 3.3 `node_list` — the schema container (exists, unchanged)

`NodeDictType`: the ordered `<node>` children. **Decode never instantiates it** — the converter
yields `[{"node": {...}}, ...]` as soon as cardinality is not single, which `NodeDictType`'s never
is. It exists for registry totality and the coherence check, exactly as feature 006 documented.
This feature does not change that, and does not rename it.

### 3.4 `NodeIndex` — the working set (migrates in, renamed)

`cuems-nodeconf`'s `node_list`/`CuemsNodeDict`, which is a *different shape* from §3.3 despite
sharing its old name (spec FR-002).

| Member | Behaviour |
|---|---|
| mapping | key → `node`. The key function is supplied by the caller, **not** hard-coded |
| `by_role(role)` | the nodes whose `node_role` is `role`, as a tuple |
| `controllers` | `by_role(NodeRole.controller)` — the one selection with a caller in every repo |

`masters`, `slaves` and `firstruns` do not migrate: they name a vocabulary that no longer exists,
and `nodes` as a role selection on a collection of nodes is ambiguous by construction (R5).

**Why the key is not fixed**: `cuems-nodeconf` keys by MAC and its own comment records that keying
merges on the Avahi-derived MAC produced duplicate controller entries, because the controller
advertises as `controller` rather than as its MAC. The identity contract makes `uuid` the primary
key. Moving the collection must not silently re-key it, so the choice stays with the caller.

### 3.5 `CuemsNetworkMapType` — the document (exists; gains persistence)

Holds `node_list`. Gains `save(path)` — validate, then write atomically (research R6). Its
`node_list` value stays a list of `{"node": <node>}` wrappers, because `cuems-engine` iterates it
in that shape and this feature does not edit that repository.

---

## 4. State and lifecycle

A node has no state machine in this model. Two fields describe state and both are plain data:

- **`adopted`** — set by `cuems-nodeconf`'s adoption flow, which stays there (FR-032).
- **`online`** — a *live* fact written by discovery. It is persisted, which means a map read from
  disk carries a possibly-stale value; `cuems-engine` already comments that the on-disk `<online>`
  is not authoritative for GO gating. This feature does not change that and does not make the
  model pretend otherwise.

Role transitions (`firstrun` → `controller`/`node`, and role flips) belong to adoption and remain
in `cuems-nodeconf`.

---

## 5. Coherence

`tests/unit/test_coherence.py` already includes `network_map` in its schema list and asserts set
equality between each bound class's `declared_fields()` and the derived `TypeSpec` field names.
After the rename, that test fails until `node.DECLARED_DEFAULTS` says `node_role` — which is
FR-006 working as designed, and is the reason no new test is written for it.

Three assertions are **new**, because the schema now carries meaning the model must match:

1. `NodeRole` member values == `NodeRoleType`'s `xs:enumeration` facets, as sets.
2. Every adapter-bound qname in `network_map.xsd` resolves to a non-passthrough adapter, and every
   free-text field resolves to `PASSTHROUGH` (the structural form of the coercion guarantee).
3. No `network_map` type is bound to `GENERIC` (registry totality, already asserted; restated here
   because the schema gains types).

---

## 6. What is deleted

| Symbol | Where | Fate |
|---|---|---|
| `node`, `node_list`, `CuemsNode`, `CuemsNodeDict`, `node.NodeType` | `cuems-nodeconf/cuemsnodeconf/CuemsNode.py` | file deleted |
| `nodeXmlBuilder`, `node_listXmlBuilder`, `nodeParser`, `node_listParser`, `STRING_TYPED_NODE_FIELDS`, the four globals injections | `cuems-nodeconf/cuemsnodeconf/NodeXmlBuilders.py` | file deleted |
| `AvahiTool.NodeType` | `cuems-nodeconf/cuemsnodeconf/AvahiTool.py` | replaced by the import |
| `CuemsNodeDictXmlBuilder` | `cuemsutils/xml/XmlBuilder.py:73` | deleted (FR-018) |
| `<node_type>` element, `NonEmptyString` typing of the role | `network_map.xsd` | replaced |

`CuemsNodeDictParser` was already removed by feature 006; its absence stays asserted by
`tests/contract/test_no_internal_deprecation.py`.
