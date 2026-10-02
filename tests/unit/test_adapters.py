"""Adapter unit tests (T035).

The adapters are the seam where the schema's declared type replaces
``str_to_value``'s guess. Every assertion here is a value that the old
heuristic got wrong, or a shape the UI depends on.
"""

from __future__ import annotations

import pytest

from cuemsutils.cues.FadeCue import FadeCurveType
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.adapters import ADAPTERS, PASSTHROUGH, adapter_for

UUID_STR = "8726353c-5c8c-41fe-bab7-1b9d765ced77"


# --- booleans: the UI contract -------------------------------------------


@pytest.mark.parametrize("raw,expected", [("True", True), ("False", False)])
def test_bool_decodes_from_the_capitalised_strings(raw, expected):
    assert adapter_for("BoolType").decode(raw) is expected


@pytest.mark.parametrize("value,expected", [(True, "True"), (False, "False")])
def test_bool_round_trips_to_strings_in_both_output_directions(value, expected):
    """C5 — ``to_wire`` emits a **string**, not a JSON boolean.

    ``cms:BoolType`` is an ``xs:string`` enum (X1). The Angular UI reads
    ``"True"``/``"False"``; emitting real booleans would break it without a
    line of frontend code changing.
    """
    adapter = adapter_for("BoolType")
    assert adapter.to_lexical(value) == expected
    assert adapter.to_wire(value) == expected
    assert not isinstance(adapter.to_wire(value), bool)


def test_bool_none_stays_none():
    adapter = adapter_for("BoolType")
    assert adapter.decode(None) is None
    assert adapter.to_lexical(None) is None


#: Everything a ``cms:BoolType`` field must **refuse** on ingestion.
#:
#: The first ten are exactly the strings
#: :func:`test_free_text_is_never_coerced_to_a_boolean` pins against
#: ``NameStringType``, restated here against the *boolean* side of the same
#: seam — that test closed the defect class on one side only, and ``"yes"``,
#: ``"on"`` and ``"y"`` used to decode to ``False`` here.
REFUSED_BOOLS = [
    "n", "y", "t", "f", "N", "Y", "on", "off", "no", "yes",
    "true", "false", "TRUE", "FALSE", "True ", " True",
    "1", "0", "", "banana", "None",
]


@pytest.mark.parametrize("raw", REFUSED_BOOLS)
def test_bool_refuses_anything_the_schema_does_not_declare(raw):
    """A value that is not ``"True"``/``"False"`` is an error, not ``False``.

    ``decode`` used to be ``raw == "True"``, so **every** other string became
    ``False``: a payload carrying ``"true"`` disabled a cue, the document was
    schema-valid (``False`` is a legal ``BoolType``), T1 could not refuse it,
    T2 has no rule for it and the ``LoadReport`` said ``CLEAN``. A disabled cue
    does not fire, and nothing anywhere reported it.

    This is the one adapter that could turn a bad value into a *good,
    different* one. ``_Int``/``_Float``/``_CTimecodeAdapter`` raise; the enum
    and uuid adapters pass a detectably wrong value through for ``save``'s T1
    to refuse on the facet. Only this one manufactured a plausible value.

    See ``specs/planning/booltype-silent-false-coercion-defect.md``.
    """
    with pytest.raises(ValueError, match="cms:BoolType"):
        adapter_for("BoolType").decode(raw)


@pytest.mark.parametrize("raw", [1, 0, 2, -1, 1.0, [], {}, object()])
def test_bool_refuses_non_bool_non_string_values(raw):
    """``bool(raw)`` is gone, deliberately.

    It was what made ``1`` decode to ``True`` while ``"1"`` decoded to
    ``False`` — an inconsistency with no caller: unreachable from XML (T1
    admits only the two literals) and from a well-formed payload (a JSON
    boolean arrives as a ``bool``).
    """
    with pytest.raises(ValueError, match="cms:BoolType"):
        adapter_for("BoolType").decode(raw)


def test_bool_still_accepts_what_the_schema_and_json_actually_carry():
    """The accepted set, stated positively so the refusal above is bounded.

    Nothing that a valid document or a well-formed payload can carry is
    refused: the two XSD literals, both Python booleans, and ``None`` for an
    absent optional element.
    """
    adapter = adapter_for("BoolType")
    assert adapter.decode("True") is True
    assert adapter.decode("False") is False
    assert adapter.decode(True) is True
    assert adapter.decode(False) is False
    assert adapter.decode(None) is None


# --- the defect class str_to_value created --------------------------------


@pytest.mark.parametrize("text", ["n", "y", "t", "f", "N", "Y", "on", "off", "no", "yes"])
def test_free_text_is_never_coerced_to_a_boolean(text):
    """ClickUp 869cqbpxa, made unrepresentable rather than denylisted.

    ``str_to_value`` ran every scalar through ``strtobool``, so a cue named
    ``n`` was persisted as ``False``. Here ``NameStringType`` is declared a
    string, so there is nothing to guess.
    """
    assert adapter_for("NameStringType").decode(text) == text


@pytest.mark.parametrize("text", ["none", "null", "NULL", "None"])
def test_nullish_names_survive(text):
    """The harder half of the same defect.

    A cue named ``none`` decoded to ``None``, serialized to ``<name/>``, and
    then failed ``NameStringType``'s ``minLength=1`` — a hard save error rather
    than silent corruption.
    """
    assert adapter_for("NameStringType").decode(text) == text


