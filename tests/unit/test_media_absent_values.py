# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""What a loaded ``Media`` answers for its four stored values (feature 017, A-6, X-4).

``cuems-engine``'s reconciliation asked (its pre-spec, X-4 / R-1): when a version-2 media block
carries none of ``pixel_width`` / ``pixel_height`` / ``file_size`` / ``file_md5``, what does the
library hand back? Its "missing → probe" branch needed to know whether to test for ``None`` or for
an internal sentinel.

**The answer is ``None``, measured and pinned here**:
- on a loaded document without the values, ``.get(k)`` and the attribute are ``None``, the key is
  not in the mapping, and ``to_wire()`` omits it;
- with the values, they come back as ``int``, ``int``, ``int``, ``str``, with
  ``file_size`` 107374182400 (100 GiB, past 32 bits) intact;
- the internal ``Unset`` default is never returned.
"""
import json

import pytest

from cuemsutils.cues import CuemsScript, VideoCue
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.helpers import Unset
from tests.support.capture_goldens import build_generated_script

KEYS = ("pixel_width", "pixel_height", "file_size", "file_md5")
VALUES = {"pixel_width": 1920, "pixel_height": 1080, "file_size": 107374182400,
          "file_md5": "d41d8cd98f00b204e9800998ecf8427e"}


def _loaded_media(tmp_path, **values):
    script = build_generated_script()
    video = next(c for c in script.cuelist.contents if isinstance(c, VideoCue))
    video.media = Media({
        "file_name": "f.mov", "id": "", "duration": "00:00:10.000",
        "regions": [Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})],
        **values,
    })
    path = tmp_path / "script.xml"
    script.save(str(path))
    loaded = CuemsScript.load(str(path))
    return next(c for c in loaded.cuelist.contents if isinstance(c, VideoCue))


def _media_wire(cue):
    """The ``Media`` mapping inside the cue's wire projection, wherever it sits."""
    def find(node):
        if isinstance(node, dict):
            if isinstance(node.get("Media"), dict):
                return node["Media"]
            for value in node.values():
                found = find(value)
                if found is not None:
                    return found
        elif isinstance(node, list):
            for value in node:
                found = find(value)
                if found is not None:
                    return found
        return None

    wire = cue.to_wire() if hasattr(cue, "to_wire") else json.loads(json.dumps(cue))
    media = find(wire)
    assert media is not None, "no Media in the cue's wire projection"
    return media


@pytest.mark.parametrize("key", KEYS)
def test_absent_is_none_by_get_and_by_attribute(tmp_path, key):
    media = _loaded_media(tmp_path).media
    assert media.get(key) is None
    assert getattr(media, key) is None
    assert media.get(key) is not Unset and getattr(media, key) is not Unset


@pytest.mark.parametrize("key", KEYS)
def test_absent_is_not_a_key_and_is_omitted_from_the_wire(tmp_path, key):
    cue = _loaded_media(tmp_path)
    assert key not in cue.media
    assert key not in _media_wire(cue)


def test_present_values_come_back_typed(tmp_path):
    media = _loaded_media(tmp_path, **VALUES).media
    assert [type(media.get(k)) for k in KEYS] == [int, int, int, str]
    assert [getattr(media, k) for k in KEYS] == [VALUES[k] for k in KEYS]
    assert media.file_size == 107374182400  # 100 GiB: unbounded, not a 32-bit int


def test_present_values_are_on_the_wire(tmp_path):
    cue = _loaded_media(tmp_path, **VALUES)
    wire = _media_wire(cue)
    assert {k: wire[k] for k in KEYS} == VALUES
