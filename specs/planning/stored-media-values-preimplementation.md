cuems · ClickUp 869fat84r · for feat/xml-refactor

# Media pixel size, file size and MD5 stored in the project: what changes, and what it means for `feat/xml-refactor`

Contents

- [Why](#why)
- [The change at a glance](#the-change-at-a-glance)
- [1. cuems-utils](#1-cuems-utils)
- [2. cuems-editor](#2-cuems-editor)
- [2b. cuems-editor and cuems-frontend: a media file that changed after its values were stored (D20, 2026-10-05)](#2b-cuems-editor-and-cuems-frontend-a-media-file-that-changed-after-its-values-were-stored-d20-2026-10-05)
- [3. cuems-engine](#3-cuems-engine)
- [3b. cuems-engine: each node reports its own differing files (D20)](#3b-cuems-engine-each-node-reports-its-own-differing-files-d20)
- [4. cuems-frontend](#4-cuems-frontend)
- [5. Compatibility with released lines](#5-compatibility-with-released-lines)
- [6. Packaging facts found on the way](#6-packaging-facts-found-on-the-way)
- [7. What this means for each feat/xml-refactor branch](#7-what-this-means-for-each-featxml-refactor-branch)
- [8. Tests on our branches](#8-tests-on-our-branches)
- [9. Questions for you](#9-questions-for-you)

**For:** the team working on `feat/xml-refactor` in `cuems-utils`, `cuems-editor`, `cuems-engine` and `cuems-frontend`. **Date:** 2026-10-02 (updated the same evening; §2b and §3b added 2026-10-05 for D20, and rewritten the same day for its revision 2)

**Status:** implemented and verified on test2, **not pushed yet**:

- `cuems-utils` `feat/869fat84r-media-dimensions` (rc15, with `file_md5`)
- `cuems-editor` `feat/869fat84r-media-dimensions`, plus `debian/869fat84r-utils-floor`
- `cuems-engine` PR #22
- D20 (a media file that changed after its values were stored, §2b, §3b): editor `dd8897c`, `b29d40e`, `9b6eb13`, then revision 2 `199606e`, `0b291d1`; engine `15fa371`, `52c7d06` on PR #22's branch; frontend `feat/869fat84r-media-check` (`5899563`, `6854cbc`, `a3b07fd`, `a1c34bf`, `cba3c0b`)

**Full plan:** `cuems-RELATIONS/Plans/2026-10-01-engine-late-go-media-probe.md` **ClickUp:** 869fat84r. Related, separate: 869fb97my (fps, codecs and audio channels in the media DB, not in the project).

## Why

When a cue is selected and GO follows straight away (power-bridge `/gocue`, Companion), the GO can start late. The node engine runs `ffprobe` on each video file to get its width and height, on the first arm of that file since the engine started, while holding the command lock.

Measured on test2 with a copy of the Medina sala1 show, selecting and GOing right after a fresh load:

| Engine | ffprobes on the command thread | Node lag | Cues late |
| --- | --- | --- | --- |
| without the fix | 4 | **760–800 ms** | 9, up to 840 ms |
| with the fix | 0 | **40 ms** | 0 |

A file's pixel size never changes. The editor already probes each file at upload for its duration and stores it in the project; the pixel size is now stored the same way. With it come the file's size and its MD5, so a stored value can be checked against the file it was made from.

## The change at a glance

| Repo | Change | Base branch |
| --- | --- | --- |
| `cuems-utils` | Four optional elements in `MediaType`, `Media` accessors, a writer that keeps schema order. Released as rc15 | `main` |
| `cuems-editor` | Store the values at upload; DB columns and migration; fill the values at save; backfill (the strip option was removed later, D23); dependency floor. D20: check media at load and report stale values (§2b) | `rc1` |
| `cuems-engine` | Read the stored pixel size; probe only as a fallback | PR #22 (`fix/node-prearm-broken-chain`, against `rc_1`) |
| `cuems-frontend` | None for the stored values. D20: a warning banner for stale media (§2b) | `main` |

---

## 1. `cuems-utils`

### Schema (`script.xsd`, `MediaType`)

Four optional elements, appended **after `regions`**:

```xml
<xs:complexType name="MediaType">
  <xs:sequence minOccurs="0" maxOccurs="1">
    <xs:element name="file_name" type="xs:string" />
    <xs:element name="id" type="cms:TargetType" />
    <xs:element name="duration" type="cms:TimecodeType" />
    <xs:element name="regions" type="cms:RegionsType" />
    <!-- Original size of the media file in pixels (first video stream),
         as ffprobe reports it. Not the layer's size on screen. VideoCues only. -->
    <xs:element name="pixel_width"  type="xs:positiveInteger" minOccurs="0" />
    <xs:element name="pixel_height" type="xs:positiveInteger" minOccurs="0" />
    <!-- The file's size in bytes. Every media type. -->
    <xs:element name="file_size" type="xs:positiveInteger" minOccurs="0" />
    <!-- The file's MD5, lowercase hex, from the upload. Every media type. -->
    <xs:element name="file_md5" type="cms:Md5Type" minOccurs="0" />
  </xs:sequence>
</xs:complexType>

<xs:simpleType name="Md5Type">
  <xs:restriction base="xs:string">
    <xs:pattern value="[0-9a-f]{32}" />
  </xs:restriction>
</xs:simpleType>
```

- **The elements are optional.** Every existing project stays valid. An absent element means "unknown". Never write an empty one: `<pixel_width/>` fails `xs:positiveInteger`.
- **Who carries what:**

  | Element | VideoCue | AudioCue |
  | --- | --- | --- |
  | `pixel_width`, `pixel_height` | yes | never, even when it plays a video file |
  | `file_size`, `file_md5` | yes | yes |
- **What each one is for:**
  - `pixel_width` / `pixel_height`: the engine scales the layer with them instead of probing the file.
  - `file_size`: the engine compares it with its own copy (a `stat`, microseconds) to notice a file replaced under the same name, and then probes.
  - `file_md5`: identifies the file unambiguously, for integrity checks. The size cannot see a corrupt or partial copy that has the right length; the MD5 can. **The engine never hashes a file when it arms a cue**: that would read the whole file, worse than the probe being removed. Checking a node's copy against the MD5 (in the background, or in the media sync) is a possible follow-up, not part of this change.
- **The names are deliberate.** `pixel_width` and `pixel_height` are the media's original size. `width` and `height` already exist in `CanvasRegionType` as unit floats. A layer size scaled by the user may be added later under its own names.
- **Not in the schema, on purpose:** fps, codecs, audio channels, sample rate. The players read those themselves when they open the file, at no cost. They go into the editor's media DB only, in a separate task (869fb97my).

### Object model (`Media`)

- Properties and `get_`/`set_` methods for `pixel_width`, `pixel_height`, `file_size`, `file_md5`. The getters return `None` when the key is absent.
- Integer fields accept a positive `int` or a string of digits, and store an `int`.
- `file_md5` accepts 32 hex digits in any case, and stores them lowercase.
- `None` **removes the key**. Anything else raises `ValueError`.

### Writer

`Media` is written **in schema order**, whatever the dict order, with **no element for a `None` value**. On `main` today, `MediaXmlBuilder` writes keys in dict order and an empty element for `None`; both would produce invalid files once these elements exist.

### Release

rc15, cut from `main`. It also releases `9c17418` (the `ease_in`/`ease_out` curve names).

---

## 2. `cuems-editor`

- **At upload:**
  - movies get `pixel_width` / `pixel_height` from `CuemsDBMedia.probe_dimensions()`. It sits next to `probe_duration()`, uses the engine's ffprobe query and a 5 s timeout, and never raises;
  - every file gets `file_size` (a `stat`);
  - every file gets `file_md5`: **the MD5 the client already sends, which `CuemsUpload.check_file_integrity` verifies**. It is stored as is, so nothing hashes the file a second time.
- **DB columns.** `Media` gets `pixel_width`, `pixel_height`, `file_size` (integers) and `file_md5` (text), all nullable.
- **Migration.** `create_tables(safe=True)` never adds columns to an existing table, and the editor had no migration mechanism.
  - `ensure_media_columns()` adds the missing columns with `ALTER TABLE`, from both places that open the DB: `CuemsProjectManager` and the repair tool.
  - If it fails, the editor stops with the reason.
  - An older editor still reads the migrated DB.
- **Fill at save, on the server.** The walk that fixes durations (`fix_media_durations_in_contents`) becomes a media-metadata walk:
  - It first **strips** invalid values from every `Media`, and any pixel size from AudioCues, so a client value can never fail the XSD.
  - It then writes the DB values: all four into VideoCues, size and MD5 into AudioCues.
  - A row with no pixel size yet is probed once and stored, and a row with no size gets one. A save **never computes an MD5**: hashing a large file would make the save wait. Missing MD5s come from the repair tool.
  - Orphan references (no DB row) keep their valid values.
  - Errors are handled per cue.
  - It runs on `update()`, `new()` and `duplicate()`.
- **Repair tool** (`cuems-editor-repair-durations`):
  - Pass A re-measures every file: the pixel size of movies, and the size and MD5 of all files. It fills what is missing and reports differences: `DIMS_CHANGED`; `MD5_CHANGED`, marked dirty, meaning the file is not the one the row was made for.
  - `--no-md5` skips the hashing.
  - Pass B writes the values into every project.
  - `--strip-dimensions` removes all four elements from every project, for a box that has to go back to an older utils.
  - A dry-run never writes the DB: on an unmigrated DB it reads a migrated temporary copy.
- **Dependency floor.** `debian/control` moves to `cuems-utils (>= 0.1.0rc15)`, and pyproject with it. The deb strips the venv, so only the package dependency is enforced. Without it, a new editor on rc14 utils would fail every save of a project with a video cue.

## 2b. `cuems-editor` and `cuems-frontend`: a media file that changed after its values were stored (D20, 2026-10-05)

If a library file is replaced by hand on the controller, under the same name, the stored duration and sizes no longer match it.

**Revision 2, after your branch's principle** (a script changes only on an operator's save; Ion agreed): the editor **never rewrites a project on its own**. It corrects what belongs to the library and reports the rest.

- **At `project_ready`** (the UI and the power-bridge boot auto-load), `CuemsMediaRefresh.refresh_media_before_load()`:
  1. reads the project file without the schema (about 1 ms) and compares each file with its `Media` row: the size, and the `.idx` header of a video the sync carries (`.mp4 .mov .avi .mkv .mpg`);
  2. only when there are files to measure, asks the engine for `project_status`, and does nothing while a show runs;
  3. re-probes a changed file in one ffprobe (`CuemsDBMedia.probe_media()`), within 20 s, and corrects the row (a changed file's MD5 is cleared);
  4. rebuilds a changed video's `.idx` (`cuems-videoindexer`, an asyncio subprocess);
  5. **reports** the values the project still holds that no longer match.

  It never raises, and the load always goes on with the stored values. - **The report** is a new frame, `media_check_report` (shape in `tests/ws-command-responses.txt`): - the stale values are grouped by file (at most 20 files, plus a count); - the changed files not yet measured are listed as `unverified`; - `complete=false` with a reason when part of the check did not run.

  It is sent: - **after** the `project_ready` reply, to every session on the project; - after the `project` frame of a `project_load`, from a read-only check (no probe, engine query or DB write; shared by simultaneous opens); - after a save. - **A save measures a changed file first** (as it already measured a row with no stored size), so it writes the file's real values. The report after it clears the warning. - **Until that save, the show plays the stored values.** That means the old duration, plus a probe of the picture size when the node arms the cue. The editor journal and the UI say so. - **The UI** (`cuems-frontend` `feat/869fat84r-media-check`, off `main`): - `MediaCheckService`, injected in `AppComponent`, keeps one warning per project and clears it on a complete report with nothing stale; - `MediaWarningsComponent` shows the warnings as a **banner between the header and the page**, at the page's width. It pushes the page down and covers no control (a floating toast covered the project page's Show / Close Project buttons). Each warning can be dismissed, and comes back only when its content changes; - a file's line shows what the operator sees and hears, the duration and the picture size; a change to the size or MD5 alone reads "the file changed"; - the notification card also renders `title`, keeps line breaks, and has a warning icon (no existing caller passes a title); - texts in es/en/ca. - **For your branch.** At `project_load` the same items map onto your report: - each item becomes `RepairRecord(field_path="<cue_id>/<field>", previous_value=stored, substituted_value=current, rule_name="media_file_changed")`; - with `outcome=REPAIRED` and `file_differs_from_loaded=True`.

  **But note:** with that rule, a project whose media changed becomes unsavable until a frontend handles `document_load_report` and `repair_acknowledge`, and none does yet. - **Removed in revision 2:** - the rewrite at load, and its `script.xml.pre-refresh-*` backups; - **the project lock** (with no unattended writer it only guarded concurrent operator saves, which stay last-writer-wins); - the repair tool's `--strip-dimensions` (the rollback is the XSD-patched utils debs; an unshipped emergency script lives in cuems-RELATIONS). - **`save_xml` stays atomic.** It writes a temporary file in the same directory, copies the old file's mode (the nodes' rsync reads the files as `nobody`), and renames it over, falling back to the in-place write when the directory is not writable. Your `CuemsScript.save` is atomic too, **but does not copy the mode**: please keep the old file's mode. - **A dependency on the videocomposer.** `CuemsDBMedia.video_index_state()` reads the first 32 bytes of the `.idx` (`IdxHeader` version 1 in `VideoFileInput.cpp`: magic `CXID`, size, mtime in whole seconds, frame count). It fails closed on an unknown version. If you change that header, tell us. - **Pre-existing fixes in the same path:** - `deletele_mising_media_references` used Python `and` in a peewee `where()`, so it deleted every dangling `ProjectMedia` row. It is now parenthesised `&`; - `export()` skips a dangling row instead of raising; - a relink warning had four placeholders and three arguments, so it raised `IndexError` instead of warning; - a re-upload after a permanent deletion skips trashed projects, and relinks only.

## 3. `cuems-engine`

- New `PlayerHandler.cue_media_dimensions(cue)`, used where `media_dimensions()` was called (`arm_cue.py`, `run_cue.py`):

  | Stored in the project | Result |
  | --- | --- |
  | `pixel_width` and `pixel_height`, and `file_size` equal to the node's copy (`os.stat`) | the stored values; **no subprocess** |
  | `file_size` different from the node's copy | probe, plus a WARNING naming both sizes |
  | pixel size missing or invalid | probe as before, plus one WARNING per file per engine process |
- It reads with `cue.media.get(...)`, not the new properties, so it runs on any utils that can load the file. `file_md5` is not read by the engine.
- The engine's utils floor does not change.

## 3b. `cuems-engine`: each node reports its own differing files (D20)

`NodeEngine.ready_project` keeps `deploy_media()`'s result and calls `check_own_media_sizes()`. For each of the node's own files (`CuemsScript.get_own_media`), it compares the stored `file_size` (`cue.media.get('file_size')`) with the node's copy. It logs one ERROR per file that differs or is missing, saying that the stored duration is kept and whether the media sync failed. It is report only and isolated: it runs after the previous project's teardown, so it never raises.

## 4. `cuems-frontend`

No change for the stored values. The frontend rebuilds `Media` as `{file_name, id, duration, regions}` on save, and ignores unknown keys on load. The editor adds the values after the frontend has built the dict.

D20 adds the stale-media warning banner (§2b) on `feat/869fat84r-media-check`, off `main`.

---

## 5. Compatibility with released lines

- **An old utils rejects a project that carries the new elements.** It validates strictly. This is accepted, because release 1 has not shipped.
- **Old lines get an XSD-only patch.** On `main` and the old tags, the parser assigns `Media` keys raw (`GenericParser`, `dict.__setitem__`) and never calls setters, so a patched old utils loads the values and old code never reads them.
- **Each patch adds only, and never tightens:**
  - **rc14:** rc15's file, which compared with rc14 only adds the new elements, `Md5Type` and the two curve names. It is shipped as the original rc14 deb **repacked** with that one file replaced, not rebuilt.
  - **`pre_release_1` (`2321a1f`):** that commit's own file plus the additive changes, never rc15's `duration` type or its stricter timecode pattern.
  - **Proof:** both lines, `file_md5` included, load a project with the elements and re-save it valid; every real project they accepted before still loads; their own suites are unchanged.
  - **Known limitation:** an old parser converts an MD5 that looks like a number (all digits, or digits with one `e`; about one MD5 in a million) to an `int` or `float`, so an old editor's re-save of that project fails the schema. rc15 keeps `file_md5` a string (`STRING_TYPED_KEYS`). **Your refactor needs the same protection**: never coerce `file_md5`.
- **Deployment order on a cluster:** every box gets rc15 or the patched XSD **before** the controller's editor is upgraded.
- **An old editor that re-saves a project drops the values.** Nothing breaks: the engine probes and warns.

## 6. Packaging facts found on the way

They matter to whoever releases the refactor too:

1. **The editor deb cannot be built until cuemsutils rc15 is on PyPI.** `dh-virtualenv` resolves `cuemsutils>=0.1.0rc15` from PyPI before stripping the venv. Publish utils first.
2. **Every engine deb and every utils deb ship `/usr/lib/cuems/bin/cffi-gen-src`.** Upgrading utils on a box with those engine debs fails ("trying to overwrite"). This is pre-existing (the same class as the `CACHEDIR.TAG` leak) and needs a packaging fix before any utils upgrade in the field.
3. **A utils rebuild also pulls newer build-time dependencies** (cffi 2.1.0 → 2.1.1, pip, setuptools, wheel).

---

## 7. What this means for each `feat/xml-refactor` branch

I read the four branches on 2026-10-02. How to fold this in is your call; these are the places it touches.

### `cuems-utils` (`6213b16`, rc16, does not contain `main`'s `9c17418`)

1. **Declare the fields, or they are dropped on write.** `Media.DECLARED_DEFAULTS` lists four fields, and the mapper filters a model with declared fields to exactly those, dropping and logging every other key (FR-015a). The four new fields are optional, so they need a default that emits nothing when absent, unlike `Unset`, which marks required fields.
2. **`Media` needs the setters on your branch too.** Decode builds it through `_instantiate(model, decoded)`. If that goes through `CuemsDict.setter`, a key with no `set_<key>` is skipped and decoding loses the value. On `main`, unknown `Media` keys survive.
3. **Files written by rc15 carry no `doc_version`**, so your reader treats them as script version 1. `_script_1_to_2` edits `<duration>` in place and leaves the other `Media` children alone, so the new elements survive the conversion. They then have to validate against your version 2 `script.xsd`, including `Md5Type`.
4. **A version step is your decision.** An additive optional element needs no conversion. Bumping `script` to 3 would give an older refactored library a clear `DocumentTooNewError` instead of "unexpected element".
5. **Merge `9c17418` from `main`.** rc15 releases it.
6. **Ordering is already solved on your side.** Your spec-driven ordering (known fields by schema position, unknown keys last) gives the right order once the fields are declared.

### `cuems-editor` (`89af5a9`, `rc1` + 9 commits; re-checked 2026-10-05 at `bf57d95`)

At `89af5a9` your branch had not changed the files this touches (`CuemsDBProject.py`, `CuemsDBModel.py`, `CuemsDBMedia.py`, `CuemsUpload.py`, `repair_durations.py`, `CuemsProjectManager.py`), so §2 would have merged cleanly.

**At `bf57d95` that is no longer true.** Your branch now changes `CuemsDBProject.py` (about 345 lines) and `CuemsWsUser.py` (about 370 lines), and so does our work.

- **Trial merges (2026-10-05):** most of the conflict comes from the stored values themselves (S2/D18: 8 blocks / 398 lines in `CuemsDBProject.py`, 5 / 206 in `repair_durations.py`). D20 revision 2 adds mostly new methods and small hunks in `project_ready`, `send_project` and `received_project`.
- **The difference of principle is resolved.** D20 revision 2 follows your rule: no project is rewritten without an operator's save (question 3 below).
- **Our repair tool still has Pass B**, an explicit, dry-run-first bulk save of every project. It is the duration repair used in the field. Your branch replaced it with the NEEDS_SAVE listing; at the merge, take yours, and port Pass A's pixel size, size and MD5 checks.

Two things to watch:

- Your `pyproject.toml` floor is still `cuemsutils>=0.1.0rc10`. It has to reach rc15, or rc16 if you release together.
- Your branch has no `debian/` directory, so the package floor lands on `debian/bookworm` (branch `debian/869fat84r-utils-floor`). Please keep it when you package.

### `cuems-engine` (`1662a99`, based on `main`, 14 commits behind `rc_1`, pins `cuemsutils>=0.1.0rc16,<0.1.1`)

- The call sites are the same (`arm_cue.py:147`, `run_cue.py:462` on your branch), so the change ports directly.
- It lands on `rc_1` through PR #22, which your branch does not contain yet. You get it when you merge `rc_1`, together with the pre-arm work.
- Keep `cue.media` dict-like with `.get()`, or tell us before that changes.

### `cuems-frontend` (`3183845`, 23 commits behind `main`)

- Nothing to change for the stored values.
- D20's banner (§2b) is new files plus two lines in `app.component.html` / `app.component.ts` and the notification card. It should merge cleanly, unless your branch changed the card.
- Separately: your branch still sends `duration: '00:00:00.000'` in `Media`, which predates `main`'s media-duration fix. The editor's fill corrects it, but merging `main` would remove the difference.

---

## 8. Tests on our branches

These are worth mirroring on yours.

**utils:**

- An old project loads and writes back unchanged.
- A project with the elements loads them, the integers as `int` and the MD5 as a lowercase `str`, and writes back equivalent after re-parse.
- A `Media` with the keys in any order, or with `None` values, is written in schema order with no empty element.
- Invalid values (`0`, negative, non-numeric, an MD5 that is not 32 lowercase hex digits) are rejected by both the XSD and the setters.
- An AudioCue carries size and MD5.
- Old lines (rc14 and `2321a1f`), each with its patched XSD, load and re-save a project with the elements, and real projects still validate.

**editor:**

- Migration on an old-schema DB; the second start does nothing; a failure stops the editor.
- Upload stores the pixel size for movies, and size and the verified MD5 for every type.
- The fill, rule by rule, on `update()`, `new()` and `duplicate()`; an AudioCue never gets a pixel size.
- The repair tool: a dry-run writes nothing; MD5 filled, and changed ones reported; `--no-md5`; `--strip-dimensions`.
- A failed probe never fails an upload or a save.

**editor, D20:**

- A load of an unchanged library probes nothing, asks the engine nothing and writes nothing.
- A replaced file: the row and the project are corrected, the MD5 is cleared, and there is one WARNING. A legacy project that only lacks values is not rewritten.
- `update` holding its transaction while the load-time check waits on the same project: no deadlock, and the edits are kept.

**engine:**

- With stored values, no subprocess runs on arm or on run.
- Missing values or a size mismatch fall back to the probe with exactly one WARNING per file.
- The scale computed from stored and from probed values is identical.

## 9. Questions for you

1. Do you want the four fields declared directly on your branches, or merged in from `main`/`rc1`/`rc_1` after rc15? `RESOLVED 2026-10-06`
All modifications should end in the integration branches, and will be later added to `feat/xml-refactor` for the new coordinated release if not already present or superseeded by the refactor works.

2. Is this a `script` version step on your side, or not (§7, utils point 4)? `RESOLVED 2026-10-06`
No it is not, all this changes will land into `doc_version=2` together with the rest of the modifications to the schemas, and be usable as `1 -> 2` transition. 

3. *Answered 2026-10-05 by Ion: your rule holds.* D20 revision 2 reports instead of rewriting (§2b). Remaining question: on your branch, should the stale values at `project_load` be added to your `document_load_report` as `media_file_changed` repairs? If so, the acknowledge flow needs a frontend first, or a project whose media changed cannot be saved. `RESOLVED 2026-10-06`
Yes, `media_file_changed` will be part of the `document_load_report`, and the acknowlegment machinery will be delivered as part of the `feat/xml-refactor` works on `cuems-frontend`
