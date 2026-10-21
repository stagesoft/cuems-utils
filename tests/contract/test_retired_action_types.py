# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``pause_project`` and ``resume_project`` are not action types (feature 017, Q13, FR-029d).

Project-scope pause/resume is deferred to a future release. Both values left ``script.xsd``'s
``ActionType`` in the still-unreleased version-2 step. The record of what was retired, and how to
bring them back, is ``specs/planning/project-pause-resume-deferred.md``.

Measured before the retirement: no producer had ever written either value (frontend, editor,
nodeconf and power-bridge: zero hits on every line), and no corpus document or golden carried one.
So nothing in the field is invalidated, and no conversion is registered. A document that somehow
carries one is refused by **T1** (an enumeration violation on `action_type` that lists the allowed values). It is never rewritten into another action.
"""
import json

import pytest

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import SchemaError
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import get_schema
from cuemsutils.xml.spec import TypeKey
from tests.support.capture_goldens import build_generated_script
from tests.support.invalid_scripts import write_bypassing_validation

RETIRED = ("pause_project", "resume_project")


def _with(action_type):
    script = build_generated_script()
    action = next(c for c in script.cuelist.contents if isinstance(c, ActionCue))
    dict.__setitem__(action, "action_type", action_type)
    return script


@pytest.mark.parametrize("value", RETIRED)
def test_a_retired_value_is_refused_by_t1_at_save(tmp_path, value):
    with pytest.raises(SchemaError) as caught:
        _with(value).save(str(tmp_path / "script.xml"))
    violation = caught.value.violation
    assert violation.tier == "T1"
    assert violation.rule == "XsdEnumerationFacets"
    # The T1 message names the field and lists the values that ARE allowed; the
    # retired one is absent from that list (the library's T1 wording, unchanged by 017).
    assert violation.location[1] == "action_type"
    assert "stop_project" in violation.message and value not in violation.message


@pytest.mark.parametrize("value", RETIRED)
def test_a_retired_value_is_refused_by_t1_at_load(tmp_path, value):
    path = tmp_path / "script.xml"
    write_bypassing_validation(_with(value), str(path))
    with pytest.raises(SchemaError):
        CuemsScript.load_with_report(str(path))


@pytest.mark.parametrize("value", RETIRED)
def test_a_retired_value_from_json_is_refused_where_a_document_would_be(tmp_path, value):
    payload = json.loads(_with(value).to_json())
    script = CuemsScript.from_json(json.dumps(payload))
    with pytest.raises(SchemaError):
        script.save(str(tmp_path / "script.xml"))


def test_the_descriptor_does_not_publish_a_retired_value():
    published = _action_types()
    for value in RETIRED:
        assert value not in published


def _action_types():
    """The ``ActionType`` enumeration as the descriptor publishes it, read the way
    ``test_action_type.py`` reads it (the list the frontend consumes, 015 G3)."""
    type_descriptor = SchemaDescriptor().describe(TypeKey("script", "ActionCueType"))
    field = next(f for f in type_descriptor.fields if f.name == "action_type")
    assert field.enum_values is not None
    return set(field.enum_values)


def test_the_schema_does_not_enumerate_a_retired_value():
    values = get_schema("script").types["ActionType"].enumeration
    for value in RETIRED:
        assert value not in values
