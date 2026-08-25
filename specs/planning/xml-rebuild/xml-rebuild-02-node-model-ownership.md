# XML infrastructure rebuild — Part 2a: Does the node model belong in `cuems-utils`?

**Status:** analysis for decision
**Date:** 2026-08-10
**Question (from review of [Part 1](xml-rebuild-01-audit.md), Q8):** given that
`cuems-nodeconf`'s `feat/nodeconf-reenable` lands shortly, analyse the real need for
`NodeXmlBuilders` to be scoped outside `cuems-utils`, compare against equivalent usage in
sibling repos, and evaluate incorporating the NodeConf data model into the `cuemsutils`
package.

**Answer, up front:** the node model does not need to be outside `cuems-utils`, and its
being outside is the *cause* of finding F8, not a constraint on fixing it. Recommendation
in §7 — move the persistence-facing half, leave discovery in nodeconf.

> **State note:** `cuems-nodeconf` was verified in sync (`main` 0/0 vs `origin/main`, clean
> tree). It is currently checked out on `feat/nodeconf-reenable`, whose package layout
> (`cuemsnodeconf/`) this analysis uses. Line references are to that branch.

---

## 1. Where the network-map concern actually lives today

| Concern | Owner | Consumers |
|---------|-------|-----------|
| **Schema** `network_map.xsd` | **`cuems-utils`** `xml/schemas/` | mirrored to `/etc/cuems/` by `cuems-common` |
| **Read path** `NetworkMap(Settings)`, `get_node`, `get_nodes_by_adoption` | **`cuems-utils`** [Settings.py:102-151](../../src/cuemsutils/xml/Settings.py#L102-L151) | `cuems-engine` `ControllerEngine.py:249`, `cuems-editor` `CuemsWsServer.py:470` |
| **Config integration** `load_network_map`, `node_network_map` | **`cuems-utils`** [ConfigManager.py:59-123](../../src/cuemsutils/tools/ConfigManager.py#L59-L123) | engine, editor |
| **Object model** `node`, `node_list`, `NodeType` | `cuems-nodeconf` `cuemsnodeconf/CuemsNode.py` (110 LOC) | nodeconf only |
| **Write path** `node_listXmlBuilder`, `nodeXmlBuilder` | `cuems-nodeconf` `cuemsnodeconf/NodeXmlBuilders.py` (90 LOC) | nodeconf only |
| **Parse-to-objects** `nodeParser`, `node_listParser` | `cuems-nodeconf` same file | nodeconf only |
| **Dead stubs for exactly this job** `CuemsNodeDictXmlBuilder`, `CuemsNodeDictParser` | **`cuems-utils`** [XmlBuilder.py:73](../../src/cuemsutils/xml/XmlBuilder.py#L73), [Parsers.py:313](../../src/cuemsutils/xml/Parsers.py#L313) | **nobody** |

`cuems-utils` already owns the schema, the read path, and the configuration integration for
network maps. It owns everything except the object model and the serializers — the two
pieces that then have to reach back into it by monkeypatching module globals.

**The last row is the tell.** `CuemsNodeDictXmlBuilder` and `CuemsNodeDictParser` live in
`cuems-utils`, are referenced by nothing, and are named after `CuemsNodeDict` — which is
nodeconf's own backwards-compatibility alias for `node_list`
(`CuemsNode.py:108`). Their bodies are near-duplicates of nodeconf's
`node_listXmlBuilder` / `node_listParser`. This migration was started and abandoned.

---

## 2. Comparison with sibling repos

Every other consumer follows one pattern, and `cuems-nodeconf` is the sole exception.

| Repo | Schema | Object model | Serialization | Repo's own role |
|------|--------|--------------|---------------|-----------------|
| `cuems-engine` | cuems-utils | cuems-utils (`cues/`) | cuems-utils | orchestration only — `XmlReaderWriter(...).read_to_objects()` |
| `cuems-editor` | cuems-utils | cuems-utils (`cues/`) | cuems-utils | orchestration only — `CuemsParser`, `write_from_object` |
| `cuems-nodeconf` | **cuems-utils** | **nodeconf** | **nodeconf** | orchestration **+ model + serializers** |

Verified: nodeconf is the **only** repo in the ecosystem that subclasses the builder or
parser classes. A grep for builder/parser extension across `cuems-engine`,
`cuems-editor`, `cuems-common`, `cuems-wsclient`, `cuems-audioplayer`,
`cuems-videocomposer` and `cuems-dmxplayer` returns one hit, and it is a *comment* in
`cuems-engine/src/cuemsengine/cues/ActionHandler.py:715` referring to `GenericParser`
behaviour — not an extension.

So the `globals()` monkeypatch (F8) is not a general-purpose extension point that other
repos depend on. **It has exactly one user, and that user exists only because the model
was placed on the wrong side of the boundary.** If the model moves, F8's requirement for a
public registration API disappears rather than being replaced.

---

## 3. Evidence the split is already causing damage

Six independent defects, all traceable to the model being separated from its schema.

### 3.1 F7 — the coercion bug exists *because* the parser is external
`nodeParser` re-implements `GenericParser.parse()` and, in doing so, calls
`self.str_to_value(dict_value)` without `key=`
(`cuemsnodeconf/NodeXmlBuilders.py:80`), losing `STRING_TYPED_KEYS` protection. A
first-party parser inside `cuems-utils` would have inherited the fix automatically. This
is the direct cost of a 90-line copy living in another repo: a bug fixed in one place
stayed open in the other.

### 3.2 The model has drifted from its own schema
`network_map.xsd` declares `role_id`, `alias` and `hostname` (the `feat/node-identity`
fields). The `node` class declares properties for `uuid`, `mac`, `name`, `node_type`,
`ip`, `adopted`, `online` — **and none of the three identity fields**. They survive only as
untyped dict keys, which is exactly why F7 damages them silently. Schema and model are
maintained in different repos and have already diverged.

### 3.3 `NodeType` is defined twice inside nodeconf
`CuemsNode.node.NodeType` (`CuemsNode.py:36`) and `AvahiTool.NodeType`
(`AvahiTool.py:9`) are two separate enums with identical members
(`slave`, `master`, `firstrun`). Neither is the schema's.

### 3.4 The schema does not constrain `node_type` at all
`network_map.xsd` types it as `cms:NonEmptyString` — any non-blank text validates. The
three-value vocabulary exists only in Python, twice, in the repo that does not own the
schema.

Note also that `cuems-utils/CLAUDE.md` states *"the `NodeType.master|slave` enum and
identity fields live here"* (in the XSD). The identity fields do; **the enum does not** —
it is not in the schema in any form, and the real vocabulary has a third member,
`firstrun`. The documentation already describes the ownership we do not have.

### 3.5 A `str()`/`__repr__` mixup leaked into a cross-repo wire format
`node.NodeType` overrides `__repr__` to return `self.name`, but the builder serializes with
`str(value)` — and `Enum.__str__` yields `"NodeType.slave"`, not `"slave"`. Verified:

```
str(NodeType.slave)  -> 'NodeType.slave'      # what gets written
repr(NodeType.slave) -> 'slave'               # what was intended
```

Because the XSD accepts any non-empty string (§3.4), this validated silently and became
permanent. It is now an *enshrined* contract:

- `CuemsNodeConf.py:425-428` — `# node_type -> "NodeType.<name>" string for cuems-engine
  compatibility`, then `snode['node_type'] = f"NodeType.{nt.name}"`
- `CuemsNodeConf.py:578` — `# Normalize node_type - handle both "master" and
  "NodeType.master" formats`
- `CuemsNodeConf.py:411` — `# converting node_type enum -> str in place broke later enum
  comparisons`

A serialization bug in an external model became an inter-repo compatibility requirement,
and nodeconf now carries normalization code for both spellings. *(For accuracy: this does
not currently break `node_list.masters/.slaves/.firstruns`, because those are only ever
evaluated against the live Avahi discovery dict — `self.listener.nodes` — and never
against a map loaded from XML.)*

### 3.6 nodeconf uses APIs deprecated since 0.0.7
`XmlReader` / `XmlWriter` in `CuemsNodeConf.py` and `CuemsHwDiscovery.py`. Being outside
the library, nodeconf never felt the deprecation pressure the library intended.

---

## 4. What incorporating the model would look like

The seam that matters: **`cuems-utils` owns what a node *is* and how it is *stored*;
`cuems-nodeconf` owns how nodes are *found*, *adopted* and *configured*.**

**Moves into `cuems-utils`** (~200 LOC total):

| From | To | Note |
|------|-----|------|
| `node`, `node_list`, `NodeType` | `cuemsutils/cues/`-adjacent new module (e.g. `cuemsutils/xml/` or a `cuemsutils/nodes.py`) | `node` is already a `dict` subclass with property getters/setters — structurally identical to `CuemsDict`/`Cue`. It would gain `REQ_ITEMS`-style layered defaults for free. |
| `node_listXmlBuilder`, `nodeXmlBuilder` | replace the dead `CuemsNodeDictXmlBuilder` | finishes the abandoned migration |
| `nodeParser`, `node_listParser` | replace the dead `CuemsNodeDictParser` | **F7 dies here** — first-party parsers use `key=` |
| `role_id`, `alias`, `hostname` properties | added to `node` | closes the §3.2 drift |

**Stays in `cuems-nodeconf`:**

- `CuemsAvahiListener`, `AvahiTool`, `AliasPublisher` — mDNS/zeroconf discovery
- `CuemsNodeConf` — adoption flow, node-type election, systemd orchestration
- `CuemsConfServer`, `communicate.py` — the config-serving protocol

**Follows automatically:**

- F8's registration API becomes unnecessary — nothing external registers builders any more.
- `NetworkMap` can return `node_list` objects instead of raw nested dicts, so
  `get_nodes_by_adoption`'s dict-mutation contract (which `cuems-engine`
  `ControllerEngine.py:1155` already works around: *"We avoid
  `NetworkMap.get_nodes_by_adoption()` because it mutates the dict"*) can be given a clean
  non-mutating form.
- `NodeType` gains one definition, and X-numbered schema work can later constrain
  `node_type` to an `xs:enumeration` matching it.

---

## 5. Counter-arguments, honestly stated

1. **`node` objects carry live runtime state, not just persisted state.** The Avahi
   listener constructs `CuemsNode(...)` for discovered hosts that may never be written to
   disk, and `online` is a runtime fact. Moving the class means `cuems-utils` hosts a type
   used for transient discovery data.
   *Assessment:* acceptable. The class is a data holder; `online`/`adopted` are already
   schema fields. `cuems-utils` already hosts `Cue`, which likewise carries runtime state
   (`_armed_list`, `_go_thread`) alongside persisted fields.

2. **`masters` / `slaves` / `firstruns` are arguably domain logic.** Moving `node_list`
   moves them, giving `cuems-utils` vocabulary about cluster roles.
   *Assessment:* they are one-line predicates over `node_type`, a schema field. The
   ecosystem index (`cuems-RELATIONS`) already treats node roles as a shared concept, and
   `cuems-engine` already branches on adoption state.

3. **The `"NodeType.<name>"` wire format is now a cross-repo contract with
   `cuems-engine`.** Moving the enum means `cuems-utils` inherits the wart; fixing it is a
   coordinated change across nodeconf, engine and every `network_map.xml` on disk.
   *Assessment:* real, and it argues for moving the model **without** changing the wire
   format in the same step. Owning the wart in one place is strictly better than the
   current state, where two repos normalize for it independently. A later fix becomes
   possible; today it is not.

4. **nodeconf is mid-restructure.** `feat/nodeconf-reenable` is already moving these files.
   *Assessment:* this cuts both ways and is the main sequencing question (§7). Doing the
   move *as part of* that restructuring is cheaper than doing it afterwards as a second
   disruption.

5. **Scope.** This was framed as an `xml/` refactor; it now proposes a cross-repo
   ownership change.
   *Assessment:* it is ~200 LOC and it *removes* work from the rebuild — F7 and F8 both
   dissolve rather than needing designed solutions. But it is a genuine scope decision and
   is yours to make, not mine to assume.

---

## 6. What happens if we do nothing

The rebuild still works, but it must:

- design, document and support a **public builder/parser registration API** purely for one
  external consumer (F8);
- keep `str_to_value` (or its schema-driven successor) callable from outside with a
  key-aware signature that external parsers can get wrong again (F7 recurrence risk);
- leave `CuemsNodeDictXmlBuilder` / `CuemsNodeDictParser` as dead code, or delete them and
  lose the record that the migration was intended;
- accept that `network_map.xsd` and the `node` model continue to drift in separate repos.

That is a permanent tax paid to keep 200 LOC on the far side of a boundary that nothing
else in the ecosystem observes.

---

## 7. Recommendation

**Move the persistence-facing half of the node model into `cuems-utils`; leave discovery
and adoption in `cuems-nodeconf`.** Do not change the `"NodeType.<name>"` wire format in
the same step.

Sequencing, given that `feat/nodeconf-reenable` lands shortly:

1. **Now, independent of the rebuild:** apply the F7 fix to both `main` and
   `feat/nodeconf-reenable` as separate commits (per the Q6 decision), with a regression
   test. This is a one-line change and must not wait on an ownership decision.
2. **Let `feat/nodeconf-reenable` land.** Do not add churn to a branch mid-flight.
3. **Then move the model**, against the settled `cuemsnodeconf/` layout, as its own
   change with its own version bump — before the XML rebuild, so the rebuild never has to
   design the F8 registration API at all.
4. **Then rebuild `xml/`**, with F7 and F8 already dissolved and one fewer external
   consumer of the builder internals.

This ordering means the rebuild's blast radius shrinks rather than grows: by the time it
starts, `cuems-nodeconf` is a plain `XmlReaderWriter` consumer like `cuems-engine` and
`cuems-editor`.

---

## 8. Consequences for Part 1's findings

| Finding | Effect if §7 is adopted |
|---------|-------------------------|
| **F7** (nodeconf coercion bug) | Fixed in step 1; permanently prevented in step 3 — the parser becomes first-party. |
| **F8** (globals monkeypatch) | **Dissolved.** No external registrant remains; no public registration API needs designing. |
| **F10** (dead code) | `CuemsNodeDictXmlBuilder` / `CuemsNodeDictParser` stop being dead — they become the landing site. |
| **§3 consumer inventory** | `cuems-nodeconf` drops from "deep coupling, must migrate" to the same light coupling as `cuems-engine`. |
| **D2 feasibility** | Improves. `network_map.xsd` is small, fully typed, and would be the cleanest first target for the schema-driven serializer. |
| **X9** (`PutType` unreferenced) | Should be resolved during the move, alongside `cuems-common`'s mirrored copy. |

---

## 9. Decision

**Q9 resolved: adopt §7 in full** — move `node`, `node_list`, `NodeType` **and** the
builders/parsers into `cuems-utils`; leave Avahi discovery, adoption and systemd
orchestration in `cuems-nodeconf`. The `"NodeType.<name>"` wire format is **not** changed
in the same step.

### Progress

- ✅ **Step 1 — F7 fixed on both branches.** `cuems-nodeconf` `4b6844e` (main) and
  `0a3ce37` (`feat/nodeconf-reenable`). Committed locally, **not pushed**.
- ⏳ **Step 2** — let `feat/nodeconf-reenable` land.
- ⏳ **Step 3** — move the model (this document's recommendation), own version bump.
- ⏳ **Step 4** — rebuild `xml/`, with F7 and F8 already dissolved.

`STRING_TYPED_NODE_FIELDS` and `tests/test_node_field_coercion.py` migrate with the parser
in step 3; the field list is stated from `network_map.xsd`, so it transfers unchanged.
