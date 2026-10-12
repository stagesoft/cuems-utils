"""Version steps at the registry level (ITEM E, US6, T099) — research R9,
FR-051d/FR-052.

Isolated from any real schema: none of this feature's own three
transformations exercises an identity step, so the mechanism needs its own
test rather than being left to the first feature that relies on it.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cuemsutils.xml import versioning


def test_an_unregistered_step_is_a_valid_identity():
    schema_name = "scratch_schema_with_no_registered_conversion"
    root = ET.Element("Root")
    ET.SubElement(root, "child").text = "unchanged"
    tree = ET.ElementTree(root)

    steps = versioning.convert(schema_name, tree, 1, 2)

    assert len(steps) == 1
    step = steps[0]
    assert step.from_version == 1 and step.to_version == 2
    assert step.dropped_elements == ()
    assert root.find("child").text == "unchanged"


def test_a_multi_step_walk_runs_every_step_in_order():
    schema_name = "scratch_schema_multi_step"
    calls: list[int] = []

    def _step(version):
        def _apply(root):
            calls.append(version)
            return []
        return _apply

    for v in (1, 2, 3):
        versioning.register_conversion(
            schema_name, v, versioning.Conversion(f"step {v}", _step(v))
        )

    tree = ET.ElementTree(ET.Element("Root"))
    steps = versioning.convert(schema_name, tree, 1, 4)

    assert calls == [1, 2, 3]
    assert [s.from_version for s in steps] == [1, 2, 3]
    assert [s.to_version for s in steps] == [2, 3, 4]


def test_read_version_of_a_marker_less_document_is_1():
    tree = ET.ElementTree(ET.Element("Root"))
    assert versioning.read_version(tree) == 1


def test_read_version_reads_the_declared_attribute():
    root = ET.Element("Root")
    root.set(versioning.DOC_VERSION_ATTR, "7")
    assert versioning.read_version(ET.ElementTree(root)) == 7


def test_document_too_new_error_names_schema_and_both_versions():
    exc = versioning.DocumentTooNewError("script", 5, 2)
    assert exc.schema_name == "script"
    assert exc.version == 5
    assert exc.current == 2
    message = str(exc)
    assert "5" in message and "2" in message and "script" in message
