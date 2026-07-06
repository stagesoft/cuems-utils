"""Roundtrip tests for canvas_region through both serialization paths."""

from datetime import datetime, timezone
from pathlib import Path

import pytest

from cuemsutils.cues import CueList, CuemsScript, VideoCue
from cuemsutils.cues.CueOutput import VideoCueOutput
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.xml import XmlReaderWriter
from cuemsutils.xml.Settings import ProjectMappings

DATA_DIR = Path(__file__).parent / "data"
TMP_DIR = Path(__file__).parent / "tmp"
TMP_DIR.mkdir(exist_ok=True)

NODE = "0367f391-ebf4-48b2-9f26-000000000001"
ALIAS_NAME = f"{NODE}_0"
CUSTOM_NAME = f"{NODE}_custom_0"


# ---------------------------------------------------------------------------
# Script path — minimal script with alias + custom outputs, float roundtrip
# ---------------------------------------------------------------------------

def _make_script_with_video_cue(region):
    """Build a minimal CuemsScript containing one VideoCue with an alias
    VideoCueOutput and a custom VideoCueOutput carrying ``region``."""
    geom_skeleton = {
        "x_scale": 1,
        "y_scale": 1,
        "corners": {
            "top_left": {"x": 0, "y": 0},
            "top_right": {"x": 0, "y": 0},
            "bottom_left": {"x": 0, "y": 0},
            "bottom_right": {"x": 0, "y": 0},
        },
    }
    vc = VideoCue({
        "Media": Media({
            "file_name": "f.mov",
            "id": "",
            "duration": "00:00:00.000",
            "regions": [
                Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})
            ],
        }),
        "ui_properties": {"warning": None},
    })
    vc.outputs = [
        VideoCueOutput({
            "output_name": ALIAS_NAME,
            "output_geometry": geom_skeleton,
        }),
        VideoCueOutput({
            "output_name": CUSTOM_NAME,
            "output_geometry": geom_skeleton,
            "canvas_region": region,
        }),
    ]
    cuelist = CueList({"contents": [vc]})
    script = CuemsScript({"CueList": cuelist})
    script.name = "canvas_region roundtrip"
    # Dates required by CuemsScript schema assertion (modified >= created).
    now = datetime.now(timezone.utc).isoformat()
    script.created = now
    script.modified = now
    return script


def test_script_roundtrip_preserves_canvas_region():
    region = {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5}
    script = _make_script_with_video_cue(region)
    tmp = TMP_DIR / "test_canvas_region_script.xml"

    writer = XmlReaderWriter(schema_name="script", xmlfile=str(tmp))
    writer.write_from_object(script)
    assert writer.validate() is None

    reader = XmlReaderWriter(schema_name="script", xmlfile=str(tmp))
    loaded = reader.read_to_objects()

    video_cues = [c for c in loaded.cuelist.contents if isinstance(c, VideoCue)]
    assert video_cues
    custom = [
        o for o in video_cues[0].outputs if o["output_name"].endswith("_custom_0")
    ]
    assert len(custom) == 1
    r = custom[0]["canvas_region"]
    assert r["x"] == pytest.approx(0.1, rel=1e-6)
    assert r["y"] == pytest.approx(0.1, rel=1e-6)
    assert r["width"] == pytest.approx(0.5, rel=1e-6)
    assert r["height"] == pytest.approx(0.5, rel=1e-6)


