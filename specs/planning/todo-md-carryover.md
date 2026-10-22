<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Backlog carried over from the deleted `ToDo.md`

**Why this exists.** Feature 017's first-stable-release cleanup (FR-061, Q12) deleted the
repository-root `ToDo.md` (last edited 2025-12). Each item was checked against the code on
2026-10-21. Items still true are carried here with their evidence. Items done or superseded are
listed, with their reason, in the cleanup commit's message and at the end of this file. Pick items
up from here, or delete them when they are decided. A living backlog, not a plan.

## Still open

1. **`unix_name` on the script.** *"`unix_name` is missing on `script.xsd` for `CuemsScript`."*
   Measured: neither `script.xsd` nor `cues/CuemsScript.py` mentions `unix_name`. Open question:
   is a filesystem-safe project name wanted in the document at all? It would be an additive
   optional element: a `script` version step after `0.1.1`, under
   `specs/agreements/schema-evolution-convention.md`.
2. **`check_mappings` as `@singledispatch`.** It is still three plain methods:
   `cues/AudioCue.py:142`, `cues/Cue.py:374`, `cues/CueList.py:71`. A refactor idea with no
   behaviour change; worth it only if a fourth implementation appears.
3. **`ConfigManager.get_video_output_id` / `get_audio_output_id` for the mapping layer.** Both still
   exist (`tools/ConfigManager.py:868`, `:883`), and the notes for features 011 and 015 record that
   `get_{video,audio}_output_id('default')` raises `KeyError` on every node. Decide whether to delete
   them (the `v0.1.2` removal is the natural place) or rewrite them against the device-class
   mappings.
4. **Coverage goals.** *"complete testing for `ConfigManager`"* and *"complete 100% usage of
   `test_logging.py` to ensure syslog is working"*. The logging test module is `tests/test_logger.py`;
   no `test_logging.py` exists. Both are aspirations without a target. If wanted, state a coverage
   number and let CI's combined coverage figure carry it (017's CI gate).

## Not this repository's, recorded for its owner

- *"leave `loaded` flag to be used only for `arm()`"*. The only `loaded` here is
  `xml/settings.py`'s document-load flag. `arm()` and its loaded state are `cuems-engine`'s.
- *"revisar osc puertos hub"* (review the hub's OSC ports). Not specific enough to check. The OSC
  port fields are in `settings.xsd` (`osc_port`, `gradient_osc_port`). Raise it with the engine and
  nodeconf owners if it still means something.

## Done or superseded (not carried)

- *"`ActionCue` `fade_out` can edit by OSC the volume of the target cue…"*: superseded. `fade_out`
  left `ActionType` in 008, and `fade_action` with a `FadeCue` does this.
- *"crear xml schema de audiomixer"*: done. `audiomixer` is part of `settings.xsd`.
- *Parsers-Builders* (remove duplication; 100% tests on `xml`; `Settings` writes objects
  properly, with a legacy `data2xml` test sketch): superseded. 004 replaced the four mapping
  implementations with one schema-derived engine, 006 deleted the legacy parser tree, and 008
  ITEM B gave every configuration document a `save()` path. The sketch uses an API that no longer
  exists.
