"""Failure-path preservation (T019) — FR-015a.

``DmxSceneXmlBuilder.build`` wraps its whole body in ``try/except Exception``
and logs the error instead of raising. A DMX scene that fails to serialize
therefore produces **no elements and no exception**: the surrounding document
is written as if the scene were empty.

This is a defect. It is also, right now, behaviour — a show with a bad DMX scene
saves today rather than failing, and changing that is a behaviour change FR-015
forbids here. So it is pinned *before* the builders are replaced, and the
replacement must reproduce it behind one named compatibility behaviour carrying
its removal target (T046), rather than as an ambient ``except Exception`` in the
general path.

What is asserted, per FR-015a:

* it does not raise;
* surrounding data is unaffected;
* something is logged at ERROR, so the failure is not entirely silent.

Log **text** is deliberately not asserted — FR-032 puts log output outside the
byte-identity guarantee, and T060 rewrites these records.
"""

from __future__ import annotations

import logging
from xml.etree.ElementTree import Element, SubElement

from cuemsutils.xml.XmlBuilder import DmxSceneXmlBuilder


class _ExplodingScene:
    """Stands in for a DMX scene whose serialization fails.

    Raising from ``items()`` is the earliest point the builder touches the
    object, so the failure lands inside the ``try`` with nothing yet emitted —
    the worst case, and the one worth pinning.
    """

    def items(self):
        raise RuntimeError("scene serialization failed")


def test_failure_is_swallowed_not_raised():
    tree = Element("root")
    DmxSceneXmlBuilder(_ExplodingScene(), xml_tree=tree).build()


def test_failure_emits_no_elements():
    tree = Element("root")
    DmxSceneXmlBuilder(_ExplodingScene(), xml_tree=tree).build()
    assert list(tree) == []


def test_surrounding_data_is_unaffected():
    """The half of FR-015a that is easy to lose in a rewrite.

    "Does not raise" is only half the behaviour: siblings written before and
    after the failing scene must survive it. A replacement that caught the
    exception but abandoned the parent element would pass a
    ``pytest.raises``-free check and still lose the document.
    """
    tree = Element("root")
    before = SubElement(tree, "before")
    before.text = "kept"

    DmxSceneXmlBuilder(_ExplodingScene(), xml_tree=tree).build()

    after = SubElement(tree, "after")
    after.text = "kept"

    assert [child.tag for child in tree] == ["before", "after"]
    assert [child.text for child in tree] == ["kept", "kept"]


def test_failure_is_logged_at_error(caplog):
    """Not silent — but not asserted word for word.

    The message text is out of scope (FR-032) and T060 rewrites it. What must
    survive is that a failed scene leaves an ERROR record behind.
    """
    with caplog.at_level(logging.ERROR):
        DmxSceneXmlBuilder(_ExplodingScene(), xml_tree=Element("root")).build()
    assert any(r.levelno >= logging.ERROR for r in caplog.records)


def test_a_healthy_scene_still_emits(caplog):
    """The control case.

    Without it, an implementation that swallowed *everything* would pass every
    other test in this file.
    """
    tree = Element("root")
    with caplog.at_level(logging.ERROR):
        DmxSceneXmlBuilder({"id": 0}, xml_tree=tree).build()
    assert [child.tag for child in tree] == ["id"]
    assert not [r for r in caplog.records if r.levelno >= logging.ERROR]
