---
description: "Task list for feature 010 — consumer migration"
---

# Tasks: Consumer migration

**Input**: Design documents from `/specs/010-consumer-migration/`
**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/)

**Tests**: REQUIRED by the constitution (Principle II). Written first, failing before implementation.

**Organization**: grouped by user story. The spec has ten; **three are this repository's work and
seven are not** — see the scope boundary immediately below.

## ⚠️ Scope boundary — read before using this file

This feature spans seven repositories, and each runs its own spec-kit flow from
`specs/planning/xml-rebuild/010-consumer-prompts/`. **This `tasks.md` is `cuems-utils`' list plus
the cross-repo gates that live in no consumer repository.** The plan settles the split
("What this repository's `tasks.md` contains"):

| In this file | Not in this file |
|---|---|
| US3 in full (wave 0 — the public descriptor path) | The per-call-site edits in the six consumer repositories |
| US9 in full (wave 4 — rollout, release gate, data migration) | Anything each consumer already tracks in its own `tasks.md` |
| US10 in full (wave 5 — removal, count, migration guide) | |
| For US1/US2/US4/US5/US6/US7/US8: **gate references only** — the guide entry each one owes, and the verification that it actually landed | |

Duplicating a consumer's edits here would create two task lists that drift, and the one in the
wrong repository would win arguments it should lose.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: the user story from [spec.md](spec.md) this task serves

## Path conventions

`src/cuemsutils/`, `tests/` at this repository's root. Consumer repositories are referenced by
absolute path under `/disk/Projects/StageLab/` where a verification task must read them.

---

## Phase 1: Setup

**Purpose**: the measurement and document scaffolding every later phase writes into.

- [ ] T001 Record the measured suite baseline (`hatch test --show`; expect ~2573 passed / 96 skipped / 2 xfailed ≈ 20.73 ms/test) in `specs/010-consumer-migration/baseline.md`
- [ ] T002 [P] Create `specs/010-consumer-migration/migration-guide.md` with the section skeleton — it accumulates across the whole feature rather than being written at the end (FR-UX-001)
- [ ] T003 [P] Create `specs/010-consumer-migration/import-census.md` carrying the census command and **today's non-zero** result, so the wave-5 gate has a starting measurement to move from (FR-029)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: confirm what this feature *assumes already exists*, so no later task rebuilds it.

**⚠️ CRITICAL**: Assumption 3 of the spec says everything else this feature asks of the library
already landed in 007 and 008. That is a claim to verify once, here — not per story.

- [ ] T004 Confirm — do **not** rebuild — the inherited surfaces, recording each with its location in `specs/010-consumer-migration/baseline.md`: `NetworkMap.partition_by_adoption` (`src/cuemsutils/xml/settings.py:209`), the `cuems-convert-documents` entry point (`src/cuemsutils/xml/convert_documents.py` + `pyproject.toml` `[project.scripts]`), the public report types in `src/cuemsutils/errors.py` (`LoadReport`/`Outcome`/`RepairRecord`/`ConversionRecord`), and the strict load path's three outcomes
- [ ] T005 [P] Record the six consumer repositories' measured starting state (branch, spec-kit presence, test runner, packaging) in `specs/010-consumer-migration/baseline.md` — five have no spec-kit, two have no `tests/`, two have no `debian/`

**Checkpoint**: the inherited surface is confirmed; US3 can begin.

---

## Phase 3: User Story 3 — The schema descriptor has a public path (Priority: P1) 🎯 MVP

**Goal**: a consumer can reach the descriptor for all six schemas through the public configuration
façade, without importing internal machinery.

**Independent Test**: for each of the six schemas, the public result equals the internal one; every
complex type yields a constructible instance that validates; `cuemsutils.xml.__all__` is still `[]`.

**Blocks**: consumer flows 02 (`cuems-editor`) and 05 (`cuems-frontend`).

### Tests for User Story 3 (REQUIRED) ⚠️

> Write these first and confirm they FAIL before implementation.

