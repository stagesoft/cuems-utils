# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T047 — three version steps, and **no** conversion for any of them (FR-022, FR-022a, FR-023, research R5).

The registry represents the identity step by the **absence** of an entry, and
its own docstring says "no conversion" and "a conversion that happens to do
nothing" must not be confusable. So the assertion is not "the conversion does
nothing" — it is that no entry exists.

The rejected alternative is the most important one in the feature: repairing in
a conversion, by minting a new identity per document, would give ``settings.xml``
and ``network_map.xml`` **different answers for the same node**. That is §9.4's
measured failure, ``Node with uuid ... not found``. A cross-document identity
cannot be repaired one document at a time, which is exactly why the repair is
out-of-band and why FR-023 is detect-and-report rather than detect-and-fix.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

import pytest

from cuemsutils.xml import versioning
from tests.support.cluster_fixture import (
    SHAPES,
    NodeSpec,
    mac_for,
    network_map_xml,
    project_mappings_xml,
    settings_xml,
)

#: ``schema -> (before this feature, after it)``.
STEPS = {
    "network_map": (1, 2),
    "project_mappings": (1, 2),
    "settings": (2, 3),
}


@pytest.mark.parametrize("schema_name,versions", sorted(STEPS.items()))
def test_current_version_is_bumped(schema_name, versions):
    _before, after = versions
    assert versioning.CURRENT_VERSION[schema_name] == after


def test_the_other_three_schemas_did_not_move():
    """Versions move **per schema**. A feature that bumped all six would make
    every document in the field one version behind for no reason."""
    assert versioning.CURRENT_VERSION["script"] == 2
    assert versioning.CURRENT_VERSION["project_settings"] == 1
    assert versioning.CURRENT_VERSION["hardware_outputs"] == 2


@pytest.mark.parametrize("schema_name,versions", sorted(STEPS.items()))
def test_no_conversion_is_registered_for_the_step(schema_name, versions):
    """The absence **is** the identity step (research R5). Registering a
    do-nothing ``Conversion`` to carry a description would violate the
    machinery's documented invariant and leave a future reader unable to tell a
    deliberate identity step from a transformation that lost its body."""
    before, _after = versions
    assert versioning._CONVERSIONS.get((schema_name, before)) is None


@pytest.mark.parametrize("schema_name,versions", sorted(STEPS.items()))
def test_a_pre_step_document_is_recognised_and_recorded_as_an_identity_step(
        schema_name, versions, tmp_path):
    before, after = versions
    rows = [NodeSpec(SHAPES["uuid4"], mac_for(0), "controller", "n0", "10.0.0.1")]
    text = {
        "network_map": network_map_xml(rows, version=before),
        "project_mappings": project_mappings_xml(rows, version=before),
        "settings": settings_xml(SHAPES["uuid4"], mac_for(0), "/opt/cuems_library",
                                 version=before),
    }[schema_name]
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")

    tree = ET.parse(str(path))
    assert versioning.read_version(tree) == before

    steps = versioning.convert(schema_name, tree, before, after)
    assert len(steps) == after - before
    for step in steps:
        assert "identity" in step.description
        assert step.dropped_elements == ()


@pytest.mark.parametrize("schema_name,versions", sorted(STEPS.items()))
def test_no_repair_is_attempted_on_a_non_converged_identity_in_a_pre_step_document(
        schema_name, versions, tmp_path):
    """FR-023: detect and report, never repair. The conversion leaves the
    identity exactly as it found it — including a uuid1, which the narrowed
    type then rejects at T1 with FR-024's message."""
    before, after = versions
    rows = [NodeSpec(SHAPES["uuid1"], mac_for(0), "controller", "n0", "10.0.0.1")]
    text = {
        "network_map": network_map_xml(rows, version=before),
        "project_mappings": project_mappings_xml(rows, version=before),
        "settings": settings_xml(SHAPES["uuid1"], mac_for(0), "/opt/cuems_library",
                                 version=before),
    }[schema_name]
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")

    tree = ET.parse(str(path))
    versioning.convert(schema_name, tree, before, after)

    still_there = [e.text for e in tree.getroot().iter()
                   if e.tag.rsplit("}", 1)[-1] == "uuid"]
    assert SHAPES["uuid1"] in still_there, (
        "the conversion changed an identity. A per-document mint gives "
        "settings.xml and network_map.xml different answers for the same node, "
        "which is §9.4's measured failure."
    )


def test_a_document_with_no_marker_is_still_version_one():
    """Unchanged, and load-bearing: absent means version 1 (FR-050), so a
    document written before the marker existed is not thereby unreadable."""
    root = ET.fromstring('<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/"/>')
    assert versioning.read_version(root) == 1
