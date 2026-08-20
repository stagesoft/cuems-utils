"""Contract C1 (T019) — ``validate()`` collects, ``save()`` raises first.

The asymmetry is deliberate and is the whole content of this file:
``validate()`` exists to *inspect*, so it answers exhaustively; ``save()``
exists to *persist*, so it answers atomically and early (FR-004, FR-004a).
A single "is this valid?" primitive would have to pick one, and picking either
makes the other call site wrong.

``ValidationReport`` is internal — a caller inspects the report it is handed
and never constructs one — so its shape is asserted here against the behaviour
``validate()``'s docstring publishes, not against an imported type.
"""

from __future__ import annotations

import sys

import pytest

from cuemsutils.errors import ValidationError
from tests.support import invalid_scripts as broken
from tests.support.public_api import assert_no_xml_import


def test_a_valid_script_reports_nothing_and_the_report_is_falsy():
    report = broken.valid_script().validate()
    assert not report
    assert len(report) == 0
    assert list(report) == []


def test_validate_names_all_three_violations():
    """FR-004: ≥3 distinct violations, all three reported."""
    report = broken.invalid_both_tiers().validate()
    assert len(report) >= 3, [v.message for v in report]

    rules = {v.rule for v in report}
    assert len(rules) >= 2, rules
    assert {v.tier for v in report} == {"T1", "T2"}


def test_every_violation_names_its_tier_rule_location_and_message():
    for violation in broken.invalid_both_tiers().validate():
        assert violation.tier in ("T1", "T2")
        assert violation.rule
        assert isinstance(violation.location, tuple)
        assert len(violation.location) == 2
        assert violation.message


def test_validate_never_raises_on_a_violation():
    """It reports. Raising is ``save()``'s job, and only ``save()``'s."""
    assert broken.structurally_invalid().validate()
    assert broken.semantically_invalid().validate()


def test_save_raises_once_and_writes_nothing(tmp_path):
    target = tmp_path / "show.xml"
    with pytest.raises(ValidationError):
        broken.invalid_both_tiers().save(target)
    assert not target.exists()


def test_the_raised_error_carries_a_violation_validate_also_reports(tmp_path):
    """FR-034b — the failure mode is a consumer catching the exception and
    finding nothing on it to show a user."""
    script = broken.invalid_both_tiers()

    with pytest.raises(ValidationError) as caught:
        script.save(tmp_path / "show.xml")

    carried = caught.value.violation
    assert carried is not None
    reported = list(script.validate())
    assert carried in reported, (carried, reported)


def test_validate_touches_no_file(tmp_path, monkeypatch):
    """"No file involved" is a contract clause, not an implementation note."""
    monkeypatch.chdir(tmp_path)
    broken.invalid_both_tiers().validate()
    assert list(tmp_path.iterdir()) == []


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
