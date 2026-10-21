# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
"""Stored media dimensions: ``pixel_width``, ``pixel_height``, ``file_size``,
and the file's ``file_md5``.

The node engine used to run ``ffprobe`` for a video file's size on its first
arm since the engine started, under the command lock, so a GO sent right
after a cue selection started up to 400 ms late (ClickUp 869fat84r). The
editor now probes once at upload and stores the values in ``MediaType``, next
to the duration; ``file_size`` (bytes) lets the engine notice a file that was
replaced under the same name.

The elements are optional, appended after ``regions``. ``file_md5`` (D18) identifies the file
unambiguously, for integrity checks; it is the MD5 the upload already carries. ``file_size`` and
``file_md5`` apply to every media type; the pixel size to VideoCues only.

Design: cuems-RELATIONS Plans/2026-10-01-engine-late-go-media-probe.md §3.1, D18.

**Ported by feature 017 (A-4, spec D4) from rc15's version of this file.** That version wrote and
read through the deprecated ``XmlReaderWriter`` / ``CuemsParser``, which bypass T2. This one
writes through ``CuemsScript.save`` (which validates T1 + T2 before writing), reads through
``CuemsScript.load``, and uses ``to_json`` / ``from_json`` for the editor's JSON path. Every test
keeps its name and its assertion, except one:

* **retired**: ``TestFileMd5::test_stored_lowercase``. rc15's setter lowercased an uppercase md5.
  014's ``Md5Type`` is strict and the setter **raises** instead (``Uuid``'s precedent), and every
  released producer lowercases before assigning. Spec FR-003a item 1;
  ``specs/017-release-line-reconciliation/evidence/test-retirements.md``.

Two of these tests are also spec FR-012's public-path proof that rc15's legacy-path edits are not
needed by real usage: ``TestWrite::test_written_in_schema_order_whatever_the_dict_order`` (the four
media children in schema order) and ``TestFileMd5::test_a_number_shaped_md5_survives_the_parser``
(an all-digit md5 stays a ``str``).
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from cuemsutils.cues import AudioCue, CuemsScript, VideoCue
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.errors import SchemaError
from tests.support.capture_goldens import build_generated_script

DIMS = ("pixel_width", "pixel_height", "file_size")
SCHEMA_ORDER = [
    "file_name",
    "id",
    "duration",
    "regions",
    "pixel_width",
    "pixel_height",
    "file_size",
]


def _media(**extra):
    base = {
        "file_name": "f.mov",
        "id": "",
        "duration": "00:00:10.000",
        "regions": [Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})],
    }
    return {**base, **extra}


def _script(media: Media, cue_class=VideoCue) -> CuemsScript:
    """The generated show (a complete, valid project), with *media* on its *cue_class* cue."""
    script = build_generated_script()
    cue = next(c for c in script.cuelist.contents if isinstance(c, cue_class))
    cue.media = media
    return script


def _write(script: CuemsScript, path: Path) -> Path:
    """The public write path: T1 + T2 are checked before anything is written."""
    script.save(str(path))
    return path


def _media_children(path: Path, cue_class=VideoCue) -> list[str]:
    """The children of *cue_class*'s ``<Media>``, in document order."""
    class_value = {VideoCue: "video", AudioCue: "audio"}[cue_class]
    root = ET.parse(path).getroot()
    for cue in root.iter():
        if cue.tag.rsplit("}", 1)[-1] == "Cue" and cue.get("class") == class_value:
            media = next(el for el in cue if el.tag.rsplit("}", 1)[-1] == "Media")
            return [child.tag.rsplit("}", 1)[-1] for child in media]
    raise AssertionError(f"no {class_value} cue in {path}")


def _read(path: Path) -> CuemsScript:
    return CuemsScript.load(str(path))


def _video_media(script):
    return next(c for c in script.cuelist.contents if isinstance(c, VideoCue)).media