def test_script_roundtrip_non_trivial_float():
    """0.333 has imprecise xs:float representation; roundtrip must still
    validate and land within a sensible tolerance."""
    region = {"x": 0.333, "y": 0.25, "width": 0.5, "height": 0.4}
    script = _make_script_with_video_cue(region)
    tmp = TMP_DIR / "test_canvas_region_script_nontrivial.xml"

    writer = XmlReaderWriter(schema_name="script", xmlfile=str(tmp))
    writer.write_from_object(script)
    assert writer.validate() is None

    reader = XmlReaderWriter(schema_name="script", xmlfile=str(tmp))
    loaded = reader.read_to_objects()
    loaded_vc = [c for c in loaded.cuelist.contents if isinstance(c, VideoCue)][0]
    custom = [
        o for o in loaded_vc.outputs if o["output_name"].endswith("_custom_0")
    ][0]
    r = custom["canvas_region"]
    assert r["x"] == pytest.approx(0.333, rel=1e-6)
    assert r["y"] == pytest.approx(0.25, rel=1e-6)
    assert r["width"] == pytest.approx(0.5, rel=1e-6)
    assert r["height"] == pytest.approx(0.4, rel=1e-6)


# ---------------------------------------------------------------------------
# get_all_output_names — tuple shape for custom outputs
# ---------------------------------------------------------------------------

def test_get_all_output_names_returns_custom_suffix():
    """MediaCue.get_all_output_names splits output_name at [:36]/[37:].
    For `<uuid>_custom_0` the second element is 'custom_0'. Downstream
    consumers must tolerate the non-integer form."""
    vc = VideoCue()
    vc.outputs = [
        VideoCueOutput({
            "output_name": ALIAS_NAME,
            "output_geometry": {"x_scale": 1, "y_scale": 1},
        }),
        VideoCueOutput({
            "output_name": CUSTOM_NAME,
            "output_geometry": {"x_scale": 1, "y_scale": 1},
            "canvas_region": {"x": 0, "y": 0, "width": 1, "height": 1},
        }),
    ]
    assert vc.get_all_output_names() == [
        (NODE, "0"),
        (NODE, "custom_0"),
    ]


# ---------------------------------------------------------------------------
# Mappings path — xmlschema decode preserves non-trivial floats
# ---------------------------------------------------------------------------

_MAPPINGS_FIXTURE = """<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">
    <number_of_nodes>1</number_of_nodes>
    <default_audio_input />
    <default_audio_output />
    <default_video_input />
    <default_video_output>{node}_0</default_video_output>
    <default_dmx_input />
    <default_dmx_output />
    <nodes>
        <node>
            <uuid>{node}</uuid>
            <mac>2cf05d21cca3</mac>
            <video>
                <outputs>
                    <output>
                        <id>0</id>
                        <name>alias</name>
                        <mappings>
                            <mapped_to>alias</mapped_to>
                        </mappings>
                    </output>
                    <output>
                        <id>1</id>
                        <name>custom</name>
                        <canvas_region>
                            <x>0.333</x>
                            <y>0.25</y>
                            <width>0.5</width>
                            <height>0.4</height>
                        </canvas_region>
                        <mappings>
                            <mapped_to>custom</mapped_to>
                        </mappings>
                    </output>
                </outputs>
            </video>
        </node>
    </nodes>
    <new_nodes></new_nodes>
</cms:CuemsProjectMappings>
"""


def test_mappings_non_trivial_float_survives_xmlschema_decode():
    """Build a mappings fixture with a non-trivial float region on disk,
    let xmlschema decode it via ProjectMappings, and confirm the values
    land within tolerance. This is the path that the UI will actually read."""
    fixture = TMP_DIR / "test_mappings_nontrivial.xml"
    fixture.write_text(_MAPPINGS_FIXTURE.format(node=NODE), encoding="utf-8")

    m = ProjectMappings(str(fixture))
    outputs = m.processed["nodes"][0]["node"]["video"][0]["outputs"]
    template = next(o for o in outputs if "canvas_region" in o["output"])
    r = template["output"]["canvas_region"]
    assert r["x"] == pytest.approx(0.333, rel=1e-6)
    assert r["y"] == pytest.approx(0.25, rel=1e-6)
    assert r["width"] == pytest.approx(0.5, rel=1e-6)
    assert r["height"] == pytest.approx(0.4, rel=1e-6)
    # Type should be float (via xs:float), not Decimal.
    assert isinstance(r["x"], float)
