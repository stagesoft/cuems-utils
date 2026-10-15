<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# What the consumers must do — the obligations this feature places on other repositories

**FR-106** · created 2026-10-13 by the `/speckit.analyze` pass · **every row measured in that
repository's checkout, never predicted here** (FR-106a)

---

## Why this document exists

The gate list reads as nine symmetric items. It is not symmetric: **four** of them are complete when
this library lands, and **six** have a half this repository cannot write — three of those being
strict xfails in `cuems-editor` that SC-012 originally claimed would all turn XPASS on this
feature's landing. `contracts/sibling-gates.md` had already measured the opposite (three of its seven
*Flips when* cells say "**and**"), but only G1's obligation had been written down as a requirement,
so nothing connected the two.

The result was a success criterion this feature could not satisfy and three obligations with no
owner. This document is the one place they are all counted, and it is this repository's counterpart
to `../cuems-editor/specs/002-config-round-trip/tag-readiness.md` — the same set seen from the other
side. **T105e reconciles them row by row**; a row in one and not the other is a missed obligation.

**Status vocabulary** (FR-106a — no row may be a prediction):

| Status | Meaning |
|---|---|
| `verified outstanding` | measured in that checkout; the work is not done |
| `verified done` | measured in that checkout; the work is done |
| `not verifiable yet` | with the reason — a tag not cut, a checkout absent |

---

## The ten obligations

Measured 2026-10-13 against each sibling's working tree. Where a sibling carries an
`xml-refactor-merge-candidate` tag, the **re-verification at the tag** is T105a–T105e's job
(FR-080c): a tip is not a stable reference, which is the lesson that produced that requirement.

### 1 — `cuems-editor` · G1 · pass the tolerance on at its own write site

| | |
|---|---|
| **Site** | `src/cuemseditor/CuemsWsUser.py:258-261`, `_config_path` — calls `manager.conf_path(file_name)` / `manager.project_path(project_uname, file_name)` with no tolerance, and its own docstring says *"`FileNotFoundError` when it does not exist (UR-6)"* |
| **Must do** | pass `must_exist=False` at the **write** site. The read sites are correct as they stand: `_load_config_document:285` catches `FileNotFoundError` and answers with a root instance, and `_resolve_config_path:297` answers `None` — both are deliberate, and neither should start tolerating |
| **Marker** | `tests/test_schema_descriptor.py::test_first_config_save_of_project_settings_round_trips` |
| **Flips on a library change alone?** | **No** |
| **Requirement** | FR-008 · verified by **T105a** |
| **Status** | `verified outstanding` (2026-10-13) |

### 2 — `cuems-editor` · G2 · stop refusing `project_settings`, and give it a load step

| | |
|---|---|
| **Site** | `CuemsWsUser.py:234-235` — `CONFIG_LOAD_REFUSED['project_settings']` reads *"project_settings has no public read projection in cuemsutils (cuems-editor UR-7); it cannot be loaded yet"*; the name is absent from `CONFIG_LOAD_STEPS`, so `_load_config_document:290` short-circuits with `return True, revision, None` |
| **Must do** | remove the refusal entry, add the `project_settings` load step, and delete the `None`-document early-out so `to_wire('project_settings')` is reached |
| **Marker** | `tests/test_upstream_gates.py::test_config_load_project_settings_round_trips` |
| **Flips on a library change alone?** | **No** |
| **Requirement** | FR-017 · verified by **T105b** |
| **Status** | `verified outstanding` (2026-10-13) |

### 3 — `cuems-nodeconf` · G4 · ship the `node_set` handler

| | |
|---|---|
| **Site** | nothing to point at — `node_set` appears **nowhere** in that repository's source (measured 2026-10-13, zero hits). The brief is `specs/planning/12-node-set-alias.md`, whose §4 states the ordering *"the library first, then this repository"* |
| **Must do** | ship the IPC action that calls `NodeIndex.set_alias`, with the semantics its own brief states — which **T050** verifies word for word against this library's implementation, because any divergence is a change to a two-repository contract (FR-046) |
| **Marker** | `cuems-editor`'s `tests/test_upstream_gates.py::test_nodeconf_engine_callback_accepts_node_set` — the test is in a *third* repository, and reads *unknown action* today |
| **Flips on a library change alone?** | **No.** This is the only obligation of this feature's whose work and whose test node are in two different repositories, neither of them this one |
| **Requirement** | FR-047 · verified by **T105c** |
| **Status** | `verified outstanding` (2026-10-13) |

