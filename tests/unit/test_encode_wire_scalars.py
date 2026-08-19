"""Scalar wire forms (T006) — data-model.md §6, contracts §W2.

Each row of the wire-format scalar table, exercised directly against
``Mapper.encode_wire`` on small synthetic cues, isolated from the corpus so a
failure here names the exact type rather than a byte offset in a 24 KB
document.
"""

from __future__ import annotations

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.Cue import Cue
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.mapper import Mapper

MAPPER = Mapper("script")


def _wire(obj):
    return MAPPER.encode_wire(obj)


def test_booltype_encodes_as_capitalized_strings():
    cue = Cue({"name": "probe", "autoload": True, "enabled": False})
    wire = _wire(cue)
    assert wire["autoload"] == "True"
    assert wire["enabled"] == "False"
    assert isinstance(wire["autoload"], str)
    assert isinstance(wire["enabled"], str)


def test_percenttype_and_looptype_encode_as_int():
    cue = AudioCue({"name": "probe", "master_vol": 42, "loop": 3})
    wire = _wire(cue)
    assert wire["master_vol"] == 42 and type(wire["master_vol"]) is int
    assert wire["loop"] == 3 and type(wire["loop"]) is int


def test_ctimecodetype_encodes_as_wrapped_dict():
    cue = Cue({"name": "probe", "offset": CTimecode("00:00:01.000")})
    wire = _wire(cue)
    assert wire["offset"] == {"CTimecode": "00:00:01.000"}


def test_enum_encodes_as_member_name():
    from cuemsutils.cues.FadeCue import FadeCue, FadeCurveType

    cue = FadeCue(
        {
            "action_target": "probe-target",
            "curve_type": FadeCurveType.exponential,
            "duration": "00:00:02.000",
            "target_value": 50,
        }
    )
    wire = _wire(cue)
    assert wire["curve_type"] == "exponential"
    assert isinstance(wire["curve_type"], str)


def test_wildcard_scalar_encodes_as_string():
    """``ui_properties`` — X10's documented fallback."""
    from cuemsutils.helpers import as_cuemsdict

    cue = Cue({"name": "probe"})
    cue.ui_properties = as_cuemsdict({"warning": 0})
    wire = _wire(cue)
    assert wire["ui_properties"]["warning"] == "0"
    assert isinstance(wire["ui_properties"]["warning"], str)


def test_unparseable_uuid_stays_the_raw_string():
    """The nil uuid — real editor traffic (corpus-sweep.md)."""
    cue = ActionCue({"action_target": "00000000-0000-0000-0000-000000000000"})
    wire = _wire(cue)
    assert wire["action_target"] == "00000000-0000-0000-0000-000000000000"


def test_valid_uuid_encodes_as_its_string_form():
    u = Uuid()
    cue = ActionCue({"action_target": str(u)})
    wire = _wire(cue)
    assert wire["action_target"] == str(u)
    assert isinstance(wire["action_target"], str)
