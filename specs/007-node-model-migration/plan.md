# Implementation Plan: Node model migration — the model comes home to its schema

**Branch**: `007-node-model-migration` | **Date**: 2026-08-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/007-node-model-migration/spec.md`

---

## Summary

Move the node object model and its serializers into `cuemsutils` from `cuems-nodeconf`, and while
the schema is open, complete the migration `cuems-common` already had scheduled: `<node_type>`
typed as free text becomes `<node_role>` typed as a real enumeration over `controller` / `node` /
`firstrun`.

The technical approach, in one line each:

- **The model is already half here.** Feature 006 created `cuemsutils/config/network_map.py` with
  `node`, `node_list`, `PutType` and `CuemsNetworkMapType` as declared-field containers, including
  the three identity fields the `cuems-nodeconf` model omits, and reserved the behaviour for this
  feature by name. This feature adds behaviour to landed containers and deletes the other copy.
- **Typing comes from the schema, once.** Two adapter bindings (`NodeRoleType` → an enum adapter,
  `UuidType` → the existing UUID adapter) plus a per-schema opt-in to running the adapter table,
  and `node_role`/`adopted`/`online`/`uuid` are typed while free text is left alone *because no
  codec is bound to its type*. The 106-case regression test stops testing a denylist and starts
  testing a property of the schema.
- **The write path is small because the machinery is generic.** `documents.build_tree`,
  `iter_schema_errors` and `write_tree` already take a schema name and already write atomically;
  `CuemsNetworkMapType.save()` is a façade over them, and `cuems-nodeconf`'s hand-rolled atomic
  write is deleted rather than ported.
- **Deployed nodes are converted, not tolerated.** A stdlib textual rewrite shipped by
  `cuems-common` and run from `postinst`, idempotent by inspection, touching no byte outside the
  matched element.

Three repositories are edited: `cuems-utils`, `cuems-nodeconf`, `cuems-common`. Nothing releases
until feature 009 migrates the readers.

---

## Technical Context

**Language/Version**: Python 3.11+. Tests run under **pyenv 3.11.9**; conda is not used for this
project.
**Primary Dependencies**: `xmlschema==3.4.3` (pinned — XSD 1.1 is required by `xs:assert` in
`script.xsd`). `lxml==6.1.0` is present but **not** in the XML write path; the writer is stdlib
`ElementTree`. The `cuems-common` conversion script is **stdlib only**, by the shared-venv rule.
**Storage**: XML documents on disk. `/etc/cuems/network_map.xml` (a dpkg conffile, rewritten in
place by `cuems-nodeconf` on every adoption) and its schema mirror `/etc/cuems/network_map.xsd`.
**Testing**: `hatch test --show`; pytest with a frozen corpus under `tests/data/corpus/` and
recorded goldens under `tests/golden/` pinned by `MANIFEST.sha256`.
**Target Platform**: Debian bookworm nodes; the shared venv at `/usr/lib/cuems`.
**Project Type**: shared Python library (`cuemsutils` on PyPI) plus a coordinated change in two
sibling repositories.
**Performance Goals**: network-map load within 110% of the pre-feature measurement; suite
per-test figure within 110% of the feature 006 baseline (~27 ms/test, 2222 passed / 94 skipped /
2 xfailed in ~59 s).
**Constraints**: `network_map` round trip differs from its input in exactly two ways (element
rename, value mapping) and in no other byte; the other five schemas keep full byte identity; the
editor↔UI `project_load` payload is untouched by this feature and must be shown to be so.
**Scale/Scope**: ~200 LOC moved in; one schema edited; ~10 fields; three corpus documents; three
repositories; three `cuems-common` tools; one `postinst` hook.

**Unresolved**: none. All five spec clarifications are answered and every Phase 0 unknown is
resolved in [research.md](research.md).

### Standing decisions this plan operates under

D1, D2, D5, D9, D11, D12, D13, D14, D15, Q11→(c), Q14→(i) — unchanged.

**D3 is relaxed exactly once, by recorded decision.** "Wire-compatible with every XML on disk; no
`.xsd` edits" continues to bind the other five schemas (FR-010a, SC-010a). For `network_map.xsd`
it is lifted; the `/speckit.plan` invocation restated D3 from the shared context block *and* asked
in its own technical context for the XSD to be changed so `node_role` is `NodeRoleType`. The
clarification session settled that conflict in favour of the change, and this plan follows the
clarification.

---

## Constitution Check

*GATE: evaluated before Phase 0 and re-evaluated after Phase 1. Result: **PASS**, with one
justified deviation recorded under Complexity Tracking.*

### I. Code Quality By Default

- No new lint or type warnings (SC-QUALITY-001). The package's existing gates apply unchanged.
- Every public symbol added — `NodeRole`, `NodeIndex`, `save()`, `partition_by_adoption` — carries
  the rationale documentation the surrounding modules already carry. `config/network_map.py` sets
  a high bar for that and this feature extends the same file.
- Two docstrings state facts this feature **overturns** and must be rewritten rather than left:
  `Mapper.decode_config` ("no adapters run", with `adopted`/`online` as its worked example) and
  `ConfigDict.from_decoded`. Leaving a superseded rationale in place is a quality defect of the
  kind this repository's review has consistently caught.
- Net deletion: two `cuems-nodeconf` source files, one dead stub, one hand-rolled atomic write,
  one duplicated enum, one name-keyed denylist.

### II. Tests As A Release Gate

Fail-before-pass is achievable for every behavioural requirement, and three cases are worth naming
because their failure modes are silent:

| Test | Fails before because |
|---|---|
| Coherence (`test_coherence.py`, existing) | the model still says `node_type` after the schema says `node_role` |
| `strtobool(bool)` regression (C6) | written *before* typing lands; proves the interaction research R7 measured |
| FR-026d repair (`test_declared_break_nodeconf.py`, rewritten) | the pre-feature state has no working node write path |
| Conversion idempotence (M3) | no conversion script exists |

Ported: the 106-case coercion regression suite, restated against the derived adapter table
(research R4). Added: the D14 chain test for `network_map`
(`xml → object → json → object → xml`), the FR-010 diff test, the conversion tests, and the
schema/enum agreement test.

Existing suite: 2222 passed / 94 skipped / 2 xfailed must stay green, minus the deliberate
changes enumerated in the migration guide.

### III. Consistent User Experience

- **Error messages** follow the configuration accessors' existing conventions: `SchemaError` from
  the accessor, naming document, node and field (FR-UX-001, C8). A legacy `<node_type>` document
  must fail with a message that names the migration — the single most likely thing an operator
  will hit.
- **Naming** follows the ecosystem's stated direction rather than inventing one:
  `cuems-common/CLAUDE.md` already mandates controller/node for new fields, and `role_id` already
  uses `controller`/`nodeNN`.
- **Node objects replace raw dicts** for engine and editor, documented in the migration guide with
  every changed name and type against its call site (FR-023, FR-028).
- The retired `masters`/`slaves` selection names are not silently dropped: they name a vocabulary
  that no longer exists, and the guide says what replaces them.

### IV. Performance Budgets Are Requirements

- Network-map load: ≤ 110% of the pre-feature measurement, same corpus and machine.
- Suite per-test: ≤ 110% of the feature 006 baseline.
- Both measured before any code changes (quickstart §1) and recorded in `baseline.md` **whether or
  not they pass** — feature 006 recorded its wall-time budget as exceeded rather than restating it
  as passing, and that convention holds.
- Expected direction: decoding `network_map` now runs the adapter table where it previously did
  not, which adds work on a document with ~10 fields per node. The budget exists to catch that
  being wrong by an order of magnitude, not to forbid it.

---

## Project Structure

### Documentation (this feature)

```text
specs/007-node-model-migration/
├── plan.md                      # This file
├── research.md                  # Phase 0 — R1..R12, all unknowns resolved
├── data-model.md                # Phase 1 — schema delta, adapters, Python model
├── quickstart.md                # Phase 1 — how to run and verify by hand
├── contracts/
│   ├── node-api.md              # C1..C9 — the surface cuemsutils exposes
│   └── schema-migration.md      # M1..M6 — schema, conversion, tools, release gate
├── checklists/
│   └── requirements.md          # spec quality checklist (all items pass)
├── baseline.md                  # written by the first task, before any code change
├── migration-guide.md           # written by this feature, consumed by 009
└── tasks.md                     # /speckit.tasks output — NOT created by /speckit.plan
```

### Source code

```text
# ---- cuems-utils (this repository) -------------------------------------
src/cuemsutils/
├── config/                      # INTERNAL — exports nothing publicly (FR-007)
│   ├── __init__.py
│   └── network_map.py           # schema-bound containers; PutType deleted (X9)
├── xml/
│   ├── schemas/network_map.xsd  # node_role + NodeRoleType + UuidType; PutType deleted
│   ├── adapters.py              # +2 bindings; _register_enums gains NodeRole
│   ├── registry.py              # per-schema "runs adapters" declaration
│   ├── mapper.py                # decode_config honours it; docstring rewritten
│   ├── settings.py              # NetworkMap: node objects, non-mutating partition
│   ├── documents.py             # unchanged — already schema-generic
│   └── XmlBuilder.py            # CuemsNodeDictXmlBuilder deleted
└── tools/
    ├── NodeList.py              # NEW, PUBLIC — NodeRole, NodeIndex, the ported classes
    └── ConfigManager.py         # save_network_map()