### 4 — `cuems-frontend` · G3 · delete the hand-written transform

| | |
|---|---|
| **Site** | `src/app/services/projects/handlers/schema-descriptor.handler.ts` — `toWireShape` plus the starting-values table; exercised by `schema-descriptor.handler.spec.ts:46` as *"the UR-1 transform"* |
| **Must do** | delete it in **one** edit, with **no** value hand-authored on its side. That deletion — not a test passing here — is G3's completion marker for that repository |
| **Marker** | the deletion itself, plus its spec block |
| **Flips on a library change alone?** | No, but it is a *removal* rather than a blocked feature: the workaround was written as one function precisely so it could go in one edit |
| **Requirement** | FR-031, SC-006 · verified by **T106** |
| **Status** | `verified outstanding` (2026-10-13) |

### 5 — `cuems-editor` · G3 · correct a docstring that becomes false

| | |
|---|---|
| **Site** | `CuemsWsUser.py:264-270`, `_root_instance` — *"A starting point for a form, not a saveable document: its required leaves are null (cuems-frontend UR-1, gate G3)"* |
| **Must do** | correct it. After G3 the required leaves are **seeded** and the instance **saves** (FR-023, FR-025), so the docstring states the exact opposite of the behaviour. It is the clearest single artefact of the position FR-026 reverses, living in a consumer rather than here |
| **Marker** | the docstring; no test asserts it |
| **Flips on a library change alone?** | No — and it would go stale **silently**, which is why it is a row rather than a note |
| **Requirement** | FR-026 (the reversal), FR-106 · verified by **T105e**'s reconciliation |
| **Status** | `verified outstanding` (2026-10-13) |

### 6 — `cuems-editor` · S1 · delete the regular expression over our prose

| | |
|---|---|
| **Site** | `src/cuemseditor/node_reads.py:37` — `_COLLIDED_IDENTITY = re.compile(r'node identities are not unique: (\S+) is carried by')`; `:43` returns `''` when it does not match; `IdentityCollision.message` (`:22-33`) carries the library's sentence as the payload. The module says so itself: *"This only lifts the identity out of the sentence the library wrote, because the exception carries no structured field for it (upstream report UR-4)"* |
| **Must do** | catch `cuemsutils.errors.NodeIdentityCollisionError` by name, read `collisions` and the hardware addresses as attributes, and delete both the pattern and the empty-string fallback |
| **Marker** | the two deletions and the named `except` — **this is the whole of SC-009**, whose only measurable form is a removal in this repository |
| **Flips on a library change alone?** | No |
| **Requirement** | FR-065b, SC-009 · verified by **T105d** |
| **Status** | `verified outstanding` (2026-10-13) |

### 7 — `cuems-engine` · the one surviving live dead-end document

| | |
|---|---|
| **Site** | `dev/test_xml_files/settings.xml` — carries the retired counts (flat `<audioplayer>`/`<dmxplayer>`) at that repository's tip. Measured 2026-10-13: the **only** such document across all seven checkouts |
| **Must do** | migrate with the fixed `cuems-reshape-devices`, **in this feature** (FR-105), rather than leaving it for the next gate to find with its own signal buried under it |
| **Marker** | the document reshapes and then loads |
| **Flips on a library change alone?** | It is fixed *by* running our own tool, so yes once someone runs it — which is what makes leaving it undone indefensible |
| **Requirement** | SC-003a, FR-105 · closed by **T039a** |
| **Status** | ✅ **closed in the engine's own history** (re-verified 2026-10-14 on `feat/xml-refactor`: the file is current, see the table at the end). *Historical reading, 2026-10-13, taken against a stale copy:* ⚠ measured, and the premise was wrong (2026-10-13): the fixed tool correctly reshapes the flat players (`classify` returns `old`, `reshape_players` runs), but the **whole** `dev/test_xml_files/` directory in that repository — every one of its ten documents, not only `settings.xml` — carries a stale pre-rename namespace (`http://stagelab.net/cuems`) against this schema's `https://stagelab.coop/cuems/`, so the post-reshape validation refuses it for a reason that predates this feature and is unrelated to G5. The reshape tool correctly reports `skipped (would not validate: … is not an element of the schema …)` and writes nothing — no backup is left, no bytes changed. **Not closed here**: fixing one file's namespace in isolation would be a partial, misleading patch to a directory-wide, pre-existing defect in a sibling repository, and is out of this feature's scope to decide unilaterally. Recorded as a new finding for that repository's own maintainers rather than forced to a false "done". |

