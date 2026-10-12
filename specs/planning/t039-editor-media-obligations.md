<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# T039 — the two obligations feature 014 pushes onto `cuems-editor`, specified

**Written** 2026-10-12 from `cuems-utils` feature 014's T039, which says only *"carry both into the
sibling-gate correspondence rather than this repository's tasks"*. This is that correspondence,
written so it can be implemented without re-deriving anything.

**Measured read-only** against `cuems-editor` at `origin/feat/869fat84r-media-dimensions` =
**`0b291d1`** (the rc15 line), `002-config-round-trip` = **`22f9af4`** and `feat/xml-refactor` =
**`a3309ab`**. **Nothing in that repository was modified** — another session is working in that
checkout, and a parallel session mutating a shared tree is the exact defect feature 014's own gate
prompt had to fix (`specs/014-xs-boolean-and-media-elements/baseline.md` §8.6).

---

## 1. The headline: both obligations are already implemented — on the other line

T039 asks for two things. Measured, **the rc15 line already does both, and more strictly than T039
specified.** Neither is a missing one-liner.

| T039 | What it asked for | What `0b291d1` actually has |
|---|---|---|
| **(a)** | *"`cuems-editor` must `.lower()` a client md5 before assigning it"* | `CuemsDBProject._md5` (`:72-77`) returns `value.lower()` for 32 hex digits and **`None` for anything else** — so a wrong-length or non-hex digest is *dropped* rather than lowercased into garbage. Applied through `_valid` (`:80-81`) in `_fix_one_media` step 1. Also `.lower()`ed at ingest, `CuemsDBMedia.py:425` |
| **(b)** | *"the AudioCue pixel rule has no validator… the place is the editor's fill"* | `_allowed_keys(cue_type)` (`:169-175`) returns `STORED_KEYS[2:]` for an `AudioCue`, so `_fix_one_media` **deletes** a pixel key the cue may not carry, and `_set_dimensions` never writes one back |

So T039 is **not** new work in the sense its text implies. The work is making sure these two
behaviours **survive the merge onto the 013/014 line**, where none of this code exists yet.

## 2. Why there is nothing to patch today

The media work is **absent from the xml-refactor line entirely.** `git grep` over
`002-config-round-trip -- src` finds **zero** occurrences of `pixel_width`, `pixel_height`,
`file_size` or `Media.file_md5`. (`tests/test_repair_durations.py`'s `_file_hash` is an unrelated
test helper that hashes a file for comparison; 002's own `file_md5` is the **script** file's digest
for its repair report, a different thing with the same name.)

`origin/feat/869fat84r-media-dimensions` is **not an ancestor** of `002-config-round-trip`, and
**002's spec does not mention `869fat84r` once.** So the merge is unplanned on the 002 side as well
as unperformed.

## 3. The defect a naive merge produces — this is the real T039

`CuemsDBProject.py` exists on both lines and the two versions are **architecturally different**, not
textually divergent. This is the thing to get right.

| | rc15 line (`0b291d1`) | xml-refactor line (`22f9af4`) |
|---|---|---|
| What the walk traverses | **wire dicts** | **objects** |
| Cue identification | `if 'AudioCue' in item: cue_type = 'AudioCue'` (`:243-248`) | `isinstance(cue, MEDIA_CUES)` where `MEDIA_CUES = (AudioCue, VideoCue, DmxCue, MediaCue)` (`:58`, `:88`) |
| Media access | `cue_data.get('Media')`, a plain dict | `cue.get('Media')`, a `Media` object |
| Mutation | `media[key] = value`, `del media[key]` | `media.duration = CTimecode(...)` — **attribute assignment** |
| `fix_media_durations_in_contents` | `(contents, resolver, dimensions_resolver=None)` | `(contents, resolver)` |
| Top-level functions in the file | 26 | 6 |

Three consequences, in order of how quietly they fail:

### 3.1 The AudioCue pixel strip stops working, silently

`_allowed_keys` compares `cue_type == 'AudioCue'`, and `cue_type` comes from the **pre-013 wire
key** `item['AudioCue']`. On the 013 shape the key is `Cue` with a `class` attribute, so
`'AudioCue' in item` is never true: `cue_type` falls through to `None`, `_allowed_keys(None)`
returns **all four** `STORED_KEYS`, and **a pixel size on an AudioCue is no longer stripped.**

That is obligation (b) regressing to exactly the state T039 describes as unenforced — and it
regresses *without a test failing*, because the schema accepts the pixel keys on any `MediaType`.
This is the same defect class as 010 FR-013b, which 013's own migration guide got wrong in the
opposite direction: **match on cue identity, never by walking the wire dict for a class-named key.**

### 3.2 Dict mutation becomes setter assignment, and the setter **raises**

On the object line, `media[key] = value` becomes an attribute assignment through the cuemsutils
`Media` setters, which feature 014 made strict. Verified empirically against
`cuems-utils` `014-xs-boolean-and-media-elements`:

| Assignment | Result |
|---|---|
| `file_md5 = 'abcdef0123456789abcdef0123456789'` | OK |
| `file_md5 = 'ABCDEF…'` (uppercase) | **`ValueError`** — *"must be 32 lowercase hexadecimal characters"* |
| `file_md5 = 'zzzz…'` (32 non-hex) | **`ValueError`** |
| `file_size = '107374182400'` (digit string) | OK, stored as `int` |
| `pixel_width = 0` | **`ValueError`** — absent means unknown; `0` is not a value |
| `pixel_width = 1.5` | **`ValueError`** — deliberately not `int()`, which would truncate to 1 |
| `pixel_width = True` | **`ValueError`** — `bool` is an `int` subclass |
| `pixel_width = None` | OK, **and the key is removed** |

