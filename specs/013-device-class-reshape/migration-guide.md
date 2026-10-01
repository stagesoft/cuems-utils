<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Migration guide — feature 013, device-class reshape

**Feature**: `013-device-class-reshape` | **Tasks**: T051, T052 | **Written**: 2026-10-01
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Data model**: [data-model.md](data-model.md)

This document is for the maintainer of **one** consumer repository. Find your repository
below, read your own files and your own lines, and you have the whole change. Nobody should
have to infer the contract from a schema diff.

Every line number here was **checked against the sibling tree at the commit named in that
section's heading**, not transcribed from the spec. Line numbers drift; the commit pin is
what makes the check repeatable, and `tests/contract/test_migration_guide_names_sites.py`
(T053) fails if a site named in the spec's M1–M13 goes missing from this file.

---

## 0. The whole change, in four sentences

An element named after a device class becomes **one element carrying a `class`
attribute**. `<audio>` / `<video>` / `<dmx>` under a mappings node become
`<device class="…">` inside `<devices>`; the six root `default_*` elements become
`<default class="…" direction="…">` inside `<defaults>`; `<videoplayer>` /
`<audioplayer>` / `<dmxplayer>` become `<player class="…">` inside `<players>`; and
`<AudioCue>` / `<VideoCue>` / `<DmxCue>` and the three `*CueOutput` elements become
`<Cue class="…">` and `<CueOutput class="…">`.

**The Python classes do not change.** `AudioCue` is still an `AudioCue`, `VideoCueOutput`
is still a `VideoCueOutput`, with the same fields, the same equality and the same hash, so
every `isinstance` and `singledispatch` registration keeps working untouched.

**No document version moves.** `doc_version` is untouched (FR-020), so an older
`cuems-utils` meeting a new-shape document gets a raw schema error, not
`DocumentTooNewError` — see §6.

**One tool migrates an installation**: `cuems-reshape-devices`, §1.

---

## 1. Migrating documents on disk: `cuems-reshape-devices`

```bash
cuems-reshape-devices --check              # report only, writes nothing
cuems-reshape-devices --dry-run            # name the backup each document would get
cuems-reshape-devices                      # reshape, backing up first
cuems-reshape-devices PATH [PATH ...]      # explicit paths instead of discovery
```

With no `PATH`, it discovers `CUEMS_CONF_PATH` (default `/etc/cuems`) and the project
library through `settings.xml`'s `library_path`. **Scripts are found by root element, not
by filename** — a show saved as anything other than `script.xml` is still found.

Exit codes: `0` everything is current, `1` `--check` found an old-shape document or a
document was skipped, `2` a usage error or an installation that will not resolve.

Each document is backed up to `<name>.<YYYYMMDDTHHMMSS>.bak` **before** being rewritten, a
backup failure leaves that one document unrewritten and the run continues, and a document
that would not validate after reshaping is **not written**. A second run reports nothing to
do and changes no bytes.

### 1a. Order matters: reshape, then convert

If any document on the installation predates feature 008's schema versions — a script with
`<duration>00:00:01.000</duration>` as bare text rather than a `<CTimecode>` wrapper — run
**`cuems-reshape-devices` first and `cuems-convert-documents` second**.

The reason, because getting it backwards is a dead end rather than a slow path. The two
tools each validate before writing, and until this feature they would have deadlocked:

* `cuems-convert-documents` first — it converts, then validates (its SC-017 check), and the
  cues are still old-shape, so it raises.
* `cuems-reshape-devices` first, validating the reshaped tree as it stands — the devices
  are right but `duration` is still version 1, so the document "would not validate" and the
  tool declines to write it.

`cuems-reshape-devices` therefore validates the document **as the load path will see it**:
it applies the registered version conversions to a throwaway copy, in memory, and validates
that. Nothing is written from the copy, `doc_version` is not moved, and the version gate
(`DocumentTooNewError`) is still never this tool's to apply. So the reshape succeeds on a
version-old document, leaves it version-old, and `cuems-convert-documents` then works
because the cues are new-shape by the time it validates.

---

