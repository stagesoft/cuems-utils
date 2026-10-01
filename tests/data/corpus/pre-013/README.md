<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# pre-013 corpus — old-shape snapshots

**Feature**: `013-device-class-reshape` | **Task**: T005 | **Frozen**: 2026-10-01, before any schema edit.

These are the pre-narrowing shapes of the four documents feature 013 reshapes.
They are the migration fixture and the FR-027 fixture. Once a schema narrows,
no new old-shape document can be produced from this tree (research R13).

`pre-008/` is a different snapshot, for feature 008's version conversions. It
is left alone.

| File | Copied from | Old shape this file still has |
|------|-------------|-------------------------------|
| `project_mappings.xml` | `cuems-utils/project_mappings.xml` | `<audio>` / `<video>` / `<dmx>` on `<node>`, six `default_*` root elements |
| `settings.xml` | `cuems-utils/settings.xml` | `<videoplayer>` / `<audioplayer>` / `<dmxplayer>`, `<audiomixer>` beside them |
| `script.xml` | `cuems-engine/projects/complex_test/script.xml` | `<AudioCue>` / `<VideoCue>` and their cue-output elements |
| `outputs.xml` | `cuems-utils/outputs.xml` | `<video_outputs>` / `<audio_outputs>` |
| `dmxcue-fragment.xml` | `cuems-engine/sample_dmxcue.xml` | the only `<DmxCue>` in the current corpus; a fragment, not a script document |

Byte-identical to those sources at `ce0564586ea6f395358996ff64a9a354e17967f3`.
Not regenerated. Not part of the corpus manifest (`tests/support/corpus.py`
excludes `pre-013/` the way it excludes `pre-008/`).
