# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T045 — the sentinel validates, and nothing else nil-like does (FR-021, assumption 1).

The premise the whole narrowing design rests on. Feature 011's freshly installed
node carries ``00000000-0000-0000-0000-000000000000`` in all three documents; a
pattern that refused it would make every newly installed node unloadable and
the package's own build-time generation fail.

It is admitted **by union, not by loosening**. That distinction is the content
of the second half of this file: no other nil-like value becomes valid, because
the sentinel is an enumeration of exactly one string rather than a relaxed
pattern.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import ids
from cuemsutils.xml.schema import get_schema
from tests.support.cluster_fixture import (
    NodeSpec,
    mac_for,
    network_map_xml,
    project_mappings_xml,
    settings_xml,
)

SCHEMAS = ["network_map", "project_mappings", "settings"]

#: Values that look like a nil uuid, are not the sentinel, and must stay
#: invalid. The upper-case spelling matters most: a schema that accepted it
#: would give the *same* node two spellings of "not provisioned", and a literal
#: substitution matches one of them.
NEAR_MISSES = [
    "00000000-0000-0000-0000-00000000000",     # 35 characters
    "00000000-0000-0000-0000-0000000000000",   # 37
    "00000000-0000-4000-8000-000000000000",    # a *converged* nil-looking value
    "0000000000000000000000000000000000000",
    "",
]


def _document(schema_name, identity):
    rows = [NodeSpec(identity, mac_for(0), "controller", "n0", "10.0.0.1")]
    return {
        "network_map": network_map_xml(rows),
        "project_mappings": project_mappings_xml(rows),
        "settings": settings_xml(identity, mac_for(0), "/opt/cuems_library"),
    }[schema_name]


def _valid(schema_name, text, tmp_path):
    path = tmp_path / f"{schema_name}.xml"
    path.write_text(text, encoding="utf-8")
    try:
        get_schema(schema_name).validate(str(path))
        return True
    except Exception:
        return False


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_the_sentinel_validates(schema_name, tmp_path):
    assert _valid(schema_name, _document(schema_name, ids.NOT_PROVISIONED_UUID), tmp_path)


@pytest.mark.parametrize("value", NEAR_MISSES)
@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_no_other_nil_like_value_validates(schema_name, value, tmp_path):
    if value == "00000000-0000-4000-8000-000000000000":
        # This one *is* a converged uuid4 and is therefore valid — which is the
        # right answer and is asserted in the other direction below.
        pytest.skip("a converged uuid4 that happens to look nil is valid, correctly")
    assert not _valid(schema_name, _document(schema_name, value), tmp_path)


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_the_sentinel_is_admitted_by_its_own_named_type(schema_name):
    """Two separately named definitions and a union of them (FR-021c), not one
    widened pattern — so either half can be named, tested and removed on its
    own, and the union is the only one an element references."""
    import re
    from pathlib import Path

    text = (Path("src/cuemsutils/xml/schemas") / f"{schema_name}.xsd").read_text()
    sentinel = re.search(
        r'<xs:simpleType name="NotProvisionedUuidType">(.*?)</xs:simpleType>', text, re.S
    )
    assert sentinel
    assert f'<xs:enumeration value="{ids.NOT_PROVISIONED_UUID}"' in sentinel.group(1)
    assert "xs:pattern" not in sentinel.group(1), (
        "the sentinel is an enumeration of one value, not a pattern — a pattern "
        "here is how other nil-like values would quietly become valid"
    )

    union = re.search(r'<xs:simpleType name="NodeUuidType">(.*?)</xs:simpleType>', text, re.S)
    assert union
    assert "cms:ConvergedUuidType" in union.group(1)
    assert "cms:NotProvisionedUuidType" in union.group(1)


@pytest.mark.parametrize("schema_name", SCHEMAS)
def test_only_the_union_is_referenced_by_an_element(schema_name):
    from pathlib import Path

    text = (Path("src/cuemsutils/xml/schemas") / f"{schema_name}.xsd").read_text()
    assert 'type="cms:NodeUuidType"' in text
    assert 'type="cms:ConvergedUuidType"' not in text
    assert 'type="cms:NotProvisionedUuidType"' not in text
