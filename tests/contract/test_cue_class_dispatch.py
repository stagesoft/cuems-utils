# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T045 — a cue's class selects its Python model (FR-050a, FR-052, SC-012).

Axis D narrows two ``xs:choice`` groups: six cue elements become ``CueList``,
``Cue``, ``ActionCue``, ``FadeCue``, and three cue-output elements become one
``CueOutput``. **The Python classes survive.** ``AudioCue`` is still an
``AudioCue`` when its class is ``audio``, with the same fields, the same
equality and the same hash — which is what keeps ``cuems-engine``'s 30-odd
``isinstance`` and ``singledispatch`` sites working untouched (research R7).

An unknown class is valid (A2) and decodes to the base model rather than
failing, the same way an unknown device class decodes to ``DeviceType``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from xmlschema import XMLSchema11

from cuemsutils.cues.ActionCue import ActionCue
from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.CueList import CueList
from cuemsutils.cues.CueOutput import AudioCueOutput, CueOutput, DmxCueOutput, VideoCueOutput
from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.cues.DmxCue import DmxCue
from cuemsutils.cues.FadeCue import FadeCue
from cuemsutils.cues.MediaCue import MediaCue
from cuemsutils.cues.VideoCue import VideoCue
from cuemsutils.xml.spec import TypeKey, derive

_SCHEMA = (
    Path(__file__).resolve().parents[2]
    / "src" / "cuemsutils" / "xml" / "schemas" / "script.xsd"
)

_COMMON = """
      <autoload>False</autoload>
      <description>d</description>
      <enabled>True</enabled>
      <id>{id}</id>
      <loop>1</loop>
      <name>n</name>
      <offset><CTimecode>00:00:00.000</CTimecode></offset>
      <post_go>pause</post_go>
      <postwait><CTimecode>00:00:00.000</CTimecode></postwait>
      <prewait><CTimecode>00:00:00.000</CTimecode></prewait>
      <target></target>
      <timecode>False</timecode>
      <ui_properties></ui_properties>
"""

_MEDIA = """
      <Media>
        <file_name>f.wav</file_name>
        <id>{media_id}</id>
        <duration><CTimecode>00:00:01.000</CTimecode></duration>
        <regions>
          <Region>
            <id>0</id><loop>1</loop>
            <in_time><CTimecode>00:00:00.000</CTimecode></in_time>
            <out_time><CTimecode>00:00:01.000</CTimecode></out_time>
          </Region>
        </regions>
      </Media>
"""


def _audio_cue(cue_class: str = "audio", with_vol: bool = True) -> str:
    vol = "<master_vol>100</master_vol>" if with_vol else ""
    return f"""    <Cue class="{cue_class}">
{_COMMON.format(id="aaaaaaaa-0000-4000-8000-000000000001")}
{_MEDIA.format(media_id="aaaaaaaa-0000-4000-8000-0000000000a1")}
      <outputs>
        <CueOutput class="audio">
          <output_name>aaaaaaaa-0000-4000-8000-0000000000ff_0</output_name>
          <output_vol>100</output_vol>
          <channels><channel><channel_num>0</channel_num><channel_vol>100</channel_vol></channel></channels>
        </CueOutput>
      </outputs>
      {vol}
    </Cue>
"""


def _video_cue() -> str:
    return f"""    <Cue class="video">
{_COMMON.format(id="bbbbbbbb-0000-4000-8000-000000000002")}
{_MEDIA.format(media_id="bbbbbbbb-0000-4000-8000-0000000000a2")}
      <outputs>
        <CueOutput class="video">
          <output_name>bbbbbbbb-0000-4000-8000-0000000000ff_0</output_name>
          <output_geometry>
            <x_scale>1.0</x_scale><y_scale>1.0</y_scale>
            <corners>
              <top_left><x>0</x><y>0</y></top_left>
              <top_right><x>0</x><y>0</y></top_right>
              <bottom_left><x>0</x><y>0</y></bottom_left>
              <bottom_right><x>0</x><y>0</y></bottom_right>
            </corners>
          </output_geometry>
        </CueOutput>
      </outputs>
      <opacity>100</opacity>
    </Cue>
"""