@pytest.mark.parametrize("text", ["1", "0", "42", "007"])
def test_numeric_looking_names_stay_strings(text):
    assert adapter_for("NameStringType").decode(text) == text
    assert adapter_for("DescriptionStringType").decode(text) == text


def test_keys_that_should_coerce_still_do():
    """The control. Without it, "never coerce anything" would pass above."""
    assert adapter_for("LoopType").decode("1") == 1
    assert adapter_for("PercentType").decode("42") == 42
    assert adapter_for("UnitFloat").decode("0.5") == 0.5


# --- identifiers ----------------------------------------------------------


def test_uuid_decodes_to_a_uuid_object():
    decoded = adapter_for("UuidType").decode(UUID_STR)
    assert isinstance(decoded, Uuid)
    assert str(decoded) == UUID_STR


def test_target_permits_empty_and_decodes_it_to_none():
    """``TargetType`` allows the empty string — a cue with no target.

    Handled in the adapter because ``Uuid('')`` raises, so a caller that
    forgot this case would turn "no target" into a crash.
    """
    adapter = adapter_for("TargetType")
    assert adapter.decode("") is None
    assert adapter.decode(None) is None
    assert isinstance(adapter.decode(UUID_STR), Uuid)


def test_uuid_is_idempotent_on_already_decoded_values():
    """Objects built in Python arrive already typed."""
    existing = Uuid(UUID_STR)
    assert adapter_for("UuidType").decode(existing) is existing


# --- the complex wrapper (R5) --------------------------------------------


def test_ctimecode_decodes_from_its_wrapper():
    decoded = adapter_for("CTimecodeType").decode({"CTimecode": "00:00:02.000"})
    assert isinstance(decoded, CTimecode)


def test_ctimecode_to_wire_keeps_the_wrapper_shape():
    """C5 — ``{"CTimecode": "..."}`` is the shape the UI reads."""
    wire = adapter_for("CTimecodeType").to_wire(CTimecode("00:00:02.000"))
    assert wire == {"CTimecode": "00:00:02.000"}


def test_ctimecode_to_lexical_is_the_bare_text():
    """The XML carries the value inside a ``<CTimecode>`` child element.

    So the *element text* is bare — the wrapper is structure, not text. Getting
    this backwards would emit the dict repr into the document.
    """
    assert adapter_for("CTimecodeType").to_lexical(CTimecode("00:00:02.000")) == "00:00:02.000"


def test_ctimecode_empty_wrapper_is_none():
    assert adapter_for("CTimecodeType").decode({"CTimecode": None}) is None


# --- enums ----------------------------------------------------------------


def test_fade_curve_enum_round_trips():
    adapter = adapter_for("FadeCurveType")
    assert adapter.decode("linear") is FadeCurveType.linear
    assert adapter.to_lexical(FadeCurveType.linear) == "linear"
    assert adapter.to_wire(FadeCurveType.linear) == "linear"


def test_unknown_enum_member_passes_through_rather_than_raising():
    """FR-015 — validation belongs to the schema, not to serialization.

    The schema has already rejected out-of-enumeration values in any document
    that reaches here, and objects built in Python are not schema-checked at
    all. Raising would turn a validation concern into a save-time crash.
    """
    assert adapter_for("FadeCurveType").decode("not_a_curve") == "not_a_curve"


@pytest.mark.parametrize(
    "type_name", ["PostGoType", "ActionType", "FadeTypeType", "FadeModeType"]
)
def test_enum_types_without_a_python_class_stay_strings(type_name):
    """Four of the six enum types have no Python enum in the object model.

    They are plain strings today, constrained by the schema's enumeration.
    Giving them real enum classes would change the object model, which is
    feature 004's explicit non-goal.
    """
    adapter = adapter_for(type_name)
    assert adapter.decode("pause") == "pause"
    assert adapter.to_wire("pause") == "pause"


# --- binding and defaults -------------------------------------------------


def test_unbound_type_falls_through_to_passthrough():
    """A simple type with no bespoke codec is served by ``xmlschema``.

    Registry totality (C7) is about *complex* types; requiring an adapter for
    every simple type would be busywork that adds no guarantee.
    """
    assert adapter_for("SomeTypeThatDoesNotExist") is PASSTHROUGH
    assert adapter_for(None) is PASSTHROUGH


def test_adapters_are_bound_by_type_qname_not_by_key_name():
    """The structural reason the denylist retires.

    ``STRING_TYPED_KEYS`` had to enumerate key *names*, and carried defensive
    entries for keys that were not yet reachable, because a name is not a type.
    Every key of a given XSD type now gets the same treatment automatically.
    """
    assert all(isinstance(name, str) for name in ADAPTERS)
    assert "name" not in ADAPTERS
    assert "NameStringType" in ADAPTERS


@pytest.mark.parametrize("type_name", sorted(ADAPTERS))
def test_every_adapter_implements_all_three_directions(type_name):
    adapter = ADAPTERS[type_name]
    assert callable(adapter.decode)
    assert callable(adapter.to_lexical)
    assert callable(adapter.to_wire)
    assert adapter.decode(None) is None
    assert adapter.to_lexical(None) is None
