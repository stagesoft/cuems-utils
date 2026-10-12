# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T030 — a reshaped document decodes equal to its new-shape counterpart.

One test per axis, each comparing the tool's output against the corpus
document the same source became when T024/T042/T050 migrated it. Equality is
on the **decoded domain**, not on bytes: the claim is that no value was read,
computed or dropped (FR-024), which a byte comparison could not distinguish
from "the tool happens to serialize the way the corpus is formatted".
"""

from __future__ import annotations

import shutil
from pathlib import Path

from cuemsutils.xml.reshape_devices import main
from cuemsutils.xml.settings import ProjectMappings
from tests.support.roundtrip import as_plain

_OLD = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "project_mappings.xml"
_NEW = Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils" / "project_mappings.xml"


def _domain(path: Path) -> dict:
    loaded = as_plain(ProjectMappings(str(path)).processed)
    loaded.pop("schemaLocation", None)
    return loaded


_OLD_SETTINGS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "settings.xml"
_NEW_SETTINGS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils" / "settings.xml"


def test_reshaped_settings_match_the_new_shape_document(tmp_path):
    from cuemsutils.xml.settings import Settings

    target = tmp_path / "settings.xml"
    shutil.copyfile(_OLD_SETTINGS, target)
    assert main([str(target)]) == 0

    def domain(path: Path) -> dict:
        loaded = as_plain(Settings(str(path)).processed)
        loaded.pop("schemaLocation", None)
        return loaded

    assert domain(target) == domain(_NEW_SETTINGS)


def test_reshaped_values_match_the_new_shape_document(tmp_path):
    target = tmp_path / "project_mappings.xml"
    shutil.copyfile(_OLD, target)
    assert main([str(target)]) == 0
    assert _domain(target) == _domain(_NEW)


_OLD_SCRIPT = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "script.xml"
_NEW_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "cuems-engine" / "projects" / "complex_test" / "script.xml"
)


def test_reshaped_cues_match_the_new_shape_document(tmp_path):
    """Axis D, on a script found under a name that is not ``script.xml``.

    ``pre-013/script.xml`` is the frozen copy of
    ``cuems-engine/projects/complex_test/script.xml``, which T050 migrated, so
    the two are the same document either side of the reshape. Discovery is by
    root element — the filename here is deliberately something else.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    target = tmp_path / "a-show-under-another-name.xml"
    shutil.copyfile(_OLD_SCRIPT, target)
    assert main([str(target)]) == 0
    assert CuemsScript.load(target).to_wire() == CuemsScript.load(_NEW_SCRIPT).to_wire()


def test_reshaped_cues_are_the_classes_they_were(tmp_path):
    """The reshape is a rename, so every cue keeps its Python class (FR-050a)."""
    from cuemsutils.cues.CuemsScript import CuemsScript

    target = tmp_path / "show.xml"
    shutil.copyfile(_OLD_SCRIPT, target)
    assert main([str(target)]) == 0

    def classes(script):
        found = []

        def walk(cues):
            for cue in cues:
                found.append(type(cue).__name__)
                contents = cue.get("contents") if hasattr(cue, "get") else None
                if contents:
                    walk(contents)

        walk(script["CueList"]["contents"])
        return found

    assert classes(CuemsScript.load(target)) == classes(CuemsScript.load(_NEW_SCRIPT))
    assert "AudioCue" in classes(CuemsScript.load(target))


_OLD_OUTPUTS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "outputs.xml"
_NEW_OUTPUTS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils" / "outputs.xml"


def test_reshaped_hardware_outputs_match_the_new_shape_document(tmp_path):
    """Axis D's second half (T048, FR-053)."""
    from cuemsutils.xml.documents import read_document

    target = tmp_path / "outputs.xml"
    shutil.copyfile(_OLD_OUTPUTS, target)
    assert main([str(target)]) == 0

    def domain(path: Path) -> dict:
        loaded = as_plain(read_document("hardware_outputs", str(path)))
        loaded.pop("schemaLocation", None)
        return loaded

    assert domain(target) == domain(_NEW_OUTPUTS)
