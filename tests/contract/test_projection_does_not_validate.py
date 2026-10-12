"""Contract C1 (T022b) — a projection is not a validation gate (FR-005a, FR-006).

``to_wire()`` and ``to_json()`` report what the object *holds*. ``save()`` is
the gate. Keeping the two separable is deliberate and the reason is measured
rather than stylistic: running T1 inside the projection would cost roughly the
15.49 ms the direct projection exists to avoid, on a 5 ms budget on the
system's hottest path.

Asserted rather than assumed, because the natural instinct when adding a
validation tier is to run it everywhere — and a ``to_wire()`` that raises turns
"the editor renders a half-built cue" into "the editor shows nothing".
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import ValidationError
from tests.support import invalid_scripts as broken
from tests.support.public_api import assert_no_xml_import

CASES = {
    "structural": broken.structurally_invalid,
    "semantic": broken.semantically_invalid,
    "both": broken.invalid_both_tiers,
}


@pytest.fixture(params=sorted(CASES), ids=sorted(CASES))
def invalid_script(request):
    return CASES[request.param]()


def test_to_wire_returns_a_payload_rather_than_raising(invalid_script):
    payload = invalid_script.to_wire()
    assert isinstance(payload, dict)
    assert payload["CuemsScript"]


def test_to_json_returns_text_rather_than_raising(invalid_script):
    text = invalid_script.to_json()
    assert isinstance(text, str)
    assert json.loads(text)


def test_save_on_the_same_object_raises(tmp_path, invalid_script):
    with pytest.raises(ValidationError):
        invalid_script.save(tmp_path / "show.xml")


def test_a_half_built_object_projects_to_a_partial_payload():
    """"Partial payload, not an exception" — stated in the contract, so pinned."""
    payload = AudioCue().to_wire()
    assert isinstance(payload, dict)


def test_an_empty_script_projects():
    payload = CuemsScript().to_wire()
    assert isinstance(payload, dict)


def test_the_projection_reports_the_broken_value_rather_than_hiding_it():
    """It is a *faithful* projection: the bad value is what comes out."""
    script = broken.structurally_invalid()
    assert script.to_wire()["CuemsScript"]["id"] == broken.BAD_UUID


def test_validate_is_what_a_caller_wanting_a_guarantee_calls(invalid_script):
    assert invalid_script.validate()


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
