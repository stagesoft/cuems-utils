# `xsd_type_for` — standalone XSD type resolution, built and withdrawn

**Status**: not in the codebase. Built 2026-09-04 during feature 010's wave 0, withdrawn the same
day when the requirement that motivated it was narrowed. **Recorded here for out-of-the-box
recovery** — the code below is the exact implementation and its exact tests, both green when
removed.
**Removed from**: `src/cuemsutils/xml/spec.py` and `tests/contract/test_xsd_type_resolution.py`
**Written per** this repo's `specs/planning/` convention (see `nodeconf-atomization.md`).

## Why it existed

Feature 010's SC-003 briefly required that **every complex type's constructible instance validate
against its own schema**. Two kinds of type exist and they are reached differently:

- a **named global type** is in the schema's type table under its qname;
- an **anonymous, path-bound type** has no qname, and is reached by walking its element path from
  the schema's global element.

Measured 2026-09-04 across all six schemas:

| Schema | Named | Path-bound |
|---|---|---|
| script | 29 | 2 |
| settings | 6 | 2 |
| network_map | 2 | 1 |
| project_mappings | 11 | 1 |
| project_settings | 1 | 1 |
| outputs | 1 | 1 |
| **Total** | **50** | **8** |

Both kinds are `Xsd11ComplexType` and both carry `validate`/`is_valid` in `xmlschema` 3.4.3, so a
caller that can resolve a `TypeKey` to its type can validate **any** complex type standalone — no
wrapper document, no schema edit. `xsd_type_for` was the single entry point that resolved either
kind, so call sites stopped branching on whether a type had a qname.

**The split is named versus anonymous, not root versus non-root.** A named type nested five levels
deep validates standalone perfectly well. An earlier reading of SC-003 had that wrong and would have
narrowed the criterion to document roots — 8 of 58 rather than 58 of 58.

## Why it was withdrawn

SC-003 was narrowed again, on measurement: **12 of the 58** complex types have a required field with
no usable default, so a defaults-only instance cannot validate for them. The descriptor's
constructible instance became a **seed the consumer fills**, explicitly not required to be
schema-valid — and with that clause gone, `xsd_type_for` had no caller in the library.

It is withdrawn rather than kept because this project's own standard (D17) is that dead code is
removed, not left resolving. It is recorded rather than deleted because the machinery is correct,
was measured, and the next requirement that needs per-type validation should not have to rediscover
any of it.

## When to bring it back

Any requirement that needs to validate a **fragment** against a specific complex type, rather than a
whole document against its root. Plausible candidates, none of them scheduled:

- validating an editor's partial payload for one cue type before it becomes a document;
- checking that a descriptor-driven form's output conforms to the type it was generated from;
- a stricter reading of a future SC-003 successor.

Note it resolves types; it does **not** encode a Python object into XML. `XsdComplexType.validate`
takes an XML source (an `Element`, or a string), not a `dict` — a dict route needs
`XsdComplexType.encode`, which validates while encoding. That distinction cost a measurement here
and is worth keeping.

## The code

Restores into `src/cuemsutils/xml/spec.py`, immediately after `_resolve` and before `derive_named`.
It depends only on `_resolve` and `get_schema`, both already in that module.

```python
def xsd_type_for(key: TypeKey):
    """The ``XsdComplexType`` a :class:`TypeKey` names, for **either** kind.

    A named global type is looked up in the schema's type table; an anonymous,
    path-bound type is reached by walking its element path. Both are
    ``Xsd11ComplexType`` and both carry ``validate``/``is_valid``, so a caller
    holding the resolved type can validate any complex type **standalone** —
    against the type itself, with no document wrapped around it.

    That matters because the two kinds are not "root versus nested": 50 of the
    58 complex types across the six schemas are named, including deeply nested
    ones, and only 8 are path-bound (the document roots and their immediate
    anonymous children). Resolving through the element is what makes those 8
    validatable too, rather than leaving them to be checked only in place.

    Delegates to :func:`_resolve` rather than repeating its walk. A second path
    walker beside the first is the duplication (F15) this rebuild exists to end,
    and the two would drift the first time the schema shape changed.
    """
    return _resolve(key, get_schema(key.schema))
```

**The delegate it relies on**, unchanged and still in the codebase — reproduced so a restorer can
confirm the contract it depends on has not moved:

```python
def _resolve(key: TypeKey, schema):
    if not key.is_path:
        return schema.types[key.name]

    # An element path: walk it from the schema's global element. This is how
    # the anonymous root types are reached (R3) — they have no qname to look up.
    parts = key.name.split("/")
    element = schema.elements[parts[0]]
    for part in parts[1:]:
        element = next(
            child
            for child in element.type.content.iter_elements()
            if getattr(child, "local_name", None) == part
        )
    return element.type
```

## The tests

Restores as `tests/contract/test_xsd_type_resolution.py`. All nine passed when removed.

```python
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
```

## Recovery checklist

1. Paste the function into `src/cuemsutils/xml/spec.py` after `_resolve`.
2. Paste the test file back as `tests/contract/test_xsd_type_resolution.py`.
3. Re-measure the 50/8 split before trusting the numbers above — this repository has twice found
   counts in comments that had gone stale (`TOTAL_COMPLEX_TYPES` was `56` against a true `58`, and
   feature 010's exempt-set line numbers had all moved).
4. Give it a caller in the same change. It was withdrawn for having none, and restoring it without
   one repeats that.
