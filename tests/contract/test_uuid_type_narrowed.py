# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T044 — the three schemas refuse a non-converged identity (FR-020, FR-020a, FR-021a, SC-007).

The point of no return for documents on disk, which is why US2 lands first: the
re-mint has to exist before anything here can be repaired (§9.3).

Each shape is asserted against **all three** schemas, because the convergence
claim is about the set of them and a narrowing that reached two of three would
leave the one it missed as the place divergence comes back.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import ids
from cuemsutils.xml.schema import get_schema
from tests.support.cluster_fixture import (
    SHAPES,
    NodeSpec,
    mac_for,
    network_map_xml,
    project_mappings_xml,
    settings_xml,
)

NON_CONVERGED = ["uuid1", "uuid5", "uuid4upper"]


def _documents(identity):
    """One instance of each of the three narrowed schemas, carrying ``identity``."""
    rows = [NodeSpec(identity, mac_for(0), "controller", "n0", "10.0.0.1")]
    return {
        "network_map": network_map_xml(rows),
        "project_mappings": project_mappings_xml(rows),
        "settings": settings_xml(identity, mac_for(0), "/opt/cuems_library"),
    }


def _valid(schema_name, text, tmp_path):
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")
    try:
        get_schema(schema_name).validate(str(path))
        return True
    except Exception:
        return False


@pytest.mark.parametrize("shape", NON_CONVERGED)
@pytest.mark.parametrize("schema_name", ["network_map", "project_mappings", "settings"])
def test_a_non_converged_identity_is_rejected(schema_name, shape, tmp_path):
    documents = _documents(SHAPES[shape])
    assert not _valid(schema_name, documents[schema_name], tmp_path), (
        f"{schema_name}.xsd still accepts a {shape} node identity"
    )


@pytest.mark.parametrize("schema_name", ["network_map", "project_mappings", "settings"])
def test_a_lowercase_uuid4_is_accepted(schema_name, tmp_path):
    documents = _documents(SHAPES["uuid4"])
    assert _valid(schema_name, documents[schema_name], tmp_path)


@pytest.mark.parametrize("schema_name", ["network_map", "project_mappings", "settings"])
def test_a_value_that_is_not_a_uuid_at_all_is_rejected(schema_name, tmp_path):
    documents = _documents("not-a-uuid")
    assert not _valid(schema_name, documents[schema_name], tmp_path)


@pytest.mark.parametrize("schema_name", ["network_map", "project_mappings", "settings"])
def test_a_thirty_five_character_value_is_rejected(schema_name, tmp_path):
    """Length is pinned explicitly as well as by the pattern's fixed groups.
    A truncated identity is the shape a hand edit produces."""
    documents = _documents(SHAPES["uuid4"][:-1])
    assert not _valid(schema_name, documents[schema_name], tmp_path)


def test_the_schemas_and_the_library_agree_on_what_converged_means(tmp_path):
    """One definition, checked in both places it is written down. The schemas'
    ``ConvergedUuidType`` pattern and ``ids.CONVERGED_PATTERN`` are two
    spellings of data-model §1.2's first line, and nothing but this keeps them
    the same."""
    import re
    from pathlib import Path

    schemas = Path("src/cuemsutils/xml/schemas")
    for name in ("network_map", "project_mappings", "settings"):
        text = (schemas / f"{name}.xsd").read_text()
        body = re.search(
            r'<xs:simpleType name="ConvergedUuidType">(.*?)</xs:simpleType>', text, re.S
        )
        assert body, f"{name}.xsd does not declare ConvergedUuidType"
        pattern = re.search(r'<xs:pattern value="([^"]+)"', body.group(1))
        assert pattern and pattern.group(1) == ids.CONVERGED_PATTERN, (
            f"{name}.xsd's ConvergedUuidType pattern differs from "
            "cuemsutils.tools.ids.CONVERGED_PATTERN"
        )


def test_mapped_to_type_is_deliberately_untouched():
    """Out of scope by FR-020b, and handed to feature 014. ``MappedToType`` is
    inside a complex type no element references (M-k), so narrowing it would be
    a schema change with no reachable effect — and one more thing for this
    feature's hashes to move."""
    import re
    from pathlib import Path

    text = Path("src/cuemsutils/xml/schemas/project_mappings.xsd").read_text()
    body = re.search(r'<xs:complexType name="MappedToType">(.*?)</xs:complexType>', text, re.S)
    assert body
    assert 'name="uuid" minOccurs="1" maxOccurs="1" type="xs:string"' in body.group(1)