- [ ] T006 [P] [US3] Contract test: the public descriptor equals the internal descriptor for **each of the six schemas** — six assertions, not a sample — in `tests/contract/test_public_descriptor.py` (SC-003)
- [ ] T007 [P] [US3] Contract test: every complex type across the six schemas yields a constructible empty instance that **validates against its own schema**, 100% of types counted, in `tests/contract/test_descriptor_instances.py` (FR-022a, SC-003)
- [ ] T008 [P] [US3] Contract test: asking for one schema's descriptor does **not** construct the other five, in `tests/contract/test_descriptor_laziness.py` — and this test must not be defeated by T006 building all six first (research R8)
- [ ] T009 [P] [US3] Extend the public-surface contract test so `cuemsutils.xml.__all__` staying `[]` is asserted alongside the new accessor, in `tests/contract/test_public_surface.py` (FR-024)

### Implementation for User Story 3

- [ ] T009a [P] [US3] Contract test: a show document carrying a dangling `target` or `action_target` loads with the reference cleared and named in the report, and **100% of the cases the editor's current implementation catches** are caught — case by case, not a sample — in `tests/contract/test_dangling_reference_rule.py` (FR-043a, FR-043c, SC-010a)
- [ ] T010 [US3] Decide the public accessor's **name**, record it in `specs/010-consumer-migration/contracts/descriptor-access.md`, and pin it in `tests/contract/test_config_accessor_names.py` alongside the existing accessor names — FR-028 makes the name part of the deliverable, not an implementation detail
- [ ] T011 [US3] Add the constructible empty instance per complex type to `src/cuemsutils/xml/descriptor.py` (FR-022a), leaving the five existing facts unrecomputed (FR-022b, FR-027)
- [ ] T012 [US3] Add the descriptor accessor to `src/cuemsutils/tools/ConfigManager.py` covering all six schemas including `script`, **lazily per schema** (FR-020, FR-022, research R8) — depends on T010, T011
- [ ] T013 [US3] Write FR-021's rationale into that accessor's docstring in `src/cuemsutils/tools/ConfigManager.py`: why a configuration-domain object serves the show schema. A reader who finds it without the reason files it as a mistake
- [ ] T014 [US3] Make the example generators (`generate_script_example`, `generate_settings_example`) reachable from the same public path in `src/cuemsutils/tools/ConfigManager.py` (FR-023)
- [ ] T015 [US3] For each of `cuems-nodeconf`'s two internal imports — `cuemsutils.xml.mapper`'s `Mapper`/`read_config_document` and `cuemsutils.xml.settings`'s `NetworkMap` — name the public equivalent, add a test per import, and record both in `specs/010-consumer-migration/migration-guide.md`; where an equivalent already exists, **name it rather than adding a synonym** (FR-025)
- [ ] T015a [US3] Register the dangling-reference semantic rule in `src/cuemsutils/xml/validators.py` — every `target`/`action_target` resolves to a cue in the same document; a reference that does not is **repairable**, cleared to the field's default and named in the load report (FR-043a). It lands in wave 0, **before** the editor deletes its copy in wave 2a, so no window exists in which neither runs. Measured 2026-09-03 the rule table holds exactly one rule, so this is the second and the first on the show path
- [ ] T016 [US3] Measure wave 0's cost against the "no measurable cost" budget and record it in `specs/010-consumer-migration/baseline.md` — eager construction of all six is a design error, not an overrun to accept (FR-PERF-001)
- [ ] T017 [US3] Write the descriptor section of `specs/010-consumer-migration/migration-guide.md` at call-site granularity, so flows 02 and 05 can be written against it without reading library source (FR-UX-001)

**Checkpoint**: US3 complete → `cuems-editor` and `cuems-frontend` flows are unblocked.

---

## Phase 4: Consumer-repository gates (US1, US2, US4, US5, US6, US7, US8)

**Goal**: this repository's obligations for the seven stories whose edits live elsewhere — the
migration guide entry each one owes, and the verification that it actually landed rather than
merely merged.

**Independent Test**: each gate task names a consumer artifact and either finds it or does not.

**Note**: every task here is `[P]` against the others — they read different repositories and write
different guide sections — but each is blocked by its own consumer flow completing.

