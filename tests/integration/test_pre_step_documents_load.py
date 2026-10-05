# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T052 — a pre-step document is **recognised**, and then judged (US3 scenario 5, FR-022a).

Both halves, because the story's fifth scenario is about *recognition*, not
about surviving:

* a pre-step document whose identity is already converged **loads** — the
  version step is an identity step, so nothing about the document has to change
  for it to be read;
* one carrying a uuid1 is **rejected with FR-024's message** — the marker told
  the library how to read it, and the narrowed type then refused what it found.

The distinction matters because the two failures look the same from outside and
have opposite remedies: "your document is from an older release" is handled
automatically, "your node's identity is the wrong shape" needs the operator.
"""

from __future__ import annotations

import pytest

from cuemsutils.errors import SchemaError, ValidationError
from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.settings import NetworkMap, ProjectMappings, Settings
from tests.contract.test_version_steps import NO_LONGER_AN_IDENTITY_STEP
from tests.support.cluster_fixture import (
    SHAPES,
    NodeSpec,
    mac_for,
    network_map_xml,
    project_mappings_xml,
    settings_xml,
)

#: ``schema -> (reader, pre-step version)``.
CASES = {
    "network_map": (NetworkMap, 1),
    "project_mappings": (ProjectMappings, 1),
    "settings": (Settings, 2),
}


def _write(tmp_path, schema_name, identity, version):
    rows = [NodeSpec(identity, mac_for(0), "controller", "n0", "10.0.0.1")]
    text = {
        "network_map": network_map_xml(rows, version=version),
        "project_mappings": project_mappings_xml(rows, version=version),
        "settings": settings_xml(identity, mac_for(0), "/opt/cuems_library", version=version),
    }[schema_name]
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize("schema_name", sorted(CASES))
def test_a_converged_pre_step_document_loads(tmp_path, schema_name):
    reader, version = CASES[schema_name]
    path = _write(tmp_path, schema_name, SHAPES["uuid4"], version)
    document = load_config_document(reader, str(path), schema_name)
    assert document.document_version == version


@pytest.mark.parametrize("schema_name", sorted(CASES))
def test_the_marker_is_recognised_rather_than_reported_unknown(tmp_path, schema_name):
    """Not "unknown version" and not "malformed". The walk says what it did.

    **Premise narrowed by 014 (X1), not loosened.** This asserted that every
    one of the three steps describes itself as an *identity* step — the
    registry representing it by the absence of an entry. ``network_map`` 1 -> 2
    now carries the boolean rewrite, so it has a registered ``Conversion`` and
    a description of its own; see
    :data:`tests.contract.test_version_steps.NO_LONGER_AN_IDENTITY_STEP`, which
    is where that exception is named.

    What the test is actually for survives both cases: the marker produces a
    *described* step rather than an unknown version or a parse failure. The
    identity wording still binds for the two schemas it still applies to.
    """
    reader, version = CASES[schema_name]
    path = _write(tmp_path, schema_name, SHAPES["uuid4"], version)
    document = load_config_document(reader, str(path), schema_name)
    assert len(document.document_conversions) >= 1
    for step in document.document_conversions:
        assert step.description, (schema_name, step)
        if schema_name in NO_LONGER_AN_IDENTITY_STEP:
            assert "xs:boolean" in step.description, step.description
        else:
            assert "identity" in step.description


@pytest.mark.parametrize("schema_name", sorted(CASES))
def test_a_uuid1_pre_step_document_is_rejected_with_the_actionable_message(
        tmp_path, schema_name):
    reader, version = CASES[schema_name]
    path = _write(tmp_path, schema_name, SHAPES["uuid1"], version)
    with pytest.raises((SchemaError, ValidationError)) as raised:
        load_config_document(reader, str(path), schema_name)
    message = str(raised.value)
    assert SHAPES["uuid1"] in message
    assert "cuems-init-node --remint" in message


@pytest.mark.parametrize("schema_name", sorted(CASES))
def test_a_current_version_document_loads_too(tmp_path, schema_name):
    """The step is not a requirement to carry the old marker."""
    from cuemsutils.xml import versioning

    reader, _version = CASES[schema_name]
    current = versioning.CURRENT_VERSION[schema_name]
    path = _write(tmp_path, schema_name, SHAPES["uuid4"], current)
    document = load_config_document(reader, str(path), schema_name)
    assert document.document_version == current
    assert document.document_conversions == ()


@pytest.mark.parametrize("schema_name", sorted(CASES))
def test_a_document_newer_than_the_library_is_still_distinguishable(tmp_path, schema_name):
    """Feature 008's FR-052, unchanged by the bumps. A reader asked for a
    version it does not have must say so rather than produce an "unexpected
    element" failure from deep inside a decode."""
    reader, _version = CASES[schema_name]
    path = _write(tmp_path, schema_name, SHAPES["uuid4"], 99)
    with pytest.raises(ValidationError) as raised:
        load_config_document(reader, str(path), schema_name)
    assert "newer than this library" in str(raised.value)
