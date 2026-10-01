<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Prompt — amend `cuems-editor` `001` tasks after `cuems-utils` 013 lands

**Paste everything below the rule into a session running in
`/disk/Projects/StageLab/cuems-editor`.** The session has no memory of the
`cuems-utils` work. What it cannot discover here is inlined.

Authored in `cuems-utils` at `specs/planning/`. The fault list was measured
2026-10-01 against editor `specs/001-cuems-utils-migration/` (draft, 63 tasks,
none done) and `cuems-utils` `5ea30e2` (013 axes A and C in, axis D not in,
`partition_by_adoption` not yet public). **Do not run this prompt against that
tree.** The gate below is the start.

---

You are amending `specs/001-cuems-utils-migration/` so its tasks match a landed
`cuems-utils` feature **013** (device-class reshape). You are not starting a
second feature. You are not implementing `src/`.

001 was written against `cuems-utils` `e9ed8af` and treats 013 as one commit pin:
`from cuemsutils.tools.NodeList import partition_by_adoption`. That pin is
necessary and already in FR-009 / T012 / T036. It is not the whole of 013.
Axes A and D change documents this feature loads and the wire `to_wire()`
emits. The task list still says the `project` frame has exactly two deltas and
that `initial_mappings` keeps the pre-013 form. Those sentences become false
the day 013 is the library this editor imports.

## 0. Gate — stop if 013 has not landed

Run these against `../cuems-utils`. All five must hold. Record the SHA
(`git -C ../cuems-utils rev-parse HEAD`) and each result in
`specs/001-cuems-utils-migration/evidence/cuems-utils-013-landed.txt`. If any
fails, stop. Write which check failed. Do not amend the tasks against a
partial 013 (axis A without axis D freezes a half shape).

```bash
git -C ../cuems-utils rev-parse HEAD
# 1. public partition
../cuems-utils/.venv/bin/python -c "from cuemsutils.tools.NodeList import partition_by_adoption"
# 2. axis A — one device element
grep -n 'name="device"' ../cuems-utils/src/cuemsutils/xml/schemas/project_mappings.xsd
# 3. axis D — one cue element
grep -n 'name="Cue"' ../cuems-utils/src/cuemsutils/xml/schemas/script.xsd
# 4. the reshape tool exists
grep -n 'cuems-reshape-devices' ../cuems-utils/pyproject.toml
# 5. the editor section of the guide exists
test -f ../cuems-utils/specs/013-device-class-reshape/migration-guide.md
```

`hardware_outputs.xsd` (013 T048) may still be the old shape. Do not wait on
it. 001 already rejects schema `hardware_outputs` and defers the port inventory
to `cuems-utils` 014.

Read, after the gate passes:

| Order | Where | Why |
|---|---|---|
| 1 | `specs/001-cuems-utils-migration/spec.md`, `tasks.md`, `plan.md`, `data-model.md`, `contracts/project-payload.md` | the text you are amending |
| 2 | `../cuems-utils/specs/013-device-class-reshape/migration-guide.md` §4 | the editor sites, measured at `106015c`, and the dict-shaped fix |
| 3 | `../cuems-utils/specs/013-device-class-reshape/contracts/library-surface.md` §5 | what `to_wire()` actually changes |
| 4 | `../cuems-utils/specs/013-device-class-reshape/data-model.md` §2 and §4.1 | mappings document and cue element, before and after |

Then re-measure the six sites in guide §4 against **this** tree. Line numbers
there are `106015c`. Yours have moved if 001's source work has started. Grep;
do not transcribe.

## 1. What 013 changed, inlined

**Mappings (axis A), already the on-disk shape.** A node's per-class elements
become one repeated element:

```xml
<audio>…</audio>  →  <devices><device class="audio">…</device></devices>
<video>…</video>  →  <devices><device class="video">…</device></devices>
```

The same collapse applies to the six `default_*_{input,output}` elements: one
`<defaults><default class="…" direction="input|output">`.

**Scripts (axis D).** Hardware cues and their outputs change **wire key only**.
Python classes do not move. `AudioCue`, `VideoCue`, `DmxCue` and the three
`*CueOutput` classes keep their names, fields, equality, hashing, and
`isinstance` behaviour. `ActionCue`, `FadeCue`, and `CueList` keep their own
elements. An unknown class decodes to `MediaCue` / `CueOutput`.

```json
{"AudioCue": {...}}       →  {"Cue": {..., "class": "audio"}}
{"AudioCueOutput": {...}} →  {"CueOutput": {..., "class": "audio"}}
```

`video` and `dmx` move the same way. `class` is whatever the document says,
including a class this library has never named.

There is **no conversion on read** and **no `doc_version` step**. An old-shape
script or mappings file fails the strict load. `cuems-reshape-devices` is the
only rewriter for that shape. It is run over the whole library in one pass,
because a half-migrated library would put `Cue` and `AudioCue` in one payload.

