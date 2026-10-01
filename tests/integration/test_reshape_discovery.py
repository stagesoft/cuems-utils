# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T031 — discovery uses the configuration directory and the library root element."""

from __future__ import annotations

from pathlib import Path

from cuemsutils.xml.reshape_devices import main

_OLD = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "pre-013" / "project_mappings.xml"
)


def test_no_paths_finds_conf_the_library_and_names_an_unknown_root(tmp_path, capsys):
    conf = tmp_path / "conf"
    library = tmp_path / "library"
    project = library / "projects" / "one"
    project.mkdir(parents=True)
    conf.mkdir()
    (conf / "settings.xml").write_text(
        '<?xml version="1.0"?><cms:CuemsSettings xmlns:cms="https://stagelab.coop/cuems/">'
        f"<Settings><library_path>{library}</library_path></Settings></cms:CuemsSettings>",
        encoding="utf-8",
    )
    mappings = conf / "default_mappings.xml"
    mappings.write_bytes(_OLD.read_bytes())
    script = project / "show.xml"
    script.write_text(
        '<?xml version="1.0"?><cms:CuemsProject xmlns:cms="https://stagelab.coop/cuems/">'
        "<name>n</name></cms:CuemsProject>",
        encoding="utf-8",
    )
    stranger = project / "notes.xml"
    stranger.write_text("<?xml version='1.0'?><Nope/>", encoding="utf-8")

    code = main(["--conf", str(conf), "--library", str(library), "--check"])
    out = capsys.readouterr().out
    assert code == 1
    assert f"{mappings}: old-shape" in out
    assert f"{script}: not applicable" in out
    assert f"{stranger}: skipped (unrecognised root Nope)" in out
    assert mappings.read_bytes() == _OLD.read_bytes()
