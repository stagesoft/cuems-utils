# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Targetless (project-scope) action types — feature 017, A-1.

``stop_project`` acts on the whole loaded project and takes no target. One named set,
``cuemsutils.cues.ActionCue.TARGETLESS_ACTION_TYPES``, is consulted by:
- three T2 rules: ``action_target_required``, ``action_target_resolves`` and
  ``project_action_takes_no_target``;
- the construction guard, and through it ``from_json``.

Everything here goes through the **public** path (``CuemsScript.save`` / ``load_with_report`` /
``from_json`` / ``validate``), never the deprecated XML modules (spec D4). Each test is one row of
``specs/017-release-line-reconciliation/contracts/targetless-actions.md``.

A leftover target on a ``stop_project`` cue (a uuid kept when a ``stop`` cue was retyped) is
**repaired to ``None`` on load** and **refused on save**. Repair is a load-path concept: ``save``
refuses every T2 violation, repairable or not (spec Clarifications, "Q2 revisited").
"""
import json
import uuid

import pytest

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome, SchemaError, ValidationError
from tests.support.capture_goldens import build_generated_script
from tests.support.invalid_scripts import write_bypassing_validation

RULE = "project_action_takes_no_target"


def _script_with_action(action_type, action_target):
    """The generated show with its one ActionCue set to *action_type* / *action_target*.

    Plain ``dict`` assignment bypasses the setters on purpose, which is how a document's
    content reaches the object on load. A test that needs a setter calls it explicitly.
    """
    script = build_generated_script()
    action = next(c for c in script.cuelist.contents if isinstance(c, ActionCue))
    dict.__setitem__(action, "action_type", action_type)
    dict.__setitem__(action, "action_target", action_target)
    return script, action


def _audio_id(script):
    return next(c for c in script.cuelist.contents if type(c).__name__ == "AudioCue").id


def _the_action(script):
    return next(c for c in script.cuelist.contents if isinstance(c, ActionCue))


# --- rows 1–4: construction and JSON ---------------------------------------------------

def test_row1_stop_project_constructs_without_a_target():
    cue = ActionCue({"action_type": "stop_project"})
    assert cue.action_target is None


def test_row2_stop_project_constructs_with_a_none_target():
    """S-2: what the frontend sends (``action_target = null``) and the editor passes on."""
    cue = ActionCue({"action_type": "stop_project", "action_target": None})
    assert cue.action_target is None


def test_row3_an_empty_target_is_stored_as_none():
    """A-3a re-expressed: the refactor's coercion maps ``""`` to ``None`` at construction."""
    cue = ActionCue({"action_type": "stop_project", "action_target": ""})
    assert cue.action_target is None


def test_the_setter_accepts_none_on_a_stop_project_cue():
    cue = ActionCue({"action_type": "stop_project"})
    cue.action_target = None
    assert cue.action_target is None


def test_row4_from_json_accepts_a_null_target():
    script, action = _script_with_action("play", None)
    dict.__setitem__(action, "action_target", _audio_id(script))
    payload = json.loads(script.to_json())

    def retype(node):
        if isinstance(node, dict):
            if node.get("action_type") == "play" and "action_target" in node:
                node["action_type"], node["action_target"] = "stop_project", None
                return True
            return any(retype(v) for v in node.values())
        if isinstance(node, list):
            return any(retype(v) for v in node)
        return False

    assert retype(payload), "the generated show's ActionCue was not found in its JSON"
    decoded = CuemsScript.from_json(json.dumps(payload))
    action = _the_action(decoded)
    assert action.action_type == "stop_project"
    assert action.action_target is None


# --- rows 5–6: the round trip --------------------------------------------------------

def test_row5_save_writes_an_empty_target_element(tmp_path):
    script, _ = _script_with_action("stop_project", None)
    path = tmp_path / "script.xml"
    script.save(str(path))
    assert "<action_target />" in path.read_text()


def test_row6_the_saved_document_loads_clean(tmp_path):
    script, _ = _script_with_action("stop_project", None)
    path = tmp_path / "script.xml"
    script.save(str(path))
    loaded, report = CuemsScript.load_with_report(str(path))
    assert report.outcome is Outcome.CLEAN
    action = _the_action(loaded)
    assert action.action_type == "stop_project"
    assert action.action_target is None


# --- rows 7 / 7a: a leftover target is repaired on load -------------------------------

