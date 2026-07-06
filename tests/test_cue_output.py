"""Unit tests for VideoCueOutput validation + canvas_region handling."""

from decimal import Decimal

import pytest

from cuemsutils.cues.CueOutput import (
    AudioCueOutput,
    DmxCueOutput,
    VideoCueOutput,
)

NODE = "0367f391-ebf4-48b2-9f26-000000000001"
ALIAS_NAME = f"{NODE}_0"
CUSTOM_NAME = f"{NODE}_custom_0"


# ---------------------------------------------------------------------------
# Alias (no canvas_region)
# ---------------------------------------------------------------------------

def test_alias_without_canvas_region_is_accepted():
    out = VideoCueOutput({"output_name": ALIAS_NAME, "output_geometry": {}})
    assert out.output_name == ALIAS_NAME
    assert out.canvas_region is None
    assert "canvas_region" not in out


def test_alias_with_stray_canvas_region_is_rejected():
    with pytest.raises(ValueError, match="must be absent for alias"):
        VideoCueOutput({
            "output_name": ALIAS_NAME,
            "canvas_region": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
        })


# ---------------------------------------------------------------------------
# Custom (canvas_region required)
# ---------------------------------------------------------------------------

def test_custom_with_canvas_region_is_accepted():
    out = VideoCueOutput({
        "output_name": CUSTOM_NAME,
        "canvas_region": {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6},
    })
    assert out.output_name == CUSTOM_NAME
    assert out.canvas_region == {"x": 0.1, "y": 0.2, "width": 0.5, "height": 0.6}


def test_custom_without_canvas_region_is_rejected():
    with pytest.raises(ValueError, match="required for custom"):
        VideoCueOutput({"output_name": CUSTOM_NAME})


def test_custom_higher_index_is_accepted():
    # Schema supports _custom_<n>; V1 UI caps at _custom_0 but parser accepts more.
    name = f"{NODE}_custom_3"
    out = VideoCueOutput({
        "output_name": name,
        "canvas_region": {"x": 0, "y": 0, "width": 1, "height": 1},
    })
    assert out.output_name == name


# ---------------------------------------------------------------------------
# output_name shape
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("bad_name", [
    "not-a-uuid_0",
    "0367f391-ebf4-48b2-9f26-000000000001",         # no suffix
    "0367f391-ebf4-48b2-9f26-000000000001_",        # empty suffix
    "0367f391-ebf4-48b2-9f26-000000000001_abc",     # alpha suffix (not custom_<n>)
    "0367f391-ebf4-48b2-9f26-000000000001_custom_", # custom without int
    "0367f391-ebf4-48b2-9f26-000000000001_custom",  # custom without _<n>
])
def test_malformed_output_name_is_rejected(bad_name):
    with pytest.raises(ValueError, match="output_name"):
        VideoCueOutput({"output_name": bad_name})


def test_non_string_output_name_is_rejected():
    with pytest.raises(ValueError, match="must be a string"):
        VideoCueOutput({"output_name": 42})


# ---------------------------------------------------------------------------
# canvas_region shape + ranges + containment
# ---------------------------------------------------------------------------

def _custom(region):
    return {"output_name": CUSTOM_NAME, "canvas_region": region}


