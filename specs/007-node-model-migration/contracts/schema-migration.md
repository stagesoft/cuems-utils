# Contract: the `network_map.xsd` migration

**Feature**: `007-node-model-migration` | **Date**: 2026-08-24

This is the cross-repository half. It governs the schema edit, the documents already on disk, and
the release ordering that keeps a deployed node from meeting a document it cannot read.

---

## M1 — The schema change is exactly two elements and two types

| Change | Detail |
|---|---|
| Renamed | `<node_type>` → `<node_role>`, **in place** (fourth child of `NodeType`) |
| Retyped | that element: `cms:NonEmptyString` → `cms:NodeRoleType` |
| Retyped | `<uuid>`: `cms:NonEmptyString` → `cms:UuidType` |
| Added | `NodeRoleType` — `xs:string` restricted to `controller`, `node`, `firstrun` |
| Added | `UuidType` — `xs:string` restricted to the canonical 8-4-4-4-12 hex pattern |

**Asserted**: no other schema file is modified (FR-010a). Diffing the five others against their
pre-feature content yields nothing.

**Asserted**: the element keeps its position, so derived element order is unchanged and the
FR-010 round-trip diff stays at two differences.

---

## M2 — The mirrored copy is identical

`cuems-common`'s `etc/cuems/network_map.xsd`, installed to `/etc/cuems/network_map.xsd`, is
byte-identical to `cuemsutils/xml/schemas/network_map.xsd`.

**Asserted**: by comparison, in a test that fails when they diverge. They have drifted before —
the mirror is the copy every `xmllint --schema` invocation on a node actually uses.

---

## M3 — The conversion

A stdlib-only script, shipped by `cuems-common`, invoked from `debian/postinst`.

**Behaviour**:

| Input | Output |
|---|---|
| `<node_type>NodeType.master</node_type>` | `<node_role>controller</node_role>` |
| `<node_type>master</node_type>` | `<node_role>controller</node_role>` |
| `<node_type>NodeType.slave</node_type>` / `slave` | `<node_role>node</node_role>` |
| `<node_type>NodeType.firstrun</node_type>` / `firstrun` | `<node_role>firstrun</node_role>` |
| any other value | left untouched; the file then fails validation, loudly |
| no `<node_type>` present | file untouched, exit 0 |
| file absent | exit 0 |

**Asserted — idempotence**: converting twice produces bytes identical to converting once
(SC-004b).

**Asserted — minimality**: every byte outside the matched elements is unchanged, including
indentation, the `cms:` prefix and `xsi:schemaLocation`. This is why the implementation is a
textual rewrite and not an ElementTree round trip (research R8).

**Asserted — validity**: the converted corpus documents validate against the updated schema.

**Asserted — no import of `cuemsutils`**: the script runs from `/usr/bin` where the shared venv is
not importable.

**Packaging obligations**:

- Runs in `postinst`, after dpkg has resolved the conffile.
- Handles a `.dpkg-new` / `.dpkg-dist` sibling left by a conffile prompt — `/etc/cuems/network_map.xml`
  is a conffile that `cuems-nodeconf` rewrites on every adoption, so on a live node it is always
  locally modified.
- Never fails the upgrade: an absent, already-converted, or unparseable file exits 0 with a
  diagnostic.
- The shipped default `etc/cuems/network_map.xml` is updated in the source tree, so a fresh
  install never needs converting.

---

## M4 — The `cuems-common` tools

Three tools select the controller by XPath on the old element and must move together with it:

| Tool | Expression today | Consequence if stale |
|---|---|---|
| `cuems-write-chrony-source` | `./node_list/node[node_type='NodeType.master']/ip` | no time sync source; cluster drifts |
| `cuems-log-collector-url` | same | logs stop reaching the collector |
| `cuems-logs` | `findtext("node_type")`, then strips the `NodeType.` prefix | role column reads `-` |

**Asserted**: all three resolve the controller's IP from a converted map, and zero occurrences of
`node_type` or the `NodeType.` prefix remain in `cuems-common` source, shipped files or
documentation (SC-004a).

**Also in scope**: `docs/node-identity-contract.md`, `CLAUDE.md` and `README.md` document
`node_type` and the `NodeType.master` spelling as *the contract*. They are the ecosystem's
reference for this field and are updated in the same branch.

**Out of scope**: the Avahi service templates' `node_type` TXT record. That is a discovery
surface, not the XML document (spec Assumption 10). Inventoried, not changed.

---

## M5 — Release ordering is a gate

**Stated in the migration guide, not merely observed**:

1. `cuems-utils` — schema, model, engine, write path.
2. `cuems-nodeconf` — model and serializers deleted; the sole writer follows the schema.
3. `cuems-common` — mirror, conversion, tools, documentation.
4. **Feature 008** — `cuems-engine` and `cuems-editor` readers.

**No release of any of the three repositories ships before step 4** (FR-030c). The hard cutover
has no working partially-deployed state: a converted map meets an unmigrated reader, or an
unconverted map meets a migrated schema, and both fail.

**Asserted**: the guide states the ordering, the reason, and the failure mode of getting it wrong.

---

## M6 — Goldens change once, deliberately

**Asserted**: the `network_map` goldens are regenerated and `tests/golden/MANIFEST.sha256` is
updated in the same commit, with the justification recorded — the ceremony feature 006 established
for the only two goldens it modified.

**Asserted**: every changed line in that diff is the rename or the value mapping.

**Asserted**: no other golden under `tests/golden/` changes (SC-010a).
