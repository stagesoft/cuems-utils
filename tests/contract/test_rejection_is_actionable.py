# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T051 — a rejected document says what to do about it (FR-024, FR-023's reporting half).

Produced in the **validation error path**, because no conversion exists to
produce it (FR-023, research R5). That is not a fallback: a cross-document
identity cannot be repaired one document at a time, so the only honest thing a
single-document read can do is name the fault and the out-of-band tool that
fixes it.

Four things, and each answers a question an operator will otherwise have to ask
someone: which document, which path within it, what value, and what to run.
"""

from __future__ import annotations

import pytest

from cuemsutils.errors import SchemaError, ValidationError
from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.settings import NetworkMap, ProjectMappings, Settings
from tests.support.cluster_fixture import (
    SHAPES,
    NodeSpec,
    mac_for,
    network_map_xml,
    project_mappings_xml,
    settings_xml,
)

READERS = {
    "network_map": NetworkMap,
    "project_mappings": ProjectMappings,
    "settings": Settings,
}


def _reject(tmp_path, schema_name, identity):
    rows = [NodeSpec(identity, mac_for(0), "controller", "n0", "10.0.0.1")]
    text = {
        "network_map": network_map_xml(rows),
        "project_mappings": project_mappings_xml(rows),
        "settings": settings_xml(identity, mac_for(0), "/opt/cuems_library"),
    }[schema_name]
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")
    with pytest.raises((SchemaError, ValidationError)) as raised:
        load_config_document(READERS[schema_name], str(path), schema_name)
    return str(path), str(raised.value)


@pytest.mark.parametrize("schema_name", sorted(READERS))
@pytest.mark.parametrize("shape", ["uuid1", "uuid5", "uuid4upper"])
def test_the_message_names_the_document(tmp_path, schema_name, shape):
    path, message = _reject(tmp_path, schema_name, SHAPES[shape])
    assert path in message


@pytest.mark.parametrize("schema_name", sorted(READERS))
def test_the_message_names_the_offending_value(tmp_path, schema_name):
    _path, message = _reject(tmp_path, schema_name, SHAPES["uuid1"])
    assert SHAPES["uuid1"] in message


@pytest.mark.parametrize("schema_name", sorted(READERS))
def test_the_message_names_where_in_the_document(tmp_path, schema_name):
    _path, message = _reject(tmp_path, schema_name, SHAPES["uuid1"])
    assert "uuid" in message


@pytest.mark.parametrize("schema_name", sorted(READERS))
def test_the_message_names_the_repair_tool(tmp_path, schema_name):
    """The one thing a generic schema error cannot say, and the whole reason
    this rule is in the T2 tier rather than expressed as ``xs:unique`` in the
    schema (research R2)."""
    _path, message = _reject(tmp_path, schema_name, SHAPES["uuid1"])
    assert "cuems-init-node --remint" in message


@pytest.mark.parametrize("schema_name", sorted(READERS))
def test_the_message_says_the_shape_it_wanted(tmp_path, schema_name):
    """"Invalid" is not actionable. "uuid4, lowercase" is."""
    _path, message = _reject(tmp_path, schema_name, SHAPES["uuid1"])
    assert "uuid4" in message


@pytest.mark.parametrize("schema_name", sorted(READERS))
def test_the_sentinel_is_not_reported_as_needing_a_re_mint(tmp_path, schema_name):
    """It is admitted, so there is nothing to report. A freshly installed node
    must not be told to run a cluster-wide migration."""
    rows = [NodeSpec(SHAPES["sentinel"], mac_for(0), "controller", "n0", "10.0.0.1")]
    text = {
        "network_map": network_map_xml(rows),
        "project_mappings": project_mappings_xml(rows),
        "settings": settings_xml(SHAPES["sentinel"], mac_for(0), "/opt/cuems_library"),
    }[schema_name]
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")
    load_config_document(READERS[schema_name], str(path), schema_name)