### 8 — the eleven historical dead-end documents · the control population

| | |
|---|---|
| **Site** | restored by ref, because they exist in no working tree — 014's gate pass hand-rewrote them, which is the cost SC-004 says stops at two: **9** at `cuems-power-bridge@dd1256f^` (`tests/fixtures/network_map/map-*/settings.xml`), **2** at `cuems-nodeconf@61c5705^` (`tests/fixtures/etc_cuems/settings{,_sentinel}.xml`) |
| **Must do** | nothing in those repositories — their fixtures are already hand-corrected. This row exists because the **population is SC-003's evidence**, and it had been described rather than pinned, which would have cost whoever ran T039 an afternoon of searching |
| **Marker** | 11 of 11 migrate with one invocation, against a control of 0 of 11 |
| **Requirement** | SC-003 · measured by **T039** |
| **Status** | `verified done` — nothing outstanding in either sibling; the refs are the deliverable |

### 9 — every Python sibling · fixtures the indenting writer may break

| | |
|---|---|
| **Site** | unknown until measured. S3 changes the bytes of every document this library writes, and five repositories hold fixtures and assertions over such documents |
| **Must do** | close, **in this feature**, any fixture this feature breaks — in that sibling's own checkout (FR-105). 014 paid for this lesson with eleven hand-rewritten documents across two repositories |
| **Marker** | T107's **two-arm** run — the branch point and this branch — so nothing is attributed to this feature without a control. Without that arm, 014's gates would have reported 151 of someone else's failures as their own |
| **Flips on a library change alone?** | n/a — this is breakage, not a gate |
| **Requirement** | FR-103, FR-105, SC-014 · measured by **T107**, closed by **T108** |
| **Status** | `not verifiable yet` — needs the code of all nine stories in |

### 10 — `cuems-editor` · the tag-readiness record

| | |
|---|---|
| **Site** | `specs/002-config-round-trip/tag-readiness.md`, *Status: **NOT READY*** |
| **Must do** | move to ready once rows 1, 2, 3 and 6 land. It cannot move on this feature alone, and **that is the correction** SC-012a records: the original SC-012 made this record's state a deliverable of this repository |
| **Marker** | the record's own status line |
| **Requirement** | SC-012a, SC-012b, FR-106 · reconciled by **T105e** |
| **Status** | `verified outstanding` (2026-10-13) |

---

## What *does* flip on this feature's landing alone

Four of `cuems-editor`'s seven strict xfails, all G3, and they are what SC-012 now claims:

| Test | Blocked today by |
|---|---|
| `test_a_cue_built_from_the_descriptor_instance_saves_through_project_save` | refused at the output volume |
| `test_a_config_root_instance_saves_through_config_save[settings]` | the root instance is `{"Settings": null}` |
| `test_a_config_root_instance_saves_through_config_save[project_mappings]` | refused at the node count |
| `test_a_config_root_instance_saves_through_config_save[project_settings]` | refused at a setting's name |

**G5 has no sibling test at all.** It is this library's defect; the editor never had a test for it,
and it appears in that repository's gate record only so the list is complete in one place.

---

## The reading that outlives this feature

Nine items, ten obligations, and **six of them in repositories this feature does not touch**. The
asymmetry is not a planning failure — a library's gates mostly *are* half-obligations — but the gate
list had no column for it, so three obligations existed only as a sentence in a contract document
and one success criterion asserted the opposite of what had been measured.

