# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>

"""Media cues without a usable media block (ClickUp 869fej07m).

Two readers of a cue's media, two behaviours, pinned here:

* ``CueList.get_media`` (editor path: update, new, duplicate, relink)
  - a media block without a file (what a client that dropped the block
    produces: an empty ``Media`` object) **raises** a named ``ValueError``.
    It used to raise a bare ``KeyError 'file_name'`` from inside a
    ``hasattr`` guard; silently skipping instead would let the save write an
    empty ``<Media/>`` and lose the cue's media for good;
  - no media object at all (``None``: what an empty ``<Media/>`` or a JSON
    ``Media: null`` decodes to) is **skipped with a warning**, so legacy
    projects stay listable and duplicable.
* ``CuemsScript.get_own_media`` (engine path, every node, every load)
  **never raises**: both shapes are logged and left out, the project still
  loads and that cue fails at arm, locally, as it always did for ``<Media/>``.

Shapes are built the way the decoders build them: ``dict.__setitem__`` for
the raw ``None`` (``Parsers.py`` assigns an empty element as ``None``),
``set_Media(None)`` / ``ensure_items`` for the empty ``Media`` object.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cuemsutils.cues import AudioCue, CueList, CuemsScript, VideoCue
from cuemsutils.cues.MediaCue import Media, MediaCue


def _uuid() -> str:
    return str(uuid.uuid4())


def _media(**over):
    base = {"file_name": "a.wav", "id": _uuid(), "duration": "00:00:01.000", "regions": []}
    base.update(over)
    return Media(base)


def _audio(name="A", media=_media, **fields):
    init = {"id": _uuid(), "name": name}
    if media is not None:
        init["Media"] = media() if callable(media) else media
    init.update(fields)
    return AudioCue(init)


def _video(name="V"):
    return VideoCue({"id": _uuid(), "name": name, "Media": _media(file_name="v.mov")})


def _with_raw_media(cue, value):
    """Bypass the property setter: the XML/JSON decoders store the raw value."""
    dict.__setitem__(cue, "Media", value)
    return cue


def _cuelist(*cues):
    return CueList({"id": _uuid(), "contents": list(cues)})


# ─── MediaCue.media_status ────────────────────────────────────────────────


class TestMediaStatus:
    def test_ok(self):
        state, name = _audio().media_status()
        assert (state, name) == ("ok", "a.wav")

    def test_none_object(self):
        assert _with_raw_media(_audio(), None).media_status() == ("none", None)

    def test_empty_media_object_is_invalid(self):
        cue = _audio()
        cue.media = None  # set_Media wraps it: Media(None) -> empty object
        assert isinstance(cue.media, Media)
        assert cue.media_status() == ("invalid", None)

    def test_missing_file_name_key_is_invalid(self):
        cue = _audio()
        dict.__delitem__(cue.media, "file_name")
        assert cue.media_status() == ("invalid", None)

    @pytest.mark.parametrize("empty", ["", None])
    def test_empty_file_name_is_invalid(self, empty):
        cue = _audio()
        dict.__setitem__(cue.media, "file_name", empty)
        assert cue.media_status() == ("invalid", None)

    def test_missing_id_key_is_invalid(self):
        cue = _audio()
        dict.__delitem__(cue.media, "id")
        assert cue.media_status() == ("invalid", None)

    def test_empty_id_is_ok(self):
        """The dummy scripts in this suite use id '' — only a missing key is a defect."""
        assert _audio(media=lambda: _media(id=""))\
            .media_status() == ("ok", "a.wav")

    def test_never_touches_the_raising_property(self):
        cue = _audio()
        cue.media = None
        with pytest.raises(KeyError):
            _ = cue.media.file_name  # the property still raises; status must not
        assert cue.media_status()[0] == "invalid"


# ─── CueList.get_media (editor path) ──────────────────────────────────────


class TestGetMedia:
    def test_collects_names_recursively(self):
        a, v = _audio("A1"), _video("V1")
        inner = _cuelist(v)
        got = _cuelist(a, inner).get_media()
        assert {str(k): list(val.values())[0] for k, val in got.items()} == {
            str(a.id): "a.wav",
            str(v.id): "v.mov",
        }

    def test_invalid_media_object_raises_naming_the_cue(self):
        bad = _audio("Intro")
        bad.media = None
        with pytest.raises(ValueError) as e:
            _cuelist(_audio("ok"), bad).get_media()
        assert "Intro" in str(e.value) and str(bad.id) in str(e.value)
        assert "no media file" in str(e.value)

    def test_missing_file_name_key_raises(self):
        bad = _audio("B")
        dict.__delitem__(bad.media, "file_name")
        with pytest.raises(ValueError):
            _cuelist(bad).get_media()

    def test_missing_id_key_raises(self):
        bad = _audio("B")
        dict.__delitem__(bad.media, "id")
        with pytest.raises(ValueError):
            _cuelist(bad).get_media()

    def test_none_media_is_skipped_with_a_warning(self):
        """Legacy <Media/>: the other cues are still listed, nothing raises."""
        legacy = _with_raw_media(_audio("Old"), None)
        good = _audio("A1")
        with patch("cuemsutils.cues.CueList.Logger") as log:
            got = _cuelist(legacy, good).get_media()
        assert set(map(str, got)) == {str(good.id)}
        assert log.warning.called
        assert "Old" in log.warning.call_args.args[0]

    def test_nested_invalid_also_raises(self):
        bad = _audio("Deep")
        bad.media = None
        with pytest.raises(ValueError):
            _cuelist(_audio("A"), _cuelist(bad)).get_media()


# ─── CuemsScript.get_own_media (engine path) ──────────────────────────────


def _script(*cues):
    return CuemsScript({"id": _uuid(), "name": "s", "CueList": _cuelist(*cues)})


_CONFIG = SimpleNamespace(node_conf={"uuid": "4b9b5a1e-0000-4000-8000-000000000001"})


@pytest.fixture
def every_cue_is_local():
    with patch.object(MediaCue, "localize_cue", lambda self, node_id: setattr(self, "_local", True)):
        yield


class TestGetOwnMedia:
    def test_ok_cues_listed(self, every_cue_is_local):
        a, v = _audio("A1"), _video("V1")
        got = _script(a, v).get_own_media(_CONFIG)
        assert {str(k): val for k, val in got.items()} == {str(a.id): "a.wav", str(v.id): "v.mov"}

    @pytest.mark.parametrize("shape", ["none", "invalid"])
    def test_never_raises_logs_and_skips(self, every_cue_is_local, shape):
        bad = _audio("Broken")
        if shape == "none":
            _with_raw_media(bad, None)
        else:
            bad.media = None
        good = _audio("A1")
        with patch("cuemsutils.cues.CuemsScript.Logger") as log:
            got = _script(bad, good, _cuelist(_video("V"))).get_own_media(_CONFIG)
        assert str(good.id) in map(str, got) and str(bad.id) not in map(str, got)
        assert len(got) == 2  # good + nested video
        msgs = [c.args[0] for c in log.error.call_args_list]
        assert any("Broken" in m and str(bad.id) in m and shape in m for m in msgs)

    def test_get_own_media_filenames_still_works(self, every_cue_is_local):
        bad = _with_raw_media(_audio("Old"), None)
        names = _script(bad, _audio("A1")).get_own_media_filenames(_CONFIG)
        assert names == ["a.wav"]
