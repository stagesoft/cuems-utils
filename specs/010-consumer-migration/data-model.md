# Data model — consumer migration

**Date**: 2026-09-03 | **Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

This feature adds no schema, no table and no new persisted entity. What it *does* have is a set of
entities that **cross repository boundaries** — each owned by one repository, consumed by several,
and currently represented differently on each side of the boundary. That divergence is the feature.

So this document models each entity as: what it is, who owns it, how it is represented **today** in
each consumer, and what it becomes. The "today" column is the migration's actual work list; where
it says *string* against an owner that says *typed*, that is an FR-030a-ii caller waiting to be
found.

---

## 1. Node role

**Owns**: `cuemsutils.tools.NodeList.NodeRole` (007). **Values**: `controller`, `node`, `firstrun`.

| Surface | Today | After |
|---|---|---|
| `network_map.xml` | `<node_role>` typed `cms:NodeRoleType` (007) | unchanged |
| Library decode | `NodeRole` enum | unchanged |
| `cuems-engine` | `CONTROLLER_NETWORK_FLAG = "NodeType.master"`, compared at two sites | `NodeRole.controller`, compared as a value |
| `cuems-wsclient` | `node_type: str \| None`, compared `!= "NodeType.slave"` | the library's typed value; **the private reader is deleted, not re-spelled** |
| `cuems-editor` | string in the node field list | `NodeRole` |
| Avahi TXT record | key `node_type`, values `master`/`slave`/`firstrun` | the role vocabulary, in both owning repositories at once |

**Validation**: a value outside the three is a schema violation, rejected at T1 — not a repairable
field. **Lifecycle**: set at first-run configuration; changed by an operator promoting a node.

**Why it is first in this document**: it is the only entity in the feature whose divergence is
currently *silent in production*. Every other row fails loudly or visibly.

---

## 2. Node adoption and presence

**Owns**: the network-map configuration object (008). **Fields**: `adopted`, `online` (booleans),
`uuid` (typed identifier).

