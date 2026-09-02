"""``SchemaDescriptor`` covers all six schemas, field set for field set (T053, SC-010).

The descriptor never re-walks the XSD (research R3) — it calls
``spec.derive()`` for structure. This is therefore a construction-integrity
test, not a derivation test: it protects against the descriptor silently
dropping, renaming or reordering a field on the way from ``FieldSpec`` to
``FieldDescriptor``.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import derive


def test_descriptor_declares_all_six_schemas():
    assert tuple(SchemaDescriptor().schemas) == SCHEMA_NAMES
    assert len(SchemaDescriptor().schemas) == 6


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_schema_produces_at_least_one_type_descriptor(schema_name):
    descriptor = SchemaDescriptor()
    assert descriptor.types(schema_name), f"{schema_name} produced nothing"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_type_descriptors_field_set_equals_the_content_model(schema_name):
    descriptor = SchemaDescriptor()
    for type_descriptor in descriptor.types(schema_name):
        spec = derive(type_descriptor.key)
        assert (
            tuple(f.name for f in type_descriptor.fields) == spec.field_names
        ), type_descriptor.key


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_descriptor_covers_every_bound_type_in_the_registry(schema_name):
    """Named and path-bound types are both represented, not just one kind."""
    registry = get_registry(schema_name)
    descriptor = SchemaDescriptor()
    keys = {t.key for t in descriptor.types(schema_name)}
    for name in registry.bound_type_names:
        assert any(k.name == name and not k.is_path for k in keys), name
    for path in registry.bound_path_names:
        assert any(k.name == path and k.is_path for k in keys), path
