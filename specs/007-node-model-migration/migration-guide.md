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

**Scope note, updated**: `cuems-utils` (Phases 1–4, 6, 8) landed in an earlier pass. Phase 5 (US3,
`cuems-common`) and Phase 7 (US5, `cuems-nodeconf`), descoped from that earlier pass, have now
landed too — each on its own `007-node-model-migration` branch, in its own repository, as **local
commits only**. Nothing in either sibling repository has been pushed or merged; §7 (the release
gate) states what that does and does not authorise. The table below now reflects the actual state
of every symbol T006a's inventory named, not an intended one.

| Source | New home | Status | Authorising requirement |
|---|---|---|---|
| `cuemsnodeconf.CuemsNode.node` | `cuemsutils.config.network_map.node` (internal) / `cuemsutils.tools.NodeList.node` (public re-export) | **landed** — typed, tested (C1–C11), constructible directly (FR-004) | FR-002, FR-002b, data-model §3.2 |
| `cuemsnodeconf.CuemsNode.node_list` | `cuemsutils.config.network_map.node_list` | **landed** — unchanged from feature 006, registry-bound | FR-002, data-model §3.3 |
| `cuemsnodeconf.CuemsNode.CuemsNodeDict`, `CuemsNode` (aliases) | *(deleted, not recreated)* | **landed** by policy — FR-002a is explicit that no shim is created | FR-002a |
| `cuemsnodeconf.AvahiTool.NodeType` (enum) | `cuemsutils.tools.NodeList.NodeRole` | **landed** — values verified against the loaded schema (C1) | FR-001, research R3 |
| `cuemsnodeconf.NodeXmlBuilders.{node,node_list}XmlBuilder` | `cuemsutils.xml.documents.build_tree` (registry-driven, via `CuemsNetworkMapType.save`) | **landed** — the write path exists and is tested (C4, C5) | FR-009, research R6 |
| `cuemsnodeconf.NodeXmlBuilders.{node,node_list}Parser` | `cuemsutils.xml.mapper.Mapper.decode_config` (registry-driven) | **landed** — was already true from feature 006's bindings | FR-011a, research R1 |
| `cuemsnodeconf.NodeXmlBuilders.STRING_TYPED_NODE_FIELDS` | *(deleted, not recreated — structural guarantee instead)* | **landed** — `tests/contract/test_node_field_coercion.py` asserts its absence (T064) and the structural replacement (T065) | FR-012, research R4 |
| `cuemsnodeconf.CuemsNodeConf`'s MAC-keyed working set | `cuemsutils.tools.NodeList.NodeIndex` | **landed** — `CuemsNodeConf.__init__`, `read_network_map`, `write_network_map` and every call site now build/consume a `NodeIndex` (T074) | research R5 |
| `cuemsnodeconf.CuemsNode.py`, `NodeXmlBuilders.py` (the files) | *(deletion target)* | **landed** — both files deleted (T071, T072), local branch | FR-018 |
| `cuemsnodeconf.CuemsNodeConf.py`'s `node_type` normalisation, hand-rolled atomic write, `XmlReader`/`XmlWriter` use | *(removal target — the upstream model and `save()` make each unnecessary)* | **landed** — `read_network_map` has no normalisation left (T075), `write_network_map` calls `CuemsNetworkMapType.save()` (T076), no `XmlReader`/`XmlWriter` import remains in `CuemsNodeConf.py` (T077; `CuemsHwDiscovery.py` named in the task does not exist in this repository — confirmed by directory listing, so there was nothing to retire there) | FR-015, FR-031, research R6 |
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

1. `cuems-utils` — schema, model, engine, write path. **Landed.**
2. `cuems-nodeconf` — model and serializers deleted; the sole writer follows the schema. **Landed
   on a local `007-node-model-migration` branch** (Phase 7 / US5) — not pushed, not merged, not
   released.
3. `cuems-common` — mirror, conversion, tools, documentation. **Landed on a local
   `007-node-model-migration` branch** (Phase 5 / US3) — not pushed, not merged, not released.
4. **Feature 008** — `cuems-engine` and `cuems-editor` readers (§5, §6 above). **Not started.**

**No release of any of the three repositories ships before step 4.** The hard cutover has no
working partially-deployed state: a converted map meets an unmigrated reader (§3's table — silent,
not loud), or an unconverted map meets the migrated schema (`SchemaError`, C8) — either way a node
stops functioning, not gracefully. Landing steps 2 and 3 as local commits does not change this —
"landed" here means the branch exists and its own suite is green (§14), not that either repository
is releasable in isolation.

**The cluster, not just one machine** (T087a): a staged rollout — some nodes converted, some not,
or a controller upgraded ahead of its nodes — is **not supported**. `network_map.xml` is the
controller's view of every node; a controller running the migrated schema and reading an
unconverted map fails closed (C8) rather than partially. The cluster upgrades as a unit, once
`cuems-common`'s branch (step 3) ships the conversion in `postinst` via an actual release.