@pytest.mark.parametrize("which", ["resolving", "dangling"])
def test_row7_a_leftover_target_is_repaired_to_none_on_load(tmp_path, which):
    script, action = _script_with_action("stop_project", None)
    # A dangling leftover is a uuid4 *string*, as a document carries one. A stdlib ``uuid.UUID``
    # object would be serialised as child elements and fail T1 instead.
    leftover = _audio_id(script) if which == "resolving" else str(uuid.uuid4())
    dict.__setitem__(action, "action_target", leftover)
    path = tmp_path / "script.xml"
    write_bypassing_validation(script, str(path))

    loaded, report = CuemsScript.load_with_report(str(path))

    assert report.outcome is Outcome.REPAIRED
    assert report.file_differs_from_loaded is True
    # Exactly one finding: a dangling leftover must not ALSO trip action_target_resolves.
    assert [r.rule_name for r in report.repairs] == [RULE]
    (record,) = report.repairs
    assert record.field_path.endswith("/action_target")
    assert str(record.previous_value) == str(leftover)
    assert record.substituted_value is None
    assert _the_action(loaded).action_target is None


# --- rows 8 / 8a / 8b: built in code with a target ------------------------------------

def test_row8_stop_project_constructs_with_a_target():
    cue = ActionCue({"action_type": "stop_project", "action_target": str(uuid.uuid4())})
    assert cue.action_target is not None


def test_row8a_save_refuses_a_leftover_target_with_an_actionable_message(tmp_path):
    script, action = _script_with_action("stop_project", None)
    dict.__setitem__(action, "action_target", _audio_id(script))
    with pytest.raises(ValidationError) as caught:
        script.save(str(tmp_path / "script.xml"))
    assert caught.value.violation.rule == RULE
    message = str(caught.value)
    assert str(_audio_id(script)) in message
    assert "must be empty" in message
    assert "stop_project acts on the whole project" in message
    assert not (tmp_path / "script.xml").exists()


def test_row8b_validate_reports_it_and_changes_nothing():
    script, action = _script_with_action("stop_project", None)
    target = _audio_id(script)
    dict.__setitem__(action, "action_target", target)
    report = script.validate()
    assert [v.rule for v in report.violations] == [RULE]
    assert action.action_target == target


# --- rows 9–10: the negative twins ------------------------------------------------------

def test_row9_a_stop_cue_without_a_target_is_still_refused_at_construction():
    with pytest.raises(ValueError, match="^action_target is required$"):
        ActionCue({"action_type": "stop", "action_target": None})


def test_row10_a_stop_cue_without_a_target_is_refused_at_save(tmp_path):
    script, _ = _script_with_action("stop", None)
    with pytest.raises(ValidationError) as caught:
        script.save(str(tmp_path / "script.xml"))
    assert caught.value.violation.rule == "action_target_required"
    assert str(caught.value).endswith("action_target is required")


def test_row10_a_stop_cue_without_a_target_is_refused_at_load_and_never_retyped(tmp_path):
    """Not repaired, and never turned into another action type (FR-023)."""
    script, action = _script_with_action("stop", None)
    path = tmp_path / "script.xml"
    write_bypassing_validation(script, str(path))
    with pytest.raises(ValidationError) as caught:
        CuemsScript.load_with_report(str(path))
    assert caught.value.violation.rule == "action_target_required"
    assert "<action_type>stop</action_type>" in path.read_text()


def test_changing_the_type_away_from_stop_project_is_caught_at_save(tmp_path):
    """``set_action_type`` runs no rule, so a ``None`` target left behind by retyping
    ``stop_project`` → ``stop`` surfaces at save, never silently (research R4)."""
    cue = ActionCue({"action_type": "stop_project"})
    cue.action_type = "stop"
    script, action = _script_with_action("play", None)
    script.cuelist.contents[script.cuelist.contents.index(action)] = cue
    with pytest.raises(ValidationError) as caught:
        script.save(str(tmp_path / "script.xml"))
    assert caught.value.violation.rule == "action_target_required"


# --- row 12: an unknown action type ------------------------------------------------------

def test_row12_an_unknown_action_type_is_refused_by_t1_at_save(tmp_path):
    script, _ = _script_with_action("no_such_action", None)
    with pytest.raises(SchemaError):
        script.save(str(tmp_path / "script.xml"))


def test_row12_an_unknown_action_type_is_refused_by_t1_at_load(tmp_path):
    script, action = _script_with_action("no_such_action", None)
    dict.__setitem__(action, "action_target", _audio_id(script))
    path = tmp_path / "script.xml"
    write_bypassing_validation(script, str(path))
    with pytest.raises(SchemaError):
        CuemsScript.load_with_report(str(path))
