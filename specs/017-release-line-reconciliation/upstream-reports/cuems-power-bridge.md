<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Upstream report → `cuems-power-bridge`: the `stop_project` contract and `CACHEDIR.TAG`

**From:** `cuems-utils` feature 017, 2026-10-22. Informational. `cuems-utils` edits no file in your
repository.

## `stop_project`: the library half has landed

The wire contract is: the frontend authors it → the editor saves it through `cuems-utils` → the
engine runs it → the bridge reacts. `cuems-utils 0.1.1` now accepts and loads `stop_project` cues,
including projects an rc17 cluster saved. Your `origin/main` `CLAUDE.md:60` already describes the
bridge's side: a `stop_project` cue looks to the bridge exactly like an operator STOP
(`running no` → re-arm → `armed yes`, `/go` replays from the top, `/go` during re-arm answers 409
`not_armed`). Nothing changes there. **Please show that behaviour against the re-cut tags** at your
reconciliation.

## Pause/resume: deferred, and a note for when it comes

`pause_project` / `resume_project` are retired from the vocabulary (Q13). When project pause is
implemented later, it must **not** look like a STOP to the bridge, or `auto_load_persistent` would
re-drive a paused show. Your rule *"never auto-stop a running project"* (`CLAUDE.md:20`) will also
need a statement about a **paused** project: running, but held. Recorded in `cuems-utils`'
`specs/planning/project-pause-resume-deferred.md` §3.3.

## X-3: `CACHEDIR.TAG`

`cuems-utils 0.1.1` does **not** ship `/usr/lib/cuems/CACHEDIR.TAG`: `debian/rules` strips it, a
test pins it, and the built `.deb` was checked. Your package has the same fix (`0.3.0-8`), so the
shared venv's file-overwrite conflict is closed from both sides.