## 2. `cuems-engine` — every site keeps resolving correctly

Verified at `cuems-engine` `feat/xml-refactor` **`1662a99`** (clean working tree).

**No source file in this repository needs to change** — measured, not asserted: all three
runs are in [sibling-repository-updates.md](sibling-repository-updates.md). The suite goes
from 923 passed at the branch point to 96 failures on this branch and back to one with a
single `cuems-reshape-devices` invocation over `dev/test_xml_files/`, and every one of those
96 is an old-shape **fixture**, never a call site. The fifteen sites below are listed in
full because "nothing to do here" is a result worth being able to check.

Two things this repository does have to do, neither of them a code change: run the tool over
`dev/test_xml_files/` (five documents move), and update `tests/test_port_handler.py`, which
names the old player elements. A third, separate from this feature: repair
`dev/test_xml_files/projects/complex_test/project_mappings.xml`, which has been invalid
against `project_mappings.xsd` for several releases — see §7.

| Site | Code | Classification |
|---|---|---|
| `src/cuemsengine/NodeEngine.py:456` | `self.cm.node_hw_outputs.get("audio_outputs")` | keeps resolving correctly |
| `src/cuemsengine/NodeEngine.py:457` | `self.cm.node_hw_outputs["audio_outputs"]` | keeps resolving correctly |
| `src/cuemsengine/NodeEngine.py:566` | `if not self.cm.node_hw_outputs["video_outputs"]:` | keeps resolving correctly — **unguarded subscript** |
| `src/cuemsengine/NodeEngine.py:508` | `self.cm.node_mappings.get("audio", [])` | keeps resolving correctly |
| `src/cuemsengine/NodeEngine.py:598` | `self.cm.node_mappings.get("video", [])` | keeps resolving correctly |
| `src/cuemsengine/NodeEngine.py:472`, `src/cuemsengine/NodeEngine.py:473` | `node_conf["audiomixer"]["path"]`, `["args"]` | keeps resolving correctly — `audiomixer` was not reshaped at all |
| `src/cuemsengine/NodeEngine.py:530`, `src/cuemsengine/NodeEngine.py:531`, `src/cuemsengine/NodeEngine.py:534` | `node_conf["audioplayer"][…]` | keeps resolving correctly |
| `src/cuemsengine/NodeEngine.py:565`, `src/cuemsengine/NodeEngine.py:571` | `node_conf["videoplayer"]`, `.get("videoplayer", {})` | keeps resolving correctly |
| `src/cuemsengine/NodeEngine.py:645`, `src/cuemsengine/NodeEngine.py:646`, `src/cuemsengine/NodeEngine.py:651` | `node_conf["dmxplayer"][…]` | keeps resolving correctly |

### Why, in each case

**`node_hw_outputs`** is a `HardwareOutputs` dict built by walking the document's devices,
with a `__missing__` that answers `[]` for a well-formed `{class}_{inputs|outputs}` key.
`NodeEngine.py:566`'s unguarded subscript is the reason `__missing__` exists rather than a `.get`
default: a node with no video device must get `[]` there, not a `KeyError`. A **typo**
still raises `KeyError`, deliberately — and note that `dict.get` does *not* consult
`__missing__`, which is what keeps `NodeEngine.py:456` truthful: `.get("audio_outputs")` returns `None`
on a node with no audio device, exactly as it did before.

**`node_mappings["audio"]`** answers from `devices`, derived per class from the document
(FR-012a). This one is worth dwelling on: `NodeEngine.py:508` and `NodeEngine.py:598` are `.get(…, [])`, so had the
accessor simply stopped answering, the engine would have configured **no ports at all**,
on a startup path, **with no error**. That is the failure class this derivation exists to
prevent.

**`node_conf["videoplayer"]`** and its two siblings project out of `players` by class. The
*nested* reads the engine makes — `["path"]`, `["args"]`, `["osc_port"]`,
`["output_latency_ms"]` — are inside the player object and so are unchanged.
`node_conf["audiomixer"]` is the element itself, not a projection: `audiomixer` has no
device class and was deliberately left where it is (FR-040a).

