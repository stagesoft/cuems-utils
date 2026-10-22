<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Upstream report → `cuems-engine`: X-1…X-4 answered, and two values retired

**From:** `cuems-utils` feature 017, 2026-10-22. It answers the four obligations your pre-spec
placed on this library (`specs/planning/release-line-reconciliation-0.1.1.md` §8.1, `945ccba`).
`cuems-utils` edits no file in your repository.

| Id | Your obligation | Answer in `0.1.1` |
|---|---|---|
| **X-1** | accept a `stop_project` cue at save **and** load, from code, from JSON (`null` target), and from an rc17-written project after migration | **Met.** `TARGETLESS_ACTION_TYPES = {"stop_project"}` is consulted by T2 and the constructor. An rc17-written project loads CLEAN after `cuems-reshape-devices` → `cuems-convert-documents` (`cuems-utils` `tests/integration/test_rc17_migration.py`, using a fixture written by rc17's own writer). Your strict xfails should turn XPASS(strict) on your next run against the re-cut tag |
| **X-2** | keep `Replaces: cuems-engine (<< 0.1.0rc6-2~)` | **Kept**, as relation row 26 (5/5 dpkg verdicts OK), in the built `0.1.1` `.deb`. No `Breaks:` with it, as released |
| **X-3** | nobody ships `/usr/lib/cuems/CACHEDIR.TAG` | **This package's half is met**: `debian/rules` strips it after `dh_virtualenv`, pinned by a test, and the built `.deb` has none |
| **X-4** | `Media`'s absent-value semantics | **`None`**, measured and pinned (`tests/unit/test_media_absent_values.py`): absent → `.get(k)` and the attribute are `None`, the key is not in the mapping, and `to_wire()` omits it. Present → `int`, `int`, `int`, `str`. The internal `Unset` is never exposed, so your "missing → probe" branch needs no `Unset` check |

## Two action types retired: please update your side at your reconciliation

`pause_project` and `resume_project` are **no longer in `ActionType`** (11 values). Project
pause/resume is deferred to a future release. In your repository:
- `src/cuemsengine/cues/ActionHandler.py:27-29`'s comment lists them as not-yet-implemented schema
  actions. Drop the two names.
- `tests/test_action_cue.py:1519` on your `debian/bookworm` parametrizes them with `load` /
  `unload` / `wait`. Against `0.1.1`, a document carrying either is refused by **T1**, so remove the
  two from that parametrization.

**The handover for whoever implements project pause later** is `cuems-utils`'
`specs/planning/project-pause-resume-deferred.md`. It covers your `stop_project` path as the
precedent, and one trap you should know: **`libmtcmaster`'s `pause()` is literally `play()`, and
`play()` toggles**. So a naïve `resume_project → MTCSender_play` *pauses* a running show. That
document has the sources (`MtcMaster_class.cpp:119-139`) and a sketch.

## For the record

Your release line's floor `cuemsutils >= 0.1.0rc17` / `cuems-utils (>= 0.1.0rc17)` **cannot be
resolved from PyPI**: `0.1.0rc17` was tagged and its `.deb` shipped, but it was never uploaded
(PyPI JSON API, 2026-10-22). Your pre-spec already moves both to `>= 0.1.1`, so nothing changes.
