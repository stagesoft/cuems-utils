# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""Feature 014 — the four optional ``MediaType`` elements (T001, T002, T003).

``pixel_width``, ``pixel_height``, ``file_size`` and ``file_hash``, all
``minOccurs="0"``. The input document specified three; ``file_hash`` is this
feature's addition (plan.md decision 11, §10).

Three things these tests exist to pin, each of which is a decision rather than
a mechanism:

* **``file_size`` must hold a file larger than 100 GB.** 100 GiB is
  107,374,182,400 bytes, which overflows a 32-bit int, so the type choice is
  load-bearing. ``xs:positiveInteger`` is unbounded in XSD and decodes to an
  arbitrary-precision Python ``int``. This is the test that refuses a future
  "let's make it ``xs:long``".
* **``0`` is not a value.** Absent means unknown; a zero-byte or zero-pixel
  file is not playable media. All three integers share the rule.
* **``file_hash`` is lowercase-only**, matching ``UuidType``'s existing
  ``[a-f0-9]`` pattern. ``md5sum``, ``hashlib`` and ``ffmpeg`` all emit
  lowercase, and accepting uppercase would make the ingestion vocabulary wider
  than the schema's — the same argument ``_Bool`` makes about ``"true"``.
"""

from __future__ import annotations

import pathlib
import re

import pytest

from cuemsutils.xml.schema import get_schema

#: The corpus fixture, used as the document frame. A ``complexType`` cannot
#: validate a fragment — ``is_valid`` on one treats a string as *data to
#: decode* — so every case here goes through the real root element, which is
#: also what a consumer actually does.
FIXTURE = "tests/data/media_block/media_block_showcase.xml"

#: The first cue's ``Media`` block in that fixture, matched so its contents can
#: be swapped per case.
_MEDIA_RE = re.compile(r"(<Media>)(.*?)(</Media>)", re.S)

#: The four elements this feature adds, stripped out to give a clean base.
_BLOCK_RE = re.compile(
    r"<(pixel_width|pixel_height|file_size|file_hash)>[^<]*</\1>|"
    r"<(pixel_width|pixel_height|file_size|file_hash)\s*/>"
)


def _document(extra: str) -> str:
    """The fixture with the first cue's media block replaced by *extra*."""
    text = pathlib.Path(FIXTURE).read_text(encoding="utf-8")
    base = None

    def swap(match):
        nonlocal base
        if base is None:
            base = _BLOCK_RE.sub("", match.group(2))
            return f"{match.group(1)}{base}{extra}{match.group(3)}"
        return match.group(0)

    return _MEDIA_RE.sub(swap, text, count=1)


def _is_valid(extra: str) -> bool:
    return get_schema("script").is_valid(_document(extra))


# --- T001: the block validates, and its absence still validates -------------


def test_a_media_block_with_all_four_elements_validates():
    assert _is_valid(
        "<pixel_width>3840</pixel_width>"
        "<pixel_height>2160</pixel_height>"
        "<file_size>107374182400</file_size>"
        "<file_hash>d41d8cd98f00b204e9800998ecf8427e</file_hash>"
    )


def test_a_media_block_with_none_of_them_still_validates():
    """All four are ``minOccurs="0"`` — every existing project stays valid."""
    assert _is_valid("")


@pytest.mark.parametrize(
    "extra",
    [
        "<pixel_width>1920</pixel_width>",
        "<pixel_width>1920</pixel_width><pixel_height>1080</pixel_height>",
        "<file_size>1</file_size>",
        "<file_hash>d41d8cd98f00b204e9800998ecf8427e</file_hash>",
    ],
    ids=["width-only", "pixel-pair", "size-only", "hash-only"],
)
def test_the_four_are_independently_optional(extra):
    """They come as a *set* by convention, not by schema.

    The input document says so: "A file with only some of them is still valid;
    the engine then probes." So a partial block must not be a schema error —
    the completeness rule lives in the consumer, not here.
    """
    assert _is_valid(extra)


def test_the_fixture_validates_against_the_real_schema():
    """``media_block_showcase.xml`` — one cue with all four, one with none.

    It lives in ``tests/data/media_block/`` rather than in the corpus **on
    purpose**: corpus membership requires a pre-refactor verdict in
    ``outcomes.json``, and a document carrying elements this feature adds
    cannot have one — the pre-feature schema rejects it. See
    ``tests/data/corpus/PROVENANCE.md``.
    """
    assert get_schema("script").is_valid(FIXTURE)