**Enforcement status, honestly**: FR-030d's versioned package dependencies (T054a, "an out-of-order
upgrade is refused rather than merely discouraged") are now present in `cuems-common`'s
`debian/control` on its local branch (`Breaks: cuems-nodeconf (<< 0.1.0-8)`, alongside
`cuems-utils (>= 0.1.0rc15)`). **Mechanical demonstration is moved to feature 008** (T054b, §13):
no packaging/build sandbox was available in either pass of this feature to actually install an
out-of-order combination and watch `dpkg` refuse it — and no releasable `.deb` of any of the three
repositories exists until feature 008's release anyway. The constraint is written and reviewed here;
running it against a real install is feature 008's, alongside the release it gates. Recorded here so
"the gate exists" is not conflated with "the gate is mechanically guaranteed" before it actually is.

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

**Re-measured now that Phases 5 and 7 have landed** (local branches, not pushed — §7): neither
repository is at zero, and neither is expected to be — SC-004a's own class of exclusion (§9, the
four Avahi files) and the diagnostic-testing pattern (§10 above) both recur here, this time in a
second and third repository:

- `cuems-common` — non-diagnostic hits are exactly the four Avahi service-template files §9 already
  excludes (`cuems.service.master`, `cuems.service.slave`, `cuems.service.firstrun`, plus the
  base `cuems.service`, deliberately untouched — verified against §9's table by name). Every other
  hit is either the mirrored schema's explanatory comment (`etc/cuems/network_map.xsd:50`, prose,
  same pattern as `cuems-utils`'s own copy) or a test deliberately constructing a legacy-spelling
  document to prove it converts or is refused (`tests/test_network_map_conversion.py`,
  `tests/test_controller_resolution.py`).
- `cuems-nodeconf` — non-diagnostic hits are the Avahi wire-format boundary itself
  (`CuemsAvahiListener.py`, `AvahiTool.py`, `CuemsSettings.py`): the TXT record key/value stays
  `node_type=master`/`slave`/`firstrun` until feature 008 (spec Assumption 10), so these sites
  necessarily still name it, each behind the explicit `_AVAHI_NODE_TYPE_TO_ROLE` translation dict
  documented at every one of the three call sites. Everything else is either a code comment
  explaining the migration (`CuemsNodeConf.py:430,563`) or the same deliberate-construction test
  pattern (`tests/test_node_type.py`, `tests/test_avahi_listener.py`). The one exception:
  `test_run_nodeconfig.py` (repository root) — an orphan (§11) with the retired vocabulary as a
  live literal, left as found because it is dead code no path reaches, not because it was missed.

SC-004a's full claim (zero across all three, outside the named exclusions) now holds for the parts
of each repository this feature's scope actually touches — the two Avahi wire-format boundaries
(here and in `cuems-common`'s templates) are the same explicitly-deferred exception §9 already
named, not a new one.

---

## 11. The FR-018 orphan search (T078a)

Symbols, modules and tests whose subject is the node model or its serialization, with no caller in
their own repository and no consumer outside it — searched across both repositories now that Phase
5 and Phase 7 have landed.

**The duplicate-named legacy modules in `src/cuemsutils/xml/`**, named explicitly by this task so
"we looked" is distinguishable from "we did not think to look":

| Module | Holds node content? |
|---|---|
| `Settings.py` | No — a deprecation shim (`deprecated_alias` re-exports of `settings.py`'s classes); carries no logic of its own. |
| `settings.py` | **Yes** — `NetworkMap.get_node`, `get_nodes_by_adoption` (deprecated) and `partition_by_adoption` all read `node_list`/`node` shape. This is the module `cuemsnodeconf.CuemsNodeConf.read_network_map` now imports as `_NetworkMapReader` (T075). |
| `XmlReaderWriter.py` | No — a deprecation shim. |
| `xml_reader_writer.py` | No — generic reader/writer machinery (`CuemsXml`), schema-agnostic. |
| `CMLCuemsConverter.py` | No — a deprecation shim. |
| `converter.py` | No — the D5 thin converter, schema-agnostic. |
| `Parsers.py` | No — generic cue-oriented parser machinery; no `node`/`network_map` reference. |
| `XmlBuilder.py` | No — generic builder machinery; no `node`/`network_map` reference. |

**Orphans found in `cuems-nodeconf`** (repository root, outside the migrated `cuemsnodeconf/` and
`tests/` trees):

| Path | Finding |
|---|---|
| `test_xml_roundtrip.py` | Deleted (T078) — its subject, the `NodeXmlBuilders.py` globals-injection mechanism, no longer exists. |
| `test_run_nodeconfig.py` | **Orphan, left in place.** A manual smoke script (`from CuemsAvahiListener import ...` — a bare top-level import that does not resolve from the package layout `cuemsnodeconf.CuemsAvahiListener` uses everywhere else, so it has not been runnable as `python test_run_nodeconfig.py` for some time). References `CuemsConfServer` and the pre-migration `listener.nodes.master`/`.slaves` API (singular `.master`, which never existed even before this feature — the real attribute was always plural `.masters`). No file in `cuemsnodeconf/` or `tests/` imports it; `run_nodeconf.py` (the actual systemd entry point) imports only `CuemsNodeConf`. Not deleted, because deletion was not in scope for this task (T078 named only `test_xml_roundtrip.py`) — recorded here so its orphan status is documented rather than silently discovered later. |
| `test_run_classes.py` | **Orphan, left in place.** Same repository-root pattern: `from CuemsNodeConf import CuemsNodeConf` (bare top-level import, same non-resolving layout). No caller anywhere. Not deleted, same reasoning as above. |
| `cuemsnodeconf/CuemsConfServer.py` | **Orphan within the package.** Its only consumer is `test_run_nodeconfig.py` above — itself an orphan. `run_nodeconf.py` does not construct a `CuemsConfServer`. Not touched (T078a is a search-and-record task, not a deletion task, and it is not one of the two files T071/T072 name). |
| `cuemsnodeconf/CuemsSettings.py` | **Orphan within the package**, transitively: its only consumer is `CuemsConfServer.py` above. Not touched, same reasoning. |
| `cuemsnodeconf/AvahiTool.py` | Confirmed orphan (already noted at T073's implementation, restated here for the record): a standalone manual debug CLI (`if __name__ == "__main__"`), self-referencing only. Its `NodeType` enum duplicate was removed and replaced with `NodeRole` (T073) precisely because the file itself was kept — an orphan is not evidence a file should be deleted without instruction, only that it has no production caller. |

**No further orphans found in `cuems-common`**: Phase 5's four-commit scope (schema mirror, script,
three tools, docs) touched only files with existing production callers (`postinst`,
`debian/install`, the systemd units invoking the three scripts); nothing new was left dangling.

## 12. The FR-032 boundary check (T078b)

Searching the migrated surface (`cuemsutils.tools.NodeList`, `cuemsutils.config.network_map`, and
every call site touched in `cuems-nodeconf`'s Phase 7) for discovery, adoption and orchestration
symbols against §2's inventory (`cuems-nodeconf discovery / adoption / orchestration symbols (stay
— FR-032)`):

**Count: 0.** None of the six symbols/modules that table names as staying —
`CuemsNodeConf` (orchestration + adoption), `CuemsAvahiListener` (discovery), `CuemsConfServer`
(req/rep server), `AliasPublisher` (Avahi alias publication), `AvahiTool` minus its now-removed
enum (discovery utility), `CuemsSettings` (local config) — were moved, renamed, or reimplemented in
`cuemsutils` by this feature. `CuemsNodeConf.py` and `AvahiTool.py` were edited **in place** to
*consume* the upstream model (T073–T077), which is what FR-032 anticipates as a call-site change,
not a boundary crossing. SC-013 (the count named in this task) is satisfied at zero.

## 13. The out-of-order-upgrade enforcement demonstration (T054b)

**Moved to feature 008, not completed here — recorded as a deliberate move, not silently dropped.**
T054a's versioned package constraint (`cuems-common`'s `debian/control`: `Depends: cuems-utils (>=
0.1.0rc15)`, `Breaks: cuems-nodeconf (<< 0.1.0-8)`) is written and reviewed by inspection. T054b
asks for more: an actual `dpkg -i` of an out-of-order combination, showing the refusal happen. That
requires a Debian packaging/build sandbox (a `.deb` built from each of the three repositories,
installed in sequence) that was not available in either pass of this feature — and, more to the
point, all three repositories only exist as unreleased local branches until feature 008 lands (§7):
there is no built `.deb` of any of them yet to install in the wrong order. Feature 008 is the first
point a real cross-repository release exists, which makes it the first point this demonstration is
actually possible rather than merely theoretical. SC-012 is therefore satisfied by this feature's
scope (the constraint exists and is reviewed) but its *demonstration* is feature 008's to run,
alongside the release it is gating.

## 14. `cuems-nodeconf`'s suite result (T079)

Run against the migrated `cuemsutils` (editable install, this repository's working tree, pyenv
3.11.9 — the same interpreter `cuems-utils`'s own CLAUDE.md names as canonical for this project):

```
78 passed in 26.87s
```

Zero failures, zero skips. Composition: the 67 tests already present under `tests/` (12 rewritten
off the deleted `CuemsNode`/`CuemsNodeDict` API onto `NodeIndex`/`NodeRole`/`node` — dict-key access
throughout, since none of these classes define `__getattr__`; a fixture UUID in
`test_phase1_changes.py` was also corrected from a non-canonical string to a schema-valid one, since
`network_map.xsd`'s `UuidType` pattern now rejects it where the old free-text `node_type` model
never checked), plus T067 (`test_node_type.py`), T068 (appended to `test_node_adoption.py`) and T069
(`test_no_injection.py`) added by this task, plus `dbus.UInt32` added to `tests/conftest.py`'s
existing `dbus` stub (needed once `test_phase1_changes.py`'s `AliasPublisher` test could actually
run, having previously been blocked at collection by the `CuemsNode` import error). `tests/`
composition: `NodeIndex`/`NodeRole`/`node` from `cuemsutils.tools.NodeList` throughout, no
`CuemsNode`/`CuemsNodeDict` reference remaining anywhere under `tests/`.
