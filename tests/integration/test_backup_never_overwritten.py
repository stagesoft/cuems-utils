# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T038c — a backup never overwrites another backup (FR-102b).

Both rewriters name a backup ``<name>.<YYYYMMDDTHHMMSS>.bak``. Run in their
required order (reshape, then convert) inside one second, the second tool's
backup of the *reshaped* document used to replace the first tool's backup of
the *original*, so the pre-upgrade document was on disk nowhere while both
tools exited 0. Measured 2026-10-16: 3 of 6 chained CLI runs lost it. The
clock is pinned here, so the collision is certain rather than timing-dependent.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path

import pytest

from cuemsutils.xml import convert_documents, reshape_devices
from cuemsutils.xml.documents import backup_document

_PRE_013 = (
    Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "script.xml"
)
_SECOND = "20261016T220941"


@pytest.fixture
def one_second(monkeypatch):
    monkeypatch.setattr(time, "strftime", lambda _fmt, *_a: _SECOND)


def test_the_pair_in_one_second_keeps_the_original(tmp_path, one_second):
    target = tmp_path / "script.xml"
    shutil.copyfile(_PRE_013, target)
    original = target.read_bytes()

    assert reshape_devices.main([str(target)]) == 0
    assert convert_documents.main([str(target)]) == 0

    backups = sorted(tmp_path.glob("script.xml.*.bak"))
    assert len(backups) == 2, backups
    contents = [backup.read_bytes() for backup in backups]
    assert original in contents, "the pre-upgrade document is on disk nowhere"
    assert contents[0] != contents[1], "the second backup must be the reshaped document"


def test_the_oldest_backup_is_the_pre_upgrade_state(tmp_path, one_second):
    """The restore point FR-102b names: the first backup taken of a document."""
    target = tmp_path / "script.xml"
    shutil.copyfile(_PRE_013, target)
    original = target.read_bytes()

    reshape_devices.main([str(target)])
    convert_documents.main([str(target)])

    first = tmp_path / f"script.xml.{_SECOND}.bak"
    assert first.read_bytes() == original
    assert (tmp_path / f"script.xml.{_SECOND}.1.bak").is_file()


def test_backup_document_never_replaces_an_existing_file(tmp_path):
    target = tmp_path / "doc.xml"
    target.write_bytes(b"<new/>")
    taken = tmp_path / f"doc.xml.{_SECOND}.bak"
    taken.write_bytes(b"<original/>")

    written = backup_document(target, _SECOND)

    assert taken.read_bytes() == b"<original/>"
    assert written == tmp_path / f"doc.xml.{_SECOND}.1.bak"
    assert written.read_bytes() == b"<new/>"


def test_a_failed_copy_leaves_no_empty_backup(tmp_path, monkeypatch):
    """A reserved name that was never filled must not pose as a backup."""
    target = tmp_path / "doc.xml"
    target.write_bytes(b"<doc/>")

    def _fail(_src, _dst):
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copy2", _fail)
    with pytest.raises(OSError):
        backup_document(target, _SECOND)
    assert list(tmp_path.glob("doc.xml.*.bak")) == []