**Cue classes** are unchanged, so the engine's ~30 `isinstance` / `singledispatch` sites
are untouched. None of them parses an element name.

### What *does* need checking: fixtures and the test estate

`dev/test_xml_files/settings.xml` is in the old axis-C shape, and
`tests/test_port_handler.py` mentions the old player element names. Neither is a call site;
both are **data**, which a call-site census cannot see — the lesson feature 012 recorded
when its own census predicted two risks that produced zero failures while the real breakage
was in test fixtures. Run the suite rather than reading the diff (§7).

---

## 3. `cuems-common` — three readers, three classifications

Verified at `cuems-common` `feat/xml-refactor` **`6ab4655`** (clean working tree).

These are `/usr/bin`-class scripts that **cannot import `cuemsutils`** (the shared venv is
one-way), so they read XML by XPath and none of them is shielded by a Python accessor. They
port in this repository, by hand.

| Site | Reads today | New path | Classification |
|---|---|---|---|
| `usr/lib/cuems/bin/cuems-extract-video-latency:39` | `.//videoplayer/output_latency_ms` | `.//players/player[@class='video']/output_latency_ms` | **keeps resolving and becomes wrong** |
| `usr/lib/cuems/bin/cuems-generate-display-conf:66`, `usr/lib/cuems/bin/cuems-generate-display-conf:67`, `usr/lib/cuems/bin/cuems-generate-display-conf:76` | `.//video/outputs/output`, then `mappings/mapped_to` and `canvas_region` on each | `.//devices/device[@class='video']/outputs/output` | **keeps resolving and becomes wrong** |
| `usr/lib/cuems/bin/cuems-display-setup:527` | `.//video/outputs/output/mappings/mapped_to` | `.//devices/device[@class='video']/outputs/output/mappings/mapped_to` | becomes wrong |
| `usr/lib/cuems/bin/cuems-display-setup:569`, `usr/lib/cuems/bin/cuems-display-setup:571` | `target_node.find('./video/outputs')`, then `sys.exit` when absent | `./devices/device[@class='video']/outputs` | **raises** — `sys.exit('ERROR: <video><outputs> missing under local node')` |

### State this plainly to whoever operates a node

**A node whose `cuems-common` is not re-packaged loses its configured video latency with no
error at all.** `ElementTree.find` returns `None` for a path that no longer matches,
`cuems-extract-video-latency` returns `None`, the `OUTPUT_LATENCY_FLAG` it writes comes out
empty, and the script exits `0`. The latency the operator configured is silently discarded.
`cuems-generate-display-conf` fails the same way, producing an empty or wrong
`display.conf`. `cuems-display-setup` is the one that fails loudly, which is the better
outcome.

So the display pipeline — the thing that drives the monitors — is in **axis A's** blast
radius, not only axis C's.

**This port is a dependency of the coordinated `xml-refactor-merge-candidate` tag, not of
the `cuems-utils` branch.** `cuems-utils` can land on its own branch; the tag set cannot be
cut until this is done. A candidate tag set is only as current as its least current member,
and no packaging relation expresses that.

---

## 4. `cuems-editor` — a pass-through, plus keyed access on its own paths

Verified at `cuems-editor` `feat/xml-refactor` **`106015c`** (clean working tree).
Research R8 measured `36260e2`; the branch has moved since, and the line numbers below are
this commit's.

