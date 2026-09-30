<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Tasks: uuid4 convergence

**Input**: Design documents from `/specs/012-uuid4-convergence/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED by the constitution (Principle II). Every behaviour change has a test that
fails before the implementation and passes after it.

**Organization**: grouped by user story. Phases run in priority order, which here is **also** the
correct dependency order — US3 is P3 *and* must land last.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable — different files, no dependency on an incomplete task
- **[Story]**: US1–US5, on user-story phases only

## Path Conventions

Single project: `src/cuemsutils/`, `tests/` at repository root.

## Run the suite

```bash
PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q
```

`hatch` is not installed on this box and the `hatch test` env lacks `hypothesis` — see
[quickstart.md](quickstart.md).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: the fixtures every later phase measures against.

- [ ] T001 Create a fixture-cluster builder in `tests/support/cluster_fixture.py` — writes a
      configuration directory (`settings.xml`, `network_map.xml`, `default_mappings.xml`) plus a
      library with `projects/<name>/{mappings.xml,<script>}` and a mirrored `trash/projects/`,
      parameterised by node count, identity shape per node, and script filename
- [ ] T002 [P] Create the named performance fixture **`remint_200`** in
      `tests/support/library_fixture.py` — a generator parameterised by project count and node
      count, with `remint_200` fixed at **200 projects, ~4 MB** (research R8). This is the fixture
      SC-PERF-001's wall-clock ceiling names, so its scale is part of the budget, not a detail
- [ ] T003 [P] Record the pre-change suite baseline **as a range** in
      `specs/012-uuid4-convergence/baseline.md`, over at least three runs, noting the
      `test_descriptor_laziness` skip-count drift so a later comparison is not read as a regression

**Checkpoint**: fixtures exist; nothing in `src/` has changed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: the vocabulary and the two primitives that both the check and the re-mint need.

**⚠️ CRITICAL**: no user story work can begin until this phase is complete.

- [ ] T004 Create `src/cuemsutils/tools/ids.py` with the identity classification vocabulary —
      `converged` / `not-converged` / `not-provisioned` / `unrecognised` per data-model §1.3 — and
      **two separately named definitions**, the converged pattern and the sentinel, plus the
      `admitted` union of them (data-model §1.2, FR-021c). `converged` means uuid4 lowercase and
      **only** that: the sentinel is admitted, never converged, and §1.3's classification, §6.1's
      decode table and the published coercion rule all depend on the two staying distinct
- [ ] T005 [P] Test the classification in `tests/unit/test_identity_classification.py` — uuid4,
      uuid1, uuid5, upper-case uuid4, the sentinel, and a non-uuid string each land in exactly one
      class; the sentinel is **not** classified as `not-converged`
- [ ] T006 Implement the token scanner in `src/cuemsutils/tools/ids.py` — finds every
      36-character uuid token in a file's bytes, reporting whether each was the whole value of an
      element or **embedded** in a compound string
- [ ] T007 [P] Test the scanner in `tests/unit/test_token_scanner.py` — bare elements, compound
      `<uuid>_<output>` values, `<uuid>_custom_<n>`, the three `default_*_output` forms, and a
      file with no tokens at all
- [ ] T008 Implement library-reach resolution in `src/cuemsutils/tools/library_reach.py` —
      `library_path` from `settings.xml`, enumerating `projects/*/` and `trash/projects/*/`, with
      scripts identified **by root element, not filename** (research R3) and `mappings.xml`
      treated as optional per project
- [ ] T009 [P] Test the reach in `tests/unit/test_library_reach.py` — a script named
      `script.xml`, one named `cue_script.xml`, one named neither, a project with no mappings, a
      non-script `.xml` in a project directory that is **not** selected, and `trash/` included

**Checkpoint**: classification, scanning and reach are available to every story.

---

## Phase 3: User Story 1 — the read-only check (Priority: P1) 🎯 MVP

**Goal**: an operator learns whether a machine needs the migration, without risk.

**Independent Test**: point the check at a tree containing a uuid1, a uuid5, a uuid4 and the
sentinel; every occurrence is classified correctly with its document and path, the exit status
distinguishes "migration needed" from "already converged", and every file's bytes and
modification time are unchanged.

### Tests for User Story 1

- [ ] T010 [P] [US1] Contract test in `tests/contract/test_check_writes_nothing.py` — after a run
      over a fixture cluster, assert **no** file created, modified, moved or deleted, comparing
      both content hashes and modification times, and that no backup appeared (FR-003, **SC-005**'s
      zero-files half)
- [ ] T011 [P] [US1] Test in `tests/integration/test_check_classifies.py` — a mixed tree reports
      each occurrence with path, location, value and class, including occurrences embedded in
      compound strings (FR-001, FR-002, **SC-005**'s 100%-classification half)
- [ ] T012 [P] [US1] Test in `tests/contract/test_check_exit_classes.py` — 0 converged,
      1 migration-needed **and** 1 mirror-disagreement, 2 absent/unreadable, 3 sentinel; and that
      precedence 3 > 2 > 1 still holds (FR-004, contracts/cli-check.md)
- [ ] T013 [P] [US1] Test in `tests/integration/test_check_degrades.py` — an absent, unreadable or
      library-path-less `settings.xml` degrades to a configuration-only survey that **says so**,
      and an unrecognised document is named while the survey continues (FR-005, research R9)
- [ ] T014 [P] [US1] Test in `tests/integration/test_check_on_invalid_documents.py` — the check
      runs on documents the tightened schema would refuse, proving it never routes through the
      validating load path (**FR-001a**, which is satisfied by design rather than by a dedicated
      test; this is the test that observes the design holding)

### Implementation for User Story 1

- [ ] T015 [US1] Extend `src/cuemsutils/tools/identity_check.py` with shape classification, using
      Phase 2's vocabulary — every identity it already reads gains a class
- [ ] T016 [US1] Extend `identity_check.py`'s reach to the project library via
      `tools/library_reach.py`, reading with stdlib XML only
- [ ] T017 [US1] Widen the exit classes in `identity_check.py` — 1 now also means
      "migration needed"; add the `verdict` field that distinguishes it, per contracts/cli-check.md
- [ ] T018 [US1] Extend the `--json` output shape in `identity_check.py` with per-occurrence
      `location`, `classification` and `embedded`, per data-model §3
- [ ] T018a [US1] Extend the **existing** `tests/contract/test_identity_check.py` for the widened
      class 1 and the extended verdict vocabulary — it asserts `verdict == "mismatch"` and the
      current exit-class meanings today, and T017/T018 change both. Extend it in step rather than
      leaving it to pass while testing the superseded vocabulary (Principle III: the vocabulary is
      extended, not replaced, so every shipped verdict must still mean what it meant)
- [ ] T019 [US1] Add `--library` to the check in `src/cuemsutils/tools/init_node.py`'s parser and
      thread it through, defaulting to the configured library path

**Checkpoint**: US1 is independently shippable. It writes nothing and needs no other phase.

---

## Phase 4: User Story 2 — the cluster re-mint (Priority: P2)

**Goal**: every node identity converges, everywhere it was written, in one resumable operation.

**Independent Test**: on a fixture cluster with a project library carrying compound output names,
after the re-mint no old identity token survives anywhere, every touched document validates,
adoption state per node is unchanged, and a second run rewrites nothing.

### Tests for User Story 2

- [ ] T020 [P] [US2] Test the table's invariants in `tests/unit/test_substitution_table.py` —
      every new value is uuid4 minted through the library's only minter (**FR-006**), all distinct,
      no new value appears as an old one, an already-converged node has no entry, keys built from
      node identities only (**FR-010**, data-model §2.1)
- [ ] T021 [P] [US2] Test in `tests/integration/test_remint_persists_first.py` — the table exists
      on disk **before** the first document is written (FR-007)
- [ ] T022 [P] [US2] Test in `tests/integration/test_remint_resume.py` — interrupted after some
      files, a re-run loads the table rather than rebuilding it and no node receives a second new
      identity (FR-008, **SC-006**, data-model §2.2). Also assert the refusal rule in the direction
      data-model §2.2a and contracts/cli-remint.md state it: a table whose `controller` is not
      **this node** is accepted, and only one whose `controller` is not **the map's** controller is
      refused
- [ ] T023 [P] [US2] Test in `tests/integration/test_remint_idempotent.py` — a second run over a
      converged cluster substitutes nothing and changes zero bytes in zero files (FR-013, **SC-004**)
- [ ] T024 [P] [US2] Test in `tests/integration/test_remint_compound.py` — `<output_name>` values
      of the form `<old>_<output>` carry the new identity with the rest of the value byte-identical,
      and every other byte in the file is unchanged (FR-009)
- [ ] T025 [P] [US2] Test in `tests/integration/test_remint_collision_aborts.py` — two nodes
      sharing an identity: the run aborts, names both rows **with their MACs** and every script
      referencing the token, and **no file is modified** (FR-019)
- [ ] T026 [P] [US2] Test in `tests/integration/test_remint_leaves_converged.py` — a node already
      carrying a valid uuid4 is untouched and no file mentioning only that node is rewritten (FR-014)
- [ ] T027 [P] [US2] Test in `tests/integration/test_remint_exhaustive.py` — after a run, a
      recursive search for every old token over the configuration directory and the whole library
      returns nothing (FR-016, SC-001)
- [ ] T028 [P] [US2] Test in `tests/integration/test_remint_preserves_adoption.py` — `adopted` and
      `online` per node are identical before and after (FR-018, SC-003)
- [ ] T029 [P] [US2] Test in `tests/integration/test_remint_reach.py` — scripts under any filename,
      optional per-project `mappings.xml`, and `trash/projects/` are all rewritten (FR-011, FR-012)
- [ ] T029a [P] [US2] Test in `tests/integration/test_remint_documents_valid.py` — after a run,
      **every touched document validates against its schema** and a **full load succeeds for each
      node** (FR-017, SC-002). Distinct from T027, which proves only that no old token survives:
      a file can be token-free and still unloadable
- [ ] T029b [P] [US2] Test in `tests/integration/test_remint_mtime_advances.py` — every rewritten
      library file is **the same size** as before and its **modification time is later**. The
      replication that carries the library to the nodes compares size and time with no checksum,
      so the time is the only signal it has; a rewrite that restored times would strand every
      replica silently (FR-011b, SC-002a, research R11)
- [ ] T029c [P] [US2] Test in `tests/integration/test_remint_scope_split.py` — on a node that is
      **not** the controller: with `--table`, only its own configuration documents are rewritten
      and the library replica is **untouched**; without `--table`, the run **refuses** rather than
      minting one locally; and a table whose `controller` is the map's controller is **accepted**,
      which is the normal case everywhere but one (FR-011a, FR-019c, contracts/cli-remint.md)
- [ ] T029d [P] [US2] Test in `tests/integration/test_remint_on_invalid_documents.py` — the survey
      and the collision abort both run to completion on documents the **tightened** schema refuses:
      a uuid1 cluster, and a network map with two rows sharing an identity, which FR-019a's new rule
      refuses at read time. Assert the abort still names both rows and their MACs, which it can only
      do by having read the map. This is the re-mint's half of the property FR-001 states for the
      check, and it is not implied by ordering — US2 lands before US3, but the re-mint is what a
      deployed cluster runs *after* upgrading to the narrowed library (FR-006a)
- [ ] T029e [P] [US2] Test in `tests/integration/test_remint_completion_record.py` — each run leaves
      a completion record naming the table's digest, the scope, the paths rewritten and each
      verification result; two nodes' records assemble into a roll-call whose key set equals the
      map's rows; and a run on a three-node map with only two records present is reported as
      **incomplete**, not converged (FR-017a, SC-002b, data-model §2.3)
- [ ] T030 [P] [US2] Test in `tests/integration/test_clone_refused.py` — a stored identity whose
      recorded MAC is not this hardware's is refused with re-minting offered, and a **matching**
      MAC still preserves the identity (FR-019d, research R6)
- [ ] T031 [P] [US2] Test in `tests/contract/test_uuid_flag_checked.py` — an explicit identity that
      collides with a row in the network map is refused; a non-colliding uuid4 is accepted (FR-019b)
- [ ] T032 [P] [US2] Test in `tests/integration/test_remint_backups_untouched.py` — `.bak-*` and
      conversion backups are **not** rewritten (FR-015)
- [ ] T033 [P] [US2] Test in `tests/unit/test_remint_estimate.py` — the estimate is surveyed bytes
      divided by the throughput **the survey observed on this machine**, not by the 500 MB/s floor:
      feed the survey a known elapsed time and byte count and assert the arithmetic, then assert that
      a survey too small to time falls back to the floor **and says so in its output**. `--dry-run`
      writes nothing at all, not even a table (FR-PERF-003)

### Implementation for User Story 2

- [ ] T034 [US2] Create `src/cuemsutils/tools/remint.py` with the survey — classify every identity
      across the configuration documents and the library, reading with **stdlib XML only** and never
      through the validating load path (FR-006a), and returning the byte volume **and its own elapsed
      time**, which together are the observed throughput the estimate divides by (FR-PERF-003)
- [ ] T035 [US2] Implement collision detection in `remint.py`, run **after** the survey and
      **before the table is built** — earlier than "before any write", so an abort costs not even a
      minted identity — aborting per contracts/cli-remint.md. It reads the map with stdlib XML,
      because a colliding map is exactly what FR-019a's rule refuses at read time and the abort
      message must name both rows (FR-006a)
- [ ] T036 [US2] Implement table build and persistence in `remint.py` — minted through
      `cuemsutils.tools.Uuid`, checked for minted collisions, persisted before the first write
- [ ] T037 [US2] Implement the apply loop in `remint.py` — per file: read, substitute every entry,
      write to a temporary, `os.replace`, append the path to `applied`
- [ ] T037a [US2] Implement the **scope split** in `remint.py` (FR-011a) — determine whether this
      node is the controller from its role in the network map; the library reach runs **only** on
      the controller, the configuration reach on every node. A plain node with no table refuses
      rather than minting; a plain node never rewrites its library replica
- [ ] T038 [US2] Implement resume in `remint.py` — load an existing table, skip `applied` paths,
      never re-mint. Refuse a table whose `controller` is **not the map's controller** — *not* one
      whose controller is merely not this node, which is the normal, intended case on every node
      but one (contracts/cli-remint.md, "Not a refusal")
- [ ] T039 [US2] Implement the verification pass in `remint.py` — zero old tokens, every touched
      document valid, a full load succeeds **on this node**, adoption state unchanged
      (FR-016–FR-018). This is the one place the validating load path is used, and it runs only after
      the rewrite has made validation possible
- [ ] T039a [US2] Implement the completion record in `remint.py` — written after the verification
      pass, into the state directory the tool already owns, carrying the table's digest, the scope,
      the paths rewritten and each verification result (FR-017a, data-model §2.3). Include the
      roll-call helper that keys records by node and compares the set against the map's rows: the
      controller's run exiting cleanly is not evidence about any other node, which is the whole
      reason this exists
- [ ] T040 [US2] Add the `--uuid` map check to `_resolve_identity` in
      `src/cuemsutils/tools/init_node.py` (FR-019b)
- [ ] T041 [US2] Add clone refusal to `_resolve_identity` in `init_node.py` — derive the hardware
      MAC unconditionally, compare with the stored one, refuse on mismatch pointing at
      `--force-new-identity`; a `_derive_mac` failure must stay a non-event on the preserve path
      (FR-019d, research R6)
- [ ] T042 [US2] Implement the estimate and confirmation in `remint.py` — predicted duration is
      surveyed bytes divided by **the throughput T034's survey observed on this machine**, presented
      with the `--yes` confirmation (FR-PERF-003). **Not** the 500 MB/s constant: that is a *floor*
      T077 asserts the implementation beats, so dividing by it would overstate every estimate by the
      margin of the beating and miss SC-PERF-003's ±25% while the implementation was entirely
      correct. The floor is the **fallback only**, used when the survey is too small to time
      meaningfully, and the output must say when it was used so a pessimistic estimate is never
      presented as a measured one
- [ ] T043 [US2] Wire `--remint`, `--dry-run`, `--table` and `--resume` into `init_node.py`'s
      parser, following the tool's existing conventions (FR-UX-001, contracts/cli-remint.md).
      `--table` is how a node that is not the controller proceeds, so its help text must say that
      rather than describing it as an override

**Checkpoint**: a deployed cluster can be repaired. US3 is now safe to land.

---

## Phase 5: User Story 3 — the narrowing (Priority: P3)

**Goal**: the schema refuses a non-converged identity, so the divergence cannot return.

**⚠️ HARD DEPENDENCY**: US2 must be complete. Landing this first invalidates every deployed
identity with nothing able to repair it (§9.3).

**Independent Test**: each non-converged shape is rejected with an actionable message; a uuid4
document and the pristine freshly-installed document set are accepted; the package's own
build-time generation succeeds.

### Tests for User Story 3

- [ ] T044 [P] [US3] Test in `tests/contract/test_uuid_type_narrowed.py` — uuid1, uuid5 and an
      upper-case uuid4 are each rejected in all three schemas; a lowercase uuid4 is accepted
      (FR-020, FR-020a, FR-021a, SC-007)
- [ ] T044a [P] [US3] Test the overlap end state in
      `tests/contract/test_uuid_type_name_resolved.py` — `UuidType` is declared in **one** schema
      (`script.xsd`) after the deletion, and `ConvergedUuidType` / `NotProvisionedUuidType` /
      `NodeUuidType` are each declared identically in the three that moved. Assert against the
      shipped allowlist module itself, so the four overlap tests and this one cannot disagree
      (FR-020c, FR-021d, FR-025, SC-009, research R13)
- [ ] T045 [P] [US3] Test in `tests/contract/test_sentinel_still_valid.py` — the sentinel validates
      in all three schemas, and no other nil-like value does (FR-021, assumption 1)
- [ ] T046 [P] [US3] Test in `tests/contract/test_generation_under_narrowing.py` — the build-time
      document generation succeeds and its output still validates (SC-008, finding M-f)
- [ ] T047 [P] [US3] Test in `tests/contract/test_version_steps.py` — the three `CURRENT_VERSION`
      bumps; a pre-step document is recognised by its marker and recorded as an **identity** step;
      **no** conversion is registered for any of them, and no repair is attempted on a non-converged
      identity found in one (FR-022, FR-022a, **FR-023**, research R5)
- [ ] T048 [P] [US3] Test in `tests/contract/test_node_uuid_unique_rule.py` — the rule is
      registered, `document_scoped=True`, `repairable=False`, and a colliding map raises
      `ValidationError` naming both rows (FR-019a, **SC-012**, research R2)
- [ ] T049 [P] [US3] Extend `tests/contract/test_rule_targets_resolve.py` — the new rule's
      `(class-name, field)` target resolves against the model's MRO (trap 7.6)
- [ ] T050 [P] [US3] Re-check every negative fixture affected by the tightening in
      `tests/data/corpus/negative/` — assert **which** error each now raises, not merely that it
      still fails (FR-027, trap 7.3)
- [ ] T051 [P] [US3] Test in `tests/contract/test_rejection_is_actionable.py` — a rejected document
      produces an error naming the document, the path, the value and the repair tool (FR-024,
      **FR-023**'s reporting half, produced in the validation error path because no conversion
      exists to produce it)
- [ ] T052 [P] [US3] Test in `tests/integration/test_pre_step_documents_load.py` — a pre-step
      document is recognised by its marker as an identity step rather than reported as unknown or
      malformed; a pre-step document whose identity is already converged **loads**, and one carrying a
      uuid1 is **rejected with FR-024's message**. Both halves, because the story's fifth scenario is
      about recognition, not about surviving (US3 scenario 5, FR-022a)

### Implementation for User Story 3

- [ ] T053 [US3] In `src/cuemsutils/xml/schemas/network_map.xsd`: declare `ConvergedUuidType`,
      `NotProvisionedUuidType` and their union `NodeUuidType`, retype `node_list/node/uuid` to
      `cms:NodeUuidType`, and **delete the schema's own `UuidType` declaration** (FR-020c). The
      deletion is the point, not a tidy-up: `UuidType` is also declared in `script.xsd`, and the
      overlap ratchet allows a twice-declared name only as a recorded **identical** duplicate
      (content must match) or a recorded **divergent** one (content must still differ). Narrowing in
      place gives network_map's the sentinel, which FR-021 forbids giving script's — so the two could
      never match, the divergence entry could never be removed, and FR-025's completion marker would
      be permanently unreachable. Deleting leaves the name declared once, which is the only state in
      which the stale-entry test *requires* the removal T059 makes (research R13)
- [ ] T054 [US3] In `src/cuemsutils/xml/schemas/project_mappings.xsd`: declare the same three types
      — byte-identical bodies, modulo this file's indentation — and retype `NodeMappingType/uuid` to
      `cms:NodeUuidType`. Leave `MappedToType` **untouched** — out of scope by FR-020b
- [ ] T055 [US3] In `src/cuemsutils/xml/schemas/settings.xsd`: declare the same three types and
      retype `NodeConfType/uuid` to `cms:NodeUuidType`, replacing `cms:NonEmptyString`. Three
      declarations of one type is the project's established way of sharing across these schemas —
      none of the six includes or imports another (research R13) — and T059 records them as such
- [ ] T056 [US3] Bump `CURRENT_VERSION` in `src/cuemsutils/xml/versioning.py` — `network_map`
      1→2, `project_mappings` 1→2, `settings` 2→3. Register **no** conversion (research R5)
- [ ] T057 [US3] Register the node-identity uniqueness rule in
      `src/cuemsutils/xml/validators.py`, modelled on `action_target_resolves`
- [ ] T058 [US3] Produce FR-024's actionable message in the validation error path —
      `src/cuemsutils/xml/validators.py` for the rule's own text and
      `src/cuemsutils/tools/ConfigBase.py`'s `load_config_document` for the config-domain
      translation, matching on the rule's own wording rather than on exception type, because
      `xmlschema`'s own errors are also `ValueError` subclasses (feature 008's precedent)
- [ ] T059 [US3] **In one commit**, three pins that T053–T055 invalidate together — any one left
      behind is a test asserting something no longer true (FR-025, FR-026, FR-021d, SC-009, traps 7.5
      and 7.6):
      1. update `CURRENT_SCHEMA_HASHES` in `tests/contract/test_schema_scope.py` for the three
         changed schemas;
      2. **remove** the `UuidType` entry from `KNOWN_DIVERGENT_DECLARATIONS` in
         `tests/contract/test_schema_name_overlap.py` — now required, not merely permitted, because
         after T053's deletion the name overlaps no more and `test_the_allowlist_has_no_stale_entries`
         fails while the entry stays;
      3. **add** `ConvergedUuidType`, `NotProvisionedUuidType` and `NodeUuidType` to
         `KNOWN_IDENTICAL_DUPLICATES` in the same file, each recorded for
         `("network_map", "project_mappings", "settings")` — without this,
         `test_no_unrecorded_type_name_is_declared_in_two_schemas` fails at this very commit, which
         is the ratchet working as designed.
      Put the reason in the commit message. Ordering within the commit does not matter; landing any
      part of it separately does

**Checkpoint**: the convergence is complete and cannot regress.

---

## Phase 6: User Story 4 — the library surface (Priority: P4)

**Goal**: one type for one value, and no consumer has to copy the library's rules.

**⚠️ T060 IS A BLOCKING PRECONDITION**, not a follow-up (FR-032).

**Independent Test**: the same identity read through every public accessor has the same type; a
collection of identities sorts; the published coercion rule matches what the library itself does.

- [ ] T060 [US4] Record the consumer census as an artifact in
      `specs/012-uuid4-convergence/consumer-census.md` — every sibling repository by name, with
      **two** results each (FR-032, FR-032a, SC-011):
      1. what it does with the own-identity accessor's changed return type — call sites and the risk
         under a changed type. Research R4 has this measurement; this task records it;
      2. what it does when a **network-map read raises** for a colliding identity. FR-019a makes
         uniqueness a registered, not-repairable rule, so a map that loads today — `NodeIndex.merge`
         collapsing the duplicate silently (M-l) — raises `ValidationError` for every reader
         afterwards. This reaches every repository that reads the map, not only the two that read the
         accessor, and unlike the type change it turns a successful read into an exception. The
         measurement for this half is **not** in R4 and must be taken.
      **No task below may start until this is done**, and the second column is blocking on the same
      terms as the first: the type change fails silently, the refusal fails loudly in the wrong place,
      and neither is a thing to discover in a venue

### Tests for User Story 4

- [ ] T061 [P] [US4] Test in `tests/contract/test_identity_type_parity.py` — on a provisioned node,
      the own-identity accessor and a map identity have the same type and compare equal (FR-028,
      SC-010)
- [ ] T062 [P] [US4] Test in `tests/contract/test_unprovisioned_parity.py` — on an unprovisioned
      node, **every** accessor yields the published sentinel constant (FR-028, US4 scenario 2)
- [ ] T063 [P] [US4] Test in `tests/unit/test_identity_ordering.py` — a collection of identities
      sorts; ordering agrees with the string form; slicing, `len` and `split` remain absent
      (FR-029, data-model §6.2)
- [ ] T064 [P] [US4] Test in `tests/contract/test_published_coercion.py` — the published rule and
      the library's own decoding agree on a uuid4, a uuid1, a non-uuid string and an empty value
      (FR-030)
- [ ] T065 [P] [US4] Test in `tests/contract/test_public_surface.py` — the sentinel constant and
      the coercion rule are reachable from `cuemsutils.tools` and declared in `__all__` (FR-031)

### Implementation for User Story 4

- [ ] T066 [P] [US4] Add a total ordering to `src/cuemsutils/tools/Uuid.py`, consistent with the
      string form; add nothing else
- [ ] T067 [US4] Add the per-**field** adapter opt-in to `src/cuemsutils/xml/registry.py` and
      `src/cuemsutils/xml/adapters.py` — **do not** flip `runs_adapter_table` for `settings`
      (research R1)
- [ ] T068 [US4] Opt `NodeConfType/uuid` into its declared adapter in the settings registry, so a
      provisioned node's own identity decodes to the identity type and the sentinel decodes to the
      published constant (FR-021b)
- [ ] T069 [US4] Publish the coercion rule in `src/cuemsutils/tools/ids.py` — outside
      `cuemsutils.xml`, which consumers may not import (FR-030, Q14)
- [ ] T070 [US4] Declare `__all__` in `src/cuemsutils/tools/identity_check.py` naming the sentinel
      constant, and re-export it from `cuemsutils.tools` (FR-031)

**Checkpoint**: consumers see one surface; `cuems-engine`'s mirror can be deleted in a follow-up.

---

## Phase 7: User Story 5 — the migration guide (Priority: P5)

**Goal**: an operator is not surprised by what the migration costs.

**Independent Test**: every stated loss, hazard and precondition appears, and every version and
component named is verified against the actual trees rather than asserted.

- [ ] T071 [US5] Write `specs/012-uuid4-convergence/migration-guide.md` with §10's procedure made
      executable — survey, stop, table, apply, verify
- [ ] T071a [US5] In `specs/012-uuid4-convergence/migration-guide.md`, state the **scope split**
      and its ordering (FR-011a): the controller re-mints the library and its own configuration;
      every other node re-mints only its own configuration, from the distributed table; the
      library then reaches the nodes by the ordinary project-deployer replication on the next
      project load. Give the operator the one check that tells them replication has happened, and
      say that a node's library replica is **not** re-minted in place — a node re-minted but not
      re-synced still holds stale output prefixes
- [ ] T072 [US5] In `specs/012-uuid4-convergence/migration-guide.md`, state the reimage property
      (a re-imaged node no longer regenerates its identity and must be re-adopted) and the backup
      hazard (pre-migration and conversion backups are not rewritten; restoring one reintroduces a
      stale identity) (FR-033, FR-033a, §9.5)
- [ ] T073 [US5] In `specs/012-uuid4-convergence/migration-guide.md`, name every component that
      must be stopped before the re-mint, including `cuems-nodeconf` — it **writes** the network
      map, so a discovery pass mid-rewrite can reintroduce an old identity (FR-034, §10.4)
- [ ] T073a [US5] In `specs/012-uuid4-convergence/migration-guide.md`, carry the **table copy** as a
      numbered step (FR-007, FR-034): where the controller leaves the persisted table, how the
      operator gets it onto each remaining node, and that a node invoked without it refuses **by
      design** — a node that mints its own table is the divergence §10.3 warns about, so the refusal
      is the design working, not a fault to work around. This feature adds no transport; the copy is
      an operator step and must read as one
- [ ] T074 [US5] Add the coupled consumer version to the precondition list in
      `specs/012-uuid4-convergence/migration-guide.md` — the re-mint ships in the same upgrade as
      `cuems-engine 0.1.0rc7` and never runs under an older engine, whose `cluster_status` cannot
      sort the resulting identities (FR-035, upstream report)
- [ ] T075 [US5] Add the incomplete-re-mint detector to the verification steps in
      `specs/012-uuid4-convergence/migration-guide.md` — after re-minting, load each project on the
      controller and check `cuems-engine`'s `cluster_warning`; a non-empty "missing" list naming an
      old identity is a script the reach did not cover (FR-036, M-e)
- [ ] T076 [US5] In `specs/012-uuid4-convergence/migration-guide.md`, state the four collision
      routes (M-l) and which of them this feature closes, so an operator knows cloning a
      provisioned disk is now refused rather than silently duplicating an identity (**FR-036a**)

- [ ] T076a [US5] In `specs/012-uuid4-convergence/migration-guide.md`, give the procedure for a
      **pre-existing collision** (FR-036b). Without it the migration has a dead end: the re-mint
      aborts on a shared identity (FR-019) and the library refuses to guess which row is real
      (FR-019a is not repairable), so a cluster arriving with a collision is stopped by two
      requirements and released by neither. The procedure is the manual act the library declines to
      automate — decide from the two rows' hardware addresses and the scripts naming the shared token
      which node the outputs belong to, treat the other as never provisioned and re-mint it with the
      identity tool — and it MUST be run **before** the re-mint, while the map still loads, because
      after the narrowing a colliding map does not load at all
- [ ] T076b [US5] In `specs/012-uuid4-convergence/migration-guide.md`, state the **roll-call**
      (FR-036c): the operator confirms the cluster is converged by holding one completion record per
      row in the network map and counting them, not by the controller's run exiting cleanly. Say what
      a missing record means and what to do about it
- [ ] T076c [US5] **Verify the guide** in `tests/contract/test_migration_guide.py` — every item
      FR-033 through FR-036c requires is present, and every version and component the guide names
      resolves in the actual trees rather than being asserted: the coupled `cuems-engine` version, the
      components on the stop list, and the paths the procedure tells an operator to type. This is
      US5's Independent Test made executable. It exists because the constitution requires testing work
      and verification steps **per story**, and a phase of six writing tasks had none — a guide whose
      named version has moved is worse than no guide, because an operator follows it

**Checkpoint**: the migration is documented to the standard the field needs, and the guide is
checked rather than trusted.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T077 [P] Measure throughput at **2 and 10 nodes** — the ends of the cluster range — over
      identical library bytes in `tests/integration/test_remint_throughput.py`. Assert
      **≥ 500 MB/s**, and that the slower run's elapsed time is **≤ 1.10× the faster run's**
      (SC-PERF-001, research R8). A **ratio, not a percentage**: the fixture runs in single-digit
      milliseconds, where the 1% this task originally carried is ~80 µs — below the machine's timing
      jitter, so the assertion would have measured noise. The bound keeps its discriminating power
      because a per-node repeated pass makes the 10-node run about **5×** the 2-node run, not 1.1×.
      Both figures are **FR-PERF-001**'s non-provisional budgets
- [ ] T078 [P] Assert the `remint_200` fixture's wall-clock ceiling of **≤ 2.0 s** in
      `tests/integration/test_remint_fixture_ceiling.py` (SC-PERF-001). This ceiling **is**
      provisional — the one figure **FR-PERF-001** states as an estimate: if the measurement lands
      well under it, lower it to the measured figure plus headroom and record the change in
      `baseline.md`. It is never raised to accommodate an implementation
- [ ] T079 [P] Measure the read path against `specs/008-rebuild-extension/baseline.md` in
      `tests/integration/test_read_path_regression.py`, same method as that baseline
      (SC-PERF-002, **FR-PERF-002**, research R14). **Two rows, two comparisons, and the difference is
      not a convenience**: the show-document load is asserted against its recorded **budget**, while
      the `network_map` configuration load is asserted against its recorded **measured band**,
      10.14–10.49 ms. That row is recorded in 008's baseline as exceeded-or-marginal against its own
      10.20 ms budget, so asserting the budget would fail on a tree where this feature changed
      nothing — which teaches a reader to ignore the test rather than telling them anything about the
      narrowing
- [ ] T080 [P] Assert the estimate's accuracy in `tests/integration/test_estimate_tolerance.py` —
      predicted within **±25%** of actual, at both node counts (SC-PERF-003). This passes only
      because T042 divides by the **survey-measured** throughput: dividing by the 500 MB/s floor, as
      an earlier draft did, would put the estimate at `measured ÷ 500` times the actual duration, so
      an implementation running at 1 GB/s would report double and fail this test while being entirely
      correct. The tolerance is wide because the estimate answers "is my maintenance window long
      enough", not "how many milliseconds"

**Note on placement**: these four go in `tests/integration/`, where this repository already keeps
its timing tests (`test_construction_performance.py`). No `tests/performance/` directory is
introduced.
- [ ] T081 Record every measurement in `specs/012-uuid4-convergence/baseline.md`, **as measured**,
      including any budget exceeded — this repository's standing practice
- [ ] T082 Verify the four collision routes are closed or refused in
      `tests/integration/test_collision_routes.py` — clone refused, colliding explicit identity
      refused, re-mint over an existing collision aborts, table built on the controller (SC-013)
- [ ] T083 Apply this feature's corrections to `specs/planning/etc-cuems-first-install.md` and
      `specs/planning/etc-cuems-first-install-execution.md` (FR-037), never silently: §9.2's
      narrowing description (the sentinel exception, M-f), §9.4's detection assignment (it extends
      the identity check, not the conversion tool), §10.5's script-filename procedure (root element,
      not filename — research R3), the two-versus-three schema count, and §10.7's items now answered
      from code (research R3, R7). Add §9.2's **rename-and-delete**: the planning text describes
      network_map's `UuidType` as narrowing to match script's, which M-p measures to be impossible
      once the sentinel is admitted — the declaration is deleted and the element retyped instead
      (M-p, FR-020c)
- [ ] T084 Record the D13 amendment against feature 011 in
      `specs/011-etc-cuems-first-install/` — "mint iff there is none" becomes "iff there is none,
      **or** the identity on disk was minted for different hardware". A later reader finds 011's
      decision text first, so the amendment must live there, not only here
- [ ] T084a Record the §10.7 hardware confirmations in
      `specs/012-uuid4-convergence/baseline.md` (FR-038) — which items research answered from code
      (the script filename, R3; the `trash/` layout, R7; the replication path, R11), which remain
      genuinely unconfirmed (whether every project carries its own `mappings.xml`; whether any
      other file in a project directory embeds an output name), and the date each was checked.
      Both production machines have been unreachable since 2026-09-23, so the honest record is
      what this task produces — an unconfirmed item recorded as unconfirmed, with the mitigation
      named, not an item quietly dropped. The migration guide's "first real run" step cites it
- [ ] T085 [P] Run the project's lint and type checks over `src/cuemsutils/` and `tests/`;
      confirm no new warnings (Principle I, SC-QUALITY-001)
- [ ] T086 Re-run the full suite and record the result as a **range**, comparing against T003's
      baseline; confirm per-test timing is within budget (SC-TEST-001)

---

## Dependencies

```
Phase 1 Setup
    │