def test_canvas_region_boundary_values_accepted():
    out = VideoCueOutput(_custom({"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}))
    assert out.canvas_region["width"] == 1.0


def test_canvas_region_missing_key_rejected():
    with pytest.raises(ValueError, match="missing keys"):
        VideoCueOutput(_custom({"x": 0, "y": 0, "width": 1}))


def test_canvas_region_unexpected_key_rejected():
    with pytest.raises(ValueError, match="unexpected keys"):
        VideoCueOutput(_custom({
            "x": 0, "y": 0, "width": 1, "height": 1, "z": 0,
        }))


@pytest.mark.parametrize("region,message_fragment", [
    ({"x": -0.1, "y": 0, "width": 0.5, "height": 0.5}, "x must be in"),
    ({"x": 0, "y": -0.1, "width": 0.5, "height": 0.5}, "y must be in"),
    ({"x": 0, "y": 0, "width": 0.0, "height": 0.5}, "width must be in"),
    ({"x": 0, "y": 0, "width": 0.5, "height": 0.0}, "height must be in"),
    ({"x": 0, "y": 0, "width": 1.5, "height": 0.5}, "width must be in"),
    ({"x": 0, "y": 0, "width": 0.5, "height": 1.5}, "height must be in"),
])
def test_canvas_region_component_out_of_range_rejected(region, message_fragment):
    with pytest.raises(ValueError, match=message_fragment):
        VideoCueOutput(_custom(region))


def test_canvas_region_x_plus_width_overflow_rejected():
    with pytest.raises(ValueError, match="x\\+width"):
        VideoCueOutput(_custom({"x": 0.7, "y": 0.1, "width": 0.5, "height": 0.5}))


def test_canvas_region_y_plus_height_overflow_rejected():
    with pytest.raises(ValueError, match="y\\+height"):
        VideoCueOutput(_custom({"x": 0.1, "y": 0.7, "width": 0.5, "height": 0.5}))


def test_canvas_region_accepts_decimal_input():
    # xmlschema legacy paths may yield Decimal; VideoCueOutput must coerce.
    out = VideoCueOutput(_custom({
        "x": Decimal("0.1"),
        "y": Decimal("0.2"),
        "width": Decimal("0.5"),
        "height": Decimal("0.5"),
    }))
    assert out.canvas_region["x"] == pytest.approx(0.1)
    assert isinstance(out.canvas_region["width"], float)


# ---------------------------------------------------------------------------
# Post-init mutation via properties
# ---------------------------------------------------------------------------

def test_set_output_name_to_malformed_rejects():
    out = VideoCueOutput({"output_name": ALIAS_NAME})
    with pytest.raises(ValueError, match="output_name"):
        out.output_name = "garbage"


def test_switch_alias_to_custom_without_region_rejects():
    out = VideoCueOutput({"output_name": ALIAS_NAME})
    with pytest.raises(ValueError, match="without setting canvas_region"):
        out.output_name = CUSTOM_NAME


def test_clearing_canvas_region_on_custom_rejects():
    out = VideoCueOutput(_custom({"x": 0, "y": 0, "width": 1, "height": 1}))
    with pytest.raises(ValueError, match="cannot be cleared on custom"):
        out.canvas_region = None


def test_setting_canvas_region_on_alias_rejects():
    out = VideoCueOutput({"output_name": ALIAS_NAME})
    with pytest.raises(ValueError, match="cannot be set on alias"):
        out.canvas_region = {"x": 0, "y": 0, "width": 1, "height": 1}


def test_canvas_region_set_validates_shape():
    out = VideoCueOutput(_custom({"x": 0, "y": 0, "width": 1, "height": 1}))
    with pytest.raises(ValueError, match="x\\+width"):
        out.canvas_region = {"x": 0.9, "y": 0, "width": 0.5, "height": 0.5}


# ---------------------------------------------------------------------------
# XSD element order — canvas_region comes after output_geometry
# ---------------------------------------------------------------------------

def test_items_keeps_canvas_region_after_output_geometry():
    out = VideoCueOutput({
        "output_name": CUSTOM_NAME,
        "canvas_region": {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5},
        "output_geometry": {"x_scale": 1, "y_scale": 1},
    })
    keys = [k for k, _ in out.items()]
    assert keys.index("output_geometry") < keys.index("canvas_region")
    assert keys.index("output_name") < keys.index("output_geometry")


# ---------------------------------------------------------------------------
# Audio / DMX: no validation, no regression
# ---------------------------------------------------------------------------

def test_audio_cue_output_accepts_free_form_names():
    out = AudioCueOutput({"output_name": f"{NODE}_system:playback_1"})
    assert out["output_name"] == f"{NODE}_system:playback_1"


def test_dmx_cue_output_accepts_free_form_names():
    out = DmxCueOutput({"output_name": NODE})
    assert out["output_name"] == NODE
