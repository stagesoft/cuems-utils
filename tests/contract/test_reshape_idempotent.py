# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T028 — a second run changes no bytes (FR-026)."""

from __future__ import annotations

import shutil
from pathlib import Path

from cuemsutils.xml.reshape_devices import main

_OLD = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "pre-013" / "project_mappings.xml"
)


def test_a_second_run_changes_no_bytes(tmp_path, capsys):
    target = tmp_path / "project_mappings.xml"
    shutil.copyfile(_OLD, target)
    assert main([str(target)]) == 0
    rewritten = target.read_bytes()
    capsys.readouterr()
    assert main([str(target)]) == 0
    assert target.read_bytes() == rewritten
    assert "nothing to do" in capsys.readouterr().out
