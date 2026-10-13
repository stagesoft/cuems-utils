<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature Specification: The consumer-gate closure

**Feature Branch**: `015-consumer-gate-closure`
**Created**: 2026-10-13
**Status**: Planned
**Input**: User description: "Use `specs/planning/upcoming-feature-requirements-2026-10-02.md` as the
source file for a new 015 spec. This is a gating feature that will combine some consumer and
ecosystem debts with a thorough cleanup on the stray plans and superseded mechanisms." Four
maintainer decisions accompanied it — D1 the source's landed decisions are not re-examined, D2 the
deletable files of §9.3's last row are removed in the polish phase, D3 all stray and pending tasks
of §9.1 are included, D4 every `cuems-nodeconf` requirement except `NodeIndex`'s `node_set`
machinery belongs to a future spec.

**Source of record**: `specs/planning/upcoming-feature-requirements-2026-10-02.md` — §0a is the
ranked work order (G1–G5), §9 is the straggler sweep (S1–S4). Supporting inputs:
`specs/planning/settings-reshape-defeats-f3-conversion-defect.md` (G5's own record),
`specs/planning/hardware-outputs-capability-layer.md` (what this feature is **not**),
`specs/planning/etc-cuems-first-install-execution.md` §5 step 7 / §6,
`../cuems-editor/specs/002-config-round-trip/tag-readiness.md`,
`../cuems-nodeconf/specs/planning/12-node-set-alias.md`,
`../cuems-frontend/specs/001-schema-descriptor-migration/upstream-reports/UR-1-descriptor-instance-not-wire-shaped.md`.

**Branch point**: `75a958e` on `feat/xml-refactor` — the documentation commit that made 015 the
gates and deferred `hardware_outputs`. Nothing in `src/` has moved since `2a4b892` (014's merge).

**Suite at the branch point, measured on this branch 2026-10-13 rather than inherited**
(`PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q`):

```
5 failed, 3565 passed, 113 skipped, 2 xfailed, 277 warnings in 31.13-31.83 s   (= 8.73-8.93 ms/test)
```

**Re-measured 2026-10-13 after the toolchain migration**, three runs on a quiet box. The counts are
**identical** to the pre-migration reading — same five failures, same 3565/113/2 — so the migration
changed nothing functional, and the identical skip count confirms dependency parity.

**The interpreter changed under this feature, and then the divergence was closed.** The suite now
runs on CPython **3.11.9** — the version the convention names, for the first time. Two 3.11.9 builds
exist on this box: uv-managed python-build-standalone (`Clang 18.1.8`) which `hatch` resolves, and
`~/.pyenv/versions/3.11.9` (`GCC 12.4.0`). Measured side by side, pyenv's build was initially
**32–72% slower** — until it was rebuilt with `--enable-optimizations --with-lto`, after which the
two agree to within **0–2%**, inside the instrument's own noise. **PGO+LTO was the entire
difference.** Every budget here is stated against a figure measured on this branch point, in the same
session as its verification, on the interpreter `hatch` resolves. See `research.md` R10/R11.

---

## Why this feature exists

The `xml-refactor` arc has reached the point where **this library is what three sibling repositories
are waiting for**. Not advisory — measured:

| Repository | What it is holding | Evidence |
|---|---|---|
| `cuems-editor` | **seven** strict xfails, one per gate item, each of which fails the suite with `XPASS(strict)` the day the library lands its half | `../cuems-editor/specs/002-config-round-trip/tag-readiness.md`, *Status: NOT READY* |
| `cuems-nodeconf` | a whole planned IPC action (`node_set`) with an unchecked prerequisite, and a brief that says *"Order: the library first, then this repository"* | `../cuems-nodeconf/specs/planning/12-node-set-alias.md` §4 |
| `cuems-frontend` | a hand-written transform of a projection it does not own, written as one function so it can be deleted in one edit | `UR-1`, *Workaround taken, and its cost* |

And one of the five gates is not a gap at all but a **defect** that makes an ordinary deployed node
un-migratable by any combination of the shipped tools. Reproduced on this branch, 2026-10-13, on the
pre-F3 document `cuems-nodeconf` carried at `4d7c91d`:

```
cuems-reshape-devices <file>
  -> skipped (would not validate: ... Unexpected child with tag 'audio_cards' at position 3 ...)
     nothing to do (1 skipped)       exit 1
```

Three independent repositories arrived at that mechanism separately, and two of them hand-wrote
eleven `settings.xml` files between them because the tool could not. A third should not have to.

**What this feature is not**: `hardware_outputs`. It left the numbered sequence on 2026-10-12 and
is now `specs/planning/hardware-outputs-capability-layer.md` — deferred, unnumbered, re-owned to
`cuems-nodeconf`. No requirement here touches it, and the eight code sites that used to name it by
feature number are **already re-pointed** (verified 2026-10-13: zero remaining).

---

## What is already settled, and is not re-opened here

Per **D1**, the source document's landed decisions are inputs, not questions. Restated so that no
task re-derives them:

| Settled | Decision | Where |
|---|---|---|
| **SET-1** | `__version__` stays `0.1.0rc16`. The coordinated tag moves no version. Do **not** propose an `rc17` | source §0a, *The version does not move for this tag* |
| **SET-2** | The configuration round trip itself needs no work — `network_map` round-trips with identical bytes; `settings` round-trips with equal values. The gates are the documents and fields the trip cannot **reach** | source §0a, measured 2026-10-08 |
| **SET-3** | `cuems-editor` UR-5 is **closed** by 014's `ConfigManager.from_json`. §1 of the source is history | source §0, §1 |
| **SET-4** | `cuems-editor` UR-3 (`to_wire` projects a model default for an omitted optional element) is **withdrawn, not a defect** — but it is a *general* property of the projection and wants documenting once. That documenting is this feature's straggler **S4** (a different series — see the note below) | source §5 row 1 |
| **SET-5** | FR-044's "fold the repair tool's rewriting pass into `cuems-convert-documents`" is **superseded**; do not re-propose it | source §5 row 2 |
| **SET-6** | 013's guide's `if 'Cue' in item` prescription is **withdrawn and corrected in place**; the landed form matches on cue identity | source §5 row 3 |
| **SET-7** | A content-hash helper for revision tokens is **not asked for**. `Md5Type`/`file_md5` is a `Media` field and is not generalised | source §0a, *not gates* |
| **SET-8** | One call that ingests, resolves the target and persists is **declined again**. `from_json` returns the object; `save_*` writes what the manager holds | source §8, 014 plan §9.3 |
| **SET-9** | An engine-side configuration reload is **not this repository's**. The editor answers *"restart required"* | source §0a, *not gates* |
| **SET-10** | `save` upgrading `doc_version` and rewriting `schemaLocation` is **expected behaviour**, documented consumer-side. No work | source §0a, *not gates* |
| **SET-11** | Upstream report numbers are **per repository and collide**. Every citation in this feature is `<repo> UR-<n>` | source §4 |
| **SET-12** | `xml/XmlBuilder.py` (frozen legacy, no live caller) is already scheduled for the deprecated-surface release. Nothing new here | source §5 row 4 |
| **SET-13** | Per **D4**, every `cuems-nodeconf` requirement other than `NodeIndex.set_alias` — the atomization split, the probe/transcribe ownership, the `display.conf` transcription — belongs to a future spec | D4; capability layer §3 |

⚠ **Two series, deliberately distinguished.** The settled items above are **SET-1…SET-13**; the
source document's four stragglers are **S1…S4** (S1 the structured collision, S2 the union
narrowing, S3 the indenting writer, S4 the projection property plus the sweep). They were both
numbered `S*` until 2026-10-13, which made "S2" name two unrelated things in one document — one of
them *"no work"* and the other a requirement block. Every citation in this feature, its plan, its
tasks and its contracts now uses the `SET-` prefix for a settled item.

---

## Clarifications

### Session 2026-10-13

- Q: FR-025 requires the 64 required-with-no-default fields to acquire a usable value so an instance
  can save. Where does that value come from, given that a model-layer default would flip all 64 from
  `UNREPAIRABLE` to `REPAIRABLE` and so change the load path from refusing a document to repairing
  it? → A: **Instance-local seeding from the XSD type.** The seed is derived inside instance
  construction; the per-field `default` fact stays `Unset` and the repairability classification stays
  `UNREPAIRABLE`, so feature 008's five load outcomes are untouched. This is also what the consumer
  report asked for — it names per-field defaults as explicitly *not* expected.
- Q: What does projecting a project's `project_settings` return when the project has no settings
  file, given that the measurement shows nothing is retained and the source document's "keeps
  defaults" premise is false? → A: **A valid empty document.** Refined by measurement during
  planning: the projection of an empty document is `{}`, not `{"setting": []}` — the repeated field
  is omitted when empty, which is the projection's existing rule for an optional empty field. The
  schema
  declares `setting` with `minOccurs="0"`, so zero settings is a valid document, and "no file" and
  "a file with no settings" therefore project identically — which is correct, because the schema
  says they are the same document. `AttributeError` stays reserved strictly for *not loaded*, so a
  consumer can still tell "you never loaded a project" from "this project has no settings file".
- Q: What shape carries the colliding node identity as data — the existing `Violation` pair, a
  dedicated exception subclass, or both? → A: **Both.** A nameable `ValidationError` subclass in
  `cuemsutils.errors` carrying the colliding identities and their hardware addresses as attributes,
  **with its `violation` populated** as `location=(identity, "uuid")`. The subclass is what the
  errors module's own stated position asks for — *"an exception the caller cannot name is one the
  caller cannot catch, and the alternative consumers reach for is matching on message strings"*,
  which is exactly what the consumer is doing today. The subclass inherits the violation slot, so
  populating it costs nothing and keeps the generic path informative for a caller that does not
  name the subclass.
- Q: The show-document load exceeds its 16.5 ms budget by 1.7–8.4% at the branch point, which is
  inside this instrument's measured resolution — re-baseline, record as exceeded-or-marginal, or
  investigate the ~13% drift from 014's own worst case? → A: **Record as exceeded-or-marginal and
  leave the budget where it is, with the investigation recorded as a follow-up that has an owner.**
  Not re-baselined: that would be the fourth raise in four features, and the first with no mechanism
  named — a regression detector raised every time it fires becomes a ratchet that always passes. Not
  investigated inside this feature either: an open-ended performance investigation is not something
  a gate feature nothing else depends on should carry.
- Q: Four red tests come from one collision — this repository asserts *landed, frozen* migration
  guides against *moving* sibling checkouts. Re-pin, stop asserting, scope to the in-flight guide,
  or split by assertion class? → A: **Split by assertion class, and make the surviving assertions
  resolve at the coordinated tag rather than at a sibling's tip.** A pin in a landed guide is dated
  provenance and is no longer asserted for resolution; an operator-facing claim must be true today
  and the two false ones are corrected as a documentation defect. Thereafter every cross-repository
  claim resolves at each sibling's `xml-refactor-merge-candidate` tag, which is a stable reference by
  construction — the moving tip never was one. Measured 2026-10-13: four of seven siblings carry the
  tag, and **all three values `CLAUDE.md` records have moved** (`e3c9430`→`91b2d25`,
  `b305c1c`→`c29c25c`, `399baf7`→`cabbb3e`), which is the drift this mechanism exists to catch.

### Analysis pass 2026-10-13 (`/speckit.analyze`)

A cross-artefact consistency pass over spec, plan and tasks found **26** items and all are applied
here rather than left in a report. The six that changed what this feature *does*, as opposed to how
it is worded:

1. **A constitution MUST was being set aside without being tracked.** Principle I requires passing
   static checks and SC-QUALITY-001 requires no new **type** warning, while the plan declined a
   type-checker gate and no task ran one — though `pyproject.toml` has defined
   `[tool.hatch.envs.types]` → `mypy` all along. Both gates now run against a branch-point baseline
   (neither is clean today, so a baseline comparison is the only honest form).
2. **SC-012 was unreachable from this repository**, and `contracts/sibling-gates.md` had already
   measured why: three of `cuems-editor`'s seven xfails need sibling-side work. Only G1's obligation
   (FR-008) had been written down. Now FR-017, FR-047 and FR-065b join it, FR-106 collects all of
   them in `consumers_works.md`, and SC-012 claims the four this feature can actually reach.
3. **The golden re-cut was scheduled before two of the additions it records.** `public_api.json`
   enumerates every public error class, and S1 adds one in a phase six later than the re-cut. The
   whole golden event moves to the polish phase, which is also the only arrangement in which
   FR-074's *"one reviewable change"* is true in fact and not only in the record.
4. **SC-009 had no task at all** — its measurable half is a removal in `cuems-editor` — and the
   checkpoint claiming it attributed the verification to an unrelated task.
5. **Three of four documentation obligations landed in modules `docs/` does not render** (FR-UX-003a).
6. **SC-TEST-002 would have passed with five new failures**, and the dead-end population SC-003
   measures existed in no working tree until it was pinned by ref.

The rest were numeric drift between artefacts (golden counts, seeding-rule counts, two performance
bands), four requirements with no task, one overloaded identifier series, and wording. Each is
applied at its own site; **no finding was recorded as accepted-and-not-fixed**.

---

## The branch point's five red tests

Measured 2026-10-13 on `75a958e`, before any change. One becomes a requirement of its own (FR-079) and the
other four are one cause, carried by FR-080.

| Test | Measured | Disposition |
|---|---|---|
| `test_read_path_regression.py::test_the_show_document_load_is_within_its_recorded_budget` | show-document load, **16 samples across three windows**: band **16.465–17.750 ms**, median **16.864**, against a budget of **16.5 ms**. **14 of 16 exceed it** — so the assertion is **flaky on an unchanged tree**, not cleanly failing. Still far inside 008's original 35.99 ms, so only the first of its two assertions is at issue | **FR-079** |
| `test_migration_guide.py::test_the_coupled_engine_version_resolves` | 012's guide names `cuems-engine 0.1.0rc7`; that tree declares `0.1.0-rev1` | **FR-080** |
| `test_migration_guide.py::test_the_engine_really_broadcasts_the_status_the_guide_tells_you_to_watch` | 012's guide tells an operator to watch for `cluster_warning`; the string is absent from the engine's controller source | **FR-080** |
| `test_migration_guide_names_sites.py::…[cuems-editor]` | 013's guide pins `106015c`; it does not resolve in `../cuems-editor` | **FR-080** |
| `test_migration_guide_names_sites.py::…[cuems-frontend]` | 013's guide pins `3183845`; it does not resolve in `../cuems-frontend` | **FR-080** |

The last four are **one finding**: this repository ships contract tests that re-validate *landed*
migration guides against **live sibling checkouts**, while `CLAUDE.md`'s policy says a landed spec is
frozen historical record and is not retroactively rewritten. Those two cannot both hold while the
siblings move. The collision is named in FR-080 and its resolution is the first clarification below.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — An operator saves a project's configuration for the first time (Priority: P1)

An operator opens a new project in the UI, fills in its settings, and presses save. The project has
never been saved, so its `settings.xml` does not exist yet. The save must land in the canonical
place this library owns, not in a path the consumer guessed.

**Why this priority**: gate **G1**. It is the *first* save of any project document, so without it
the whole configuration round trip the editor's 002 was built for is unreachable for a new project.
`cuems-editor` carries a strict xfail against it.

**Independent Test**: ask the library for the write target of a file that does not exist, with
existence tolerated; assert the path is returned rather than refused, that it is the canonical
`library_path/projects/<uname>/<file>`, and that a document saved to it loads back equal.

**Acceptance Scenarios**:

1. **Given** a project with no `settings.xml`, **When** the canonical write target is requested with
   existence not required, **Then** the path is returned and no error is raised.
2. **Given** the same call **without** existence tolerated, **When** the file is absent, **Then**
   `FileNotFoundError` is raised exactly as today — every existing caller's behaviour is unchanged.
3. **Given** the returned target, **When** a configuration document is saved to it, **Then** the
   file is created and reloads with equal values.
4. **Given** a target whose **parent directory** is absent, **When** a save is attempted, **Then**
   it fails — this is a separate and correct matter, not something the tolerant path invents.
5. **Given** this library's own suite, **When** `test_config_manager_save_accessors.py` runs,
   **Then** it no longer replaces a public method to obtain a write target.

---

### User Story 2 — An operator edits a project's settings in the UI (Priority: P1)

An operator opens a project's settings form. The form shows the values the project's file actually
holds — not schema blanks — edits one, and saves the whole document back.

**Why this priority**: gate **G2**. `from_json(SchemaName.PROJECT_SETTINGS, …)` can already ingest a
document that **no public call can produce**; the read side is simply missing. The editor refuses
`config_load('project_settings')` with an error frame naming the report, and has no workaround
because its own public-surface test forbids reaching the private attribute — which is correct.

**Independent Test**: load a project whose `settings.xml` exists, project it, feed the projection
back through ingestion, save, reload, and compare equal.

**Acceptance Scenarios**:

1. **Given** a loaded project with a `settings.xml`, **When** the `project_settings` section is
   projected, **Then** a wire-shaped dictionary of the file's actual values is returned.
2. **Given** that projection, **When** it is ingested and saved and the document reloaded, **Then**
   the values compare equal.
3. **Given** the public section list, **When** it is inspected, **Then** `project_settings` is a
   member, so the error message that enumerates the sections names it.
4. **Given** the projection, **When** it is produced, **Then** it comes through the **same**
   projection body as every other section — not a second implementation.
5. **Given** a project with **no** `settings.xml`, **When** the section is projected, **Then** a
   valid empty document is returned — not an error — and it is identical to the projection of a
   file that exists and holds no settings.
6. **Given** a manager whose project configuration was **never loaded**, **When** the section is
   projected, **Then** the "not loaded" exception is raised, so the two states stay distinguishable.

---

### User Story 3 — A deployed node's `settings.xml` migrates with the shipped tools (Priority: P1)

An operator upgrades a node whose `settings.xml` was last written before 2026-09-23. They run the
migration tool the refusal message names. It migrates the document.

**Why this priority**: gate **G5**, and the only item here that is a **defect** rather than a gap.
Today *no* combination of the shipped tools or the load path produces a valid document from that
state, and it is the ordinary state of a deployed node. It blocks the coordinated tag because the tag
is what puts the new schema in front of nodes holding these documents.

**Independent Test**: point the device-reshape tool at a document that is **both** pre-013
(flat players) and pre-F3 (carrying the retired counts) and assert it is reshaped and then loads.
The composition is the test; a unit test on the converter with an already-reshaped tree would pass
the moment paths are added and would not catch the next instance of the class.

**Acceptance Scenarios**:

1. **Given** a document with flat players **and** the two retired counts, **When** the reshape tool
   runs, **Then** the document is reshaped and written, not skipped.
2. **Given** that reshaped document, **When** it is loaded, **Then** it loads and the two retired
   counts are gone, each drop named in the load report.
3. **Given** a document with flat players and **no** retired counts, **When** the tool runs, **Then**
   it still reshapes cleanly — the eight-day window between F3 and the reshape is not broken.
4. **Given** an already-migrated document, **When** the tool runs again, **Then** no bytes change.
5. **Given** a version-old `script`, **When** the two tools run in the documented order, **Then**
   both still complete — the fix must not invert the deadlock 013 resolved deliberately.
6. **Given** a document the version step must repair, **When** the converter reaches it, **Then**
   it drops the field **wherever it finds it**, because the tree may or may not have been reshaped
   first and both are legitimate.

---

### User Story 4 — A client builds a document from the descriptor and it saves (Priority: P1)

A UI asks the library what a cue output — or a whole configuration document — looks like, fills in
the fields a user supplies, and sends it back. It saves.

**Why this priority**: gate **G3**, and the widest item here. It replaces a retired mechanism
(`initial_template`): with the template gone, the descriptor's per-type instance is the *only*
remaining answer to "what shape is a new output?", granted as a deliberate exception precisely
because per-field defaults cannot describe a nested complex type. Four of `cuems-editor`'s seven
strict xfails are this one.

**Independent Test**: for each schema, take the root instance and each nested type instance the
consumers name, and assert it saves through this library's own write path without hand editing.

**Acceptance Scenarios**:

1. **Given** a type instance with a repeated complex field, **When** it is inspected, **Then** it
   nests the way the wire nests — a list of singly-keyed objects — not an object holding a list.
2. **Given** a cue-output instance, **When** it is inspected, **Then** it carries the wrapper the
   wire carries.
3. **Given** a root instance whose root has a single complex child, **When** it is inspected,
   **Then** that child is expanded, not `null`.
4. **Given** any root instance of any schema, **When** it is saved through this library, **Then**
   the save succeeds.
5. **Given** a cue built from a cue instance, **When** it is saved as part of a script, **Then** the
   save succeeds.
6. **Given** a field whose default is a callable, **When** the instance is produced, **Then** the
   callable is **not invoked** — the cached-descriptor reason for that still holds, and the callable
   stays visible on the field.
7. **Given** the consumer's deletable workaround, **When** this lands, **Then** the frontend's
   single named transform can be deleted in one edit with no value hand-authored on its side.

---

### User Story 5 — An operator labels a node and the label persists (Priority: P1)

An operator types a human label for a node in the UI. The label survives the next discovery pass,
the next IP change, and the next adopt.

**Why this priority**: gate **G4**. `network_map.xml` has exactly one runtime writer, which never
re-reads the file, so a label written by anyone else is **silently reverted** at that daemon's next
write. The daemon delegates every map mutation to this library, so the setter belongs here. This is
the one `cuems-nodeconf` item inside 015 per **D4**, and it is what unblocks a whole planned IPC
action in that repository.

**Independent Test**: set a label on an index, assert the node object the document holds is the one
that changed, assert the document saves carrying it, and assert the signature moved.

**Acceptance Scenarios**:

1. **Given** a known node, **When** a non-empty label is set, **Then** the node is mutated **in
   place** and the call reports success.
2. **Given** a known node, **When** the label is cleared, **Then** the key is removed and the
   document saves with no label element.
3. **Given** an unknown node identity, **When** a label is set, **Then** the call reports failure
   and nothing is mutated.
4. **Given** an invalid label — empty, or whitespace only — **When** it is set, **Then** the call
   raises **before touching anything**. Measured: an in-place empty label makes the save fail
   *after* the index changed, and the daemon's pending-write retry then fails on that row until
   restart.
5. **Given** a label set to the value it already has, **When** it is set, **Then** the call reports
   success and the signature does not move, so the caller's write-if-changed path does not write.
6. **Given** an **offline** node or the controller, **When** a label is set, **Then** it succeeds —
   a label has no liveness precondition, unlike adoption.
7. **Given** a discovery merge after a label is set, **When** the merge runs, **Then** the label
   survives it.
8. **Given** the public documentation of the map's write path, **When** a consumer reads it,
   **Then** it says the file has one runtime writer and that any other writer is reverted.

---

### User Story 6 — A consumer reports a duplicate node identity without parsing prose (Priority: P2)

Two rows of a network map carry one identity. The consumer's error frame needs the colliding
identity as **data**, to send it and to log once per distinct identity.

**Why this priority**: **S1** (`cuems-editor` UR-4). The workaround now shipping is one anchored
regular expression over a **sentence in this library's own validator**, falling back to an empty
identity if the wording ever changes. That makes a sentence a load-bearing interface no test on
either side declares: this library can reword it in a patch release and break a consumer's error
reporting with no failing test anywhere. Same fault class as a cross-repository contract carried by
one side only.

**Independent Test**: load a map with one identity on two rows; assert the raised error carries the
identity and its hardware addresses as structured data, and that the consumer's regular expression
becomes unnecessary.

**Acceptance Scenarios**:

1. **Given** a map with a colliding identity, **When** it is loaded, **Then** the raised error
   carries the colliding identity as a value, not only inside a message.
2. **Given** the same error, **When** it is inspected, **Then** the hardware addresses that
   distinguish the rows are reachable as data.
3. **Given** a map with **two** distinct collisions, **When** it is loaded, **Then** a consumer can
   tell them apart without re-parsing text.
4. **Given** the existing message, **When** this lands, **Then** its operator-facing wording and its
   remedy sentence are unchanged — this adds structure, it does not reword the diagnostic.

---

### User Story 7 — A descriptor-driven form renders an open field as a field (Priority: P2)

A form built from the schema descriptor shows a node identity as a text field and a latency as a
number, not as a dropdown with one option.

**Why this priority**: **S2**, and it is in 015 on **cost-of-adjacency** grounds, not urgency —
G3 already opens the descriptor, and doing unions later re-opens the same file. Measured 2026-10-13,
and **wider than the source document states**: the source names one site; there are **five**, across
**three** schemas, and the second type is a different and arguably worse case because its field is
genuinely numeric:

| Schema | Type | Field | Reported choices | Actually valid |
|---|---|---|---|---|
| `network_map` | `NodeType` | `uuid` | `('00000000-0000-0000-0000-000000000000',)` | any uuid4, plus that sentinel |
| `settings` | `NodeConfType` | `uuid` | same | same |
| `project_mappings` | `NodeMappingType` | `uuid` | same | same |
| `settings` | `AudioPlayerType` | `output_latency_ms` | `('auto',)` | `auto`, **or 0–500** |
| `settings` | `VideoPlayerType` | `output_latency_ms` | `('auto',)` | `auto`, **or 0–500** |

The mechanism is one function merging the enumerations of a union's members. Its own documentation
treats that merge as the feature — it names the latency type as the case it *handles* — so this is a
recorded decision being corrected, not an oversight being patched.

**Independent Test**: derive each schema's descriptor and assert that no field whose type is a union
with a non-enumerated member reports a closed set of choices.

**Acceptance Scenarios**:

1. **Given** a field typed by a union **all** of whose members are enumerations, **When** the
   descriptor is derived, **Then** the merged choices are reported as today.
2. **Given** a field typed by a union with at least one non-enumerated member, **When** the
   descriptor is derived, **Then** no closed choice set is reported.
3. **Given** all five measured sites, **When** the descriptor is derived, **Then** none reports a
   one-value choice set.
4. **Given** every other descriptor fact for those fields, **When** compared, **Then** nothing else
   changed — this narrows one fact, it does not restructure the descriptor.

---

### User Story 8 — A hand-maintained configuration file stays readable after a UI save (Priority: P2)

An operator who hand-edits `settings.xml` opens it after a UI save and can still read it.

**Why this priority**: **S3**. Recorded in the source as *"worth doing; does not gate"* — and
G1 + G2 together make UI saves of configuration documents routine for the first time, which turns a
cosmetic annoyance into a predictable one. Operators hand-edit these files; a 44-line document
becoming one line is a real regression in their workflow.

⚠ **Measured cost, accepted by maintainer decision 2026-10-13.** This is not a one-liner. The
writer never indents, so changing it is a sanctioned **golden-recut event** — the arc's fourth —
touching all five golden XML documents and their manifest, requiring the two canonically-authored
corpus documents to be re-authored in the new form, and potentially flipping the contract test that
asserts a hand-authored document is reformatted on its first cycle. That test's own documentation
says such a flip must be *"a decision rather than a drift"*. This is that decision.

**Independent Test**: save a configuration document and assert the written bytes carry line breaks
and indentation; then assert the writer is still idempotent and still produces a document that
reloads equal.

**Acceptance Scenarios**:

1. **Given** any document this library writes, **When** it is written, **Then** it is indented and
   line-broken.
2. **Given** a document written by this library, **When** it is loaded and written again, **Then**
   the bytes are identical — idempotence is preserved.
3. **Given** every golden document, **When** the suite runs, **Then** the goldens and the manifest
   match the new form, re-cut as one reviewable change and recorded as a sanctioned golden event.
4. **Given** the atomic-write guarantees, **When** indentation is added, **Then** encoding, the XML
   declaration, the namespace prefix, the preserved file mode, and the temporary-plus-replace
   behaviour are all unchanged.
5. **Given** the two canonically-authored corpus documents, **When** the round-trip contract runs,
   **Then** their first-cycle byte-identity claim still holds, in the new form.

---

### User Story 9 — The planning folder and the arc's records tell the truth (Priority: P3)

A maintainer or agent opening `specs/planning/` finds documents that describe work that is still
open, and no document that describes work already done.

**Why this priority**: **S4** plus the sweep and the deletions (**D2**, **D3**, and the extension
agreed 2026-10-13). It is the lowest priority because nothing is blocked on it — and it is in scope
because this folder's deletion policy says a planning document's job ends when the decision it was
tracking is made and acted on, and because 015 is the feature that finally makes every one of those
decisions.

**Independent Test**: after the polish phase, assert that every document named for deletion is gone,
that every stale statement named for correction is corrected, and that no requirement in this spec
is left without a disposition.

**Acceptance Scenarios**:

1. **Given** the public documentation of the wire projection, **When** a consumer reads it, **Then**
   it states **once** that the projection fills a model default for an optional element the document
   omitted, and that this is a general property of the projection rather than a fact about any one
   field.
2. **Given** `specs/planning/`, **When** the polish phase completes, **Then** the nine documents
   named in FR-091 are deleted, and each one's deletion condition is satisfied at that moment.
3. **Given** the execution companion, **When** it is read, **Then** its stale statements named in
   FR-092 are corrected.
4. **Given** the two sweep gaps found on 2026-10-13, **When** the polish phase completes, **Then**
   each has a disposition and no residue is orphaned.
5. **Given** the coordinated tag's work order, **When** it is read in any of its homes, **Then** all
   of them agree.

---

### Edge Cases

- **A tolerant write target whose parent directory does not exist.** Measured: the save fails on the
  temporary file. Correct, separate, and explicitly not fixed here.
- **A tolerant write target for a file the caller then never writes.** Returning a path is not
  creating one; nothing is created as a side effect of asking.
- **Projecting a project's settings when the project has no settings file.** Measured 2026-10-13:
  nothing is retained — the document attribute is `None` and the settings dictionary is `{}`, so
  there are in fact **no defaults to project**, contrary to the source document's reading. Settled
  as a valid empty document (FR-015), which the schema permits.
- **Projecting a project section on a manager that never loaded a project.** Distinct from the
  above and must stay distinct (FR-015a) — one is an ordinary first-run state, the other is a
  programming error.
- **A label set between two discovery passes.** Measured: a discovered node carries only the
  discovered fields, so a merge copies those and the label survives. Pinned rather than assumed.
- **A label on a node the index has not loaded yet.** The readiness window is the daemon's, not this
  library's; an empty index simply reports the identity as unknown.
- **A union whose members are all enumerations.** Must keep merging. The narrowing is conditional,
  not a removal.
- **An instance for a type that is recursive.** The existing cycle guard governs; a default must not
  turn a guarded branch into an infinite expansion.
- **A required field with a callable default, inside an instance that must now save.** The callable
  is still not invoked, so "saveable" and "no frozen fresh identifier" must both hold.
- **A pre-F3 document with the retired counts in a *reshaped* tree.** Arises inside the tool's own
  pre-write validation probe, which is exactly where today's dead end is. The converter must handle
  it, and the composition is what the test exercises.
- **A pre-F3 document with more than one node section.** The converter addresses one; whether that
  is sufficient is a question the fix must answer rather than inherit.
- **Indentation of a document that already contains mixed content or significant whitespace.**
  Indenting must not change any element's text where that text is data.
- **A sibling checkout that is absent, not merely moved.** The cross-repo contract tests shell out
  to sibling trees; a developer without those checkouts must not be told a guide is wrong.

---

## Requirements *(mandatory)*

### Functional Requirements — G1: a write target for a file that does not exist

- **FR-001**: The library MUST provide a public way to obtain the canonical path of a configuration
  file that does not exist yet, for both the node-level and the project-level path conventions.
- **FR-002**: That capability MUST be an **addition**. Both helpers MUST keep refusing a missing file
  for every existing caller and every existing call signature; the refusing behaviour stays the
  default.
- **FR-003**: The tolerance MUST NOT be acquirable by accident from an existing positional call
  site.
- **FR-004**: The path convention MUST remain defined in exactly one place. No consumer is expected
  to reconstruct `projects/<uname>/<file>`.
- **FR-005**: Asking for a tolerant target MUST NOT create a file, a directory, or any other
  side effect.
- **FR-006**: The four save accessors' default-path behaviour MUST be unchanged for an existing
  file, and MUST be stated for a missing one.
- **FR-007**: This library's own suite MUST stop replacing a public method to obtain a write target;
  that workaround is the defect's in-repository footprint and leaving it would keep a passing test
  that documents the gap as permanent.
- **FR-008**: The consumer-side obligation MUST be recorded: `cuems-editor`'s strict xfail for this
  gate does **not** flip on a library change alone — that repository must also pass the tolerance on
  at its own write site.

### Functional Requirements — G2: a public read for a project's settings

- **FR-010**: `project_settings` MUST be publicly readable as a wire-shaped projection of the
  document the library has loaded.
- **FR-011**: That projection MUST go through the **same** projection body as every other
  configuration section. A second projection is forbidden.
- **FR-012**: `project_settings` MUST be a member of the public section list, so the error that
  enumerates valid sections names it.
- **FR-013**: The projection MUST round-trip: project, ingest, save, reload, compare equal.
- **FR-014**: No consumer may be required to reach a private attribute to read this document. The
  consumer's public-surface test forbidding that is correct and stays correct.
- **FR-015**: When the project has **no** settings file, the projection MUST return a valid empty
  document — zero settings — because the schema declares the settings element with `minOccurs="0"`
  and so a document carrying none is valid. Measured during planning: that projection is `{}`, and
  such a document **saves** (verified), so this is reachable without a new shape. "No file" and "a file with no settings" therefore
  project identically, which is correct rather than lossy: the schema says they are the same
  document.
- **FR-015a**: The "not loaded" exception MUST stay reserved for *not loaded*. A load that
  succeeded and tolerated an absent file MUST NOT answer with the same exception as a manager whose
  project configuration was never loaded, or a consumer cannot tell a programming error from an
  ordinary first-run state.
- **FR-015b**: Determining whether the file exists MUST remain the consumer's own call, through the
  existence-checking path helper G1 leaves in place. The projection MUST NOT acquire an existence
  flag of its own — that would be a second answer to a question one call already answers.
- **FR-016**: The pre-existing mismatch that makes the legacy **`project_conf` dictionary** always
  empty MUST be left alone unless this feature decides otherwise explicitly — it is a separate latent
  defect recorded in the code, and repairing it silently would change what consumers read. ⚠ This is
  **not** the document G2 projects: `project_conf` is the legacy flattened dict, empty because
  `ProjectSettings.main_key` does not match the decoded root's content key, while FR-010 projects the
  held root object. Naming the attribute matters because the two were conflatable, and a reader who
  conflates them concludes G2 is blocked by this requirement, which it is not.

- **FR-017**: The consumer-side obligation MUST be recorded: `cuems-editor`'s strict xfail for this
  gate does **not** flip on a library change alone either — that repository must also remove
  `project_settings` from its refusal set and give it a load step. Stated as its own requirement
  rather than left implicit, because G1's identical obligation (FR-008) was the only one the first
  pass wrote down, which made SC-012 read as achievable here.

### Functional Requirements — G3: the descriptor's instance

- **FR-020**: A type instance MUST nest repeated complex content the way the wire nests it — a list
  of singly-keyed objects — in **every** schema, not only for cue outputs. Measured sites include
  cue output channels, network-map node rows, and project-mapping defaults.
- **FR-021**: A cue-output instance MUST carry the wrapper the wire carries.
- **FR-022**: A root instance whose root type has a single complex child MUST expand that child
  rather than reporting it as absent. Measured: two of six roots report only `null` today.
- **FR-023**: Every schema's root instance MUST be saveable through this library's own write path
  without hand editing.
- **FR-024**: Every type instance the consumers name MUST be saveable as part of the document that
  contains it.
- **FR-025**: Required fields with no model-layer default MUST be seeded, inside instance
  construction, with a value that satisfies their declared type, so FR-023 and FR-024 can hold.
  Measured on this branch: **64 such scalar fields across 19 types in the show schema alone.**
- **FR-026**: FR-025 **reverses a recorded decision** — the descriptor's documented position that an
  instance is *"not required to be schema-valid… a seed the consumer fills"*. The reversal MUST be
  recorded in the same place as a decision, not left as a silent contradiction, and the measurement
  behind it carried with it.
- **FR-026a**: FR-025's seeding MUST NOT change the per-field **default** fact, and MUST NOT change
  any field's **repairability** classification. The classification's first rule is *"no default means
  unrepairable"*, so a model-layer default for these 64 fields would move them to repairable — and
  feature 008's load path repairs a repairable violation where it raises on an unrepairable one.
  Seeding an instance is a construction convenience; it MUST NOT convert 64 fields across 19 types
  from "the document is refused" to "the document loads with a fabricated value", for every consumer,
  as a side effect.
- **FR-026b**: The seed for a field MUST satisfy that field's declared type and facets, not merely
  its primitive kind. A restricted string whose facets forbid the empty string, and an identity type
  with a pattern, each need a seed that validates — which is the measurable difference between
  "a value of the right Python type" and "a document that saves".
- **FR-027**: A callable default MUST still not be invoked when an instance is produced, and MUST
  still be visible on the field itself. The caching reason for that stands: invoking a fresh-identity
  generator once would freeze one value and hand it to every later caller.
- **FR-028**: A value supplied for FR-025 MUST be **derived** from the schema — the field's own type
  and facets — by one mechanism in the descriptor's own machinery. No per-field hand-written table of
  fallbacks, and no per-type special case.
- **FR-029**: Every other descriptor fact MUST be unchanged — the five pre-existing per-type facts
  keep their meaning.
- **FR-030**: The instance MUST remain a value a consumer can serialise; nothing non-serialisable
  may enter it.
- **FR-031**: The consumer's deletable workaround MUST become deletable in one edit, with no value
  hand-authored on its side.

### Functional Requirements — G4: the operator's node label

- **FR-035**: The node index MUST provide an in-place setter for the operator-owned label, keyed by
  node identity. **One concept, three spellings, stated once here**: this document calls it the
  *label*; the schema element, the model field and the setter call it **`alias`**
  (`NodeIndex.set_alias`); `cuems-nodeconf`'s IPC action that drives it is **`node_set`**. Every
  later requirement means the same field.
- **FR-036**: It MUST validate the label **before** mutating anything: a non-empty, non-blank string,
  or an explicit clear. Anything else raises.
- **FR-037**: Clearing MUST remove the key, because the element is optional.
- **FR-038**: It MUST report failure for an unknown identity, and success otherwise — whether or not
  the value changed. The caller distinguishes "unchanged" by the index signature, as the existing
  adoption call site does.
- **FR-039**: It MUST mutate the node object the document holds, honouring the existing aliasing
  contract. Rebinding a copy is a breaking change, not a tidy-up, and would break a consumer while
  leaving every suite green.
- **FR-040**: The aliasing contract test MUST cover it.
- **FR-041**: The signature MUST already include the label, so a write-if-changed path needs no
  further change. Verified on this branch: it does.
- **FR-042**: The setter MUST cover the label **only**. A general "set operator fields" call is
  deliberately not provided, because it would invite writes to fields discovery overwrites.
- **FR-043**: An offline node and the controller MUST both be labellable — a label has no liveness
  precondition.
- **FR-044**: A discovery merge MUST NOT clear a label, and that MUST be pinned by test rather than
  argued from the merge's implementation.
- **FR-045**: The public documentation of the map's save and ingest paths MUST state that the file
  has exactly one runtime writer and that any other writer's changes are reverted. Two consumers have
  already read those calls as the way to persist a UI edit.
- **FR-046**: The semantics MUST remain identical to those stated in `cuems-nodeconf`'s own brief,
  which states them in the same words. Any divergence is a change to a two-repository contract.

- **FR-047**: The consumer-side obligation MUST be recorded, and it is the **only** gate whose
  sibling half is in a *second* repository: `cuems-editor`'s xfail for G4 flips when the index setter
  lands **and** `cuems-nodeconf` ships the `node_set` handler that calls it. This feature delivers
  the library half and discharges nodeconf's stated ordering (SC-013); it does not ship either
  repository's code.

### Functional Requirements — G5: the version step must find its fields in either shape

- **FR-050**: The `settings` version step MUST locate and drop the two retired counts whether or not
  the document's players have been reshaped.
- **FR-051**: It MUST drop the field **wherever** it finds it, not assume one shape — on the load
  path the tree has not been reshaped, inside the reshape tool's pre-write probe it has, and both
  are legitimate.
- **FR-052**: It MUST stay idempotent: a document with neither field present converts to itself.
- **FR-053**: The red test MUST be the **composition** — the reshape tool run over a document that
  is both pre-013 and pre-F3, asserted reshaped and then loaded. A unit test on the converter with
  an already-reshaped tree would pass the moment paths are added and would not catch the next
  instance of this class.
- **FR-054**: The tool's order MUST NOT be inverted. Converting before reshaping re-creates, for the
  show schema, exactly the dead end this fixes for the settings schema. The order is right; the
  converter's paths are stale.
- **FR-055**: A flat document **without** the retired counts MUST keep migrating cleanly — the
  eight-day window between the two schema changes is a real population.
- **FR-056**: The tool MUST still refuse to write a document that would not validate. The fix makes
  more documents valid; it does not relax the guarantee.
- **FR-057**: Every drop MUST still be named in the load report.
- **FR-058**: The operator-facing triage question MUST be documented as "does it carry the retired
  counts?", not "is it flat-shaped?" — the two are different populations and the second is the
  wrong test.

### Functional Requirements — S1: the collision carries its identity

- **FR-060**: A node-identity collision MUST raise a **nameable** exception type a consumer can
  catch, published from the one public errors module, carrying the colliding identity as an
  attribute rather than only inside a message.
- **FR-060a**: That type MUST be a `ValidationError` subclass, so a consumer that catches the
  general case keeps catching this one and the existing exception tree's shape — the contract the
  errors module documents — is preserved rather than widened at the root.
- **FR-060b**: Its carried violation MUST be populated, locating the failure as
  `(identity, "uuid")` — the pair form the violation type already documents as addressable without
  parsing a string. A caller that does not name the subclass MUST still get the identity.
- **FR-061**: The hardware addresses that distinguish the colliding rows MUST be reachable as data
  on the same exception, because they are the only thing that tells the rows apart and today they
  exist only inside a sentence.
- **FR-062**: Two distinct collisions in one document MUST be distinguishable without re-parsing
  text, so a consumer can log once per distinct identity.
- **FR-063**: The existing operator-facing message, including its remedy sentence and the command it
  names, MUST be unchanged. This adds structure; it does not reword a diagnostic that reads well.
- **FR-064**: The message-shape recognition this library already performs MUST keep working. It
  exists because the failure was not distinguishable by exception type; once FR-060 makes it so,
  that recognition MAY become type-based — but the message-shape path MUST keep answering for any
  caller still on it, and the change MUST NOT alter which cases are recognised.
- **FR-065**: A test on **this** side MUST declare the structured contract — the exception type, its
  attributes and its populated violation — so the interface stops being a sentence that no test on
  either side declares.
- **FR-065a**: The new exception type MUST join the errors module's published surface and its
  documented hierarchy, since a type a consumer cannot import is a type it cannot catch. This is
  the module's **first** addition since feature 009's.

- **FR-065b**: The consumer-side completion marker MUST be recorded and **verified in that
  repository rather than predicted here**: `cuems-editor` removes its anchored pattern over this
  library's prose and the empty-string fallback behind it, and its handler names the exception type.
  That removal — not a test passing here — is what SC-009 measures, and it had no owner until this
  requirement.

### Functional Requirements — S2: a union is not an enumeration

- **FR-066**: A field typed by a union MUST report a closed set of choices only when **every** member
  of that union is an enumeration.
- **FR-067**: All five measured sites MUST stop reporting a one-value choice set.
- **FR-068**: A union all of whose members are enumerations MUST keep reporting their merged values.
- **FR-069**: The existing documentation that treats the partial merge as correct MUST be corrected
  where it stands, since it names one of the five sites as the case it handles.

### Functional Requirements — S3: the writer indents

- **FR-070**: Documents this library writes MUST be indented and line-broken.
- **FR-071**: The writer MUST remain idempotent: a document it wrote, reloaded and rewritten, is
  byte-identical.
- **FR-072**: Encoding, the XML declaration, the namespace prefix, the preserved target file mode,
  and the temporary-plus-atomic-replace behaviour MUST all be unchanged. None of them is optional
  and each has a recorded failure behind it.
- **FR-073**: Indentation MUST NOT alter any element's text where that text is data.
- **FR-074**: The golden documents and their manifest MUST be re-cut as **one** reviewable change,
  recorded as a sanctioned golden event with its reason, the way the arc's three earlier recuts were.
- **FR-075**: The two canonically-authored corpus documents MUST be re-authored in the new form so
  that their first-cycle byte-identity claim still holds, rather than being reclassified into the
  reformatted set.
- **FR-076**: Any flip of the contract test that asserts a hand-authored document is reformatted on
  its first cycle MUST be recorded as this decision, which that test's own documentation asks for.

### Functional Requirements — S4 and the sweep

- **FR-078**: The public documentation of the wire projection MUST state **once** that the projection
  fills a model default for an optional element the document omitted, and that this is a general
  property of the projection rather than a fact about any one field — stated where the rendered API
  documentation picks it up, not in a planning file.
- **FR-079**: The show-document load MUST be recorded as **straddling** its budget, with the measured
  band, not as a clean overrun. Measured at the branch point on the interpreter `hatch` resolves,
  by the budget's own method, **16 samples across three windows**: band **16.465–17.750 ms**, median
  **16.864**, pooled spread **7.8%**. **14 of 16 exceed the 16.5 ms budget and 2 do not**, so the
  assertion is **flaky on an unchanged tree** — which is a worse outcome than a clean failure,
  because an intermittent red is indistinguishable from a real regression appearing.
- **FR-079a**: The straddled **line** MUST be replaced by a comparison against the **measured band**,
  following this repository's own precedent for this exact pathology: 012's R14 replaced 008's
  straddled `network_map` budget with a band comparison, on the recorded ground that *"asserting a
  straddled budget would fail on an unchanged tree"*. This is **not** a fourth raise of the budget —
  the objection to a raise stands (008 → 35.99, 012 → 15.0, 013 → 16.5, each time with a mechanism
  named; a detector raised whenever it fires passes by construction). Changing a line into a band is
  a change of **instrument**, which 012 made deliberately and documented.
- **FR-079b**: The recorded state MUST be visible in the test, not only in a baseline document, so
  that a later reader cannot mistake "straddled and accepted" for "passing". The band and the
  sample count MUST both appear, because a band from five samples in one window is what this
  feature's own first two passes got wrong.
- **FR-079c**: The drift MUST be recorded as a follow-up with an owner, carrying this feature's 16
  measurements, the budget's history (008 → 35.99, 012 → 15.0, 013 → 16.5), and the fact that it
  **survived a full interpreter migration** (CPython 3.11.2 → 3.11.9, two builds) — which is what
  makes it a real drift rather than an instrument artefact. Against 013's own 14.07–14.96 ms
  measurement the band is **+13% to +19%**. It MUST NOT be investigated inside this feature.
- **FR-080**: The four stale cross-repository assertions MUST be resolved **by assertion class**,
  because the two classes fail for different reasons and one policy mishandles one of them:
  - **Provenance** — a commit a landed guide names as "verified at" is a **dated measurement**.
    Asserting it against today's tree is a category error, and the policy of record already says a
    landed spec's references as they stood *at the time* are not retroactively rewritten.
  - **Operator instructions** — a version an operator must require, or a signal they are told to
    watch for, must be true **today**. Freezing a wrong instruction would leave a guide sending
    someone to watch for a signal that no longer exists.
- **FR-080a**: Provenance pins MUST carry the date of their measurement, and their **resolution**
  MUST NOT be asserted against a sibling's moving branch. Measured 2026-10-13: both pinned commits
  are absent from their sibling's history entirely, so they are dead references rather than moved
  ones.
- **FR-080b**: The two false operator-facing claims in 012's guide MUST be **corrected** — the
  coupled engine version (the guide requires `0.1.0rc7`; that tree declares `0.1.0-rev1`, a renamed
  scheme under which "rc7 or later" is not merely stale but unverifiable) and the status signal the
  guide tells an operator to watch for (absent from that repository's controller source). This is a
  documentation defect, fixed as one, and MUST NOT be presented as a rewrite of history.
- **FR-080c**: Every surviving cross-repository assertion MUST resolve a sibling at its
  **`xml-refactor-merge-candidate` tag**, not at its tip. A tag is a stable reference by
  construction; a tip never was one, which is why this collision occurred twice. An absent tag MUST
  skip with a reason — never pass silently — and a present tag whose tree contradicts the claim MUST
  fail.
- **FR-080d**: Re-cutting any candidate tag MUST re-run that validation across the **whole** set.
  This is the recorded lesson of 011, where the tag set did not compose for a day because one
  member's tag pointed at a tree shipping a superseded value: *a candidate tag set is only as current
  as its least current member, and no packaging relation expresses that*. The mechanism FR-080c asks
  for is the first thing in the ecosystem that would express it.
- **FR-080e**: The coordinated validation MUST be usable before every sibling is tagged. Measured
  2026-10-13: **four of seven** carry the tag (`cuems-common` `91b2d25`, `cuems-nodeconf` `c29c25c`,
  `cuems-power-bridge` `cabbb3e`, `cuems-frontend` `531004b`); `cuems-engine`, `cuems-editor` and
  this repository do not. A partial tag set MUST yield a partial, honest result.
- **FR-080f**: The values this repository's own records state for those tags MUST be re-verified
  against the tags themselves, not transcribed. Measured 2026-10-13: **all three recorded in
  `CLAUDE.md` have moved** since they were written — exactly the drift FR-080c prevents, found by
  looking rather than by being told.
- **FR-081**: A developer without the sibling checkouts MUST NOT be told a guide is wrong.
  **Already satisfied** — verified 2026-10-13: both contract test files skip with a stated reason
  when a sibling is not checked out. The requirement is kept as a property this feature must not
  regress, not as new work.
- **FR-090**: Every row of the source document MUST end this feature either implemented or recorded
  as declined, which is the condition the source document names for its own deletion.
- **FR-091**: The polish phase MUST delete the following nine documents, each of which names its own
  deletion condition and has it satisfied by this feature: the seven landed one-shot prompts of
  §9.3's last row (`013-specify-prompt.md`, `editor-specify-prompt.md`,
  `editor-001-amend-after-013-prompt.md`, `feature-014-sibling-gate-prompt.md`,
  `nodeconf-uuid4-fixture-migration-prompt.md`, `media-pixel-dimensions-for-xml-refactor.md`,
  `stored-media-values-preimplementation.md`), plus `upcoming-feature-requirements-2026-10-02.md`
  (this feature's own source) and `settings-reshape-defeats-f3-conversion-defect.md` (G5's record).
- **FR-092**: The execution companion's stale statements MUST be corrected: its §3.3 flag **F1**,
  which describes schema annotations as pending when all six schemas carry them (verified
  2026-10-13), and its §5 step 6, which records 014 as 45/46 with one task open when that feature
  closed at 46/46.
- **FR-093**: The two documents the §9 sweep did not reach MUST be dispositioned:
  `refactor-sequencing-2026-10-01.md`, whose own stop-condition is now satisfied — the frontend flow
  it waited for has landed and carries a candidate tag — but whose residue (the adoption/liveness UI
  tier, *"new feature work… no other home yet"*) MUST be re-homed **into a named destination before
  that document is deleted**, namely a new `specs/planning/adoption-liveness-ui-tier.md`; and the
  `specs/planning/xml-rebuild/` subtree (ten design documents and eleven consumer prompts), which
  MUST acquire a per-document disposition.
- **FR-093a**: No document may be deleted by the sweep until the destination of every piece of its
  residue **exists**. "Re-homed" is a file that exists and holds the content, not an intention
  recorded in a disposition table — otherwise the sweep is how the residue is lost.
- **FR-094**: Every home of the coordinated tag's work order MUST agree after this feature — the
  execution companion, `CLAUDE.md`, and the gate list — so that "the tag comes after 011–015" and
  "015 is the gates" are both true at once.
- **FR-095**: No artefact of this feature — requirement, comment, docstring or diagnostic — may cite
  a feature *number* as a stand-in for a **live obligation** described in another document. Name the
  document or name the behaviour; numbers get reassigned and comments do not get swept, which has now
  cost two passes. The model defect is `ConfigManager`'s refusal reading *"…until feature 015"* for
  work that had moved to an unnumbered planning document.
  **What this does not forbid, stated because the prohibition was read too widely on its first
  pass**: a *dated provenance citation* of landed work in this repository — "008's load path",
  "012's R14 precedent", "013's 14.07–14.96 ms", "011's tag-set lesson" — is a reference to a frozen
  record that cannot be reassigned, and it is how this repository's specs cite their own history.
  This document uses them deliberately. The test is whether a reader must look the number up to
  learn **what they must do**: if so, name the behaviour; if it merely says where a measurement or a
  decision came from, the number is the most precise thing available.

### Cross-cutting requirements

- **FR-100**: Every change here MUST be **additive to the public surface**. No existing public call
  changes its signature's meaning, its default behaviour, or its exception type. G5 is a defect fix
  and changes behaviour only in the direction of succeeding where it previously refused.
- **FR-101**: No schema version step may be added. The five gates are public-surface and defect
  work; `doc_version` does not move for any schema.
- **FR-102**: The per-schema decode asymmetry MUST be preserved — exactly one configuration schema
  runs the adapter table, and normalising that would silently retire a measured guarantee.
- **FR-103**: Every sibling obligation MUST be stated with the test node that flips, and MUST be
  verified against that sibling's checkout rather than predicted. 014 learned this twice: a
  prediction that a sibling's test would close by re-run was wrong, and a gate without a control arm
  attributed 151 of someone else's failures to the feature under test.
- **FR-104**: Any sibling verification run in parallel MUST use a **per-session worktree** of this
  repository, never the shared checkout. A prompt that tells N parallel sessions to mutate one shared
  resource is a defect in the prompt.
- **FR-105**: Sibling fixtures this feature breaks MUST be closed **in this feature**, not left for
  the next gate to discover with its own signal buried underneath — 014's cross-cutting finding, paid
  for by eleven hand-rewritten documents across two repositories.
- **FR-106**: Every obligation this feature places on another repository MUST be collected in **one**
  document, `specs/015-consumer-gate-closure/consumers_works.md`, one row per obligation, each
  carrying: the repository, what that repository must do, the test node or artefact that marks it
  done, whether it flips on a library change alone, and its verification status measured in that
  checkout. The five gates and the four stragglers are **not** symmetric here — four of this
  feature's items are complete when the library lands, and five have a half this feature cannot
  write — and a reader of the gate list cannot currently tell which is which. `cuems-editor`'s
  tag-readiness record is that repository's view of the same set; this document is ours, and the two
  must agree row by row.
- **FR-106b**: The count is **ten**, measured 2026-10-13, not the eight a reading of the gate list
  gives: the two that a gate-shaped reading misses are `cuems-editor`'s `_root_instance` docstring,
  which states the exact position FR-026 reverses and would have gone stale silently, and
  `cuems-editor`'s own tag-readiness record, whose state the first draft of SC-012 made a deliverable
  of **this** repository.
- **FR-106a**: No consumer obligation may be stated only as a prediction. Each row's status MUST be
  one of *verified done*, *verified outstanding*, or *not verifiable yet* with the reason — measured
  against that sibling's checkout at its `xml-refactor-merge-candidate` tag where it has one
  (FR-080c), and never against a sibling's moving tip.
- **FR-107**: The **type** findings in `src/` MUST be reduced wherever they are reducible without a
  behaviour change. Measured at the branch point: **80 in 26 files**. Every finding MUST end this
  feature either **fixed** or **recorded with a one-line reason** why it is not — an unexamined
  finding is not permitted, because a baseline nobody has read is a number rather than a standard.
  Code quality is a requirement of the coming stable version, not a courtesy of it.
- **FR-108**: Suppression comments MUST be swept, and the three classes MUST be treated differently
  because they fail differently:
  - **A stale suppression MUST be deleted.** Measured: **all eleven** `# type: ignore` comments in
    `src/` are unused — `--warn-unused-ignores` reports every one — and two `# noqa: F401` are stale
    against a rule that *is* enabled (`NodeList.py:22`, `init_node.py:36`).
  - **An inert suppression MUST become a plain comment, keeping its sentence.** Sixteen `noqa`
    directives in `src/` name rules this project does not select (ten `BLE001`, two `N801`, and one
    each of `C901`, `E501`, `SIM115`), so they suppress nothing — but most carry the *reason* the
    code is written that way (*"a broken universe must still name itself"*). Deleting the directive
    must not delete the rationale: the sentence is the valuable half and is the only record of the
    decision.
  - **A suppression inside a frozen module MUST be left alone.** `xml/Parsers.py` and
    `xml/XmlBuilder.py` are excluded from lint by recorded decision (feature 004) precisely so that
    nothing reformats a module whose whole guarantee is that it does not change, and both are
    scheduled for deletion with the stable release. `XmlBuilder.py:98`'s ignore stays, even though it
    is both unused *and* names a code that does not exist (`attr-union`, for `union-attr`) — which is
    itself the evidence that it never suppressed anything.
- **FR-108a**: Enabling a lint rule this project does not currently select is **out of scope**. The
  sixteen inert directives are evidence that someone once considered `BLE001` and the others; whether
  to adopt them is a project decision, not a side effect of a sweep.
- **FR-109**: Both static baselines MUST become a **descending ratchet**. The figure recorded at the
  end of this feature MUST be lower than the branch point's, and that new figure becomes the gate —
  rather than the hold the first pass specified, which would have let 80 type findings and 606 lint
  findings sit unchanged forever provided nothing was added.
- **FR-110**: The sweep MUST NOT change behaviour, and MUST be shown not to: no golden moves, no wire
  dict moves, no load outcome changes, and the suite stays green. It MUST land as **its own commit**,
  separately from every story's code, because **438 of the 606 lint findings are whitespace on blank
  lines** and a sweep mixed into a feature's diff makes both unreviewable.
- **FR-111**: Two hazards MUST be respected, neither of which is visible from a finding list:
  - **Import sorting (`I001`, 17 findings in `src/`) MUST NOT be bulk-auto-fixed.** This package has
    documented import-order dependencies — `adapters._register_enums()` runs at import time and
    imports `NodeRole` back out of `NodeList` while that module is still initialising, which is why
    `NodeList` is a lazy module `__getattr__` — plus three deliberate late imports marked
    `# noqa: E402`. A re-sorted import block can turn a working lazy import into an `ImportError`
    that neither the type nor the lint gate would catch. File by file, suite after each.
  - **`E721`'s correct fix is `type(x) is Y`, never `isinstance(x, Y)`.** `type(x) == Y` asserts the
    **exact** type, and this project depends on the distinction: 013 keeps the cue classes
    subclass-dispatchable and puts a bare `MediaCue` in an `isinstance` tuple *because* an unknown
    class decodes to it. Converting the 24 `E721` findings in `tests/` to `isinstance` would silently
    weaken 24 assertions from "exactly this type" to "this type or any subclass".
- **FR-112**: `tests/`' 29 `E712` comparisons MUST be examined rather than rewritten in bulk. Feature
  014 made booleans real (`xs:boolean`), so a test comparing `== True` may now be asserting genuine
  boolean identity where before it was comparing strings. `is True` is usually the right fix and
  sometimes the assertion is the point.
- **FR-113**: Both static instruments MUST be **version-bounded**, because a baseline whose tool
  version floats is not a baseline. This is FR-PERF-005's rule — *name the build, not just the
  version* — applied to the two tools whose **finding counts** this feature turns into gates.
  Measured at the branch point: `mypy>=1.0.0` is lower-bounded only and resolves **2.4.0**, and
  **`ruff` is not pinned at all** and resolves **0.17.0**. The second is the worse case and is the
  one nobody named: at 0.x the **minor** version is the breaking unit, so an ordinary `0.17 → 0.18`
  can add rules and move the lint figure with no change to the code. A bound is not a freeze — a
  bump inside it may still move the count, which re-baselines with the delta attributed to the tool
  instead of being mistaken for a regression.
- **FR-113a**: The remaining test-env dependencies MUST NOT be bounded by this feature. `pytest`,
  `pytest-mock`, `pytest-cov`, `hypothesis` and `coverage` are all unpinned, and that is a separate
  question: none of them defines a recorded figure, and a changed test count is visible in the suite
  line where a changed lint count is invisible until someone diffs it.
- **FR-UX-001**: Every new or changed message MUST follow this project's established diagnostic
  shape: name the document, the locus, the value and the remedy. The refusal that names its own
  remedy — measured as reading correctly in the one place it matters — is the model.
- **FR-UX-002**: No operator-facing wording that currently reads well MUST be reworded as a side
  effect of adding structure behind it.
- **FR-UX-003**: Every new public call MUST be documented where the rendered API documentation picks
  it up, including the one-runtime-writer warning of FR-045 and the projection property of FR-078.
- **FR-UX-003a**: Where the module holding a new public call is **not** rendered today, it MUST be
  added to `docs/` as part of this feature. Measured 2026-10-13: `docs/` is mkdocstrings over an
  **explicit list** of modules, and three of this feature's four documentation obligations land
  outside it — `cuemsutils.errors` (FR-065a's new exception type),
  `cuemsutils.tools.NodeList` (FR-035's setter) and `cuemsutils.config.network_map` (FR-045's
  one-runtime-writer warning) are rendered **nowhere**. Only FR-078's `cuemsutils.helpers` is already
  in the list. A docstring in an unrendered module is not published documentation, which is the
  premise FR-UX-003 rests on and the reason two consumers read a call the wrong way in the first
  place.
- **FR-UX-003b**: That gap MUST be closed by a **test**, not only by this feature's edit: every
  module this feature adds a public call to MUST be asserted present in the rendered documentation,
  so the next feature's public addition cannot repeat it silently.
- **FR-PERF-001**: This feature MUST state its performance budgets against figures **measured on its
  own branch point**, recorded in its own baseline document, and MUST record an exceeded budget as
  exceeded rather than restating it as passing.
- **FR-PERF-002**: Budget tolerance MUST account for this instrument's measured resolution, measured
  across **more than one window**. Pooled over 16 samples in three windows, the show-document load's
  spread is **7.8%**; the per-window spreads were **2.9%, 7.7% and 4.8%**. So **115%** is the
  tolerance, and 014's recorded ±4–8% is **corroborated**, not superseded.
  ⚠ This feature revised the tolerance to 110% on the strength of a single five-sample window
  reading 2.9%, and that was wrong — the narrowest window is not the instrument. A tolerance claim
  MUST rest on samples from at least two separated windows.
- **FR-PERF-003**: The paths this feature actually touches MUST each carry a budget: the document
  **write** path (S3 adds a pass over every written tree; the show-document save measures
  **13.612–14.297 ms** at the branch point over eight samples), the **descriptor derivation** (G3 and
  S2 both change it; it measures **1.015–1.060 ms** for the show schema over eight samples), and the suite (**8.73–8.93 ms/test**). All three
  re-measured 2026-10-13 after the toolchain migration, on the interpreter `hatch` resolves.
- **FR-PERF-005**: Every recorded figure MUST name **the interpreter build** it was taken on, not
  only the version. Two CPython 3.11.9 builds exist on this box and they differ by **32–72%** on
  these paths; a figure labelled only "3.11.9" is not reproducible.
- **FR-PERF-004**: The three configuration and show **load** paths MUST be measured and reported even
  though this feature does not intend to change them, because FR-079's finding is on exactly one of
  them and a feature that edits the writer must prove it did not move the reader.

### Key Entities

- **Configuration write target** — the canonical path of a configuration file, whether or not it
  exists. Node-level and project-level conventions, each owned by exactly one place in this library.
- **Configuration section projection** — one configuration document's values in wire form, produced
  by one projection body shared across every section and both domains. `project_settings` joins it
  here.
- **Type instance** — a constructible, nested exemplar of one complex type, derived from the schema
  and the model's defaults. After this feature it is in wire shape and it saves.
- **Field description** — the per-field facts the descriptor emits. One of them, the closed choice
  set, stops being reported for a field whose type is only partly enumerated.
- **Node index entry** — one node's row in the network map, held by reference so that a mutation is
  already visible in the document about to be serialised. The operator-owned label is the one field a
  consumer may now set.
- **Identity collision** — two or more map rows carrying one node identity, with the hardware
  addresses that distinguish them. Becomes a nameable exception carrying both as data, having been
  only prose.
- **Version step** — a registered transformation from one document version to the next, which must
  read what is on disk — and after the device reshape, "what is on disk" has two spellings.
- **Written document** — the bytes this library produces: atomic, mode-preserving,
  prefix-registered, declaration-carrying, and from this feature on, indented.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can save a project configuration that has never been saved before, and the
  file lands in the canonical location without the consumer reconstructing any path convention.
- **SC-002**: An operator can open a project's settings form, see the values the file holds, change
  one, save, and reopen to find the change — for all **four** configuration domains, where today it
  is three.
- **SC-003**: Every `settings.xml` in the measured dead-end population migrates with **one**
  invocation of the shipped tool. The reference population is **11 documents across two sibling
  repositories, of which 0 migrate today**; the target is 11 of 11, verified by running the tool over
  restored copies of those documents. **The population is pinned by ref, not described** — located
  2026-10-13 by searching both repositories' histories for the hand-rewrites 014's gate pass paid
  for, because the documents no longer exist in either working tree:
  - **9** at `cuems-power-bridge@dd1256f^` — `tests/fixtures/network_map/map-{controller-only,incomplete,mixed,no-self,none-adopted,partial-resolve,pre007,two-adopted,unresolvable}/settings.xml`
  - **2** at `cuems-nodeconf@61c5705^` — `tests/fixtures/etc_cuems/settings{,_sentinel}.xml`
- **SC-003a**: The **one surviving live** dead-end document MUST also migrate, and it is evidence
  that this population is not merely historical: `cuems-engine`'s `dev/test_xml_files/settings.xml`
  carries the retired counts at its tip (measured 2026-10-13, the only such document across all seven
  checkouts). It is a twelfth case, outside SC-003's hand-rewrite reference population, and it is the
  one a developer actually hits today.
- **SC-004**: No further hand-rewrite of a `settings.xml` is required by any repository. Two sessions
  have each hand-written what the tool should have produced; the count stops at two.
- **SC-005**: A client can build any configuration document, and any cue output, from the
  descriptor's instance and save it with **zero** hand-authored values and **zero** local reshaping.
- **SC-005a**: The number of fields whose repairability classification changes is **zero**, and the
  number of load-path outcomes that change for any existing document is **zero**. Measured by
  comparing the full repairability map and the load outcomes before and after.
- **SC-006**: The consumer's named workaround transform is deleted in one edit, and its removal is
  confirmed in that repository rather than predicted here.
- **SC-007**: An operator-set node label survives a discovery pass, an IP change, an adopt and an
  un-adopt, demonstrated by test rather than by reading the merge.
- **SC-008**: An invalid label leaves the index **unchanged** — measurable as: the document still
  saves afterwards. ⚠ The "today" in the first draft of this criterion was **`cuems-nodeconf`'s**,
  not this library's: there is no label setter here to raise, and the failure mode being prevented —
  a half-applied write whose row then fails every pending save until the daemon restarts — is what
  that repository's own in-place mutation does today. Stated as the attribution it is, so nobody
  measures a before-state this repository never had.
- **SC-009**: A consumer can report a duplicate identity with **no** regular expression over this
  library's prose, and can `except` the condition by name rather than inspecting a general failure.
  Measured as: the consumer's anchored pattern and its empty-string fallback are both removed, and
  its handler names the exception type.
- **SC-010**: **Zero** descriptor fields report a one-value choice set for a type that accepts open
  values. Measured at the branch point: **5**.
- **SC-011**: A hand-maintained configuration document is still human-readable after a UI save —
  measured as: the written document's line count is greater than one and within ±1 line of the
  equivalent hand-indented form, and a save that changes **one** element's text produces a diff of at
  most **3** changed lines against the operator's prior hand edit. The second clause replaces *"a
  diff a reviewer can read"*, which named the right outcome and could not be asserted.
- **SC-012**: **The four library-only** of `cuems-editor`'s seven strict xfails for the five gates
  turn XPASS on this feature's landing alone — the three G3 config-root instances and the G3 cue
  instance. Verified in that repository's checkout, not predicted here.
- **SC-012a**: The remaining **three** are recorded as consumer obligations with an owner and a
  measured status, not as this feature's deliverables: **G1** needs `cuems-editor` to pass the
  tolerance on at its own write site (FR-008), **G2** needs it to remove `project_settings` from its
  refusal set and give it a load step (FR-017), and **G4** needs `cuems-nodeconf` to ship the
  `node_set` handler (FR-047). That repository's tag-readiness record moves from *NOT READY* to ready
  when those three land, which is **after** this feature and outside it. ⚠ The first draft of SC-012
  asserted all seven, which `contracts/sibling-gates.md` had already measured as unreachable from
  this repository — the gate list and the success criterion disagreed.
- **SC-012b**: `consumers_works.md` accounts for **every** obligation on another repository — the
  three above, G3's `cuems-frontend` transform deletion (FR-031), S1's `cuems-editor` regex removal
  (FR-065b), and any further one found while verifying — each with its status measured in that
  checkout. Zero obligations exist only as a prediction in this repository (FR-106a).
- **SC-013**: `cuems-nodeconf`'s `node_set` becomes implementable — its unchecked prerequisite is
  satisfied and the ordering statement *"the library first, then this repository"* is discharged.
- **SC-014**: No sibling repository reports a new failure attributable to this feature without a
  control-arm measurement at the branch point distinguishing it from pre-existing breakage.
- **SC-015**: Every one of the source document's rows — G1–G5, S1–S4, and the settled items — is
  implemented or recorded as declined, which is the condition that permits that document's deletion.
- **SC-016**: `specs/planning/` contains no document whose work is complete, and no document whose
  stop-condition is satisfied, after the polish phase.
- **SC-017**: Every statement of the coordinated tag's work order agrees with every other.
- **SC-017a**: Every cross-repository claim this repository asserts resolves at a **tag**, and zero
  resolve at a sibling's tip. Measurable by inspection of the assertions.
- **SC-017b**: Re-cutting one candidate tag produces a validation result for the **whole** set, so
  the 011 incident — a tag set that did not compose for a day, invisible to every packaging
  relation — is detectable rather than discoverable by accident.
- **SC-017c**: Every candidate-tag value this repository records matches the tag it names, verified
  against the tag. Measured at the branch point: **three of four are wrong.**
- **SC-QUALITY-001**: No new lint or **type** finding is introduced — both gates run, `ruff` through
  `test.py3.11:lint` and `mypy` through the `types:check` script this repository already defines,
  each compared against a **registered branch-point baseline** rather than against zero, because
  neither tool is clean on this tree and mypy had never been run on it at all. The type gate's scope
  is **`src/cuemsutils`**, baseline **80 errors in 26 files**, registered 2026-10-13; `tests/` is
  excluded because `[tool.hatch.envs.types]` installs no test dependencies, so 158 of the 278 errors
  the unscoped script reports are the one module `pytest` being unimportable — an env defect, not a
  finding, and not this feature's to repair. Four of the nine files this feature edits are at **zero**,
  including both that receive new public API, which is where the gate earns its keep — and every new public call carries
  documentation stating its contract — including the one-runtime-writer warning and the projection
  property, each of which exists because a consumer already read a call the other way.
- **SC-QUALITY-003**: The `src/` **type** findings are **below 80**, and every one of the 80 is
  accounted for — fixed, or carried with a stated reason. Measured by diffing the end-state run
  against `snapshots/types-before.txt`.
- **SC-QUALITY-004**: The `src/` **lint** findings are **zero**, or every residual one is carried
  with a stated reason. Branch point: **316**, of which **302 are mechanical** (267 `W293`, 11
  `W291`, 7 `F541`, and 17 `I001` that are mechanical only file by file) and **14 are judgement**.
  `tests/`' 290 are reduced by at least its 209 mechanical findings; its 81 judgement findings are
  examined under FR-111 and FR-112 rather than bulk-fixed.
- **SC-QUALITY-005**: **Zero** unused `# type: ignore` and **zero** stale `noqa` outside the two
  frozen modules — measured as `--warn-unused-ignores` and `--extend-select RUF100` each reporting
  nothing in `src/` but those modules. Every inert directive that carried a reason still carries that
  reason as a plain comment; **zero rationale sentences are lost**, which is the way this task can go
  wrong while every number improves.
- **SC-QUALITY-007**: Both static instruments are version-bounded, and every recorded finding count
  names the tool version it was measured on. Measured at the branch point: mypy is lower-bounded
  only, **ruff is unbounded entirely**, and neither recorded figure could have been reproduced from
  the repository alone.
- **SC-QUALITY-006**: The sweep changed no behaviour, shown rather than asserted: the goldens, the
  wire dicts and `outcomes.json` are byte-identical across it, the suite is green, and
  `git diff -w` over the mechanical commit is **empty**.
- **SC-QUALITY-002**: Every module carrying a public call this feature adds is present in the
  rendered API documentation, asserted by test. Measured at the branch point: **3 of the 4** modules
  this feature documents into are absent from `docs/`.
- **SC-TEST-001**: Every requirement has a test that **fails before** the change and passes after.
  For G5 the failing test is the composition, not the unit.
- **SC-TEST-002**: The suite ends **green**. All five branch-point failures are this feature's to
  dispose of — FR-079 disposes of one and FR-080 of the other four — so zero of them may remain, and
  no new failure may appear. ⚠ The first draft read *"no more failures than the five measured at the
  branch point, each attributed"*, which would have been satisfied by five **new** attributed
  failures and sat badly against the constitution's *"merges MUST be blocked if any relevant test
  suite fails"*. The branch point being red is a fact about the branch point, not a budget.
- **SC-PERF-001**: The document **write** path stays within the budget this feature's baseline
  records for it. Branch-point reference: show-document save **14.297 ms** (worst observed) → budget
  **≤ 16.4 ms** at 115%.
- **SC-PERF-002**: **Descriptor derivation** stays within its recorded budget. Branch-point
  reference: **1.060 ms** for the show schema (worst observed) → budget **≤ 1.22 ms**.
- **SC-PERF-005**: The show-document load's **band** is recorded, the assertion no longer flakes on
  an unchanged tree, no test reports the figure as comfortably passing, and the drift has a named
  follow-up carrying all 16 measurements. Measurable as: the test compares against a band whose
  provenance and sample count are stated, and the follow-up record exists and names an owner.
- **SC-PERF-003**: The suite stays within its recorded per-test budget — **8.93 ms/test** at the
  branch point → **≤ 10.3 ms/test** at 115%. The per-test figure is what binds, never the wall time — a growing corpus reads as a regression otherwise, which this
  repository has recorded twice.
- **SC-PERF-004**: The three configuration load paths and the show load path are measured and
  reported, whether or not they moved.

---

## Assumptions

1. **D1 is taken literally.** The thirteen settled items above are inputs. A task that re-derives
   one of them is doing work this feature has already paid for.
2. **D2's polish-phase deletion is the agreed-wider nine**, not the seven of §9.3's last row —
   decided 2026-10-13 on the ground that the source document and the G5 record each name their own
   deletion condition and this feature satisfies both.
3. **D3's stragglers are S1–S4**, all four in scope, including S2 on cost-of-adjacency grounds and
   S3 with its measured golden-recut cost accepted.
4. **D4 confines the `cuems-nodeconf` surface to the label setter.** Nothing about the atomization
   split, the hardware probe, or the `display.conf` transcription is in scope.
5. **G3 goes to "shape **and** saveable"**, decided 2026-10-13, which reverses the descriptor's
   recorded position that an instance need not be schema-valid. FR-026 requires that reversal to be
   recorded where the old position stands. The saveability is reached by **instance-local seeding
   derived from each field's XSD type**, not by model-layer defaults — clarified 2026-10-13, because
   the model-layer route would have changed the load path's strictness for 64 fields as a side
   effect (FR-026a).
6. **The sweep extends to both gaps found on 2026-10-13** — the sequencing document and the
   `xml-rebuild/` subtree — decided 2026-10-13.
7. **The version stays `0.1.0rc16`** and the deprecated-surface deletions, the version move and the
   five sibling re-bounds are **not** this feature's. They live in their own documents and ship with
   a release this feature does not cut.
8. **No new runtime dependency.** Every item is reachable with the pinned schema library and the
   standard library.
9. **Measurement, not transcription.** Every line number cited in planning or in a sibling's report
   is re-verified before it is relied on; several in the source document were measured against
   earlier commits.
10. **The tag is the gate, not the release.** Closing these five items makes the coordinated
    `xml-refactor-merge-candidate` tag cuttable; it ships nothing on its own.

---

## Out of scope

| Item | Where it lives |
|---|---|
| `hardware_outputs` — the structure pass, the inventory move, `default_mappings.xml`, the stored counts, the zero-caller output-id pair, the sibling namespace typo | `specs/planning/hardware-outputs-capability-layer.md` — deferred, unnumbered, re-owned to `cuems-nodeconf` |
| The deprecated-surface removal — five modules, seven aliases, nine symbol sites, the frozen legacy builder | `specs/planning/deprecated-surface-removal-v0-1-1.md` — gated on a release, not a feature |
| The version move and the five sibling package re-bounds, which are **one atomic step** | `specs/planning/coordinated-release-version-bump.md` |
| The relocation of the timeout-loop class out of the package root | ships with the removal release; landing it here would mean two public paths for one class across a release boundary |
| The Envelope feature | `specs/planning/envelope-feature.md` — an open central decision, not a gap |
| `cuems-nodeconf`'s ten-responsibility split, and everything in **D4** beyond the label setter | `specs/planning/nodeconf-atomization.md` and a future spec |
| Per-type XSD validation | `specs/planning/xsd-type-resolution.md` — the record of a removed mechanism, nothing to carry |
| An engine-side configuration reload; a generalised content-hash helper; one call that ingests-resolves-persists | declined above as SET-7, SET-8, SET-9 |
| The always-empty project-settings dictionary (a separate latent defect, recorded in code) | FR-016 leaves it alone deliberately |

---

## Dependencies

| Depends on | Kind |
|---|---|
| 014 (`xs:boolean`, the media block, configuration ingestion) | **landed** on its branch; this feature's G2 is the read-side mirror of 014's `from_json` |
| 013 (device-class reshape) | **landed**; G5 is a defect in its composition with an earlier version step |
| `cuems-editor` 002 | its seven strict xfails are the acceptance evidence for G1–G4; it is **not** blocked on this feature for its own landing |
| `cuems-nodeconf`'s `node_set` | **blocked on G4**, by its own stated ordering |
| `cuems-frontend` 001 | **landed**; its UR-1 is G3's statement of requirement and its workaround is G3's completion marker |
| The coordinated `xml-refactor-merge-candidate` tag | **blocked by all five gates.** This feature is what makes it cuttable; the capability layer is outside it and may ride a later one |

---

## Questions taken in the clarification pass

**All five are settled** — the answers are recorded in *Clarifications* above and applied to the
requirements. The two below keep their own subsections because the *reasoning* outlives the answer,
and because one of them records a measurement this pass had to correct.

### Q1 — the show-document load, marginally over its budget at the branch point

The show-document load measures **16.781–17.882 ms** on a quiet box against the **16.5 ms** budget
013 re-baselined, by the budget's own method — **exceeded by 1.7–8.4%**, with the best observation
only 0.28 ms over the line.

⚠ **Corrected during this clarification pass.** The specify pass recorded 32.8–33.5 ms and called it
*"consistent across three isolated runs, so not scheduler noise"*. Those three runs were taken
immediately after a full-suite run, under a sustained load average of 2.26 — three readings under one
contention, not three isolations. Re-measured on a quiet box through the identical invocation, the
same test reads 17.1–17.3 ms. The budget is exceeded **marginally**, not doubled. The lesson is the
one this repository already records: ±4–8% is this instrument's resolution, and a tight budget on a
non-idle box measures the afternoon.

The remaining question is the disposition, which is now a small decision rather than a scope risk.

**Settled 2026-10-13**: recorded as exceeded-or-marginal, the budget not raised, the drift carried
as a follow-up with an owner — FR-079 through FR-079c.

**Confirmed the same day by the toolchain migration**, which was the strongest available test of the
decision: the interpreter moved from CPython 3.11.2 to 3.11.9 — across two different 3.11.9 builds —
and the overrun **persisted**. Had it been an artefact of the old interpreter it would have vanished.

**Refined once more by sampling properly.** Sixteen samples across three windows give a band of
**16.465–17.750 ms** (median 16.864) against the 16.5 ms budget: **14 of 16 exceed it, 2 do not**.
So the honest verdict is not "exceeded by ~4%" but **straddled at its floor**, which makes the
assertion flaky rather than failing — and that has its own precedent and remedy in this repository
(012's R14), now adopted as FR-079a. The drift against 013's 14.07–14.96 ms is **+13% to +19%**.

### Q2 — frozen landed specs versus live cross-repository assertions

**Settled 2026-10-13** — FR-080 through FR-080f. Split by assertion class, and resolve the surviving
assertions at each sibling's coordinated tag rather than at its tip, since the tag is the only stable
reference in a seven-repository set. Recorded here because the reasoning outlives the four tests: the
collision recurred because a *dated measurement* and a *live instruction* were being enforced by one
mechanism, and because that mechanism pointed at a moving branch.