def _find_media_dicts(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "Media" and isinstance(value, dict):
                yield value
            else:
                yield from _find_media_dicts(value)
    elif isinstance(node, list):
        for item in node:
            yield from _find_media_dicts(item)


# ---------------------------------------------------------------------------
# Object model
# ---------------------------------------------------------------------------


class TestMediaSetters:
    def test_absent_means_none(self):
        media = Media(_media())
        assert media.pixel_width is None
        assert media.pixel_height is None
        assert media.file_size is None
        assert not any(k in media for k in DIMS)

    def test_ints_and_digit_strings_are_stored_as_int(self):
        media = Media(_media(pixel_width="1920", pixel_height=1080, file_size="4096"))
        assert (media.pixel_width, media.pixel_height, media.file_size) == (1920, 1080, 4096)
        assert all(type(media[k]) is int for k in DIMS)

    def test_none_removes_the_key(self):
        media = Media(_media(pixel_width=1920, pixel_height=1080, file_size=10))
        media.pixel_width = None
        media.file_size = None
        assert "pixel_width" not in media and "file_size" not in media
        assert media.pixel_height == 1080

    @pytest.mark.parametrize("bad", [0, -1, "0", "-5", "abc", "", 1.5, "1.5", True, [1920]])
    def test_invalid_values_are_rejected(self, bad):
        for key in DIMS:
            with pytest.raises(ValueError):
                Media(_media(**{key: bad}))


# ---------------------------------------------------------------------------
# Writing: schema order, no empty element, valid file
# ---------------------------------------------------------------------------


class TestWrite:
    def test_written_in_schema_order_whatever_the_dict_order(self, tmp_path):
        media = Media()
        # Arrival order deliberately scrambled: the dimensions first.
        media.file_size = 5000
        media.pixel_height = 1080
        media.pixel_width = 1920
        media.setter({k: v for k, v in _media().items()})
        path = _write(_script(media), tmp_path / "pixdims_order.xml")
        assert _media_children(path) == SCHEMA_ORDER
        _read(path)  # valid: loads without raising

    def test_a_raw_dict_with_none_values_writes_no_empty_element(self, tmp_path):
        """A Media can carry None for a dimension (the editor strips them, but the
        writer must not depend on it). <pixel_width/> would fail xs:positiveInteger."""
        media = Media(_media())
        dict.__setitem__(media, "pixel_width", None)
        dict.__setitem__(media, "pixel_height", None)
        dict.__setitem__(media, "file_size", None)
        path = _write(_script(media), tmp_path / "pixdims_none.xml")
        assert _media_children(path) == SCHEMA_ORDER[:4]
        _read(path)

    def test_a_project_without_dimensions_is_written_as_before(self, tmp_path):
        path = _write(_script(Media(_media())), tmp_path / "pixdims_absent.xml")
        assert _media_children(path) == SCHEMA_ORDER[:4]
        _read(path)


# ---------------------------------------------------------------------------
# Reading: the XSD and the load path
# ---------------------------------------------------------------------------


class TestRead:
    def test_round_trip_keeps_the_values_as_ints(self, tmp_path):
        media = Media(_media(pixel_width=3840, pixel_height=2160, file_size=123456789))
        path = _write(_script(media), tmp_path / "pixdims_roundtrip.xml")
        loaded = _video_media(_read(path))
        assert loaded.get("pixel_width") == 3840
        assert loaded.get("pixel_height") == 2160
        assert loaded.get("file_size") == 123456789
        assert all(type(loaded.get(k)) is int for k in DIMS)

    def test_written_again_after_reading_is_equivalent(self, tmp_path):
        media = Media(_media(pixel_width=1280, pixel_height=720, file_size=42))
        first = _write(_script(media), tmp_path / "pixdims_rw1.xml")
        second = _write(_read(first), tmp_path / "pixdims_rw2.xml")
        assert _media_children(second) == SCHEMA_ORDER
        assert _video_media(_read(second)) == _video_media(_read(first))

    @pytest.mark.parametrize(
        "element", ["<pixel_width>0</pixel_width>", "<pixel_width>-3</pixel_width>",
                    "<pixel_width>wide</pixel_width>", "<pixel_width/>",
                    "<file_size>0</file_size>"]
    )
    def test_the_schema_rejects_invalid_values(self, tmp_path, element):
        good = _write(_script(Media(_media())), tmp_path / "pixdims_bad_base.xml")
        bad = tmp_path / "pixdims_bad.xml"
        bad.write_text(good.read_text().replace("</regions>", "</regions>" + element, 1))
        with pytest.raises(SchemaError):
            _read(bad)

    def test_the_schema_rejects_them_out_of_order(self, tmp_path):
        good = _write(_script(Media(_media())), tmp_path / "pixdims_misorder_base.xml")
        bad = tmp_path / "pixdims_misorder.xml"
        bad.write_text(
            good.read_text().replace("<regions>", "<pixel_width>10</pixel_width><regions>", 1)
        )
        with pytest.raises(SchemaError):
            _read(bad)

    def test_editor_json_with_dimensions_parses_and_writes(self, tmp_path):
        """The editor's save path: frontend JSON → ``CuemsScript.from_json`` → XML. The
        writer, not the JSON's key order, must decide the order of the elements."""
        media = Media(_media(pixel_width=1920, pixel_height=1080, file_size=99))
        as_json = json.loads(_script(media).to_json())
        # Put the dimensions FIRST in every Media dict that carries them.
        for media_dict in _find_media_dicts(as_json):
            if all(k in media_dict for k in DIMS):
                dims = {k: media_dict.pop(k) for k in DIMS}
                rest = dict(media_dict)
                media_dict.clear()
                media_dict.update({**dims, **rest})
        parsed = CuemsScript.from_json(json.dumps(as_json))
        out = _write(parsed, tmp_path / "pixdims_json_out.xml")
        assert _media_children(out) == SCHEMA_ORDER
        assert _video_media(_read(out)).get("pixel_width") == 1920


# ---------------------------------------------------------------------------
# file_md5 (D18)
# ---------------------------------------------------------------------------

MD5 = "d41d8cd98f00b204e9800998ecf8427e"
FULL_ORDER = SCHEMA_ORDER + ["file_md5"]


class TestFileMd5:
    def test_absent_means_none(self):
        assert Media(_media()).file_md5 is None

    # test_stored_lowercase is RETIRED (017 A-4): see the module docstring.

    def test_none_removes_the_key(self):
        media = Media(_media(file_md5=MD5))
        media.file_md5 = None
        assert "file_md5" not in media

    @pytest.mark.parametrize("bad", ["xyz", MD5[:-1], MD5 + "0", "g" * 32, "", 123, True])
    def test_invalid_values_are_rejected(self, bad):
        with pytest.raises(ValueError):
            Media(_media(file_md5=bad))

    def test_written_last_whatever_the_dict_order(self, tmp_path):
        media = Media()
        media.file_md5 = MD5
        media.file_size = 5000
        media.pixel_height = 1080
        media.pixel_width = 1920
        media.setter(_media())
        path = _write(_script(media), tmp_path / "pixdims_md5_order.xml")
        assert _media_children(path) == FULL_ORDER
        _read(path)

    def test_round_trip_keeps_it_as_str(self, tmp_path):
        media = Media(_media(pixel_width=1920, pixel_height=1080, file_size=7, file_md5=MD5))
        loaded = _video_media(_read(_write(_script(media), tmp_path / "pixdims_md5_rt.xml")))
        assert loaded.get("file_md5") == MD5

    @pytest.mark.parametrize("md5", ["00000000000000000000000000000007",
                                     "12e45678901234567890123456789012"])
    def test_a_number_shaped_md5_survives_the_parser(self, tmp_path, md5):
        """All digits, or digits with one 'e', must not be coerced to int/float on read,
        or the next save no longer validates. On the public path the adapter table
        binds types, and ``Md5Type`` restricts ``xs:string``, so it stays a ``str``."""
        media = Media(_media(file_size=7, file_md5=md5))
        first = _write(_script(media), tmp_path / "pixdims_md5_num1.xml")
        loaded = _read(first)
        assert _video_media(loaded).get("file_md5") == md5
        assert type(_video_media(loaded).get("file_md5")) is str
        _write(loaded, tmp_path / "pixdims_md5_num2.xml")  # saves: still valid
        through_json = CuemsScript.from_json(loaded.to_json())
        assert _video_media(through_json).get("file_md5") == md5

    def test_none_writes_no_element(self, tmp_path):
        media = Media(_media(file_size=7))
        dict.__setitem__(media, "file_md5", None)
        path = _write(_script(media), tmp_path / "pixdims_md5_none.xml")
        assert _media_children(path) == SCHEMA_ORDER[:4] + ["file_size"]
        _read(path)

    @pytest.mark.parametrize("element", ["<file_md5>xyz</file_md5>", f"<file_md5>{MD5.upper()}</file_md5>",
                                         "<file_md5/>", f"<file_md5>{MD5}0</file_md5>"])
    def test_the_schema_rejects_invalid_values(self, tmp_path, element):
        text = _write(_script(Media(_media())), tmp_path / "pixdims_md5_bad_base.xml").read_text()
        bad = tmp_path / "pixdims_md5_bad.xml"
        bad.write_text(text.replace("</regions>", "</regions>" + element, 1))
        with pytest.raises(SchemaError):
            _read(bad)

    def test_an_audio_cue_carries_size_and_md5(self, tmp_path):
        """Size and MD5 apply to every media type (the pixel size does not)."""
        media = Media(_media(file_size=99, file_md5=MD5))
        path = _write(_script(media, cue_class=AudioCue), tmp_path / "pixdims_md5_audio.xml")
        assert _media_children(path, AudioCue) == SCHEMA_ORDER[:4] + ["file_size", "file_md5"]
        _read(path)
