"""T007 / FR-022a / SC-003 — a constructible empty instance per complex type.

Feature 010, US3. The one descriptor capability this feature adds. It exists
because a **nested object is not a field default**: ``getTemplateOutputStructure``
in the UI needs the *shape* of a cue's output — geometry, region, mapping —
which no combination of the five per-field facts supplies.

**Scope, measured 2026-09-04.** SC-003 requires every complex type's instance to
validate against its schema, and every one can — by the route its type admits:

* a **named global type** (50 of 58) validates **standalone**. `xmlschema` 3.4.3
  exposes ``validate``/``is_valid`` on ``XsdComplexType``, so a fragment is
  checked against the type directly, with no document around it;
* an **anonymous, path-bound type** (8 of 58 — the document roots and their
  immediate anonymous children) has no entry in the schema's type table, so it
  is validated **in place**, at its path in the enclosing document.

The split is **named versus anonymous**, not root versus non-root: a named type
nested five levels deep validates standalone perfectly well. An earlier draft of
this file asserted the latter and would have narrowed the criterion to 8 types
of 58.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema


def _types(schema_name: str):
    return SchemaDescriptor().types(schema_name)




def _public():
    """Imported at call time, not at module import.

    A module-level import of a symbol that does not exist yet is a **collection
    error**, and a collection error interrupts the whole suite — 2573 unrelated
    tests stop running until wave 0 lands. Deferring it keeps these tests
    honestly red (failed, not skipped, not errored) while the rest of the suite
    still runs on a shared branch.
    """
    from cuemsutils.tools.ConfigManager import ConfigManager, SchemaName

    return ConfigManager, SchemaName


@pytest.fixture
def manager():
    ConfigManager, _ = _public()
    return ConfigManager(load_all=False)


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_complex_type_yields_an_instance(manager, schema_name):
    """100% of types, counted — not the one type the UI happened to need."""
    described = _types(schema_name)
    assert described, f"{schema_name} declares no complex types"

    for type_descriptor in described:
        instance = manager.build_instance(type_descriptor.key)
        assert instance is not None, f"no instance for {type_descriptor.key}"


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_instance_carries_the_declared_defaults(manager, schema_name):
    """The instance is the descriptor's own answer, not a second opinion: every
    declared field is present and equal to the default the descriptor emits."""
    for type_descriptor in _types(schema_name):
        instance = manager.build_instance(type_descriptor.key)
        for field in type_descriptor.fields:
            assert field.name in instance, (
                f"{type_descriptor.key}.{field.name} missing from the instance"
            )
            assert instance[field.name] == field.default, (
                f"{type_descriptor.key}.{field.name} is {instance[field.name]!r}, "
                f"descriptor default is {field.default!r}"
            )


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_instance_validates_by_the_route_its_type_admits(manager, schema_name):
    """SC-003 in full — 58 of 58, not 8 of 58."""
    _, SchemaName = _public()
    member = SchemaName(schema_name)
    schema = get_schema(schema_name)

    for type_descriptor in _types(schema_name):
        element = manager.build_instance_element(type_descriptor.key)
        qname = type_descriptor.key.qualified_name
        if qname in schema.types:
            # Named global type: validated standalone, against the type itself.
            schema.types[qname].validate(element)
        else:
            # Anonymous, path-bound: validated in place, at its path.
            manager.validate_document(member, manager.build_instance_document(member))
