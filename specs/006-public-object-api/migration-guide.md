# Migration guide — the six retired entry points (T084, FR-UX-001)

**Feature**: 006-public-object-api · **Date**: 2026-08-20
**Executed by**: feature **008**. Consumer repositories are **not** edited here.

Every entry point below still resolves in `v0.1.0` and warns on each use. All
six are removed in **`v0.1.1`**. This document is the work list.

Sites were located on: `cuems-engine` @ `rc_1` `afff04a`, `cuems-editor` @ `rc1`
`ef74136`, `cuems-nodeconf` @ `feat/nodeconf-reenable` `0a3ce37`.

---

## The map

| Retired | Replacement |
|---|---|
| `XmlReaderWriter(...).read_to_objects()` | `CuemsScript.load(path)` |
| `XmlReaderWriter(...).write_from_object(obj)` | `script.save(path)` |
| `XmlReaderWriter(schema_name="script", xmlfile=None).validate_object(obj)` | `script.validate()` |
| `XmlReaderWriter(...).read()` | `script.to_wire()` — **see the note below** |
| `CuemsParser(payload).parse()` | `CuemsScript.from_json(payload)` |
| `Settings` / `NetworkMap` / `ProjectMappings` / `ProjectSettings` | `ConfigManager(config_dir)` |

**`schema_name` disappears.** It is a property of the type, not of the caller.
Every replacement above knows its own schema.

### The one behavioural difference in the map

`read()` returns the reader's raw dict; `to_wire()` returns the projection. They
are identical **except** that `to_wire()` carries no
`{http://www.w3.org/2001/XMLSchema-instance}schemaLocation` key. That is an XML
artifact with no meaning to a consumer, nothing in any repository reads it
(`schemalocation-evidence.md` records the search), and the deprecation warning
on `read()` says so in its message.

Everything else is byte-identical, asserted per corpus document by
`tests/contract/test_wire_byte_identity.py` — the feature's gating test.

---

## Call sites

### `cuems-engine` (1 site)

**`src/cuemsengine/core/BaseEngine.py:509`**

```python
reader = XmlReaderWriter(schema_name="script", xmlfile=xml_file)
# ... .read_to_objects()
```
→
```python
script = CuemsScript.load(xml_file)
```

Also `src/cuemsengine/ControllerEngine.py:12` and
`src/cuemsengine/core/BaseEngine.py:17` — imports of `NetworkMap` and
`XmlReaderWriter` respectively.

`ControllerEngine` uses `NetworkMap.get_nodes_by_adoption`, which is **not**
retired and stays on the class. The import moves from
`cuemsutils.xml.Settings` to `cuemsutils.tools.ConfigManager`'s accessors, or —
if the static helper is genuinely all it needs — to
`cuemsutils.xml.settings` and stays internal-but-reachable for one more release.
That choice belongs to 008; it is flagged here because it is the one site the
map above does not answer cleanly.

### `cuems-editor` (9 sites)

**`src/cuemseditor/CuemsDBProject.py`** — the bulk of the work.

| Line | Now | Becomes |
|---:|---|---|
| 280 | `CuemsParser(data).parse()` | `CuemsScript.from_json(data)` |
| 408 | `CuemsParser(data).parse()` | `CuemsScript.from_json(data)` |
| 487 | `CuemsParser(data).parse()` | `CuemsScript.from_json(data)` |
| 724 | `CuemsParser(self.load(...)).parse()` | `CuemsScript.from_json(self.load(...))` |
| 799 | `XmlReaderWriter(schema_name=..., xmlfile=...)` then `write_from_object` | `script.save(path)` |
| 811 | `XmlReaderWriter(schema_name=..., xmlfile=...)` then `read_to_objects` | `CuemsScript.load(path)` |

`self.script_schema_name` becomes unused once 799 and 811 migrate. Deleting it
is part of the change, not a follow-up: an attribute naming a schema that
nothing passes is exactly the kind of thing that gets passed again later.

**`src/cuemseditor/repair_durations.py:204, 230, 231`** — a maintenance script
that reads, reparses and rewrites. All three lines collapse to
`CuemsScript.load(path)` … `script.save(path)`. Worth doing early: it is
self-contained and touches no running path.

**`src/cuemseditor/cli.py:60`** — `ProjectMappings(settings_file)` →
`ConfigManager(config_dir).mappings`. Note the argument changes from a *file* to
a *directory*; this is the one site where the call shape changes rather than the
name.

**`src/cuemseditor/CuemsWsServer.py:23`** — `from cuemsutils.xml import
NetworkMap`, used for `get_nodes_by_adoption`. Same question as
`ControllerEngine`'s, same answer: 008 decides.

### `cuems-nodeconf` (0 sites)

No import of any retired name. Nothing to do.

---

## Ordering

1. **`repair_durations.py`** — self-contained, off the running path, three lines.
2. **`CuemsDBProject.py`** — six sites, all mechanical, one attribute deletion.
3. **`BaseEngine.py`** — one site.
4. **`cli.py`** — the one site whose call *shape* changes.
5. **The two `NetworkMap` imports** — needs the decision above first.

Each step is independently shippable: the shims work throughout `v0.1.0`, so a
half-migrated consumer is a warning-noisy consumer, not a broken one.

## How to know it is done

Run the consumer's test suite with `-W error::DeprecationWarning`. Every
remaining call site announces itself, at the caller's line — which is what the
per-call emission (FR-027b) is for. Zero warnings means zero sites.

## What is *not* in scope

- **The wire format.** `initial_template` now matches `project_load`; the
  Angular UI's `=== true || === 'True'` dual-check already absorbs it and no
  frontend change is required. See `frontend-note.md`.
- **Config value shapes.** `ConfigManager`'s accessors return objects instead of
  raw dicts, but those objects *are* dicts — `isinstance`, `[]`, `.get()` and
  iteration all behave as before. Nothing in the consumers needs touching for
  that, which is why it landed in this feature rather than in 008.
