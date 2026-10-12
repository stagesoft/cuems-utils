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

#: Feature 014 retyped ``cms:BoolType`` to the built-in, and ``xmlschema``
#: reports a built-in's ``type.name`` **qualified**. There is no ``BoolType``
#: left to ask for, which is the point — the name is gone from all three
#: schemas, not merely unused.
BOOLEAN_TYPE = "{http://www.w3.org/2001/XMLSchema}boolean"


# --- booleans: the UI contract, as feature 014 left it ---------------------
#
# This section used to pin the **opposite** contract, and the change is
# deliberate rather than a drift. Before feature 014, ``cms:BoolType`` was an
# ``xs:string`` enum of ``"True"``/``"False"``, so ``decode`` carried the
# asymmetry and both output directions emitted the capitalised strings. X1
# retyped it to the standard ``xs:boolean``: the XML now carries lowercase and
# the wire carries a real JSON boolean.
#
# What is **retired** here, named rather than quietly deleted:
#
# * ``test_bool_decodes_from_the_capitalised_strings`` — ``"True"`` is now a
#   *refused* spelling, so the assertion inverts (see
#   ``test_bool_refuses_the_retired_capitalised_spelling``).
# * ``test_bool_round_trips_to_strings_in_both_output_directions`` — its whole
#   premise was that ``to_wire`` must **not** return a ``bool``. It now must.
#
# What **survives unchanged** is the thing that matters most: ``decode`` is
# strict, because ``from_json`` has no document to validate against and this
# adapter is that path's structural check. ``be3e86e`` established that and 014
# widens the accepted set rather than loosening the posture.


@pytest.mark.parametrize(
    "raw,expected",
    [("true", True), ("false", False), ("1", True), ("0", False),
     (True, True), (False, False)],
)
def test_bool_decodes_xs_booleans_whole_lexical_space(raw, expected):
    """``true|false|1|0`` plus a real ``bool`` from a JSON payload."""
    assert adapter_for(BOOLEAN_TYPE).decode(raw) is expected


@pytest.mark.parametrize("value,expected", [(True, "true"), (False, "false")])
def test_bool_writes_the_canonical_lowercase_form(value, expected):
    """``str(True)`` is ``'True'``, which ``xs:boolean`` rejects.

    So ``to_lexical`` is overridden, and it is the one thing standing between
    the object model and an unwritable document: ``Mapper._lexical`` is the only
    producer of element text on a stdlib-``ElementTree`` write path, and
    ``save`` validates before writing.
    """
    assert adapter_for(BOOLEAN_TYPE).to_lexical(value) == expected


@pytest.mark.parametrize("value", [True, False])
def test_bool_wire_form_is_a_real_boolean(value):
    """``to_wire`` is deleted; ``_Passthrough``'s is inherited.

    The replacement for ``test_bool_round_trips_to_strings_in_both_output_directions``,
    whose premise X1 retires. Both halves are asserted — ``is value`` **and**
    ``not isinstance(..., str)`` — because ``"True" == True`` is ``False`` while
    ``bool("False")`` is ``True``, and a test checking only truthiness would
    pass on either encoding.
    """
    adapter = adapter_for(BOOLEAN_TYPE)
    assert adapter.to_wire(value) is value
    assert not isinstance(adapter.to_wire(value), str)


def test_bool_none_stays_none():
    adapter = adapter_for(BOOLEAN_TYPE)
    assert adapter.decode(None) is None
    assert adapter.to_lexical(None) is None
    assert adapter.to_wire(None) is None


#: Everything a boolean field must **refuse** on ingestion.
#:
#: The first ten are the strings
#: :func:`test_free_text_is_never_coerced_to_a_boolean` pins against
#: ``NameStringType``, restated here against the *boolean* side of the same
#: seam — ``be3e86e``'s point, which 014 keeps.
#:
#: ``"True"``/``"False"`` lead the list because they are what **changed**: they
#: were the only accepted spellings and are now refused. That is the one place
#: this feature is not purely additive for a client, and the reason
#: ``cuems-frontend``'s ``sequence.component.ts:997`` is hard-coupled to it.
REFUSED_BOOLS = [
    "True", "False", "TRUE", "FALSE",
    "n", "y", "t", "f", "N", "Y", "on", "off", "no", "yes",
    "True ", " true", "", "banana", "None", "2", "-1", "1.0",
]


