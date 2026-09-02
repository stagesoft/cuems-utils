"""Backups come from the schema-upgrade path and from nothing else (ITEM E,
US7, T116a) — FR-041b, FR-041c, SC-016c.

SC-016c names three write paths: config saves (Phase 1, counted by
``tests/integration/test_config_save.py::test_routine_saves_produce_zero_backup_files``,
T029 — unbuildable earlier than that), **show-document saves**, and
**repaired-document saves** (T121's overwrite) — both counted here, since
neither existed until this phase.
"""

from __future__ import annotations

from cuemsutils.errors import Outcome
from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support import invalid_scripts as broken


def _backup_like_files(directory) -> list:
    return [
        p
        for p in directory.iterdir()
        if p.suffix in (".bak", ".back") or ".bak." in p.name or p.name.endswith(".back")
    ]


def test_a_show_document_save_produces_zero_backups(tmp_path):
    script = broken.valid_script()
    path = tmp_path / "show.xml"
    script.save(path)

    # A second, ordinary save — the routine case FR-041b scopes the backup
    # obligation away from.
    script.save(path)

    assert _backup_like_files(tmp_path) == []


def test_saving_a_repaired_document_overwrites_with_zero_backup(tmp_path):
    """FR-041c: the repaired document is saved by **overwriting**, with no
    backup — the operator's review of the report (FR-053a) is what makes the
    overwrite safe, not a copy of the corrupt original."""
    script = broken.repairable_violation()
    path = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(script, path)

    loaded, report = CuemsScript.load_with_report(path)
    assert report.outcome is Outcome.REPAIRED

    loaded.save(path)  # overwrite in place — the corrupt original is gone

    assert _backup_like_files(tmp_path) == []
    reloaded, second_report = CuemsScript.load_with_report(path)
    assert second_report.outcome is Outcome.CLEAN


def test_loading_an_old_document_produces_zero_backups(tmp_path):
    """The third routine path this suite can count directly: converting on
    *load* — as opposed to the standalone tool's deliberate rewrite — writes
    nothing at all (FR-041a), so there is nothing to back up in the first
    place."""
    import shutil

    from tests.support.corpus import REPO_ROOT

    source = (
        REPO_ROOT / "tests" / "data" / "corpus" / "pre-008" / "script_v1_all_transforms.xml"
    )
    working_copy = tmp_path / "doc.xml"
    shutil.copy2(source, working_copy)

    _loaded, report = CuemsScript.load_with_report(working_copy)
    assert report.outcome is Outcome.CONVERTED
    assert _backup_like_files(tmp_path) == []


def test_only_the_standalone_tool_ever_writes_a_backup(tmp_path):
    """The positive control: the one path that *does* write a backup is
    named, so "zero backups" above is not vacuously true because nothing in
    this file ever calls it."""
    import shutil

    from cuemsutils.xml.convert_documents import ConversionOutcome, convert_file
    from tests.support.corpus import REPO_ROOT

    source = (
        REPO_ROOT / "tests" / "data" / "corpus" / "pre-008" / "script_v1_all_transforms.xml"
    )
    working_copy = tmp_path / "doc.xml"
    shutil.copy2(source, working_copy)

    status = convert_file(working_copy)

    assert status == ConversionOutcome.CONVERTED
    assert len(_backup_like_files(tmp_path)) == 1
