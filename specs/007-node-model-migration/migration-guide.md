# Migration guide — feature 007: node model migration

Consumed by feature 008 (the reader migration in `cuems-engine`/`cuems-editor`) and by whoever
performs the release. Built incrementally as the feature lands; the enumeration required by
FR-027a lives in [§1](#1-required-contents-fr-027a) and every other requirement that names an
obligation for this file cross-references that list rather than restating it.

---

## 1. Required contents (FR-027a)

This file must contain, each in its own section below:

1. The starting symbol table (T006) and the `node_type`/`NodeType.` occurrence count (SC-004a's
   denominator) — [§2](#2-starting-symbol-inventory-t006-t006a).
2. The `cuems-nodeconf` node/discovery/adoption/orchestration inventory (T006a) and the
   semantically-wrong-but-still-resolving class (T006f) — [§2](#2-starting-symbol-inventory-t006-t006a),
   [§3](#3-fr-030a-ii-semantically-wrong-not-broken-t006f).
3. The moved-symbol table: source → new home → status → authorising requirement (T084).
4. The public import path for consumers (T084a).
5. What `cuems-engine` must change in feature 008 (T085).
6. What `cuems-editor` must change in feature 008 (T086).
7. The release gate, stated as a gate (T087, T087a, T087b).
8. Schema item X9 resolution record (T088).
9. The FR-018 orphan search result (T078a) and the FR-032 boundary check (T078b).
10. The out-of-order-upgrade enforcement demonstration (T054b).
11. `cuems-nodeconf`'s suite result against the migrated `cuemsutils` (T079).

---

## 2. Starting symbol inventory (T006, T006a)

### `node_type` / `NodeType.` occurrences at the pre-feature commit

See `baseline.md` §"Symbol inventory" for the full table. Total: **192** occurrences across
`cuems-utils` (12), `cuems-nodeconf` (146), `cuems-common` (27), `cuems-engine/src` (5),
`cuems-editor/src` (2). This is SC-004a's denominator, subject to the four-file Avahi exclusion
recorded in [§9](#9-avahi-discovery-files-excluded-from-sc-004a-t060-t060a).

### `cuems-nodeconf` node symbols (deleted by US5)

| Symbol | File | Fate |
|---|---|---|
| `node_list` (dict subclass) | `cuemsnodeconf/CuemsNode.py` | deleted — replaced by `cuemsutils.config.network_map.node_list` (schema container) and `NodeIndex` (working set) |
| `node` (dict subclass) | `cuemsnodeconf/CuemsNode.py` | deleted — replaced by `cuemsutils.config.network_map.node` |
| `node_listXmlBuilder` | `cuemsnodeconf/NodeXmlBuilders.py` | deleted — the injection mechanism itself is retired |
| `nodeXmlBuilder` | `cuemsnodeconf/NodeXmlBuilders.py` | deleted |
| `node_listParser` | `cuemsnodeconf/NodeXmlBuilders.py` | deleted |
| `nodeParser` | `cuemsnodeconf/NodeXmlBuilders.py` | deleted |
| `NodeType` (enum) | `cuemsnodeconf/AvahiTool.py` | deleted — replaced by `cuemsutils.tools.NodeList.NodeRole` |

### `cuems-nodeconf` discovery / adoption / orchestration symbols (stay — FR-032)

Excluded from the migrated surface by decision (FR-030a-i): the repository root and `tests/` are
not migrated; the node standard and its testing live in `cuems-utils` exclusively.

| Module | Symbols | Role |
|---|---|---|
| `CuemsNodeConf.py` | `CuemsNodeConf` — `adopt_node`, `unadopt_node`, `merge_discovered_nodes`, `check_missing_adopted_nodes`, `check_first_run`, `refresh_network_map`, `write_network_map`, `read_network_map`, `set_node_type`, `publish_aliases_if_master`, `change_network_to_master`, and the run loop | orchestration + adoption — the process that owns `/etc/cuems/network_map.xml` |
| `CuemsAvahiListener.py` | `CuemsAvahiListener` — `add_service`, `remove_service`, `update_service` | discovery |
| `CuemsConfServer.py` | `CuemsConfServerHandler`, `CuemsConfServer` | the req/rep server nodeconf exposes |
| `AliasPublisher.py` | `AliasPublisher` | Avahi alias publication |
| `AvahiTool.py` | `MyAvahiListener`, `AvahiTool` (minus the `NodeType` enum above) | discovery utility |
| `CuemsSettings.py` | settings loader | local config |

None of these symbols move. `CuemsNodeConf.py` and `AvahiTool.py` are edited in place (T073–T076)
to consume the upstream model rather than the deleted local one — that is a call-site change, not a
boundary crossing.

---

## 3. FR-030a-ii: semantically wrong, not broken (T006f)

Class of caller that keeps *resolving* after this feature but becomes silently **wrong**, because
it still compares against the retired `master`/`slave` vocabulary. Distinct from FR-026d's break
(an `ImportError`) — nothing here raises; the comparison just never matches again once a document
only ever contains `controller`/`node`/`firstrun`. Searched for, not waited for, because nothing
fails to surface it.

| Repository | Site | What goes silently wrong |
|---|---|---|
| `cuems-engine` | `BaseEngine.py:33` — `CONTROLLER_NETWORK_FLAG = "NodeType.master"` | after conversion, no node's `node_role` (or its pre-008 raw-string reading of the renamed element) is ever `"NodeType.master"` again — the controller is never found by this comparison. Feature 008's work (FR-028). |
| `cuems-engine` | `BaseEngine.py:410,440` | the two sites comparing `node.get("node_type") == CONTROLLER_NETWORK_FLAG` — same failure, structural: they read a key (`node_type`) the document no longer has at all after conversion, so `.get` returns `None` and the comparison is `False` for every node, not just silently wrong for the value. |
| `cuems-engine` | `BaseEngine.py:443` — `node.get("online") == "True"` | **found during T085's verification, not in the original inventory.** Independent of the `node_type` rename: once `network_map` runs the adapter table (this feature, research R1), `online` decodes to a Python `bool`. `True == "True"` is `False`, so this filter silently excludes every node — the `hosts` list this feeds is `check_missing_adopted_nodes`'s input, per its call site at line ~430. Feature 008's work; not a `node_type`/`node_role` issue, an `adopted`/`online` typing one, and worth stating as its own class rather than folded into the rename finding. |
| `cuems-editor` | `CuemsWsServer.py:425` | the `basic_fields` list names `'node_type'`; after conversion the document has no such key, so this field is silently absent from every node payload sent to the UI rather than raising. |

No `cuems-common` site falls in this class: the three tools T055–T057 name are fixed in this
feature's own US3, not deferred.

---

## 3a. US4's finding: the coercion guarantee needs no implementation (T065)

The outcome a reader will not expect, stated so it is not mistaken for an oversight: **there is no
code to write**. `NonEmptyString` and `xs:string` are unbound in `ADAPTERS` (`xml/adapters.py`) —
confirmed directly: `'NonEmptyString' in ADAPTERS` and `'string' in ADAPTERS` are both `False`. So
`adapter_for` returns `PASSTHROUGH` for every free-text node field
(`mac`/`name`/`ip`/`role_id`/`alias`/`hostname`) by construction, not because any code path checks
their names. The 106-case regression suite (ported to `tests/contract/test_node_field_coercion.py`,
T061–T064) is therefore a **guarantee test over the derived table** — it fails only if a future
adapter binding accidentally claims one of these type qnames, which is exactly the property worth
pinning.

**A second, distinct finding surfaced while asserting T064's "no denylist anywhere in the
package"**: `xml/Parsers.py` still declares `STRING_TYPED_KEYS`, a **different, pre-existing**
denylist for an unrelated domain — the frozen, deprecated `CuemsParser`'s cue/script field
type-guessing (feature 004, ClickUp 869cqbpxa: `name`/`description`/`file_name` and four defensive
entries). It is not `STRING_TYPED_NODE_FIELDS` (which does not migrate, per FR-012/C3), predates
this feature, and this feature does not touch `CuemsParser` or script parsing — removing it is out
of scope here. Recorded as a finding so "we looked and it's out of scope" is distinguishable from
"we did not think to look" (FR-018's standard, applied to a place FR-018 itself doesn't reach).

---

## 4. The moved-symbol table (T084)

**Scope note, stated once rather than per row**: this pass of feature 007 implements Phases 1–4, 6
and 8 (`cuems-utils` only) — Phase 5 (US3, `cuems-common`) and Phase 7 (US5, `cuems-nodeconf`) were
descoped by an explicit decision partway through implementation, recorded here rather than left to
be inferred from an empty section. The table below therefore states the **intended** destination
and **authorising requirement** for every symbol T006a's inventory named, with status `landed`
where the `cuems-utils` half is done and `not started` where the move depends on editing
`cuems-nodeconf`, which this pass does not do. Nothing in this table is a broken promise: the
`cuems-utils` destinations exist, work, and are tested; only the *deletion* of the `cuems-nodeconf`
source, which depends on a repository this pass never opens, remains.

| Source | New home | Status | Authorising requirement |
|---|---|---|---|
| `cuemsnodeconf.CuemsNode.node` | `cuemsutils.config.network_map.node` (internal) / `cuemsutils.tools.NodeList.node` (public re-export) | **landed** — typed, tested (C1–C11), constructible directly (FR-004) | FR-002, FR-002b, data-model §3.2 |
| `cuemsnodeconf.CuemsNode.node_list` | `cuemsutils.config.network_map.node_list` | **landed** — unchanged from feature 006, registry-bound | FR-002, data-model §3.3 |
| `cuemsnodeconf.CuemsNode.CuemsNodeDict`, `CuemsNode` (aliases) | *(deleted, not recreated)* | **landed** by policy — FR-002a is explicit that no shim is created | FR-002a |
| `cuemsnodeconf.AvahiTool.NodeType` (enum) | `cuemsutils.tools.NodeList.NodeRole` | **landed** — values verified against the loaded schema (C1) | FR-001, research R3 |
| `cuemsnodeconf.NodeXmlBuilders.{node,node_list}XmlBuilder` | `cuemsutils.xml.documents.build_tree` (registry-driven, via `CuemsNetworkMapType.save`) | **landed** — the write path exists and is tested (C4, C5) | FR-009, research R6 |
| `cuemsnodeconf.NodeXmlBuilders.{node,node_list}Parser` | `cuemsutils.xml.mapper.Mapper.decode_config` (registry-driven) | **landed** — was already true from feature 006's bindings | FR-011a, research R1 |
| `cuemsnodeconf.NodeXmlBuilders.STRING_TYPED_NODE_FIELDS` | *(deleted, not recreated — structural guarantee instead)* | **landed** — `tests/contract/test_node_field_coercion.py` asserts its absence (T064) and the structural replacement (T065) | FR-012, research R4 |
| `cuemsnodeconf.CuemsNodeConf`'s MAC-keyed working set | `cuemsutils.tools.NodeList.NodeIndex` | **landed** in `cuems-utils`; **not started** in `cuemsnodeconf` — the call site still builds its own dict | research R5 |
| `cuemsnodeconf.CuemsNode.py`, `NodeXmlBuilders.py` (the files) | *(deletion target)* | **not started** — depends on editing `cuems-nodeconf` (Phase 7 / US5), out of scope this pass | FR-018 |
| `cuemsnodeconf.CuemsNodeConf.py`'s `node_type` normalisation, hand-rolled atomic write, `XmlReader`/`XmlWriter` use | *(removal target — the upstream model and `save()` make each unnecessary)* | **not started** — same reason | FR-015, FR-031, research R6 |
| discovery/adoption/orchestration symbols (`CuemsAvahiListener`, `CuemsConfServer`, `AliasPublisher`, `AvahiTool` minus its enum) | *(stay in `cuems-nodeconf`)* | **not applicable** — FR-032 says these do not move | FR-032 |

## 4a. The consumer's public import path (T084a)

```python
from cuemsutils.tools.NodeList import NodeRole, NodeIndex, node
```

**`cuemsutils.config` is internal.** `cuemsutils.config.__all__ == []` (contract C10) — a consumer
importing `cuemsutils.config.network_map.node` directly is importing an implementation detail that
happens to work today, the same status every name reachable through the emptied `cuemsutils.xml`
has carried since feature 006. `cuemsutils.tools.NodeList` is the one path this feature commits to.

---

## 5. What `cuems-engine` must change in feature 008 (T085)

Verified against the live call sites in `cuems-engine/src/cuemsengine/core/BaseEngine.py` at this
commit (`afff04a`), not transcribed from the spec:

| Site | Today | Must become |
|---|---|---|
| `BaseEngine.py:33` — `CONTROLLER_NETWORK_FLAG = "NodeType.master"` | a module-level string constant | `from cuemsutils.tools.NodeList import NodeRole`; compare against `NodeRole.controller` |
| `BaseEngine.py:410` — `node.get("node_type") == CONTROLLER_NETWORK_FLAG` (`_controller_ip_from_map`) | reads a key the converted document no longer has | `node.get("node_role") is NodeRole.controller` — and `node` is a typed object once `self.cm.network_map` is read through the migrated `ConfigManager`, so `.get` still works (it's dict-shaped) but the *value* comparison must change too |
| `BaseEngine.py:440` — same comparison, in the adopted-nodes host list | same | same fix |
| `BaseEngine.py:443` — `node.get("online") == "True"` | string comparison | `node.get("online") is True` — **found during this task's verification**, not in the original T006f inventory; independent of the `node_type` rename (§3's table, added row) |
| `BaseEngine.py:433` — `self.cm.network_map.get_nodes_by_adoption(network_dict)` | calls the now-deprecated, mutating method | migrate to `NetworkMap.partition_by_adoption(self.cm.network_map)` (US6, T082) — returns bare node objects, not `{"node": ...}` wrappers, so the unpacking at the call site changes shape too |

## 6. What `cuems-editor` must change in feature 008 (T086)

Verified against `cuems-editor/src/cuemseditor/CuemsWsServer.py` at this commit (`ef74136`):

| Site | Today | Must become |
|---|---|---|
| `CuemsWsServer.py:425` — `basic_fields = ['online', 'adopted', 'ip', 'name', 'node_type', 'mac', 'role_id', 'alias', 'hostname']` (`merge_nodes` or equivalent, ~line 384–431) | names `'node_type'`; the merge silently drops that field once the document no longer has it | rename to `'node_role'` in the list. Also: `online`/`adopted` become `bool` after this feature — if this merged dict is what reaches the UI payload verbatim, feature 008 must decide whether the frontend needs the wire string form (`to_wire()`) or can consume `bool` directly; this feature does not answer that, it only surfaces the question (FR-UX-001 is a `cuems-utils`-side contract, not a frontend one) |
| `CuemsWsServer.py:470` — `NetworkMap.get_nodes_by_adoption(network_map_dict)` (`reload_network_map_nodes`) | same deprecated, mutating call as `cuems-engine`'s | same migration to `partition_by_adoption` |

**No frontend (Angular) change is required by this repository's own note pattern** (mirroring
feature 006's `frontend-note.md`) unless feature 008 decides the wire-string question above
resolves toward changing the payload shape; that decision is feature 008's, not restated here.

---

## 7. The release gate (T087, T087a, T087b)

**Stated as a gate, per M5** (`contracts/schema-migration.md`):

1. `cuems-utils` — schema, model, engine, write path. **Landed, this pass.**
2. `cuems-nodeconf` — model and serializers deleted; the sole writer follows the schema. **Not
   started this pass** (Phase 7 / US5, descoped).
3. `cuems-common` — mirror, conversion, tools, documentation. **Not started this pass** (Phase 5 /
   US3, descoped).
4. **Feature 008** — `cuems-engine` and `cuems-editor` readers (§5, §6 above).

**No release of any of the three repositories ships before step 4.** The hard cutover has no
working partially-deployed state: a converted map meets an unmigrated reader (§3's table — silent,
not loud), or an unconverted map meets the migrated schema (`SchemaError`, C8) — either way a node
stops functioning, not gracefully.

**The cluster, not just one machine** (T087a): a staged rollout — some nodes converted, some not,
or a controller upgraded ahead of its nodes — is **not supported**. `network_map.xml` is the
controller's view of every node; a controller running the migrated schema and reading an
unconverted map fails closed (C8) rather than partially. The cluster upgrades as a unit, at step 3
above, once `cuems-common` ships the conversion in `postinst`.

**Enforcement status, honestly**: FR-030d's versioned package dependencies (T054a, "an out-of-order
upgrade is refused rather than merely discouraged") are `cuems-common` `debian/control` changes —
**not implemented in this pass**, because `cuems-common` is out of scope. Until that phase lands,
this gate is **documented, not enforced** — `dpkg` will not by itself refuse installing a migrated
`cuems-utils` ahead of a converted `cuems-common`. Recorded here so "the gate exists" is not
conflated with "the gate is mechanically guaranteed" before it actually is.

**Downgrade is unsupported** (T087b): no reverse conversion (`node_role` → `node_type`) is
provided, or planned — `NodeRoleType`'s enumeration is a narrower vocabulary than free text was,
and a value written as `controller` has no principled string to revert to (`master` and `firstrun`'s
bare spelling are both plausible; the mapping is not invertible). The only path back for a converted
node is restoring the timestamped backup the conversion script writes before any change (FR-011i,
`test_backup_precedes_write_and_restores_exact_bytes`) — which is why that backup is not optional
and is asserted to reproduce the pre-conversion bytes exactly (SC-011).

---

## 8. Schema item X9: resolved (T088)

`PutType` — declared in `network_map.xsd`, referenced by no element in it — is **deleted**, not
re-deferred. Removed from three places in the same commit (`f04ec26`):

1. The schema (`<xs:complexType name="PutType">` in `network_map.xsd`).
2. The model class (`cuemsutils.config.network_map.PutType`).
3. The registry binding (`nm.PutType` in `_config_models("network_map")`).

**Rationale**: nothing in the schema references it — no element anywhere has `type="cms:PutType"`
within `network_map.xsd` — so it was dead weight carried since before this feature, discovered
during the schema edit rather than searched for deliberately. `project_mappings.xsd`'s own
`PutType` (a *different* complex type, different field set, different schema — research R4's "one
registry per schema") is untouched; deleting one could never have implied deleting the other, and
`tests/contract/test_schema_scope.py` pins that no schema but `network_map.xsd` changed.

`tests/contract/test_node_coherence.py::test_no_network_map_type_is_bound_to_generic` and the
registry's own `validate()` (raises `RegistryIncompleteError` for an unbound complex type) are what
would have caught a dangling reference had one existed; neither fired, confirming the type was
truly unreferenced rather than silently miscounted.

---

## 9. Avahi discovery files excluded from SC-004a (T060, T060a)

See §4 of `contracts/schema-migration.md` (M4) for the full table. Named here as the explicit
exclusion set SC-004a's occurrence count is measured against — never a pattern, always these four
files:

| File | Carries |
|---|---|
| `etc/avahi/services/cuems.service` | `node_type` TXT record |
| `usr/share/cuems/cuems.service.master` | TXT record **and** the retired word in its filename |
| `usr/share/cuems/cuems.service.slave` | TXT record **and** the retired word in its filename |
| `usr/share/cuems/cuems.service.firstrun` | TXT record |

Deferred to feature 008 (a discovery surface, not the XML document — spec Assumption 10). Renaming
`cuems.service.master`/`cuems.service.slave` reaches `debian/install` and anything resolving a
template by name, which is why it is not done incidentally here.

---

## 10. SC-004a re-verified for `cuems-utils` (T092)

Re-running T006's inventory (`baseline.md`'s "Symbol inventory" table recorded 192 occurrences
across three repositories at the pre-feature commit) against `cuems-utils` alone, at this feature's
landing:

```bash
grep -rln "node_type\|NodeType\." src/cuemsutils/ --include="*.py" --include="*.xsd"
grep -rln "node_type\|NodeType\." tests/data/ tests/support/ --include="*.py"
```

**Zero occurrences in live code paths.** What the grep *does* still find, and why each is not a
violation:

- `src/cuemsutils/errors.py`, `src/cuemsutils/tools/ConfigBase.py` — the migration-naming
  diagnostics (`network_map_node_type_message`, T044) necessarily reference the retired spelling
  *to detect it in a document and name it in the error*. This is the machinery that makes the old
  vocabulary's presence loud (C8), not a live consumer of it.
- `src/cuemsutils/config/network_map.py`, `src/cuemsutils/xml/schemas/network_map.xsd` — prose
  and a comment stating what the rename replaced, for a future reader.
- `tests/` — either the same diagnostic-testing pattern (`test_node_errors.py`,
  `test_network_map_conversion.py` deliberately construct legacy-spelling documents to prove they
  are rejected or converted), or `test_schema_scope.py`'s hash-pinning comment, or
  `test_coherence.py:118`'s `test_the_two_node_types_are_different_classes` — a **false-positive
  match**: this is `network_map.xsd`'s complex type `NodeType` (research R3 — "the type of a
  `<node>` element", unrenamed by this feature) versus `project_mappings.xsd`'s unrelated `NodeType`
  binding, nothing to do with the retired role vocabulary.
- `tests/data/corpus/**/network_map.xml`, `tests/data/network_map.xml` — **zero** occurrences; the
  live corpus is fully converted (T015).

**Excluded from this count, deliberately**: `specs/007-node-model-migration/pre-state/` (a
snapshot of the pre-conversion documents, kept specifically to measure the FR-010 diff against —
finding the old spelling there is the point, not a defect) and this feature's own spec/planning
prose (`baseline.md`, `golden-changes.md`, this file), which discusses the migration by name
throughout.

**Not measured here**: `cuems-nodeconf` and `cuems-common`. Both still carry the pre-feature counts
from `baseline.md` (146 and 27 respectively) because neither repository was edited this pass — SC-
004a's full claim (zero across all three) is **not yet true**, and is not claimed to be; it becomes
checkable again once Phases 5 and 7 land.

---

*Sections 4–8, 10 are filled in by their respective Phase 5/7/9 tasks (T054b, T078a, T078b, T084,
T084a, T085–T088, T079, T092) as the corresponding work lands. §10 above completes the cuems-utils
portion; the cuems-nodeconf/cuems-common portions remain open.*
