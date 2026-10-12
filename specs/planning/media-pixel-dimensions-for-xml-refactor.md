<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
-->

# Media pixel dimensions stored in the project: what changes, and what it means for `feat/xml-refactor`

**For:** the team working on `feat/xml-refactor` in `cuems-utils`, `cuems-editor`, `cuems-engine` and `cuems-frontend`.
**Date:** 2026-10-02
**Status:** designed and reviewed, **not implemented yet**. Nothing is on any branch.
**Full plan:** `cuems-RELATIONS/Plans/2026-10-01-engine-late-go-media-probe.md`
**ClickUp:** 869fat84r

## Why

When a cue is selected and GO follows straight away (power-bridge `/gocue`, Companion), the GO can start up to 400 ms late. The node engine runs `ffprobe` on each video file to get its width and height. It does this on the first arm of that file since the engine started, while holding the command lock. In the measured case, 93 % of the delay was those probes.

A file's pixel size never changes. The editor already probes each file at upload for its duration and stores the result in the project. The fix stores the pixel size the same way, so the engine reads it from the project instead of probing.

## The change at a glance

| Repo | Change | Base branch |
|---|---|---|
| `cuems-utils` | Three optional elements in `MediaType`, `Media` accessors, and a writer that keeps schema order. Released as rc15 | `main` |
| `cuems-editor` | Probe at upload; DB columns and migration; fill the values at save; backfill and strip tool; dependency floor | `rc1` |
| `cuems-engine` | Read the stored values and probe only as a fallback | PR #22 (`fix/node-prearm-broken-chain`, against `rc_1`) |
| `cuems-frontend` | None | — |

---

## 1. `cuems-utils`

### Schema (`script.xsd`, `MediaType`)

Three optional elements, appended **after `regions`**:

```xml
<xs:complexType name="MediaType">
  <xs:sequence minOccurs="0" maxOccurs="1">
    <xs:element name="file_name" type="xs:string" />
    <xs:element name="id" type="cms:TargetType" />
    <xs:element name="duration" type="cms:TimecodeType" />
    <xs:element name="regions" type="cms:RegionsType" />
    <!-- Original size of the media file in pixels (first video stream),
         as ffprobe reports it. Not the layer's size on screen. -->
    <xs:element name="pixel_width"  type="xs:positiveInteger" minOccurs="0" />
    <xs:element name="pixel_height" type="xs:positiveInteger" minOccurs="0" />
    <!-- File size in bytes when the dimensions were measured. The engine
         compares it with its own copy of the file to detect a file that was
         replaced under the same name. -->
    <xs:element name="file_size" type="xs:positiveInteger" minOccurs="0" />
  </xs:sequence>
</xs:complexType>
```

- **The elements are optional.** Every existing project stays valid.
- **Only VideoCues carry them.** An AudioCue never does, even when it plays a video file.
- **They come as a set.** A file with only some of them is still valid; the engine then probes.
- **The names are deliberate.** `pixel_width` and `pixel_height` are the media's original size. `width` and `height` already exist in `CanvasRegionType` as unit floats. A layer size scaled by the user may be added later under its own names.
- **An absent element means "unknown".** Never write an empty one: `<pixel_width/>` fails `xs:positiveInteger`.

### Object model (`Media`)

- `get_`/`set_pixel_width`, `pixel_height` and `file_size`, plus the three properties.
- The getter returns `None` when the key is absent.
- The setter accepts a positive `int` or a string of digits, and stores an `int`. `None` **removes the key**. Anything else raises `ValueError`.

### Writer

`Media` is written **in schema order**, whatever the dict order, with **no element for a `None` value**.

On `main` today, `MediaXmlBuilder` writes keys in dict order and writes an empty element for `None`. Both would produce invalid files once these elements exist.

### Release

rc15, cut from `main`. It also releases `9c17418` (the `ease_in`/`ease_out` curve names).

---

## 2. `cuems-editor`

