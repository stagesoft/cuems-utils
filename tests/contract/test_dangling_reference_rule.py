"""T009a / FR-043a / FR-043c / SC-010a — dangling references are the library's job.

Feature 010, US3 (wave 0). ``cuems-editor`` corrects dangling ``target`` and
``action_target`` references today, as a **raw-dict walk before parsing**
(``CuemsDBProject._clean_dangling_targets`` / ``_nullify_dangling_refs``). The
correction needs nothing but the document, so under FR-043's responsibility
test it belongs to the library, which owns repair (D21). The editor's copy is
**deleted, not ported** — two implementations of one repair is how they drift.

Two things this file is careful about:

* **It lands in wave 0, before the editor deletes its copy in wave 2a.** Between
  those two moments both run, which is harmless; the reverse order would leave a
  window in which neither does.
* **FR-043c is the point.** Without it FR-043 was satisfiable by deleting the
  fixups entirely, so these cases mirror what the editor's implementation
  actually catches — a plain ``target``, an ``action_target``, and a reference
  **nested inside a CueList**, which its recursive walk reaches and a flat one
  would not.

``target``'s declared default is already ``None`` (``cues/Cue.py:17``), so
repair-to-default and the editor's ``cue_data['target'] = None`` agree.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome
from tests.support import invalid_scripts as broken

DANGLING = "00000000-dead-beef-0000-000000000000"


def _first_cue(script):
    return script.cuelist.contents[0]


def _write(script, path):
    broken.write_bypassing_validation(script, path)
    return path


def test_a_dangling_target_is_cleared_and_reported(tmp_path):
    script = broken.valid_script()
    dict.__setitem__(_first_cue(script), "target", DANGLING)
    path = _write(script, tmp_path / "dangling_target.xml")

    loaded, report = CuemsScript.load_with_report(path)

    assert report.outcome is Outcome.REPAIRED
    assert _first_cue(loaded)["target"] is None
    assert any(r.rule_name == "target_resolves" for r in report.repairs), (
        "the repair must be named in the report, not applied silently"
    )
    record = next(r for r in report.repairs if r.rule_name == "target_resolves")
    assert record.previous_value == DANGLING
    assert record.substituted_value is None


def test_a_dangling_action_target_is_cleared_and_reported(tmp_path):
    from cuemsutils.cues.ActionCue import ActionCue

    script = broken.valid_script()
    action = next(
        c for c in script.cuelist.contents if isinstance(c, ActionCue)
    )
    dict.__setitem__(action, "action_target", DANGLING)
    path = _write(script, tmp_path / "dangling_action_target.xml")

    loaded, report = CuemsScript.load_with_report(path)

    assert report.outcome is Outcome.REPAIRED
    assert any("action_target" in r.field_path for r in report.repairs)


def test_a_reference_that_resolves_is_left_alone(tmp_path):
    """The rule must discriminate. A test that only proves clearing would pass
    against an implementation that clears every reference."""
    script = broken.valid_script()
    first, second = script.cuelist.contents[0], script.cuelist.contents[1]
    dict.__setitem__(second, "target", first["id"])
    path = _write(script, tmp_path / "resolving_target.xml")

    loaded, report = CuemsScript.load_with_report(path)

    assert report.outcome is Outcome.CLEAN
    assert loaded.cuelist.contents[1]["target"] == first["id"]


def test_the_rule_reaches_references_nested_inside_a_cuelist(tmp_path):
    """SC-010a — 100% of the cases the editor's implementation catches. Its walk
    recurses into nested CueLists; a flat implementation would pass every test
    above and still miss this.

    The nested CueList is **constructed here**, not looked for: the shared
    fixture is flat (AudioCue, DmxCue, VideoCue, ActionCue, FadeCue), and
    skipping when it is absent would let this coverage requirement disappear
    quietly the moment the fixture changed."""
    from cuemsutils.cues.CueList import CueList

    script = broken.valid_script()
    inner = script.cuelist.contents[0]
    dict.__setitem__(inner, "target", DANGLING)
    nested = CueList({"contents": [inner]})
    dict.__setitem__(script.cuelist, "contents", [nested] + list(script.cuelist.contents[1:]))
    path = _write(script, tmp_path / "dangling_nested.xml")

    loaded, report = CuemsScript.load_with_report(path)

    assert report.outcome is Outcome.REPAIRED
    assert any(r.rule_name == "target_resolves" for r in report.repairs)


def test_the_rule_is_registered_and_repairable():
    """FR-043a — repairable, so a dangling reference degrades a document rather
    than rejecting it, matching the editor's behaviour today."""
    from cuemsutils.xml.validators import RULES

    # Matched by what a rule *covers*, not by what it is called: T015a has not
    # named it yet, and a name heuristic would false-positive on the existing
    # ``action_target_required`` (repairable=False) and ``fade_target_value_range``
    # (whose field is ``target_value``). Asserting on ``applies_to`` pins the
    # contract without over-constraining the name.
    repairable_fields = {
        field
        for rule in RULES.values()
        if rule.repairable
        for _type, field in rule.applies_to
    }
    assert "target" in repairable_fields, (
        f"no repairable rule covers 'target'; repairable fields = {sorted(repairable_fields)}"
    )
    assert "action_target" in repairable_fields, (
        f"no repairable rule covers 'action_target'; "
        f"repairable fields = {sorted(repairable_fields)}"
    )
