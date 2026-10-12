"""Contract C1 — ``NodeRole`` is the single vocabulary, and it agrees with the schema."""

from __future__ import annotations

from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.xml.schema import get_schema


def test_node_role_values_equal_the_schema_enumeration():
    """Not a hand-copied list — read from the loaded schema, so the two
    cannot drift (C1)."""
    facets = set(get_schema("network_map").types["NodeRoleType"].enumeration)
    assert {member.value for member in NodeRole} == facets


def test_node_role_members():
    assert NodeRole.controller.value == "controller"
    assert NodeRole.node.value == "node"
    assert NodeRole.firstrun.value == "firstrun"