| Surface | Today | After |
|---|---|---|
| Library decode | `bool` / `Uuid` (007's single-schema adapter exception) | unchanged |
| `cuems-engine` | `node.get("online") == "True"` — a string comparison | boolean |
| `cuems-editor` | strings in the node field list and the reload path | `bool` / `Uuid` |
| `cuems-nodeconf` | its own adopt/unadopt/merge/refresh/signature methods | calls into the library object |

**State transitions**: unadopted → adopted (operator action through the UI's adopt control,
dispatched by the daemon); adopted → unadopted (same path, reversed); offline ↔ online (discovery,
not operator action). **Invariant carried from 008**: the controller is always adopted.

**Partition**: `NetworkMap.partition_by_adoption` is **non-mutating**; the accessor it replaces
mutated the map it was given, which is why `cuems-engine` grew an inline workaround. After this
feature the caller's map is unchanged by the call.

---

## 3. Show document

**Owns**: `script.xsd` + `CuemsScript`. **Version**: `script` is at document version **2**; the
other five schemas at 1.

| Property | Value |
|---|---|
| Version marker | an optional attribute on the root type, read by a pre-validation probe |
| On the wire | **excluded from every projection** — the UI never sees it (FR-012) |
| Media duration, in XML | `<duration><CTimecode>HH:MM:SS.mmm</CTimecode></duration>` (was bare text) |
| Media duration, on the wire | `{"CTimecode": "HH:MM:SS.mmm"}` (was a bare string) |
| Distribution | rsynced controller → node by the engine's deploy path — a third exposure surface |

**Lifecycle, and the three load outcomes** (D21) — the state machine this feature's consumers must
finally handle in full:

```
                    ┌── version < current ──→ converted in memory ──→ loaded
                    │                          (disk untouched)
document on disk ───┼── current, valid ──────────────────────────────→ loaded
                    │
                    ├── current, repairable ──→ field set to the ────→ loaded
                    │                           descriptor default      + report
                    │                           (disk untouched)
                    └── current, unrepairable ─────────────────────────→ raises
```

**Persistence rule this feature adds** (FR-048a): none of the three non-failing outcomes writes to
disk. A repaired or converted document reaches disk only through a user-initiated save. Therefore a
repaired document that is never saved is **repaired again on every load and reported every time**,
and that repetition is signal, not noise (FR-048c).

---

## 4. Load report

**Owns**: `cuemsutils.errors` — `LoadReport`, `Outcome`, `RepairRecord`, `ConversionRecord`
(public since 008; verified present).

| Question it answers | Consumed by |
|---|---|
| Which document | editor → UI |
| Which fields were repaired, and to what | editor → UI |
| Which conversions ran | editor → UI |
| Whether the file on disk is now stale | **editor → UI, and load-bearing under FR-048b** |

**Never `None`**: a clean load returns an empty report, not absent one. **Never sent by the
library**: `cuemsutils` has no notification channel and must not gain one — 008 produces the
report, this feature forwards it.

**Sibling entity, new here**: the **unrepairable-load failure**. Not a `LoadReport` — the load
raised — but it travels the same message family (FR-049), because from an operator's side both are
"the library found something wrong with this document", differing only in whether it continued.

---

## 5. Schema descriptor

**Owns**: `cuemsutils.xml.descriptor` internally; reached publicly through the configuration
façade after wave 0.

Per complex type, across **all six** schemas:

| Fact | Status |
|---|---|
| Field name | exists (008) |
| XSD type | exists (008) |
| Cardinality | exists (008) |
| Legal values, where the type is a restricted enumeration | exists (008) |
| Model-layer default | exists (008) |
| **Constructible empty instance** | **added here** (FR-022a) — the one new fact |

**Why the sixth exists**: a nested object is not a field default. `getTemplateOutputStructure`
needs the *shape* of a cue's output — geometry, region, mapping — which no combination of per-field
facts supplies.

**Replaces**: `initial_template`-as-a-concrete-instance, and `templates/settings.xml`. Both were
hand-maintained; the descriptor is derived, so it cannot drift from the schema.

---

## 6. Editor↔UI payload

**Owns**: `cuems-editor`, projected from `CuemsScript.to_wire()`. Contract in
[`contracts/editor-ui-messages.md`](contracts/editor-ui-messages.md).

**Byte-identical to today's except for exactly two changes** — this is the constraint most often
misremembered, so it is stated as a delta and never as unconditional identity:

| Delta | Landed by |
|---|---|
| `schemaLocation` absent | 006 |
| `Media.duration` wrapped as `{"CTimecode": …}` | 008 |

Everything else is unchanged: every other key, the ordering, and the **string** boolean form. The
UI reads `enabled === true \|\| enabled === 'True'` and writes the string form back; that dual read
stays valid and simplifying it is an optional follow-up (FR-088e). `doc_version` is **not** a third
delta.

**New sibling**: the **payload version** advertised on connect (FR-105). It describes this contract,
not a document, and must not be confused with §3's document version marker (FR-106).

---

## 7. Package dependency edge

**Owns**: each repository's `debian/control` and `pyproject.toml`.

| Repository | Today | Gap |
|---|---|---|
| `cuems-common` | `>= 0.1.0rc15` **plus `Breaks:`** | the only mechanically enforced edge |
| `cuems-engine` | `>=0.1.0rc10` (pyproject) / `>= 0.1.0rc4` (control) | floor only, **and the two disagree** |
| `cuems-editor` | `>=0.1.0rc10` (pyproject) | floor only; **no `debian/` at all** |
| `cuems-nodeconf` | `>=0.1.0rc15` / `>= 0.1.0rc5` | floor only |
| `cuems-wsclient` | `>=0.1.0rc5`, optional | floor only, and optional |
| `cuems-frontend` | — | **not packaged; cannot hold an edge** → FR-105's handshake exists for this row |

**The modelling point**: a `>=` floor says "I need at least this". The release gate says "an
unmigrated consumer must refuse a library that has moved past it" — an *upper* bound or a `Breaks`.
A floor cannot express the gate, which is why four edges are missing rather than merely loose.
