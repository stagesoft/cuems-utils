"""The D14 chain (T016) — contract C4, and this feature's primary gate.

    xml -> object -> json -> object -> xml

**Every intermediate is compared against its golden, not only the endpoints.**
That is the whole design of the test: two independent errors that cancel at the
ends are the failure mode a round-trip assertion is blindest to, and the chain
has four places for them to hide.

This file is written against **pre-refactor** code, is green at the commit that
introduces it, and must be green after the swap **without having been edited**.
That property is checkable from ``git log -p tests/integration/test_d14_chain.py``
and is asserted procedurally by T050 (SC-TEST-001). If a link fails after the
swap, the engine is wrong — not the golden (FR-021).

Note the json leg is the editor's real path, not a synthetic one:
``cuems-editor`` receives a JSON payload and rebuilds objects through
``CuemsParser``, which is exactly what ``_json_to_object`` does here.
"""

from __future__ import annotations

import json

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

CHAIN_DOCS = [d for d in DOCUMENTS if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()]
IDS = [d.relpath for d in CHAIN_DOCS]


def _json_to_object(payload: dict):
    """The editor's JSON→object path.

    ``CuemsParser`` dispatches on the first key, so the payload is wrapped in
    its root name — the same shape ``cuems-editor`` sends on ``project_load``.
    """
    from cuemsutils.xml.Parsers import CuemsParser

    return CuemsParser({"CuemsScript": payload}).parse()


@pytest.mark.parametrize("doc", CHAIN_DOCS, ids=IDS)
def test_d14_chain_every_intermediate_matches_its_golden(doc, tmp_path):
    # link 1: xml -> object, and the dict it was decoded from
    decoded = rt.read_dict(doc)
    assert rt.json_dumps(decoded) == rt.golden_json(f"dict/{doc.slug}.reader.json")

    obj = rt.read_objects(doc)

    # link 2: object -> json
    payload = json.loads(json.dumps(obj))

    # link 3: json -> object. The rebuilt object must equal the one the XML
    # produced; if it does not, the divergence is in the wire format and the
    # final XML comparison would hide it behind a second conversion.
    rebuilt = _json_to_object(payload)
    assert rebuilt == obj

    # link 4: object -> xml, byte-identical to the golden
    produced = rt.write_bytes(doc, rebuilt)
    assert produced == rt.golden_bytes(f"xml/{doc.slug}.xml")


@pytest.mark.parametrize("doc", CHAIN_DOCS, ids=IDS)
def test_json_leg_is_lossless_for_the_xml_that_follows_it(doc, tmp_path):
    """The two routes to XML must agree.

    Writing straight from the loaded object and writing after a JSON round-trip
    must produce the same bytes. A difference here means the JSON leg loses or
    reshapes something that survives in the object — the class of defect that
    only shows up as "the editor saved a different file than the engine did".
    """
    direct = rt.write_bytes(doc, rt.read_objects(doc))
    via_json = rt.write_bytes(
        doc, _json_to_object(json.loads(json.dumps(rt.read_objects(doc))))
    )
    assert via_json == direct


def test_generated_document_survives_the_whole_chain():
    """The chain over a document containing every cue type.

    The three vendored documents that reach the write path do not, between
    them, exercise dmx or fade cues through the json leg.
    """
    doc = next(d for d in DOCUMENTS if d.schema == "script")
    obj = rt.build_generated_script()

    direct = rt.normalize_uuids(rt.write_bytes(doc, obj))
    assert direct == rt.golden_bytes("generated/create_script.xml")

    rebuilt = _json_to_object(json.loads(json.dumps(obj)))
    via_json = rt.normalize_uuids(rt.write_bytes(doc, rebuilt))
    assert via_json == direct
