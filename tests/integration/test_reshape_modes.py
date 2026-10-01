# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T033 — exit 0 current, exit 1 check-found-old or skipped, exit 2 usage."""

from __future__ import annotations

import shutil
from pathlib import Path

from cuemsutils.xml.reshape_devices import main

_OLD = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "pre-013" / "project_mappings.xml"
)
_NEW = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "cuems-utils" / "project_mappings.xml"
)


def test_network_map_and_project_settings_are_not_applicable(tmp_path, capsys):
    corpus = Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils"
    network = tmp_path / "network_map.xml"
    settings = tmp_path / "project_settings.xml"
    shutil.copyfile(corpus / "network_map.xml", network)
    shutil.copyfile(
        Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-engine" / "project_settings.xml",
        settings,
    )
    before = (network.read_bytes(), settings.read_bytes())
    assert main([str(network), str(settings)]) == 0
    assert (network.read_bytes(), settings.read_bytes()) == before
    out = capsys.readouterr().out
    assert f"{network}: not applicable" in out
    assert f"{settings}: not applicable" in out
    assert "nothing to do" in out


def test_a_new_shape_document_exits_zero(tmp_path):
    target = tmp_path / "mappings.xml"
    shutil.copyfile(_NEW, target)
    assert main([str(target)]) == 0


def test_check_finds_an_old_document_and_writes_nothing(tmp_path, capsys):
    target = tmp_path / "mappings.xml"
    shutil.copyfile(_OLD, target)
    before = target.read_bytes()
    assert main(["--check", str(target)]) == 1
    assert target.read_bytes() == before
    assert "old-shape" in capsys.readouterr().out


def test_dry_run_names_the_backup_and_writes_nothing(tmp_path, capsys, monkeypatch):
    from cuemsutils.xml import reshape_devices

    target = tmp_path / "mappings.xml"
    shutil.copyfile(_OLD, target)
    before = target.read_bytes()
    monkeypatch.setattr(reshape_devices.time, "strftime", lambda _fmt: "20261001T120000")
    assert main(["--dry-run", str(target)]) == 0
    assert target.read_bytes() == before
    assert "mappings.xml.20261001T120000.bak" in capsys.readouterr().out
    assert not target.with_name("mappings.xml.20261001T120000.bak").exists()


def test_a_missing_installation_exits_two(tmp_path, capsys):
    assert main(["--conf", str(tmp_path / "missing")]) == 2
    assert "absent" in capsys.readouterr().err


def test_check_with_dry_run_is_a_usage_error():
    assert main(["--check", "--dry-run"]) == 2