def _dmx_cue() -> str:
    return f"""    <Cue class="dmx">
{_COMMON.format(id="cccccccc-0000-4000-8000-000000000003")}
      <fadein_time>0.0</fadein_time>
      <fadeout_time>0.0</fadeout_time>
      <outputs>
        <CueOutput class="dmx">
          <output_name>cccccccc-0000-4000-8000-0000000000ff_0</output_name>
        </CueOutput>
      </outputs>
      <DmxScene>
        <id>0</id>
        <DmxUniverse universe_num="0">
          <dmx_channels><DmxChannel><channel>0</channel><value>0</value></DmxChannel></dmx_channels>
          <universe_num>0</universe_num>
        </DmxUniverse>
      </DmxScene>
    </Cue>
"""


def _action_cue(target: str = "ffffffff-0000-4000-8000-000000000006") -> str:
    return f"""    <ActionCue>
{_COMMON.format(id="dddddddd-0000-4000-8000-000000000004")}
      <action_target>{target}</action_target>
      <action_type>play</action_type>
    </ActionCue>
"""


def _fade_cue(target: str = "ffffffff-0000-4000-8000-000000000006") -> str:
    return f"""    <FadeCue>
{_COMMON.format(id="eeeeeeee-0000-4000-8000-000000000005")}
      <action_target>{target}</action_target>
      <action_type>play</action_type>
      <curve_type>linear</curve_type>
      <duration><CTimecode>00:00:02.000</CTimecode></duration>
      <target_value>0</target_value>
    </FadeCue>
"""


def _nested_cuelist() -> str:
    return f"""    <CueList>
{_COMMON.format(id="ffffffff-0000-4000-8000-000000000006")}
      <contents></contents>
    </CueList>
"""


