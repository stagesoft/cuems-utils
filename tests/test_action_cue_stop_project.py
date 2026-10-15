# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

"""The ``stop_project`` ActionCue vocabulary (0.1.0rc17, ClickUp 869fhjdq5).

``stop_project`` is the first project-scope action: the authored end of an
unattended show. It has no target, so its ``action_target`` is written empty
and comes back as ``None`` after parse. These tests pin that contract at the
schema and model level; the engine's behaviour is tested in cuems-engine.
"""

from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import pytest
from xmlschema import XMLSchemaValidationError

from cuemsutils.cues import ActionCue, AudioCue, CueList, CuemsScript
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.xml import XmlReaderWriter
from cuemsutils.xml.Parsers import CuemsParser

TMP_DIR = Path(__file__).parent / "tmp"
TMP_DIR.mkdir(exist_ok=True)

SCHEMA_PATH = (
    Path(__file__).parents[1] / "src" / "cuemsutils" / "xml" / "schemas" / "script.xsd"
)
# Only the root element carries the cms namespace; cue elements are unqualified.


def _audio_cue():
    cue = AudioCue({
        "Media": Media({
            "file_name": "f.wav",
            "id": "",
            "duration": "00:00:00.000",
            "regions": [
                Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})
            ],
        }),
        "ui_properties": {"warning": None},
    })
    cue.name = "audio"
    return cue


def _action_cue(action_type, action_target=""):
    cue = ActionCue({
        "action_target": action_target,
        "action_type": action_type,
        "ui_properties": {"warning": 0},
    })
    cue.name = action_type
    return cue


def _script(*cues):
    cuelist = CueList({"contents": list(cues)})
    cuelist.name = "main"
    script = CuemsScript({"CueList": cuelist})
    script.name = "proj"
    now = datetime.now(timezone.utc).isoformat()
    script.created = now
    script.modified = now
    return script


def _write(script, tmp_name):
    path = str(TMP_DIR / tmp_name)
    writer = XmlReaderWriter(schema_name="script", xmlfile=path)
    writer.write_from_object(script)
    return writer, path


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

def test_stop_project_is_in_the_action_type_enum():
    text = SCHEMA_PATH.read_text()
    assert '<xs:enumeration value="stop_project" />' in text


def test_stop_project_with_an_empty_target_validates_and_round_trips():
    writer, path = _write(
        _script(_audio_cue(), _action_cue("stop_project")), "stop_project.xml"
    )
    assert writer.validate() is None

    # On disk the target is an empty element, which TargetType allows.
    tree = ElementTree.parse(path)
    targets = tree.getroot().findall(".//ActionCue/action_target")
    assert len(targets) == 1
    assert not (targets[0].text or "").strip()

    loaded = XmlReaderWriter(schema_name="script", xmlfile=path).read_to_objects()
    cue = loaded.cuelist.contents[1]
    assert isinstance(cue, ActionCue)
    assert cue.action_type == "stop_project"
    # The parser maps the empty string to None and bypasses the setter: the
    # contract is "falsy", never a uuid, never the string 'None'.
    assert not cue.action_target
    assert cue.action_target is None


def test_an_unknown_action_type_is_still_rejected_by_the_schema():
    with pytest.raises(XMLSchemaValidationError):
        writer, _ = _write(
            _script(_audio_cue(), _action_cue("bogus_action")), "bogus_action.xml"
        )
        writer.validate()


def test_cue_level_actions_keep_working_with_a_uuid_target():
    target = _audio_cue()
    action = _action_cue("stop", str(target.id))
    writer, path = _write(_script(target, action), "cue_level_stop.xml")
    assert writer.validate() is None
    loaded = XmlReaderWriter(schema_name="script", xmlfile=path).read_to_objects()
    cue = loaded.cuelist.contents[1]
    assert cue.action_type == "stop"
    assert str(cue.action_target) == str(target.id)


# ---------------------------------------------------------------------------
# Model and the editor's JSON path
# ---------------------------------------------------------------------------

def test_constructor_accepts_an_empty_target_and_refuses_none():
    cue = ActionCue({"action_target": "", "action_type": "stop_project"})
    assert cue.action_target == ""
    with pytest.raises(ValueError):
        ActionCue({"action_target": None, "action_type": "stop_project"})


def test_setter_still_refuses_none_after_init():
    cue = _action_cue("stop_project")
    with pytest.raises(ValueError):
        cue.action_target = None


def test_editor_json_payload_with_a_null_target_parses_to_none():
    """CuemsParser is what CuemsDBProject.update() runs on the frontend payload,
    and the frontend serialises a missing target as null."""
    parsed = CuemsParser({
        "ActionCue": {
            "action_type": "stop_project",
            "action_target": None,
            "ui_properties": {"warning": 0},
        }
    }).parse()
    assert isinstance(parsed, ActionCue)
    assert parsed.action_type == "stop_project"
    assert parsed.action_target is None