- **Probe at upload.** `CuemsDBMedia.probe_dimensions()` sits next to `probe_duration()`. It uses the same ffprobe query as the engine, with a 5 s timeout. It never raises: on failure it logs a WARNING and stores nothing. The upload also records the file size from `os.stat`.
- **DB columns.** The `Media` model gets `pixel_width`, `pixel_height` and `file_size` as `IntegerField(null=True)`.
- **Migration.** `create_tables(safe=True)` never adds columns to an existing table, and the editor has no migration mechanism yet.
  - A new shared function adds the missing columns with `ALTER TABLE`.
  - It is called from both places that open the DB: `CuemsProjectManager` and the repair tool.
  - If it fails, the editor stops with a clear error.
  - An older editor still reads the migrated DB, because peewee selects named columns.
- **Fill at save, on the server.** The walk that today fixes durations (`fix_media_durations_in_contents`) becomes a media-metadata walk:
  - First it **strips** `None`, `0` or non-numeric values from every `Media`, so a client value can never fail the XSD.
  - Then it writes the DB values into each **VideoCue**. If the DB row has none, the save path probes the file once and stores the result.
  - It never writes into an AudioCue or an orphan reference.
  - Errors are handled per cue, so one bad cue does not stop the fill for the cues after it.
  - Each caller passes its own resolver, so a dry-run of the repair tool never probes or writes.
- **Every writing path.** `update()` already runs the fill. `new()` has no fill today, so it gets one; `duplicate()` gets one too.
- **Repair tool** (`repair_durations.py`, `cuems-editor-repair-durations`):
  - Pass A re-probes every video row and reports differences.
  - Pass B writes the values into each project's `script.xml`. A change of dimensions counts as a change, so projects whose durations are already correct are not skipped.
  - New `--strip-dimensions` removes the elements again, for a box that has to go back to an older utils.
- **Dependency floor.** `debian/control` moves to `cuems-utils (>= 0.1.0rc15)`, together with the pyproject floor. The deb strips the venv, so only the package dependency is enforced. Without it, a new editor on rc14 utils would fail every save of a project that has a video cue.

## 3. `cuems-engine`

- New `PlayerHandler.cue_media_dimensions(cue)`, used at the two places that call `media_dimensions()` today (`arm_cue.py`, `run_cue.py`):

  | Stored in the project | Result |
  |---|---|
  | `pixel_width` and `pixel_height`, and `file_size` equal to the node's own copy (`os.stat`) | the stored values; **no subprocess** |
  | `file_size` different from the node's copy | probe, plus a WARNING naming both sizes |
  | dimensions missing or invalid | probe as today, plus one WARNING per file per engine process |

- It reads with `cue.media.get("pixel_width")` and so on, not with the new properties. That way it runs on any utils that can load the file.
- The engine's utils floor does not change.
- The change goes into PR #22 on `rc_1`, next to the pre-arm fix (869f9wqpn), as separate commits.

## 4. `cuems-frontend`

No change. The frontend rebuilds `Media` as `{file_name, id, duration, regions}` on save, and ignores unknown keys on load. The editor adds the values after the frontend has built the dict.

---

## 5. Compatibility with released lines

- **An old utils rejects a project that carries the new elements**, because it validates strictly against an XSD that lacks them. This is accepted, because release 1 has not shipped.
- **Old lines get an XSD-only patch.** On `main` and on the old tags, the parser assigns `Media` keys raw (`GenericParser`, `dict.__setitem__`) and never calls setters. A patched old utils therefore loads the values as plain ints, and old code never reads them.
- **Each patch adds only, and never tightens:**
  - **rc14:** rc15's file. Compared with rc14, it only adds these elements and the two curve names.
  - **`pre_release_1` (`2321a1f`):** that commit's own file plus the additive changes. It must not take rc15's `duration` type or its stricter timecode pattern.
- **Deployment order on a cluster:** every box gets rc15 or the patched XSD **before** the controller's editor is upgraded.
- **An old editor that re-saves a project drops the values.** Nothing breaks: the engine probes and warns.

---

## 6. What this means for each `feat/xml-refactor` branch

I read the four branches on 2026-10-02. How to fold this in is your call; these are the places it touches.