def _document(contents: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<cms:CuemsProject xmlns:cms="https://stagelab.coop/cuems/" doc_version="2">
  <CuemsScript>
    <CueList>
{_COMMON.format(id="00000000-0000-4000-8000-00000000000a")}
      <contents>
{contents}
      </contents>
    </CueList>
    <description>d</description>
    <id>00000000-0000-4000-8000-00000000000b</id>
    <name>n</name>
    <created>2020-01-01T00:00:00.000</created>
    <modified>2020-01-01T00:00:00.000</modified>
    <ui_properties></ui_properties>
  </CuemsScript>
</cms:CuemsProject>
"""


def _write(tmp_path: Path, contents: str) -> Path:
    path = tmp_path / "script.xml"
    path.write_text(_document(contents), encoding="utf-8")
    return path


def _contents(script: CuemsScript) -> list:
    return script["CueList"]["contents"]


def test_the_three_cue_classes_and_three_output_classes_still_import():
    """SC-012's first half: the names consumers hold are still names."""
    assert (AudioCue, VideoCue, DmxCue) == (AudioCue, VideoCue, DmxCue)
    assert issubclass(AudioCueOutput, CueOutput)
    assert issubclass(VideoCueOutput, CueOutput)
    assert issubclass(DmxCueOutput, CueOutput)


def test_a_class_carrying_element_decodes_to_its_own_model(tmp_path):
    path = _write(tmp_path, _audio_cue() + _video_cue() + _dmx_cue())
    script = CuemsScript.load(path)
    cues = _contents(script)
    assert [type(cue).__name__ for cue in cues] == ["AudioCue", "VideoCue", "DmxCue"]
    assert isinstance(cues[0], AudioCue)
    assert isinstance(cues[1], VideoCue)
    assert isinstance(cues[2], DmxCue)
    # The narrower fields survive the fallback-typed element declaration.
    assert cues[0]["master_vol"] == 100
    assert cues[1]["opacity"] == 100


def test_cue_outputs_dispatch_on_the_same_discriminator(tmp_path):
    path = _write(tmp_path, _audio_cue() + _video_cue() + _dmx_cue())
    cues = _contents(CuemsScript.load(path))
    assert isinstance(cues[0]["outputs"][0], AudioCueOutput)
    assert isinstance(cues[1]["outputs"][0], VideoCueOutput)
    assert isinstance(cues[2]["outputs"][0], DmxCueOutput)


def test_equality_and_hashing_answer_as_before(tmp_path):
    """Two loads of one document give equal, equally hashing cues."""
    path = _write(tmp_path, _audio_cue())
    first = _contents(CuemsScript.load(path))[0]
    second = _contents(CuemsScript.load(path))[0]
    assert first == second
    assert hash(first) == hash(second)
    assert len({first, second}) == 1
    # Still unequal to a cue of another class, and still hashable at all —
    # ``CuemsDict.__eq__`` sets ``__hash__`` to ``None`` on a subclass that
    # does not restate it, and an unhashable cue is a TypeError in the engine.
    other = AudioCue({"name": "different"})
    assert first != other


def test_an_unknown_cue_class_decodes_to_the_base_model(tmp_path):
    """A class the registry does not name is valid and falls back (A2, FR-002)."""
    path = _write(tmp_path, _audio_cue(cue_class="lighting", with_vol=False))
    cue = _contents(CuemsScript.load(path))[0]
    assert type(cue) is MediaCue
    assert cue["class"] == "lighting"


def test_an_unknown_output_class_decodes_to_the_base_model(tmp_path):
    body = f"""    <Cue class="audio">
{_COMMON.format(id="aaaaaaaa-0000-4000-8000-000000000001")}
{_MEDIA.format(media_id="aaaaaaaa-0000-4000-8000-0000000000a1")}
      <outputs>
        <CueOutput class="lighting">
          <output_name>aaaaaaaa-0000-4000-8000-0000000000ff_0</output_name>
        </CueOutput>
      </outputs>
      <master_vol>100</master_vol>
    </Cue>
"""
    path = _write(tmp_path, body)
    output = _contents(CuemsScript.load(path))[0]["outputs"][0]
    assert type(output) is CueOutput
    assert output["class"] == "lighting"


def test_action_fade_and_cuelist_are_still_their_own_elements(tmp_path):
    """Cue *kinds*, not hardware classes — no new class adds one (FR-050a)."""
    path = _write(tmp_path, _action_cue() + _fade_cue() + _nested_cuelist())
    cues = _contents(CuemsScript.load(path))
    assert [type(cue).__name__ for cue in cues] == ["ActionCue", "FadeCue", "CueList"]
    assert isinstance(cues[0], ActionCue)
    assert isinstance(cues[1], FadeCue)
    assert isinstance(cues[2], CueList)
    for cue in cues:
        assert "class" not in cue


def test_the_choice_members_are_the_four_the_reshape_leaves(tmp_path):
    """The schema side of the same claim, read from the derivation."""
    choice = derive(TypeKey("script", "CueListContentsType"))
    assert [f.name for f in choice.fields] == ["CueList", "Cue", "ActionCue", "FadeCue"]
    outputs = derive(TypeKey("script", "OutputsType"))
    assert [f.name for f in outputs.fields] == ["CueOutput"]


def test_the_per_class_element_names_are_gone_from_the_schema():
    schema = XMLSchema11(str(_SCHEMA))
    declared = {e.local_name for e in schema.iter_components() if getattr(e, "local_name", None)}
    for retired in ("AudioCue", "VideoCue", "DmxCue",
                    "AudioCueOutput", "VideoCueOutput", "DmxCueOutput"):
        assert retired not in declared, f"{retired} is still a declared element name"


@pytest.mark.parametrize("cue_class,model", [("audio", AudioCue), ("video", VideoCue), ("dmx", DmxCue)])
def test_from_json_dispatches_on_the_same_discriminator(tmp_path, cue_class, model):
    """The editor's ingestion path shares the one dispatch (FR-052)."""
    builders = {"audio": _audio_cue, "video": _video_cue, "dmx": _dmx_cue}
    path = _write(tmp_path, builders[cue_class]())
    wire = CuemsScript.load(path).to_wire()
    again = CuemsScript.from_json(wire)
    assert isinstance(_contents(again)[0], model)
