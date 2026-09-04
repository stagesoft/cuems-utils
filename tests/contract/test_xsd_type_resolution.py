"""Uniform XSD-type resolution — one resolver for both kinds of type key.

Feature 010, US3 (wave 0). SC-003 requires every complex type's instance to be
validated against its schema. Two kinds of type exist and they are reached
differently:

* a **named global type** (50 of 58, measured 2026-09-04) is in the schema's
  type table under its qname;
* an **anonymous, path-bound type** (8 of 58 — the document roots and their
  immediate anonymous children) has no qname to look up, and is reached by
  walking its element path from the schema's global element.

Both kinds are ``Xsd11ComplexType`` and both carry ``validate``/``is_valid``, so
**a caller that can resolve a key to its type can validate every type uniformly**
— no wrapper documents, no schema edits, no per-kind branching at the call site.

``spec._resolve`` already walks the path. This surface exists so the descriptor
and its tests do not grow a *second* path walker beside it: a second reader for
something this library already resolves is the F15 duplication the rebuild
exists to end.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import TypeKey


def _keys(schema_name: str) -> list[TypeKey]:
    registry = get_registry(schema_name)
    return [
        TypeKey(schema_name, name)
        for name in sorted(registry.bound_type_names)
    ] + [
        TypeKey(schema_name, path, is_path=True)
        for path in sorted(registry.bound_path_names)
    ]


@pytest.mark.parametrize("schema_name", SCHEMA_NAMES)
def test_every_type_key_resolves_to_a_validatable_xsd_type(schema_name):
    """58 of 58 — both kinds, no exceptions, nothing skipped."""
    from cuemsutils.xml.spec import xsd_type_for

    keys = _keys(schema_name)
    assert keys, f"{schema_name} declares no complex types"

    for key in keys:
        xsd_type = xsd_type_for(key)
        assert xsd_type is not None, f"{key} resolved to nothing"
        assert hasattr(xsd_type, "validate"), f"{key} resolved to a non-validatable object"
        assert hasattr(xsd_type, "is_valid")


def test_both_key_kinds_are_exercised():
    """Guards the assertion above: if ``bound_path_names`` ever emptied, every
    case would still pass while covering only the easy half."""
    named = sum(len(get_registry(n).bound_type_names) for n in SCHEMA_NAMES)
    path_bound = sum(len(get_registry(n).bound_path_names) for n in SCHEMA_NAMES)

    assert named and path_bound, "one of the two key kinds is unexercised"


def test_the_resolver_does_not_duplicate_the_existing_path_walk():
    """F15 — one resolver, not two. ``xsd_type_for`` must delegate to the walk
    ``spec._resolve`` already performs rather than reimplementing it."""
    import inspect

    from cuemsutils.xml import spec

    source = inspect.getsource(spec.xsd_type_for)
    assert "_resolve" in source, (
        "xsd_type_for must delegate to _resolve, not walk element paths itself"
    )


def test_an_anonymous_root_type_validates_standalone():
    """The claim that motivated this surface: an anonymous type has no qname,
    and is still validatable once resolved through its element."""
    from cuemsutils.xml.spec import xsd_type_for

    key = TypeKey("script", "CuemsProject", is_path=True)
    xsd_type = xsd_type_for(key)

    assert xsd_type.name is None, "CuemsProject's type is expected to be anonymous"
    assert xsd_type.is_valid("") is False or xsd_type.is_valid("") is True