The cheap defence is the one this feature institutionalises for cross-repository *claims* in
FR-080c: **assert against the artefact, not against a description of it.** Rows 1, 2, 3, 5 and 6
above are each a file and a line number in somebody else's tree. Every one of them was found by
looking, and three had been missed by every pass that did not.

---

## Re-verified after the code landed — 2026-10-14 (T105a–T105e, T106, T107)

Measured in each checkout at its working tree (this library's tree: the uncommitted branch
`015-consumer-gate-closure`; control arm: a throwaway `git worktree` at `75a958e`, never the shared
checkout). `cuems-engine` was first read on `format/module_extraction` and **re-read on `feat/xml-refactor` (`fc0cad3`, `__version__ = "0.1.0rc7"`) the same day**; row 7 reflects the latter. Neither `cuems-editor` nor `cuems-engine` carries an `xml-refactor-merge-candidate` tag,
so these are tips, not tags — **`not verifiable at a tag yet`** for those two, and the table is to be
re-run when they are tagged.

| # | Row | Measured status | Evidence |
|---|---|---|---|
| 1 | `cuems-editor` G1 | `verified outstanding` | `CuemsWsUser.py:258-261` `_config_path` still calls `conf_path(file_name)` / `project_path(project_uname, file_name)` with no `must_exist`; its G1 xfail still stands (4 xfailed) |
| 2 | `cuems-editor` G2 | `verified outstanding` | `CONFIG_LOAD_REFUSED['project_settings']` at `:234`, absent from `CONFIG_LOAD_STEPS`, `:290` early-out intact |
| 3 | `cuems-nodeconf` G4 | `verified outstanding` | no `node_set` anywhere under `cuemsnodeconf/`; editor's `test_nodeconf_engine_callback_accepts_node_set` still xfails *unknown action* (the control reading); the library half (`NodeIndex.set_alias`) is landed; the handler spec is `../cuems-nodeconf/specs/planning/12-node-set-alias.md` |
| 4 | `cuems-frontend` G3 | `verified outstanding`, deletable in one edit | `toWireShape` + `UR1_UI_STARTING_VALUES` (`schema-descriptor.handler.ts:84,149`) are called from `project-create.handler.ts:19,37` only. **Measured against the library's instances (T106)**: repeated containers arrive as lists of single-key wrappers (`channels: [{"channel": …}]`), `class` is present, every required scalar carries a value — so nothing needs hand-authoring on the UI side. ⚠ **The values differ from the UI's table**: library seeds are `output_vol 0`, `channel_vol 0`, `x_scale/y_scale 0.0`, where the UI's table gives `80`, `80`, `1`, `1`. Deleting the transform in one edit therefore **changes what a new output starts at**; that is a product decision for the frontend, not a defect here |
| 5 | `cuems-editor` G3 docstring | `verified outstanding` | `_root_instance` (`CuemsWsUser.py:264-270`) still reads *"not a saveable document: its required leaves are null"*, now false |
| 6 | `cuems-editor` S1 | `verified outstanding` | `node_reads.py:38` `_COLLIDED_IDENTITY` regex and the `''` fallback in `collided_identity` both still present; `NodeIdentityCollisionError` is not named anywhere in `src/` |
| 7 | `cuems-engine` dead-end doc | `verified done` (2026-10-14, on `feat/xml-refactor` @ `fc0cad3`) | `dev/test_xml_files/settings.xml` is in the current namespace and device shape (014's `9fce7e6`); `cuems-reshape-devices --dry-run` reports `already current`, and `load_config_document(Settings, …)` returns a `Settings`. The earlier ⚠ measurement below was taken on the wrong branch (`format/module_extraction`) and is **superseded** |
| 8 | control population | `verified done` | unchanged |
| 9 | fixtures the indenting writer breaks | **one found, closed** (below) | see T107/T108 |
| 10 | tag-readiness record | reconciled | see below |

### What flipped, and what did not (editor's seven strict xfails)

| Test | Result with this library | Why |
|---|---|---|
| `test_a_config_root_instance_saves_through_config_save[settings]` | **XPASS(strict)** — flipped | G3 (b) landed |
| `…[project_mappings]` | **flipped** | same |
| `…[project_settings]` | **flipped** | same |
| `test_a_cue_built_from_the_descriptor_instance_saves_through_project_save` | **still xfails** — *not* the flip SC-012 claimed | the failure is now `missing required attribute 'class'` at `CueOutput`, and the cause is the **test's construction**, not the library: it takes `_script_instance('AudioCueOutputsType')`, which now (FR-021) *already carries* the `CueOutput` wrapper and `class`, then sets `output_name` beside it and wraps it again as `{'CueOutput': [output]}` — a double wrap built for the old, unwrapped instance. Rebuilding that one construction is the editor's half of G3 (a) |
| G1, G2, G4 | still xfail | each has a consumer half (rows 1–3) |

So **three of the four** flips SC-012 claimed happen on this library change; the fourth needs the
editor to follow FR-021. SC-012's "four" is corrected here rather than in the frozen spec.

### T108 — the fixture this feature broke, closed in the sibling

`cuems-editor` `tests/test_repair_durations.py::test_structured_duration_differing_from_the_database_is_reported`
failed only on this branch: it asserted `…</CTimecode></duration>` after stripping `\n`, which
left the indentation. Fixed in that checkout to strip inter-element whitespace. The three flipped
xfails had their markers removed (S6: *the marker comes off and the assertion stays*). **Both edits
are uncommitted in `../cuems-editor`** for the maintainer to review there. After them the editor's
suite is `2 failed · 261 passed · 3 skipped · 4 xfailed`; the 2 failures
(`test_document_load_report.py::test_an_unrepairable_open_is_document_load_failed[…]`) fail
identically on the control arm and are not this feature's.

### T105e — reconciled with `../cuems-editor/specs/002-config-round-trip/tag-readiness.md`

Both list the same seven xfails and the same owners; they agree row by row, with two corrections
this measurement forces on the editor's record (not edited there — that is its repository's record):
the three config-root G3 rows are no longer standing, and the G3 cue row's flip condition is
*"the test builds the cue from the wrapped instance"*, not only a library change. **G5**: closed in
this library (`b43bc50`), no editor test, as that record says.

