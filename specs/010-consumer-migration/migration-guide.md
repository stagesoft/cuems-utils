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
| `cuems-common` | | not started |
| `cuems-nodeconf` | | not started |
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

## 5. The ecosystem-wide count

*(FR-070–FR-073a, FR-UX-003. Filled by T062. Carries the counting **method** alongside the count,
and the exempt set enumerated as `<path>:<start_line>[-<end_line>]` with its two distinct
reasons — "exists to detect or convert the retired spelling" (permanent) and "not shipped"
(removable at any time) — never merged.)*

## 6. Rollout, rollback and the release gate

*(FR-091–FR-104. Filled by T038a, T040, T041, T043–T045.)*
