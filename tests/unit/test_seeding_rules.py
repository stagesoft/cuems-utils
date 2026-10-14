"""G3, T063/T064 — the eight ordered seeding rules and the seven built-ins
(contracts/seeding-rules.md), keyed on the **resolved simple type**, never
on the field's name.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import (
    _BUILTIN_SEEDS,
    _PATTERN_SEEDS,
    _seed_for,
)
from cuemsutils.xml.schema import get_schema

# -- rule 1: enumeration -------------------------------------------------


@pytest.mark.parametrize(
    "schema_name,type_name,expected",
    [
        ("script", "PostGoType", "pause"),
        ("script", "ActionType", "play"),
        ("script", "FadeCurveType", "linear"),
        ("network_map", "NodeRoleType", "controller"),
    ],
)
def test_rule_1_enumeration_is_the_first_declared_value(schema_name, type_name, expected):
    simple_type = get_schema(schema_name).types.get(type_name)
    assert simple_type.enumeration[0] == expected, (type_name, simple_type.enumeration)
    assert _seed_for(schema_name, type_name) == expected


# -- rule 2: union --------------------------------------------------------


def test_rule_2_union_prefers_an_enumerated_member():
    """``NodeUuidType``'s ``NotProvisionedUuidType`` member is itself a
    one-value enumeration — the sentinel — which rule 2 must prefer over
    applying rules 3-7 to the other, pattern-restricted member."""
    seed = _seed_for("network_map", "NodeUuidType")
    assert seed == "00000000-0000-0000-0000-000000000000"


def test_rule_2_union_auto_or_int_latency():
    seed = _seed_for("settings", "AutoOrIntLatencyMsType")
    assert seed == "auto"


# -- rules 3-6: facets -----------------------------------------------------


@pytest.mark.parametrize(
    "schema_name,type_name,expected",
    [
        ("script", "PercentType", 0),
        ("script", "ChannelNumberType", 0),
        ("script", "ChannelValueType", 0),
        ("settings", "NonPrivilegedPort", 1024),
    ],
)
def test_rule_3_min_inclusive(schema_name, type_name, expected):
    assert _seed_for(schema_name, type_name) == expected


def test_rule_3_date_type_is_lexical_not_a_datetime_object():
    """The facet's own bound is an ``elementpath`` ``DateTime``, not a
    string — the seed must be the lexical form or the XML writer emits an
    empty string for it (measured: ``CuemsScript``'s ``created``/
    ``modified`` otherwise fail ``xs:assert modified &gt;= created``)."""
    seed = _seed_for("script", "DateType")
    assert seed == "2020-01-01T00:00:00"
    assert isinstance(seed, str)


def test_rule_4_min_exclusive_and_max_inclusive():
    """``PositiveUnitFloat`` (``minExclusive 0.0``, ``maxInclusive 1.0``) ->
    the inclusive bound, since "smallest valid value" is not expressible
    for an exclusive float bound."""
    assert _seed_for("script", "PositiveUnitFloat") == 1.0


def test_rule_5_only_max_inclusive():
    assert _seed_for("settings", "IntLatencyMsType") == 0


@pytest.mark.parametrize(
    "schema_name,type_name,expected",
    [
        ("script", "DescriptionStringType", ""),  # minLength 0
        ("script", "NameStringType", "x"),  # minLength 1
    ],
)
def test_rule_6_length_bounded_no_pattern(schema_name, type_name, expected):
    assert _seed_for(schema_name, type_name) == expected


# -- rule 7: the pattern table ----------------------------------------------


@pytest.mark.parametrize("type_name,seed", sorted(_PATTERN_SEEDS.items()))
def test_rule_7_pattern_table_entries_validate_against_their_own_type(type_name, seed):
    """Guard 2 (contracts/seeding-rules.md): every table entry validates
    against its own declared type — checked against whichever schema
    declares it (``NonEmptyString``/``TimecodeType``/… are duplicated
    identically across schemas, research R4)."""
    import re

    from cuemsutils.xml.schema import SCHEMA_NAMES

    checked = False
    for schema_name in SCHEMA_NAMES:
        simple_type = get_schema(schema_name).types.get(type_name)
        if simple_type is None:
            continue
        checked = True
        for key, facet in (simple_type.facets or {}).items():
            if key.rsplit("}", 1)[-1] != "pattern":
                continue
            for pattern in facet.patterns:
                assert re.fullmatch(pattern.pattern, seed), (type_name, pattern, seed)
    assert checked, f"{type_name} is declared in no schema"


# -- rule 8: XSD built-ins --------------------------------------------------


@pytest.mark.parametrize("builtin,seed", sorted(_BUILTIN_SEEDS.items()))
def test_rule_8_builtins(builtin, seed):
    assert _seed_for("script", builtin) == seed


def test_all_seven_builtins_are_covered():
    assert len(_BUILTIN_SEEDS) == 7


def test_all_five_pattern_entries_are_covered():
    assert len(_PATTERN_SEEDS) == 5


# -- T064: a callable default is still not invoked, stays visible -------


def test_a_callable_default_is_not_invoked_and_stays_on_the_field():
    from cuemsutils.xml.descriptor import SchemaDescriptor
    from cuemsutils.xml.spec import TypeKey

    descriptor = SchemaDescriptor().describe(TypeKey("script", "AudioCueType"))
    field = next(f for f in descriptor.fields if f.name == "id")
    assert callable(field.default), "AudioCueType.id's default must still be callable"
    # Two independent derivations must agree on the seeded value -- which
    # could only happen if the callable default was never actually called
    # (feature 010's own reasoning, unchanged by G3).
    other = SchemaDescriptor().describe(TypeKey("script", "AudioCueType"))
    other_field = next(f for f in other.fields if f.name == "id")
    assert other_field.default is field.default
