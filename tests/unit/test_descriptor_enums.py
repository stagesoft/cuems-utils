"""Enumeration facets, read per schema and never by bare QName (T054, FR-029, research R4).

``BoolType`` is declared independently in ``script.xsd``, ``settings.xsd`` and
``network_map.xsd`` — one namespace, no imports, three separate definitions.
Reading a facet by a bare type name would silently resolve to whichever
schema happened to load first; every assertion here goes through a specific
``(schema, type)`` pair to prove that never happens.
"""

from __future__ import annotations

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema
from cuemsutils.xml.spec import TypeKey


def _field(descriptor, schema, type_name, field_name, *, is_path=False):
    key = TypeKey(schema, type_name, is_path=is_path)
    type_descriptor = descriptor.describe(key)
    return next(f for f in type_descriptor.fields if f.name == field_name)


def test_every_declared_enum_field_matches_its_own_schemas_facets():
    """Cross-checked against ``xmlschema``'s own facet list, per schema."""
    descriptor = SchemaDescriptor()
    checked = 0
    for schema_name in SCHEMA_NAMES:
        schema = get_schema(schema_name)
        for type_descriptor in descriptor.types(schema_name):
            for field in type_descriptor.fields:
                if field.xsd_type is None:
                    continue
                simple_type = schema.types.get(field.xsd_type)
                if simple_type is None or not simple_type.is_simple():
                    continue
                facets = simple_type.enumeration
                if not facets:
                    continue
                assert field.enum_values is not None, (schema_name, field.name)
                assert set(field.enum_values) == set(facets), (schema_name, field.name)
                checked += 1
    assert checked > 0


def test_bool_type_resolves_independently_per_schema():
    """The same QName, three schemas, each read from its own schema object."""
    script_values = get_schema("script").types["BoolType"].enumeration
    settings_values = get_schema("settings").types["BoolType"].enumeration
    network_map_values = get_schema("network_map").types["BoolType"].enumeration

    assert set(script_values) == {"True", "False"}
    assert set(settings_values) == {"True", "False"}
    assert set(network_map_values) == {"True", "False"}

    descriptor = SchemaDescriptor()
    script_field = _field(descriptor, "script", "CueType", "autoload")
    network_map_field = _field(descriptor, "network_map", "NodeType", "adopted")
    assert set(script_field.enum_values) == {"True", "False"}
    assert set(network_map_field.enum_values) == {"True", "False"}


def test_union_enumeration_is_read_from_its_member_type():
    """``AutoOrIntLatencyMsType`` is a union; the facet lives on one member."""
    descriptor = SchemaDescriptor()
    field = _field(descriptor, "settings", "AudioPlayerType", "output_latency_ms")
    assert field.enum_values is not None
    assert "auto" in field.enum_values


def test_a_non_enumerated_field_carries_no_enum_values():
    descriptor = SchemaDescriptor()
    field = _field(descriptor, "script", "MediaType", "file_name")
    assert field.enum_values is None
