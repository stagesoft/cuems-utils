# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""010 T036 — a re-run over a partly converted library converts only the remainder.

FR-095c, SC-017b, research R3. This verifies a property 008's design already
provides — ``convert_file`` returns ``CURRENT`` before it backs anything up — so
it is expected to pass on first run. It is here so that the property survives
the next change to the tool: an interrupted conversion is finished by running
the same command again, and that must convert nothing twice, back up nothing
twice and corrupt nothing.
"""

from __future__ import annotations

import shutil

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.xml.convert_documents import main
from tests.support.corpus import REPO_ROOT

PRE_008 = REPO_ROOT / "tests" / "data" / "corpus" / "pre-008" / "script_v1_all_transforms.xml"


def test_a_rerun_converts_exactly_the_remainder(tmp_path, capsys):
    documents = [tmp_path / f"show{n}.xml" for n in range(6)]
    for document in documents:
        shutil.copyfile(PRE_008, document)

    # The "interruption": the first run reached only half the library.
    done, remainder = documents[:3], documents[3:]
    assert main([str(path) for path in done]) == 0
    converted_bytes = {path: path.read_bytes() for path in done}
    capsys.readouterr()

    assert main([str(path) for path in documents]) == 0
    out = capsys.readouterr().out

    for path in done:
        assert f"{path}: already current" in out
        assert path.read_bytes() == converted_bytes[path], "converted twice"
        assert len(list(tmp_path.glob(f"{path.name}.*.bak"))) == 1, "backed up twice"
    for path in remainder:
        assert f"{path}: converted" in out
        assert len(list(tmp_path.glob(f"{path.name}.*.bak"))) == 1
    for path in documents:
        CuemsScript.load(path)  # nothing left in a partial state
