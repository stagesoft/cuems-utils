# Data model — feature 008

Written as this feature's own design, since 008 has no section of
`xml-rebuild-06-target-design.md` to follow the way 005–007 did. ITEM C's shape is informed by the
landed `ConfigManager`/`ConfigBase` pattern; ITEM D's by `TypeSpec`/`FieldSpec`.

**Two sections are hand-off interfaces** — §2 (`save()`) and §3 (the descriptor). Phase 2 is
implemented against them **as landed code**, not as plan text. If either is still negotiable when
Phase 1 merges, the phase gate has bought nothing (FR-018, FR-035).

---

## 1. The version marker

A **document property**, not a domain field. It never becomes a model attribute, never appears in a
wire projection, and no model class declares it (research R1).

| Aspect | Decision |
|---|---|
| Representation | Optional unqualified attribute `doc_version` on each root element's anonymous complex type |
| Type | `xs:positiveInteger`, `use="optional"` |
| Scope | Per schema — six independent sequences (FR-048b) |
| Absent | Means version **1**, the oldest. Every document written before this feature (FR-050) |
| Written by | `mapper.build_document`, beside `xsi:schemaLocation` |
| Read by | A pre-validation probe: stdlib `ElementTree`, root attribute only, no schema (R2) |
| Excluded from | `spec._derive_attributes`, every wire projection, every model class |

**Version numbers after this feature.** `script` → **2**; the other five stay at **1**. Only
`script.xsd` changes content this feature. Per FR-048b the sequences are independent: moving `script`
must age nothing else, which is measured (SC-023b) rather than argued from the registry's shape.

**What emitting the marker invalidates, and where that is discharged.** `doc_version` is written by
`mapper.build_document`, which every writer in the library goes through — so the moment it lands, every
golden cut in Phase 1 and every config round-trip fixture gains a root attribute it did not have:

| Artifact | Effect | Discharged by |
|---|---|---|
| `tests/golden/**` (cut in ITEMs A and D) | every root element gains `doc_version` | FR-010's **third** recorded golden event |
| Config round-trip fixtures (FR-015) | writer's output form now carries the attribute | FR-015's normalisation absorbing it |
| `project_load` payload | **unaffected** — the marker is a document property, never a wire field | asserted by test (R1) |

This is a Phase 2 change reaching back into Phase 1's artifacts. It is scheduled, not discovered.

### 1.1 Conversion registry

```
(schema_name, from_version) -> Conversion | None
```

A `Conversion` transforms a parsed tree in memory and reports what it changed. `None` is a valid
entry: an identity step, for purely additive schema growth (FR-051d, R9). The registry is walked
step by step, so a document three versions old runs three conversions in order — not one bespoke
old-to-current jump.

**`script` 1 → 2 carries three transformations in one step** (FR-051b), which is what demonstrates the
mechanism composes rather than merely works:

| # | Transformation | From FR |
|---|---|---|
| 1 | `<duration>TC</duration>` → `<duration><CTimecode>TC</CTimecode></duration>` on `Media` | FR-051 |
| 2 | `action_type` `fade_in` → `play`, `fade_out` → `stop` | FR-051a |
| 3 | `<fade_profiles>` and children **dropped**, each drop reported | FR-051c |

---

## 2. Hand-off interface 1 — the config write path (ITEM B)

**Landed and frozen (T036).** `save()` exists on `CuemsSettingsType`, `CuemsProjectSettingsType`,
`CuemsProjectMappingsType` (`src/cuemsutils/config/`) and the pre-existing `CuemsNetworkMapType`, all
via the shared `config.base.save_document`; `ConfigManager.save_settings`/`save_project_settings`/
`save_project_mappings` (`src/cuemsutils/tools/ConfigManager.py`) match the signatures below exactly —
asserted by `tests/integration/test_config_save.py::test_every_domain_save_has_the_same_argument_shape_and_default_path_behaviour`.
Phase 2 is written against this as landed code.

Fixed shape. Phase 2's backup-before-upgrade writes through this.

```
ConfigDict subclass:
    save(path: str | PathLike) -> None

ConfigManager:
    save_settings(path: str | None = None) -> None
    save_project_settings(project_uname: str, path: str | None = None) -> None
    save_project_mappings(project_uname: str, path: str | None = None) -> None
```