### Correction, 2026-10-14 (later the same day): `cuems-engine` was read on the wrong branch

Everything above that says `cuems-engine` was *unverifiable* or *unmeasurable* came from its checkout
being on `format/module_extraction`, a branch with no `xml-refactor` line. On **`feat/xml-refactor`**
(`fc0cad3`; created locally from `origin/feat/xml-refactor`, tree clean):

- **Row 7** is `verified done` — see the table.
- Its suite, **run in two arms** (A = this library at `75a958e`, B = this branch): **28 failed ·
  831 passed · 1 error in both, with the identical set of 28 failures** — `test_ossia.py` (14),
  `test_pyossia_osc.py` (8), `test_players_dmxplayer.py` (5), `test_project_go.py` (1). **None is
  attributable to this feature.** ⚠ The runner could not use the real `pyossia` (`>= 2.0.0-rc6+124+cuems3`
  is not obtainable here; the local `libossia` is rc4 and fails to load), so a **mock** stood in, and the
  28 are exactly the tests that touch it (`isinstance() arg 2 must be a type`). A verdict on those
  needs a host with `python3-pyossia`. `libmtcmaster` was built in scratch to let the rest import.
- The two facts 012's guide states about the engine are **true at this branch**: `__version__ =
  "0.1.0rc7"` and `cluster_warning` is published at `/engine/status/cluster_warning` with a `"missing"`
  list (`ControllerEngine.py:1126`). The "corrections" this feature first made to that guide were
  therefore **wrong and have been reverted**; the tests that guard them skip only because the engine
  carries no `xml-refactor-merge-candidate` tag, not because the claims fail.

---

## Closed — 2026-10-15: every consumer half done, each row measured at its commit

All ten obligations are now `verified done`, measured against each sibling's **committed** tree
(GPG-signed local commits, not pushed when this was written; no tag was created or moved, since tags
stay maintainer-only). Library half: `cuems-utils` `0b3690e`. The earlier tables above stay as
written.

| # | Row | Status | Closed by | Evidence |
|---|---|---|---|---|
| 1 | `cuems-editor` G1 | `verified done` | editor `6de91fb` | `_config_path(..., must_exist=False)` at the write site; `_save_config_document` treats a `None` revision as a create (no backup; a file that appeared meanwhile is `ConfigChanged`). G1 test XPASSed strictly, marker off; two new direct tests |
| 2 | `cuems-editor` G2 | `verified done` | editor `35a79d1` | refusal removed, `load_project_settings` load step, early-out deleted. ⚠ **The editor's predicted shape was wrong**: the projection keys each item `{"SettingType": {…}}`, which is this library's single projection (contract C2, "a second projection is forbidden"). The G2 test now asserts that shape **and** C2's round trip through `config_save` |
| 3 | `cuems-nodeconf` G4 | `verified done` | nodeconf `3d3601d` (already landed) | the editor's G4 test passes against nodeconf `82b0a69` and **fails** against `155fe6c` with `unknown action: node_set` (control arm, scratch worktrees, removed) |
| 4 | `cuems-frontend` G3 | `verified done` | frontend `6b69b41`, on this library's `0b3690e` | `toWireShape` + `UR1_UI_STARTING_VALUES` deleted in one edit, no value authored on that side. That needed this library's **seeding rule 0**: `script.xsd` declares `default=` on `output_vol`/`channel_vol` (80) and `x_scale`/`y_scale` (1), which resolved row 4's ⚠ (the old seeds were 0 / 0 / 0.0: silent, invisible). A new output starts exactly as before (T016); only `output_name` moved (`null` → the placeholder `"x"`, overwritten by every caller). Descriptor fixtures re-recorded beside the old ones. 288 specs pass |
| 5 | `cuems-editor` G3 docstring | `verified done` | editor `fc025a7` | `_root_instance`, `config_load` and `ws-command-responses.txt` now say the root instance is saveable |
| 6 | `cuems-editor` S1 | `verified done` | editor `2360936` | `except NodeIdentityCollisionError`, `IdentityCollision.from_error`; pattern and `''` fallback deleted, and a source-grep test keeps them out |
| 7 | `cuems-engine` dead-end doc | `verified done` | (2026-10-14) | unchanged |
| 8 | control population | `verified done` | — | unchanged |
| 9 | indenting-writer fixtures | `verified done` | editor `8c42e71` | the one fixture T108 found, now committed in that repository |
| 10 | `cuems-editor` tag-readiness | `verified done` | editor `e5e6ac1` | **Status: READY**. Its three conditions measured: no xfail (271 passed, 3 skipped; the seven gate tests pass without markers), G5 `b43bc50` an ancestor of `0b3690e`, run recorded as `evidence/suite-tag-ready.txt` |

**The G3 cue flip.** The fourth of SC-012's flips came from the editor rebuilding its own test
construction (`fc025a7`: the output instance already carries its `CueOutput` wrapper and the test
wrapped it again), not from a library change, as the table above predicted on 2026-10-14.

**Three findings worth carrying:**
- **The `SettingType` wire key.** `to_wire('project_settings')` keys repeated items by the bound
  model class, where `network_map`'s `node` happens to match its element name only because its class
  is named that. It is consistent, round-trips, and is contractually the shared projection, so it was
  not changed. But it is a class name on the wire. Changing it would be a library-wide wire decision,
  not a project_settings one.
- **Media values in a new cue.** The descriptor now seeds `Media`'s four optional media values with
  placeholders (`file_md5` `"000…0"`, sizes 1). A UI that sends them would put values in a script
  that disagree with the library row, which the editor's media check reports as repairs. The frontend
  drops them; any other client building cues from the descriptor must do the same.
- **What remains is outside every repository's code**: pushing the four repositories, re-cutting the
  candidate tags (maintainer-only), and the live quickstart run against a controller on the
  coordinated tag (`cuems-frontend` `not-performed.md`).
