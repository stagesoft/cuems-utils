# Retirements: the one index (FR-029b, SC-006)

Every absorbed test, script or vocabulary item that 017 deliberately does **not** keep, with its
reason. Columns follow data-model §6. A retirement not named in spec FR-003a's list needs the
maintainer's go-ahead before it lands (T040).

| What | Origin | Reason (the settled decision it contradicts, or "no tests") | Replacement / record |
|---|---|---|---|
| `ActionType` values `pause_project`, `resume_project` | `script.xsd` since 2020; rc17 kept them "unimplemented" | Q13: project pause/resume is deferred to a future release; no producer ever wrote them and no document carried them (measured) | `specs/planning/project-pause-resume-deferred.md` (verbatim record, prior art, how to reinstate); `tests/contract/test_retired_action_types.py` pins the refusal |
| `tests/test_action_cue_stop_project.py::test_constructor_accepts_an_empty_target_and_refuses_none`, the "refuses `None`" half | rc17 (`363eaf5`) | A-1 / S-2: a `stop_project` cue accepts a `None` target, which is what the frontend sends (spec FR-003a item 6). The `""` → `None` half is kept | `tests/unit/test_targetless_actions.py::test_row2…`, `::test_row3…` |
| `tests/test_action_cue_stop_project.py::test_setter_still_refuses_none_after_init` | rc17 (`363eaf5`) | A-1: the setter accepts `None` for `stop_project` (FR-003a item 6). Its intent, that a cue-level action needs a target, is kept | `tests/unit/test_stop_project_cue.py::test_the_setter_still_refuses_none_for_a_cue_level_action` |
| `tests/test_action_cue_stop_project.py` (root copy; the other five tests) | rc17 | replaced by its public-API port (D4); used the deprecated `XmlReaderWriter`/`CuemsParser` | `tests/unit/test_stop_project_cue.py` (2 ported; 3 covered by `test_targetless_actions.py` rows 4, 5–6, 12; mapping in its docstring) |
| `tests/test_media_guards.py` (root copy) | rc16 (`3fa8728`) | **moved, not changed**: the tests already exercise the public model | `tests/unit/test_media_guards.py` |
| `tests/unit/test_media_pixel_dimensions.py::TestFileMd5::test_stored_lowercase` | rc15 (869fat84r) | 014's strict `Md5Type`: the setter **raises** on an uppercase md5 rather than lowercasing it (`Uuid`'s precedent; 014 plan §10.5). Every released producer lowercases before assigning (`cuems-editor` 002 T039; the rc15 line's own editor, `CuemsDBMedia.py:443`). Spec FR-003a item 1 | `TestFileMd5::test_the_schema_rejects_invalid_values[<file_md5>D41D…</file_md5>]` pins the refusal; the strict setter is `tests/unit/test_media_block.py`'s |
| `tests/testdev_nng_talk.py` | 2025 (a manual NNG talk script) | **no tests**: never collected (`python_files` matches `test_*.py`), and kept only as a manual experiment (§14.3) | none; `tests/integration/test_hubservices.py` and `test_communicatorservices.py` are the NNG tests |
