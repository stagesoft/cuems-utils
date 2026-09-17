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
| `cuemsutils.config.network_map.CuemsNetworkMapType` (internal, **no public equivalent today**) | none — see [§4a's finding](#️-one-finding-the-gate-caught-a-third-internal-import). `ConfigManager.load_network_map()`/`save_network_map()` read and write one; nothing constructs one | **open** |
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
| `cuems-engine` | | not started |
| `cuems-editor` | | not started |
| `cuems-common` | Avahi templates and their filenames · the live-file migration tool · conversion ordering · release-gate demonstration | **landed** 2026-09-17 (`1a00159`), **unmerged** — holds a merge gate with `cuems-nodeconf` |
| `cuems-nodeconf` | network-map object swap · relocated timing helper · Avahi vocabulary (its half) · packaging bounds | **all three stories landed** 2026-09-17 (`8ce7552`), **unmerged** — holds a merge gate with `cuems-common` |
| `cuems-frontend` | | not started |
| **`cuems-wsclient`** | | not started |
| *(`cuems-power-bridge`)* | **not in D32's six** — found carrying the retired vocabulary in shipped code; see [§5](#️-the-denominator-is-wrong-a-seventh-consumer-carries-the-retired-vocabulary) | **unscheduled** |

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

There is no public name for that class today. `ConfigManager.load_network_map()` **returns** one and
`save_network_map()` writes one, but neither lets a caller build one from an index it holds in
memory. So this is a real gap in wave 0's surface against D34, not a consumer mistake.

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

**Re-checked at `8ce7552`**: both docstrings are still stale (`tools/NodeList.py:177`, `config/network_map.py:156`), and `cuems-nodeconf`'s T049 is still open on its side — the report has been received here by inspection rather than delivered.

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
(`/disk/Projects/StageLab/cuems-power-bridge/dev/planning/cuems-power-bridge-node-role-findings.md`,
untracked) opened it from `cuems-common`'s side; verifying it against the bridge's source turned up
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

## 6. Rollout, rollback and the release gate

*(FR-091–FR-104. Filled by T038a, T040, T041, T043–T045.)*
