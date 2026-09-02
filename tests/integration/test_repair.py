"""Repair-and-notify (ITEM E, US7, T108-T110/T115/T116) — data-model.md §3.1/§4.

A current-version document with a repairable T2 violation loads anyway, with
the field substituted to the descriptor's default and the substitution
recorded; an unrepairable one raises. Both sides are exercised on the same
load path (SC-020a), not assumed from one another.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome, ValidationError
from tests.support import invalid_scripts as broken


# --- T108: a repairable violation loads with the descriptor default -------


def test_repairable_violation_loads_with_the_descriptor_default(tmp_path):
    script = broken.repairable_violation()
    path = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(script, path)

    loaded, report = CuemsScript.load_with_report(path)

    assert report.outcome is Outcome.REPAIRED
    fade = next(c for c in loaded.cuelist.contents if c.get("action_type") == "fade_action")
    assert fade["action_type"] == "fade_action"
    assert len(report.repairs) == 1
    record = report.repairs[0]
    assert record.previous_value == "play"
    assert record.substituted_value == "fade_action"
    assert record.rule_name == "fade_action_type"


# --- T109: an unrepairable violation raises, naming document and field ----


def test_unrepairable_violation_raises_naming_the_field(tmp_path):
    script = broken.unrepairable_violation_reaching_the_t2_tier()
    path = tmp_path / "unrepairable.xml"
    broken.write_bypassing_validation(script, path)

    with pytest.raises(ValidationError) as excinfo:
        CuemsScript.load(path)

    assert excinfo.value.violation is not None
    assert excinfo.value.violation.location[1] == "action_target"
    assert excinfo.value.violation.rule == "action_target_required"


# --- T110: both sides of the boundary, on the same load path (SC-020a) ----


def test_the_repairable_unrepairable_boundary_is_exercised_both_ways(tmp_path):
    repairable_path = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(broken.repairable_violation(), repairable_path)
    loaded, report = CuemsScript.load_with_report(repairable_path)
    assert report.outcome is Outcome.REPAIRED

    unrepairable_path = tmp_path / "unrepairable.xml"
    broken.write_bypassing_validation(
        broken.unrepairable_violation_reaching_the_t2_tier(), unrepairable_path
    )
    with pytest.raises(ValidationError):
        CuemsScript.load(unrepairable_path)


# --- T115: every dropped element from conversion is reported --------------


def test_every_fade_profiles_drop_is_reported_zero_silent():
    from tests.support.corpus import REPO_ROOT

    all_transforms = (
        REPO_ROOT / "tests" / "data" / "corpus" / "pre-008" / "script_v1_all_transforms.xml"
    )
    loaded, report = CuemsScript.load_with_report(all_transforms)

    dropped = [d for record in report.conversions for d in record.dropped_elements]
    assert dropped, "the fade_profiles block must be reported dropped"
    assert len(dropped) == 1  # exactly one AudioCue carries fade_profiles in this fixture


# --- T116: a repaired-then-saved document does not re-report on reload ----


def test_saving_a_repaired_document_does_not_reproduce_the_repair_on_reload(tmp_path):
    script = broken.repairable_violation()
    original = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(script, original)

    loaded, first_report = CuemsScript.load_with_report(original)
    assert first_report.outcome is Outcome.REPAIRED

    resaved = tmp_path / "resaved.xml"
    loaded.save(resaved)  # the repaired field is now valid; save() succeeds

    reloaded, second_report = CuemsScript.load_with_report(resaved)
    assert second_report.outcome is Outcome.CLEAN
    assert second_report.repairs == ()
