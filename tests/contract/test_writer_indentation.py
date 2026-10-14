"""Contract C7 (feature 015, S3) — a document this library writes stays readable.

``write_tree`` is the one choke point for every document the package writes,
so indentation is tested once here, against it, rather than once per domain.
Before S3 the writer emitted a single line, so a hand-maintained
``settings.xml`` became unreadable — and un-diffable — after the first UI save.
"""

from __future__ import annotations

import difflib
import os
import stat
import sys
from xml.etree.ElementTree import Element, ElementTree, SubElement, fromstring

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS

DOC = next(d for d in DOCUMENTS if d.relpath == "cuems-utils/fade_showcase.xml")


def _written(tmp_path, tag="w"):
    """The writer's output for the fade-showcase corpus document."""
    obj = rt.read_objects(DOC)
    target = tmp_path / f"{tag}.xml"
    target.write_bytes(rt.write_bytes(DOC, obj))
    return target


def _reload_and_write(doc_path, tmp_path, tag):
    obj = rt.read_objects(DOC, source=doc_path)
    target = tmp_path / f"{tag}.xml"
    target.write_bytes(rt.write_bytes(DOC, obj))
    return target


# --------------------------------------------------------------------------
# FR-070 / SC-011 — indented, line-broken, small diffs
# --------------------------------------------------------------------------


def test_a_written_document_is_indented_and_line_broken(tmp_path):
    written = _written(tmp_path).read_text(encoding="utf-8")
    lines = written.splitlines()

    # The corpus file is hand-authored in the writer's output form (T090),
    # so it is the "equivalent hand-indented form" the contract names.
    hand = DOC.path.read_text(encoding="utf-8").splitlines()
    assert len(lines) > 1
    assert abs(len(lines) - len(hand)) <= 1, (len(lines), len(hand))
    assert any(line.startswith("  ") for line in lines[1:])


def test_a_one_element_change_is_a_small_diff(tmp_path):
    before = _written(tmp_path, "before")
    text = before.read_text(encoding="utf-8")
    assert "<name>bed</name>" in text

    edited = tmp_path / "edited.xml"
    edited.write_text(
        text.replace("<name>bed</name>",
                     "<name>pad</name>"),
        encoding="utf-8",
    )
    after = _reload_and_write(edited, tmp_path, "after")

    diff = [
        line
        for line in difflib.unified_diff(
            text.splitlines(), after.read_text(encoding="utf-8").splitlines(), lineterm=""
        )
        if line[:1] in "+-" and line[:3] not in ("+++", "---")
    ]
    assert diff, "the edit must show up in the diff"
    assert len(diff) <= 3, diff


# --------------------------------------------------------------------------
# FR-071 — idempotence
# --------------------------------------------------------------------------


def test_rewriting_a_written_document_is_byte_identical(tmp_path):
    once = _written(tmp_path, "once")
    twice = _reload_and_write(once, tmp_path, "twice")
    assert twice.read_bytes() == once.read_bytes()


# --------------------------------------------------------------------------
# FR-073 — mixed content is data
# --------------------------------------------------------------------------


def test_indentation_does_not_alter_text_that_is_data(tmp_path):
    """``UiPropertiesType`` (``xs:anyType``) is the one mixed-content type."""
    from cuemsutils.xml.documents import write_tree

    root = Element("ui_properties")
    root.text = "lead"
    child = SubElement(root, "icon")
    child.text = "play"
    child.tail = "trail"
    leaf = SubElement(root, "color")
    leaf.text = " spaced text "
    target = tmp_path / "ui.xml"

    write_tree(ElementTree(root), target)

    back = fromstring(target.read_bytes())
    assert back.text == "lead"
    assert back.find("icon").text == "play"
    assert back.find("icon").tail == "trail"
    assert back.find("color").text == " spaced text "


# --------------------------------------------------------------------------
# FR-072 — what the writer already guaranteed
# --------------------------------------------------------------------------


def test_the_other_writer_guarantees_are_unchanged(tmp_path):
    from cuemsutils.xml.documents import write_tree

    obj = rt.read_objects(DOC)
    scratch = tmp_path / "scratch.xml"
    scratch.write_bytes(rt.write_bytes(DOC, obj))
    tree = ElementTree(fromstring(scratch.read_bytes()))

    target = tmp_path / "doc.xml"
    target.write_text("<old/>")
    os.chmod(target, 0o640)
    write_tree(tree, target)

    raw = target.read_bytes()
    # encoding + declaration
    assert raw.startswith(b"<?xml version='1.0' encoding='utf-8'?>")
    # the cms prefix survives a parse that discarded its declaration
    assert b"<cms:" in raw and b"ns0:" not in raw
    # mode preserved, no temporary left behind
    if sys.platform != "win32":
        assert stat.S_IMODE(os.stat(target).st_mode) == 0o640
    assert [p.name for p in tmp_path.iterdir() if p.name not in ("doc.xml", "scratch.xml")] == []


# --------------------------------------------------------------------------
# FR-070 — one serialization point
# --------------------------------------------------------------------------


def test_only_documents_serializes_an_element_tree():
    """No other module may call ``tree.write(..., xml_declaration=...)``.

    ``cuems-init-node`` once carried its own copy and wrote the
    ``/etc/cuems`` documents on one line; the guard is what stops a fourth
    writer growing back. The frozen legacy tree has no live caller and is
    excluded by name.
    """
    import re
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src" / "cuemsutils"
    offenders = [
        str(p.relative_to(root))
        for p in root.rglob("*.py")
        if p.name not in {"documents.py", "XmlBuilder.py"}
        and re.search(r"xml_declaration\s*=", p.read_text(encoding="utf-8"))
    ]
    assert offenders == [], offenders


def test_init_node_documents_are_indented(tmp_path):
    from cuemsutils.tools.init_node import _serialize
    from cuemsutils.xml.descriptor import generate_settings_example

    data = _serialize(generate_settings_example(), "settings")
    assert data.count(b"\n") > 10 and b"\n  <Settings>" in data