Symmetric with the landed `CuemsNetworkMapType.save()` / `ConfigManager.save_network_map()`.

**Contract, identical across all four domains:**

1. Validate T1 first, raise `SchemaError` on the first structural violation, write nothing.
2. Build through `documents.build_tree`, write through `write_tree`.
3. **Does not mutate the object** — `build_tree` reads declared fields through the adapters'
   `to_lexical`/`to_wire` and never writes back.
4. **Atomic**: temp file in the destination directory, then `os.replace`. A concurrent reader sees the
   whole old file or the whole new one, never a truncated document (FR-017).
5. **No backup.** Backups belong to schema upgrades only (FR-016, FR-041b). `os.replace` carries the
   safety story for ordinary writes.
6. `path=None` defaults to where the corresponding loader read from.

**Why this is a Phase 1 deliverable with a Phase 2 consumer.** ITEM E's upgrade path persists
converted documents through exactly this call. Fixing the signature now is what lets Phase 2 be
written against landed code (D28, D30).

---

## 3. Hand-off interface 2 — the schema descriptor (ITEM D)

**Landed and frozen (T082).** `SchemaDescriptor`, `TypeDescriptor`, `FieldDescriptor` and
`Repairability` exist in `src/cuemsutils/xml/descriptor.py`, matching the shape below exactly —
including `default`'s `Unset` sentinel and the three-rule repairability derivation in §3.1.
Verified against the landed module directly (not against the tests alone) on 2026-09-02: field
for field, `FieldDescriptor` carries `name`, `xsd_type`, `required`, `repeated`, `order`, `kind`,
`enum_values`, `default`, `repairability` — no more, no fewer. Phase 2 is written against this as
landed code.

New module. Reuses `spec.derive()` for structure; adds what `derive` does not carry (research R3).

```
SchemaDescriptor
    schemas: tuple[str, ...]                 # all six
    types(schema) -> tuple[TypeDescriptor]
    describe(TypeKey) -> TypeDescriptor

TypeDescriptor
    key: TypeKey
    fields: tuple[FieldDescriptor, ...]      # declared order, from derive()

FieldDescriptor
    name: str
    xsd_type: str | None
    required: bool
    repeated: bool
    order: int
    kind: FieldKind                          # ELEMENT | ATTRIBUTE | WILDCARD
    enum_values: tuple[str, ...] | None      # from xs:enumeration facets (FR-029)
    default: Any | Unset                     # model-layer value (FR-030, FR-031)
    repairability: Repairability             # REPAIRABLE | UNREPAIRABLE (FR-031a)
```

**The four sources, and which answers what.** The descriptor is not schema-derived in the way
`FieldSpec` is — two of its four inputs are not the schema, which is the reason it is a separate
structure:

| Attribute | Source |
|---|---|
| `name`, `xsd_type`, `required`, `repeated`, `order`, `kind` | `spec.derive()` — the schema |
| `enum_values` | `xs:enumeration` facets on the resolved simple type, **per schema** (R4) |
| `default` | The bound model class's `declared_defaults()`, via the registry (R5) |
| `repairability` | The registered semantic-rule surface (R8) |

**`Unset` distinguishes "no default" from "defaults to `None`"** — the sentinel already exists and
already carries that meaning, so FR-031 needs no new convention.

### 3.1 Repairability derivation

One rule, stated once (FR-031b), so no field is classified case by case:

1. A field targeted by a registered T2 rule takes **that rule's declared** repairability.
2. A field with **no default** (`Unset`) is **UNREPAIRABLE** — there is nothing to recover it to.
3. Any other field is **REPAIRABLE**: no rule can flag it, so the classification is unreachable in
   practice and the permissive value costs nothing.

Rule 2 outranks rule 1: a rule may declare its violation repairable, but if the field has no default
the repair cannot be performed.

**Resolving a rule target to a descriptor field — the two name spaces do not coincide.** Rules target
**model class names**:

```python
@register("output_name_shape", [("VideoCueOutput", "output_name")], repairable=...)
```

