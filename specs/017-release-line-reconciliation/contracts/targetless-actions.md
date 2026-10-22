<!--
SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
SPDX-License-Identifier: GPL-3.0-or-later
-->

# Contract: targetless (project-scope) action types — A-1

**Consumers:** `cuems-editor` (saves through `CuemsScript`), `cuems-frontend` (sends
`action_target: null`), `cuems-engine` (runs `stop_project`). **Requirements:** FR-020–FR-025,
FR-041 (X-1), SC-004. **Design:** research R3–R5.

## The set

`cuemsutils.cues.ActionCue.TARGETLESS_ACTION_TYPES == frozenset({"stop_project"})`. Internal (not
exported, not in the API snapshot). Adding a member is a one-line change plus its own test.

## Behaviour (each row is a test; `T` = a resolving cue uuid, `D` = a dangling one)

| # | Input | Path | Result |
|---|---|---|---|
| 1 | `ActionCue({"action_type": "stop_project"})` | construct | ok; `action_target is None` |
| 2 | `ActionCue({"action_type": "stop_project", "action_target": None})` | construct (S-2) | ok |
| 3 | `ActionCue({"action_type": "stop_project", "action_target": ""})` | construct (A-3a) | ok; stored `None` |
| 4 | `CuemsScript.from_json(…{"action_type": "stop_project", "action_target": null}…)` | JSON | ok |
| 5 | script with row 1's cue | `save` → file | written; the element is `<action_target />`; no violation |
| 6 | row 5's file | `load_with_report` | outcome **CLEAN**; `action_type == "stop_project"`, `action_target is None` |
| 7 | document with `stop_project` and target `T` (Q2 revisited) | `load_with_report` | **REPAIRED**: `action_target is None`; one `RepairRecord(field_path="<cue>/action_target", previous_value=T, substituted_value=None, rule_name="project_action_takes_no_target")`; file stale |
| 7a | the same with target `D` (dangling) | `load_with_report` | as row 7: one record, **no** `action_target_resolves` finding |
| 8 | `stop_project` built in code (or via `from_json`) with target `T` or `D` | construct | ok (the guard refuses only a missing target outside the set) |
| 8a | row 8's script | `save` | refused, `ValidationError`, rule `project_action_takes_no_target`, message: *action_target `<uuid>` must be empty: stop_project acts on the whole project and takes no target; clear it* |
| 8b | row 8's script | `validate()` | reports the same violation; nothing changed |
| 8c | `describe()` of `ActionCue`'s `action_target` | descriptor | **UNREPAIRABLE** (unchanged; FR-023a) |
| 9 | `ActionCue({"action_type": "stop", "action_target": None})` | construct | `ValueError: action_target is required` (unchanged wording) |
| 10 | a `stop` cue whose target is `None` (set before `_initialized`, or `action_type` changed after) | save / load | refused, T2 `action_target_required`, **not repaired**, and the action type is **never changed** (FR-023) |
| 11 | `pause_project` / `resume_project`, with or without a target | save / load / `from_json` | refused, **T1 enumeration**: retired from `ActionType` (Q13, FR-029d) |
| 12 | `action_type="no_such_action"` | save / load | refused, T1 enumeration |
| 13 | rc17 fixture (`tests/data/rc17/stop_project.xml`) | `cuems-reshape-devices` → `cuems-convert-documents` → `load_with_report` | reshape ok, convert "converted", load **CLEAN** |
| 14 | rc17 control twin (`stop` → the audio cue) | same | CLEAN (as on `5e4c637`) |

## Invariants

- **No version step.** `CURRENT_VERSION['script']` stays 2. `script.xsd`'s recorded hash changes
  once, in A-1's commit (A-2d).
- **No writer or reader change.** `None` ↔ `<action_target />` already round-trips (R4).
- **The descriptor publishes 11 `ActionType` values**: `stop_project` in, `pause_project` /
  `resume_project` out (A-2b, Q13). It does not publish the set.
- **One hash change** for `script.xsd`, covering both the `stop_project` merge and the retirement,
  in A-1's commit.
- **Messages:** rows 9–11 carry exactly `action_target is required`, and the T2 finding names the
  rule `action_target_required` (FR-UX-001).
