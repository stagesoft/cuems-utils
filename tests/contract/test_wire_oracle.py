"""The round-trip oracle (T004) — contracts §W1a, data-model.md §6.

``encode_wire`` is a **direct** object walk, not a round trip through XML
(plan.md's measured 33.99 ms vs 16.95 ms finding is why). That means nothing
proves it produces the *same* dict a round trip would, unless something
checks — so this test builds the oracle the slow way, once per corpus script
document, and asserts the fast path agrees.

``Mapper('script').encode_wire(obj) == schema.to_dict(build_document(obj))``

The schema is bound at construction and ``spec`` is resolved from the
object's class when omitted (data-model.md §6) — every call site in this
feature omits it, so this test does too.
"""

from __future__ import annotations

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import GOLDEN_ROOT, script_documents

#: Scoped to documents that actually reach the object layer. Nine of the
#: fourteen ``script_documents()`` are pinned as ``to_objects: error`` by
#: design (fragments, namespace typos, the two ``legacy/`` output-name
#: revisions — see PROVENANCE.md); ``encode_wire`` has no object to encode
#: for them. The same filter ``test_d14_chain.py`` uses: a written XML
#: golden exists only for documents that reached the object layer *and*
#: the write layer.
SCRIPT_DOCS = [
    d for d in script_documents() if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()
]
IDS = [d.relpath for d in SCRIPT_DOCS]

#: The written tree carries ``xsi:schemaLocation``; ``encode_wire`` never
#: does (T009 — the projection omits it from the start, contracts §W4). Not
#: part of the oracle claim, which is about the fields the schema describes.
SCHEMA_LOCATION_KEY = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"


def _slow_oracle(doc, obj) -> dict:
    """``object -> tree -> to_dict`` — the round trip ``encode_wire`` replaces."""
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

    reader = XmlReaderWriter(
        schema_name=doc.schema, xmlfile="/dev/null", xml_root_tag="CuemsProject"
    )
    tree = reader.build_xml_from_object(obj)
    decoded = reader.schema_object.to_dict(
        tree, validation="strict", strip_namespaces=False
    )
    return {k: v for k, v in decoded.items() if k != SCHEMA_LOCATION_KEY}


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_encode_wire_matches_the_round_trip_oracle(doc):
    from cuemsutils.xml.mapper import Mapper

    obj = rt.read_objects(doc)
    fast = Mapper("script").encode_wire(obj)
    slow = _slow_oracle(doc, obj)

    diffs = rt.wire_diff(fast, slow)
    assert not diffs, "encode_wire disagrees with the round-trip oracle:\n  " + "\n  ".join(
        diffs
    )


def test_encode_wire_signature_takes_an_optional_spec():
    """The pinned signature (data-model.md §6): ``spec`` is optional, and
    every call site in this feature omits it."""
    import inspect

    from cuemsutils.xml.mapper import Mapper

    sig = inspect.signature(Mapper.encode_wire)
    params = list(sig.parameters)
    assert params[:2] == ["self", "obj"]
    assert "spec" in sig.parameters
    assert sig.parameters["spec"].default is None