| Site | Code | Classification |
|---|---|---|
| `src/cuemseditor/CuemsWsServer.py:439` | `# Keep outputs (audio, video, dmx) from existing node` | **comment only** — the node merge above it is a genuine pass-through over a dict it never keys into |
| `src/cuemseditor/CuemsDBProject.py:385` | `CUE_TYPES = ['AudioCue', 'VideoCue', 'DmxCue', 'ActionCue', 'FadeCue', 'CueList']` | keeps resolving and **becomes wrong** for the three hardware names |
| `src/cuemseditor/CuemsDBProject.py:408`, `src/cuemseditor/CuemsDBProject.py:422` | `_collect_cue_ids` / `_nullify_dangling_refs` iterate `CUE_TYPES` | same — dangling-reference cleanup stops seeing hardware cues |
| `src/cuemseditor/CuemsDBProject.py:78`–`src/cuemseditor/CuemsDBProject.py:82` | `if 'AudioCue' in item:` / `elif 'VideoCue' in item:` in `_walk_media_durations` | same |
| `src/cuemseditor/CuemsDBProject.py:883`, `src/cuemseditor/CuemsDBProject.py:895` | `XmlReaderWriter` write / read of a project script | **raises** on an un-migrated document |
| `src/cuemseditor/repair_durations.py:204`, `src/cuemseditor/repair_durations.py:231` | `XmlReaderWriter(...).read()` then `.write_from_object(obj)` | **raises** on an un-migrated document |

### The fix for the keyed sites

`CUE_TYPES` and the `'AudioCue' in item` tests both become one key plus a class read:

```python
# before
if 'AudioCue' in item:
    cue_data = item['AudioCue']

# after
if 'Cue' in item:
    cue_data = item['Cue']          # cue_data['class'] is 'audio' | 'video' | 'dmx' | …
```

`CUE_TYPES` collapses to `['Cue', 'ActionCue', 'FadeCue', 'CueList']`. Note what this buys:
a **new** hardware class is then covered without touching this list, which is the point of
the whole feature.

### FR-033, stated because it is easy to get wrong

`CuemsWsServer.py`'s node merge is **not** among flow 02's fourteen deprecated-surface call
sites. It is a separate concern that happens to live in the same file.

### Two edge cases this feature creates

Both follow from there being **no conversion on read** for the device shape — that is
deliberate (FR-020: no version step), and these are its consequences rather than oversights.

1. **A half-migrated library produces two shapes in one merge payload.** If some project
   scripts have been reshaped and others have not, a payload assembled across them carries
   both `Cue` and `AudioCue` keys. Run `cuems-reshape-devices` over the whole library in one
   pass; that is why it discovers the library rather than taking one path.
2. **A load-and-save tool now fails on an un-migrated document instead of silently
   upgrading it.** `repair_durations.py` is the case: it used to read, fix and write, and an
   un-migrated document will now raise at the read. Failing is the safer direction — the
   alternative is a tool that rewrites a document it did not fully understand.

### A pre-existing failure you will meet first

The editor's suite has **one** fault with nine symptoms:
`ModuleNotFoundError: No module named 'cuemsutils.create_script'`, reached through
`CuemsWsServer.py:27`, which feature 008 retired. It is not this feature's, and it is not
three separate problems. Expect it, and do not read it as a device-class regression.

---

## 5. `cuems-frontend` — the wire contract, written out

Verified at `cuems-frontend` `feat/xml-refactor` **`3183845`** (clean working tree).

### The contract, in one line (FR-032)

```json
{"AudioCue": {...}}  →  {"Cue": {..., "class": "audio"}}
```

and the same for cue outputs:

```json
{"AudioCueOutput": {...}}  →  {"CueOutput": {..., "class": "audio"}}
```

`class` is `"audio"`, `"video"`, `"dmx"`, or **any other string** — the vocabulary is open,
and a class the UI has never seen must not be an error. Nothing else about the projection
changed: same field names, same order within a cue, same scalar forms.

`ActionCue`, `FadeCue` and `CueList` keep their own keys and carry **no** `class`. They are
cue *kinds*, not hardware classes, and no new hardware class adds one.

### Axis D sites

