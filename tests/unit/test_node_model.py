"""``node`` behaviour (T028, T029) — data-model.md §3.2."""

from __future__ import annotations

from cuemsutils.config.network_map import node
from cuemsutils.tools.NodeList import NodeRole
from tests.support.config_inventory import build_config_manager


def test_node_constructible_directly_without_a_document():
    """FR-004 — the Avahi listener builds nodes that never reach a file."""
    n = node(
        uuid="0367f391-ebf4-48b2-9f26-000000000099",
        mac="aabbccddeeff",
        name="freshly-discovered",
        node_role=NodeRole.firstrun,
        ip="192.168.1.200",
    )
    assert n["uuid"] == "0367f391-ebf4-48b2-9f26-000000000099"
    assert n["node_role"] is NodeRole.firstrun
    assert "adopted" not in n


def test_document_omitting_optional_fields_yields_no_keys_for_them():
    """A document omitting role_id/alias/hostname yields an object without
    those keys — not one carrying three empty strings (schema evolution
    convention, unchanged from feature 006)."""
    cm = build_config_manager()
    n = cm.network_map["node_list"][0]["node"]

    assert "role_id" not in n
    assert "alias" not in n
    assert "hostname" not in n
    # And the required/present fields are there, correctly typed.
    assert n["node_role"] is NodeRole.controller
    assert n["adopted"] is True


def test_node_is_a_dict_subclass():
    n = node(uuid="x", mac="y", name="z", node_role=NodeRole.node, ip="1.1.1.1")
    assert isinstance(n, dict)
