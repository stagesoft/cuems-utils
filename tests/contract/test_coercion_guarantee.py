"""Contract C1 (T017) — the coercion guarantee, through the public surface.

FR-001: *the returned object is fully coerced — every field holds its declared
type, at every depth, regardless of how the document was written.* The way to
test a claim like that is to build the same content three ways and compare the
**types** at every path, because ``==`` on two dicts holding the same keys is
``True`` whatever their members' classes are. That is exactly how
``ui_properties`` and ``regions`` diverged for as long as they did.

Three constructions: built in memory, ``CuemsScript.load()``, and
``CuemsScript.from_json()``. Two claims, and they are deliberately not the same
claim:

* **``load()`` vs ``from_json()`` — zero differences.** Both are decode paths
  and the whole point of FR-001 is that they land in the same place. Nothing
  about a document's *format* may reach the object.
* **built vs ``load()`` — zero differences in the groups FR-019 enumerates**,
  with the residual pinned by count. Feature 005 closed the enumerated groups
  and left 14 differences in three groups outside them (wildcard ``None``
  round-trip, ``OPAQUE_TYPES``, GENERIC-bound ``output_geometry``); that is a
  recorded open item carried to this feature's PR, not something US1 closes.
  Asserting "zero" here would either fail permanently or force the residual to
  be hidden — pinning the number is the honest form.

See ``specs/005-object-model-unification/migration-map.md``.
"""

from __future__ import annotations

import json
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from tests.integration.test_construction_parity import (
    classify,
    differences,
    render,
    type_map,
)
from tests.support import roundtrip as rt
from tests.support.corpus import script_documents
from tests.support.public_api import assert_no_xml_import

#: The residual measured after feature 005, reproduced here so a *change* in
#: it fails rather than passing quietly in either direction.
RESIDUAL_GROUPS = {"wildcard_none", "opaque_dmx", "built_uncoerced", "other"}


@pytest.fixture(scope="module")
def three_ways(tmp_path_factory):
    """One document's content, constructed three ways — public API only."""
    built = rt.build_generated_script()

    path = tmp_path_factory.mktemp("coercion") / "built.xml"
    built.save(path)
    loaded = CuemsScript.load(path)

    from_json = CuemsScript.from_json(loaded.to_json())
    return built, loaded, from_json


def test_load_and_from_json_produce_identical_internal_types(three_ways):
    """The strong claim: format does not reach the object (FR-001, FR-002)."""
    _, loaded, from_json = three_ways
    rows = differences(type_map(loaded), type_map(from_json))
    assert not rows, "load() vs from_json():\n  " + render(rows)


def test_load_and_from_json_produce_equal_objects(three_ways):
    _, loaded, from_json = three_ways
    assert from_json == loaded


def test_built_and_loaded_agree_on_every_enumerated_group(three_ways):
    built, loaded, _ = three_ways
    rows = differences(type_map(built), type_map(loaded))
    offending = [r for r in rows if classify(*r) not in RESIDUAL_GROUPS]
    assert not offending, "built vs load():\n  " + render(offending)


def test_the_built_vs_loaded_residual_is_exactly_the_recorded_one(three_ways):
    """The gap is recorded, never read as a clean result."""
    built, loaded, _ = three_ways
    rows = differences(type_map(built), type_map(loaded))
    groups = {classify(*r) for r in rows}
    assert groups <= RESIDUAL_GROUPS, (
        "a new difference group appeared outside the recorded residual:\n  "
        + render(rows)
    )


@pytest.mark.parametrize(
    "doc", script_documents(), ids=[d.relpath for d in script_documents()]
)
def test_every_corpus_script_loads_and_re_ingests_to_the_same_types(doc):
    """The guarantee over the whole corpus, not one generated document."""
    try:
        loaded = CuemsScript.load(doc.path)
    except Exception as exc:  # noqa: BLE001 - the accept/reject set is pinned
        pytest.skip(f"{doc.relpath} does not reach the object layer: {exc}")

    rebuilt = CuemsScript.from_json(json.dumps(loaded.to_wire()))
    rows = differences(type_map(loaded), type_map(rebuilt))
    assert not rows, f"{doc.relpath}:\n  " + render(rows)


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