- [ ] T018 [P] [US1] Record `cuems-wsclient`'s migration in `specs/010-consumer-migration/migration-guide.md` — the sixth consumer, absent from 007's guide, 008's guide and the cross-repo plan's repository list, which is why a silently broken shutdown path survived two features (FR-UX-002)
- [ ] T019 [P] [US1] Verify the `cuems-wsclient` gate: its private network-map reader is gone (not re-spelled), and its first test fails against the old string comparison; record in `specs/010-consumer-migration/baseline.md` (FR-050, FR-051, SC-001, SC-007)
- [ ] T020 [P] [US2] Record the deleted template module and its replacement — the UUID helper re-sourced from `cuemsutils.helpers` — in `specs/010-consumer-migration/migration-guide.md` with before/after (FR-040, FR-UX-001)
- [ ] T021 [P] [US2] Verify `cuems-editor` imports and reaches its listening state against the current library; record in `specs/010-consumer-migration/baseline.md` (SC-002)
- [ ] T022 [P] [US4] Record the engine's role and online retyping and the non-mutating adoption partition in `specs/010-consumer-migration/migration-guide.md` with before/after (FR-031–FR-034)
- [ ] T023 [P] [US4] Verify each of the engine's four "keeps resolving but becomes wrong" sites (`/disk/Projects/StageLab/cuems-engine` `BaseEngine.py:33,410,440,443`) carries a test that **fails against the pre-migration value**; record the four in `specs/010-consumer-migration/baseline.md` (FR-004, SC-007)
- [ ] T024 [P] [US5] Record the discovery-vocabulary cutover across **both** owning repositories in `specs/010-consumer-migration/migration-guide.md`, including the two template filenames and the packaging entries that place them (FR-060–FR-063)
- [ ] T025 [P] [US5] Verify the end-to-end discovery check ran — a node published by `/disk/Projects/StageLab/cuems-nodeconf`'s migrated publisher, discovered with its role by its migrated listener — and that no half-renamed combination is shippable; record in `specs/010-consumer-migration/baseline.md` (SC-012)
- [ ] T026 [P] [US6] Record the editor's five show-parsing sites, the wire projection, the message family and the **two** payload deltas in `specs/010-consumer-migration/migration-guide.md` (FR-041, FR-042, FR-047–FR-049c)
- [ ] T027 [P] [US6] Verify the payload against the **two-delta** statement — `schemaLocation` absent, duration wrapped, nothing else moved including key order and the string boolean form — never against unconditional byte-identity, and **against this repository's golden corpus** (`tests/golden/`, already carrying `doc_version="2"` and the wrapped duration) rather than a payload captured at migration time; record the goldens used **by checksum** in `specs/010-consumer-migration/baseline.md` (FR-013, FR-013a, SC-005, SC-005a)
- [ ] T027a [P] [US6] Verify the fixup split landed as specified: the editor's dangling-reference code is **deleted** (not ported), the database-sourced duration correction **stays** and operates on the loaded object rather than a dict, and both still detect what they detect today — measured case by case (FR-043–FR-043d, SC-010a, SC-010b)
- [ ] T027b [P] [US6] Verify **zero** consumer code paths manipulate the wire dict to achieve an object-level result — the projection appears once, at the UI boundary, in each consumer that has one; record per repository in `specs/010-consumer-migration/baseline.md` (FR-013b, SC-005b)
- [ ] T028 [P] [US6] Verify `/disk/Projects/StageLab/cuems-editor`'s `repair_durations.py` still reads the corrupt documents it exists to repair, and that exactly **one** document rewriter remains in the ecosystem; record the fixture set and result in `specs/010-consumer-migration/baseline.md` (FR-045, SC-010)
- [ ] T028a [P] [US6] Record in `specs/010-consumer-migration/migration-guide.md` that FR-043a **widens behaviour for every consumer**, not only the editor: a document with a dangling reference now loads with it cleared and reported wherever it is loaded, where previously only documents passing through the editor were corrected — the engine could previously dispatch against a reference to a cue that does not exist (FR-043d)
- [ ] T029 [P] [US7] Record the node daemon's network-map swap, the relocated timing helper and the two internal imports in `specs/010-consumer-migration/migration-guide.md` (FR-064–FR-068)
- [ ] T030 [P] [US7] Verify 008's characterization tests in `/disk/Projects/StageLab/cuems-nodeconf` pass **unchanged** against the library's object — not edited to accommodate the new API; record the run in `specs/010-consumer-migration/baseline.md` (FR-065, SC-008)
- [ ] T031 [P] [US8] Record the UI's template and configuration-domain port, and the media-duration unwrapping, in `specs/010-consumer-migration/migration-guide.md` (FR-085–FR-088d)
- [ ] T032 [P] [US8] Verify the characterization tests for `/disk/Projects/StageLab/cuems-frontend`'s `projects.service.ts`, `project-edit/sequence/sequence.component.ts` and `settings.component.ts` were committed **before** the port and are green after it; record both commits in `specs/010-consumer-migration/baseline.md` (FR-084, D35, SC-013)
- [ ] T033 [US6] Verify 008's consumer-impacting changes against **each live call site `specs/008-rebuild-extension/migration-guide.md` named** — the duration type and wire change, the validating load path, and the version marker's presence — and record the per-site results in `specs/010-consumer-migration/baseline.md` (FR-080–FR-083)
- [ ] T034 [US4] Count the "keeps resolving but becomes wrong" callers found and the discriminating tests added, and state the two counts as **equal** in `specs/010-consumer-migration/migration-guide.md` (SC-007)

