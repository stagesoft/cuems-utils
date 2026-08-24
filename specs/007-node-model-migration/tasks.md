---
description: "Task list for feature 007 — node model migration"
---

# Tasks: Node model migration — the model comes home to its schema

**Input**: Design documents from `/specs/007-node-model-migration/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED by constitution principle II. Every behavioural task has a test that fails
before it and passes after.

**Organization**: grouped by user story. Two structural notes, because this feature is not a
single-repository refactor:

1. **The corpus and its goldens are converted in Phase 2, not in Polish.** The moment
   `network_map.xsd` is edited, every corpus `network_map.xml` becomes invalid against it and the
   suite goes red until they are converted. The conversion is therefore foundational, and this
   *corrects* the ordering in plan.md §Phasing steps 3/8 — see the note at the end of this file.
2. **The conversion script is written in Phase 2, packaged in US3.** The same stdlib script that
   saves a deployed node's `/etc/cuems/network_map.xml` is what converts the test corpus. Writing
   it once and using it in both places is what makes its correctness testable *here* rather than
   only on a node; its `postinst` wiring, the mirror, the tools and the docs stay in US3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1–US6, mapping to spec.md's user stories
- Paths are repository-relative. `../cuems-nodeconf/` and `../cuems-common/` are sibling checkouts.

---

## Phase 1: Setup — capture what is true today, and normalise the corpus

**Purpose**: every later claim in this feature is a comparison against this phase. It runs once,
before any source file changes.

**Why normalisation is here and not later**: the corpus network maps are 4-space indented and
carry two different absolute `xsi:schemaLocation` forms, while the writer emits no indentation and
the bare filename. Measured during cross-artifact analysis — without normalising first, FR-010's
"differs in exactly two ways" asserts a property the writer cannot produce, and the failure would
appear only at the round-trip test with the schema, model and write path all built. The show
corpus is already stored in this normalised form; that is what makes its byte-identity contract
checkable at all.

- [X] T001 Capture the pre-feature goldens by running `pyenv exec python -m tests.support.capture_goldens` (no `--force`) and confirm a clean tree afterwards, in `tests/golden/`
- [X] T002 Record the pre-feature suite figures — passed/skipped/xfailed, wall time, per-test milliseconds — from `hatch test --show` into `specs/007-node-model-migration/baseline.md`
- [X] T003 [P] Record the pre-feature `network_map` load timing (median of 5 runs, `ConfigManager.load_network_map` against `tests/data/network_map.xml`) into `specs/007-node-model-migration/baseline.md`
- [X] T004 [P] Copy the three corpus network maps and `tests/data/network_map.xml` to `specs/007-node-model-migration/pre-state/` as the fixed input for the FR-010 diff assertion
- [X] T005 Demonstrate the FR-026d break on the pre-feature state: import `cuemsnodeconf.NodeXmlBuilders` against the current `cuemsutils` and show the injected handlers are not consulted; record the transcript in `specs/007-node-model-migration/baseline.md`
- [X] T006 [P] Inventory every occurrence of `node_type` and the `NodeType.` prefix across `src/`, `tests/`, `../cuems-nodeconf/`, `../cuems-common/`, `../cuems-engine/src/`, `../cuems-editor/src/` into `specs/007-node-model-migration/migration-guide.md` as the starting symbol table (SC-004a's denominator)
- [X] T006a [P] Inventory every node symbol and every discovery/adoption/orchestration symbol in `../cuems-nodeconf/cuemsnodeconf/` into `specs/007-node-model-migration/migration-guide.md`, as the denominators FR-027 and FR-032 are measured against. Record that the repository root and `tests/` are **excluded by decision** (FR-030a-i) — that code is partially implemented and far from the other repositories' integration maturity, and the migrated node standard and its full testing live in `cuems-utils` exclusively
- [X] T006f [P] Inventory the FR-030a-ii class separately — callers that keep resolving but become **semantically wrong** — across `../cuems-nodeconf/` and the two feature-008 repositories, into `specs/007-node-model-migration/migration-guide.md`. Nothing fails when a member of this class is missed, so it is searched for, not waited for

### Normalising the corpus, before anything else touches it

- [X] T006b Rewrite the four corpus network maps (`tests/data/network_map.xml`, `tests/data/corpus/*/network_map.xml`) to the writer's output form — no indentation, `xsi:schemaLocation` carrying the bare filename — as its own commit (FR-010b, C4a)
- [X] T006c Assert the normalisation changed no element name and no element value, and record the diff in `specs/007-node-model-migration/golden-changes.md` separately from the rename diff (C4a)
- [X] T006d Regenerate the `network_map` goldens for the normalised documents and update `tests/golden/MANIFEST.sha256`, in the same commit as T006b, with the justification recorded (M6)
- [X] T006e Re-take the Phase 1 pre-state copies from the **normalised** documents into `specs/007-node-model-migration/pre-state/`, since that is the basis the FR-010 diff is measured against

**Checkpoint**: the baseline exists, the declared break is proven, and the corpus is stored in the
form the writer produces — so "differs in exactly two ways" is now a property that can hold.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the schema change and everything that must move with it in the same breath. Until
this phase completes the suite is red by construction, so it is not a checkpoint anyone stops at.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

### The interaction that must be proven first

- [X] T007 Write the failing regression test for `strtobool(bool)` — `NetworkMap.get_nodes_by_adoption` handed an already-typed boolean — in `tests/contract/test_adoption_selection.py` (research R7; must fail now)
- [X] T008 Make `NetworkMap.get_nodes_by_adoption` accept `bool` as itself and `str` through `strtobool` in `src/cuemsutils/xml/settings.py`, so T007 passes before any typing lands

### The schema

- [X] T009 Rename `<node_type>` to `<node_role>` **in place** (fourth child of `NodeType`) and retype it `cms:NodeRoleType` in `src/cuemsutils/xml/schemas/network_map.xsd`
- [X] T010 Add the `NodeRoleType` simple type — `xs:string` restricted to `controller`, `node`, `firstrun` — in `src/cuemsutils/xml/schemas/network_map.xsd`
- [X] T011 Add the `UuidType` simple type (canonical 8-4-4-4-12 hex pattern) and retype `<uuid>` with it in `src/cuemsutils/xml/schemas/network_map.xsd`
- [X] T011a Delete the unreferenced `PutType` complex type from `src/cuemsutils/xml/schemas/network_map.xsd` — schema item X9, resolved (FR-029)
- [X] T011b Delete the `PutType` model class from `src/cuemsutils/config/network_map.py` and its binding from `_config_models` in `src/cuemsutils/xml/registry.py`, leaving `project_mappings.xsd`'s separate `PutType` untouched (FR-029)
- [X] T012 Assert no other schema file changed: diff the five other `.xsd` files against `HEAD` in `tests/contract/test_schema_scope.py` (M1, FR-010a)

### The conversion script (written here, packaged in US3)

- [X] T013 [P] Write the stdlib textual conversion script — `<node_type>V</node_type>` → `<node_role>MAPPED</node_role>`, no other byte touched, no `cuemsutils` import — at `../cuems-common/usr/bin/cuems-migrate-network-map`
- [X] T013a [P] Make the script **refuse the whole file** on an unrecognised role value: nothing written, bytes unchanged, a diagnostic naming document, node, value and the accepted values, exit 0 (FR-011h) — in `../cuems-common/usr/bin/cuems-migrate-network-map`
- [X] T013b [P] Make the script write a timestamped backup beside the original before any write, without unbounded accumulation, in `../cuems-common/usr/bin/cuems-migrate-network-map` (FR-011i)
- [X] T013c [P] Make the script emit **positive evidence on success** — nodes converted and backup path — and make all four outcomes (converted / already converted / absent / refused) distinguishable in that record, in `../cuems-common/usr/bin/cuems-migrate-network-map` (FR-011d-i)
- [X] T014 [P] Write the conversion tests — both legacy spellings, absent file, absent element, idempotence, byte-minimality — in `tests/contract/test_network_map_conversion.py` (M3, SC-004b)
- [X] T014a [P] Test the refusal path: an unrecognised value leaves the file byte-identical, emits the naming diagnostic, and exits 0; a map mixing recognised and unrecognised values is refused whole, never half-converted — in `tests/contract/test_network_map_conversion.py` (FR-011h)
- [X] T014b [P] Test that restoring the backup reproduces the pre-conversion bytes exactly, in `tests/contract/test_network_map_conversion.py` (FR-011i, SC-011)
- [X] T014c [P] Test the positive-evidence record: a successful run reports the node count and backup path, and the four outcomes are mutually distinguishable — "already converted" is never silence — in `tests/contract/test_network_map_conversion.py` (FR-011d-i)

### Converting the corpus, deliberately

- [X] T015 Convert `tests/data/network_map.xml` and the three `tests/data/corpus/*/network_map.xml` documents using the script from T013, and record the diff in `specs/007-node-model-migration/golden-changes.md`
- [X] T016 Regenerate the `network_map` goldens with `pyenv exec python -m tests.support.capture_goldens --force` and update `tests/golden/MANIFEST.sha256` in the **same commit**, with the justification in the commit message (M6)
- [X] T017 Assert every changed line in the golden diff is either the rename or the value mapping, and that no other golden under `tests/golden/` changed, in `specs/007-node-model-migration/golden-changes.md` (SC-010a)

### The typed decode

- [X] T018 Create `src/cuemsutils/tools/NodeList.py` and add the `NodeRole` enum there — members `controller`, `node`, `firstrun`, values identical to the schema's facets (FR-002b, data-model §3)
- [X] T019 Bind `ADAPTERS["NodeRoleType"] = _EnumAdapter(NodeRole)` in `_register_enums` in `src/cuemsutils/xml/adapters.py`, importing lazily inside the function as `FadeCurveType` already is, so no import cycle is created (research R10a)
- [X] T020 Declare the per-schema "runs the adapter table" opt-in as data on the registry, set for `network_map` only, in `src/cuemsutils/xml/registry.py` (research R1)
- [X] T021 Honour that declaration in `Mapper.decode_config` — run `adapter_for(field.xsd_type)` on scalar fields when set — in `src/cuemsutils/xml/mapper.py`
- [X] T022 Rewrite the `Mapper.decode_config` docstring: its "no adapters run" paragraph and its `adopted`/`online` worked example are now false for one schema and must say so rather than be discovered, in `src/cuemsutils/xml/mapper.py`
- [X] T023 [P] Rewrite the `ConfigDict.from_decoded` docstring for the same reason, in `src/cuemsutils/config/base.py`
- [X] T024 Rename the model's declared field `node_type` to `node_role` in `node.DECLARED_DEFAULTS` in `src/cuemsutils/config/network_map.py`, and rewrite the module docstring's "two things that do not change" section, which this feature changes both of

**Checkpoint**: `hatch test --show -- tests/unit/test_coherence.py` is green again, the four other
config schemas' goldens are untouched, and the suite is back to the T002 baseline minus the
deliberate changes.

---

## Phase 3: User Story 1 — The node model lives where its schema lives (Priority: P1) 🎯 MVP

**Goal**: node objects with declared fields, typed values, and the identity fields the schema
declares — reachable from the public configuration surface.

**Independent Test**: load each corpus `network_map.xml` through `ConfigManager` and assert every
node is a declared-field object whose field types match the derived adapter table, including
`role_id`/`alias`/`hostname`, with the values the regenerated goldens record.

### Tests for User Story 1 ⚠️

- [X] T025 [P] [US1] Contract test C1 — `NodeRole` member values equal `NodeRoleType`'s `xs:enumeration` facets, read from the loaded schema — in `tests/contract/test_node_role_vocabulary.py`
- [X] T026 [P] [US1] Contract test C2 — node field types match the derived adapter table (`NodeRole`, `bool`, `Uuid`, `str`), and the other four config schemas decode identically to their recorded goldens — in `tests/contract/test_node_typing.py`
- [X] T027 [P] [US1] Contract test C9 — `node.declared_fields()` equals `NodeType`'s derived field names as sets, and no `network_map` type is bound to `GENERIC` — in `tests/contract/test_node_coherence.py`
- [X] T028 [P] [US1] Test that a node is constructible directly from field values, without a document (FR-004), in `tests/unit/test_node_model.py`
- [X] T029 [P] [US1] Test that a document omitting `role_id`/`alias`/`hostname` yields an object without those keys rather than three empty strings, in `tests/unit/test_node_model.py`
- [X] T029a [P] [US1] Contract test C10 — `cuemsutils.config` exports nothing publicly, and `NodeRole`/`NodeIndex` are importable from `cuemsutils.tools.NodeList` — in `tests/contract/test_node_public_path.py` (FR-007)
- [X] T029b [P] [US1] Contract test C11 — `node`, `node_list` and `CuemsNetworkMapType` answer `declared_fields`, `items`, `to_wire`, `to_json`, equality and copy through the inherited implementations, with no node-specific override — in `tests/contract/test_node_public_path.py` (FR-005)

### Implementation for User Story 1

- [X] T030 [US1] Add `NodeIndex` — a mapping of caller-supplied key → `node`, with `by_role(NodeRole)` and a `controllers` convenience — in `src/cuemsutils/tools/NodeList.py` (data-model §3.4)
- [X] T031 [US1] Export `NodeRole`, `NodeIndex` and the public re-export of `node` from `src/cuemsutils/tools/NodeList.py`, and keep `src/cuemsutils/config/__init__.py` exporting nothing publicly (FR-007)
- [X] T032 [US1] Make `NetworkMap.get_node` return a `node` object and raise an unambiguous error when the UUID is absent, in `src/cuemsutils/xml/settings.py` (FR-021)
- [X] T033 [US1] Make `ConfigManager.network_map` and `node_network_map` return node objects and update their docstrings' type claims, in `src/cuemsutils/tools/ConfigManager.py`
- [X] T034 [US1] Add the structural coercion assertion — every free-text field's XSD type resolves to `PASSTHROUGH`, every typed field to its bound adapter — in `tests/contract/test_node_typing.py` (data-model §5)

**Checkpoint**: US1 is independently verifiable — reads produce typed node objects, and nothing
writes yet.

---

## Phase 4: User Story 2 — Node serialization works again, through the one engine (Priority: P1)

**Goal**: a first-party write path for network maps, served by the derived engine, with the
round-trip difference pinned to exactly the declared transformation.

**Independent Test**: load each corpus map, write it back, and assert the diff against the Phase 1
pre-state is exactly the rename plus the value mapping and nothing else.

### Tests for User Story 2 ⚠️

- [X] T035 [P] [US2] Contract test C4 — the round-trip diff **set** against `pre-state/` is exactly the two declared differences, and `<node_type>` appears in zero written documents — in `tests/contract/test_network_map_roundtrip.py`
- [X] T036 [P] [US2] Contract test C5 — a role value outside the enumeration raises before any byte is written and leaves the target exactly as it was, including not existing — in `tests/contract/test_network_map_write.py`
- [X] T037 [P] [US2] Contract test C5 — `save()` does not mutate the object it is given: `node_role` is still a `NodeRole` after the call (FR-015) — in `tests/contract/test_network_map_write.py`
- [X] T038 [P] [US2] Contract test C5 — the write is atomic: a concurrent reader sees the old document or the new one, never a truncated one — in `tests/contract/test_network_map_write.py`
- [X] T039 [P] [US2] D14 chain test — `xml → object → json → object → xml` for network maps, asserting the `node_role` element name and its enumerated value at both ends — in `tests/integration/test_network_map_chain.py` (FR-025)
- [X] T040 [P] [US2] Contract test C7 — no handler class is resolved through a module namespace anywhere in the read or write chain — in `tests/contract/test_no_globals_injection.py` (FR-020)
- [X] T041 [P] [US2] Contract test C8 — a document still carrying `<node_type>` fails with a message naming the migration, and an out-of-vocabulary role names the field and the accepted values — in `tests/contract/test_node_errors.py`
- [X] T041a [P] [US2] Test the operator recovery path: reading a refused map raises the **corresponding named error** carrying document, node, offending value, accepted values and the remedy — and a recognisable legacy value additionally emits a **deprecation notice** naming its replacement, so "old" is distinguishable from "meaningless" — in `tests/contract/test_node_errors.py` (FR-011h-i)

### Implementation for User Story 2

- [X] T042 [US2] Add `CuemsNetworkMapType.save(path)` — validate via `documents.iter_schema_errors`, then write via `documents.write_tree` — in `src/cuemsutils/config/network_map.py` (research R6)
- [X] T043 [US2] Add `ConfigManager.save_network_map()` as the façade form, in `src/cuemsutils/tools/ConfigManager.py`
- [X] T044 [US2] Raise a migration-naming error for a document carrying `<node_type>`, at the configuration accessor where `SchemaError` is already raised, in `src/cuemsutils/tools/ConfigManager.py` and `src/cuemsutils/tools/ConfigBase.py`
- [X] T044a [US2] Give that error the remedy and the deprecation notice FR-011h-i requires — accepted values plus "edit and re-run the conversion", and a replacement-naming notice for a recognisable legacy value — in `src/cuemsutils/errors.py` and the accessors that raise it
- [X] T045 [US2] Delete the dead `CuemsNodeDictXmlBuilder` stub at `src/cuemsutils/xml/XmlBuilder.py:73` and its entry in the module's export list (FR-018)
- [X] T046 [US2] Rewrite `tests/contract/test_declared_break_nodeconf.py` to assert the **repaired** state while still naming FR-026d, so the record of what broke and when it closed survives (FR-019)
- [X] T046a [US2] Assert `cuemsutils` exposes no public means of registering an external builder or parser class, in `tests/contract/test_no_globals_injection.py` (FR-017, C7 — a distinct claim from "the chain consults no module namespace")
- [X] T046b [US2] Update `tests/golden/api/public_api.json` and `tests/golden/MANIFEST.sha256` for the added public surface — `tools/NodeList.py`'s exports and `ConfigManager.save_network_map` — and record the enumerated diff and justification in `specs/007-node-model-migration/api-surface-diff.md` (FR-007a, SC-014). Without this, T031 and T043 fail `test_public_api_surface` and `test_golden_immutability`

**Checkpoint**: node serialization works through the registry; feature 004's declared break is
closed in this repository.

---

## Phase 5: User Story 3 — A deployed node survives the rename (Priority: P1)

**Goal**: an upgrade converts `/etc/cuems/network_map.xml` before anything reads it, and the
`cuems-common` surfaces that name the old field move with it.

**Independent Test**: run the conversion on a pre-rename map, validate against the updated schema,
run it again and assert the bytes are unchanged.

**Repository**: `../cuems-common/`, on its own branch (FR-030b).

### Tests for User Story 3 ⚠️

- [ ] T047 [P] [US3] Test that the packaged conversion handles a `.dpkg-new` / `.dpkg-dist` sibling left by a conffile prompt, in `tests/contract/test_network_map_conversion.py`
- [ ] T048 [P] [US3] Test that an absent, already-converted or unparseable file exits 0 with a diagnostic and never fails the upgrade, in `tests/contract/test_network_map_conversion.py`
- [ ] T049 [P] [US3] Test M2 — `../cuems-common/etc/cuems/network_map.xsd` is byte-identical to `src/cuemsutils/xml/schemas/network_map.xsd` — in `tests/contract/test_schema_mirror.py`
- [ ] T050 [P] [US3] Test that each of the three `cuems-common` tools resolves the controller's IP from a converted map, in `../cuems-common/tests/`

### Implementation for User Story 3

- [ ] T051 [US3] Create the `cuems-common` branch from `rc_1` at `0be3506f22de6ea2dd6d20fbd211febe7b26c710` (FR-030b) and mirror the updated schema to `../cuems-common/etc/cuems/network_map.xsd`
- [ ] T052 [P] [US3] Convert the shipped default map at `../cuems-common/etc/cuems/network_map.xml` so a fresh install never needs converting
- [ ] T053 [US3] Wire the conversion into `../cuems-common/debian/postinst`, after dpkg resolves the conffile, never failing the upgrade — and record its ordering against `dh_installsystemd`'s service restart as **deferred to feature 008** rather than settling it here (FR-011d-ii)
- [ ] T054 [US3] Install the conversion script through `../cuems-common/debian/install`
- [ ] T054a [US3] Add versioned dependencies between the `cuems-common`, `cuems-utils` and `cuems-nodeconf` packages so an out-of-order upgrade is refused rather than merely discouraged, in `../cuems-common/debian/control` and the sibling control files (FR-030d)
- [ ] T054b [US3] Demonstrate the enforcement: attempt the out-of-order upgrade on a test install and record that it is refused, in `specs/007-node-model-migration/migration-guide.md` (SC-012)
- [ ] T054c [US3] Document the restore procedure for a converted map where an operator will look — `../cuems-common/docs/node-identity-contract.md` — and cross-reference it from the migration guide (FR-011i)
- [ ] T055 [P] [US3] Update the controller XPath in `../cuems-common/scripts/cuems-write-chrony-source`
- [ ] T056 [P] [US3] Update the controller XPath in `../cuems-common/scripts/cuems-log-collector-url`
- [ ] T057 [P] [US3] Update the role read and prefix-stripping in `../cuems-common/usr/bin/cuems-logs`
- [ ] T058 [P] [US3] Update the field contract in `../cuems-common/docs/node-identity-contract.md`
- [ ] T059 [P] [US3] Update the `node_type` references in `../cuems-common/CLAUDE.md` and `../cuems-common/README.md`, including the line that lists this migration as pending
- [ ] T060 [US3] Inventory the Avahi service templates' `node_type` TXT record — `etc/avahi/services/cuems.service` and `usr/share/cuems/cuems.service.{master,slave,firstrun}` — and record all four in `specs/007-node-model-migration/migration-guide.md` as **feature 008's work, deliberately unedited here** (Assumption 10, FR-011g), including that `.master`/`.slave` carry the retired vocabulary in their **filenames** and that renaming them reaches `debian/install` and anything resolving a template by name
- [ ] T060a [US3] Record that same four-file list in `specs/007-node-model-migration/migration-guide.md` as SC-004a's **named exclusion**, so the count T092 runs and the files it skips are stated in one place rather than inferred

**Checkpoint**: an upgraded node reads its own map; zero `node_type` occurrences remain in
`cuems-common`.

---

## Phase 6: User Story 4 — The coercion guard becomes first-party (Priority: P2)

**Goal**: the data-integrity guarantee that lived as a copy in another repository becomes a
property of the library that owns the schema — and stops being a denylist.

**Independent Test**: the ported regression suite passes against `cuemsutils`'s own read path with
no import from `cuems-nodeconf`.

### Tests for User Story 4 ⚠️

- [X] T061 [P] [US4] Port the 106-case regression suite to `tests/contract/test_node_field_coercion.py`, stating its field list from the schema; text fields become the six that remain, `adopted`/`online`/`uuid` assertions carry across verbatim (research R4)
- [X] T062 [P] [US4] Test that a node named `none` writes `<name>none</name>` and the document validates, in `tests/contract/test_node_field_coercion.py`
- [X] T063 [P] [US4] Test that `role_id='n'`, `alias='off'` and `hostname='007'` survive a full read → write → read cycle, in `tests/contract/test_node_field_coercion.py`
- [X] T064 [P] [US4] Assert no name-keyed denylist exists anywhere in the package — neither `STRING_TYPED_KEYS` nor `STRING_TYPED_NODE_FIELDS` — in `tests/contract/test_node_field_coercion.py` (C3)

### Implementation for User Story 4

- [X] T065 [US4] Confirm the guarantee needs no implementation — `NonEmptyString` and `xs:string` are unbound in `ADAPTERS`, so `adapter_for` returns `PASSTHROUGH` — and record that finding in `specs/007-node-model-migration/migration-guide.md`, since "the fix is that there is no code" is the outcome a reader will not expect
- [ ] T066 [US4] Delete `../cuems-nodeconf/tests/test_node_field_coercion.py`, whose replacement now lives upstream

**Checkpoint**: F7 is structurally unrepresentable rather than denylisted.

---

## Phase 7: User Story 5 — `cuems-nodeconf` stops owning a model it cannot maintain (Priority: P2)

**Goal**: the source copy is gone and the repository consumes the model from upstream.

**Independent Test**: both source files are absent, no assignment into a `cuemsutils` module
namespace exists, and the repository's own suite is green against the migrated `cuemsutils`.

**Repository**: `../cuems-nodeconf/`, on a new branch from `feat/nodeconf-reenable` at
`0a3ce37ab8dd33501c4817fa57fd8e390732967d` (FR-030a).

### Tests for User Story 5 ⚠️

- [ ] T067 [P] [US5] Test that no node-role enum is defined locally and all usages resolve to the `cuemsutils` definition, in `../cuems-nodeconf/tests/test_node_type.py`
- [ ] T068 [P] [US5] Test that adoption writes a schema-valid map end to end, in `../cuems-nodeconf/tests/test_node_adoption.py` (SC-008)
- [ ] T069 [P] [US5] Test that no assignment into a `cuemsutils` module namespace exists in the sources, in `../cuems-nodeconf/tests/test_no_injection.py`

### Implementation for User Story 5

- [ ] T070 [US5] Create the branch from `feat/nodeconf-reenable` at `0a3ce37` and confirm the FR-026d break reproduces there before changing anything
- [ ] T071 [US5] Delete `../cuems-nodeconf/cuemsnodeconf/CuemsNode.py`
- [ ] T072 [US5] Delete `../cuems-nodeconf/cuemsnodeconf/NodeXmlBuilders.py`, and with it the four globals injections and `STRING_TYPED_NODE_FIELDS`
- [ ] T073 [US5] Remove the duplicate enum from `../cuems-nodeconf/cuemsnodeconf/AvahiTool.py` and import `NodeRole` instead
- [ ] T074 [US5] Reformat `../cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py` onto the upstream model: `NodeIndex` with its MAC key function, `NodeRole` comparisons, and no `CuemsNode`/`CuemsNodeDict` aliases (FR-002a)
- [ ] T075 [US5] Delete the `node_type` normalisation in `read_network_map` — both spellings are gone after conversion — in `../cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py`
- [ ] T076 [US5] Delete the hand-rolled atomic write and the separate serialization copy in `write_network_map`, replacing both with the upstream `save()` — the workaround for in-place mutation is unnecessary once FR-015 holds — in `../cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py`
- [ ] T077 [US5] Retire `XmlReader`/`XmlWriter` in `../cuems-nodeconf/cuemsnodeconf/CuemsNodeConf.py` and `CuemsHwDiscovery.py` for the current public surface (FR-031)
- [ ] T078 [US5] Delete `../cuems-nodeconf/test_xml_roundtrip.py`, whose subject is the injection mechanism that no longer exists
- [ ] T078a [US5] Run the FR-018 orphan search — symbols, modules and tests whose subject is the node model or its serialization with no caller in their own repository and no consumer outside it — across both repositories, and record the result in `specs/007-node-model-migration/migration-guide.md`, stating for each duplicate-named legacy module in `src/cuemsutils/xml/` (`Settings.py`/`settings.py`, `XmlReaderWriter.py`/`xml_reader_writer.py`, `CMLCuemsConverter.py`/`converter.py`, `Parsers.py`, `XmlBuilder.py`) whether it holds node content or none, so "we looked" is distinguishable from "we did not think to look" (FR-018)
- [ ] T078b [US5] Run the FR-032 boundary check: search the migrated surface for discovery, adoption and orchestration symbols against T006a's inventory, and record the count in `specs/007-node-model-migration/migration-guide.md` (SC-013)
- [ ] T079 [US5] Run `../cuems-nodeconf`'s suite green against the migrated `cuemsutils` and record the result in `specs/007-node-model-migration/migration-guide.md`

**Checkpoint**: `cuems-nodeconf` is a plain consumer, like `cuems-engine` and `cuems-editor`.

---

## Phase 8: User Story 6 — Adopted-node selection stops mutating its input (Priority: P3)

**Goal**: give `cuems-engine` a non-mutating answer to reach for, so its inline workaround can go
in feature 008.

**Independent Test**: call the replacement on a loaded map and assert the map's values are
identical before and after, while the returned partition is correct.

### Tests for User Story 6 ⚠️

- [X] T080 [P] [US6] Contract test C6 — every node value is equal field by field before and after `partition_by_adoption`, in `tests/contract/test_adoption_selection.py`
- [X] T081 [P] [US6] Test the partition for maps whose `adopted` is `True`, `False` and absent, in `tests/contract/test_adoption_selection.py`

### Implementation for User Story 6

- [X] T082 [US6] Add `NetworkMap.partition_by_adoption(map)` returning `(adopted, unadopted)` as tuples of node objects, mutating nothing, in `src/cuemsutils/xml/settings.py`
- [X] T083 [US6] Deprecate `get_nodes_by_adoption` with a message pointing at the replacement, keeping it working until feature 008 migrates its caller (Assumption 8), in `src/cuemsutils/xml/settings.py`

**Checkpoint**: all six stories are independently functional.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [X] T083a Enumerate the migration guide's required contents in **one** section of `specs/007-node-model-migration/migration-guide.md`, and make the requirements that feed it cross-reference that enumeration rather than each restating an obligation (FR-027a)
- [X] T084 Complete the moved-symbol table in `specs/007-node-model-migration/migration-guide.md` — source → new home → status → **authorising requirement** — measured against T006a's inventory so completeness has a denominator (FR-027, SC-007). A row whose movement no requirement authorises is recorded as a finding, not given a blank cell
- [X] T084a Record the public import path `cuemsutils.tools.NodeList` in the guide's consumer section, with the warning that `cuemsutils.config` is internal (FR-007)
- [X] T085 Add to the migration guide what `cuems-engine` must change in feature 008 — `CONTROLLER_NETWORK_FLAG` and its two comparison sites, the `network_map` reads, the `get_nodes_by_adoption` workaround — verified against each live call site rather than transcribed (FR-011g, FR-028)
- [X] T086 Add to the migration guide what `cuems-editor` must change — the node field list at `CuemsWsServer.py:425` and the `reload_network_map_nodes` reads — verified against the live call sites (FR-011g, FR-028)
- [X] T087 State the release gate in `specs/007-node-model-migration/migration-guide.md` as a gate: the four-step ordering, why nothing ships before feature 008, the failure mode of getting it wrong, and the package dependencies that enforce it (FR-030c, FR-030d, M5)
- [X] T087a Extend that gate to the **cluster**: state whether a staged rollout is supported and, if not, that the cluster upgrades as a unit — FR-030d enforces ordering within one machine, and a controller upgraded ahead of its nodes is a disagreement no package dependency can see (FR-030c)
- [X] T087b Record in the guide that **downgrade is unsupported** and that restoring the FR-011i backup is the only path back — no reverse conversion is provided (FR-011i)
- [X] T088 [P] Record schema item X9 as **resolved** — `PutType` deleted from schema, model and registry — with its rationale, in `specs/007-node-model-migration/migration-guide.md` (FR-029)
- [X] T089 [P] Extend `specs/planning/schema-evolution-convention.md` with the three precedents this feature set — renaming, constraining and deleting — each with the migration pattern it used; the convention today covers only additive change (FR-029)
- [X] T090 [P] Update `CLAUDE.md`'s Recent Changes with feature 007's landed facts, including the single-schema typing exception and the relaxed-once D3
- [X] T091 Re-measure the `network_map` load timing and the suite per-test figure, and record **both** against their budgets in `specs/007-node-model-migration/baseline.md` whether or not they pass (FR-PERF-001, SC-009)
- [X] T092 Verify SC-004a by re-running T006's inventory: zero `node_type` and zero `NodeType.` occurrences across the three edited repositories' code, schemas, shipped files and documentation, **excluding the four Avahi discovery files T060 names**. The exclusion is applied as that explicit file list, never as a pattern that could silently swallow a fifth file
- [X] T092a Run the project's lint and type gates and confirm no new warnings; review every public symbol added for the rationale documentation the surrounding modules carry (SC-QUALITY-001)
- [X] T092b Record which tests were observed failing before their implementation, in `specs/007-node-model-migration/baseline.md`, so fail-before-pass is evidenced rather than claimed (SC-TEST-001)
- [X] T093 Confirm the editor↔UI `project_load` payload is untouched by showing the show-document goldens are byte-identical (FR-033, SC-010a)
- [X] T094 Run `specs/007-node-model-migration/quickstart.md` end to end and correct anything that does not reproduce

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies. Must complete before any source change, or the baseline is meaningless.
- **Phase 2 (Foundational)**: depends on Phase 1. **Blocks every user story.** The suite is red inside this phase by construction — T009 invalidates the corpus and T015/T016 restore it.
- **Phase 3–8 (Stories)**: all depend on Phase 2.
- **Phase 9 (Polish)**: depends on all stories.

### Story dependencies

- **US1 (P1)**: after Phase 2. No dependency on another story.
- **US2 (P1)**: after Phase 2. Uses US1's model but is testable on its own — a write path can be exercised against objects built directly.
- **US3 (P1)**: after Phase 2 only. It is a different repository and depends on the schema, not on US1 or US2. **Fully parallel with them.**
- **US4 (P2)**: after Phase 2. Its evidence is the derived table, which Phase 2 lands.
- **US5 (P2)**: after **US1 and US2** — `cuems-nodeconf` cannot consume a model and a write path that do not exist yet. This is the one genuine cross-story dependency.
- **US6 (P3)**: after Phase 2. Independent; T007/T008 already touched the same file, so it is sequential with them, not parallel.

### Within each story

Tests before implementation, and they must fail first. T007 before T009 is the sharpest case: the
`strtobool(bool)` interaction is proven on the pre-typing state or it is not proven at all.

### Parallel opportunities

- T003, T004, T006 in Phase 1.
- T013 and T014 with T009–T012 in Phase 2 (different repositories, different files).
- All of US1's tests (T025–T029); all of US2's tests (T035–T041); all of US4's tests (T061–T064).
- **US3 in full, alongside US1 and US2** — a second person can take `cuems-common` from the moment the schema lands.
- T055–T059 within US3.
- T088, T089, T090 in Polish.

---

## Parallel Example: User Story 2

```bash
# All seven US2 tests can be written together — different files, no shared state:
Task: "C4 round-trip diff set in tests/contract/test_network_map_roundtrip.py"
Task: "C5 validate-before-write in tests/contract/test_network_map_write.py"
Task: "C5 non-mutation in tests/contract/test_network_map_write.py"
Task: "C5 atomicity in tests/contract/test_network_map_write.py"
Task: "D14 chain in tests/integration/test_network_map_chain.py"
Task: "C7 no globals injection in tests/contract/test_no_globals_injection.py"
Task: "C8 error messages in tests/contract/test_node_errors.py"
```

---

## Implementation Strategy

### MVP

Phase 1 → Phase 2 → **US1**. At that point the node model lives in `cuemsutils`, reads produce
typed objects, and the schema and the model agree — the feature's title is true, even though
nothing writes yet.

### Incremental delivery

1. Setup + Foundational → the schema has moved and the corpus is converted.
2. **US1** → typed node objects from the public surface. *MVP.*
3. **US2** → serialization works again; feature 004's break is closed here.
4. **US3** → deployed nodes survive. Can run in parallel with 2 and 3.
5. **US4** → the guard is first-party.
6. **US5** → the source copy is deleted; two copies of the model stop existing.
7. **US6** → the non-mutating selection.
8. Polish → migration guide, budgets, the release gate.

**Nothing is released at any of these points.** The gate is feature 008 (FR-030c); "deploy/demo"
does not apply to this feature and the checkpoints are validation points only.

### Parallel team strategy

Two people: one takes `cuems-utils` (US1, US2, US4, US6), the other takes `cuems-common` (US3)
from the moment T009–T011 land, then `cuems-nodeconf` (US5) once US2 is done.

---

## Note: a correction to plan.md's phasing

plan.md §Phasing puts the schema edit at step 3 and the golden regeneration at step 8, on the
principle that goldens are never regenerated to make a test pass. Mapping the tasks showed that
ordering cannot hold: `tests/data/corpus/*/network_map.xml` all carry `<node_type>`, so the moment
step 3 lands they fail validation and the suite is red through steps 4–7.

The resolution keeps the principle intact rather than waiving it. The corpus documents are
converted by the **conversion script** (T013), which is a deliverable with its own tests (T014)
and is not the code under test — so the goldens are regenerated by a tool whose correctness is
established independently, never to make a failing assertion pass. Steps 3 and 8 of plan.md are
therefore one foundational block, T009–T017, and the FR-010 diff is measured against the Phase 1
`pre-state/` copy rather than against the working tree.
