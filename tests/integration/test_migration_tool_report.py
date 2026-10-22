# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""The migration tools report a document the loader would refuse (feature 017, S-3, FR-029c, Q3).

``cuems-reshape-devices`` and ``cuems-convert-documents`` validated only T1 before writing. So a
document that was T1-valid but T2-invalid after migration was reported as a success, written,
and then **refused by every node on load**. ``stop_project`` was the first value to make that
happen in practice (S-1′).

After each write, both tools now run the loader's own T1 + T2 check on what they wrote, and
**report** every document the loader would refuse: a WARNING naming the document and the rule,
and a ``refused on load`` count in the summary. What is written and the exit status do not
change, because both tools run in ``postinst``, which never fails (Q3: report, don't refuse).
``--check`` reports the same about what the tool would write.
"""
import shutil
from pathlib import Path

from cuemsutils.xml import convert_documents, reshape_devices

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "rc17"
CONTROL_TARGET = "2c7b5a2f-3d4e-4f60-9b0c-1d2e3f4a5b61"


def _control_with_an_emptied_stop_target(tmp_path) -> Path:
    """T1-valid (``TargetType`` admits the empty string), T2-invalid once loaded: a
    ``stop`` cue needs a target."""
    doc = tmp_path / "stop_no_target.xml"
    text = (FIXTURES / "stop_control.xml").read_text()
    assert f"<action_target>{CONTROL_TARGET}</action_target>" in text
    doc.write_text(text.replace(f"<action_target>{CONTROL_TARGET}</action_target>",
                                "<action_target />"))
    return doc


def test_a_document_the_loader_would_refuse_is_written_and_reported(tmp_path, capsys):
    doc = _control_with_an_emptied_stop_target(tmp_path)

    assert reshape_devices.main([str(doc)]) == 0
    reshaped = doc.read_bytes()
    out = capsys.readouterr()
    assert f"{doc}: reshaped" in out.out
    assert "would be refused on load: [T2] action_target_required" in out.err
    assert "1 refused on load" in out.out

    assert convert_documents.main([str(doc)]) == 0
    out = capsys.readouterr()
    assert f"{doc}: converted" in out.out
    assert doc.read_bytes() != reshaped  # convert still wrote its conversion
    assert "would be refused on load: [T2] action_target_required" in out.err
    assert "1 refused on load" in out.out


def test_check_reports_what_the_tool_would_write(tmp_path, capsys):
    doc = _control_with_an_emptied_stop_target(tmp_path)
    before = doc.read_bytes()
    reshape_devices.main(["--check", str(doc)])
    out = capsys.readouterr()
    assert doc.read_bytes() == before  # --check writes nothing
    assert "would be refused on load: [T2] action_target_required" in out.err
    assert "1 refused on load" in out.out


def test_a_document_the_loader_accepts_gets_no_report(tmp_path, capsys):
    for name in ("stop_project.xml", "stop_control.xml"):
        doc = tmp_path / name
        shutil.copy(FIXTURES / name, doc)
        assert reshape_devices.main([str(doc)]) == 0
        assert convert_documents.main([str(doc)]) == 0
    out = capsys.readouterr()
    assert "would be refused on load" not in out.err
    assert "refused on load" not in out.out
