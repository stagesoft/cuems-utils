<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Upstream report → `cuems-frontend`: the action types `cuems-utils 0.1.1` publishes

**From:** `cuems-utils` feature 017, 2026-10-22. Informational. `cuems-utils` edits no file in your
repository.

## The published list changed: 11 action types

The schema descriptor you read (015 G3) now publishes `ActionCueType.action_type` with **11**
values:

```
play  pause  stop  load  unload  enable  disable  fade_action  wait  go_to  stop_project
```

- **`stop_project` is in.** This is the library half of your `dev` line's STOP-project chips
  (`6dc775c`; `sequence.component.html:124-125`, `:590-605`).
- **`pause_project` and `resume_project` are out.** Project pause/resume is deferred to a future
  release. You never authored them (measured: zero hits on `feat/xml-refactor`, `dev` and `main`).
  If your option lists are built from the descriptor, they drop out by themselves; if any list is
  hand-written, remove them. The handover is `cuems-utils`'
  `specs/planning/project-pause-resume-deferred.md`.

## `null` target for `stop_project`: accepted

Your `sequence.component.ts:1507` sets `action_target = null` for `stop_project`. `0.1.1` accepts
that at construction and through `from_json`, writes `<action_target />`, and loads it clean. A
`stop_project` cue that **keeps** a uuid, for example after a retype from `stop`, is refused on save.
Keep clearing the target as you do now.

## How to verify

Against `cuems-utils` at the 017 head, through the editor: author a `stop_project` cue, save, and
reopen. It reappears with no target, and the action list offers 11 values.
