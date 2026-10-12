"""Enumeration facets, read per schema and never by bare QName (T054, FR-029, research R4).

``BoolType`` *used to be* declared independently in ``script.xsd``,
``settings.xsd`` and ``network_map.xsd`` — one namespace, no imports, three
separate definitions — and reading a facet by a bare type name would silently
resolve to whichever schema happened to load first. **Feature 014 deleted all
three** in favour of the built-in ``xs:boolean``, so that particular hazard is
gone; several other types are still duplicated the same way
(``CanvasRegionType``, ``DateType``, ``NonEmptyString``, …), so the rule
stands: every assertion here goes through a specific ``(schema, type)`` pair,
never a bare QName.
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


def test_bool_type_is_gone_from_every_schema():
    """Retired premise (014, X1), inverted rather than deleted.

    This asserted that ``BoolType`` *resolves independently per schema* — the
    same QName declared three times, each read from its own schema object. That
    was the anti-drift property F2 cared about, and X1 dissolved it: the three
    declarations are **deleted** and the elements carry the built-in
    ``xs:boolean``, so there is no name to diverge.

    Kept as the assertion that the deletion is total. A declaration creeping
    back into one schema and not the others is the X14-class defect the
    original test guarded against, and this is what now catches it.
    """
    for schema_name in ("script", "settings", "network_map"):
        assert "BoolType" not in get_schema(schema_name).types, schema_name


def test_a_boolean_field_is_no_longer_reported_as_an_enumeration():
    """The finding that decided X1, asserted at the descriptor.

    ``autoload`` and ``adopted`` came back with
    ``enum_values=('True', 'False')`` — structurally identical to ``post_go``'s
    three values — so a descriptor-driven form rendered a two-option dropdown
    where a checkbox belongs, and feature 010's T031a would have verified that
    as correct.
    """
    descriptor = SchemaDescriptor()
    for schema_name, type_name, field_name in (
        ("script", "CueType", "autoload"),
        ("network_map", "NodeType", "adopted"),
    ):
        field = _field(descriptor, schema_name, type_name, field_name)
        assert field.enum_values is None, (schema_name, field_name, field.enum_values)
        assert "bool" in field.xsd_type.lower(), field.xsd_type


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
