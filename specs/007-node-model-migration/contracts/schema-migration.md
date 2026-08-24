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
| Deleted | `PutType` — unreferenced by any element in this schema; X9 **resolved** (FR-029) |

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
| any other value | **the whole file is refused** — nothing written, bytes unchanged, a diagnostic names the document, the node and the value alongside the accepted ones; exit 0 so the upgrade survives (FR-011h) |
| no `<node_type>` present | file untouched, exit 0 |
| file absent | exit 0 |

**Asserted — no half-conversion**: a map mixing a recognised and an unrecognised value is refused
whole. Converting the recognised nodes and skipping one would leave a document carrying both
vocabularies, which no requirement describes and no test can pin.

**Asserted — a backup precedes any write** (FR-011i): a timestamped copy is written beside the
original before it is modified, restoring it reproduces the pre-conversion bytes exactly (SC-011),
and backups do not accumulate without bound. The file holds node aliases and adoption state that
exist nowhere else on the cluster.

**Asserted — idempotence**: converting twice produces bytes identical to converting once
(SC-004b).

**Asserted — minimality**: every byte outside the matched elements is unchanged, including
indentation, the `cms:` prefix and `xsi:schemaLocation`. This is why the implementation is a
textual rewrite and not an ElementTree round trip (research R8).

**Asserted — positive evidence** (FR-011d-i): a successful run records how many nodes it converted
and where the backup went. All four outcomes are distinguishable in that record:

| Outcome | Recorded as |
|---|---|
| converted | node count + backup path |
| already converted | explicitly, not silence |
| absent | explicitly |
| refused | the FR-011h diagnostic |

Silence on success would leave an operator unable to tell "already in the new format" from "the
conversion never reached this node".

**Asserted — validity**: the converted corpus documents validate against the updated schema.

**Asserted — no import of `cuemsutils`**: the script runs from `/usr/bin` where the shared venv is
not importable.

**Packaging obligations**:

- Runs in `postinst`, after dpkg has resolved the conffile. **Its ordering against
  `dh_installsystemd`'s service restart — which runs in the same `postinst` — is deferred to
  feature 008** (FR-011d-ii): the services that read the map are the ones 008 migrates.
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
documentation (SC-004a) — **excluding the four Avahi discovery files named below**, which SC-004a
exempts by name.

**Also in scope**: `docs/node-identity-contract.md`, `CLAUDE.md` and `README.md` document
`node_type` and the `NodeType.master` spelling as *the contract*. They are the ecosystem's
reference for this field and are updated in the same branch.

**Deferred to feature 008, not exempt**: the Avahi service templates' `node_type` TXT record. That
is a discovery surface, not the XML document (spec Assumption 10), so this feature inventories it
and does not edit it — but it carries the retired vocabulary and must follow it.

| File | Carries |
|---|---|
| `etc/avahi/services/cuems.service` | `node_type` TXT record |
| `usr/share/cuems/cuems.service.master` | TXT record **and** the retired word in its filename |
| `usr/share/cuems/cuems.service.slave` | TXT record **and** the retired word in its filename |
| `usr/share/cuems/cuems.service.firstrun` | TXT record |

**Asserted**: these four are named in the migration guide as feature 008's work, with the
`debian/install` and template-resolution consequences of the filename change (FR-011g), and they
are the exact set SC-004a's count excludes. Naming them is what keeps "deferred" distinguishable
from "missed".

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

**Asserted — and enforced, not only documented** (FR-030d, SC-012): versioned dependencies between
the `.deb` packages make the out-of-order upgrade impossible on a single node. `dpkg` is otherwise
free to upgrade `cuems-utils` before `cuems-common`, producing a migrated schema beside an
unconverted map — the exact state the release gate forbids. Demonstrated by attempting the
out-of-order upgrade and observing it refused.

---

## M6 — Goldens change once, deliberately

**Asserted**: the `network_map` goldens are regenerated and `tests/golden/MANIFEST.sha256` is
updated in the same commit, with the justification recorded — the ceremony feature 006 established
for the only two goldens it modified.

**Asserted**: every changed line in that diff is the rename or the value mapping. The
normalisation diff (C4a) is a separate change and is reviewed separately.

**Asserted**: `tests/golden/api/public_api.json` is modified once more, with its own recorded
justification and enumerated diff (FR-007a) — three permitted golden modifications in this
feature, each named.

**Asserted**: no other golden under `tests/golden/` changes (SC-010a).
