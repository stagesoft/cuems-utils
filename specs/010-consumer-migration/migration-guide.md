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

## 6. Rollout, rollback and the release gate

*(FR-091–FR-104. Filled by T038a, T040, T041, T043–T045.)*