def test_an_empty_element_is_refused():
    """"Never write an empty one" is enforced by the type, not by convention."""
    assert not _is_valid("<pixel_width/>")
    assert not _is_valid("<file_size/>")
    assert not _is_valid("<file_hash/>")


# --- T002: the range, and the refusals --------------------------------------


@pytest.mark.parametrize(
    "value,label",
    [
        ("1", "one byte"),
        ("2147483647", "2^31 - 1, the last 32-bit int"),
        ("2147483648", "2^31, which overflows a 32-bit int"),
        ("107374182400", "100 GiB — the requirement"),
        ("1099511627776", "1 TiB"),
        ("9223372036854775808", "2^63, past a 64-bit signed int"),
    ],
)
def test_file_size_holds_a_file_past_100_gb(value, label):
    """``xs:positiveInteger`` is unbounded; this pins that it is not narrowed.

    100 GiB = 107,374,182,400 bytes. A future change to ``xs:int`` or
    ``xs:long`` would pass the first two cases and fail the rest, which is
    exactly what this parametrisation is for.
    """
    assert _is_valid(f"<file_size>{value}</file_size>"), label


def test_file_size_decodes_to_an_arbitrary_precision_int():
    """Unbounded in the schema *and* unbounded through the decoder."""
    document = _document("<file_size>9223372036854775808</file_size>")
    decoded = get_schema("script").decode(document)
    # ``contents`` keeps the repeated-element wrapper the D5 converter
    # preserves, so the cues are a list under one ``Cue`` key.
    media = decoded["CuemsScript"]["CueList"]["contents"]["Cue"][0]["Media"]
    assert media["file_size"] == 9223372036854775808
    assert isinstance(media["file_size"], int)


@pytest.mark.parametrize("element", ["pixel_width", "pixel_height", "file_size"])
@pytest.mark.parametrize("value", ["0", "-1", "-2147483648", "1.5", "", "lots"])
def test_the_three_integers_refuse_zero_and_everything_non_positive(element, value):
    """``0`` is refused **by design**: absent means unknown, 0 is not a value.

    A zero-byte file is not playable media and a zero-pixel video is not a
    video. If a zero-length file ever needs representing, that is
    ``xs:nonNegativeInteger`` and a decision to take then — not a hedge built
    in now.
    """
    assert not _is_valid(f"<{element}>{value}</{element}>")


# --- T003: the hash ---------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "d41d8cd98f00b204e9800998ecf8427e",  # md5 of the empty string
        "00000000000000000000000000000000",
        "ffffffffffffffffffffffffffffffff",
    ],
)
def test_file_hash_accepts_32_lowercase_hex(value):
    assert _is_valid(f"<file_hash>{value}</file_hash>")


@pytest.mark.parametrize(
    "value,why",
    [
        ("D41D8CD98F00B204E9800998ECF8427E", "uppercase — the decision, not the mechanism"),
        ("d41D8cd98f00b204e9800998ecf8427e", "mixed case"),
        ("d41d8cd98f00b204e9800998ecf8427", "31 characters"),
        ("d41d8cd98f00b204e9800998ecf8427ee", "33 characters"),
        ("d41d8cd98f00b204e9800998ecf8427g", "non-hex character"),
        ("d41d8cd9-8f00-b204-e980-0998ecf8427e", "a uuid-shaped string"),
        ("", "empty"),
    ],
)
def test_file_hash_refuses_everything_else(value, why):
    """Lowercase-only, matching ``UuidType``'s existing ``[a-f0-9]`` pattern.

    The uppercase case is the one that records a *decision*: ``md5sum``,
    ``hashlib`` and ``ffmpeg`` all emit lowercase, and a wider ingestion
    vocabulary than the schema's is a value legal on the wire that can never
    appear in a file — the same argument ``_Bool`` makes about ``"true"``.
    """
    assert not _is_valid(f"<file_hash>{value}</file_hash>"), why


def test_md5_hash_type_is_a_named_type_shaped_like_uuid_type():
    """One declared vocabulary, one house style for a pattern-restricted string."""
    types = get_schema("script").types
    assert "Md5HashType" in types, "the hash needs a named type, not an inline restriction"
    md5, uuid = types["Md5HashType"], types["UuidType"]
    assert md5.base_type.name == uuid.base_type.name  # both restrict xs:string


# --- T006: the writer claim, asserted rather than assumed -------------------


