# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
# SPDX-FileContributor: Ion Reguera <ion@stagelab.coop>
"""Stored media dimensions: ``pixel_width``, ``pixel_height``, ``file_size``.

The node engine used to run ``ffprobe`` for a video file's size on its first
arm since the engine started, under the command lock, so a GO sent right
after a cue selection started up to 400 ms late (ClickUp 869fat84r). The
editor now probes once at upload and stores the values in ``MediaType``, next
to the duration; ``file_size`` (bytes) lets the engine notice a file that was
replaced under the same name.

The three elements are optional, appended after ``regions``. Two paths have to
hold, and they are tested separately because they share no code:

* the object model (``Media``'s setters), used by code that builds a Media;
* the parse path (``CuemsParser`` / ``XmlReaderWriter``), which assigns keys
  raw and never calls the setters, so validity and order there come from the
  XSD and from ``MediaXmlBuilder``.

Design: cuems-RELATIONS Plans/2026-10-01-engine-late-go-media-probe.md §3.1.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pytest

from cuemsutils.cues import CueList, CuemsScript, VideoCue
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.xml import XmlReaderWriter
from cuemsutils.xml.Parsers import CuemsParser

TMP_DIR = Path(__file__).parent.parent / "tmp"
TMP_DIR.mkdir(exist_ok=True)

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


def _script(media: Media) -> CuemsScript:
    vc = VideoCue({"Media": media, "ui_properties": {"warning": None}})
    script = CuemsScript({"CueList": CueList({"contents": [vc]})})
    script.name = "pixel dimensions"
    now = datetime.now(timezone.utc).isoformat()
    script.created = now
    script.modified = now
    return script


def _write(script: CuemsScript, name: str) -> Path:
    path = TMP_DIR / name
    writer = XmlReaderWriter(schema_name="script", xmlfile=str(path))
    writer.write_from_object(script)
    return path


def _media_children(path: Path) -> list[str]:
    root = ET.parse(path).getroot()
    media = next(el for el in root.iter() if el.tag.rsplit("}", 1)[-1] == "Media")
    return [child.tag.rsplit("}", 1)[-1] for child in media]


def _read(path: Path):
    return XmlReaderWriter(schema_name="script", xmlfile=str(path)).read_to_objects()


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


def _validate(path: Path):
    return XmlReaderWriter(schema_name="script", xmlfile=str(path)).validate()


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
    def test_written_in_schema_order_whatever_the_dict_order(self):
        media = Media()
        # Arrival order deliberately scrambled: the dimensions first.
        media.file_size = 5000
        media.pixel_height = 1080
        media.pixel_width = 1920
        media.setter({k: v for k, v in _media().items()})
        path = _write(_script(media), "pixdims_order.xml")
        assert _media_children(path) == SCHEMA_ORDER
        assert _validate(path) is None

    def test_a_raw_dict_with_none_values_writes_no_empty_element(self):
        """The parse path assigns keys raw: a Media can carry None for a
        dimension (the editor strips them, but the writer must not depend on
        it). <pixel_width/> would fail xs:positiveInteger."""
        media = Media(_media())
        dict.__setitem__(media, "pixel_width", None)
        dict.__setitem__(media, "pixel_height", None)
        dict.__setitem__(media, "file_size", None)
        path = _write(_script(media), "pixdims_none.xml")
        assert _media_children(path) == SCHEMA_ORDER[:4]
        assert _validate(path) is None

    def test_a_project_without_dimensions_is_written_as_before(self):
        path = _write(_script(Media(_media())), "pixdims_absent.xml")
        assert _media_children(path) == SCHEMA_ORDER[:4]
        assert _validate(path) is None


# ---------------------------------------------------------------------------
# Reading: the XSD and the parse path
# ---------------------------------------------------------------------------


class TestRead:
    def test_round_trip_keeps_the_values_as_ints(self):
        media = Media(_media(pixel_width=3840, pixel_height=2160, file_size=123456789))
        path = _write(_script(media), "pixdims_roundtrip.xml")
        loaded = _video_media(_read(path))
        assert loaded.get("pixel_width") == 3840
        assert loaded.get("pixel_height") == 2160
        assert loaded.get("file_size") == 123456789
        assert all(type(loaded.get(k)) is int for k in DIMS)

    def test_written_again_after_reading_is_equivalent(self):
        media = Media(_media(pixel_width=1280, pixel_height=720, file_size=42))
        first = _write(_script(media), "pixdims_rw1.xml")
        second = _write(_read(first), "pixdims_rw2.xml")
        assert _media_children(second) == SCHEMA_ORDER
        assert _video_media(_read(second)) == _video_media(_read(first))

    @pytest.mark.parametrize(
        "element", ["<pixel_width>0</pixel_width>", "<pixel_width>-3</pixel_width>",
                    "<pixel_width>wide</pixel_width>", "<pixel_width/>",
                    "<file_size>0</file_size>"]
    )
    def test_the_schema_rejects_invalid_values(self, element):
        good = _write(_script(Media(_media())), "pixdims_bad_base.xml")
        text = good.read_text()
        bad = TMP_DIR / "pixdims_bad.xml"
        bad.write_text(text.replace("</regions>", "</regions>" + element, 1))
        with pytest.raises(Exception):
            _validate(bad)

    def test_the_schema_rejects_them_out_of_order(self):
        good = _write(_script(Media(_media())), "pixdims_misorder_base.xml")
        text = good.read_text()
        bad = TMP_DIR / "pixdims_misorder.xml"
        bad.write_text(text.replace("<regions>", "<pixel_width>10</pixel_width><regions>", 1))
        with pytest.raises(Exception):
            _validate(bad)

    def test_editor_json_with_dimensions_parses_and_writes(self):
        """The editor's save path: frontend JSON -> CuemsParser -> XML. The
        parser never calls the setters, so this is the path that matters for
        order and types."""
        media = Media(_media(pixel_width=1920, pixel_height=1080, file_size=99))
        path = _write(_script(media), "pixdims_json_base.xml")
        as_json = XmlReaderWriter(schema_name="script", xmlfile=str(path)).read()
        # Put the dimensions FIRST in the Media dict: the writer, not the
        # arrival order, must decide the order.
        for media_dict in _find_media_dicts(as_json):
            dims = {k: media_dict.pop(k) for k in DIMS}
            rest = dict(media_dict)
            media_dict.clear()
            media_dict.update({**dims, **rest})
        parsed = CuemsParser(as_json).parse()
        out = _write(parsed, "pixdims_json_out.xml")
        assert _media_children(out) == SCHEMA_ORDER
        assert _validate(out) is None
        assert _video_media(_read(out)).get("pixel_width") == 1920