So `_valid()` stops being hygiene and becomes **load-bearing**: on the rc15 line an invalid value
was deleted from a dict and the schema caught anything missed at `save()`; on the object line an
invalid value is a `ValueError` **at assignment**. The normalisation must run **before** the value
reaches the setter, and `None` is the correct way to clear a key (it removes it — do not `del` and
do not assign `0`).

### 3.3 `MediaCue` is in the isinstance tuple, and an unknown class decodes to it

`MEDIA_CUES` already includes bare `MediaCue`, which is what an unknown `class` attribute decodes
to (013). A cue that is *not* identifiably an `AudioCue` must therefore be treated as **"may carry
pixels"**, matching today's `cue_type = None` fallback — the permissive branch is the correct one
for an unknown class, because the strip is an editor-side convention and not a schema rule.

## 4. The work, as it should be implemented

In `src/cuemseditor/CuemsDBProject.py`, **as part of merging `869fat84r` onto the xml-refactor
line** (not before — there is nothing to change until that code arrives):

1. **Port `_positive_int`, `_md5`, `_valid`, `_allowed_keys`, `dimensions_of_row`,
   `db_dimensions_resolver`, `_dimensions_snapshot`, `_set_dimensions` unchanged.** They are pure
   value logic, have no dict/object dependency, and `_md5` is obligation (a) — keep it returning
   `None` rather than raising, so the caller drops an unusable digest instead of failing a save.
2. **Replace the cue-type derivation with identity.** `_allowed_keys` takes the **cue object**, not
   a string:
   ```python
   def _allowed_keys(cue):
       """The stored keys a cue may carry: size and MD5 on an AudioCue (D18),
       all of them on anything else — including a bare MediaCue, which is what
       an unknown class decodes to (013)."""
       return STORED_KEYS[len(PIXEL_KEYS):] if isinstance(cue, AudioCue) else STORED_KEYS
   ```
3. **Normalise before assigning, and clear with `None`.** In `_fix_one_media`, for each of
   `STORED_KEYS` present on the `Media` object: compute `_valid(key, current)`; if it is `None` *or*
   the key is not in `_allowed_keys(cue)`, assign `None` (which removes it); otherwise assign the
   normalised value. Never assign a raw client value.
4. **Give `_fix_one_media` the cue, not a type string**, and thread it through
   `_walk_media_durations`, which already has the object in hand.

### Red tests, each failing before the change

| # | Test | Why it is the right test |
|---|---|---|
| 1 | An **AudioCue** whose `Media` arrives carrying `pixel_width`/`pixel_height` loses both; a **VideoCue** keeps them | obligation (b), and it fails against a straight port of `cue_type == 'AudioCue'` |
| 2 | A cue of **unknown class** (decodes to bare `MediaCue`) **keeps** its pixel size | pins the permissive fallback deliberately, so a later "tighten this" does not silently strip |
| 3 | An **uppercase** client `file_md5` is stored lowercase and the save succeeds | obligation (a) — fails with `ValueError` if the value reaches the setter unnormalised |
| 4 | A **non-hex or wrong-length** `file_md5` is dropped and the save succeeds | the half T039 did not ask for and `_md5` already provides |
| 5 | `file_size = 0`, `1.5`, `True` from a client are dropped, not assigned | each is a `ValueError` at the setter |
| 6 | Clearing a stored value leaves the key **absent**, not `0` and not `None`-valued | absent means unknown; `to_wire` must not project a null |

## 5. Where this belongs — a recommendation, not a decision

**Not `cuems-utils`.** No library change is implied: the setters' strictness is 014's deliberate
divergence from rc15 (`specs/014-xs-boolean-and-media-elements/migration-guide.md` §2.1), and
`MediaType` is shared, so no schema here can express "no pixels on an AudioCue".

**Two defensible homes**, and the choice is the editor maintainer's:

- **Inside feature 002.** It is already restructuring this exact file — and that is the argument
  *for* as much as against: 002 adds a report subsystem (`report_id`, the script-file `file_md5`
  re-hash) to a file the rc15 line has independently grown by 20 functions, including its own
  staleness-report machinery (`stale_changes`, `stale_by_file`, `cap_report_files`,
  `_light_media_blocks`, `mark_index_failed`). **Those two report subsystems will collide**, and
  that collision is worth knowing about during 002's planning rather than at merge time. 002's spec
  mentions `869fat84r` zero times today.
- **In the `869fat84r` merge itself**, as its own small feature. Cleaner separation, but it leaves
  002 planning around a file whose shape is about to change under it.

**What should not happen** is porting `869fat84r`'s `CuemsDBProject.py` onto the object line as a
textual merge. §3.1 is a silent regression and §3.2 is a `ValueError` on a save path — both are
cheap to prevent now and expensive to diagnose later.

## 6. Status of T039 in `cuems-utils`

**Left open deliberately**, not carried. Its text says *"neither of which is `cuems-utils` work"*,
and this document is the hand-off it asks for. It closes when the editor confirms the two behaviours
hold on the merged line — the six tests in §4 are the evidence to ask for.
