<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Upstream report → `cuems-editor`: what `cuems-utils 0.1.1` absorbed from the release line

**From:** `cuems-utils` feature 017 (`specs/017-release-line-reconciliation/`), 2026-10-22.
**Status:** informational, plus two things to confirm at your own reconciliation. `cuems-utils`
edits no file in your repository.

## 1. `CueList.get_media` now raises for a media block without a file (rc16, 869fej07m)

`0.1.1` carries rc16's media guards:

| Shape | Before (refactor line) | `0.1.1` |
|---|---|---|
| a media block **without a file** (an empty `Media` object, which a client produces when it drops the block) | bare `KeyError 'file_name'` from inside a `hasattr` guard | **`ValueError`** naming the cue: *"cue <name> (<id>) has no media file"* |
| **no** media object (`None`: an empty `<Media/>`, or JSON `Media: null`) | `KeyError` | **skipped**, with a WARNING |

You call `project_object.get_media()` on both of your lines (`CuemsDBProject.py:1097` on
`feat/xml-refactor`, `:1523` on `debian/bookworm`). Your release line already handles this
`ValueError` (its "save gate", rc1-5). **Please confirm your refactor line handles it too** once
you build against `0.1.1`.

## 2. Your half of `stop_project`

- **Send no target.** `null`, an absent key or `""` are all accepted by
  `ActionCue(...)`/`CuemsScript.from_json` for `stop_project`, and saved as `<action_target />`.
- **Do not keep a leftover uuid.** When a cue is retyped from `stop` to `stop_project`, clear its
  target. `0.1.1` **refuses** a `stop_project` cue that carries a target on `save`, with
  `ValidationError` naming the rule `project_action_takes_no_target`: *"action_target <uuid> must be
  empty: stop_project acts on the whole project and takes no target; clear it"*. On **load**, the
  same target is repaired to `None`, and `load_with_report` reports it (`Outcome.REPAIRED`, one
  `RepairRecord`).
- **`pause_project` and `resume_project` are no longer action types.** Your code never authored
  them (measured: zero hits on either line).

## 3. Unchanged for you

The md5 rule is as before: `file_md5` must be 32 **lowercase** hex digits (you already lowercase,
your 002 T039). The four stored media values, and every consumer bound
(`cuems-utils (>= 0.1.1)`, `(<< 0.1.2~)`), are unchanged.

## How to verify

Against `cuems-utils` at the 017 head, after your reconciliation:
- a project with a `stop_project` cue saves and reopens;
- a project with a cue whose media block lost its file fails the save with the named `ValueError`,
  not a `KeyError`.