Phase 2 Foundational  ← BLOCKS EVERYTHING
    │
    ├──────────────► Phase 3  US1 check        (P1, MVP — independent)
    │                     │
    ├──────────────► Phase 4  US2 re-mint      (P2 — needs Phase 2 only)
    │                     │
    │                     ▼
    │                Phase 5  US3 narrowing    (P3 — HARD dependency on US2)
    │                     │
    ├──────────────► Phase 6  US4 surface      (P4 — independent; T060 gates the rest)
    │
    └── (via Phase 5) ─► Phase 7  US5 guide     (P5 — needs US2 and US3 **measured**,
                          │                           NOT US4. The edge is from Phase 5,
                          │                           not from Phase 2 — an earlier
                          │                           drawing of this diagram branched it
                          │                           off the foundational phase, which
                          │                           contradicted the prose below)
                     Phase 8 Polish
```

**Forced orderings, and why**:

| Ordering | Reason |
|---|---|
| US2 before US3 | Landing the narrowing first invalidates every deployed identity with nothing able to repair it (§9.3) |
| T060 before T061–T070 | FR-032 makes the census a blocking precondition of the type change, not a follow-up |
| T059 as one commit | While the divergence entry is listed, its own test *requires* the collision to still exist (trap 7.5) |
| US5 after US2 and US3 | The guide must state measured results, not intended ones. It does **not** depend on US4 — the diagram's edge into Phase 7 comes from Phase 5 |
| T018a with T017/T018 | The shipped contract test asserts the verdict vocabulary those two tasks change; letting it lag leaves it green while testing the superseded values |
| T029a distinct from T027 | A file can be free of every old token and still fail to validate or load. FR-017 and SC-002 are not implied by SC-001 |
| T042 uses the **survey-measured** throughput, not the floor | The floor is a lower bound T077 asserts the implementation *beats*. An estimate dividing by it overstates by exactly that margin, so T042 and T080 could not both pass. Corrected 2026-09-30b; the floor is the fallback only, and the output says when it was used |
| T053 deletes rather than narrows, and T059 carries three pins | The overlap ratchet admits a twice-declared name only as a matching identical duplicate or a still-differing divergent one. FR-021 forbids giving `script.xsd`'s `UuidType` the sentinel, so the two can never match — deletion is the only route to FR-025's marker (R13). T059's three parts each fail on their own: hashes, the required removal, and the three new names' entries |
| T060's **second** column before T061–T070 | FR-032a: FR-019a turns a successful map read into a `ValidationError` for every reader, reaching more repositories than the type change does. R4 does not measure it |
| T029d is not made redundant by US2-before-US3 | The re-mint is what a deployed cluster runs *after* upgrading to the narrowed library, so every document it repairs is invalid by then — and the collision abort must read a map the new rule refuses (FR-006a) |
| T076c after T071–T076b | A verification of the guide has to come after the guide. It is not optional: the constitution requires verification steps per story, and Phase 7 had none |

**Independent**: US1 and US4 depend on nothing but Phase 2 and can proceed alongside US2.

## Parallel execution examples

**Phase 2** — after T004 and T006 and T008 land, their tests run together:

```
T005, T007, T009
```

**Phase 3** — all five US1 tests are independent files (T018a is **not** among them: it edits an
existing file that T017 and T018 are changing):

```
T010, T011, T012, T013, T014
```

**Phase 4** — nineteen US2 tests, all independent files:

```
T020 … T029, T029a, T029b, T029c, T029d, T029e, T030 … T033
```

**Phase 5** — ten US3 tests; note T053–T059 are **not** parallel, since T059's three pins must
accompany the schema edits in one commit:

```
T044, T044a, T045 … T052
```

**Phase 8** — the four performance measurements are independent:

```
T077, T078, T079, T080
```

They go in `tests/integration/`, alongside this repository's existing timing tests.

## Implementation strategy

**MVP is Phase 3 (US1) alone.** It writes nothing, needs no other story, and is the only part safe
to put on a field machine before the re-mint's reach has been confirmed on hardware (§10.7). An
operator with just US1 can answer "does this cluster need the migration?" — which is the question
they have today with no way to answer it.

**Increment 2** adds US2: the cluster can be repaired. Still nothing has narrowed, so a mistake is
recoverable.

**Increment 3** adds US3, and only then. This is the point of no return for documents on disk, and
it is why the two increments before it exist.

**US4 can ship at any point after T060**, independently of the others — it changes no document, only
what the library hands a consumer.

**Nothing ships from this branch alone** (D27). The coordinated `xml-refactor-merge-candidate` tag
comes after features 011–014, and the re-mint is additionally coupled to `cuems-engine 0.1.0rc7`
(FR-035).

## Task count

| Phase | Tasks | Added by the first analysis pass | Added by the second |
|---|---|---|---|
| 1 Setup | 3 | — | — |
| 2 Foundational | 6 | — | — |
| 3 US1 — check | 11 | T018a | — |
| 4 US2 — re-mint | 31 | T029a, T029b, T029c, T037a | T029d, T029e, T039a |
| 5 US3 — narrowing | 17 | — | T044a |
| 6 US4 — surface | 11 | — | — |
| 7 US5 — guide | 11 | T071a | T073a, T076a, T076b, T076c |
| 8 Polish | 11 | T084a | — |
| **Total** | **101** | **7** | **8** |

The first pass's seven additions closed: one requirement with an implementation and no test
(FR-017 → T029a), one property the whole library reach silently depends on (FR-011b → T029b), the
per-node/controller scope split that answers how a rewritten library reaches a node (FR-011a →
T029c, T037a, T071a), a shipped contract test the widened exit class would have left testing the
wrong vocabulary (T018a), and a requirement with no task at all (FR-038 → T084a).

The second pass's eight close its own two blocking findings and four of its five underspecifications:

| Task | Closes |
|---|---|
| T044a | FR-025's completion marker was unreachable — the overlap ratchet left only the rename-and-delete route (R13), and nothing tested the end state |
| T029d | the re-mint had no equivalent of FR-001's "usable on documents the schema refuses", though that is precisely what it repairs (FR-006a) |
| T029e, T039a | "a full load succeeds on **every** node" had no per-node record and no roll-call (FR-017a) |
| T073a | how the substitution table reaches a node was stated nowhere (FR-007, FR-034) |
| T076a | a pre-existing collision was a dead end: the re-mint aborts, the library will not guess, and after the narrowing the map does not load (FR-036b) |
| T076b | the roll-call needed an operator-facing statement (FR-036c) |
| T076c | US5 declared an Independent Test and Phase 7 had no verification task — a constitution violation, not a gap (Delivery Workflow gate) |

Nine existing tasks were **rewritten** rather than added: T042 and T080 (the estimate divides by
measured throughput, not the floor), T077 (a 1.10× ratio at named node counts, not 1% on a
millisecond fixture), T079 (two comparisons against feature 008's baseline, not one), T052, T053,
T054, T055 and T059.
