# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029 — a backup precedes every rewrite, and a failed backup skips that file."""

from __future__ import annotations

import shutil
from pathlib import Path

from cuemsutils.xml import reshape_devices

_OLD = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "pre-013" / "project_mappings.xml"
)


def test_each_rewrite_is_preceded_by_a_timestamped_backup(tmp_path, monkeypatch):
    target = tmp_path / "mappings.xml"
    shutil.copyfile(_OLD, target)
    monkeypatch.setattr(reshape_devices.time, "strftime", lambda _fmt: "20261001T120000")
    copied: list[tuple[Path, Path]] = []
    real = shutil.copy2

    def _copy(src, dst):
        copied.append((Path(src), Path(dst)))
        return real(src, dst)

    monkeypatch.setattr(reshape_devices.shutil, "copy2", _copy)
    assert reshape_devices.main([str(target)]) == 0
    assert copied == [(target, target.with_name("mappings.xml.20261001T120000.bak"))]
    assert target.with_name("mappings.xml.20261001T120000.bak").read_bytes() == _OLD.read_bytes()


def test_a_backup_failure_leaves_that_document_and_continues(tmp_path, monkeypatch):
    first = tmp_path / "a.xml"
    second = tmp_path / "b.xml"
    shutil.copyfile(_OLD, first)
    shutil.copyfile(_OLD, second)
    original = second.read_bytes()

    real = shutil.copy2

    def _copy(src, dst):
        if Path(src) == second:
            raise OSError("disk full")
        return real(src, dst)

    monkeypatch.setattr(reshape_devices.shutil, "copy2", _copy)
    code = reshape_devices.main([str(first), str(second)])
    assert code == 1
    assert second.read_bytes() == original
    assert b"<devices>" in first.read_bytes() or b"devices" in first.read_bytes()
