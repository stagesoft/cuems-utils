# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""An rc17-written project survives the upgrade to 0.1.1 (feature 017, S-1′, X-1).

``tests/data/rc17/`` holds two documents written by **rc17's own** ``XmlReaderWriter``.
``PROVENANCE.md`` beside them has the commit, the command and the hashes. They are in the
pre-013 shape, so on ``0.1.1`` they take the operator's path: ``cuems-reshape-devices``, then
``cuems-convert-documents``, then the loader.

Before A-1, both tools reported success on ``stop_project.xml`` and then **every 0.1.1 node
refused the project**, because T2's ``action_target_required`` had no notion of a project-scope
action. That is the field form of X-1, and this test is its proof.
"""
import shutil
from pathlib import Path

import pytest

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome
from cuemsutils.xml import convert_documents, reshape_devices

FIXTURES = Path(__file__).resolve().parents[1] / "data" / "rc17"


def _migrate(name, tmp_path):
    doc = tmp_path / name
    shutil.copy(FIXTURES / name, doc)
    assert reshape_devices.main([str(doc)]) == 0
    assert convert_documents.main([str(doc)]) == 0
    return doc


def _action(script):
    return next(c for c in script.cuelist.contents if isinstance(c, ActionCue))


def test_the_rc17_stop_project_document_loads_clean_after_migration(tmp_path):
    doc = _migrate("stop_project.xml", tmp_path)
    script, report = CuemsScript.load_with_report(str(doc))
    assert report.outcome is Outcome.CLEAN
    action = _action(script)
    assert action.action_type == "stop_project"
    assert action.action_target is None


def test_the_rc17_control_document_loads_clean_after_migration(tmp_path):
    """The control: everything but ``stop_project`` already migrated cleanly on 5e4c637."""
    doc = _migrate("stop_control.xml", tmp_path)
    script, report = CuemsScript.load_with_report(str(doc))
    assert report.outcome is Outcome.CLEAN
    action = _action(script)
    assert action.action_type == "stop"
    assert str(action.action_target) == "2c7b5a2f-3d4e-4f60-9b0c-1d2e3f4a5b61"


@pytest.mark.parametrize("name", ["stop_project.xml", "stop_control.xml"])
def test_rc17s_stored_media_values_survive_the_migration(tmp_path, name):
    """rc15's four values, as rc17 wrote them, reach 0.1.1 intact (X-4's present half)."""
    doc = _migrate(name, tmp_path)
    script = CuemsScript.load(str(doc))
    video = next(c for c in script.cuelist.contents if type(c).__name__ == "VideoCue")
    media = video["Media"]
    assert (media.pixel_width, media.pixel_height, media.file_size) == (1920, 1080, 107374182400)
    assert media.file_md5 == "d41d8cd98f00b204e9800998ecf8427e"
