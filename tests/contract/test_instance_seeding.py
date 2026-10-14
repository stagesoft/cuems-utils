"""G3, T056/T057 — the seeding table's completeness and validity
(contracts/seeding-rules.md, guards 1 and 2).

Guard 1: every pattern-restricted simple type reachable from any instance
in the six schemas has a ``_PATTERN_SEEDS`` entry — a sixth pattern added
to any schema must fail here rather than silently seeding ``None``.

Guard 2: every entry in the two closed tables (``_PATTERN_SEEDS``,
``_BUILTIN_SEEDS``) validates against its own declared type.
"""

from __future__ import annotations

import re

from cuemsutils.xml.descriptor import _BUILTIN_SEEDS, _PATTERN_SEEDS, SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema


def _reachable_simple_types():
    """Every ``(schema, type name)`` a field across the six schemas'
    complex types resolves its ``xsd_type`` to — the same universe
    ``_seed_for`` is ever called against."""
    found = set()
    for schema_name in SCHEMA_NAMES:
        for type_descriptor in SchemaDescriptor().types(schema_name):
            for field in type_descriptor.fields:
                if field.xsd_type is not None:
                    found.add((schema_name, field.xsd_type))
    return found


def test_every_pattern_restricted_type_reachable_has_a_table_entry():
    """Guard 1. A pattern-restricted type with no entry would seed
    ``None`` silently — this is the closed-set claim FR-028 depends on."""
    missing = []
    for schema_name, type_name in _reachable_simple_types():
        simple_type = get_schema(schema_name).types.get(type_name)
        if simple_type is None or not simple_type.is_simple():
            continue
        if simple_type.enumeration or getattr(simple_type, "member_types", None):
            continue
        facets = simple_type.facets or {}
        has_pattern = any(k.rsplit("}", 1)[-1] == "pattern" for k in facets)
        has_numeric_or_length_facet = any(
            k.rsplit("}", 1)[-1] in ("minInclusive", "minExclusive", "maxInclusive", "minLength")
            for k in facets
        )
        if has_pattern and not has_numeric_or_length_facet and type_name not in _PATTERN_SEEDS:
            missing.append((schema_name, type_name))
    assert not missing, f"pattern-restricted type(s) with no seed table entry: {missing}"


def test_every_builtin_reachable_has_a_table_entry():
    """The built-in half of guard 1 — a seventh built-in type added to any
    schema must fail here rather than seeding ``None``."""
    missing = set()
    for schema_name, type_name in _reachable_simple_types():
        simple_type = get_schema(schema_name).types.get(type_name)
        if simple_type is not None:
            continue  # locally declared; not a built-in
        if type_name not in _BUILTIN_SEEDS:
            missing.add(type_name)
    assert not missing, f"built-in type(s) with no seed table entry: {sorted(missing)}"


def test_every_pattern_table_entry_validates_against_its_own_type():
    """Guard 2 — the irreducible residue's own correctness. A table entry
    that does not match its pattern would otherwise surface only as an
    unsaveable instance in a consumer, which is exactly the failure this
    feature closes (FR-023)."""
    for type_name, seed in sorted(_PATTERN_SEEDS.items()):
        matched_anywhere = False
        for schema_name in SCHEMA_NAMES:
            simple_type = get_schema(schema_name).types.get(type_name)
            if simple_type is None:
                continue
            for key, facet in (simple_type.facets or {}).items():
                if key.rsplit("}", 1)[-1] != "pattern":
                    continue
                matched_anywhere = True
                for pattern in facet.patterns:
                    assert re.fullmatch(pattern.pattern, seed), (
                        f"{type_name}'s seed {seed!r} does not match {pattern.pattern!r}"
                    )
        assert matched_anywhere, f"{type_name} is declared in no schema"


def test_every_builtin_table_entry_has_the_declared_python_type():
    expected_python_type = {
        "boolean": bool,
        "string": str,
        "positiveInteger": int,
        "nonNegativeInteger": int,
        "integer": int,
        "float": float,
        "byte": int,
    }
    for builtin, seed in sorted(_BUILTIN_SEEDS.items()):
        assert isinstance(seed, expected_python_type[builtin]), (builtin, seed)
        if builtin == "positiveInteger":
            assert seed > 0, "0 is invalid for positiveInteger"
        if builtin == "nonNegativeInteger":
            assert seed >= 0


def test_the_tables_cover_the_closed_counts():
    """The repository's own recorded counts (contracts/seeding-rules.md):
    5 pattern entries, 7 built-ins."""
    assert len(_PATTERN_SEEDS) == 5
    assert len(_BUILTIN_SEEDS) == 7