def _written_media(media_fields: dict) -> str:
    """Build a ``Media``, write the document, return its ``<Media>`` text."""
    import tempfile
    from pathlib import Path

    from cuemsutils.cues import CuemsScript

    script, _ = CuemsScript.load_with_report(FIXTURE)
    cue = script['CueList'].contents[0]
    media = cue['Media']
    for key in ('pixel_width', 'pixel_height', 'file_size', 'file_hash'):
        setattr(media, key, None)
    for key, value in media_fields.items():
        setattr(media, key, value)

    out = Path(tempfile.mkdtemp()) / 's.xml'
    script.save(str(out))
    text = out.read_text(encoding='utf-8')
    return text[text.index('<Media>'):text.index('</Media>')]


SCHEMA_ORDER = ['file_name', 'id', 'duration', 'regions',
                'pixel_width', 'pixel_height', 'file_size', 'file_hash']


def test_the_writer_emits_schema_order_whatever_the_assignment_order():
    """plan.md §10.4 — "no writer change is needed on this branch", asserted.

    The spec-driven writer orders by schema position, so the input document's
    ``MediaXmlBuilder`` fix (which wrote keys in dict order) does not apply
    here. That is one of its three `cuems-utils` deliverables dropping out, and
    a dropped deliverable is worth one test rather than a sentence.
    """
    written = _written_media({
        'file_hash': 'd41d8cd98f00b204e9800998ecf8427e',
        'file_size': 107374182400,
        'pixel_height': 2160,
        'pixel_width': 3840,
    })
    positions = [written.index(f'<{name}>') for name in SCHEMA_ORDER]
    assert positions == sorted(positions), written


def test_the_writer_omits_an_absent_field_rather_than_emitting_it_empty():
    """``<pixel_width/>`` fails ``xs:positiveInteger``, so absent must mean absent."""
    written = _written_media({'pixel_width': 1920})
    assert '<pixel_width>1920</pixel_width>' in written
    for absent in ('pixel_height', 'file_size', 'file_hash'):
        assert f'<{absent}' not in written, f'{absent} was emitted: {written}'


def test_a_partial_block_still_round_trips_and_revalidates():
    from cuemsutils.xml.schema import get_schema as _gs

    import tempfile
    from pathlib import Path

    from cuemsutils.cues import CuemsScript

    script, _ = CuemsScript.load_with_report(FIXTURE)
    media = script['CueList'].contents[0]['Media']
    media.file_size = None
    media.file_hash = None
    out = Path(tempfile.mkdtemp()) / 's.xml'
    script.save(str(out))

    assert _gs('script').is_valid(str(out))
    reloaded, _ = CuemsScript.load_with_report(str(out))
    again = reloaded['CueList'].contents[0]['Media']
    assert again.pixel_width == 3840 and again.pixel_height == 2160
    assert again.file_size is None and again.file_hash is None


# --- the setters' own contract ----------------------------------------------


@pytest.mark.parametrize("value", [0, -1, 1.5, "lots", True, False, [], {}])
def test_the_integer_setters_refuse_what_the_schema_would(value):
    """Fail at the assignment that caused it, not at a later save.

    ``True``/``False`` are in the list because ``bool`` is an ``int`` subclass:
    without the explicit guard, ``media.pixel_width = True`` would store 1 — a
    plausible-looking pixel width.
    """
    from cuemsutils.cues.MediaCue import Media

    media = Media()
    for key in ('pixel_width', 'pixel_height', 'file_size'):
        with pytest.raises(ValueError):
            setattr(media, key, value)


def test_the_integer_setters_accept_a_string_of_digits():
    from cuemsutils.cues.MediaCue import Media

    media = Media()
    media.file_size = "107374182400"
    assert media.file_size == 107374182400
    assert isinstance(media.file_size, int)


def test_none_removes_the_key_rather_than_storing_it():
    """Absent means unknown, and that is the only way to say so."""
    from cuemsutils.cues.MediaCue import Media

    media = Media()
    media.pixel_width = 1920
    assert 'pixel_width' in media
    media.pixel_width = None
    assert 'pixel_width' not in media


def test_the_hash_setter_normalises_nothing():
    """An uppercase digest raises rather than being lowercased.

    Silently "fixing" it would leave the object and the document disagreeing
    about what is valid.
    """
    from cuemsutils.cues.MediaCue import Media

    media = Media()
    with pytest.raises(ValueError):
        media.file_hash = "D41D8CD98F00B204E9800998ECF8427E"
    media.file_hash = "d41d8cd98f00b204e9800998ecf8427e"
    assert media.file_hash == "d41d8cd98f00b204e9800998ecf8427e"