**Checkpoint**: every consumer flow has landed and is recorded. Wave 4 can begin.

---

## Phase 5: User Story 9 — An operator upgrades a cluster and it comes back whole (Priority: P3)

**Goal**: packages refuse combinations that cannot work; the document library converts with its
backups retained; and both rollback procedures are executed rather than written.

**Independent Test**: an out-of-order install is actually refused; a controller-plus-node upgrade
returns with topology intact.

**Depends on**: Phase 4 complete (all consumer flows merged).

### Tests for User Story 9 (REQUIRED) ⚠️

- [ ] T035 [P] [US9] Test that the conversion's check mode reports per-document versions and **writes nothing**, in `tests/contract/test_convert_documents_check.py` (FR-103)
- [ ] T036 [P] [US9] Test that re-running the conversion over a partly converted library converts only the remainder, writes no second backup and corrupts nothing, in `tests/integration/test_conversion_resume.py` — this **verifies a property 008's design already provides** rather than driving new code (FR-095c, SC-017b, research R3)

### Implementation for User Story 9

- [ ] T037 [US9] Add the no-write check mode to `src/cuemsutils/xml/convert_documents.py` — per-document versions plus a library-level summary, in the reporting style the tool already uses (FR-103, research R4). Recorded in the plan as this repository's third scope enlargement
- [ ] T038 [US9] Supply the four missing package edges and reconcile `cuems-engine`'s two disagreeing floors; record the result in `specs/010-consumer-migration/contracts/release-gate.md` (FR-091, FR-092)
- [ ] T039 [US9] Run 007's deferred mechanical demonstration — install an out-of-order combination and record the package manager's **refusal** — in a disposable container; record in `specs/010-consumer-migration/baseline.md` (FR-093, SC-015)
- [ ] T040 [US9] Decide and record the `postinst` ordering of the configuration conversion against the service restart, in `specs/010-consumer-migration/migration-guide.md` (FR-094)
- [ ] T041 [US9] Record in `specs/010-consumer-migration/migration-guide.md` the show-conversion trigger (an explicit operator command), the deploy-path exposure, and the safe upgrade order — **nodes first** (FR-095, FR-095b, FR-096, FR-036)
- [ ] T042 [US9] Run the conversion against a real library of **hundreds** of documents and record in `specs/010-consumer-migration/baseline.md`: documents converted (counted, not sampled), backups retained, elapsed time, and the **disk-space delta** — backups sit beside the documents and are never reclaimed automatically (SC-017, research R5)
- [ ] T043 [US9] Execute rollback drill A — pre-conversion, package downgrade only, no document touched — and record the procedure and outcome in `specs/010-consumer-migration/migration-guide.md` (FR-101, SC-017a)
- [ ] T044 [US9] Execute rollback drill B — post-conversion, downgrade plus restore from the retained backups — and record the procedure and outcome in `specs/010-consumer-migration/migration-guide.md` (FR-102, SC-017a)
- [ ] T045 [US9] Record the backup retention rule in `specs/010-consumer-migration/migration-guide.md`: retained indefinitely, reclaimed only by explicit operator action, no earlier than after the post-upgrade verification passes **and** one full show cycle has run (FR-102, research R5)
- [ ] T046 [US9] Run the cluster upgrade — controller plus at least one node, nodes first — and confirm every node discovered, adoption preserved and a show loadable on each; record in `specs/010-consumer-migration/baseline.md` (SC-016)
- [ ] T047 [US9] Run the end-to-end check from `specs/010-consumer-migration/quickstart.md`: a project saved by the editor loads in the engine and renders in the UI, differing from today in exactly the two enumerated ways; record in `specs/010-consumer-migration/baseline.md` (SC-005)
- [ ] T048 [US9] Verify the payload-version handshake defined in `specs/010-consumer-migration/contracts/editor-ui-messages.md` refuses a deliberately **stale** UI bundle and says why; record in `specs/010-consumer-migration/baseline.md` (FR-105, SC-015a)

