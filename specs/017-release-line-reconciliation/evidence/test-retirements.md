# Retirements: the one index (FR-029b, SC-006)

Every absorbed test, script or vocabulary item that 017 deliberately does **not** keep, with its
reason. Columns follow data-model §6. A retirement not named in spec FR-003a's list needs the
maintainer's go-ahead before it lands (T040).

| What | Origin | Reason (the settled decision it contradicts, or "no tests") | Replacement / record |
|---|---|---|---|
| `ActionType` values `pause_project`, `resume_project` | `script.xsd` since 2020; rc17 kept them "unimplemented" | Q13: project pause/resume is deferred to a future release; no producer ever wrote them and no document carried them (measured) | `specs/planning/project-pause-resume-deferred.md` (verbatim record, prior art, how to reinstate); `tests/contract/test_retired_action_types.py` pins the refusal |
