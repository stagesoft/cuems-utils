"""The D14 chain through the public surface alone (T022) — FR-008, SC-002.

    xml -> object -> json -> object -> xml

The same four links ``test_d14_chain.py`` drives through ``XmlReaderWriter``
and ``CuemsParser``, driven instead through ``CuemsScript.load``,
``to_json``/``to_wire``, ``from_json`` and ``save``. **No schema name is passed
anywhere and nothing from ``cuemsutils.xml`` is named** — that is the claim, and
the last test in this file asserts it against this module's own source rather
than trusting the import list to stay clean.

The point of running both legs is that they must agree. Replacing the old one
with this would remove the comparison that makes either meaningful.
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support.capture_goldens import normalize_schema_location
from tests.support.corpus import GOLDEN_ROOT, script_documents
from tests.support.public_api import assert_no_xml_import

#: Scoped to the script documents that reach the write path — the same set the
#: pre-feature chain uses, resolved the same way (a golden exists iff the
#: document round-trips).
CHAIN_DOCS = [
    d for d in script_documents() if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()
]
IDS = [d.relpath for d in CHAIN_DOCS]


@pytest.mark.parametrize("doc", CHAIN_DOCS, ids=IDS)
def test_the_public_chain_writes_byte_identical_xml(doc, tmp_path):
    obj = CuemsScript.load(doc.path)

    rebuilt = CuemsScript.from_json(obj.to_json())
    assert rebuilt == obj

    target = tmp_path / "written.xml"
    rebuilt.save(target)

    produced = normalize_schema_location(target.read_bytes())
    assert produced == (GOLDEN_ROOT / "xml" / f"{doc.slug}.xml").read_bytes()


@pytest.mark.parametrize("doc", CHAIN_DOCS, ids=IDS)
def test_the_json_leg_changes_nothing_the_xml_leg_can_see(doc, tmp_path):
    """Two routes to XML, one result.

    A difference here means the JSON leg loses or reshapes something that
    survives in the object — the class of defect that only ever shows up as
    "the editor saved a different file than the engine did".
    """
    direct = tmp_path / "direct.xml"
    via_json = tmp_path / "via_json.xml"

    obj = CuemsScript.load(doc.path)
    obj.save(direct)
    CuemsScript.from_json(obj.to_json()).save(via_json)

    assert via_json.read_bytes() == direct.read_bytes()


@pytest.mark.parametrize("doc", CHAIN_DOCS, ids=IDS)
def test_the_wire_payload_survives_a_full_round_trip(doc, tmp_path):
    obj = CuemsScript.load(doc.path)
    target = tmp_path / "written.xml"
    obj.save(target)
    assert CuemsScript.load(target).to_wire() == obj.to_wire()


def test_from_json_accepts_what_to_json_produces_at_every_depth(tmp_path):
    doc = CHAIN_DOCS[0]
    obj = CuemsScript.load(doc.path)
    payload = json.loads(obj.to_json())
    assert CuemsScript.from_json(payload).to_wire() == obj.to_wire()


def test_this_module_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
