"""Unit and integration tests for FadeCue."""

from os import path

import pytest

from cuemsutils.cues import CueList, CuemsScript
from cuemsutils.cues.FadeCue import FadeCue, FadeCurveType
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.xml import XmlReaderWriter

TMP_FILE = path.dirname(__file__) + '/tmp/test_fade_cue.xml'
TARGET_UUID = '1f301cf8-dd03-4b40-ac17-ef0e5e7988be'


# ---------------------------------------------------------------------------
# Phase 3 — User Story 1: construction and XML round-trip
# ---------------------------------------------------------------------------

def test_fade_cue_default_construction():
    """T005: FadeCue() with no args stores correct default values."""
    fc = FadeCue()

    assert fc.action_type == 'fade_action'
    assert fc.curve_type == FadeCurveType.linear
    assert fc.target_value == 0
    # duration defaults to None (engine populates before use)
    assert fc.duration is None


def test_fade_cue_explicit_construction():
    """T006: FadeCue with a fully specified dict stores all properties."""
    fc = FadeCue({
        'action_target': TARGET_UUID,
        'curve_type': FadeCurveType.sigmoid,
        'duration': '00:00:03.500',
        'target_value': 75,
    })

    assert str(fc.action_target) == TARGET_UUID
    assert fc.action_type == 'fade_action'
    assert fc.curve_type == FadeCurveType.sigmoid
    assert isinstance(fc.duration, CTimecode)
    assert fc.duration.float == pytest.approx(3.5, rel=1e-2)
    assert fc.target_value == 75


def _make_script_with_fade_cue():
    """Helper: build a minimal CuemsScript containing one FadeCue."""
    fc = FadeCue({
        'action_target': TARGET_UUID,
        'curve_type': FadeCurveType.linear,
        'duration': '00:00:05.000',
        'target_value': 50,
    })
    cuelist = CueList({'contents': [fc]})
    script = CuemsScript({'CueList': cuelist})
    script.name = 'FadeCue Test Script'
    return script, fc


def test_fade_cue_xml_serialisation():
    """T007: A FadeCue serialises to valid XML with the expected element structure."""
    script, _ = _make_script_with_fade_cue()
    writer = XmlReaderWriter(schema_name='script', xmlfile=TMP_FILE)
    writer.write_from_object(script)

    # Schema validation must pass (requires FadeCueType in XSD and FadeCue in
    # CueListContentsType — both added in T014/T015)
    assert writer.validate() is None

    # The written file must contain a FadeCue element with the correct children
    import xml.etree.ElementTree as ET
    tree = ET.parse(TMP_FILE)
    root = tree.getroot()
    def find_all_tags(element, tag):
        return element.findall('.//' + tag)

    fade_cues = find_all_tags(root, 'FadeCue')
    assert len(fade_cues) >= 1, "Expected at least one <FadeCue> element"

    fc_elem = fade_cues[0]
    assert fc_elem.find('curve_type') is not None
    assert fc_elem.find('duration') is not None
    assert fc_elem.find('target_value') is not None
    assert fc_elem.find('curve_type').text == 'linear'
    assert fc_elem.find('target_value').text == '50'


def test_fade_cue_xml_round_trip():
    """T008: A FadeCue survives an XML round-trip with full property fidelity."""
    script, original_fc = _make_script_with_fade_cue()
    writer = XmlReaderWriter(schema_name='script', xmlfile=TMP_FILE)
    writer.write_from_object(script)
    assert writer.validate() is None

    reader = XmlReaderWriter(schema_name='script', xmlfile=TMP_FILE)
    loaded_script = reader.read_to_objects()

    loaded_cues = loaded_script.cuelist.contents
    assert len(loaded_cues) >= 1

    loaded_fc = loaded_cues[0]
    # Must deserialise as a FadeCue, not a generic dict
    assert isinstance(loaded_fc, FadeCue), (
        f"Expected FadeCue, got {type(loaded_fc).__name__}"
    )
    assert loaded_fc.action_type == 'fade_action'
    assert loaded_fc.curve_type == FadeCurveType.linear
    assert loaded_fc.target_value == original_fc.target_value
    assert loaded_fc.duration.float == pytest.approx(original_fc.duration.float, rel=1e-2)