tests/
├── contract/                    # C1..C9; test_declared_break_nodeconf.py rewritten
├── unit/test_coherence.py       # already covers network_map — must go green again
├── integration/                 # D14 chain test for network_map
├── data/corpus/                 # three network maps, regenerated
└── golden/                      # network_map goldens + MANIFEST.sha256, once

# ---- cuems-nodeconf (branch from feat/nodeconf-reenable @ 0a3ce37) ------
cuemsnodeconf/
├── CuemsNode.py                 # DELETED
├── NodeXmlBuilders.py           # DELETED
├── CuemsNodeConf.py             # imports upstream; hand-rolled atomic write removed;
│                                #   node_type normalisation removed; XmlReader/Writer retired
├── AvahiTool.py                 # duplicate enum removed
└── tests/test_node_field_coercion.py   # MOVES to cuems-utils

# ---- cuems-common (own branch) -----------------------------------------
etc/cuems/network_map.xsd        # mirror, byte-identical to the package copy
etc/cuems/network_map.xml        # shipped default, new format
usr/bin/cuems-migrate-network-map # NEW — stdlib textual rewrite
debian/postinst                  # invokes it, conffile-aware
scripts/cuems-write-chrony-source, scripts/cuems-log-collector-url, usr/bin/cuems-logs
docs/node-identity-contract.md, CLAUDE.md, README.md
```

**Structure Decision**: single-library layout, unchanged, and the node code is **split across two
existing packages** rather than given a new one.

The schema-bound containers stay in `cuemsutils/config/`, created by feature 006 for precisely
this per target design §10, which remains **internal** — `cuemsutils.xml` exports nothing after
006 and `config/` joins it on that side of Q14→(i). The classes ported from `cuems-nodeconf`
(`NodeRole`, `NodeIndex`) land in a new `cuemsutils/tools/NodeList.py`, beside `ConfigBase` and
`ConfigManager`, which D15 already names as the public configuration façade.

One direction of that split is **forced**: `xml/registry.py` imports `config/network_map.py` and
`tools/ConfigManager.py` imports `xml/`, so a `config → tools` import closes a cycle. The
schema-bound classes must therefore stay where the registry reaches them, and `tools/NodeList.py`
imports downward. `NodeRole` is defined in `tools/` and `config/` does not import it — the enum
reaches the model through the adapter, registered lazily exactly as `FadeCurveType` already is.

The two sibling repositories are edited on their own branches (FR-030a, FR-030b) and are not
vendored here.

---

## Phasing

Ordered so that each step is independently green and the measurement always precedes the change it
judges.

| # | Step | Gate |
|---|---|---|
| 1 | Capture pre-state: goldens, suite figures, network-map load timing; **verify the FR-026d break exists** | `baseline.md` written; break demonstrated |
| 1b | **Normalise the corpus network maps** to the writer's output form, as its own reviewable change | C4a; no element name or value altered |
| 2 | `strtobool(bool)` regression test + fix, before typing lands | fails, then passes (C6) |
| 3 | Schema edit: `node_role`, `NodeRoleType`, `UuidType`, `PutType` deleted — **together with** the conversion script, the corpus conversion and the golden regeneration, as one block | only `network_map.xsd` differs; corpus valid again |
| 4 | `NodeRole` + adapter bindings + per-schema adapter opt-in; rewrite the two superseded docstrings | coherence green; other four schemas' goldens unchanged (C2) |
| 5 | Model behaviour: `NodeIndex`, direct construction, `NetworkMap` returns node objects, non-mutating partition | C1, C2, C3, C6 |
| 6 | Write path: `CuemsNetworkMapType.save`, `ConfigManager.save_network_map` | C4, C5 |
| 7 | Port the 106-case suite; add the D14 chain test; rewrite `test_declared_break_nodeconf.py`; delete `CuemsNodeDictXmlBuilder` | C3, C7 |
| 8 | *(folded into step 3 — see the note at the end of `tasks.md`)* | M6, SC-010a |
| 9 | `cuems-nodeconf` branch: delete both files, reformat call sites, retire deprecated entry points | its suite green (SC-008) |
| 10 | `cuems-common` branch: mirror, default map, conversion + postinst, three tools, documentation | M2, M3, M4 |
| 11 | `migration-guide.md`: moved-symbol table, consumer changes for 009, **the release gate** | FR-027, FR-028, M5 |
| 12 | Re-measure budgets; record both figures | FR-PERF-001 |

Step 2 before step 3 is deliberate: the `strtobool(bool)` interaction is the one place where two
requirements of this feature collide, and it is proven rather than assumed.

**Step 8 was originally scheduled after step 7 and has been folded into step 3.** Task mapping
showed the original ordering could not hold: every corpus `network_map.xml` carries `<node_type>`,
so the schema edit invalidates them and the suite stays red until they are converted. The
principle it protected — goldens are never regenerated to make a test pass — is kept by having the
**conversion script** do the converting: it is a deliverable with its own tests, not the code under
test, and the FR-010 diff is measured against a pre-state copy taken in step 1. Full reasoning in
the note at the end of `tasks.md`.

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|--------------------------------------|
| A per-schema exception to feature 006's "config decoding runs no adapters" rule | FR-011a requires typed node values; FR-011a-i requires the other four schemas untouched. The exception is declared as data on the registry, next to the type bindings | Typing **all** config schemas would change `settings`, `project_mappings` and `project_settings` goldens and their consumers — scope this feature does not claim, arriving through a base class rather than through a decision. Leaving `network_map` untyped would leave the role as a bare string, which is the accident being removed |
| Editing three repositories in one feature | The hard cutover has no working partially-deployed state: schema, writer and shipped mirror must move together, or a node's `/etc/cuems/network_map.xml` becomes unreadable | Splitting `cuems-common` into feature 009 would leave the conversion — the thing that saves a deployed node's cluster topology — behind the release that invalidates its file |

Neither deviates from a constitutional principle; both are recorded because they widen the blast
radius beyond a single-repository refactor and a reviewer should meet them here rather than in a
diff.

---

## Risks

| Risk | Mitigation |
|---|---|
| A node upgrades and its map is never converted | M3's postinst hook plus conffile handling; C8 makes the resulting failure name the migration instead of being cryptic |
| Typing leaks into the other four config schemas | SC-010a compares their goldens; the opt-in is per schema and declared, not inferred |
| The round-trip diff quietly grows beyond two differences | C4 asserts the diff **set**, not merely that it round-trips |
| `Uuid` rejects a real node's UUID | `_UuidAdapter` keeps unparseable values as raw text; the XSD pattern constrains shape, not uuid4 semantics (research R2) |
| Goldens regenerated to make a test pass | `MANIFEST.sha256` + the recorded-justification ceremony (M6) |
| Someone releases `cuems-utils` between 007 and 009 | FR-030c states the gate; FR-030d enforces it with versioned package dependencies, since a documented gate is not one |
| A node's map is rewritten with no recoverable prior version | FR-011i requires a timestamped backup and a documented restore before any write |
| The round-trip diff is unachievable because the corpus is stored in a form the writer never emits | Caught at analysis, not at test time: step 1b normalises the corpus first (FR-010b, C4a) |
| Public surface grows without the API snapshot noticing | FR-007a makes the golden update a named, justified modification rather than an oversight |
| `cuems-nodeconf`'s re-keying of `NodeIndex` changes silently | The key function is caller-supplied, not hard-coded (research R5) |
