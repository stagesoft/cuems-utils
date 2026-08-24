"""Contract C2 — node field types come from the derived adapter table.

Also carries T034's structural coercion assertion (data-model.md §5): every
free-text field's XSD type resolves to ``PASSTHROUGH``, every typed field to
its bound (non-passthrough) adapter. Stated as a property of the schema, not
as a list of field names — the same reason the ``NodeRole`` vocabulary test
reads the schema rather than hand-copying it.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.adapters import PASSTHROUGH, adapter_for
from cuemsutils.xml.spec import derive_named
from tests.support import roundtrip as rt
from tests.support.config_inventory import build_config_manager
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

#: FR-011a-i — decoding these three must still equal their recorded goldens,
#: byte for byte, now that network_map runs the adapter table and they do not.
OTHER_CONFIG_SCHEMAS = ("settings", "project_mappings", "project_settings")


def test_node_field_types_match_the_derived_adapter_table():
    cm = build_config_manager()
    node = cm.network_map["node_list"][0]["node"]

    assert isinstance(node["node_role"], NodeRole)
    assert isinstance(node["adopted"], bool)
    assert isinstance(node["online"], bool)
    assert isinstance(node["uuid"], (Uuid, str))  # raw text if unparseable (R2)
    assert isinstance(node["alias"], str) if "alias" in node else True
    assert isinstance(node["mac"], str)
    assert isinstance(node["name"], str)
    assert isinstance(node["ip"], str)


@pytest.mark.parametrize("schema_name", OTHER_CONFIG_SCHEMAS)
def test_other_config_schemas_decode_identically_to_their_goldens(schema_name):
    docs = [
        d
        for d in DOCUMENTS
        if d.schema == schema_name
        and (GOLDEN_ROOT / "dict" / f"{d.slug}.config.json").exists()
    ]
    assert docs, f"no golden-backed corpus document for {schema_name}"
    for doc in docs:
        produced = rt.json_dumps(rt.read_config_dict(doc))
        assert produced == rt.golden_json(f"dict/{doc.slug}.config.json")


# -- T034: the structural coercion assertion ---------------------------------


def test_every_typed_field_resolves_to_a_non_passthrough_adapter():
    typed_fields = {"uuid": "UuidType", "node_role": "NodeRoleType", "adopted": "BoolType", "online": "BoolType"}
    spec = derive_named("network_map", "NodeType")
    for name, xsd_type in typed_fields.items():
        field = spec.field(name)
        assert field is not None, name
        assert field.xsd_type == xsd_type
        assert adapter_for(field.xsd_type) is not PASSTHROUGH, name


def test_every_free_text_field_resolves_to_passthrough():
    free_text_fields = {"mac", "name", "ip", "role_id", "alias", "hostname"}
    spec = derive_named("network_map", "NodeType")
    for name in free_text_fields:
        field = spec.field(name)
        assert field is not None, name
        assert adapter_for(field.xsd_type) is PASSTHROUGH, name


def test_the_two_sets_cover_every_declared_field():
    """No field is missing from both lists above — silently untested."""
    typed = {"uuid", "node_role", "adopted", "online"}
    free_text = {"mac", "name", "ip", "role_id", "alias", "hostname"}
    spec = derive_named("network_map", "NodeType")
    assert {f.name for f in spec.fields} == typed | free_text