`ConfigManager.generate_example(SchemaName.SCRIPT)` emits the new cue key.
That call does not import `cuemsutils.xml`.

## 2. The faults to amend

Each fault is a sentence in 001 that was true at `e9ed8af` and is false once
the gate passes. Amend the spec requirement and every task that quotes it, in
the same edit. A task left pointing at the old sentence will be re-derived
wrong.

### F1 — the `project` frame has a third delta

**Now:** spec US3, FR-011, SC-004, the key-entities paragraph, `plan.md`,
`data-model.md`, `contracts/project-payload.md`, tasks phase 5 (T017, T027).
Exactly two deltas: (a) `schemaLocation` absent, (b) `Media.duration` wrapped.
A third difference fails the test.

**After:** three deltas. Add

| Id | Change |
|---|---|
| (c) | A hardware cue's wire key is `Cue`, with `class` inside (`audio`, `video`, `dmx`, or any other string the document carried). A hardware cue output's key is `CueOutput`, with `class` likewise. `ActionCue`, `FadeCue`, and `CueList` stay their own keys. |

Key order otherwise unchanged. Cue booleans stay `"True"` / `"False"`.
`doc_version` stays off the wire. Delta (c) is part of **payload version 1**
(FR-047's list of what that version includes). It is not a bump to 2: version
1 has not shipped, and FR-047 already defines version 1 as every delta this
feature enumerates. A later change to an existing message still bumps by
FR-047a.

Milestone 1 still must not be deployed to a controller. The existing reason
(duration wrapping, no handshake yet) now includes delta (c): a pre-05 UI
mis-reads `Cue`. Do not add a local rewrite that puts `AudioCue` back. That
rewrite is the wire-dict manipulation FR-012 forbids.

T013 / T015 (`initial_template` versus the reconstructed `create_script()`
baseline) gain the same cue-key delta. `generate_example` emits it. Do not
strip it to keep the old envelope pretty.

### F2 — `initial_mappings` is not the pre-013 form

**Now:** US6 scenario 2, FR-031, T009, T034. A merged node has "the same wire
form as before", and any difference from `evidence/initial-mappings.json` is a
bug or an enumerated delta. The capture procedure never names `<device class>`.
The library those sentences were measured on is `e9ed8af`.

**After:** the capture is taken against the landed SHA from the gate, not
against `e9ed8af`. State that SHA in the evidence README. The mappings half of
a merged node carries `devices` / `device` / `class` (and `defaults` /
`default` / `class` / `direction`) as `to_wire()` emitted them.

T037's "output blocks stay from the existing mapping node" means those blocks
are copied through. It does **not** mean look up `audio`, `video`, or `dmx`.
Guide §4 is right that `CuemsWsServer.py`'s merge is a pass-through: the
comment at the old `:439` is not a keyed read. Add a test that feeds a
post-013 mapping node (`device class="lighting"` included) and asserts `class`
is still in the merged `initial_mappings` value. That test fails first against
a merge that only copies the three old keys.

Do not normalize a mix of `<audio>` and `<device class="audio">` in the editor.
Say, in the edge cases, that a half-migrated library is an operator error
fixed by `cuems-reshape-devices` over the whole library. The editor serves
what the library returned.

The merge comment is still **not** one of the fourteen deprecated-surface call
sites (013 FR-033). Do not reopen the census around it.

### F3 — the duration walk is on the object, not on the wire key

**Now:** T023 rewrites `_fix_media_durations` onto the loaded object and says
nothing about `class`. Guide §4's fix for `_walk_media_durations` is this:

```python
if 'Cue' in item:
    cue_data = item['Cue']
```

That snippet walks the **wire dict**. 001 FR-012 and T023 already forbid that
walk. Implementing the snippet would close 013's note by reopening 001's
constitution violation.

**After:** T023 finds media cues on the loaded object. `isinstance` against
`AudioCue`, `VideoCue`, and `DmxCue` still works after axis D (library
FR-050a). Also visit a `MediaCue` whose `class` is none of those three: a new
class is the point of 013, and a duration correction that only knows three
names becomes wrong the day a fourth appears. Assign `CTimecode` on that
object. Do not read or write the wire dict.

The test that already requires a client payload of `"00:00:00.000"` to be
accepted and then corrected must use a payload whose cue key is `Cue` and
whose `class` is `audio`. Add the same case for `class` `video` and for one
class that is not a name in the schema (`lighting` is the 013 fixture's
class). A walker that still does `'AudioCue' in item` fails those.

### F4 — do not resurrect `CUE_TYPES`

**Now:** T024 deletes `_collect_cue_ids`, `_nullify_dangling_refs`, and
`_collect_cue_ids`'s caller path. Guide §4 says `CUE_TYPES` collapses to
`['Cue', 'ActionCue', 'FadeCue', 'CueList']` and that the dangling walks
become wrong for the three hardware names.

**After:** those walks stay deleted. The library rule is by cue identity, not
by element name, so it already sees a `Cue` of any class. Collapsing
`CUE_TYPES` and keeping the walks would be a second dangling-reference
implementation. T024's retirement note (`evidence/test-retirements.md`) must
say that, and must say the guide's collapsed list was not ported.

Add to the public-surface scan (T011) a rejection of `CUE_TYPES`,
`'AudioCue' in`, `'VideoCue' in`, and `'DmxCue' in` under `src/`. The
`ProjectMappings` exception in `cli.py` stays the only carried exception.

### F5 — `repair_durations` does not become a second reshape tool

**Now:** T029 reads with `load_with_report`, writes no script, and reports
`SKIPPED_INVALID` when it cannot read. It never mentions an old-shape script.
013's edge case is that this tool **fails** on an un-migrated document instead
of rewriting it. That is the safer direction. 001's Q5 already retired pass B
and refused a second document rewriter.

**After:** T028/T029 gain one case. A fixture in the pre-013 cue shape (element
`AudioCue`, no `class`) is reported `SKIPPED_INVALID` with the library's
reason, the file checksum is unchanged, and `cuems-reshape-devices` is not
invoked. The help text states that an old device shape is corrected by that
tool, then a save in the editor, not by this one.

Do not fold pass B back in. Do not extend `cuems-convert-documents`. 010's
FR-044 fold is a different question and is not this amendment.

### F6 — the 013 pin stops being conditional

**Now:** T012 and T036 wait until the import succeeds, and tell the session to
say "not pinnable yet" otherwise. T014 says the template replacement does not
wait on 013.

**After the gate:** the import exists. T012 records the gate's SHA; it does
not carry an "if it fails" branch. T036's precondition is that file. T014's
"does not wait" line stays, with one added clause: the example it serves
includes delta (c), and that is not a reason to wait or to reshape the
example locally.

### F7 — line numbers for the guide

001 moves the sites guide §4 names (T023, T024, T037). After the task text is
amended, write
`specs/001-cuems-utils-migration/upstream-reports/UR-2-post-013-editor-sites.md`
listing each former M11 site, whether it was deleted or rewritten, and the
path a fresh grep finds. Do not edit `../cuems-utils`. That report is how
013's guide gets re-measured; it is not a request for a new library function.

## 3. What this session edits

| File | Edit |
|---|---|
| `spec.md` | US3, US6 scenario 2, FR-008, FR-011, FR-015, FR-031, FR-047's version-1 list, SC-004, the `project` frame entity, the ecosystem-state row that says 013 is "in implementation", one edge case for a half-migrated library |
| `tasks.md` | Phase 5 title and goal; T011, T012, T013, T014, T015, T017, T023, T024, T027, T028, T029, T032, T034, T036, T037 |
| `plan.md` | The two-delta success line and the phase-5 row |
| `data-model.md` | The two-delta paragraph |
| `contracts/project-payload.md` | The sanctioned-delta table. A third difference is no longer an automatic failure; an unlisted difference still is |
| `evidence/cuems-utils-013-landed.txt` | The gate |
| `upstream-reports/UR-2-post-013-editor-sites.md` | F7 |

Do not edit `src/`, `tests/`, `debian/`, or anything under `../cuems-utils`.
If `src/` already contains `'AudioCue' in item`, a `CUE_TYPES` list, or a
merge that copies only `audio`/`video`/`dmx`, do not fix it in this session.
The amended tasks are what fail on it. Say so at the top of `tasks.md`.

Do not switch the payload oracle to `../cuems-utils/tests/golden/`. 013
restates that corpus for the cue key. 001's pass condition stays the editor
capture, taken against the landed SHA, with deltas (a), (b), and (c) listed.
A golden checksum is still not a pass here.

## 4. Do not

- Do not import `cuemsutils.xml`, add `_select_adopted`, or re-test `NodeRole`
  or `Uuid`.
- Do not walk a wire dict to preserve an object-level result.
- Do not lower `cuemsutils>=0.1.0rc16,<0.1.1`. 013 does not cut a version.
- Do not treat `node_mappings["audio"]` or `node_hw_outputs["video_outputs"]`
  as this repository's problem. Those compatibility surfaces are the engine's.
  This repository's mappings path is the dict it merges and forwards.
- Do not pull 014's port inventory, `cli.py`'s `ProjectMappings` import, or
  `default_mappings.xml` into this amendment.
- Do not cut or move a tag.

Commits are GPG-signed. On `gpg failed to sign`, retry. Never `--no-gpg-sign`.
One commit for the amendment is enough. Subject: the tasks were wrong about
the wire once 013 is the library, not a list of files.