while `TypeDescriptor.key` is schema-derived and carries the **XSD type name** (`VideoCueOutputType`),
qualified by schema. Rule 1 above therefore needs an explicit join, and it is the registry's existing
binding table — the same `registry.bind("VideoCueOutputType", VideoCueOutput)` that ITEM D already
reads for defaults (R5). The resolution is:

```
rule target (class_name, field_name)
  -> registry: class_name -> the XSD type name(s) bound to that class
  -> descriptor: (schema, xsd_type_name) -> TypeDescriptor -> field_name -> FieldDescriptor
```

Two obligations follow, both asserted by test rather than assumed:

- **Every rule target MUST resolve to at least one `FieldDescriptor`.** A target that resolves to none
  is a stale rule or a renamed field, and it must fail loudly — silently dropping it would leave the
  field classified by rules 2/3 and quietly widen what is repairable.
- **A class bound to more than one XSD type** propagates the rule's declaration to the same field in
  each. That is the correct reading — the rule fires on the object, whichever type produced it — and it
  is recorded here so the fan-out is deliberate rather than incidental.

**Every registered rule must declare.** `register()` gains a required keyword-only `repairable: bool`
with **no default**, so an undeclared rule is a `TypeError` at import (R8). The count of unclassified
fields is zero, asserted by test (SC-011a, SC-011b).

### 3.2 What the descriptor replaces

`create_script()` and `templates/settings.xml`, both deleted. Output need not be byte-identical to
either (D25, FR-033, FR-034). In particular `create_script`'s ordering defect — validate, *then* blank
the ids, so the object served would fail its own check — is not carried forward.

---

## 4. The repair report (ITEM E)

**Public**, under `cuemsutils.errors`, joining `CuemsError`/`ValidationError`/`SchemaError`/`IngestError`
on 006's precedent: an exception the caller cannot name is one it cannot catch, and a repair the
caller cannot inspect is one it cannot surface.

```
LoadReport
    document: str                            # which file
    outcome: Outcome                         # CLEAN | CONVERTED | REPAIRED
    conversions: tuple[ConversionRecord, ...]
    repairs: tuple[RepairRecord, ...]
    file_differs_from_loaded: bool           # is the on-disk file now stale?

RepairRecord:   field_path, previous_value, substituted_value, rule_name
ConversionRecord: from_version, to_version, description, dropped_elements
```

From the report alone a caller answers FR-046's five questions: which document, which field, what was
there, what replaced it, whether the file on disk now differs. `dropped_elements` is what makes
FR-051c's data drop permissible — a drop that is reported is not a silent loss (SC-016e).

**The library gains no channel.** The report is returned; 009 forwards it to the UI as a WS message
(FR-047). It also has a second job: FR-041c saves a repaired document by overwriting with no backup,
which is only safe because the operator saw this report first (FR-053a).

---

## 5. The network-map object (ITEM C) — landed (T037–T052)

`NodeIndex` is already the MAC-keyed working set feature 007 created, which is the same shape
`CuemsNodeConf` maintains ad hoc — so no translation layer is needed (research R7).

```
NodeIndex  (existing: from_nodes, by_role, controllers)
    merge(discovered: Mapping) -> None            # match by uuid, the stable key
    adopt(node_uuid) -> bool
    unadopt(node_uuid) -> bool                    # refuses the controller
    set_controller_always_adopted() -> None
    missing_adopted(discovered: Mapping) -> tuple[...]
    signature() -> tuple[...]                     # stable over persisted fields

CuemsNetworkMapType  (existing: save)
    refresh(discovered: Mapping, path) -> bool    # merge + controller;
                                                   # writes only if signature changed
```

**`refresh` takes `path`**, unlike the shape sketched earlier in this section: it writes through
`save(path)`, and `save` has no default path (§2) — the parameter was implied by "writes" and is made
explicit here now that the method is landed.

**Discovery is passed in, never reached for.** Four of `CuemsNodeConf`'s methods read
`self.listener.nodes` directly; parameterising that is what makes them functions of their inputs and
therefore pinnable by E23's characterization tests. It is also what keeps discovery — a
`cuems-nodeconf` responsibility under D23 — out of this repository.

