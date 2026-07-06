"""Unit tests for ProjectMappings canvas_region handling."""

from copy import deepcopy
from pathlib import Path

import pytest

from cuemsutils.xml.Settings import ProjectMappings

DATA_DIR = Path(__file__).parent / "data"


# ---------------------------------------------------------------------------
# Migrated fixtures load successfully
# ---------------------------------------------------------------------------

def test_default_mappings_fixture_loads():
    m = ProjectMappings(str(DATA_DIR / "default_mappings.xml"))
    assert m.loaded
    # The active node should exist and expose its video outputs.
    node = m.get_node("0367f391-ebf4-48b2-9f26-000000000001")
    assert node["uuid"] == "0367f391-ebf4-48b2-9f26-000000000001"


def test_project_mappings_fixture_loads():
    # Previously untested; schema migration should keep it valid.
    m = ProjectMappings(str(DATA_DIR / "project_mappings.xml"))
    assert m.loaded


def test_active_node_has_one_custom_template():
    m = ProjectMappings(str(DATA_DIR / "default_mappings.xml"))
    node = m.get_node("0367f391-ebf4-48b2-9f26-000000000001")
    template_count = _count_templates(node)
    assert template_count == 1


def test_alias_entry_has_no_canvas_region():
    m = ProjectMappings(str(DATA_DIR / "default_mappings.xml"))
    node = m.get_node("0367f391-ebf4-48b2-9f26-000000000001")
    # id=0 and id=1 are aliases after migration.
    for output_wrap in _video_outputs(node):
        output = output_wrap["output"]
        if output["id"] in (0, 1):
            assert "canvas_region" not in output


# ---------------------------------------------------------------------------
# Python-level validation (containment + template count)
# ---------------------------------------------------------------------------

def test_containment_failure_rejected_after_load():
    m = ProjectMappings(str(DATA_DIR / "default_mappings.xml"))
    tampered = deepcopy(m.processed)
    _video_outputs(tampered["nodes"][0]["node"])[-1]["output"]["canvas_region"] = {
        "x": 0.7, "y": 0.0, "width": 0.5, "height": 0.5,  # x+w = 1.2
    }
    # Replay the Python-side validator against the tampered dict.
    m.processed = tampered
    with pytest.raises(ValueError, match="x\\+width must be <= 1"):
        m._validate_custom_templates()


def test_multiple_templates_on_same_node_rejected():
    m = ProjectMappings(str(DATA_DIR / "default_mappings.xml"))
    tampered = deepcopy(m.processed)
    outputs = _video_outputs(tampered["nodes"][0]["node"])
    # Add a canvas_region to the id=0 alias, making the node hold two templates.
    outputs[0]["output"]["canvas_region"] = {
        "x": 0.0, "y": 0.0, "width": 0.25, "height": 0.25,
    }
    m.processed = tampered
    with pytest.raises(ValueError, match="custom templates"):
        m._validate_custom_templates()


def test_get_node_raises_for_unknown_uuid():
    m = ProjectMappings(str(DATA_DIR / "default_mappings.xml"))
    with pytest.raises(ValueError, match="not found"):
        m.get_node("ffffffff-ffff-ffff-ffff-ffffffffffff")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _video_outputs(node):
    """Dig through the decoded node dict to the list of {'output': {...}} entries."""
    video = node.get("video") or []
    outputs = []
    for group in video:
        for output_wrap in group.get("outputs") or []:
            outputs.append(output_wrap)
    return outputs


def _count_templates(node):
    return sum(
        1 for o in _video_outputs(node) if "canvas_region" in o["output"]
    )
