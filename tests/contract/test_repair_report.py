"""The repair report's public contract (ITEM E, US7, T111-T112) —
data-model.md §4, contracts §1.
"""

from __future__ import annotations

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import ConversionRecord, LoadReport, Outcome, RepairRecord
from tests.support import invalid_scripts as broken


def test_load_report_is_importable_from_cuemsutils_errors():
    assert LoadReport is not None
    assert Outcome is not None
    assert RepairRecord is not None
    assert ConversionRecord is not None


def test_load_report_answers_frs_046s_five_questions(tmp_path):
    """Which document; which fields were repaired; what replaced what; which
    conversions ran; whether the file on disk is now stale."""
    script = broken.repairable_violation()
    path = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(script, path)

    _loaded, report = CuemsScript.load_with_report(path)

    assert report.document == str(path)  # which document
    assert report.repairs  # which fields were repaired
    record = report.repairs[0]
    assert record.previous_value is not None and record.substituted_value is not None
    assert isinstance(report.conversions, tuple)  # which conversions ran
    assert report.file_differs_from_loaded is True  # is the file now stale


def test_a_clean_load_returns_clean_never_none(tmp_path):
    script = broken.valid_script()
    path = tmp_path / "clean.xml"
    broken.write_bypassing_validation(script, path)

    _loaded, report = CuemsScript.load_with_report(path)

    assert report is not None
    assert report.outcome is Outcome.CLEAN
    assert report.conversions == ()
    assert report.repairs == ()
    assert report.file_differs_from_loaded is False


def test_repair_record_carries_the_four_named_fields():
    record = RepairRecord(
        field_path="cue-id/action_type",
        previous_value="play",
        substituted_value="fade_action",
        rule_name="fade_action_type",
    )
    assert record.field_path == "cue-id/action_type"
    assert record.previous_value == "play"
    assert record.substituted_value == "fade_action"
    assert record.rule_name == "fade_action_type"


def test_conversion_record_carries_dropped_elements():
    record = ConversionRecord(
        from_version=1, to_version=2, description="x", dropped_elements=("a", "b")
    )
    assert record.dropped_elements == ("a", "b")

    # Default is empty, not None — a caller iterates it unconditionally.
    bare = ConversionRecord(from_version=1, to_version=2, description="y")
    assert bare.dropped_elements == ()


def test_outcome_has_exactly_the_three_named_members():
    assert {member.name for member in Outcome} == {"CLEAN", "CONVERTED", "REPAIRED"}
