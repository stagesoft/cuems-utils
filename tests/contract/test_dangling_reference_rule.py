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


def test_a_dangling_action_target_raises_rather_than_repairing(tmp_path):
    """The asymmetry with ``target``, and why it is not an inconsistency.

    Repair means *substitute the field's declared default*, and
    ``ActionCue.REQ_ITEMS['action_target']`` is ``None`` — which
    ``action_target_required`` rejects. Repairing would produce a document
    violating the very rule that fired. **A required reference has no valid
    default by construction**, so ``action_target_resolves`` is
    ``repairable=False`` and the load raises.

    ``cuems-editor`` cleared these to ``None`` before parsing, which is why it
    never met the contradiction: it produced documents this tier rejects, and
    that would have failed at show time regardless. The outcome differs from the
    editor's; the *detection* does not, which is what FR-043c asks for.
    """
    from cuemsutils.cues.ActionCue import ActionCue
    from cuemsutils.errors import ValidationError

    script = broken.valid_script()
    action = next(
        c for c in script.cuelist.contents if isinstance(c, ActionCue)
    )
    dict.__setitem__(action, "action_target", DANGLING)
    path = _write(script, tmp_path / "dangling_action_target.xml")

    with pytest.raises(ValidationError) as raised:
        CuemsScript.load(path)

    assert "action_target" in str(raised.value)


def test_the_dangling_action_target_message_names_the_value(tmp_path):
    """FR-049d — an operator meeting this needs to know *which* reference, or
    they cannot correct the field by hand or choose a backup to restore."""
    from cuemsutils.cues.ActionCue import ActionCue
    from cuemsutils.errors import ValidationError

    script = broken.valid_script()
    action = next(
        c for c in script.cuelist.contents if isinstance(c, ActionCue)
    )
    dict.__setitem__(action, "action_target", DANGLING)
    path = _write(script, tmp_path / "named.xml")

    with pytest.raises(ValidationError) as raised:
        CuemsScript.load(path)

    assert DANGLING in str(raised.value)


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


def test_both_reference_rules_are_registered_with_the_right_repairability():
    """``target`` repairs; ``action_target`` cannot. The asymmetry is the
    contract, so it is asserted rather than left to whichever test happens to
    exercise it.

    Matched by what a rule *covers* (``applies_to``), not by its name: a name
    heuristic false-positives on the pre-existing ``action_target_required``
    (``repairable=False``) and ``fade_target_value_range`` (whose field is
    ``target_value``).
    """
    from cuemsutils.xml.validators import RULES

    def covers(field: str):
        return {r for r in RULES.values() if any(f == field for _t, f in r.applies_to)}

    target_rules = covers("target")
    action_rules = covers("action_target")

    assert any(r.repairable for r in target_rules), (
        f"no repairable rule covers 'target'; found {sorted(r.name for r in target_rules)}"
    )
    assert action_rules, "no rule covers 'action_target'"
    assert not any(r.repairable for r in action_rules), (
        "action_target must not be repairable: its declared default is None, "
        "which action_target_required rejects — repairing would restate the "
        f"violation. Found {sorted(r.name for r in action_rules if r.repairable)}"
    )


def test_the_two_action_target_rules_report_different_faults():
    """One says *there must be a reference*, the other *the reference must
    resolve*. Both can fire, and an operator needs them told apart."""
    from cuemsutils.xml.validators import RULES

    assert "action_target_required" in RULES
    assert "action_target_resolves" in RULES
    assert RULES["action_target_resolves"].document_scoped
    assert not RULES["action_target_required"].document_scoped
