"""Strict reading, across the show surface and the config accessors (ITEM E,
US5, T085-T090) — FR-037, FR-038, SC-015.

FR-037: the public show load surface and **every** configuration accessor
now run full validation (T1 **and** T2) on every read. FR-038 states this
plainly as a reversal: reading used to never become stricter (feature 006's
``test_semantic_not_on_read.py``, now itself rewritten to record the same
reversal at its own call site) — that principle is retired for **semantic**
validation specifically, and only from this feature forward.
"""

from __future__ import annotations

import copy

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import Outcome, ValidationError
from tests.support import invalid_scripts as broken


def _cue_id_from_output(node) -> str:
    return node["uuid"]


# --- T085/FR-037: a show document violating a semantic rule is caught ------


def test_a_semantically_invalid_show_document_is_detected_on_load(tmp_path):
    """Where it previously loaded silently (FR-026, pre-008), it is now
    either repaired (loads, with a report) or raises — never silent."""
    script = broken.semantically_invalid()
    path = tmp_path / "invalid.xml"
    broken.write_bypassing_validation(script, path)

    # canvas_region_containment is repairable=False (xml/validators.py): no
    # default stands in for a placement region without silently moving the
    # output, so this specific violation raises.
    with pytest.raises(ValidationError):
        CuemsScript.load(path)


def test_a_repairable_show_violation_loads_with_a_report_instead_of_raising(tmp_path):
    """The other half of the same reversal: FR-043's repair path, reached
    from the same public entry point (SC-020a exercises both sides here)."""
    script = broken.repairable_violation()
    path = tmp_path / "repairable.xml"
    broken.write_bypassing_validation(script, path)

    loaded, report = CuemsScript.load_with_report(path)
    assert loaded is not None
    assert report.outcome is Outcome.REPAIRED
    assert report.repairs


# --- T086/FR-037: every ConfigManager/ConfigBase accessor runs both tiers --


def test_project_mappings_semantic_violation_raises_validation_error_not_schema_error(
    tmp_path,
):
    """``project_mappings``' one T2 rule (``one_custom_template_per_node``,
    FR-039) now surfaces through the **same accessor path** every config
    domain shares (``tools.ConfigBase.load_config_document``) as
    ``ValidationError`` — distinguishable from a structural (T1) failure,
    which stays ``SchemaError``. Before this feature both were folded into
    the same generic ``SchemaError`` wrap.
    """
    from cuemsutils.tools.ConfigBase import load_config_document
    from cuemsutils.xml.settings import ProjectMappings
    from tests.support.corpus import REPO_ROOT

    source = ProjectMappings(str(REPO_ROOT / "tests" / "data" / "default_mappings.xml"))
    tampered = copy.deepcopy(source.processed)
    node = tampered["nodes"][0]["node"]
    # Give the alias output (id 0) a canvas_region too, so the node now
    # carries two "custom templates" where at most one is allowed.
    outputs = [
        o["output"]
        for group in node["video"]
        for o in (group.get("outputs") or [])
    ]
    outputs[0]["canvas_region"] = {"x": 0.0, "y": 0.0, "width": 0.1, "height": 0.1}

    out_path = tmp_path / "tampered_mappings.xml"
    tampered.save(out_path)

    with pytest.raises(ValidationError) as excinfo:
        load_config_document(ProjectMappings, str(out_path), "project_mappings")
    assert not isinstance(excinfo.value, type(None))
    from cuemsutils.errors import SchemaError

    assert not isinstance(excinfo.value, SchemaError), (
        "a T2 (semantic) violation must not be reported as a T1 SchemaError"
    )


def test_a_structurally_invalid_config_document_still_raises_schema_error(tmp_path):
    """The other half: a genuine T1 failure keeps its existing type."""
    from cuemsutils.tools.ConfigBase import load_config_document
    from cuemsutils.errors import SchemaError
    from cuemsutils.xml.settings import ProjectMappings

    bad = tmp_path / "not_xml_at_all.xml"
    bad.write_text("<CuemsProjectMappings>not even close</CuemsProjectMappings>")

    with pytest.raises(SchemaError):
        load_config_document(ProjectMappings, str(bad), "project_mappings")


# --- T087: a fully valid document loads unchanged, no report, no fuss -----


def test_a_fully_valid_document_loads_clean(tmp_path):
    script = broken.valid_script()
    path = tmp_path / "clean.xml"
    broken.write_bypassing_validation(script, path)

    loaded, report = CuemsScript.load_with_report(path)
    assert loaded is not None
    assert report.outcome is Outcome.CLEAN
    assert report.conversions == ()
    assert report.repairs == ()
    assert report.file_differs_from_loaded is False


def test_every_corpus_document_still_loads_or_repairs_never_silently_wrong(tmp_path):
    """FR-037 over the corpus: nothing that used to load starts raising
    unless it genuinely carries an unrepairable T2 violation — none of the
    current corpus does."""
    from tests.support.corpus import loadable_script_documents

    for doc in loadable_script_documents():
        loaded = CuemsScript.load(doc.path)
        assert loaded is not None
