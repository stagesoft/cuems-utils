"""The D14 chain (T016) — contract C4, and this feature's primary gate.

    xml -> object -> json -> object -> xml

**Every intermediate is compared against its golden, not only the endpoints.**
That is the whole design of the test: two independent errors that cancel at the
ends are the failure mode a round-trip assertion is blindest to, and the chain
has four places for them to hide.

This file is written against **pre-refactor** code and is green at the commit
that introduces it. It had to be green after **feature 004's** swap without
having been edited — that is the property ``git log -p`` on this file makes
checkable, and it held. Feature 005 **extends** it (T011/T030, FR-026) with the
built-vs-loaded leg that 004's semantic round-trip test deferred to this
feature; every assertion above that addition is unchanged, which is the form
the "without having been edited" claim takes from here on. If a link fails
after a swap, the engine is wrong — not the golden (FR-021).

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

#: ``cuems-utils/fade_showcase.xml`` (T003c) carried an ``xfail(strict)`` on
#: the json leg through Phase 1 and Phase 2. It is the first corpus document
#: with a populated ``fade_profiles`` pair, and it exposed a pre-existing
#: defect: ``FadeProfile.__json__`` and ``FadeFunctionParameter.__json__``
#: self-wrapped as ``{"FadeProfile": {...}}``, ``CuemsParser`` rebuilt that
#: shape without unwrapping it, and the written XML got a literal
#: ``<FadeProfile>`` tag instead of ``<fade_profile>``.
#:
#: T035 deleted both bodies and the derived projection replaced them, which is
#: what the mark said would clear it. **It cleared** — the mark is gone rather
#: than flipped to non-strict, because a strict xfail that starts passing is
#: information and keeping it would discard exactly that.


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


# --- feature 005 addition (T011, FR-026) ----------------------------------
#
# Additive only: no assertion above changes. The built-vs-loaded leg is the
# comparison Part 2c Appendix A's probe performed and that 004's semantic
# round-trip test explicitly excluded as belonging to 005.


def _built_and_loaded():
    """One document's content, built and then round-tripped through XML."""
    import tempfile
    from pathlib import Path

    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter
    from tests.integration.test_construction_parity import SCRIPT_DOC

    built = rt.build_generated_script()
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "built.xml"
        path.write_bytes(rt.write_bytes(SCRIPT_DOC, built))
        loaded = XmlReaderWriter(
            schema_name="script", xmlfile=str(path)
        ).read_to_objects()
    return built, loaded


def test_a_built_object_and_a_loaded_one_agree_on_the_enumerated_types():
    """The chain's missing leg: is the object we loaded the object we built?

    The four links above prove the *values* survive the chain. They cannot see
    a type difference, because ``==`` on a ``dict`` and a ``CuemsDict`` holding
    the same keys is ``True`` — which is precisely how ``ui_properties`` and
    ``regions`` diverged for as long as they did without a single test going
    red.

    Scoped to the groups FR-019 enumerates. The three that remain are pinned,
    with their counts and their reasons, in ``test_construction_parity.py``.
    """
    from tests.integration.test_construction_parity import (
        classify,
        differences,
        type_map,
    )

    built, loaded = _built_and_loaded()

    # Deliberately **not** ``assert loaded == built``. That is a claim about
    # values, and it is false for a reason this feature does not own: wildcard
    # ``ui_properties`` content round-trips ``{'warning': 0}`` as
    # ``{'warning': '0'}``, because the schema states nothing about a
    # wildcard's children so there is no type to decode them back to. Feature
    # 004 recorded that; ``test_generated_document_survives_the_whole_chain``
    # above compares the emitted **bytes**, which is the equality that holds.
    rows = differences(type_map(built), type_map(loaded))
    offending = [r for r in rows if classify(*r) in {"ui_properties", "regions"}]
    assert not offending, "built vs loaded types:\n  " + "\n  ".join(
        f"{p}: {a} != {b}" for p, a, b in offending
    )


# --- feature 006 addition (T022, FR-008, SC-002) --------------------------
#
# The same chain, driven entirely through the public surface: no
# ``XmlReaderWriter``, no ``CuemsParser``, no schema name. Additive — nothing
# above changes — because the two must agree, and the way to show that is to
# run both rather than to replace one with the other.


def test_this_module_can_drive_the_chain_without_naming_the_xml_package():
    """SC-002, asserted against the *source* of the public leg below.

    The assertions above deliberately still import ``cuemsutils.xml`` — they
    are the pre-feature leg. So the claim is scoped to the module that holds
    only the public one.
    """
    import tests.integration.test_public_chain as public_leg

    from tests.support.public_api import assert_no_xml_import

    assert_no_xml_import(public_leg)


@pytest.mark.xfail(
    strict=True,
    reason="16 type differences remain in three groups outside FR-019's "
    "enumeration (wildcard None round-trip, OPAQUE_TYPES, and an uncoerced "
    "built side). None is reachable without widening 005 — see "
    "test_construction_parity.test_the_unenumerated_divergence_is_exactly_as_measured. "
    "Whether SC-001 means these too is an open scope question.",
)
def test_a_built_object_and_a_loaded_one_have_identical_internal_types():
    """SC-001 in full: **zero** differences, not zero in the enumerated groups."""
    from tests.integration.test_construction_parity import differences, type_map

    built, loaded = _built_and_loaded()
    rows = differences(type_map(built), type_map(loaded))
    assert not rows, "built vs loaded types:\n  " + "\n  ".join(
        f"{p}: {a} != {b}" for p, a, b in rows
    )
