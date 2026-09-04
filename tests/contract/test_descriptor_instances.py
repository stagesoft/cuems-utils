"""T007 / FR-022a / SC-003 — a constructible empty instance per complex type.

Feature 010, US3. The one descriptor capability this feature adds. It exists
because a **nested object is not a field default**: ``getTemplateOutputStructure``
in the UI needs the *shape* of a cue's output — geometry, region, mapping —
which no combination of the five per-field facts supplies.

**Scope note, recorded rather than glossed.** SC-003 says every complex type
yields an instance that "validates against its own schema". A *root-bound* type
can be validated directly, because a document can be built from it. A non-root
complex type cannot be validated standalone by the schema machinery as it
stands — there is no document for it to be the root of. So this file asserts:

* **every** complex type across all six schemas yields an instance, and that
  instance carries the descriptor's declared defaults for every declared field
  (the checkable reading of "carrying its declared defaults");
* **root-bound** types additionally validate against their schema.

If SC-003's literal reading is required for non-root types too, that needs
machinery this feature has not planned — flagged rather than silently narrowed.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES, SCHEMA_ROOTS


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
def test_root_bound_instances_validate_against_their_schema(manager, schema_name):
    """The part of SC-003 the machinery can express today."""
    _, SchemaName = _public()
    root = SCHEMA_ROOTS[schema_name]
    member = SchemaName(schema_name)
    document = manager.build_instance_document(member)
    assert document is not None, f"no document built for {schema_name} root {root}"
    manager.validate_document(member, document)
