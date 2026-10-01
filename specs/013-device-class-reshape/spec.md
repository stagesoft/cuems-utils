<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Feature Specification: Device-class reshape

**Feature Branch**: `013-device-class-reshape`
**Created**: 2026-10-01
**Status**: Draft
**Input**: User description: "Start the specification for 013-device-class-reshape (F6) in cuems-utils", against
`specs/planning/etc-cuems-first-install-execution.md` → "Feature 013",
`specs/planning/etc-cuems-first-install.md` §8.4, `specs/agreements/schema-evolution-convention.md`,
`specs/012-uuid4-convergence/` and `specs/planning/refactor-sequencing-2026-10-01.md`.
The full prompt is vendored at `specs/planning/013-specify-prompt.md`.

**Branch point**: `8b341a0` on `feat/xml-refactor` — the documentation commit immediately after
`fee13e8` (where feature 012 merged, 2026-10-01). `fee13e8` is the commit the baseline below was
stated against; the one commit between them touches only `specs/planning/`.

**Suite baseline, re-measured on this branch 2026-10-01 rather than inherited**:
**3247 passed, 115 skipped, 2 xfailed in 53.25 s = 16.40 ms/test**
(`PYENV_VERSION=3.11.9 uvx hatch run test.py3.11:run -- -q`). Identical to the figure the brief
states, which is why it is recorded as confirmed rather than as a new measurement.

---

## Why this feature exists

Adding a fourth hardware class to CUEMS today is not a data change. It is a code change in four
schemas, two `ConfigManager` constants and four repositories — and every one of those sites is a
place the classes can fall out of step. §8.4 priced it at roughly twenty sites. Re-measured on this
branch, site by site:

