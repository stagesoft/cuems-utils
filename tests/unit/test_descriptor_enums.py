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


def test_a_non_enumerated_field_carries_no_enum_values():
    descriptor = SchemaDescriptor()
    field = _field(descriptor, "script", "MediaType", "file_name")
    assert field.enum_values is None


# -- S2 (T052/T053): a union reports a closed choice set only when every
# member is an enumeration ----------------------------------------------------


def test_a_union_with_a_non_enumerated_member_reports_no_closed_set():
    """``AutoOrIntLatencyMsType`` is a union of ``'auto'`` and a numeric
    (``IntLatencyMsType``, ``0..500``) member — narrowed from this file's own
    prior assumption (restated by S2, FR-066, contract C6): ``0``-``500`` are
    valid and a form offering only ``auto`` would silently refuse them."""
    descriptor = SchemaDescriptor()
    for schema_name, type_name, field_name in (
        ("settings", "AudioPlayerType", "output_latency_ms"),
        ("settings", "VideoPlayerType", "output_latency_ms"),
    ):
        field = _field(descriptor, schema_name, type_name, field_name)
        assert field.enum_values is None, (schema_name, field_name, field.enum_values)
        assert "AutoOrIntLatencyMsType" in field.xsd_type


def test_the_three_node_uuid_sites_report_no_closed_set():
    """``NodeUuidType`` unions a pattern-restricted converged member with the
    NOT PROVISIONED sentinel — neither is an enumeration, so no closed set is
    reported (FR-066, data-model.md §4)."""
    descriptor = SchemaDescriptor()
    for schema_name, type_name in (
        ("network_map", "NodeType"),
        ("settings", "NodeConfType"),
        ("project_mappings", "NodeMappingType"),
    ):
        field = _field(descriptor, schema_name, type_name, "uuid")
        assert field.enum_values is None, (schema_name, type_name, field.enum_values)


def test_a_union_whose_every_member_is_an_enumeration_still_merges(monkeypatch):
    """FR-068 — the narrowing is **conditional**, not a removal. No bundled
    schema happens to have this shape, so it is exercised against a scratch
    one, the same way ``tests/unit/test_version_steps.py`` isolates the
    version-step mechanism from any real schema."""
    from xmlschema import XMLSchema11

    import cuemsutils.xml.descriptor as descriptor_module

    scratch = XMLSchema11(
        """<?xml version="1.0"?>
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:simpleType name="A">
            <xs:restriction base="xs:string">
              <xs:enumeration value="x"/>
              <xs:enumeration value="y"/>
            </xs:restriction>
          </xs:simpleType>
          <xs:simpleType name="B">
            <xs:restriction base="xs:string">
              <xs:enumeration value="z"/>
            </xs:restriction>
          </xs:simpleType>
          <xs:simpleType name="AllEnum">
            <xs:union memberTypes="A B"/>
          </xs:simpleType>
        </xs:schema>"""
    )
    monkeypatch.setattr(descriptor_module, "get_schema", lambda name: scratch)

    values = descriptor_module._enum_values("scratch", "AllEnum")

    assert values is not None
    assert set(values) == {"x", "y", "z"}


def test_every_other_descriptor_fact_for_the_affected_fields_is_unchanged():
    """FR-029 — only ``enum_values`` moves for the five sites; nothing else
    about those fields' facts does."""
    descriptor = SchemaDescriptor()
    for schema_name, type_name, field_name in (
        ("network_map", "NodeType", "uuid"),
        ("settings", "NodeConfType", "uuid"),
        ("project_mappings", "NodeMappingType", "uuid"),
        ("settings", "AudioPlayerType", "output_latency_ms"),
        ("settings", "VideoPlayerType", "output_latency_ms"),
    ):
        field = _field(descriptor, schema_name, type_name, field_name)
        assert field.name == field_name
        assert field.xsd_type in ("NodeUuidType", "AutoOrIntLatencyMsType")
        assert field.enum_values is None
