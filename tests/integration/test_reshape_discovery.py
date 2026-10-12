# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T031 — discovery uses the configuration directory and the library root element."""

from __future__ import annotations

from pathlib import Path

from cuemsutils.xml.reshape_devices import main

_CORPUS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013"
_OLD = _CORPUS / "project_mappings.xml"
_OLD_SCRIPT = _CORPUS / "script.xml"


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
    # Deliberately **not** called script.xml: discovery is by root element, and
    # ``script_file_name`` is an editor-internal dict key that appears in no
    # document this library reads (feature 012's finding, still true).
    script = project / "show.xml"
    script.write_bytes(_OLD_SCRIPT.read_bytes())
    # The "not applicable" arm. Until axis D landed, any script answered this
    # way because the tool had no script transformation; it now has one, so the
    # verdict has to come from a schema this feature does not reshape.
    untouched = conf / "project_settings.xml"
    untouched.write_text(
        '<?xml version="1.0"?>'
        '<cms:CuemsProjectSettings xmlns:cms="https://stagelab.coop/cuems/">'
        "</cms:CuemsProjectSettings>",
        encoding="utf-8",
    )
    stranger = project / "notes.xml"
    stranger.write_text("<?xml version='1.0'?><Nope/>", encoding="utf-8")

    code = main(["--conf", str(conf), "--library", str(library), "--check"])
    out = capsys.readouterr().out
    assert code == 1
    assert f"{mappings}: old-shape" in out
    assert f"{script}: old-shape" in out
    assert f"{untouched}: not applicable" in out
    assert f"{stranger}: skipped (unrecognised root Nope)" in out
    assert mappings.read_bytes() == _OLD.read_bytes()
    assert script.read_bytes() == _OLD_SCRIPT.read_bytes()
