# Migration guide — feature 010, consumer migration

**Status**: accumulating. This document is written **as the work lands**, not retrofitted at the
end (FR-002, FR-005). Sections are stubs until their wave closes.
**Audience**: the six consumer repositories' spec-kit flows, and whoever runs the next
ecosystem-wide sweep.
**Constitution III**: this guide is feature 010's user-experience deliverable.

Its inputs are `specs/007-node-model-migration/migration-guide.md` and
`specs/008-rebuild-extension/migration-guide.md` — both are input inventories, not background
reading.

---

## 1. What changed, entry point by entry point

*(FR-UX-001 — every removed or changed entry point mapped to its replacement, with before/after
examples, at call-site granularity, so a consumer flow can be written against this without reading
library source.)*

| Removed / changed | Replacement | Landed in |
|---|---|---|
| `cuemsutils.xml.settings.NetworkMap` (internal) | `ConfigManager.load_network_map()` + `.network_map` — returns an equal dict, asserted in `tests/contract/test_public_equivalents.py` | wave 0 |
| `cuemsutils.xml.mapper.Mapper` (internal) | **nothing — delete the import.** Measured 2026-09-04: `cuems-nodeconf` imports it and never calls it; the import line is its only occurrence in that repository | wave 0 |
| `cuemsutils.xml.mapper.read_config_document` (internal) | **nothing — delete the import**, same measurement | wave 0 |
| `cuemsutils.timeoutloop.Timeoutloop` (deprecated) | `cuemsutils.tools.TimeoutLoop.TimeoutLoop` — note the class also changes spelling, `Timeoutloop` → `TimeoutLoop` | wave 3 |
| `cuemsutils.config.network_map.CuemsNetworkMapType` (internal) | **`ConfigManager.network_map`** — it already returns a live one, `.save`/`.refresh` included. Retain the document that `load_network_map()` returns and refill its `node_list`; do not construct one. See [§4a](#️-one-finding-the-gate-caught-a-third-internal-import) | **closed** 2026-09-21 by `cuems-nodeconf` feature 002 |
| _(accumulates)_ | | |

## 2. The public descriptor path *(wave 0)*

**Requires `cuemsutils >= 0.1.0rc16`.** The surface below landed *after* `0.1.0rc15`, which is what
every consumer currently pins, so `rc15` cannot express "I need the descriptor". The library was
bumped to `0.1.0rc16` on 2026-09-07 for exactly this reason: an API nobody can name a version for
is an API nobody can depend on, and wave 0 is not usable until its consumers can pin it.

Note this is a **floor**, and FR-091 requires the gate to acquire an upper bound or a `Breaks:` as
well — a floor cannot express "must refuse a library that has moved past me", which is what the
release gate says. That is wave 4's work; the floor is what unblocks flows 02 and 05 now.

Landed 2026-09-04. Written at call-site granularity so flows 02 (`cuems-editor`) and 05
(`cuems-frontend`) can be built against it without reading library source.

### The surface

```python
from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

manager = ConfigManager(load_all=False)

types = manager.get_schema_descriptor(SchemaName.SCRIPT)   # all six schemas
example = manager.generate_example(SchemaName.SCRIPT)      # script and settings only
```

`SchemaName` has six members — `SCRIPT`, `SETTINGS`, `NETWORK_MAP`, `PROJECT_MAPPINGS`,
`PROJECT_SETTINGS`, `OUTPUTS` — whose values are the registry's own strings, so
`SchemaName(name)` and `member.value` cross between the two forms.

**A bare string is rejected**, deliberately (FR-028a). `get_schema_descriptor("script")` raises
`TypeError` naming the fix. Accepting both would reintroduce the stringly-typed surface the enum
exists to remove.

`generate_example` **raises `NotImplementedError`** for the four schemas with no generator, rather
than returning `None`. A silent `None` is the failure mode this feature exists to end.

### What a descriptor answers, per complex type

`get_schema_descriptor` returns a `TypeDescriptor` per complex type, in declared order. Each
carries `key`, `fields`, and `instance`. Each `FieldDescriptor` carries **five** facts —
`name`, `xsd_type`, `required`/`repeated`, `enum_values` (`None` unless the type is a restricted
enumeration), `default` — plus `repairability`.

`TypeDescriptor.instance` is the **sixth** fact and the one this feature added:

- **nested** — a complex field expands into its own instance, so
  `AudioCueOutputsType.instance["channels"]["channel"][0]["channel_num"]` resolves. This is what
  replaces `getTemplateOutputStructure`'s deep-clone of an example document;
- a **repeated** complex field carries **one exemplar**, not an empty list, because the call site
  clones element `[0]`;
- **callable and class defaults are not invoked** — they appear as `None`, and the callable stays
  visible on `FieldDescriptor.default`. Derivation is cached, so calling `new_uuid()` once would
  freeze one "fresh" identifier and hand the same one to every caller;
- it is a **seed the consumer fills**, and is **not** guaranteed schema-valid: 12 of the 58 complex
  types have a required field with no usable default.

### For the frontend (flow 05)

`master_vol`'s value comes from the descriptor's default (`100`), replacing the component's drifted
`|| 20`. `dmx_channels` likewise. `getTemplateOutputStructure` reads `TypeDescriptor.instance`
instead of cloning `initial_template`'s first output.

### For the editor (flow 02)

Serve `get_schema_descriptor` over the websocket. The descriptor and its instances are plain
dicts, lists, strings, numbers and `None` — JSON-serialisable as they stand, with one caveat:
`FieldDescriptor.default` may be a **callable or a class**, which is not. Project the fields you
send; `instance` is already safe.

## 3. Per-repository obligations

*(FR-UX-004 — which obligation landed in which repository. Seven flows produce seven task lists and
no single view of the whole; this is that view.)*

| Repository | Obligation | State |
|---|---|---|
| `cuems-utils` | descriptor path · deprecated-surface removal · this guide | **wave 0 landed** 2026-09-04 |
| `cuems-engine` | typed node map (role · online · adopted) · identity coercion at every ingress · the script version change · release-gate bounds | **landed** 2026-09-30 as its own feature `008-cuems-utils-migration` (64/64), **unmerged**; tag `1662a99` (2026-10-01, local). See [§4c](#4c-cuems-engine--the-typed-node-map-wave-1-landed-2026-09-30) |
| `cuems-editor` | the five show-parsing sites onto `CuemsScript` · the wire projection at one boundary · the fixup split · the descriptor and configuration-domain messages · the payload-version handshake · release-gate bounds | **landed** 2026-10-02 as its own feature `001-cuems-utils-migration` (**62/63**), **unmerged**; no tag (its message is written and held unready, T046/T061). The one open task is blocked on this library — `cuems-editor` UR-5. See [§4d](#4d-cuems-editor--the-wire-boundary-wave-2-landed-2026-10-02) |
| `cuems-common` | Avahi templates and their filenames · the live-file migration tool · conversion ordering · release-gate demonstration | **landed** 2026-09-17 (`1a00159`), **unmerged** — holds a merge gate with `cuems-nodeconf` |
| `cuems-nodeconf` | network-map object swap · relocated timing helper · Avahi vocabulary (its half) · packaging bounds | **all three stories landed** 2026-09-17 (`8ce7552`), **unmerged** — holds a merge gate with `cuems-common` |
| `cuems-frontend` | | not started |
| **`cuems-wsclient`** | | not started |
| *(`cuems-power-bridge`)* | **not in D32's six** — found carrying the retired vocabulary in shipped code; see [§5](#️-the-denominator-is-wrong-a-seventh-consumer-carries-the-retired-vocabulary) | **landed** 2026-09-24 as its own features `001-node-role-parser` (54/60) and `002-cluster-poweroff-cli` (69/69); tag **`399baf7`** (re-cut 2026-09-29 from `13a9af4` for T076's upper bound). *(Said "unscheduled" until 2026-09-29 — scheduled as US11 on 2026-09-17 and landed on 2026-09-24, so this cell lagged the repository twice.)* |

**`cuems-wsclient` is listed deliberately** (FR-UX-002). It was absent from 007's guide, 008's
guide and the cross-repo plan's repository list, and that absence is why a silently broken shutdown
path survived two features. The next sweep must reach it by construction, not by memory.

## 4. Behaviour that changes for everyone

### A dangling `target` is now cleared and reported, everywhere

`cuems-editor` has corrected dangling `target` references for some time, as a raw-dict walk before
parsing. That correction is now the library's (`target_resolves`, FR-043a): a `target` naming a cue
absent from the same document is **repairable**, cleared to `None`, and named in the `LoadReport`.

**This widens behaviour to every consumer** (FR-043d). A document with a dangling `target` now
loads with it cleared wherever it is loaded — previously only documents passing through the editor
were corrected, and the engine could dispatch against a reference to a cue that does not exist.

The editor's own implementation is **deleted, not ported**: two implementations of one repair is
how they drift.

*(FR-049c and the `action_target` half are recorded here as they land.)*

## 4c. `cuems-engine` — the typed node map *(wave 1, landed 2026-09-30)*

*(T022, T034, FR-031–FR-034. Landed in `cuems-engine` on `feat/xml-refactor` as its feature
`specs/008-cuems-utils-migration`, 64/64, verified at **`1662a99`**. Four of its findings came back
upstream as requirements this library then met — see the end of this section.)*

### Role: a string comparison becomes an enum selection (FR-031)

Feature 007 retyped `network_map.xsd`'s `<node_type>` (free text, `NodeType.master`) to
`<node_role>` (`cms:NodeRoleType`, `controller`/`node`/`firstrun`), and `network_map` is the one
configuration schema whose decode runs the adapter table — so the value arrives as a `NodeRole`
enum member, not a string.

```python
# before — cuemsengine/core/BaseEngine.py
CONTROLLER_NETWORK_FLAG = "NodeType.master"
...
    if node.get("node_type") == CONTROLLER_NETWORK_FLAG:

# after
    controllers = index.controllers          # NodeIndex.controllers, == by_role(NodeRole.controller)
    if not controllers:
        ...
    if len(controllers) > 1:                 # new: a multi-controller map is now named, not silently first-wins
        ...
    ip = controllers[0].get("ip")
```

**This is the archetype of "keeps resolving but becomes wrong"** (FR-004). `node.get("node_type")`
returns `None` against a typed map, `None == "NodeType.master"` is `False`, and the engine reports
*"No controller node found in network map"* on a map that names one. Nothing raises.

The constant `CONTROLLER_NETWORK_FLAG` is **deleted**, not re-spelled — the vocabulary now has one
home, `cuemsutils.tools.NodeList.NodeRole`, whose members are asserted against the XSD's own
enumeration facets rather than hand-copied.

### `online` and `adopted`: strings become booleans (FR-032)

The same opt-in decodes `cms:BoolType` to Python `bool` for `network_map` **and only for
`network_map`** — `settings`, `project_mappings` and `project_settings` still deliver the
`"True"`/`"False"` strings their recorded goldens carry. A consumer that reads both must not
assume one shape.

```python
# before
    if node.get("online") == "True"          # False against a typed map: every host filtered out
```

### The adoption partition: the caller was **deleted**, not ported (FR-033, FR-034)

`BaseEngine.find_hosts` called `self.cm.network_map.get_nodes_by_adoption(...)` — a method that no
longer exists on the object `ConfigManager.network_map` now returns, so the site failed loudly
(`AttributeError`) rather than quietly. The engine's clarification Q2 **deleted the method and its
only caller** instead of migrating them: adopted-node selection is now
`ControllerEngine._adopted_node_uuids`, built from the map it already holds.

`cuems-engine`'s `tests/test_public_surface.py` guards the deletion by name —
`get_nodes_by_adoption`, `partition_by_adoption` and `find_hosts` are all asserted absent from its
own source, so none can come back by re-spelling.

> **One obligation this closes by removal rather than by delivery.** FR-033 anticipated the engine
> moving to a *public, non-mutating* adoption partition. There is none:
> `NetworkMap.partition_by_adoption` lives on `cuemsutils.xml.settings`, and `cuemsutils.xml` is
> internal (Q14). The engine reported that as
> `upstream-reports/UR-1-no-public-adoption-partition.md` and then removed its own need for it.
> **The gap in this library's public surface is real and still open** — any future consumer asking
> "which nodes are adopted" has no public call to make. Carried as an open item, not as a closed
> obligation; see [§5b](#5b-open-upstream-findings-from-consumers).

### The count (T034, SC-007)

**Four callers found, four discriminating tests added — equal.**

| # | Site (`BaseEngine.py`, pre-migration lines) | Fault class | Failing-first evidence |
|---|---|---|---|
| 1 | `:33` `CONTROLLER_NETWORK_FLAG` + `:410` the comparison | keeps resolving, becomes wrong | `evidence/failing-first-site1-2-controller-lookup.txt` — 7 cases red with *"No controller node found"* |
| 2 | `:410` controller lookup (same test file, positive cases) | keeps resolving, becomes wrong | same |
| 3 | `:440` `find_hosts`' `get_nodes_by_adoption` call | **raises** (`AttributeError`) | `evidence/failing-first-site3-4-find-hosts.txt` |
| 4 | `:443` `online == "True"` inside the same comprehension | keeps resolving, becomes wrong — *not reached* in the run above, read from the code and recorded as such | same file, prediction **F1** |

**Denominator, stated because SC-007 requires it**: every call site named in 007's and 008's
migration guides, plus `cuems-engine`'s own ecosystem-wide scan — 74 raw hits over
`sorted`/`min`/`max`, `[:36]`/`[:8]`/`[-12:]`, `.split("-")`, `.join`, `isinstance(…, str)`,
`json.dumps` and raw ids passed as OSC/NNG arguments, recorded site by site in
`evidence/identity-audit.md`, run 2026-09-29 and re-run after the coercion delegation on
2026-09-30. Four of the 74 were the four above; the rest are either not ids or pass through the
`as_id`/`id_str` pair.

**Site 4 is counted and recorded as read rather than observed**, and that is the honest entry:
site 3 raises first in the same comprehension, so no test run can show site 4 failing while site 3
is still there. The engine's evidence file says so in its own header rather than implying four
observed reds.

## 4d. `cuems-editor` — the wire boundary *(wave 2, landed 2026-10-02)*

*(T020, T021, T026, T027, T027a, T027b, FR-040–FR-048. Landed in `cuems-editor` on
`feat/xml-refactor` as its feature `specs/001-cuems-utils-migration`, **62 of 63 tasks**, verified
at **`bf57d95`**: suite **154 passed / 2 skipped / 1 xfailed** against this library at `6213b16`.
The one open task is T059's second half and it is **blocked on this library** — see
[§5b](#5b-open-upstream-findings-from-consumers).)*

### The import that made the process start (FR-040, T020)

Feature 008 retired `cuemsutils.create_script`. The editor still imported it, so its websocket
server did not import at all — not a migration fault but a dead process, unnoticed because nothing
in the ecosystem ran it against a current library:

```python
# before — src/cuemseditor/CuemsWsServer.py:27
from cuemsutils.create_script import create_script, new_uuid
...
self.initital_template = create_script()        # :87

# after — CuemsWsServer.py:31, and db.py / CuemsDBMedia.py / CuemsDBProject.py already did this
from cuemsutils.helpers import new_uuid
```

The two halves of that one import move apart, which is why FR-040 names them separately:

| Was | Is | Why not a synonym |
|---|---|---|
| `new_uuid` from the deleted module | `cuemsutils.helpers.new_uuid` | four other editor files already imported it from there; the deleted module was re-exporting it |
| `create_script()` | `ConfigManager.generate_example(SchemaName.SCRIPT)`, served as `initial_template` (T014/T016), then **retired** at payload version 1 (T060) in favour of `schema_descriptor("script")`'s per-type `instance` | D25: the descriptor-generated example replaces the hand-maintained template, so the replacement is not a template module but a *generator plus a descriptor*. A client now builds a new script from the descriptor instead of being handed one |

The replacement's delta list against the `v0.1.0rc14` `create_script()` baseline is the editor's
`tests/ws-command-responses.txt`; the retired comparison test is recorded in that repository's
`evidence/test-retirements.md`.

### Five show-parsing sites, and what each became (FR-041, FR-042, T026)

| # | Site (pre-migration) | Became |
|---|---|---|
| 1–2 | `CuemsDBProject.py:883`, `:895` — `XmlReaderWriter` write / read of a project script | `CuemsScript.save` / `CuemsScript.load_with_report` |
| 3 | `CuemsDBProject.py` — `CuemsParser` on the inbound client document | `CuemsScript.from_json` |
| 4 | `CuemsDBProject.py` — the dangling-reference walk over `CUE_TYPES` | **deleted**, not ported (§4, `target_resolves`) |
| 5 | `repair_durations.py:204`, `:231` — `XmlReaderWriter(...).read()` then `.write_from_object(obj)` | `CuemsScript.load_with_report` for the read; **the write is gone** (below) |

The wire projection appears **once**, at the UI edge: `CuemsDBProject.load` returns
`script.to_wire()` and `send_project` puts it in the frame without walking it (FR-013b).

### The payload: **four** sanctioned deltas, not two (FR-010, FR-011, T027)

This guide and 010's FR-010/FR-011/SC-004 said *two*. Two was right when they were written and is
wrong now; features 008 and 013 each added one, and the fourth was ruled rather than introduced.
The list consumers must hold is the editor's
`specs/001-cuems-utils-migration/contracts/project-payload.md`:

| Id | Delta | Introduced by |
|---|---|---|
| (a) | `schemaLocation` is absent | 006 (`to_wire`'s direct projection) |
| (b) | each `Media.duration` is `{"CTimecode": "HH:MM:SS.mmm"}`, not a bare string | 008 ITEM A |
| (c) | a hardware cue's key is `Cue` with `class` inside; its output's is `CueOutput` likewise. `ActionCue`, `FadeCue` and `CueList` keep their own keys | **013 axis D** |
| (d) | a video cue whose document carries no `<opacity>` arrives with `"opacity": 100`, before `class` | ruled 2026-10-02 — reported as that repository's UR-3 and **withdrawn**: `opacity` is a `script.xsd` field of `VideoCue`, so a document that omits it carries the default and projecting it is the library doing its work |

Everything else holds and is still verified, not assumed: every other key, key order aside from the
absent and renamed keys, the **string** boolean form (`"True"`/`"False"`), and `doc_version` absent
from the wire. Re-measured in this repository 2026-10-02 against two goldens — see
[baseline.md](baseline.md) §"The editor's landing, measured here".

**Delta (d) is the one worth reading twice.** It is not a cue-key change, it is the general rule
that `to_wire()` projects a **model default** for an optional element the document did not carry.
Any consumer diffing a payload against the file it came from will meet it on some other field one
day; it is a property of the projection, not of `opacity`.

### `repair_durations.py` is no longer a document rewriter (FR-044, FR-045, T028)

FR-044 asked for the tool's rewriting pass to be **folded into** `cuems-convert-documents`. The
editor instead **retired it** (its own Q5), and that is the better answer: the tool now rewrites
`media.duration` in `project-manager.db` — the source of truth — and *lists* the projects whose
scripts disagree as `NEEDS_SAVE`. A script file changes only when an operator opens the project and
saves it. Every `script.xml` checksum is asserted unchanged after `--apply`.

Two consequences:

1. **FR-045's premise moved.** The tool no longer "reads the corrupt documents it exists to
   repair" in order to repair them — the corruption is in the DB, and the documents are read only
   to report. A document the strict path refuses is `SKIPPED_INVALID` with the library's own reason
   and the run continues. A pre-013 script is that case, naming `cuems-reshape-devices`.
2. **"Exactly one document rewriter in the ecosystem" is no longer the right count.** This library
   ships **two** standalone rewriters by deliberate decision — `cuems-convert-documents` (version
   steps) and `cuems-reshape-devices` (013's device shape, which has *no* version step), with a
   required order: reshape, then convert. Add `cuems-init-node` (011) and `--remint` (012) and the
   library writes documents from four entry points. What FR-045 actually protects is that **no
   consumer** is one of them, and that is what holds: the editor's save path is the only writer of
   a script outside this library.

### The two edge cases 013 created, as the editor resolved them

- **A half-migrated library** is an operator error fixed by running `cuems-reshape-devices` over
  the whole library, not by normalising shapes in the editor. The editor serves what the library
  returned; a local rewrite putting `AudioCue` back would be exactly the wire-dict manipulation
  FR-013b forbids.
- **The keyed-site fix 013's own guide prescribed was not taken, and should not be.**
  [§4 of 013's guide](../013-device-class-reshape/migration-guide.md) offers
  `if 'Cue' in item: cue_data = item['Cue']`. That walks the wire dict to reach an object-level
  result. The editor's walker matches on cue identity instead —
  `isinstance(cue, (AudioCue, VideoCue, DmxCue, MediaCue))` — and the bare `MediaCue` is in the
  tuple on purpose: an unknown class is the point of 013, and a duration correction that knows
  three names becomes wrong the day a fourth appears. 013's guide is corrected in place.

## 4a. `cuems-nodeconf` — the network-map swap *(wave 3, landed 2026-09-17)*

*(T029, FR-064–FR-068. Landed in `cuems-nodeconf` on `feat/xml-refactor` as its feature
`specs/001-network-map-object-adoption` US1, verified at **`8ce7552`** — by which point that
repository's US2 (the Avahi cutover, §4b) and US3 (packaging) had landed too. Line numbers below
are `8ce7552`'s.)*

### The nine ad hoc methods (FR-064)

`CuemsNodeConf.py` was 756 lines at the flow's measured start (`7abc01f`); it is 723 now. Row 5's
nine methods did **not** all disappear — five were deleted outright and four survive as thin
delegating wrappers that exist only to shape the daemon's own RPC answer. Stating it as "nine
deleted" would be wrong, and the distinction is the point: what moved is the *logic*, not the
*seam*.

| Was (`7abc01f`) | Now (`aab9b48`) | Library entry point |
|---|---|---|
| `merge_discovered_nodes` :440 | **deleted** | `CuemsNetworkMapType.refresh(discovered, path)` |
| `set_master_always_adopted` :490 | **deleted** | `NodeIndex.set_controller_always_adopted` (via `refresh`) |
| `check_missing_adopted_nodes` :501 | **deleted** | `NodeIndex.missing_adopted` (via `refresh`) |
| `_map_signature` :281 | **deleted** | `NodeIndex.signature` |
| `write_network_map` :413 | **deleted** | `CuemsNetworkMapType.save(path)` |
| `refresh_network_map` :229 | **retained, delegating** (:250) | its four-step body is one `document.refresh(...)` call |
| `adopt_node` :516 | **retained, delegating** (:476) | `NodeIndex.adopt` |
| `unadopt_node` :537 | **retained, delegating** (:499) | `NodeIndex.unadopt` |
| `read_network_map` :562 | **retained, delegating** (:521) | `ConfigManager(...).load_network_map()` + `.network_map` |

### The RPC answer had to be reconstructed (FR-066)

`NodeIndex.adopt`/`.unadopt` return a **bare bool** and do not persist. The daemon's
`engine_callback` contract with the Angular UI is `{'OK': bool, 'error'?: str}`, so the wrappers
rebuild the three error strings 008's guide (T052) named. The reconstruction is not a re-coding of
the adoption rule:

```python
# after — cuemsnodeconf/CuemsNodeConf.py:476
before = self.network_map.signature()
if not self.network_map.adopt(node_uuid):
    # a False is two-way ambiguous — absent or offline — told apart by a lookup,
    # never by re-deciding adoptability here
    if self._find_node(node_uuid) is None:
        return {'OK': False, 'error': f'Node {node_uuid} not found'}
    return {'OK': False, 'error': f'Cannot adopt node {node_uuid}: node is offline'}
if self.network_map.signature() == before:
    return {'OK': True, 'message': 'Node already adopted'}   # detected by signature, not by rule
self._save_network_map()
return {'OK': True}
```

"Already adopted" is detected by **the signature not moving**. That matters: the alternative — an
`if node['adopted']` check in the daemon — would be a second copy of the adoption rule, which is
what D22 exists to prevent.

### The relocated timing helper (FR-067)

| Before | After |
|---|---|
| `from cuemsutils.timeoutloop import Timeoutloop` (`CuemsNodeConf.py:26`) | `from cuemsutils.tools.TimeoutLoop import TimeoutLoop` (`:25`) |

Three call sites follow the class's new spelling (`:350`, `:584`, `:596`). This was the **only**
deprecated-path import `cuems-nodeconf` carried; the repository's census entry is now zero (see
[import-census.md](import-census.md)).

### The two internal imports (FR-025, FR-068)

| Before | After |
|---|---|
| `from cuemsutils.xml.mapper import Mapper, read_config_document` (`:22`) | **gone** — the import was its only occurrence, as measured |
| `from cuemsutils.xml.settings import NetworkMap as _NetworkMapReader` (`:23`) | `ConfigManager(config_dir=…, load_all=False).load_network_map()` then `.network_map` (`:521`) |
| `cleanup()` reading the never-assigned `self.cm` (`:579-581`) | **method deleted** — nothing called it (`8926f49`) |

`read_network_map` also acquired a case 008 did not anticipate: `load_network_map` ends by
resolving *this node's own* entry and raises `ValueError` when the map does not list it yet, which
is every freshly provisioned node. The daemon is what writes a node into the map, so it must be
able to read a map that omits it — it catches that `ValueError` and distinguishes it from a broken
document by checking `hasattr(manager, 'network_map')`, since a malformed document raises
`SchemaError` (not a `ValueError`).

### ⚠️ One finding the gate caught: a *third* internal import

The swap removed two `cuemsutils.xml` internal imports and introduced one `cuemsutils.config` one:

```
cuemsnodeconf/CuemsNodeConf.py:21  from cuemsutils.config.network_map import CuemsNetworkMapType
```

plus six of its test files and the vendored yardstick. `cuemsutils.config.__all__` is `[]`, and
`cuemsutils/tools/NodeList.py`'s own docstring is explicit about it: *"a consumer imports `node`
from here, never from `cuemsutils.config.network_map`"*. Feature 007 re-exported `node` for exactly
this reason but not `CuemsNetworkMapType`, because at the time no consumer needed to **construct** a
document — only to read one. The daemon now does, in `_network_map_document()`:

```python
return CuemsNetworkMapType(node_list=[{"node": n} for n in self.network_map.values()])
```

That framing was **wrong, and is kept here because being wrong twice in the same way is the
finding**. "There is no public name for that class" was inferred from `load_network_map`'s
`get_dict()` spelling rather than measured; `ConfigManager.network_map` already returned a live
`CuemsNetworkMapType`. It was not a gap in wave 0's surface, and it was not a consumer mistake
either — it was a mis-spelled accessor that misled the consumer *and* the gate reading it (T083
corrected the spelling; see the measured answer below).

**It is invisible to the import census by construction** — the census counts *deprecated* paths, not
*internal* ones — which is the second thing worth recording: a zero census is not the same claim as
"reaches the library through public paths only".

**Answered 2026-09-17 by measurement, and the answer is: `cuems-nodeconf` can close this alone,
with no library change.** The earlier framing here — that closing it required widening this
library's public surface — was wrong, and wrong in a way worth recording, because it was inferred
from a docstring rather than measured.

**`ConfigManager.network_map` already returns a live `CuemsNetworkMapType`**, `.save` and
`.refresh` included. `load_network_map` assigns `netmap.get_dict()`, which reads as "a dict" and is
why this was missed; but `get_dict()` returns the value under the document's `main_key`, and for
`network_map` that value *is* the bound object:

```
ConfigManager.network_map -> cuemsutils.config.network_map.CuemsNetworkMapType
  is CuemsNetworkMapType : True     has .save : True     has .refresh : True
```

So the daemon never needs to name the class. It needs to stop **constructing** a document and start
**refilling** the one it already holds — which preserves its own "the index is the single in-memory
source of truth" design exactly, since `node_list` is overwritten wholesale either way:

```python
# before — names an internal symbol
from cuemsutils.config.network_map import CuemsNetworkMapType
def _network_map_document(self):
    return CuemsNetworkMapType(node_list=[{"node": n} for n in self.network_map.values()])

# after — no import; the document comes from the public façade and is refilled
def _network_map_document(self):
    self._document["node_list"] = [{"node": n} for n in self.network_map.values()]
    return self._document          # retained from ConfigManager.load_network_map()
```

Verified end to end against `0.1.0rc16`, importing **only** `cuemsutils.tools.*`: load through
`ConfigManager`, refill `node_list`, then `document.save(path)`, `document.refresh(discovered, path)`
and `ConfigManager.save_network_map(path)` — all three succeed.

**One path is not covered, and it is unreachable in deployment.** On a first run with *no* map file,
`load_network_map` raises `FileNotFoundError` and `ConfigManager.network_map` is the bare `{}` that
`__init__` set — no `.save`. Nothing public constructs an empty network-map document; the
descriptor's constructible instance (T011) is a plain `dict`, deliberately, so it does not serve
here either. But `cuems-common` **ships** `/etc/cuems/network_map.xml` with an empty `<node_list/>`
as a conffile (`debian/install:204`), and `cuems-nodeconf` `Depends: cuems-common (>= 1.0.0)`. On
any packaged host the file exists, so `is_first_run` is false and the branch is dead. It is
reachable only on a dev checkout or a host where the file was deleted by hand.

**Decided (T084): this library adds no public alias.** FR-025's own instruction is *name the
existing equivalent rather than adding a synonym*, and the equivalent exists — so a new
`cuemsutils.tools` re-export of `CuemsNetworkMapType` would be the synonym FR-025 forbids, not the
fix. The migration belongs in `cuems-nodeconf`; the prompt for it is
[`specs/planning/xml-rebuild/010-consumer-prompts/04a-cuems-nodeconf-public-path.md`](../planning/xml-rebuild/010-consumer-prompts/04a-cuems-nodeconf-public-path.md).

**What this repository owed instead has landed (T083)**, because the misreading was the library's
fault and not the consumer's:

| Site | Was | Now |
|---|---|---|
| `ConfigManager.load_network_map` | `self.network_map = netmap.get_dict()`, unexplained | the same line, with what `get_dict()` actually returns stated at the assignment |
| `ConfigManager.network_map` setter | annotated `value: dict[str, Any]`, contradicting its own getter three lines above | `CuemsNetworkMapType \| dict[str, Any]` — `dict` kept only because `__init__` seeds `{}` before any load |

Neither changes behaviour. Both exist so the next reader reaches the correct conclusion without
measuring, which is what neither of the first two could do.

**One thing stays out of scope permanently.** `cuems-nodeconf`'s vendored yardstick
(`specs/planning/yardstick/test_nodeindex_characterization.py`) imports
`cuemsutils.config.network_map` too, and **must not be changed**: it is byte-identical to
`tests/contract/test_nodeindex_characterization.py` by design, and that identity is what feature
001's equivalence claim rests on. It is an enumerated exemption with that reason, not a site to
fix.

#### Closed by the consumer, 2026-09-21

`cuems-nodeconf`'s feature `002-public-network-map-path` landed it (18/18 tasks, merge candidate
`6c0cca7`). Verified here rather than taken on report:

| | |
|---|---|
| Internal imports in **shipped** code (`cuemsnodeconf/`) | **zero** |
| Its suite against this working tree | **129 passed** (was 110) |
| Vendored yardstick | still **byte-identical** |

It took the shape [flow 04a](../planning/xml-rebuild/010-consumer-prompts/04a-cuems-nodeconf-public-path.md)
described: `self._document = manager.network_map` retains what `load_network_map()` already
returned, and `_network_map_document()` refills its `node_list` instead of constructing a document.
Both of the prompt's open decisions were taken and stated rather than left implicit:

- **The first-run branch** took option A — `_seed_empty_map()` writes a minimal empty map with
  stdlib, then loads it back through the public path. So there is no construction anywhere, not even
  on the branch that is dead in deployment.
- **The test imports were kept**, labelled `# test-only (FR-007)` at each site — the answer this
  guide asked for, given explicitly rather than by silence. They then went further than the prompt
  asked and added `tests/test_public_surface.py`, which fails any *shipped* module that imports
  `cuemsutils.config` or `cuemsutils.xml`, with a guard test so a package rename cannot turn it
  silently green.

**What this demonstrates is worth more than the import.** The defect was a library accessor whose
name said "dict" while returning an object; it cost two independent readers the same wrong
conclusion, and the wrong conclusion was "the library must grow a new public symbol". The fix was to
correct the spelling (T083) and let the consumer use what already existed. A synonym added on the
first reading would have shipped, and would now be permanent.

### An 008 open item closed from the consumer side

008 recorded `NodeIndex.set_controller_always_adopted` as carrying no first-run parameter, with the
daemon's `self.is_first_run` branch **"not ported … left for 009 to reconcile"**. There is nothing
to reconcile: `cuems-nodeconf` **deleted** that branch (`91047f4`, 2026-09-07) rather than asking
for it back, on the finding that it had no reachable correct effect and one reachable harmful one —
`is_first_run` is computed once and never reset, but the daemon became resident in the Phase-1
re-enable, so on a first-boot controller an operator's adoption was silently cleared by the next
30-second worker tick, after the UI had already been told it succeeded. The library's omission was
correct.

**Two docstrings in this library now describe that retired behaviour** and should be corrected (a
documentation fix, not a behaviour change — the yardstick tests behaviour and is unaffected):

- `src/cuemsutils/tools/NodeList.py` — `set_controller_always_adopted`'s summary still reads
  *"…on a first run, nothing else is"*, which the method body does not do.
- `src/cuemsutils/config/network_map.py` — `refresh`'s **"Not ported"** paragraph still describes
  the first-run branch as an open item awaiting reconciliation.

`cuems-nodeconf` raised these as *report, do not patch* (its own T049), since the yardstick's
guarantee depends on that file not being edited from the consumer side. Patching from **this** side
is the correct route.

**Closed 2026-09-17** (T082): both docstrings were rewritten in `9e5e79f`, and `cuems-nodeconf` recorded the resolution on its own report. The yardstick is unaffected and was re-diffed to confirm.

## 4a-ii. The shipped map lists no nodes — and `get_node` used to raise `TypeError` *(T085–T088, landed 2026-09-21)*

*(Second upstream report from `cuems-nodeconf`'s feature `002-public-network-map-path`; the first —
`save_document`'s `0600` and two docstrings — was closed by `6fe2d3f` / `9e5e79f`. Full record:
[`empty-node-list-report.md`](empty-node-list-report.md), checklist
[`empty-node-list-tasks.md`](empty-node-list-tasks.md).)*

`NetworkMap.get_node` iterated `network_dict.get('node_list')` unguarded, so a map listing no nodes
raised **`TypeError: 'NoneType' object is not iterable`** instead of the `ValueError` that
`ConfigManager.node_network_map` documents. It now raises `ValueError`, message unchanged
(`Node with uuid <uuid> not found`), for all three shapes: an empty `<node_list/>`, no `node_list`
element at all, and a `None` value.

**The failing case was the default case.** `cuems-common` has shipped `/etc/cuems/network_map.xml`
with an empty `<node_list/>` since its `f78c876` (feature 001, T040), which removed a placeholder
controller that misrouted chrony and the log collector — correctly. So every fresh install, and
every upgrade where the operator takes the maintainer's conffile, read a map that made
`load_network_map()` throw an uncatchable-by-contract exception. `cuems-nodeconf` caught
`ValueError` only (deliberately narrowly, so `SchemaError` still fails loudly), so it failed
start-up, and with `Restart=on-failure`/`RestartSec=10` it retried every ten seconds forever —
unbreakable, because **only `cuems-nodeconf` writes a node into the map** and it never got that
far. `cuems-engine`'s `load_config()` calls the same method and was exposed identically.

**The trap, recorded because the obvious repair is wrong**: `.get('node_list', [])` does *not* fix
this. `node_list` is `minOccurs="0"`, and an empty `<node_list/>` decodes to a key that is
**present with value `None`**, so the default never fires. The neighbouring code at
`settings.py:187`/`:236` was safe by its `if not node_list:` check, not by its default. The fix is
`or []`, matching `config/network_map.py:181`'s existing guard.

**Why three test suites missed it** — the reusable lesson, and the reason this subsection exists
rather than just a changelog line:

| Repository | Why it did not catch this |
|---|---|
| `cuems-common` | T040 validated the empty map against the **XSD** only; it never loaded it through `ConfigManager` |
| `cuems-utils` | no test loaded an empty `node_list` through `ConfigManager` or `get_node` |
| `cuems-nodeconf` | every fixture map in `tests/fixtures/` contains nodes |

Each suite was internally consistent and collectively blind: schema-validity was checked where the
document was authored, and loading was checked only against documents that happened to be
populated. `tests/contract/test_empty_node_list.py` closes it here, and pins the fresh-node boot
sequence (load → refill → `save` → re-read) so the shipped shape stays exercised end to end.

**No pins move.** The fix ships inside `0.1.0rc16` — `__version__` unchanged, no re-cut of
`xml-refactor-merge-candidate`, consumers' `>= 0.1.0rc16, << 0.1.1~` untouched, and
`cuems-nodeconf`'s `except ValueError` needs no change. The caveat that follows from that: within
rc16 the version string cannot distinguish a build made before this fix from one made after, so
**rebuild or reinstall `cuemsutils` from the fixed commit** in every development venv and packaging
run, with `test_empty_node_list.py` as the discriminator.

**One adjacent finding, measured and deliberately left alone (T087).** Re-measuring every
`node_list` consumer against both shapes confirmed the four the report names are safe — `get_node`
now raises `ValueError`, `get_nodes_by_adoption` and `partition_by_adoption` raise their own
`ValueError`, and `refresh`/`save` complete on an empty document. But a document whose **root is
entirely empty** (`<CuemsNetworkMap/>`, no `node_list` element) decodes to `None`, so `get_dict()`
returns a plain `{}` and `refresh`/`save` raise `AttributeError` on it. That is a decode-layer
behaviour predating this fix, it affects the whole document rather than `node_list`, and **it is
not a shape anything ships** — `cuems-common` ships `<node_list/>`. `get_node` answers it correctly
either way. Recorded here rather than fixed, because widening it would touch the decode path for
all six schemas, which this report does not license.

## 4b. The discovery vocabulary cutover *(wave 1, both halves landed 2026-09-17)*

*(T024, FR-060–FR-063. **Two repositories, one cutover** — D33. It cannot be half-renamed: a
listener reading `node_role` against a publisher writing `node_type` discovers nothing, and the
failure is silent — no error, no exception, nodes simply never appear.)*

| | |
|---|---|
| `cuems-common` | `feat/xml-refactor` @ `1a00159`, feature `specs/001-node-role-and-conversion-ordering`, 46/48 tasks |
| `cuems-nodeconf` | `feat/xml-refactor` @ `8ce7552`, feature `specs/001-network-map-object-adoption` US2/US3 |

Both halves are **implemented and unmerged**, each holding a merge gate on the other
(`cuems-common` T019, `cuems-nodeconf` T042). Neither merges alone; that is the design, not a delay.

### The key and the values

| | Before | After |
|---|---|---|
| TXT key | `node_type` | **`node_role`** |
| Controller | `master` | **`controller`** |
| Non-controller | `slave` | **`node`** |
| Unassigned | `firstrun` | `firstrun` *(unchanged)* |

### The two template filenames (FR-061)

The retired words were in the **filenames**, not only the file contents, so the rename is a
`git mv` plus every site that resolves a template by name:

| Before | After |
|---|---|
| `usr/share/cuems/cuems.service.master` | **`usr/share/cuems/cuems.service.controller`** |
| `usr/share/cuems/cuems.service.slave` | **`usr/share/cuems/cuems.service.node`** |
| `usr/share/cuems/cuems.service.firstrun` | unchanged in name; its TXT record changed |

`cuems-nodeconf` shipped **unshipped duplicates** of all three at its repository root
(`cuems.service.{firstrun,master,slave}`). They are deleted rather than renamed — `cuems-common`
installs the real ones, and a second copy of a file that must not disagree is a half-rename waiting
to happen.

### Everything that resolves a template by name (FR-061)

| Repository | Site | Change |
|---|---|---|
| `cuems-common` | `usr/bin/cuems-config-node:64` | `service_files = ['cuems.service.firstrun', 'cuems.service.controller', 'cuems.service.node']` |
| `cuems-common` | `etc/sudoers.d/99-cuems-avahi:12-14` | one `NOPASSWD` `cp` rule per template, all three renamed |
| `cuems-nodeconf` | `CuemsNodeConf.py:404` | `… + '.controller'` (was `'.master'`) |
| `cuems-nodeconf` | `CuemsNodeConf.py:442` | `… + '.node'` (was `'.slave'`) |

**The sudoers rules moved file, not just text.** `cuems-common` retired `/etc/sudoers.d/99-cuems`
in favour of a new `99-cuems-avahi`, because a renamed rule inside an *edited* `99-cuems` would
never have reached that host — dpkg leaves a modified conffile alone, so the operator would keep
the old rules naming files that no longer exist, and the role flip would fail with a sudo denial.

### The publisher and the consumer (FR-061)

| Repository | Site | Change |
|---|---|---|
| `cuems-nodeconf` | `CuemsSettings.py:27` | publishes `{'node_role': 'node'}` |
| `cuems-nodeconf` | `CuemsAvahiListener.py:91-102`, `:144-155` | both handling blocks read `b'node_role'` and resolve through `NodeRole(raw_role)` directly |
| `cuems-nodeconf` | `AvahiTool.py:81`, `:93`, `:97` | read `properties[b"node_role"]` **by name** |
| `cuems-nodeconf` | `CuemsAvahiListener.py`, `AvahiTool.py` | `_AVAHI_NODE_TYPE_TO_ROLE` — **both copies deleted** |

`AvahiTool`'s three sites previously read `properties[list(properties.keys())[0]]` — whichever TXT
key happened to come first. A key that is never read by name cannot be renamed correctly, so
reading by name was part of the rename rather than beyond it.

The old-key translation table retired with the key, in both of its copies. The unrecognised-value
log survives it: it names the offending value and the accepted set
(`sorted(r.value for r in NodeRole)`), so a stray value is diagnosable rather than silently
dropped.

### The live file no package owns (FR-061)

`/etc/avahi/services/cuems.service` is created by **copying a template**, so no package ships it
and no package upgrade can rewrite it. `cuems-common` adds
**`usr/bin/cuems-migrate-avahi-service`** for it: it rewrites only
`<txt-record>node_type=VALUE</txt-record>` records, leaves every other byte alone, writes a
byte-exact `cuems.service.<timestamp>.bak` beside it first (never `*.service`, so avahi does not
load the backup as a second service group), reloads `avahi-daemon` only if the file actually
changed, and **refuses a file it cannot map whole**, naming why. `postinst` runs it; on hosts
deployed by file copy it is run by hand.

### The packaging entries that place them (FR-061)

| Package | Relation | Refuses |
|---|---|---|
| `cuems-nodeconf` 0.1.0-8 | `Breaks: cuems-common (<< 1.3.0-23~)` | a renamed daemon beside un-renamed templates |
| `cuems-common` 1.3.0-23 | `Breaks: cuems-nodeconf (<< 0.1.0-8)` | renamed templates beside an un-renamed daemon |

Both directions are guarded, which is what "no half-renamed state ships" (FR-060) requires
mechanically rather than by review. The arithmetic is verified in
[baseline.md](baseline.md)'s T025 section; the `~` in `1.3.0-23~` is deliberate, so that
`1.3.0-23~anything` (a prerelease or demo build) still satisfies the guard.

### FR-063 — 007's exclusion is not an exemption

Feature 007 excluded these four discovery files from its own count and handed them here. They are
**in scope and fixed**, not exempt; see the labelling in [§5](#5-the-ecosystem-wide-count).

## 5. The ecosystem-wide count

*(FR-070–FR-073a, FR-UX-003. The count itself is T062's and is **not run yet**. What is settled
here is the labelling T023a owes, and one correction to the count's denominator that the wave-1
gate turned up.)*

The count carries the counting **method** alongside the number (FR-070b), and the exempt set
enumerated as `<path>:<start_line>[-<end_line>]` (FR-071/FR-072) with its two distinct reasons —
"exists to detect or convert the retired spelling" (**permanent**) and "not shipped" (**removable
at any time**) — never merged. Merging them is how a working migration diagnostic gets deleted by
the next person to run the count.

### The two groups of four — they are not the same four *(T023a, FR-070a)*

The spec names two different groups of four, and each is labelled wherever it appears so a reader
cannot substitute one for the other. Conflating them either counts files that are exempt or exempts
files that must be fixed.

**Group 1 — the "discovery four" (FR-070): in scope, counted, and now FIXED.**
`cuems-common`'s Avahi files, which feature 007 excluded from its own count and handed here:

| File | Disposition, measured 2026-09-17 at `cuems-common` `1a00159` |
|---|---|
| `etc/avahi/services/cuems.service` | **fixed** — carries `node_role`; the *live* per-host copy is migrated by `usr/bin/cuems-migrate-avahi-service` |
| `usr/share/cuems/cuems.service.firstrun` | **fixed** — `node_role=firstrun` |
| `usr/share/cuems/cuems.service.master` | **fixed by rename** → `cuems.service.controller`, `node_role=controller` |
| `usr/share/cuems/cuems.service.slave` | **fixed by rename** → `cuems.service.node`, `node_role=node` |

**Group 2 — the "non-shipped four" (FR-073): exempt, and exempt for the *removable* reason.**
Named individually rather than covered by a `dev/` wildcard:

| File | Repository |
|---|---|
| `dev/network_map.xml` | `cuems-engine` |
| `dev/test_xml_files/network_map.xml` | `cuems-engine` |
| `dev/CuemsEngine_old.py` | `cuems-engine` |
| `test_run_nodeconfig.py` | `cuems-nodeconf` — **note: migrated anyway** by that repository's T037, so it no longer carries the retired spelling even though it was entitled to |

Group 1 is `cuems-common`'s and is **done**. Group 2 is exempt and always was. Neither substitutes
for the other.

### ⚠️ The denominator is wrong: a **seventh** consumer carries the retired vocabulary

FR-070's scope is "the ecosystem", and D32 fixes that at **six** consumer repositories. Measured
2026-09-17, `/disk/Projects/StageLab/cuems-power-bridge` (branch `main` @ `c201405`) is a seventh,
and it is **shipped** — `rc1_packages/cuems-power-bridge_0.3.0-5_all.deb`:

```
src/cuemspowerbridge/network_map.py:33   node_type: str | None  # "NodeType.master" | "NodeType.slave"
src/cuemspowerbridge/network_map.py:94   node_type=_text(el, "node_type"),
src/cuemspowerbridge/network_map.py:110  if n.node_type != "NodeType.slave":
```

It parses `<node_type>` and filters on `"NodeType.slave"` — against maps that
`cuems-migrate-network-map` has already converted to `<node_role>controller|node</node_role>`. On
every converted host `slave_avahi_names()` therefore returns an **empty list**.

**This is a live failure, not a latent one.** `cuems-cluster-poweroff` selects nodes through this
parser, so an orderly cluster power-off reports success having powered off nothing — the nodes stay
up while mains is cut on the controller. `cuems-common`'s own `README.md:212` records it as a known
issue since 1.3.0-23, so it is already observed in the field; what is new here is that it is a
**count and scope** finding, not only a bug.

**This is `cuems-wsclient`'s failure mode repeating** (FR-UX-002): a repository absent from the
list produces work nobody schedules, and the defect survives the feature that was supposed to
catch it. The lesson FR-UX-002 draws — *the next sweep must reach it by construction, not by
memory* — is not satisfied by adding `cuems-power-bridge` to a list by hand either. T062's counting
method (FR-070b) must therefore enumerate its paths as **"every repository under
`/disk/Projects/StageLab/` that reads `network_map.xml`"**, discovered by the command, rather than
as a fixed list of six or seven checkouts.

**Now scheduled, as US11** (added to [tasks.md](tasks.md) 2026-09-17, T070–T079). The bridge's own
findings document
(`../cuems-power-bridge/specs/planning/cuems-power-bridge-node-role-findings.md` — relocated from
`dev/planning/` on 2026-09-18 and **committed** on 2026-09-21 at `d7fed47`, so no longer untracked)
opened it from `cuems-common`'s side; verifying it against the bridge's source turned up
three things that document could not see, and they widen the defect rather than narrow it:

1. **Three sites, not one.** `cuems-common`'s `usr/bin/cuems-cluster-poweroff:275` is the one the
   document names. The bridge's own parser carries two more — `network_map.py:110`
   (`slave_avahi_names`) and `:141` (`slave_ips`).
2. **Two independent features, not one.** `slave_ips()` is not on the poweroff path at all: it
   feeds the autoload / NNG-hub readiness gate. A converted map therefore breaks **show-playback
   readiness** as well as orderly power-off.
3. **The silent branch is measured, not assumed.** `parse()` reads the element through
   `_text(el, "node_type")`, which returns `None` instead of raising. Every node is skipped, the
   target list is empty, and the run reports success — the document's §2 first row, its worse one.

The suite does not catch any of this because the fixtures at
`tests/test_network_map_ips.py:13-19` are themselves written in the retired vocabulary: the tests
are green *because* they certify the defect. That is what US11's T073 exists to fix, and why a
passing suite is not evidence there.

**The root cause is not the vocabulary.** The bridge holds a fourth copy of the node-identity model
(`role_id → alias → hostname → uuid`), parsed with bare `ElementTree` against no schema — so a
vocabulary change cannot fail loudly there by construction. 007 FR-030a-i already says the node
model lives in `cuemsutils` only; this is what violating it costs.

## 5a. `cuems-power-bridge` — the fourth copy of the node model, deleted *(US1/US11, landed 2026-09-24)*

**T018/T071/T078/T079.** The sixth consumer, absent from 007's guide, 008's guide and the
cross-repo plan's repository list — which is why a silently broken shutdown path survived two
features (FR-UX-002). Recorded here under its **current** name; it was `cuems-wsclient` until the
2026-06 rename, and treating the two as separate repositories is the double-count this feature
closed.

### What it did, and why nothing said so

The bridge carried a **private network-map parser** — bare `ElementTree`, namespace-agnostic
local-name matching, **validated against no schema** — and filtered on a string:

```python
# src/cuemspowerbridge/network_map.py, before
node_type=_text(el, "node_type"),          # :94
if n.node_type != "NodeType.slave":        # :110  slave_avahi_names
if n.node_type != "NodeType.slave":        # :141  slave_ips
```

007 renamed that element to `<node_role>`, and `cuems-common`'s `postinst` converts every
installed map. `_text()` **returns `None` rather than raising** on an absent element, so
`None != "NodeType.slave"` is true for every node, every node is skipped, and the target list is
empty. Measured against a converted map: `slave_avahi_names -> ([], [])` and `slave_ips -> []`.
Note the second element — **the unresolvable list is empty too**, so not even the
`ERROR … has no role_id/alias/hostname` path fires. There is no log line anywhere saying anything
is wrong.

### The four corrections to the findings document (T071)

The 2026-09-15 findings document opened this from `cuems-common`'s side. It is right about the
defect and incomplete about its extent; all four were measured, not argued.

**(a) The defect has three sites, not one.** The document names only `cuems-common`'s
`usr/bin/cuems-cluster-poweroff:275`. Two more live in the bridge's own parser (`:110`, `:141`).
Fixing the tool alone — the document's option D — would have left both.

**(b) Two independent features are broken, not one.** `slave_ips()` is **not** on the poweroff
path; it feeds the boot auto-load / NNG-hub readiness gate. So a converted map silently broke
**show-playback readiness** as well as orderly power-off. The document's blast-radius section
misses it entirely.

**(c) §9's first two unknowns resolve to the worse branch.** The model was never migrated, so
there is no `AttributeError` to hope for — it is §2's *first* row, the silent one.

**(d) The public path adds three preconditions**, all consequences of deleting the parser rather
than migrating it: `/etc/cuems/settings.xml` must exist and be schema-valid (`ConfigManager`
loads base settings **unconditionally, even with `load_all=False`**); this host's own uuid must
have a map entry; and every node entry must be schema-valid, where the old `parse()` required only
`<uuid>`. Against that cost, an unconverted map now raises a **named, actionable** refusal instead
of selecting nothing.

### After: option C, the parser deleted rather than migrated

| | Before | After |
|---|---|---|
| Reader | private `ElementTree`, no schema | `ConfigManager.network_map`, schema-validated |
| Role test | `n.node_type != "NodeType.slave"` (string) | `v.role is NodeRole.node` (`NodeRole` enum, lazily imported from `cuemsutils.tools.NodeList`) |
| Self-exclusion | `own_uuid()` read `/etc/cuems/settings.xml`, **swallowed every exception and returned `None`** | `str(cm.node_uuid)` through `ConfigManager`; a failure raises, classified |
| Empty selection | indistinguishable from "nothing to do" | `TopologyError`, **never** converted into an empty answer |
| Unconverted map | silently selects nobody | `NETWORK_MAP_RETIRED_VOCABULARY`, naming `cuems-migrate-network-map` |
| Two selectors | `slave_avahi_names`, `slave_ips` | `shutdown_targets`, `readiness_peers` — separate, both adopted-only |

What survives is a **thin adapter** preserving both field-learned resolution policies verbatim:
avahi ignores `<ip>`; `readiness_peers` deliberately trusts it, because the NNG hub matches bus
peers by address.

### The two secondary findings, decided rather than inherited (T078)

**(i) `own_uuid()` reading a file no package ships — resolved by construction, not by patch.** It
read `/etc/cuems/settings.xml`, swallowed every exception and returned `None`, silently disabling
uuid-based self-exclusion on any host lacking it. A controller that cannot identify itself is a
controller that can put itself in its own shutdown target list. The public path removes the
question: `ConfigManager` supplies `node_uuid`, and an unreadable or invalid `settings.xml` raises
`SETTINGS_XML_MISSING` / `SETTINGS_XML_INVALID` rather than degrading. **The decision taken is that
the file is a hard precondition and its absence is loud** — the opposite of the previous
behaviour, and the reason (d) above counts it as a cost rather than a free win.

**(ii) The stale docstring at `cuems-cluster-poweroff:240`** — "matches the network_map
`NodeType.master` entry" — is the same family as the defect: prose asserting a vocabulary the
system no longer uses. Corrected in `cuems-common` as part of its `1.3.0-23` entry.

### The root cause, which outlives the defect (T079)

The bridge carried a **fourth copy of the node-identity model** — the same
`role_id → alias → hostname → uuid` resolution `cuemsutils` owns and `cuems-common`'s `cuems-logs`
performs. It validated against no schema, so a vocabulary change **could not fail loudly there by
construction**. 007's FR-030a-i — *the node model lives in `cuemsutils` only* — is the rule it
violated.

T072 deleted the copy, so the deferred intention is discharged. What remains worth recording is
**why a fourth copy existed at all**: the repository was absent from the consumer list for two
features under one name, and re-discovered under another, so nothing ever told it that `cuemsutils`
owned the model. The copy is gone; that cause is not, and it is the same cause FR-UX-002 names.

### The packaging edge (T077)

`cuems-common` ↔ `cuems-power-bridge` had no versioned relation: `Suggests:` carries no version, so
nothing refused a new tool beside an old bridge or the reverse. **Decision: `Suggests:` stays
unversioned, and the side that changed first acquires the `Breaks:`.** Both halves are in the tree:

| Side | Relation |
|---|---|
| `cuems-common` | `Suggests: cuems-power-bridge` (**unversioned, deliberately** — a host with no bridge at all stays supported, and `cuems-common` must not make a controller-only opt-in feature mandatory for every node) + `Breaks: cuems-power-bridge (<< 0.3.1-1)` |
| `cuems-power-bridge` | `Breaks: cuems-common (<< 1.3.0-23)` |

`cuems-common` changed first — its `cuems-cluster-poweroff` now selects through the bridge's
adapter, which older bridges do not have — so it carries the versioned edge, with the reasoning in
a comment beside it. The pair upgrades together or `dpkg` refuses, instead of the mismatch
surfacing as an `AttributeError` part-way through a poweroff transaction. This is FR-091's pattern
applied to an edge FR-091 did not enumerate.

## 5b. Open upstream findings from consumers

*(Recorded 2026-10-01. A consumer flow that measures a gap in this library reports it rather than
patching it — each repository's constitution forbids editing the library whose characterization
yardstick it vendors. `cuems-nodeconf`'s three and `cuems-common`'s one are in §4a/§4a-ii, closed.
These are `cuems-engine`'s, from `specs/008-cuems-utils-migration/upstream-reports/`.)*

| Report | Asks for | State |
|---|---|---|
| **UR-1** no public adoption partition | `partition_by_adoption` reachable without importing `cuemsutils.xml` | **CLOSED** 2026-10-01 by feature **013, FR-035**: the same function object is published as `cuemsutils.tools.NodeList.partition_by_adoption`, by a lazy module `__getattr__` (a module-level import of `xml.settings` from `NodeList` raises `ImportError`). `get_nodes_by_adoption` is untouched. `cuems-editor` is the first caller — `CuemsWsServer.py:28`, `:512` — and filed the same report from its own side |
| **UR-2** `versioning.py`'s comment contradicted its own table | the comment states the table, or points at it | **CLOSED** 2026-09-30, incidentally, by feature 012's version bumps — the docstring now says versions move *per schema* and lists which feature moved which |
| **UR-4** `Uuid` equals and hashes like `str` but cannot be ordered | a total ordering consistent with the string form | **CLOSED** by feature 012's FR-029. It also removes the stated reason for FR-035's `cuems-engine 0.1.0rc7` coupling — see `specs/012-uuid4-convergence/sibling-repository-updates.md` §4.1 |
| **UR-5** `XmlReaderWriter.validate`'s deprecation advice fits only scripts | per-schema advice, or a public validator for configuration documents | **CLOSED** 2026-10-01 by feature **013, FR-036** — *both* halves: the deprecation advice is now per schema (a configuration document is sent at `validate_config_document`, not at `CuemsScript.validate`), and `cuemsutils.tools.validate_config_document` is the public stand-alone validator this section called *"a surface this library does not have and arguably should"*. It validates a **file**, not a payload — which is why it does **not** answer `cuems-editor`'s own UR-5 below |
| **UR-6** no public id-coercion helper | the uuid4→`Uuid` rule published under `cuemsutils.tools` | **CLOSED** by feature 012's FR-030. The engine deleted its mirror at `c31734c` and re-exports `coerce_identity` as `as_id` — the loop this guide exists to close, closing |
| **UR-7** `fade_out` → `stop` is not behaviour-preserving | the claim corrected wherever it is made | **CLOSED** 2026-10-01. `xml/versioning.py` and `CLAUDE.md` both said "behaviour-preserving"; the engine measured that its `_handle_fade_out` never called `disarm()`, so a converted document now disarms its target where it previously leaked player processes. An improvement, but not a preservation — and the wrong reason would stop a consumer checking its own handler. 008's own migration guide (FR-053b) had it right all along; only those two overclaimed |

**All six of `cuems-engine`'s are now closed**, and the last two closed the way the first four did:
by *publishing* a capability that already existed inside `cuemsutils.xml`, not by adding a synonym.
That is the same move FR-025 made for `CuemsNetworkMapType` and FR-030 made for the coercion rule.

### `cuems-editor`'s two, from flow 02 *(added 2026-10-02)*

⚠️ **The numbers collide across repositories, and the reports are not the same reports.** Each
consumer numbers its findings in its own `upstream-reports/` directory, so `cuems-editor`'s UR-5 is
a *different* finding from `cuems-engine`'s UR-5 directly above — which 013 closed. Cite them as
`<repo> UR-<n>`, never as a bare UR number.

| Report | Asks for | State |
|---|---|---|
| **`cuems-editor` UR-5** no public way to build a configuration document from JSON | one public ingestion per configuration domain, symmetric with `CuemsScript.from_json` — e.g. `ConfigManager.from_json(SchemaName, payload)` or `set_document(SchemaName, payload)`, decoding through the same mapper and adapters as `load_*` | **OPEN, and it blocks a consumer task.** 008 gave every configuration domain a `save_*`, but each writes the object the `ConfigManager` already holds, and nothing public turns a client's JSON document into that object. `ConfigDict.from_decoded` is on an internal class, takes the *decoded* shape rather than the wire shape, and stores values verbatim — so a wire `"node_role": "node"` would stay a string where `save_network_map` expects a `NodeRole`. `validate_config_document` validates a path, not a payload. The editor's `config_save` therefore answers the four configuration domains with an error naming this report, and its test is `xfail(strict=True)`: it turns **XPASS** the day the call exists. This is `cuems-editor` 001 **T059** — the one task of 63 that did not land |
| **`cuems-editor` UR-4** a duplicate node identity carries no structured identity | the colliding identities (and their MACs) *on the exception* — a `Violation` with `location=(identity, "uuid")`, or an attribute on a dedicated subclass | **OPEN, worked around.** `ConfigManager.load_network_map()` on a map with one identity on two rows raises `ValidationError` whose `violation` is `None` and whose `__cause__` is a plain `ValueError`; the identities exist only inside `check_node_identities_unique`'s sentence. `cuemsutils.errors.node_identity_collision_message` recognises the case and also returns a string. The editor's `network_map_error` frame needs `{"kind": "duplicate_identity", "identity": …}` as *data*, so it lifts the first identity out of this library's own prose with one anchored pattern (`node_reads.py`, `collided_identity`) and sends `"identity": ""` if the sentence ever changes. **A consumer parsing this library's prose is a contract nobody declared** — and this library can change that sentence in a patch release without knowing it broke anything |

**Both are the same shape as the six already closed** — a fact the library holds and does not hand
out. Neither is a defect in behaviour; both are gaps in the public surface, and both belong in the
next feature's public-surface pass rather than in a feature of their own. Collected with the rest of
the inbound work in
[`specs/planning/upcoming-feature-requirements-2026-10-02.md`](../planning/upcoming-feature-requirements-2026-10-02.md).

## 6. Rollout, rollback and the release gate

*(FR-091–FR-104. Filled by T038a, T040, T041, T043–T045.)*

---

## 7. Status and sequence, as at 2026-09-25

This guide is the hand-off document for the six consumer repositories. Three have taken it; three have
not. Recorded here so a reader arriving at any section knows which half they are in.

| Flow | Repository | Feature dir | State | Candidate tag |
|---|---|---|---|---|
| 03 | `cuems-common` | `001-node-role-and-conversion-ordering` | **landed** | **`e3c9430`** (re-cut 2026-09-29 from `3af31cc`, itself relocated from `f2fc0f5` on 2026-09-24) |
| 04 / 04a / 04b | `cuems-nodeconf` | `001-network-map-object-adoption`, `002-public-network-map-path`, `003-startup-readiness` | **landed** | **`b305c1c`** (re-cut from `6c0cca7`, 2026-09-28, signed and pushed) |
| 07 | `cuems-power-bridge` | `001-node-role-parser`, `002-cluster-poweroff-cli` | **landed**; recorded here in [§5a](#5a-cuems-power-bridge--the-fourth-copy-of-the-node-model-deleted-us1us11-landed-2026-09-24) | **`399baf7`** (re-cut twice on 2026-09-29: `d5c4226` → `13a9af4` → `399baf7`) |
| 01 | `cuems-engine` | `008-cuems-utils-migration` | **not started** — bases on `feat/nodelist-modify-dispatch` | — |
| 02 | `cuems-editor` | `001-cuems-utils-migration` | **not started** — bases on `feat/nodelist-adoption-api` | — |
| 05 | `cuems-frontend` | `001-schema-descriptor-migration` | **not started** — carries a scope decision, below | — |

The three outstanding are the Python show/UI path, and they are chained: `cuems-editor` was gated on
this repository's wave 0 (**closed** — the descriptor has a public path), and `cuems-frontend` on
`cuems-editor`. None of the three had a `feat/xml-refactor` branch as of 2026-09-25.

**Each now carries a self-contained planning bundle** at `specs/planning/xml-refactor/` in its own
checkout, following the precedent `cuems-nodeconf` and `cuems-power-bridge` set: a runnable flow, the
binding decision subset, that repository's consumer-audit findings, a re-measured call-site inventory,
and — for the two on the wire — the payload contract from their own side. The sibling `cuems-utils`
checkout is no longer required reading for any of them.

Findings those bundles added, each measured rather than inherited (full detail in `baseline.md`'s
2026-09-25 section):

- `cuems-engine`'s `find_hosts` has **no caller anywhere in the ecosystem** and reads the node wrapper
  instead of the node, so it raises unconditionally today — independent of the vocabulary. Two of
  T023's four sites are inside it.
- `CTimecode(CTimecode(...))` **is idempotent**, so the engine's five re-wrapping sites are redundant
  rather than broken.
- `cuems-frontend` has a **second** media-duration display site, in an Angular **template**, which a
  sweep over `*.ts` cannot find. `getTemplateOutputStructure` has **three** call sites, not one, and
  the `|| 20` `master_vol` fallback appears **three** times against a library default of `100`.
- `cuems-editor`'s `tests/test_repair_durations.py:6` is a **sixth** consumer of the retired surface,
  outside the census's `src/`-only denominator.
- **An unmerged three-repository feature from 2026-09-04** — the node adopt/un-adopt hop and cluster
  liveness — spans `cuems-editor` (`feat/nodelist-adoption-api`), `cuems-engine`
  (`feat/nodelist-modify-dispatch`) and `cuems-nodeconf` (`feat/nodelist-modify-hardening`), under three
  different branch names, **none merged**, with **`cuems-frontend`'s UI tier never written**. Three
  consequences for this guide: it sets flows 01 and 02's base branches; it makes **FR-047's
  `initial_mappings` untangling three-way** — `project_mappings`, `network_map` node status, **and**
  `nodeconf_available`, a liveness fact about a daemon belonging to no schema; and it introduces a
  liveness distinction FR-033 does not cover, between each node's `online` (~30 s discovery) and
  `node_status`'s `alive` (sub-second ping/pong, *"the only signal the GO gate trusts"*). `cluster_status`
  and `cluster_warning` are therefore **cross-repository contracts**, not internal engine names.
- **`cuems-nodeconf`'s candidate `6c0cca7` is missing that feature's node-daemon third**, and the
  question of whether that matters is answered in `nodeconf-map-write-divergence.md`: of the branch's four
  defects, the IPC-reply fix was **ported verbatim**, the truncated-map hazard is **superseded by
  construction** (the daemon renders no temp file now; `write_tree` uses `tempfile.mkstemp` — measured, 6
  distinct names over 6 saves), and the lost-adopt race is **superseded in effect** (0 of 60 concurrent
  trials, because feature 001/002 passes node dicts by reference throughout). **Two remain open**: a
  spurious *"Node not found"* in the `set_comms()` → `read_network_map()` window — which
  `cuems-engine`'s `cf5c4ad` turns from a stall into a confidently wrong answer, since its readiness probe
  is the existence of a socket `set_comms()` creates before the window opens — and `CLAUDE.md:26`'s claim
  that `<online>` is a boot-only snapshot, which is the very fact the editor and frontend bundles depend
  on for the `online`-versus-`alive` distinction. Reported, not fixed — another repository, another
  author — but both touch code flows 01 and 02 migrate.

### What the release waits on

**This feature's own gate is unchanged**: six consumer flows landed, plus a measured census of zero
(FR-029), then the deletions and the version move. What has changed is the claim about what follows.

`cuems-utils` features **011–014** — `/etc/cuems` first install, uuid4 convergence, the device-class
reshape (F6), and `hardware_outputs` becoming real — are a **hard successor** to this feature, not a
follow-up, and the shared `xml-refactor-merge-candidate` tag comes **after** them. `cuems-utils` is
therefore the last repository to cut its tag, by decision: it is the library every other repository
here pins.

Two of the four reach repositories this guide covers, so a reader should not treat this migration as
final for those files:

| | Feature | Reaches |
|---|---|---|
| 011 | `/etc/cuems` first install | `cuems-common` (hands over `network_map.{xml,xsd}`, gains the identity contract). **Blocks 012 hard** |
| 012 | uuid4 convergence | every project library — the re-mint is a **cross-document** identity change, and node uuids appear inside compound strings (`<uuid>_<output_id>` in every `<output_name>`) |
| 013 | device-class reshape | `cuems-frontend`'s four cue-type unions in `project-edit/sequence/sequence.component.ts` |
| 014 | `hardware_outputs` | `cuems-nodeconf` (transcribes `display.conf`), `cuems-editor` / `cuems-frontend` (read the port inventory from a new place) |

Authority: `specs/planning/etc-cuems-first-install-execution.md` §5 and §8.