@pytest.mark.parametrize("raw", REFUSED_BOOLS)
def test_bool_refuses_anything_outside_xs_booleans_lexical_space(raw):
    """A value that is not in the space is an **error**, never a guess.

    ``decode`` used to be ``raw == "True"``, so every other string became
    ``False``: a payload carrying ``"true"`` disabled a cue, the document was
    schema-valid, and nothing reported it (``be3e86e``). The posture is
    unchanged here; only the accepted set moved.
    """
    with pytest.raises(ValueError, match="xs:boolean"):
        adapter_for(BOOLEAN_TYPE).decode(raw)


def test_bool_refuses_the_retired_capitalised_spelling():
    """Stated on its own, because it is the migration-visible change.

    A client still sending ``"True"`` gets a ``SchemaError`` out of
    ``from_json`` rather than a silently wrong value — which is the whole
    reason this is a coordinated ecosystem step and not a tidy-up.
    """
    with pytest.raises(ValueError, match="xs:boolean"):
        adapter_for(BOOLEAN_TYPE).decode("True")


@pytest.mark.parametrize("raw", [2, -1, 1.0, [], {}, object()])
def test_bool_refuses_non_bool_non_string_values(raw):
    """``int``/``float`` are refused even though ``1`` and ``0`` are accepted
    **as text**. ``xs:boolean``'s lexical space is strings; a numeric ``1`` is
    a caller's type confusion, not a lexical form.
    """
    with pytest.raises(ValueError, match="xs:boolean"):
        adapter_for(BOOLEAN_TYPE).decode(raw)


def test_bool_round_trip_is_the_identity_on_values():
    """``decode(to_lexical(x)) is x`` — the half-applied-change detector.

    A change that updates the writer and not the reader passes both
    one-directional tests and fails this one.

    Note it is **not** the identity on *text*: ``decode("1")`` is ``True`` and
    ``to_lexical(True)`` is ``"true"``. ``<enabled>1</enabled>`` is valid
    ``xs:boolean``, so a hand-edited document can carry a form our writer never
    emits. That is a property to know, not a defect.
    """
    adapter = adapter_for(BOOLEAN_TYPE)
    for value in (True, False):
        assert adapter.decode(adapter.to_lexical(value)) is value
    assert adapter.decode("1") is True
    assert adapter.to_lexical(True) == "true"

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


def test_md5_is_bound_explicitly_and_never_coerced():
    """Feature 014 T040 — bound rather than correct by consequence.

    ``Md5Type`` restricts ``xs:string``, so it would decode correctly through
    ``PASSTHROUGH`` too. It is bound anyway for the reason the table's own
    ``NodeUuidType`` comment gives: a type that is right by *consequence* goes
    wrong silently the day something changes around it.

    The value being pinned is the one the input document warns about
    (``specs/planning/stored-media-values-preimplementation.md`` §5): an md5 of
    all digits — about one in a million — which an older parser coerced to an
    ``int``, so that the next save failed the schema.
    """
    assert "Md5Type" in ADAPTERS, "bound by name, not reached by fallthrough"
    assert adapter_for("Md5Type") is not PASSTHROUGH

    all_digits = "1" * 32
    assert adapter_for("Md5Type").decode(all_digits) == all_digits
    assert isinstance(adapter_for("Md5Type").decode(all_digits), str)

    # The "digits with one e" half of that warning — a valid md5 that Python
    # would read as a float in exponent notation.
    exponent = "1" * 31 + "e"
    assert adapter_for("Md5Type").decode(exponent) == exponent
    assert isinstance(adapter_for("Md5Type").decode("1e9" + "0" * 29), str)


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

