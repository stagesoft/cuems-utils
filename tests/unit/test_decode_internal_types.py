"""Decoded objects carry the model's types — FR-004, FR-007–FR-010 (T023).

**Must FAIL on pre-005 code**: ``ui_properties`` decodes to a plain ``dict``.

Asserted **per field path**, so a failure names the field rather than reporting
that a 24 KB document is somehow different. The broad built-vs-decoded sweep
lives in ``test_construction_parity.py``; this file pins the specific fields
FR-019 rows 1 and 2 enumerate, plus the idempotence property FR-004 requires
and no other task owns.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.helpers import CuemsDict
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.Uuid import Uuid
from tests.support import roundtrip as rt
from tests.support.corpus import by_relpath

COMPLEX = "cuems-engine/projects/complex_test/script.xml"


@pytest.fixture(scope="module")
def script():
    return rt.read_objects(by_relpath(COMPLEX))


def media_cues(script):
    return [c for c in script["CueList"]["contents"] if "Media" in c]


# --- FR-008: the ui_properties wrapper type -------------------------------


def test_cue_ui_properties_is_a_cuemsdict(script):
    """FR-008 — the type the programmatic path already produces."""
    checked = 0
    for cue in script["CueList"]["contents"]:
        ui = cue.get("ui_properties")
        if ui is None:
            continue
        assert isinstance(ui, CuemsDict), (
            f"{type(cue).__name__}.ui_properties is {type(ui).__name__}"
        )
        checked += 1
    assert checked, "no cue in the document carries ui_properties"


def test_nested_ui_properties_content_is_wrapped_at_every_depth(script):
    """Recursion, not just the top level — ``as_cuemsdict`` is recursive."""
    for cue in script["CueList"]["contents"]:
        ui = cue.get("ui_properties")
        if not isinstance(ui, CuemsDict):
            continue
        for key, value in ui.items():
            if isinstance(value, dict):
                assert isinstance(value, CuemsDict), (
                    f"ui_properties/{key} is a bare dict at depth 2"
                )


def test_ui_properties_content_is_not_filtered(script):
    """Wildcard content survives whole — it is declared nowhere."""
    populated = [
        cue.get("ui_properties")
        for cue in script["CueList"]["contents"]
        if cue.get("ui_properties")
    ]
    assert populated, "no ui_properties content to check"
    assert any(len(ui) for ui in populated), "ui_properties decoded empty"


# --- FR-009/FR-010: regions, at depth ------------------------------------


def test_media_regions_are_region_objects(script):
    cues = media_cues(script)
    assert cues, "the document has no media cues"

    checked = 0
    for cue in cues:
        regions = cue["Media"].get("regions")
        if not regions:
            continue
        for region in regions:
            assert isinstance(region, Region), (
                f"region is {type(region).__name__}: {region!r}"
            )
            checked += 1
    assert checked, "no region was checked"


def test_region_timecodes_are_ctimecode(script):
    """FR-010 — type identity holds at depth, not only at the top level."""
    for cue in media_cues(script):
        for region in cue["Media"].get("regions") or []:
            for field in ("in_time", "out_time"):
                assert isinstance(region[field], CTimecode), (
                    f"region.{field} is {type(region[field]).__name__}"
                )


def test_media_is_a_media_object(script):
    for cue in media_cues(script):
        assert isinstance(cue["Media"], Media)


def test_media_duration_decodes_to_ctimecode(script):
    """Feature 008, FR-002 — ``MediaType.duration`` is now ``CTimecodeType``.

    Identically-named ``FadeCue.duration`` always was. The exception that kept
    ``Media.duration`` a plain string is gone: both decode to ``CTimecode``
    now, on the same machinery.
    """
    from cuemsutils.tools.CTimecode import CTimecode

    for cue in media_cues(script):
        duration = cue["Media"].get("duration")
        if duration is not None:
            assert isinstance(duration, CTimecode), (
                f"Media.duration is {type(duration).__name__}, not CTimecode"
            )


def test_identifiers_are_uuid_objects(script):
    assert isinstance(script["id"], Uuid)
    for cue in script["CueList"]["contents"]:
        assert isinstance(cue["id"], Uuid), (
            f"{type(cue).__name__}.id is {type(cue['id']).__name__}"
        )


def test_timecodes_are_ctimecode(script):
    for cue in script["CueList"]["contents"]:
        for field in ("offset", "prewait", "postwait"):
            value = cue.get(field)
            if value is not None:
                assert isinstance(value, CTimecode), (
                    f"{type(cue).__name__}.{field} is {type(value).__name__}"
                )


# --- FR-004: idempotence --------------------------------------------------
#
# Objects are routinely copied and re-fed, so coercing an already-coerced value
# is a live path rather than a theoretical one. Asserted through **both**
# construction modes, because they are two entry points to one adapter table.


@pytest.mark.parametrize(
    "type_name,value",
    [
        pytest.param("CTimecodeType", CTimecode("00:00:02.000"), id="CTimecode"),
        pytest.param("UuidType", Uuid(), id="Uuid"),
        pytest.param("TargetType", Uuid(), id="Uuid-as-target"),
    ],
)
def test_coercing_an_already_coerced_scalar_is_a_no_op(type_name, value):
    """Each adapter against the type it is bound to, not against every type."""
    from cuemsutils.xml.adapters import adapter_for

    adapter = adapter_for(type_name)
    once = adapter.decode(value)
    twice = adapter.decode(once)
    assert type(twice) is type(once)
    assert twice == once


def test_re_feeding_a_region_through_construction_leaves_it_unchanged():
    original = Region({"id": 0, "loop": 1, "in_time": "00:00:01.500", "out_time": "00:00:17.500"})
    media = Media({"file_name": "f.wav", "regions": [original]})
    again = Media({"file_name": "f.wav", "regions": media["regions"]})

    assert isinstance(again["regions"][0], Region)
    assert again["regions"][0]["in_time"] == original["in_time"]
    assert isinstance(again["regions"][0]["in_time"], CTimecode)


def test_re_feeding_a_decoded_object_through_from_decoded_is_a_no_op(script):
    """The decode mode's own idempotence, on a real decoded object."""
    from cuemsutils.cues.CuemsScript import CuemsScript

    again = CuemsScript.from_decoded(dict(script))
    assert isinstance(again["id"], Uuid)
    assert type(again["id"]) is type(script["id"])
    assert list(again) == list(script), "re-feeding changed the key order"