| Site | Code |
|---|---|
| `project-edit/sequence/sequence.component.ts:232`, `sequence.component.ts:233` | `getCueTypeKey(cue.originalData)` then `cue.originalData[cueTypeKey]` |
| `project-edit/sequence/sequence.component.ts:918`–`sequence.component.ts:940` | the `cueTypeKey = 'AudioCue' / 'VideoCue' / 'ActionCue' / 'DmxCue' / 'FadeCue'` ladder |
| `project-edit/sequence/sequence.component.ts:1088` | `const result = { [cueTypeKey]: newCue };` — the **save wrapper** |
| `project-edit/sequence/sequence.component.ts:343`, `sequence.component.ts:344`, `sequence.component.ts:347`, `sequence.component.ts:348` | `cueData.AudioCueOutput?.output_name`, `output.AudioCueOutput?.output_name` |
| `project-edit/sequence/sequence.component.ts:890` | `if (cueKey === 'AudioCue' && cue.AudioCueOutput)` |
| `project-show/sequence/sequence.component.ts:117`–`sequence.component.ts:132` | `cueItem.AudioCue` / `.VideoCue` / `.DmxCue` for id and name |
| `shared/audio-mixer/audio-mixer.component.ts:61`, `audio-mixer.component.ts:63` | `output.AudioCueOutput.output_vol` read and write |

The ladder at `sequence.component.ts:918`–`940` and the wrapper at `sequence.component.ts:1088` are the two that matter most: today
the *key* carries the type, and after this feature the key is constant and the **body**
carries it. `getCueTypeKey` becomes "`Cue` for the three hardware classes, its own name for
`ActionCue` / `FadeCue` / `CueList`", and the class value moves into `newCue`.

### Axis A sites

| Site | Reads |
|---|---|
| `src/app/services/projects/projects.service.ts:39`, `src/app/services/projects/projects.service.ts:41` | the `default_audio_output` / `default_video_output` interface fields |
| `project-edit/sequence/sequence.component.ts:379`, `sequence.component.ts:449` | `mappingsResponse?.value?.default_audio_output` / `default_video_output` |
| `project-edit/sequence/sequence.component.ts:682`, `sequence.component.ts:683` | the same two keys again |

Research R9 measured about 45 line-ranges across eight files in total, including
`settings.component.ts` / `.html` and the `project-show` mixers; the table above is the
subset whose line numbers were re-verified at `3183845`. The structural mappings interface
in `projects.service.ts` is the single most load-bearing one: it is the type every other
site reads through.

### Unaffected, and worth saying so because they look affected

The TypeScript unions, the icon service, OSC paths, i18n keys and route names are
**internal UI vocabulary**, not wire keys. They can keep using the words "audio", "video"
and "dmx" freely.

### There are no characterization tests to protect you

Five `.spec.ts` files exist and **none** covers `projects.service.ts`, either
`sequence.component.ts`, or `settings.component.ts`. Flow 05 writes those tests once,
against this section — which is why this section states the contract rather than pointing
at the schema.

---

## 6. Rollback (FR-028)

### What rolling back means here

The device shape and `doc_version` are **independent**. This feature takes no version step
(`CURRENT_VERSION` is unchanged for all six schemas), so a new-shape document carries no
marker saying so. The consequences:

* **An older `cuems-utils` meeting a new-shape document gets a raw schema error**, not
  `DocumentTooNewError`. There is no version to be "too new". Expect
  `XMLSchemaChildrenValidationError: Unexpected child with tag 'devices'` or
  `… tag 'Cue'`, which names the element but does not name the cause. That asymmetry is
  the price of not taking a version step; the new library's own diagnosis is the one that
  names `cuems-reshape-devices`.
* **Conversely, the reshape does not make a document un-loadable by an older library for
  any other reason.** Nothing else about it changed.

### Rolling back: restore the backup

`cuems-reshape-devices` writes `<name>.<YYYYMMDDTHHMMSS>.bak` beside each document before
rewriting it. To roll back, stop everything that writes, restore each `.bak` over its
document, and reinstall the older `cuems-utils`.

### The point after which the backup stops being a usable rollback

A backup is a usable rollback **only until something writes the document again**. Three
distinct moments end that window, in the order you are likely to hit them:

1. **`cuems-nodeconf` rewrites `network_map.xml` every 30 s.** `network_map` is not
   reshaped by this feature, so this one does not invalidate a device-shape rollback — but
   it is the same mechanism feature 012's guide §9b describes, and if you are rolling back
   *both* features at once it is the binding constraint.
2. **The editor saves a project.** From that moment the project's `script.xml` and
   `mappings.xml` are new-shape *content written by the new library*, not merely a reshaped
   copy of the old document. The `.bak` is then stale: restoring it loses whatever the
   operator did in between. This is the one that usually closes the window first, because
   it needs nothing more than someone opening a show and pressing save.