**`refresh` returns whether it wrote**, preserving today's write-only-if-changed behaviour, which is
what `signature()` exists for. It calls `merge` and `set_controller_always_adopted` only —
`missing_adopted` is reporting-only in the daemon too (never affects the map or the write decision), so
it is not part of the orchestration; a caller that wants the warning calls it separately on the same
`discovered` argument.

**Not ported**: `CuemsNodeConf.set_master_always_adopted`'s `self.is_first_run` branch, which clears
every non-controller node's `adopted` flag on a first run. `set_controller_always_adopted()`'s shape
above carries no such parameter. Left for 009 to reconcile when the daemon actually adopts this object
— recorded here rather than silently reproduced or silently dropped.

### The dispatch chain target (T042a)

The operator's adopt/unadopt chain, traced end to end: `cuems-frontend`'s `settings.component.ts`
(`confirmAddNode`/`confirmRemoveNode`) emits `nodelist_modify` with `modify_action` `'ADD'`/`'REMOVE'`
→ forwarded to `CuemsNodeConf.engine_callback` (`CuemsNodeConf.py:113-144`), which dispatches:

| `modify_action` | Daemon call today | `NodeIndex` equivalent |
|---|---|---|
| `'ADD'` | `self.adopt_node(node_uuid)` | `NodeIndex.adopt(node_uuid)` |
| `'REMOVE'` | `self.unadopt_node(node_uuid)` | `NodeIndex.unadopt(node_uuid)` |

No third `modify_action` is recognised — anything else is already an error response in
`engine_callback`. Asserted by `tests/contract/test_dispatch_chain_target.py`.

### T049 — `write_network_map`'s `required_fields` filter: an artifact, not preserved behaviour

`CuemsNodeConf.write_network_map` (`:413-438`) pre-checks `['uuid','mac','name','node_role','ip']`
for `None` and raises `ValueError` naming the mac and field, *before* building and saving. Every one of
those five is already `minOccurs="1"` in `network_map.xsd` — `CuemsNetworkMapType.save()` (landed,
feature 007) already rejects the same documents via T1 schema validation, raising `SchemaError`. The
daemon's check predates that save path (it existed when the daemon serialized by hand) and duplicates
what the schema now enforces on its own; its only remaining difference is a friendlier message
(naming the mac and field) under a different exception type (`ValueError`, not `SchemaError`) — not a
distinct behaviour, and not part of `save()`'s documented contract (§2). Classified as an **artifact**
and not ported: `NodeIndex`/`CuemsNetworkMapType` rely on `save()`'s existing T1 validation instead.

### T050 — the `cleanup()` defect: prescribed, not fixed here

`CuemsNodeConf.cleanup` (`:579-583`) reads `self.cm.show_lock_file`, but `self.cm` is never assigned
anywhere in the class — every call raises `AttributeError`. Out of scope to fix directly (D16: this
feature does not edit consumer repositories); recorded as a prescribed fix in `migration-guide.md` for
whoever next touches `cuems-nodeconf` — likely `self.cm = ConfigManager(...)` needs assigning in
`__init__`, matching the pattern every other consumer of `show_lock_file` uses.

---

## 6. What ITEM A changes in the existing model

| Artifact | Change |
|---|---|
| `script.xsd:182` `Media.duration` | `cms:TimecodeType` → `cms:CTimecodeType` |
| `MediaCue.set_duration` | Three-branch dispatch → `format_timecode`, as the other six |
| `validators.media_duration` | `str` branch removed once unreachable |
| `adapters` `"TimecodeType": _String()` | **Verify before removing** — may still resolve for the inner `<CTimecode>` child (FR-006) |
| `settings.xsd` `CTimecodeType`/`TimecodeType` | Deleted, with `config/settings.py::CTimecodeType` |
| `script.xsd` fade-profile surface | Deleted: three types, the element on two cue types, two model classes, five rules |
| `script.xsd` `ActionType` | `fade_in`, `fade_out` deleted (ITEM D's, FR-029a) |
| `script.xsd:530` `TimecodeType` | **Survives** — lexical type of the inner `<CTimecode>` |

After ITEM A: seven elements carry a time value, all `cms:CTimecodeType`, all storing `CTimecode`.
Zero string-stored exceptions.