| Axis | Site | What one new class costs today |
|---|---|---|
| **A — node mappings** | `project_mappings.xsd` `NodeMappingType` | `default_X_input`/`default_X_output` at the document root **and** an `<X>` element in `NodeMappingType` |
| | `src/cuemsutils/config/mappings.py:116-137` | a `DECLARED_DEFAULTS` entry on `NodeMappingType`, and a `DeviceType`/`VideoDeviceType` choice |
| | `src/cuemsutils/config/mappings.py:179-192` | two `DECLARED_DEFAULTS` entries on `CuemsProjectMappingsType` |
| | `src/cuemsutils/xml/validators.py:790-796` | the T2 rule `one_custom_template_per_node` is bound to the literal pair `("NodeMappingType", "video")` |
| **B — the library's enumeration** | `tools/ConfigManager.py:69` | `_DEVICE_SECTIONS = ('audio', 'video', 'dmx')`, consumed at `:386` and `:659` |
| | `tools/ConfigManager.py:159` and `:283` | the six-key `node_hw_outputs` literal, written out twice, becomes eight |
| **C — node settings** | `settings.xsd:79-82` | a player section element (`videoplayer`/`audioplayer`/`dmxplayer`) plus a `PlayerType` extension (`:93`, `:105`, `:122`) |
| **D — the show script** | `script.xsd:104-106`, `:148-153` | `XCueType` + `XCueOutputsType` + a member in the `CueList` choice + a member in the `OutputsType` choice |
| | `hardware_outputs.xsd:13-14` | `X_outputs` (the `default_X_output` half went with feature 011's F4) |
| **E — consumers** | `../cuems-frontend` | the cue-type unions and the structurally-typed mappings interface — see M1 and M3 |
| | `../cuems-engine/src/cuemsengine/NodeEngine.py` | three fixed-key reads of `node_hw_outputs` — see M2 |
| | `../cuems-editor/src/cuemseditor/CuemsWsServer.py:439` | the three sections named in a merge comment, over a dict passed verbatim to the UI — see M5 |

The mechanism that collapses axis A is **XSD 1.1 conditional type assignment**: a device becomes
`<device class="…">` and an `xs:alternative` selects a type per class, so a class needing no special
fields costs *nothing* and one that does costs a single line.

**What this feature is**: the migration. Not the mechanism — see the next section.

---

## What is already settled, and is not re-opened here

**The mechanism is proven under the pinned dependency.** Measured 2026-09-23 under
`xmlschema==3.4.3` (pinned; XSD 1.1 is already required by `script.xsd`'s `xs:assert`): a document
carrying `<device class="lighting">` validates with **no schema change**, while `<canvas_region>`
on a non-video device is still rejected. Feasibility is not a research question for this feature,
and the plan must not spend a task re-establishing it. What is open is which documents move, how
the ones already on disk get there, and what the consumers are told.

**This is a rule-4 migration carried without a version step** — settled by the clarification
session below, and recorded here because it **departs from the brief**, from `CLAUDE.md`'s line on
feature 013, and from the prompt that opened this feature, all three of which state the Kind as
*"a rule-4 file-format migration — version step **and** conversion"*. The decision is not to skip
rule 4. It is to discharge rule 4 the way **feature 007** discharged it, which
`specs/agreements/schema-evolution-convention.md` already records as a worked precedent:

> *"A version marker that lets a reader tell old from new — **the element's own presence**. A
> document with `<node_type>` is unambiguously pre-migration; one with `<node_role>` is
> post-migration. No separate version field was needed because the two names cannot coexist under
> `xs:sequence` validation."*

`<audio>` and `<device class="audio">` cannot coexist either, so the shapes are mutually exclusive
and self-identifying. The reason for preferring it here is that the whole ecosystem lands together
behind the coordinated `xml-refactor-merge-candidate` tag (D27): there is no mixed-version window
**between components**, so a per-document version negotiation buys nothing between them.

**What it does not buy is a mixed-version window between the software and the documents, and that
window is real.** Three consequences follow, and each is a requirement below rather than a caveat:

- **Old-shape documents do not load by themselves.** With no version step there is no registry key,
  so nothing converts on read, and the strict load path feature 008 built rejects an old-shape
  document as a plain validation failure. The migration must therefore be **a documented tool that
  runs once** — rule 4's other branch, and 007's actual mechanism — not a conversion on read.
- **The error an un-migrated document produces names the wrong thing.** `xs:sequence` reports the
  first child it did not expect, which is the exact failure mode `specs/agreements/schema-evolution-convention.md`
  vendors two broken settings files as evidence of (X13). A document missed by the tool must be
  diagnosed by this feature, not by an operator working backwards from a complaint about an element
  that is present and correct.
- **A new-shape document is indistinguishable by marker from an old one.** `mapper.build_document`
  (`xml/mapper.py:1083`) stamps every written document with `CURRENT_VERSION[schema_name]`, so with
  no bump the two shapes carry the same number. An older `cuems-utils` therefore gets a raw schema
  error instead of `DocumentTooNewError`. D27 covers the shipped set; it does not cover a node left
  un-upgraded, a rollback, or a restored backup.

Two further consequences, both simplifications:

- **`DELIBERATE_IDENTITY_STEPS` is untouched.** It keeps exactly feature 012's three entries. The
  prompt's instruction — *"013's steps must not go in it"* — is satisfied because 013 has no steps,
  which is a different route to the same place and is recorded as such.
- **`CURRENT_VERSION` is untouched**, so `test_each_schema_is_at_its_pinned_version` and
  `test_every_schema_past_version_1_has_a_conversion_for_every_step` both pass unchanged.

---

## Clarifications

### Session 2026-10-01

- Q: §8.4's cost table spans four document axes, but the brief's Scope line names only two
  (`project_mappings`' device declarations and `ConfigManager`'s derivation). Which axes does 013
  collapse — A+B, A+B+C, A+B+D, or all four? → A: **All four.** This is the only answer under which
  the feature's headline — *"a new hardware class costs data, not schema"* — is literally true, and
  it is the answer under which `cuems-frontend`'s flow 05 is genuinely blocked on this feature, as
  `specs/planning/refactor-sequencing-2026-10-01.md` §4c assumes. Under A+B the frontend's 013 site
  would have been `projects.service.ts` alone (M3) and that deferral would have rested on a weaker
  basis than the sequencing document states.
- Q: Does each axis take a `doc_version` step with a registered conversion, per the Kind the brief
  states? → A: **No version bump on any schema.** Every change lands together ecosystem-wise behind
  the coordinated `xml-refactor-merge-candidate` tag, so a per-document version negotiation buys
  nothing between components. Rule 4 is discharged by feature 007's route instead — mutually
  exclusive element shapes as the marker, plus a documented tool that runs once. See the section
  above for the three consequences this carries and the requirements that answer them.

---

## Scope — all four axes

| Axis | What collapses | Schemas and code |
|---|---|---|
| **A** | node mappings | `project_mappings.xsd`'s `NodeMappingType` sections and root `default_X_*` pairs; `config/mappings.py`; the T2 rule's binding |
| **B** | the library's enumeration | `ConfigManager.py:69`'s `_DEVICE_SECTIONS`; the six-key `node_hw_outputs` literal at `:159` and `:283` |
| **C** | node settings | `settings.xsd`'s `videoplayer`/`audioplayer`/`dmxplayer` sections and their `PlayerType` extensions |
| **D** | the show script | `script.xsd`'s `CueList` choice (`:104-106`) and `OutputsType` choice (`:148-153`); `hardware_outputs.xsd`'s two flat lists |

**Not in scope on any axis**: a `doc_version` step, a registry `Conversion`, or any edit to
`CURRENT_VERSION` or `DELIBERATE_IDENTITY_STEPS`. See above.

**The one piece of knowingly duplicated work**: axis D reshapes `hardware_outputs.xsd`'s two lists,
and feature 014 replaces that schema's structure outright — on a schema with **no instance anywhere
in the ecosystem** (M9). It is in scope because the axis is, and it is the first thing to cut if the
plan needs to cut something.

---

## Measured corrections and additions to the brief

Each of these was measured on this branch on 2026-10-01. They are recorded here, not silently
applied, because several of them contradict a document that is still load-bearing elsewhere.

- **M1 — the frontend's cue-type union count is not four at one location.** The brief says *"four
  cue-type unions, at `sequence.component.ts:294-304`"*. Measured in
  `../cuems-frontend/src/app/components/projects/project-edit/sequence/sequence.component.ts`:
  the literal type union `'action' | 'audio' | 'video' | 'dmx' | 'fade'` appears **three** times
  (`:28`, `:292`, `:643`), the if/else-if discriminator chain is at `:294-304`, and a fourth form
  — a key-membership disjunction `key === 'AudioCue' || … || key === 'FadeCue'` — is at `:1140`.
  So five sites in that file, of four distinct shapes. And the brief names one file where there are
  **two**: `project-show/sequence/sequence.component.ts:141-145` carries a second discriminator
  chain of its own. The brief's count is not wrong about the cost; it is wrong about where to look.
- **M2 — `node_hw_outputs` has exactly three live consumer reads, and one of them breaks on a
  derived dict.** All three are in `../cuems-engine/src/cuemsengine/NodeEngine.py`: `:456`
  (`.get("audio_outputs")`), `:457` (subscript, guarded by `:456`) and **`:566`
  (`self.cm.node_hw_outputs["video_outputs"]`, a bare subscript with no guard)**. Today that cannot
  raise, because `ConfigManager` pre-seeds all six keys as empty lists at `:159` and `:283`. A dict
  derived from the document would omit `video_outputs` on a node with no video section, and `:566`
  would raise `KeyError` — on the engine's video-player startup path. This is the single most
  consequential consumer fact in the feature.
- **M3 — 013 reaches `cuems-frontend` on axis A regardless of axis D.**
  `../cuems-frontend/src/app/services/projects/projects.service.ts:34-60` types the *whole*
  `project_mappings` document structurally, including `nodes[].node.audio` / `.video` / `.dmx` and
  all six `default_X_input`/`_output` keys. A `<device class="…">` reshape changes that interface
  literally. So the frontend has a 013 obligation under every candidate scope, and the contract
  this feature hands it must name `projects.service.ts` whether or not it names
  `sequence.component.ts`.
- **M4 — the T2 rule is bound to a field *name*, which the reshape removes.**
  `xml/validators.py:790-796` registers `one_custom_template_per_node` against the literal pair
  `("NodeMappingType", "video")`. Once `video` is a `@class` value rather than an element name,
  that binding names nothing. Feature 008 established this as `project_mappings`' only registered
  T2 rule and as `repairable=False`; losing it silently would turn a `ValidationError` back into
  an unvalidated document. The live call site, `validate_custom_templates`
  (`xml/validators.py:95-113`), walks the `video` section by name too.
- **M5 — `cuems-editor` is a 013 site, and not at any of its fourteen known call sites.**
  `../cuems-editor/src/cuemseditor/CuemsWsServer.py:439` carries the comment *"Keep outputs (audio,
  video, dmx) from existing node"* inside `merge_node_data`, over a `mappings_dict` that
  `CuemsWsServer.py:71-72` documents as *"passed verbatim to the frontend as the initial
  mappings"*. None of this is among the fourteen deprecated-surface call sites the sequencing
  document scopes flow 02 to. It is the condition §5 of that document flagged — *"if 014 turns out
  to reach `CuemsDBProject.py`"* — arriving one feature early and on 013 instead of 014. It does
  **not** invalidate the editor-first recommendation: the merge is a pass-through, orthogonal to
  the `CuemsParser`/`XmlReaderWriter` move, and it changes when 013 lands rather than when flow 02
  does.
- **M6 — what the version steps *would* have been, recorded because the feature declines them.**
  `xml/versioning.py:CURRENT_VERSION` reads `script` 2, `settings` 3, `network_map` 2,
  `project_mappings` 2, `project_settings` 1, `hardware_outputs` 2. Had this feature taken steps
  they would have been `project_mappings` 2→3, `settings` 3→4, `script` 2→3 and
  `hardware_outputs` 2→3. It takes none (FR-020); the numbers are kept so a later feature that
  needs them does not re-derive them, and so the declined option is legible.
- **M7 — two line references in the brief are one off.** `_DEVICE_SECTIONS` is at
  `ConfigManager.py:69` and consumed at `:386` and `:659` — all three exact. The `node_hw_outputs`
  literal is at `:159` and `:283`, not `:160` and `:283`.
- **M8 — axis C's player sections are read by name outside this repository.**
  `../cuems-engine` reads `self.cm.node_conf["videoplayer"]` and `videoplayer/osc_port`;
  `../cuems-common/usr/lib/cuems/bin/cuems-extract-video-latency` reads
  `videoplayer/output_latency_ms`. Axis C is therefore not a local reshape, which is part of why
  the brief's Scope line omits it.
- **M9 — `hardware_outputs` has no instance anywhere in the ecosystem** and no registry binding
  (§3.4 of the audit, re-confirmed). Its two flat `xs:string` lists are the cheapest axis to
  reshape and the one with the least to gain, because feature 014 rewrites that schema's structure
  entirely.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A new hardware class is added by writing a document (Priority: P1)

An integrator bringing a new class of hardware into a CUEMS installation — lighting, say, or a
timecode interface — describes it in the node's mappings document as `<device class="lighting">`
with its port groups, and the library accepts, decodes and reports it. No schema is edited, no
constant is extended, and nothing in the library has to be told that "lighting" exists.

**Why this priority**: it is the feature. Every other story exists to make this one safe to ship.
It is also the one story that is independently valuable even if nothing on disk ever converts: a
greenfield node authored in the new shape works on day one.

**Independent Test**: author a mappings document containing an `audio` device, a `video` device
carrying a `canvas_region`, and a `lighting` device the library has never heard of. Confirm it
validates, that the decoded object reports three device classes with `lighting` among them, that
the hardware-output accessor answers per class, and that a `canvas_region` on the `lighting` device
is **rejected** — the class-conditional typing must still discriminate.

**Acceptance Scenarios**:

1. **Given** a mappings document whose node carries `<device class="lighting">` with one output
   group, **When** it is read, **Then** it validates and the decoded node reports a `lighting`
   device, without any schema, constant or model class naming that class.
2. **Given** that same document, **When** the hardware-output inventory is read, **Then** it
   carries a `lighting` entry derived from the document, alongside the `audio` and `video` ones.
3. **Given** a document placing a `canvas_region` on a device whose class is not `video`,
   **When** it is read, **Then** it is rejected — the conditional typing discriminates by class,
   and the special fields of a special class do not leak to every class.
4. **Given** a document whose node carries no device of a given class at all, **When** a consumer
   reads that class's hardware outputs by name, **Then** it receives an empty answer rather than
   an error (M2: `NodeEngine.py:566` subscripts without guarding, and must keep working).
5. **Given** a document carrying two devices of the same class, **When** it is read, **Then** the
   outcome is stated and tested rather than incidental — see FR-013.
6. **Given** a document carrying a device whose class is misspelled, **When** it is read, **Then**
   the misspelling surfaces as a reported unknown class rather than as a silently-created fourth
   class with no ports (FR-014).

---

### User Story 2 — Every document already on disk is migrated, once, by a tool (Priority: P2)

An operator upgrading a CUEMS installation runs one documented tool that rewrites every old-shape
document it can find — the node's configuration and every project in the library — into the new
shape, backing each one up first. A document the tool misses does not load afterwards, and when it
does not, it says so by naming the old shape and the tool, not by complaining about an element that
is present and correct.

**Why this priority**: with no version marker there is no conversion on read, so this tool *is* the
migration. Everything on disk depends on it, and the document that the tool misses is the one that
turns up at a venue. It is also the half of rule 4 the schema-evolution convention makes
non-negotiable: *"'We will just update the files on the nodes' is not a conversion path. Nobody
knows where all the files are."*

**Independent Test**: build a fixture installation — the three configuration documents plus a
project library whose mappings and scripts are all in the old shape — run the tool, and verify that
every document validates in the new shape, that each decodes to an object equal field for field to
its hand-authored new-shape equivalent, that every rewritten file has a backup, that a second run
changes no bytes, and that a deliberately skipped document produces a diagnosis naming the old
shape and the tool rather than a bare schema error.

**Acceptance Scenarios**:

1. **Given** an installation whose documents are all in the old shape, **When** the tool runs,
   **Then** every one of them is rewritten in the new shape and validates.
2. **Given** an old-shape document and its hand-authored new-shape equivalent, **When** both are
   decoded, **Then** the two objects are equal field for field. The migration is a reshape, and a
   reshape that changed a value would be a different feature.
3. **Given** the tool, **When** it rewrites a document, **Then** it backs that document up first
   and treats a backup failure as fatal for that document only — the obligation feature 008
   attached to *persisting* an upgrade, discharged the same way.
4. **Given** a completed migration, **When** the tool runs a second time, **Then** it reports
   nothing to do and no file's bytes change.
5. **Given** a document the tool did not reach, **When** the library reads it, **Then** the
   rejection names the document, the old shape it is in, and the tool that migrates it — not the
   first unexpected child `xs:sequence` happened to report. This is the X13 failure mode, and this
   requirement is what keeps this feature from repeating it.
6. **Given** a document the tool rewrote, **When** its version marker is read, **Then** it is
   unchanged — this feature bumps nothing, and a reader distinguishes the shapes by their elements.
7. **Given** scripts in a project library, **When** the tool looks for them, **Then** it finds them
   by **root element, not filename** — `script_file_name` is an editor-internal dict key, in no
   document this library reads. Feature 012 measured this; repeating the assumption would repeat
   the defect.
8. **Given** a node that is not upgraded in the same pass, or a backup restored after the
   migration, **When** an older `cuems-utils` reads a new-shape document, **Then** the migration
   guide has already said what happens: a raw schema error, not `DocumentTooNewError`, because the
   marker did not move. The guide states the point after which rollback stops being available.

---

### User Story 3 — The library stops enumerating the classes it supports (Priority: P3)

A maintainer reading `ConfigManager` finds no list of device classes. The classes a node has are
the classes its document declares; the hardware-output inventory is keyed by what was found; and
the T2 rule that constrains video outputs is bound to the class, not to an element name that no
longer exists.

**Why this priority**: it is the code half of the cost collapse, and it is what makes US1's
promise true for the *library* rather than only for the *schema*. Shipping US1's schema with
`_DEVICE_SECTIONS` still declared would mean a new class validates and is then invisible.

**Independent Test**: construct a mappings object carrying a class the library has never seen,
read every public accessor that reports devices or hardware outputs, and confirm each answers for
that class; then grep the library for a hardcoded device-class list and confirm there is none left
to find — asserted by a test, not by inspection.

**Acceptance Scenarios**:

1. **Given** a node mapping carrying an unfamiliar class, **When** the hardware-output inventory is
   built, **Then** it carries that class's entries, derived from the document.
2. **Given** the library's source, **When** it is searched for a declared tuple, list or set of
   device-class names, **Then** none exists — and a contract test asserts that, so the constant
   cannot quietly return.
3. **Given** a mappings document with two custom video templates, **When** it is read, **Then** it
   is still rejected with the T2 rule's own wording — the rule survives the reshape rather than
   being silently unbound (M4).
4. **Given** a video device in the new shape, **When** its `canvas_region` is validated for
   containment, **Then** the same check runs as before, reached through the class rather than
   through the element name.
5. **Given** the two places `node_hw_outputs` is initialised as a six-key literal
   (`ConfigManager.py:159`, `:283`), **When** the reshape lands, **Then** there is one definition,
   not two — the duplication is part of the cost this feature exists to remove.

---

### User Story 4 — Every consumer is told what changed, in writing, before it breaks (Priority: P4)

A maintainer of `cuems-engine`, `cuems-editor` or `cuems-frontend` reads the migration guide and
finds their own repository, their own files, their own line numbers, and what the new shape is.
Nobody infers the contract from a schema diff.

**Why this priority**: three of the five sites this feature changes are outside this repository,
one of them raises rather than degrading (M2), and `cuems-frontend`'s migration is *waiting on this
feature by decision*. A guide that arrives after the port is a guide that arrives too late.

**Independent Test**: the guide is checked against this specification — every consumer site named
in M1–M5 appears with its measured path and line, with the before shape, the after shape, and
whether the old form keeps resolving or raises; and every version and line number it states is
verified against the actual sibling tree rather than asserted.

**Acceptance Scenarios**:

1. **Given** the migration guide, **When** a `cuems-engine` maintainer reads it, **Then** it names
   `NodeEngine.py:456`, `:457` and `:566`, says that `:566` is an unguarded subscript, and states
   whether the three legacy keys keep resolving.
2. **Given** the migration guide, **When** a `cuems-frontend` maintainer reads it, **Then** it
   names `projects.service.ts:34-60`'s structural mappings interface **and** every cue-type site in
   both `sequence.component.ts` files (M1), each with its new shape — so flow 05's US8/T032
   characterization tests are written once against a known target rather than twice.
3. **Given** the migration guide, **When** a `cuems-editor` maintainer reads it, **Then** it names
   `CuemsWsServer.py:439`'s merge and the verbatim pass-through at `:71-72`, and says this site is
   **not** among flow 02's fourteen deprecated-surface call sites.
4. **Given** the migration guide, **When** any consumer maintainer reads it, **Then** each named
   site is classified as *raises*, *keeps resolving and becomes wrong*, or *keeps resolving
   correctly* — the three fault classes feature 010's census established, because they need
   different responses.
5. **Given** the guide's rollback section, **When** an operator reads it, **Then** it states
   whether a converted document can be read by the previous `cuems-utils`, and if it cannot, the
   point after which rollback stops being available — the shape of feature 012's §9b, answered for
   this change.

---

### User Story 5 — The schema pins and the overlap ratchet move with the schemas (Priority: P5)

A reviewer looking at this feature's commits sees each schema edit arrive together with its
recorded hash and, where a type name newly appears in more than one schema, its allowlist entry.
Nothing is left for a follow-up commit.

**Why this priority**: it is cheap, it is mechanical, and both guards exist because the project has
already been bitten. `KNOWN_DIVERGENT_DECLARATIONS` reached empty as feature 012's completion
marker; a feature that re-populated it would undo that in passing.

**Independent Test**: run `tests/contract/test_schema_scope.py` and
`tests/contract/test_schema_name_overlap.py` at every commit of the feature branch and confirm both
pass at each one — not only at the tip.

**Acceptance Scenarios**:

1. **Given** a commit that edits a schema, **When** the suite runs at that commit, **Then**
   `CURRENT_SCHEMA_HASHES` matches — the hash moved in the same commit as the schema.
2. **Given** a type name this feature declares in more than one schema, **When** the overlap test
   runs, **Then** the name is recorded in `KNOWN_IDENTICAL_DUPLICATES` with the schemas it appears
   in, and the drift test passes.
3. **Given** the end of the feature, **When** `KNOWN_DIVERGENT_DECLARATIONS` is inspected, **Then**
   it is still empty.
4. **Given** the whole feature branch, **When** `tests/packaging/test_no_version_bump.py` runs,
   **Then** it passes — `0.1.0rc16` is unchanged.

---

### Edge Cases

- **A class the library has never heard of, carrying fields only a known class may have.** The
  `canvas_region`-on-a-non-video rejection is the proven half of the mechanism; it must stay proven
  after the reshape, because an open class vocabulary without conditional discrimination would make
  every special field legal everywhere.
- **A misspelled class.** `<device class="vidoe">` is, to an open vocabulary, a new class with no
  special fields — structurally valid and silently useless. The failure surfaces far from its cause
  (an output that resolves to nothing), which is the same trap feature 012 recorded for stale
  compound identities.
- **Two devices of the same class on one node.** Today `NodeMappingType` declares each section
  `maxOccurs="1"`, so the question cannot arise. A repeated `<device>` element makes it arise by
  construction.
- **A node with no device of a class a consumer reads by name.** Measured: `NodeEngine.py:566`
  subscripts `node_hw_outputs["video_outputs"]` unguarded, and only survives today because the key
  is pre-seeded. A derived dict is a `KeyError` on the engine's startup path (M2).
- **An old-shape document inside a project the editor merges into a UI payload.** The editor's
  merge preserves the device sections by name and passes the dict verbatim to the frontend (M5), so
  a half-converted library would produce a UI payload with two shapes in it.
- **The T2 rule bound to a vanished element name** (M4). An unbound rule does not fail; it stops
  running. The observable symptom is a document with two custom templates that now loads.
- **A tool that reads and writes back, run against a half-migrated library.** The editor's
  `repair_durations.py` is a measured instance, and feature 008 established that a saved repaired
  document is a plain overwrite. With no conversion on read, such a tool now *fails* on an
  un-migrated document rather than silently upgrading it — which is the safer direction, and is
  stated here so it is a property rather than a surprise.
- **`hardware_outputs` has no instance anywhere** (M9), so an axis-D reshape of it has no
  conversion to prove on real data, and feature 014 rewrites it regardless.
- **The upgrade is one-way and the marker does not say so.** A migrated document carries the same
  `doc_version` as before (FR-020), so an older `cuems-utils` reading it gets a raw schema error,
  not `DocumentTooNewError`. For `project_mappings` and `script` this reaches every project in the
  library, not one file. D27 means no *shipped* component is older; a node left un-upgraded, a
  rollback or a restored backup is not covered by D27.

---

## Requirements *(mandatory)*

### Axis A and B — node mappings and the library's enumeration

#### The class-carrying device element

- **FR-001**: A node's devices MUST be expressed as a repeated element carrying its class as an
  attribute, replacing the one-element-per-class declarations in `NodeMappingType`.
- **FR-002**: The class vocabulary MUST be open — a class the schema does not name MUST validate
  and decode. This is the feature's whole claim; a closed enumeration would move the cost from four
  schemas to one and call it collapsed.
- **FR-003**: A class with special fields MUST keep them, selected by conditional type assignment
  on the class attribute, and those fields MUST remain invalid on every other class. The
  `canvas_region`-on-video case is the worked example and the proven one.
- **FR-004**: Adding a class that needs no special fields MUST require **no** change to any schema,
  model class, constant or test — demonstrated by a test that introduces one.
- **FR-005**: Adding a class that needs special fields MUST cost exactly one conditional-type
  declaration plus the type it names, in one schema.
- **FR-006**: The document-root `default_X_input`/`default_X_output` pairs MUST be reshaped so that
  a new class adds no root element. *(This is the half of axis A that is not inside
  `NodeMappingType`, and the half `cuems-frontend` types explicitly — M3.)*
- **FR-007**: Every reshaped element MUST obey the schema-evolution convention's rule 3 where it
  introduces a type, and rule 4 where it changes one in use — discharged by FR-020–FR-029 via
  feature 007's route rather than feature 008's.

#### Derivation in the library

- **FR-010**: The library MUST NOT declare a list of device classes anywhere. `_DEVICE_SECTIONS`
  (`ConfigManager.py:69`) is deleted, not extended.
- **FR-011**: The hardware-output inventory MUST be keyed per class, derived from the document, with
  one definition rather than the two literals at `ConfigManager.py:159` and `:283`.
- **FR-012**: Reading a class's hardware outputs by name for a class the document does not carry
  MUST yield an empty answer, not raise. *(M2: `NodeEngine.py:566` is an unguarded subscript, and
  this requirement is what keeps it working.)*
- **FR-013**: Two devices of the same class on one node MUST have a stated, tested outcome —
  rejected, or merged by a stated rule. Today's `maxOccurs="1"` makes it impossible; the reshape
  makes it expressible, so leaving it unstated would be a new ambiguity introduced by this feature.
- **FR-014**: A class the library does not recognise MUST be reportable — a consumer, or an
  operator-facing check, MUST be able to learn that a document declares a class nothing handles.
  An open vocabulary without this makes a typo indistinguishable from an integration.
- **FR-015**: The T2 rule `one_custom_template_per_node` MUST survive the reshape, bound to the
  class rather than to the element name `video`, and MUST keep its exact wording and its
  `repairable=False` classification. Its live call site `validate_custom_templates` MUST reach the
  video devices through the class too. *(M4.)*
- **FR-016**: `check_canvas_region_containment` MUST keep running on every video output's
  `canvas_region`, reached through the class.

#### The migration, carried without a version step

- **FR-020**: No schema's `doc_version` MUST change. `xml/versioning.py`'s `CURRENT_VERSION`,
  the conversion registry and `tests/contract/test_version_marker.py`'s
  `DELIBERATE_IDENTITY_STEPS` MUST all be left exactly as feature 012 left them.
- **FR-021**: The old and new shapes MUST be mutually exclusive, so that a reader can tell them
  apart from the document's own elements with no marker — feature 007's mechanism, and the property
  that makes FR-020 safe. A schema that accepted both shapes would remove the discrimination this
  requirement depends on and would keep the per-class declarations this feature exists to delete.
- **FR-022**: A documented tool MUST migrate every old-shape document in one run — the node's
  configuration documents and every project in the library, across all four axes.
- **FR-023**: That tool MUST find project scripts by **root element, not filename**.
  `script_file_name` is an editor-internal dict key and appears in no document this library reads;
  feature 012 measured this and the same trap applies here.
- **FR-024**: The migration MUST be a pure reshape: every old-shape document MUST produce an object
  equal, field for field, to the hand-authored new-shape equivalent. If any information is genuinely
  not representable in the new shape, it MUST be named in the tool's report and justified in the
  migration guide, never dropped silently.
- **FR-025**: The tool MUST back each document up before rewriting it and MUST treat a backup
  failure as fatal **for that document only** — the behaviour feature 008 established for
  `cuems-convert-documents`, applied here.
- **FR-026**: Re-running the tool on a migrated installation MUST change no file's bytes.
- **FR-027**: Reading an un-migrated document MUST produce a rejection that names the document, the
  old shape, and the tool that migrates it. A bare `xs:sequence` "unexpected child" message is the
  X13 failure mode this project has already vendored evidence of, and it is not acceptable as this
  feature's diagnosis.
- **FR-028**: The migration guide MUST state that the version marker does **not** move, that an
  older `cuems-utils` therefore gets a raw schema error rather than `DocumentTooNewError` on a
  new-shape document, and the point after which rollback stops being available. This is the cost
  FR-020 buys its simplicity with, and it is stated rather than discovered.
- **FR-029**: Whether the tool is a new entry point or an extension of an existing one MUST be
  decided in planning and recorded. `cuems-convert-documents` is version-driven and has no step to
  drive it here, so reusing it means giving it a second, shape-driven mode — a design choice with a
  cost, not a free reuse.

#### Consumer contract

- **FR-030**: The migration guide MUST name every measured consumer site — M1's five sites in two
  frontend files, M2's three engine sites, M3's frontend mappings interface, M5's editor merge —
  with its path, its line at a named commit, its before shape and its after shape.
- **FR-031**: Each named site MUST be classified as *raises*, *keeps resolving and becomes wrong*,
  or *keeps resolving correctly*, following feature 010's census classification.
- **FR-032**: The guide MUST give `cuems-frontend` the cue-type contract in full — both
  `sequence.component.ts` files (M1), all five sites in `project-edit` and the discriminator chain
  in `project-show` — with the new shape for each, so flow 05 writes its US8/T032 characterization
  tests **once**, against a known target. This is the obligation the brief states as *"state the
  contract 013 hands it; do not leave the frontend to infer it"*, and the clarification session's
  all-four answer is what makes `sequence.component.ts` genuinely 013's site.
- **FR-033**: The guide MUST state that `cuems-editor`'s `CuemsWsServer.py:439` site is **not**
  among flow 02's fourteen deprecated-surface call sites, so the editor's in-flight migration is
  not re-scoped by discovery.
- **FR-034**: No library version bump. `0.1.0rc16` stays pinned by
  `tests/packaging/test_no_version_bump.py`.

### Axis C — node settings

- **FR-040**: `settings.xsd`'s per-class player sections MUST be reshaped so that a new class adds
  no element to `NodeConfType` and no `PlayerType` extension.
- **FR-041**: `settings` MUST NOT take a version step (FR-020). Old-shape settings documents are
  migrated by FR-022's tool and diagnosed by FR-027 like every other axis.
- **FR-042**: The named external reads MUST be addressed explicitly: `cuems-engine`'s
  `node_conf["videoplayer"]` and `videoplayer/osc_port`, and `cuems-common`'s
  `cuems-extract-video-latency` reading `videoplayer/output_latency_ms` (M8). Each MUST be
  classified per FR-031 and named in the guide.
- **FR-043**: Feature 011's generated `settings.xml` MUST still be generated, validated and
  installed by the package build, and the seed-value rules in `xml/seed_values.py` MUST still find
  every field they name. A reshape that broke the build that produces the documents it applies to
  is feature 012's M-f lesson repeated.

### Axis D — the show script and hardware outputs

- **FR-050**: `script.xsd`'s per-class cue and cue-output types MUST be reshaped so that a new class
  adds no member to the `CueList` choice (`:104-106`) and none to `OutputsType` (`:148-153`).
- **FR-051**: `script` MUST NOT take a version step (FR-020). The migration MUST preserve every
  cue's decoded identity, type and output bindings exactly, and this is the axis where that is
  hardest to be sure of: a show script is the artefact a venue cannot re-author on the day.
- **FR-052**: Cue equality, hashing and the wire projection MUST be unchanged in observable
  behaviour. `Cue.__hash__` is restated rather than inherited in this codebase, and an unhashable
  cue is a `TypeError` in the engine.
- **FR-053**: `hardware_outputs.xsd`'s two flat lists MUST be reshaped per-class, with no version
  step (FR-020). Recorded as the cheapest and least valuable item in the feature: the schema has no
  instance anywhere (M9) and feature 014 rewrites its structure outright.
- **FR-054**: The golden sets MUST be treated as feature 008 treated them — any change to
  `tests/golden/` is a named, justified, recorded event, not a side effect.
- **FR-055**: The two hand-authored corpus documents
  (`tests/data/corpus/cuems-utils/{fade_showcase,unicode_showcase}.xml`) MUST be accounted for
  explicitly, as feature 008 accounted for them.

### Cross-cutting

- **FR-060**: Every schema edit MUST land in the same commit as its entry in
  `CURRENT_SCHEMA_HASHES` (`tests/contract/test_schema_scope.py:65`).
- **FR-061**: Any type name this feature declares in more than one schema MUST be recorded in
  `KNOWN_IDENTICAL_DUPLICATES` (`tests/contract/test_schema_name_overlap.py:80`) in the same commit,
  and `KNOWN_DIVERGENT_DECLARATIONS` MUST remain **empty**.
- **FR-062**: Nothing ships from this branch alone (D27). The coordinated
  `xml-refactor-merge-candidate` tag comes after 011–014, and `cuems-utils` tags last.
- **FR-063**: Commits are GPG-signed. On `gpg failed to sign`, retry; never `--no-gpg-sign`.
- **FR-UX-001**: Every operator-visible string this feature adds or changes — a reported unknown
  class, a conversion description, a rejection naming a class — MUST follow the existing
  conventions: the schema, the document, the path within it, the offending value, and what to do.
  No shipped message's spelling or meaning changes without the test that pins it changing in the
  same commit.
- **FR-PERF-001**: Mappings-document load MUST stay within **110% of this branch's measured
  figure**, measured on this branch before the change rather than inherited. Feature 008's
  `network_map` row is recorded there as exceeded-or-marginal (10.14–10.49 ms against a 10.20 ms
  budget), so a budget inherited as a number rather than re-measured fails for a reason predating
  this feature — the correction feature 012 made and this feature adopts.
- **FR-PERF-002**: Suite per-test time MUST stay within **110% of 16.40 ms/test**
  (the measured baseline above). The budget is **per test**, not wall-clock: this suite has grown
  from 1485 to 3247 tests across six features, and an absolute wall-time budget reads growth as
  regression.
- **FR-PERF-003**: The migration tool's throughput MUST be stated as a value and measured over a
  named fixture of stated size, and recorded as measured **including when exceeded**. Feature 012's
  `baseline.md` is the pattern — including its two exceeded budgets, and its finding that the
  500 MB/s floor conflated bulk throughput with per-file syscall cost on many small files. A
  project library is many small files, so that finding applies directly and the budget must be set
  from measurement rather than inherited as a number.

---

## Key Entities

- **Device class** — an open-vocabulary name identifying a kind of hardware (`audio`, `video`,
  `dmx` today; `lighting` tomorrow). Carried as an attribute on a device element; the thing a new
  class costs *data* for rather than schema.
- **Device** — one class's port groups on one node. Inputs and outputs, each a group of ports with
  an id, a name and its mappings. Typed conditionally by its class.
- **Class-conditional type** — the schema construct selecting a device's type from its class, so
  `canvas_region` exists on video devices and nowhere else.
- **Hardware-output inventory** — the per-class, per-direction list of physical port names a node
  actually has. Today a six-key literal written twice; after this feature, derived from the
  document. Read by `cuems-engine` at three sites, one of them unguarded.
- **Version step** — one increment of a schema's `doc_version` marker. `project_mappings` 2→3 at
  minimum; `settings` 3→4 and `script`/`hardware_outputs` 2→3 if their axes are in scope.
- **Migration tool** — the documented one-shot rewrite that takes an installation from the old
  shape to the new one, across the node's configuration and every project in the library. Rule 4's
  *"documented tool that runs once"* branch, and feature 007's actual mechanism. It is **not** a
  registered `Conversion`: this feature adds no version step, so the registry has no key for it.
- **Consumer contract** — the written statement, per sibling repository, of which of its measured
  sites change, to what, and whether the old form raises or merely becomes wrong.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Adding a hardware class that needs no special fields requires changes to **zero**
  schemas, **zero** model classes and **zero** constants — demonstrated by a test that adds one.
- **SC-002**: Adding a hardware class that needs special fields requires **one** conditional-type
  declaration plus the type it names, in **one** schema — down from the four-schema, two-constant,
  four-repository cost the table above prices.
- **SC-003**: The library contains **no** declared list of device classes, asserted by a contract
  test rather than by inspection.
- **SC-004**: **100%** of the old-shape documents in the corpus — across all four axes — are
  migrated by the tool, and each decodes to an object equal field for field to its hand-authored
  new-shape equivalent.
- **SC-005**: Reading an **un-migrated** document produces a rejection naming the document, the old
  shape and the tool — asserted on the message, not on the exception type, since `xmlschema`'s own
  validation errors are `ValueError` subclasses too (the distinction feature 008 had to make).
- **SC-006**: `CURRENT_VERSION`, the conversion registry and `DELIBERATE_IDENTITY_STEPS` are
  **byte-identical** to feature 012's — zero version steps, zero new conversions, three allowlist
  entries. The feature's no-bump decision is verified, not asserted.
- **SC-007**: Every consumer site measured in M1–M5 appears in the migration guide with its path,
  its line at a named commit, its fault class and its new shape — count of sites named equals count
  of sites measured.
- **SC-008**: `cuems-engine`'s suite passes against this branch, with `NodeEngine.py:566`'s
  unguarded read exercised by a test on a node carrying no device of that class. *(Verified by
  running that repository's own suite, as feature 012's `sibling-repository-updates.md` did, rather
  than inferred from a call-site census — which is what 012 measured to be the weaker instrument.)*
- **SC-009**: `KNOWN_DIVERGENT_DECLARATIONS` is empty at the tip of the branch, and
  `tests/contract/test_schema_scope.py` and `tests/contract/test_schema_name_overlap.py` pass at
  **every** commit of it, not only the tip.
- **SC-010**: `tests/packaging/test_no_version_bump.py` passes — `0.1.0rc16` unchanged.
- **SC-PERF-001**: Mappings-document load ≤ **110%** of this branch's pre-change measurement,
  recorded with the measurement that set the denominator.
- **SC-PERF-002**: Suite per-test time ≤ **18.04 ms/test** (110% of 16.40 ms).
- **SC-PERF-003**: Conversion throughput measured over the named fixture and recorded against its
  stated budget, with any exceedance recorded as exceeded and its mechanism identified — never
  restated as passing.
- **SC-QUALITY-001**: No new lint or type warnings, and no new deprecation warnings beyond the 215
  the baseline run reports.
- **SC-TEST-001**: Every behaviour change has a test that fails before the implementation and
  passes after it, with the failing-first output recorded — the convention features 008, 011 and
  012 each followed.

---

## Assumptions

Recorded as decisions, so a later reader can tell a default from a finding.

- **A1 — the class vocabulary is open.** FR-002. The proven measurement (`<device class="lighting">`
  validates with no schema change) only means anything under an open vocabulary, and a closed
  enumeration would relocate the cost rather than remove it. The price is A2.
- **A2 — an unrecognised class is reportable, not rejected.** FR-014. Rejecting it would close the
  vocabulary by another route; accepting it silently makes a typo indistinguishable from an
  integration. So it validates, decodes, and is *reported*.
- **A3 — `node_hw_outputs`' reshape belongs to 013, not 014.** The brief's Scope line puts it here,
  and the split is recorded below: 013 changes the inventory's **shape** (keys derived per class);
  014 changes its **source** (the port inventory moves out of `project_mappings`, and
  `default_mappings.xml` retires). Two features touching one accessor in sequence, by decision.
- **A4 — the three legacy key names keep resolving for the three classes that exist.** FR-012.
  `audio_outputs`, `video_outputs`, `dmx_outputs` are what `cuems-engine` reads today; a derived
  dict that produced different key spellings would break three measured sites for no gain.
- **A5 — the migration is a pure reshape with nothing dropped.** FR-024. Every old-shape element
  has a new-shape home; if the plan finds one that does not, that is a finding to record, not a
  drop to make quietly.
- **A6 — rule 4 is discharged by feature 007's route, not feature 008's.** The clarification
  session settled no version bump; 007's rename is the recorded precedent for a rule-4 migration
  whose marker is the element's own presence, and its conversion was *"a documented tool that runs
  once"*. Adopted here with the three costs stated in §"What is already settled" and answered by
  FR-020–FR-029.
- **A6a — the tool's home is a planning decision, not an assumption.** FR-029. Reusing
  `cuems-convert-documents` means giving a version-driven tool a shape-driven mode; a new entry
  point means a second migration command in one release. Neither is free, so neither is assumed.
- **A7 — the repeated-class outcome is specified rather than inherited.** FR-013. `maxOccurs="1"`
  makes the question unaskable today, so the reshape introduces it and the spec must answer it.
- **A8 — this feature changes no identity behaviour.** Feature 012's `NodeUuidType` union, the
  sentinel, the `Uuid` type and the re-mint are untouched. A mappings document's `uuid` element
  keeps its type exactly.

---

## Dependencies

- **Hard**: none. Feature 013 depends on nothing that is not already on `feat/xml-refactor`.
  Features 011 and 012 have both landed on their branches and merged into it.
- **Advisory, and stated in the brief**: 013 comes **before** 014. See the split below.
- **Inherited machinery**: feature 008's strict load path and `LoadReport`, and
  `cuems-convert-documents`' backup discipline as the pattern FR-025 follows. Feature 008's version
  marker and conversion registry are deliberately **not** used (FR-020). Feature 007 supplies the
  rule-4 route; feature 012 supplies the precedents for recording an exceeded budget, for finding
  scripts by root element rather than filename, and for measuring sibling impact by running sibling
  suites rather than counting call sites.
- **Downstream, waiting by decision**: `cuems-frontend` flow 05 of feature 010. Its US8/T032
  requires characterization tests committed **before** its port, so whatever this feature settles
  about the cue-type unions is that flow's input. FR-032 is the obligation to state it.
- **Release gate**: D27. Nothing ships from this branch alone; the coordinated
  `xml-refactor-merge-candidate` tag comes after 011–014, and `cuems-utils` tags last.

---

## The 013 ↔ 014 split, recorded now rather than discovered mid-implementation

Feature 014 moves the port inventory out of `project_mappings`, retires `default_mappings.xml` and
`settings/outputs`, and gives `hardware_outputs` a real structure. Both features touch the
hardware-output accessor. The split:

| Concern | 013 | 014 |
|---|---|---|
| The inventory's **shape** — keys derived per class rather than six literals | **yes** | no |
| The inventory's **source** — which document the ports come from | no | **yes** |
| `_DEVICE_SECTIONS` deleted | **yes** | n/a |
| `project_mappings`' device declarations reshaped | **yes** | no |
| The port inventory leaves `project_mappings` | no | **yes** |
| `default_mappings.xml` retires | no | **yes** |
| `settings/outputs` retires (audit §4.2) | no | **yes** |
| `hardware_outputs` gains DMX, `id`/`name`/`mapped_to`, geometry, latency | no | **yes** |
| `hardware_outputs`' two lists reshaped per class | **yes** | superseded by 014's structure pass |
| `get_{video,audio}_output_id` — the fossil that raises `KeyError` on every node | no | **yes** |
| `cuems-editor`'s `cli.py:59` `default_mappings.xml` read | no | **yes** |
| X15, the namespace typo in `../cuems-engine/dev/test_xml_files/outputs.xml` | no | **yes** |

**The one overlap, now that all four axes are in scope**: 013 reshapes `hardware_outputs`' two
flat lists and 014 replaces that schema's structure outright. That is work done twice on a schema
with **no instance anywhere in the ecosystem** (M9) — the weakest item in the feature, and the
first thing to cut if the plan needs to cut something. Recorded as a known duplication accepted by
the all-four decision, not as an oversight.

---

## Out of scope

- **The adoption/liveness UI tier.** Feature 010 records that it does not exist. It is new product
  work, not a migration, and it belongs to neither this feature nor flow 05's completion.
- **Feature 014's whole scope**, per the table above.
- **Re-establishing the mechanism's feasibility.** Proven 2026-09-23 under the pinned
  `xmlschema==3.4.3`.
- **Any library version bump.** FR-034.
- **Any change to node identity.** A8.
- **`cuems-hardware-discovery`**, which has no checkout. It is feature 014's problem and is
  recorded as such there.

---

## Open items handed to `/speckit.clarify`

Two consumer-reported gaps of one shape — a capability inside `cuemsutils.xml` with no public path
out — recorded in `specs/010-consumer-migration/migration-guide.md` §5b and carried as open by
`specs/planning/refactor-sequencing-2026-10-01.md` §6. They have now been deferred twice. They are
**assigned to this feature's clarification session**, which will place each in 013 or in 014's
public-surface pass; neither is to be carried forward unassigned a third time.

| Item | The gap, measured | Candidate dispositions |
|---|---|---|
| **UR-1** | `partition_by_adoption` exists only at `cuemsutils.xml.settings.NetworkMap:247`. No public call answers "which nodes are adopted". `cuems-engine` removed its own need for it by deleting `find_hosts`, so nothing is blocked today — but `cuems-editor`'s feature 001 is expected to hit it within days | publish it here as part of 013's surface work; or assign it to 014's public-surface pass with the editor's feature 001 as the forcing date |
| **UR-5** | `XmlReaderWriter.validate`'s deprecation warning sends **every** schema to `CuemsScript.validate`, which cannot validate a `settings`, `network_map`, `project_mappings` or `project_settings` document. Those are validated only as a side effect of the `ConfigManager` loaders. §5b records two candidate fixes and judges the second the better one | correct the per-schema advice only (cheap, closes the wrong-advice half); or add the public stand-alone configuration validator §5b calls *"a surface this library does not have and arguably should"* |

**Why this feature is a plausible home for both**: 013 is the feature that reshapes what a
configuration document *is*, so a maintainer porting to the new shape is exactly the reader who
needs a public way to validate one (UR-5) — and 013's own consumer contract work (FR-030–FR-033)
is the same kind of publishing act that closed UR-4 and UR-6. **Why 014 is the other plausible
home**: 014 is already scoped to add a public `ConfigManager` accessor and to settle the
`get_{video,audio}_output_id` fossil, which makes it the feature with a public-surface pass in it
by construction.

The axis-scope and version-bump questions that opened this feature are **settled** — see
§Clarifications. UR-1 and UR-5 are what the clarification session still owes.