### `cuems-utils` (`6213b16`, rc16, does not contain `main`'s `9c17418`)

1. **Declare the fields, or they are dropped on write.** `Media.DECLARED_DEFAULTS` lists four fields, and the mapper filters a model with declared fields to exactly those, dropping and logging every other key (FR-015a). The three new fields are optional, so they need a default that emits nothing when absent, unlike `Unset`, which marks required fields.
2. **`Media` needs the setters on your branch too.** Decode builds it through `_instantiate(model, decoded)`. If that goes through `CuemsDict.setter`, a key with no `set_<key>` is skipped, and decoding loses the value. This differs from `main`, where unknown `Media` keys survive.
3. **Files written by rc15 carry no `doc_version`**, so your reader treats them as script version 1. `_script_1_to_2` edits `<duration>` in place and leaves other `Media` children alone, so the new elements survive the conversion. They then have to validate against your version 2 `script.xsd`.
4. **A version step is your decision.** An additive optional element needs no conversion. Bumping `script` to 3 would give an older refactored library a clear `DocumentTooNewError` instead of "unexpected element".
5. **Merge `9c17418` from `main`.** It is the `ease_in`/`ease_out` commit, and rc15 releases it.
6. **Ordering is already solved on your side.** Your spec-driven ordering (known fields by schema position, unknown keys last) gives the right order once the fields are declared.

### `cuems-editor` (`89af5a9`, `rc1` + 9 commits)

Your branch has not changed the files this touches (`CuemsDBProject.py`, `CuemsDBModel.py`, `CuemsDBMedia.py`, `repair_durations.py`, `CuemsProjectManager.py`), so the changes in §2 should merge cleanly.

Two things to watch:
- Your `pyproject.toml` floor is still `cuemsutils>=0.1.0rc10`. It has to reach at least rc15, or rc16 if you release together.
- Your branch has no `debian/` directory, so the package floor in §2 lands on `debian/bookworm`. Please keep it when you package.

### `cuems-engine` (`1662a99`, based on `main`, 14 commits behind `rc_1`, pins `cuemsutils>=0.1.0rc16,<0.1.1`)

- The call sites are the same (`arm_cue.py:147`, `run_cue.py:462` on your branch), so the change ports directly.
- It lands on `rc_1` through PR #22, which your branch does not contain yet. You will get it when you merge `rc_1`, together with the pre-arm work.
- Keep `cue.media` dict-like with `.get()`, or tell us before that changes.

### `cuems-frontend` (`3183845`, 23 commits behind `main`)

- Nothing to change for this.
- Separately: your branch still sends `duration: '00:00:00.000'` in `Media`, which predates `main`'s media-duration fix. The editor's save-time fill corrects it, as it will correct the dimensions, but merging `main` would remove the difference.

---

## 7. Tests we will add

These are worth mirroring on your branches.

**utils:**
- An old project loads and writes back unchanged.
- A project with the elements loads them as `int` and writes back equivalent after re-parse.
- A `Media` with keys in any order, or with `None`, is written in schema order with no empty element.
- `0`, negative and non-numeric values are rejected by both the XSD and the setters.
- Old-line tests: rc14 and `2321a1f`, each with its patched XSD, load a project carrying the elements and save it, and real venue projects still validate against the patched XSD.

**editor:**
- Migration on an old-schema DB; the second start does nothing; a failure stops the editor.
- Upload stores the values for video and none for audio.
- The fill, rule by rule, on `update()`, `new()` and `duplicate()`.
- The repair tool: a dry-run writes nothing; `--strip-dimensions` works.
- A failed probe never fails an upload or a save.

**engine:**
- With stored values, no subprocess runs on arm or on run.
- Missing values or a size mismatch fall back to the probe with exactly one WARNING per file.
- The scale computed from stored and from probed values is identical.

## 8. Questions for you

1. Do you want the three fields declared directly on your branches, or merged in from `main`/`rc1`/`rc_1` after rc15?
2. Is this a `script` version step on your side, or not (§6, utils point 4)?