**Checkpoint**: the release gate is mechanical and demonstrated; the data migration is proven at scale.

---

## Phase 6: User Story 10 — The deprecated surface comes out and the guide records what moved (Priority: P3)

**Goal**: delete the deprecated surface, move to the promised release, and hand over a guide that
maps every removed or changed entry point to its replacement.

**Independent Test**: the measured import census across six consumer checkouts is zero; the
deletions land; the suite is green and faster.

**Depends on**: **a measured zero**, not on "Phase 5 is merged".

### 🛑 GATE — T049 and T050 block every deletion below

FR-090 requires this ordering to be structural. **T051–T061 must not start** until T050 records a
zero. "The consumer flows are merged" is a different claim from "the imports are gone", and the
difference is a broken daemon.

- [ ] T049 [US10] Re-run the import census across all six consumer checkouts under `/disk/Projects/StageLab/` and write the result — per repository, per path, with the command that produced it — to `specs/010-consumer-migration/import-census.md`. **Required value: zero** (FR-029)
- [ ] T050 [US10] Confirm T049's census is dated **after** the last consumer merge, and re-run it immediately before T051, updating `specs/010-consumer-migration/import-census.md` — a repository can regress between merge and removal (FR-029, FR-090)

### Implementation for User Story 10

- [ ] T051 [P] [US10] Delete `src/cuemsutils/xml/Settings.py` (FR-029a) — blocked by T050
- [ ] T052 [P] [US10] Delete `src/cuemsutils/xml/XmlReaderWriter.py` (FR-029a) — blocked by T050
- [ ] T053 [US10] Delete `src/cuemsutils/xml/Parsers.py` (FR-029a) — **first** distinguish the retired `cuemsutils.xml.CuemsParser` alias from the delegating façade that is contractually required to stay silent; they are two different symbols (FR-029d) — blocked by T050
- [ ] T054 [P] [US10] Delete `src/cuemsutils/xml/CMLCuemsConverter.py` (FR-029a) — blocked by T050
- [ ] T055 [P] [US10] Delete `src/cuemsutils/timeoutloop.py` (FR-029a) — blocked by T050
- [ ] T056 [US10] Remove the seven aliases at `src/cuemsutils/xml/__init__.py:81-91`, keeping `__all__ = []` (FR-029a, FR-024) — depends on T051–T055
- [ ] T057 [P] [US10] Remove the deprecated-symbol site at `src/cuemsutils/xml/settings.py:170` (FR-029a)
- [ ] T058 [P] [US10] Remove the deprecated-symbol site at `src/cuemsutils/xml/XmlBuilder.py:362` (FR-029a)
- [ ] T059 [US10] Retire `tests/contract/test_deprecation_shims.py` **deliberately**, recording in `specs/010-consumer-migration/migration-guide.md` what replaces it and why deleting a contract test alongside the contract it guards is correct here (FR-029b)
- [ ] T060 [US10] Move `__version__` in `src/cuemsutils/__init__.py` to the release `_deprecation.REMOVAL_RELEASE` has promised since feature 006 — or record the divergence, because otherwise every warning this library emitted for two features was wrong (FR-029c)
- [ ] T061 [US10] Record the post-removal suite time in `specs/010-consumer-migration/baseline.md` — 22 contract tests retire, so it should be **faster**; if it is not, something else changed and must be explained (FR-PERF-001)

### The count and the guide

