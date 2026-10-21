# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
"""rc17's ``stop_project`` tests (0.1.0rc17, ClickUp 869fhjdq5), ported to the public API.

This is feature 017's A-3 port (spec D4). rc17's ``tests/test_action_cue_stop_project.py`` drove
the deprecated ``XmlReaderWriter`` / ``CuemsParser``, which bypass T2. Each of its seven
assertions is either re-expressed here through ``CuemsScript.save`` / ``load_with_report``, or
already covered by ``tests/unit/test_targetless_actions.py`` (A-1's contract tests), or
**retired** because it contradicts A-1. The mapping:

| rc17 test | Here |
|---|---|
| ``test_stop_project_is_in_the_action_type_enum`` | ported |
| ``test_stop_project_with_an_empty_target_validates_and_round_trips`` | covered: ``test_targetless_actions`` rows 5–6 |
| ``test_an_unknown_action_type_is_still_rejected_by_the_schema`` | covered: row 12 |
| ``test_cue_level_actions_keep_working_with_a_uuid_target`` | ported |
| ``test_constructor_accepts_an_empty_target_and_refuses_none`` | ``""`` → ``None``: covered (row 3); "refuses ``None``": **retired** |
| ``test_setter_still_refuses_none_after_init`` | **retired** for ``stop_project``; its intent is kept for cue-level actions, ported |
| ``test_editor_json_payload_with_a_null_target_parses_to_none`` | covered: row 4 (``from_json``) |

The two retirements are recorded in
``specs/017-release-line-reconciliation/evidence/test-retirements.md``. rc17 refused a ``None``
target for ``stop_project`` at construction and at the setter. A-1 accepts it, because the
frontend sends ``null`` (S-2). That is one of spec FR-003a's deliberate departures.
"""
import pytest

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome
from cuemsutils.xml.schema import get_schema
from tests.support.capture_goldens import build_generated_script


def test_stop_project_is_in_the_action_type_enum():
    assert "stop_project" in get_schema("script").types["ActionType"].enumeration


def test_cue_level_actions_keep_working_with_a_uuid_target(tmp_path):
    """A ``stop`` aimed at a cue saves and loads with its target intact."""
    script = build_generated_script()
    action = next(c for c in script.cuelist.contents if isinstance(c, ActionCue))
    target = next(c for c in script.cuelist.contents if type(c).__name__ == "AudioCue").id
    action.action_type = "stop"
    action.action_target = target
    path = tmp_path / "cue_level_stop.xml"
    script.save(str(path))

    loaded, report = CuemsScript.load_with_report(str(path))
    assert report.outcome is Outcome.CLEAN
    cue = next(c for c in loaded.cuelist.contents if isinstance(c, ActionCue))
    assert cue.action_type == "stop"
    assert str(cue.action_target) == str(target)


def test_the_setter_still_refuses_none_for_a_cue_level_action():
    """rc17's ``test_setter_still_refuses_none_after_init``, kept where it still holds: a
    cue-level action needs a target. For ``stop_project`` the setter now accepts ``None`` (A-1)."""
    cue = ActionCue({"action_type": "stop", "action_target": ""})
    with pytest.raises(ValueError, match="^action_target is required$"):
        cue.action_target = None
