# Enum audit, feature 017: `ActionType` (FR-024, A-2a–c)

`specs/008-rebuild-extension/enum-audit.md` is frozen (a landed feature), so 017's changes to
the audited set are evidenced here. `tests/contract/test_enum_audit.py`'s `RETAINED` points at
this file.

| Value | 008 verdict | 017 verdict | Evidence (read 2026-10-21) |
|---|---|---|---|
| `stop_project` | (did not exist) | **RETAIN (added)** | **Implemented** by `cuems-engine`: released in `0.1.0rc6-5` (`origin/debian/bookworm` `b8431a3`, `debian/changelog` "869fhjdq5 (#35): stop_project ActionCue, the authored end of an unattended show"), introduced by `4121749`; handled by `ControllerEngine._handle_stop_project` and `NodeEngine._notify_stop_project`. **Authored** by `cuems-frontend`'s `dev` line (`6a8d528` 2026-10-16, "STOP project chip on stop_project cues"). Shipped in this library's `0.1.0rc17` and absorbed by 017's merge M1 |
| `pause_project` | RETAIN | **REMOVE** | Q13 (maintainer, 2026-10-21): project pause/resume deferred. Implemented nowhere: `cuems-engine` `ActionHandler.py:27-29` lists it as not implemented, and the only code is a 2020 placeholder (`origin/dev` `9852d79`). Authored nowhere: zero hits in `cuems-frontend`, `cuems-editor`, `cuems-nodeconf`, `cuems-power-bridge`. Record: `specs/planning/project-pause-resume-deferred.md` |
| `resume_project` | RETAIN | **REMOVE** | as `pause_project` |

**Result:** `ActionType` = `play pause stop load unload enable disable fade_action wait go_to
stop_project` (**11**). `load`, `unload` and `wait` are still unimplemented in the engine, and
they are untouched: 017's scope is the release line and Q13, not a full re-audit.

Red on M1 (`evidence/suite-M1.txt`): A-2a, A-2b and A-2c. Green after T036.