- [ ] T062 [US10] Run the ecosystem-wide count and record it in `specs/010-consumer-migration/migration-guide.md` **with its exempt set enumerated site by site and the two exemption reasons stated separately** — "exists to detect or convert the retired spelling" (permanent) and "not shipped" (removable at any time). Merging them is how a working migration diagnostic gets deleted by the next person to run the count (FR-070–FR-073a, SC-006)
- [ ] T063 [P] [US10] Correct the three stale documents that are this feature's own inputs (FR-005): this repository's `CLAUDE.md` (which describes a sibling's node-identity work as not started when it has been on a branch since 2026-08-24), `cuems-common`'s `CLAUDE.md:88` (which assigns a role-constant migration to a closed feature number), and `cuems-nodeconf`'s `AvahiTool.py:12` / `CuemsAvahiListener.py:19-24` (which defer the discovery key to a closed feature)
- [ ] T064 [US10] Complete `specs/010-consumer-migration/migration-guide.md`: every removed or changed entry point mapped to its replacement with before/after examples (FR-UX-001), `cuems-wsclient` listed as a consumer (FR-UX-002), the count with its exempt set (FR-UX-003), and one section stating **which obligation landed in which repository** — seven flows produce seven task lists and no single view of the whole (FR-UX-004)

**Checkpoint**: the release gate is closed and the ecosystem can ship.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T065 Validate every performance budget and record each in `specs/010-consumer-migration/baseline.md`, including any that is **exceeded — recorded as exceeded rather than restated as passing** (FR-PERF-001, SC-PERF-001)
- [ ] T066 [P] Record `network_map` config load against **008's post-landing 10.14–10.49 ms**, noting explicitly that this feature inherits an already-marginal position rather than 007's ≤10.20 ms cap, in `specs/010-consumer-migration/baseline.md` (research R6)
- [ ] T067 Run `specs/010-consumer-migration/quickstart.md` end to end and correct anything it gets wrong
- [ ] T068 [P] UX consistency pass over the new message family (`specs/010-consumer-migration/contracts/editor-ui-messages.md`) and `src/cuemsutils/xml/convert_documents.py`'s output — one reporting idiom, not two (Constitution III)
- [ ] T069 Compile the durable material out of `specs/planning/xml-rebuild/` into a new binding reference at `specs/agreements/xml-architecture-invariants.md`, following the house shape of that folder (title, adopted-by line, applies-to, `Status: binding`). It MUST carry, in the reader's terms rather than as a decision log: the settled decisions that still **bind** (D2 schema as the single source of truth; D12 public surface returns objects; D15 the two public objects; D17/D18 every time-carrying element typed and canonical; D19/D21 the three load outcomes; D22 where network-map logic lives; D25 descriptor-derived generation; D32 the six consumer repositories; D33 the discovery vocabulary's two owners; D34 the descriptor's single public path; Q11→(c) and Q14→(i)); the standing rules from `xml-rebuild-07-speckit-prompts.md` §10; the editor→UI payload's **two-delta** constraint (never restated as unconditional byte-identity); the node model's exclusivity to `cuemsutils` (007 FR-030a-i); the "keeps resolving but becomes wrong" caller class and the discipline it demands (007 FR-030a-ii); and the retired-vocabulary count's **enumerated exempt set with its two distinct reasons** (D36/C12). It MUST link to `specs/agreements/schema-evolution-convention.md` rather than restating it. It MUST **exclude** the decisions that were about *how to land this work* and are now spent history — D28's item ordering, D30's two-phase split of 008, D31's deliberate stop, D27's release gate once the release has happened — because a binding reference that carries expired scheduling teaches the next reader to follow it (`CLAUDE.md`'s "promoted into `specs/agreements/`" clause)
- [ ] T069b Assess each `specs/planning/xml-rebuild/` document against `CLAUDE.md`'s deletion policy and record the verdict **per document** in `specs/010-consumer-migration/migration-guide.md` — **blocked by T069**, and it **deletes nothing**: this task decides, T069c executes. A document is dischargeable only when all three hold: its durable content has landed in T069's agreement file, its executed content is captured in `specs/NNN-*/`, and it carries **no scheduled-but-unexecuted residue** (see T069c). Record the three verdicts separately rather than as one yes/no, because a document can fail on residue alone while being otherwise spent. Note explicitly that the ~65 references from the frozen specs `004`–`009` are **not** a blocker: `CLAUDE.md` sanctions those dangling, since a landed spec's cross-references are not retroactively rewritten
- [ ] T069c Clear the two things that make deletion safe, then delete only the documents T069b cleared. **(a) Residue**: relocate scheduled-but-unexecuted content to a home that outlives the folder — the known instance is `xml-rebuild-01-audit.md` §6's **X13–X17** schema debt, whose natural home is `specs/agreements/schema-evolution-convention.md`, where X13 (`gradient_osc_port`) is *already* recorded as scheduled work. Deleting the folder with that residue in it would destroy the only detailed record of open work, which is the failure `CLAUDE.md`'s "made and acted on" test exists to prevent. **(b) Active referrers**: update, in the same commit, the four documents that are not frozen and would otherwise point at nothing — `CLAUDE.md:12` (cites `xml-rebuild-09` as the corrector of a claim; T063 already edits this line), `CHANGELOG.md:116` (cites `xml-rebuild-01` §6 for exactly the X13–X17 debt (a) relocates), `tests/data/corpus/negative/README.md:59` (cites `xml-rebuild-07` §5.1/§9 for why the negative corpus exists), and `specs/planning/nodeconf-atomization.md:10` (cites `xml-rebuild-08` §4/E11 as provenance — it already reproduced that table into itself, which is the pattern T069 generalises, so this is a citation fix, not a content rescue). Only then delete. If a document survives because its residue could not be relocated, that is the **correct** outcome and is recorded as such — an empty folder earned document by document, never asserted

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no dependencies
- **Phase 2 (Foundational)**: after Phase 1 — blocks US3
- **Phase 3 (US3)**: after Phase 2 — **blocks consumer flows 02 and 05**, so it is first in wall-clock terms as well as priority
- **Phase 4 (consumer gates)**: each task blocked by its own consumer flow; the four wave-1 tracks are independent of US3 and of each other
- **Phase 5 (US9)**: after Phase 4 complete
- **Phase 6 (US10)**: after **T050 records a zero** — not after Phase 5 merges
- **Phase 7 (Polish)**: after Phase 6. One ordering inside it is not cosmetic: **T069 → T069b → T069c**. The durable material is compiled into `specs/agreements/` first, the per-document verdict is recorded second, and only the third task deletes anything — after relocating scheduled-but-unexecuted residue and fixing the four active referrers. Reversed, the deletion destroys exactly what the compilation exists to preserve, and git history is not a substitute for a document an active file still cites. T069b deliberately holds no destructive step: the decision and the irreversible action are separate tasks so the decision can be reviewed before it is executed

### Story dependencies

| Story | Depends on | Note |
|---|---|---|
| US1 `cuems-wsclient` | nothing | run **first** in practice: worst current state, cheapest flow |
| US2 editor start-up | nothing | blocks US6 |
| US3 descriptor path | Phase 2 | **blocks US6 and US8** |
| US4 `cuems-engine` | nothing | |
| US5 discovery cutover | nothing | two repositories, **merged simultaneously** |
| US6 `cuems-editor` | US2, US3 | |
| US7 `cuems-nodeconf` | US3 | |
| US8 `cuems-frontend` | US3, US6 | characterization tests **before** the port |
| US9 rollout and gate | US1–US8 | |
| US10 removal and guide | a **measured** zero | |

### Within each story

- Tests written and failing before implementation
- For the FR-030a-ii class, a passing suite is **not** evidence — each caller needs a test that fails against the old value
- Guide sections written as the work lands, not retrofitted at the end

---

## Parallel Opportunities

**Phase 3 (US3) — the four contract tests are independent files:**

```bash
Task: "Public == internal per schema in tests/contract/test_public_descriptor.py"
Task: "Constructible instances validate in tests/contract/test_descriptor_instances.py"
Task: "Laziness holds in tests/contract/test_descriptor_laziness.py"
Task: "__all__ stays [] in tests/contract/test_public_surface.py"
```

**Phase 4 — every gate task reads a different repository and writes a different guide section**, so
T018–T032 are fully parallel once their consumer flows land.

**Phase 6 — the deletions are separate files** once the gate opens: T051, T052, T054, T055 in
parallel; T053 needs the symbol distinction first; T056 needs all five deleted.

**Across repositories**: the four wave-1 tracks (`cuems-wsclient`, editor start-up, `cuems-engine`,
the discovery cutover) run in parallel with each other **and** with US3, since none depends on the
descriptor.

---

## Implementation Strategy

### MVP for this repository (US3 only)

1. Phase 1 → Phase 2 → Phase 3
2. **STOP and VALIDATE**: six schemas answer publicly and identically; instances validate; laziness
   holds; `__all__` is still `[]`
3. That unblocks two consumer flows — which is the entire reason US3 is P1 despite being neither the
   most urgent defect nor the largest work

### Incremental delivery

Wave 1's four tracks proceed in parallel with US3 in their own repositories. Phase 4 accumulates the
guide as they land. Nothing ships until Phase 6 closes — D27 holds across the whole feature.

### The one thing this strategy must not permit

An early Phase 6. T049/T050 exist so the possibility is absent from the file rather than avoided by
care (FR-090). If a deletion task is ever reached without a zero-valued census dated after the last
consumer merge, the correct action is to stop, not to check by hand.
