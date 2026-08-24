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

*Sections 4–8, 10–11 are filled in by their respective Phase 5/7/9 tasks (T054b, T078a, T078b,
T084, T084a, T085–T088, T079) as the corresponding work lands.*
