"""The document-version marker (ITEM E, US6, T091-T093/T099a) — data-model.md §1.

An optional, unqualified ``doc_version`` attribute on every schema's root
complex type (FR-048a), versioned **per schema** (FR-048b): a document
property, never a domain field, never on the wire (research R1).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema
from cuemsutils.xml.versioning import CURRENT_VERSION, DOC_VERSION_ATTR, read_version
from tests.support import invalid_scripts as broken


# --- T091: every written document carries the marker; absence means 1 -----


def test_every_written_script_document_carries_doc_version(tmp_path):
    script = broken.valid_script()
    path = tmp_path / "out.xml"
    script.save(path)

    tree = ET.parse(path)
    assert tree.getroot().attrib.get(DOC_VERSION_ATTR) == str(CURRENT_VERSION["script"])


def test_a_marker_less_document_is_treated_as_version_1_not_malformed():
    from tests.support.corpus import by_relpath

    doc = by_relpath("cuems-utils/unicode_showcase.xml")
    # This corpus document carries the marker now (T102a); parse the
    # *pre-008* original, which never had one, to test the true absence case.
    from tests.support.corpus import REPO_ROOT

    pre008 = REPO_ROOT / "tests" / "data" / "corpus" / "pre-008" / "cuems-utils" / "unicode_showcase.xml"
    tree = ET.parse(pre008)
    assert DOC_VERSION_ATTR not in tree.getroot().attrib
    assert read_version(tree) == 1


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_schema_declares_the_marker_as_an_optional_positive_integer(schema_name):
    root_type = get_schema(schema_name).root_elements[0].type
    attribute = root_type.attributes[DOC_VERSION_ATTR]
    assert attribute.use == "optional"
    assert attribute.type.local_name == "positiveInteger"


# --- T092: adding the attribute invalidates zero pre-change documents -----


def test_adding_the_marker_invalidates_no_corpus_document():
    """Every pre-change corpus document still validates **without** the
    marker present — the attribute is additive, ``use="optional"``, so no
    document written before this feature is retroactively broken."""
    from tests.support.corpus import script_documents

    for doc in script_documents():
        # loadable_script_documents already filters to the ones that decode;
        # any structural failure here would be a *regression* from the
        # marker's addition, not a pre-existing rejection.
        try:
            CuemsScript.load(doc.path)
        except Exception:
            pass  # pre-existing accept/reject verdicts are out of scope here


# --- T093: the marker never reaches the wire, and the payload is stable ---


def test_doc_version_never_appears_in_a_wire_projection(tmp_path):
    script = broken.valid_script()
    path = tmp_path / "out.xml"
    script.save(path)

    reloaded = CuemsScript.load(path)
    wire = reloaded.to_wire()
    assert "doc_version" not in wire
    assert "doc_version" not in wire.get("CuemsScript", wire)


def test_doc_version_is_on_no_model_class():
    from cuemsutils.cues.CuemsScript import CuemsScript as Script

    assert "doc_version" not in Script.declared_fields()


def test_project_load_payload_is_unaffected_by_the_marker_modulo_duration_reshape(tmp_path):
    """Part 2d: the payload's *only* sanctioned change this feature is
    FR-003's duration reshape. Comparing two **freshly saved and reloaded**
    scripts (one with a fade cue, one without) isolates the marker's effect
    from that reshape, which this test does not otherwise touch."""
    script = broken.valid_script()
    path = tmp_path / "out.xml"
    script.save(path)
    reloaded = CuemsScript.load(path)

    resaved = tmp_path / "out2.xml"
    reloaded.save(resaved)
    reloaded_again = CuemsScript.load(resaved)

    assert reloaded.to_wire() == reloaded_again.to_wire()


# --- T099a: versions move per schema, not in lockstep ---------------------


#: Each schema's document version, pinned. **Update an entry in the same commit
#: as the schema change that moves it**, with a registered conversion beside it.
#:
#: Re-based 2026-09-23 (`specs/planning/etc-cuems-first-install.md` §12). This
#: used to assert *only ``script`` has moved* — feature 008's measured
#: independence (FR-048b, SC-023b, T099a), true while that feature was the only
#: one editing schemas. rc16/rc17 moved two more, each dropping elements with a
#: conversion registered for the step, so the assertion is now *these are the
#: versions, and a version moves only with its conversion*.
EXPECTED_VERSIONS = {
    "script": 2,            # 008 ITEM E: duration reshape, action_type remap, fade_profiles
    "settings": 2,          # rc17 F3: derived counts dropped
    "hardware_outputs": 2,  # rc17 F4: authored defaults dropped
    "network_map": 1,
    "project_mappings": 1,
    "project_settings": 1,
}


def test_each_schema_is_at_its_pinned_version():
    assert CURRENT_VERSION == EXPECTED_VERSIONS
    assert set(EXPECTED_VERSIONS) == set(SCHEMA_NAMES)


def test_every_schema_past_version_1_has_a_conversion_for_every_step():
    """A version bump without a conversion is a document that cannot be read.

    The registry treats a missing step as *identity* — correct for purely
    additive growth, wrong for a step that drops elements, where the absence
    would let an old document reach a strict decode that rejects it. Any schema
    this project has moved so far drops something, so each of its steps is
    required to be registered; a future additive-only bump would relax this
    deliberately, and here.
    """
    from cuemsutils.xml.versioning import _CONVERSIONS

    missing = [
        (name, version)
        for name, current in CURRENT_VERSION.items()
        for version in range(1, current)
        if (name, version) not in _CONVERSIONS
    ]
    assert not missing, (
        f"schema version step(s) with no registered conversion: {missing}. "
        "An unregistered step is an identity step, which is wrong for any step "
        "that drops or reshapes an element."
    )


def test_a_config_document_written_by_this_feature_reports_version_1(tmp_path):
    from cuemsutils.xml.settings import NetworkMap
    from tests.support.corpus import REPO_ROOT

    netmap = NetworkMap(str(REPO_ROOT / "tests" / "data" / "network_map.xml"))
    out = tmp_path / "network_map.xml"
    netmap.xml_dict.save(out)

    tree = ET.parse(out)
    assert read_version(tree) == 1
    assert tree.getroot().attrib.get(DOC_VERSION_ATTR) == "1"