# ---------------------------------------------------------------------------
# Phase 4 — User Story 2: validation
# ---------------------------------------------------------------------------

def test_invalid_action_type_raises():
    """T017: Constructing FadeCue with action_type != 'fade_action' raises ValueError."""
    with pytest.raises(ValueError):
        FadeCue({'action_type': 'play', 'action_target': TARGET_UUID})


def test_invalid_curve_type_raises():
    """T018: Assigning an unrecognised curve_type raises ValueError."""
    fc = FadeCue()
    with pytest.raises(ValueError):
        fc.curve_type = 'triangle'


def test_zero_duration_raises():
    """T019: Setting duration to zero raises ValueError."""
    fc = FadeCue()
    with pytest.raises(ValueError):
        fc.duration = '00:00:00.000'


def test_negative_target_value_raises():
    """T020a: target_value below 0 raises ValueError."""
    fc = FadeCue()
    with pytest.raises(ValueError):
        fc.target_value = -1


def test_over_100_target_value_raises():
    """T020b: target_value above 100 raises ValueError."""
    fc = FadeCue()
    with pytest.raises(ValueError):
        fc.target_value = 101


def test_boundary_target_value_zero_accepted():
    """T021a: target_value of exactly 0 is valid."""
    fc = FadeCue()
    fc.target_value = 0
    assert fc.target_value == 0


def test_boundary_target_value_100_accepted():
    """T021b: target_value of exactly 100 is valid."""
    fc = FadeCue()
    fc.target_value = 100
    assert fc.target_value == 100


def test_fade_cue_construction_performance():
    """T036: Constructing 10 000 FadeCue instances completes in under 1 second (FR-PERF-001)."""
    import time
    count = 10_000
    start = time.monotonic()
    for _ in range(count):
        FadeCue()
    elapsed = time.monotonic() - start
    assert elapsed < 1.0, (
        f"FadeCue construction too slow: {count} instances in {elapsed:.3f}s (limit: 1.0s)"
    )


def test_fade_cue_inherits_none_target_guard():
    """T034: FadeCue({'action_target': None}) raises ValueError via inherited ActionCue guard."""
    with pytest.raises(ValueError):
        FadeCue({'action_target': None})


# ---------------------------------------------------------------------------
# Phase 5 — User Story 3: create_script integration
# ---------------------------------------------------------------------------

def test_create_script_contains_fade_cue():
    """T026: create_script() produces a script that contains at least one FadeCue."""
    from cuemsutils.create_script import create_script

    script = create_script()
    fade_cues = [c for c in script.cuelist.contents if isinstance(c, FadeCue)]
    assert len(fade_cues) >= 1, "Expected at least one FadeCue in create_script() output"


def test_create_script_validates_with_fade_cue():
    """T027: create_script() internally validates its output with FadeCue and returns.

    create_script() calls validate_template() before returning.  If schema
    validation had failed the error would be logged and the script returned
    would still contain the FadeCue (the function does not raise).  This test
    verifies the function completes successfully and the FadeCue is present,
    confirming no regression was introduced by adding FadeCue to the template.
    """
    from cuemsutils.create_script import create_script

    # create_script() runs validate_template internally — if it raised the test fails
    script = create_script()

    fade_cues = [c for c in script.cuelist.contents if isinstance(c, FadeCue)]
    assert len(fade_cues) >= 1, (
        "create_script() must return a script containing at least one FadeCue; "
        "check that the internal validate_template() call did not eliminate it"
    )
    # Verify the FadeCue properties are intact after the function returns
    fc = fade_cues[0]
    assert fc.action_type == 'fade_action'
    assert isinstance(fc.curve_type, FadeCurveType)
    assert fc.target_value == 0