3. **`cuems-init-node` or `cuems-config-node` rewrites a configuration document.** Same
   reasoning, for `settings.xml` and `default_mappings.xml`.

So: **roll back before the stack is restarted, or accept losing whatever was authored
after it.** If the stack has been running and projects have been saved, the forward path
(fix the consumer, keep the new shape) is the cheaper one — the reshape is lossless in the
forward direction and the backups do not need to be used at all.

### One thing a rollback cannot undo

Nothing. The reshape adds no state outside the documents themselves: no registry entry, no
version marker, no write record. That is the one genuinely reassuring property here, and it
is a consequence of FR-020 rather than of care.

---

## 7. How to verify your own repository

Run your suite against this branch **and** against the branch point, and compare. Do not
infer the result from a call-site census — feature 012 measured that instrument to be
weaker: both risks its census predicted produced zero failures, while the real breakage was
in test *data* a census cannot see. This feature has already found the same pattern:

| Repository | Old-shape XML in the tree, measured 2026-10-01 |
|---|---|
| `cuems-nodeconf` | `tests/fixtures/etc_cuems/settings.xml`, `tests/fixtures/etc_cuems/settings_sentinel.xml` |
| `cuems-power-bridge` | nine `tests/fixtures/network_map/map-*/settings.xml` |
| `cuems-engine` | `dev/test_xml_files/settings.xml`, and the old player names in `tests/test_port_handler.py` |
| `cuems-common` | `docs/latency-tuning.md` (documentation, not a fixture) |
| `cuems-editor` | none |

None of those is a call site. All of them are axis C fixtures, and every one of them will
fail against the reshaped `settings.xsd` until it is updated. The fix in each case is the
same four-line edit the tool performs: wrap the three players in `<players>` and give each a
`class`, leaving `<audiomixer>` where it is. `cuems-reshape-devices` will do it for you —
point it at the fixture directory.

### The engine's three runs, as the worked example

[sibling-repository-updates.md](sibling-repository-updates.md) records them. The short
version, because it is the shape every repository in the table above should expect:

| Arm | Result |
|-----|--------|
| branch point, fixtures as committed | 923 passed |
| this branch, fixtures as committed | 70 failed, 827 passed, 26 errors — **one cause** |
| this branch, after one tool invocation | 1 failed, 922 passed |

And the residual one is worth reading before you meet your own: it is **this guide's
half-migrated-library edge case**, reached because the tool *refused* one document —
`dev/test_xml_files/projects/complex_test/project_mappings.xml`, which has been invalid
against `project_mappings.xsd` for several releases (an `<output>` with no `<id>`, and a
missing `<new_nodes>`). The branch-point library rejects it too, verified. So the project's
settings migrated and its mappings could not, and the project stopped loading.

**The lesson to carry into your own repository**: the tool will not rewrite a document that
would not validate, by design — so a fixture that has quietly been invalid for releases
surfaces now, as a refusal, in the middle of a migration. Fix the document, then re-run the
tool. Do not read the refusal as the reshape failing.

---

## 8. What this feature does *not* do

* It does **not** change any Python class name, field, equality or hash.
* It does **not** move any `doc_version`, add a conversion, or touch
  `DELIBERATE_IDENTITY_STEPS`.
* It does **not** touch feature 012's identity surface — `SENTINEL`, `coerce_identity`,
  `--remint` — and `cuems-reshape-devices` never calls the version gate.
* It does **not** reshape `network_map.xml` or `project_settings.xml`. The tool reports
  those "not applicable".
* It does **not** fix the frozen legacy `cuemsutils.xml.XmlBuilder`. That module has no
  live caller, is removed in `v0.1.1`, and still emits per-class element names — so it now
  writes documents the current schema rejects. If you are calling it, stop; use
  `CuemsScript.save`.
* It ships nothing on its own (D27). Nothing reaches a node until the coordinated
  `xml-refactor-merge-candidate` tag.
