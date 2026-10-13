"""G5, T034 — ``_settings_1_to_2`` addresses both player shapes (research R7).

The step must drop ``audio_cards``/``universes`` wherever they are found:
under the pre-013 flat path (``audioplayer``/``dmxplayer``) and under 013's
reshaped predicate path (``players/player[@class='…']``) — and stay
idempotent when neither is present.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from cuemsutils.xml.versioning import _settings_1_to_2

_FLAT_FRAGMENT = """
<CuemsSettings>
  <Settings>
    <node>
      <audioplayer>
        <audio_cards>1</audio_cards>
      </audioplayer>
      <dmxplayer>
        <universes>2</universes>
      </dmxplayer>
    </node>
  </Settings>
</CuemsSettings>
"""

_RESHAPED_FRAGMENT = """
<CuemsSettings>
  <Settings>
    <node>
      <players>
        <player class="audio">
          <audio_cards>1</audio_cards>
        </player>
        <player class="dmx">
          <universes>2</universes>
        </player>
      </players>
    </node>
  </Settings>
</CuemsSettings>
"""

_NEITHER_FRAGMENT = """
<CuemsSettings>
  <Settings>
    <node>
      <players>
        <player class="audio"><path>/usr/bin/x</path></player>
      </players>
    </node>
  </Settings>
</CuemsSettings>
"""


def test_drops_the_flat_shape():
    root = ET.fromstring(_FLAT_FRAGMENT)
    dropped = _settings_1_to_2(root)

    assert root.find("Settings/node/audioplayer/audio_cards") is None
    assert root.find("Settings/node/dmxplayer/universes") is None
    assert sorted(dropped) == sorted([
        "audioplayer/audio_cards",
        "dmxplayer/universes",
    ])


def test_drops_the_reshaped_predicate_shape():
    root = ET.fromstring(_RESHAPED_FRAGMENT)
    dropped = _settings_1_to_2(root)

    assert root.find("Settings/node/players/player[@class='audio']/audio_cards") is None
    assert root.find("Settings/node/players/player[@class='dmx']/universes") is None
    assert sorted(dropped) == sorted([
        "players/player[@class='audio']/audio_cards",
        "players/player[@class='dmx']/universes",
    ])


def test_idempotent_when_neither_shape_carries_the_counts():
    root = ET.fromstring(_NEITHER_FRAGMENT)
    dropped = _settings_1_to_2(root)

    assert dropped == []


def test_idempotent_on_a_second_run_of_the_flat_shape():
    root = ET.fromstring(_FLAT_FRAGMENT)
    _settings_1_to_2(root)
    second = _settings_1_to_2(root)

    assert second == []


def test_no_node_section_returns_no_drops():
    root = ET.fromstring("<Settings></Settings>")
    assert _settings_1_to_2(root) == []
