"""Contract C1 (T013) — written XML is byte-identical.

The refactor's primary evidence on the write side. Every assertion here passes
*before* the engine exists, by construction, and must keep passing after the
swap; that inversion is deliberate and is recorded in `plan.md`'s Complexity
Tracking.

Scope note: only the ``script`` schema has a working write path today. The four
config classes are read-only — building XML from a settings dict raises
``AttributeError`` inside ``XmlBuilder`` — so their byte-identity contract is
C2, the read dict, and only that. ``test_write_path_scope`` pins which documents
are in which group, so the scope cannot narrow without a failure.
"""

from __future__ import annotations

import json
import re

import pytest

from tests.support import roundtrip as rt
from tests.support.capture_goldens import SCHEMA_PATH_PLACEHOLDER
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

WRITABLE = [d for d in DOCUMENTS if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()]
IDS = [d.relpath for d in WRITABLE]


def _outcomes():
    return json.loads((GOLDEN_ROOT / "outcomes.json").read_text())


@pytest.mark.parametrize("doc", WRITABLE, ids=IDS)
def test_written_xml_is_byte_identical(doc):
    """The contract itself: ``write(load(doc))`` equals the golden, exactly."""
    produced = rt.write_bytes(doc, rt.read_objects(doc))
    golden = rt.golden_bytes(f"xml/{doc.slug}.xml")
    assert produced == golden, (
        f"{doc.relpath}: written bytes differ from the golden. The engine is "
        f"wrong, not the golden (FR-021)."
    )


def test_generated_script_is_byte_identical():
    """The generated document carries the cue-type breadth (T012).

    Three vendored documents reach the write path; this one exercises audio,
    video, dmx, action and fade cues in a single file.
    """
    doc = next(d for d in DOCUMENTS if d.schema == "script")
    produced = rt.normalize_uuids(rt.write_bytes(doc, rt.build_generated_script()))
    assert produced == rt.golden_bytes("generated/create_script.xml")


# --- the enumerated properties C1 covers ---------------------------------
# Stated as separate assertions rather than left to the reader, so that a
# regression names the property it broke instead of dumping two files.

ALL_XML = [f"xml/{d.slug}.xml" for d in WRITABLE] + ["generated/create_script.xml"]


@pytest.mark.parametrize("golden", ALL_XML)
def test_xml_declaration_spelling(golden):
    """stdlib ElementTree's spelling: **single** quotes, then a newline.

    ``lxml`` writes double quotes. This assertion is what makes "the serializer
    is frozen" (R10) a test rather than a comment.
    """
    raw = rt.golden_bytes(golden)
    assert raw.startswith(b"<?xml version='1.0' encoding='utf-8'?>\n")


@pytest.mark.parametrize("golden", ALL_XML)
def test_no_trailing_newline(golden):
    assert not rt.golden_bytes(golden).endswith(b"\n")


@pytest.mark.parametrize("golden", ALL_XML)
def test_no_indentation(golden):
    """One line after the declaration — no pretty-printing anywhere."""
    body = rt.golden_bytes(golden).split(b"\n", 1)[1]
    assert b"\n" not in body
    assert b"  <" not in body


@pytest.mark.parametrize("golden", ALL_XML)
def test_empty_elements_are_self_closed_with_a_space(golden):
    """``<tag />``, not ``<tag/>`` and not ``<tag></tag>``.

    Asserted on the spelling rather than on a named tag: which elements happen
    to be empty differs per document, but the spelling is the serializer's and
    must be uniform.
    """
    raw = rt.golden_bytes(golden)
    assert re.search(rb"<[\w:]+ />", raw), "no self-closed element to check"
    assert not re.search(rb"<[\w:]+/>", raw), "found <tag/> without the space"
    assert not re.search(rb"<([\w:]+)( [^>]*)?></\1>", raw), "found <tag></tag>"


@pytest.mark.parametrize("golden", ALL_XML)
def test_root_carries_schema_location(golden):
    raw = rt.golden_bytes(golden)
    assert b'xsi:schemaLocation="https://stagelab.coop/cuems/ ' in raw


@pytest.mark.parametrize("golden", ALL_XML)
def test_schema_location_absolute_path_is_the_only_normalization(golden):
    """FR-010b — one carve-out, and it is visible.

    The written ``schemaLocation`` embeds the *writing machine's* absolute path
    to the ``.xsd`` (F24), so an un-normalized golden would be machine-specific
    and could never be compared in CI. Every other byte is compared as-is; this
    asserts the placeholder is present and that no raw absolute path leaked in
    beside it.
    """
    raw = rt.golden_bytes(golden)
    assert SCHEMA_PATH_PLACEHOLDER.encode() in raw
    assert b"/disk/" not in raw and b"/home/" not in raw
    assert b"site-packages" not in raw


@pytest.mark.parametrize("golden", ALL_XML)
def test_encoding_is_literal_utf8_never_character_references(golden):
    """FR-010a — non-ASCII stays as UTF-8 bytes.

    Numeric character references would round-trip through a parser identically
    and compare equal at the object level, while changing every byte. C1 is the
    only contract that can see the difference.
    """
    raw = rt.golden_bytes(golden)
    assert not re.search(rb"&#\d+;", raw)
    assert not re.search(rb"&#x[0-9a-fA-F]+;", raw)
    raw.decode("utf-8")  # raises if the bytes are not valid UTF-8


def test_corpus_contains_non_ascii_so_the_encoding_rule_is_load_bearing():
    """Otherwise the previous test asserts nothing.

    A rule about non-ASCII encoding proves nothing on an all-ASCII corpus, and
    a contract that cannot fail is not a contract.
    """
    non_ascii = [
        d.relpath
        for d in DOCUMENTS
        if any(b > 0x7F for b in d.path.read_bytes())
    ]
    assert non_ascii, "no corpus document contains non-ASCII content"


def test_write_path_scope_is_pinned():
    """Which documents the write path accepts today — the whole list.

    If a config document suddenly becomes writable, or a script document stops
    being, that is a behaviour change (FR-015) and it surfaces here rather than
    as a quietly shrinking parametrisation.
    """
    outcomes = _outcomes()
    writable = sorted(
        rel
        for rel, rec in outcomes.items()
        if rec.get("write", {}).get("ok") and rec["category"] != "generated"
    )
    assert writable == [
        "cuems-editor/script_minimal.xml",
        "cuems-engine/projects/complex_test/script.xml",
        "cuems-engine/projects/empty_test/script.xml",
        "cuems-utils/fade_showcase.xml",
        "cuems-utils/unicode_showcase.xml",
    ]


def test_config_documents_still_fail_to_write():
    """The read-only config path, pinned as the behaviour it is.

    Not a defect to fix here: making these writable would be a behaviour change,
    and FR-015 forbids one. Feature 006 owns it.
    """
    outcomes = _outcomes()
    for rel, rec in outcomes.items():
        if rec["schema"] in ("settings", "network_map", "project_settings"):
            if rec["read"]["ok"] and "write" in rec:
                assert not rec["write"]["ok"]
                assert rec["write"]["error_type"] == "AttributeError"
