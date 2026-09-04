"""T007 / FR-022a / SC-003 — a constructible empty instance per complex type.

Feature 010, US3. The one descriptor capability this feature adds. It exists
because a **nested object is not a field default**: ``getTemplateOutputStructure``
in the UI needs the *shape* of a cue's output — geometry, region, mapping —
which no combination of the five per-field facts supplies.

**Scope, measured 2026-09-04.** SC-003 requires every complex type's instance to
validate against its schema, and every one can — by the route its type admits:

* a **named global type** (50 of 58) is in the schema's type table;
* an **anonymous, path-bound type** (8 of 58 — the document roots and their
  immediate anonymous children) is reached by walking its element path.

Both are ``Xsd11ComplexType`` and both carry ``validate``, so ``spec.xsd_type_for``
resolves either and **every one of the 58 validates standalone** — one route, no
branching here. The split is **named versus anonymous**, not root versus
non-root: a named type nested five levels deep validates standalone perfectly
well. An earlier draft of this file asserted the latter and would have narrowed
the criterion to 8 types of 58.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import xsd_type_for


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
def test_every_instance_validates_standalone(manager, schema_name):
    """SC-003 in full — **58 of 58, one route**.

    No per-kind branching at the call site: ``xsd_type_for`` resolves a named
    type and an anonymous path-bound one alike, and both carry ``validate``. The
    earlier draft of this test branched on whether the type had a qname; the
    resolver removed the need."""
    for type_descriptor in _types(schema_name):
        element = manager.build_instance_element(type_descriptor.key)
        xsd_type_for(type_descriptor.key).validate(element)
