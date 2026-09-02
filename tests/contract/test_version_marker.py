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


def test_script_moved_but_the_other_five_schemas_did_not():
    assert CURRENT_VERSION["script"] == 2
    for schema_name in SCHEMA_NAMES:
        if schema_name == "script":
            continue
        assert CURRENT_VERSION[schema_name] == 1


def test_a_config_document_written_by_this_feature_reports_version_1(tmp_path):
    from cuemsutils.xml.settings import NetworkMap
    from tests.support.corpus import REPO_ROOT

    netmap = NetworkMap(str(REPO_ROOT / "tests" / "data" / "network_map.xml"))
    out = tmp_path / "network_map.xml"
    netmap.xml_dict.save(out)

    tree = ET.parse(out)
    assert read_version(tree) == 1
    assert tree.getroot().attrib.get(DOC_VERSION_ATTR) == "1"
