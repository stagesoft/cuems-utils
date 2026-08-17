"""Regions are typed from every source — contract C6, FR-009/FR-009a (T022).

**Must FAIL on pre-005 code.** Two defects compound here:

* ``Media.set_regions`` rebinds its loop variable and **discards** the coercion
  it just performed (F12), so the assignment does nothing;
* the decoder never reaches ``RegionType``'s binding at all, so a decoded region
  stays a raw ``{'Region': {...}}`` wrapper with its timecodes as
  ``{'CTimecode': '...'}`` dicts (F19).

The four supply shapes below are the ones regions actually arrive in — measured,
not imagined. The fifth case is the one no shape covers, and it is the reason
FR-009a exists: a shape that passes through *unchanged* is a plain-dictionary
region, which is exactly the defect this contract removes, returning silently.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.tools.CTimecode import CTimecode

IN_TIME = "00:00:01.500"
OUT_TIME = "00:00:17.500"


def a_mapping() -> dict:
    return {"id": 0, "loop": 1, "in_time": IN_TIME, "out_time": OUT_TIME}


def assert_typed(media: Media, count: int = 1):
    """Every member is a ``Region``, with timecodes as ``CTimecode``."""
    regions = media["regions"]
    assert isinstance(regions, list), f"regions is {type(regions).__name__}"
    assert len(regions) == count

    for region in regions:
        assert isinstance(region, Region), (
            f"region is {type(region).__name__}, not Region: {region!r}"
        )
        assert isinstance(region["in_time"], CTimecode), (
            f"in_time is {type(region['in_time']).__name__}"
        )
        assert isinstance(region["out_time"], CTimecode)


# --- the four shapes regions are supplied in ------------------------------


def test_a_single_mapping():
    """One region, not wrapped in a list."""
    assert_typed(Media({"file_name": "f.wav", "regions": a_mapping()}))


def test_a_list_of_mappings():
    assert_typed(Media({"file_name": "f.wav", "regions": [a_mapping()]}))


def test_a_list_of_already_typed_regions():
    """Idempotence (FR-004): coercing a ``Region`` leaves it a ``Region``.

    Objects are routinely copied and re-fed, so this is a live path.
    """
    media = Media({"file_name": "f.wav", "regions": [Region(a_mapping())]})
    assert_typed(media)


def test_the_wrapped_shape_the_reader_produces():
    """``{'Region': {...}}`` — what ``xmlschema`` hands back for ``RegionsType``.

    ``regions`` reached ``GenericParser`` with ``class_string='regions'``, whose
    lookup missed (the class is ``Region``, the tag is ``regions``) and fell
    back to a generic that returns its input untouched. Every region in every
    document and every editor payload carries this shape.
    """
    media = Media({"file_name": "f.wav", "regions": [{"Region": a_mapping()}]})
    assert_typed(media)


def test_multiple_regions_are_all_typed():
    media = Media({"file_name": "f.wav", "regions": [a_mapping(), a_mapping()]})
    assert_typed(media, count=2)


# --- the shape that matches none of the four (FR-009a) --------------------


@pytest.mark.parametrize(
    "supplied",
    [
        pytest.param("00:00:01.000", id="a_bare_string"),
        pytest.param(42, id="an_int"),
        pytest.param([["nested"]], id="a_list_of_lists"),
        pytest.param([{"NotARegion": {"x": 1}}], id="a_wrapper_with_the_wrong_tag"),
    ],
)
def test_an_unrecognised_region_shape_raises(supplied):
    """FR-009a — it must raise, naming the shape, not pass through.

    Passing an unknown shape through unchanged leaves a plain dictionary in
    ``regions``, which is precisely change 2's defect reappearing — and it would
    be invisible to the goldens, because a shape that never round-trips never
    reaches a comparison.
    """
    with pytest.raises((ValueError, TypeError)):
        Media({"file_name": "f.wav", "regions": supplied})


def test_none_regions_stay_none():
    """The one falsy case that is a real value, not a bad shape."""
    media = Media({"file_name": "f.wav", "regions": None})
    assert media["regions"] is None


# --- the setter and the constructor agree ---------------------------------


def test_assignment_through_the_setter_coerces_too():
    """F12 — ``set_regions`` discarded its own coercion.

    The loop body rebound the iteration variable instead of the list member, so
    the coerced ``Region`` was computed and thrown away on every pass.
    """
    media = Media({"file_name": "f.wav"})
    media.regions = [a_mapping()]
    assert_typed(media)
