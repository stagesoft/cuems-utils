"""Scalar and wrapper codecs, bound by XSD type qname (T040).

The small, closed, hand-written seam the design allows (Q11(c)). Everything
else — order, membership, cardinality — is derived; these are the conversions
the schema states a type for but cannot itself perform.

**This is what retires ``str_to_value``** (FR-003). The old parser guessed a
value's Python type from its *text* — running every scalar through ``int`` →
``float`` → ``strtobool`` → ``Uuid`` — which is why a cue named ``n`` was saved
as ``False`` and one named ``none`` as ``None`` (ClickUp 869cqbpxa), and why a
key-name denylist had to exist to hold the damage back. Here the type is
declared, so there is nothing to guess and the defect class becomes
unrepresentable rather than denylisted.

Three directions, and they are genuinely three:

``decode``       wire/lexical value -> Python object
``to_lexical``   Python object -> XML element text
``to_wire``      Python object -> JSON-safe scalar

``to_lexical`` and ``to_wire`` differ because the UI payload is JSON while the
XML is text. Booleans are the case that matters: ``cms:BoolType`` is an
``xs:string`` enum of ``"True"``/``"False"`` (X1), so **both** directions emit
the *strings*. Decoding them to JSON booleans would be the most natural
"improvement" available here and would break every consumer of the payload at
once (C5).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Protocol

from ..tools.CTimecode import CTimecode
from ..tools.Uuid import Uuid


class Adapter(Protocol):
    def decode(self, raw: Any) -> Any: ...
    def to_lexical(self, obj: Any) -> str | None: ...
    def to_wire(self, obj: Any) -> Any: ...


class _Passthrough:
    """No conversion. The default, and deliberately the default.

    An unbound type reaching this adapter keeps whatever ``xmlschema`` decoded
    it to, which is exactly today's behaviour for the types no bespoke handler
    ever matched.
    """

    def decode(self, raw):
        return raw

    def to_lexical(self, obj):
        return None if obj is None else str(obj)

    def to_wire(self, obj):
        return obj


class _String(_Passthrough):
    """Free text: never coerced, in either direction.

    ``name``, ``description`` and ``file_name`` are declared as string types in
    the schema, which is the whole reason ``STRING_TYPED_KEYS`` can retire — the
    protection moves from a hand-maintained denylist of *key names* to the
    type the schema already states.
    """

    def decode(self, raw):
        return raw


class _Bool:
    """``cms:BoolType`` — an ``xs:string`` enum of ``"True"`` / ``"False"``.

    Python ``bool`` in the object model, the capitalised *strings* on the wire
    and in the XML. ``str(True) == "True"`` is what the current builder emits,
    so ``to_lexical`` needs no special case; the asymmetry is all in ``decode``.
    """

    def decode(self, raw):
        if raw is None or isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            return raw == "True"
        return bool(raw)

    def to_lexical(self, obj):
        return None if obj is None else str(obj)

    def to_wire(self, obj):
        return None if obj is None else str(obj)


class _Int:
    """``PercentType``, ``LoopType``, ``ChannelNumberType``, ``ChannelValueType``."""

    def decode(self, raw):
        if raw is None or isinstance(raw, int):
            return raw
        return int(raw)

    def to_lexical(self, obj):
        return None if obj is None else str(obj)

    def to_wire(self, obj):
        return obj


class _Float:
    """``UnitFloat``, ``PositiveUnitFloat``."""

    def decode(self, raw):
        if raw is None or isinstance(raw, float):
            return raw
        return float(raw)

    def to_lexical(self, obj):
        return None if obj is None else str(obj)

    def to_wire(self, obj):
        return obj


class _UuidAdapter:
    """``UuidType`` and ``TargetType``.

    ``TargetType`` additionally permits the empty string, which decodes to
    ``None`` — a cue with no target. That is why the empty case is handled here
    rather than left to the caller: ``Uuid('')`` raises.
    """

    def decode(self, raw):
        if raw is None or raw == "":
            return None
        if isinstance(raw, Uuid):
            return raw
        try:
            return Uuid(str(raw))
        except ValueError:
            # Not a valid uuid4 — kept as the raw string.
            #
            # ``Uuid`` enforces the uuid4 shape (version nibble 4, variant
            # 8-b), which the **nil** uuid
            # ``00000000-0000-0000-0000-000000000000`` fails. It appears three
            # times in ``tests/data/sample_script.json``, so real editor
            # payloads carry it.
            #
            # ``str_to_value`` reached the same result by accident: ``Uuid``
            # was the last candidate in its coercion chain and a ``ValueError``
            # simply fell through to returning the string. FR-015 forbids the
            # engine rejecting what today's parser accepts, so the leniency is
            # kept — but scoped to the declared uuid types instead of applied
            # to every scalar in the document.
            return raw

    def to_lexical(self, obj):
        return None if obj is None else str(obj)

    def to_wire(self, obj):
        return None if obj is None else str(obj)


class _CTimecodeAdapter:
    """``CTimecodeType`` — a **complex** type, not a scalar (research R5).

    It wraps a single ``<CTimecode>`` child, so the decoded shape is
    ``{"CTimecode": "00:00:00.000"}``. That wrapper is stated by the schema
    rather than invented by the converter, and the UI unwraps it itself — which
    is why it survives here unchanged (C5).
    """

    def decode(self, raw):
        if raw is None or isinstance(raw, CTimecode):
            return raw
        if isinstance(raw, dict):
            inner = raw.get("CTimecode")
            return None if inner is None else CTimecode(inner)
        return CTimecode(raw)

    def to_lexical(self, obj):
        return None if obj is None else str(obj)

    def to_wire(self, obj):
        return None if obj is None else {"CTimecode": str(obj)}


class _EnumAdapter:
    """The six enum types.

    Decoding is deliberately **lenient**: an unknown member passes through as
    the raw string rather than raising. The schema has already rejected values
    outside the enumeration by the time a document reaches here, and objects
    built in Python are not schema-checked at all — so raising would turn a
    validation concern into a serialization crash, which is a behaviour change
    (FR-015).
    """

    def __init__(self, enum_class: type[Enum] | None = None):
        self.enum_class = enum_class

    def decode(self, raw):
        if raw is None or self.enum_class is None or isinstance(raw, self.enum_class):
            return raw
        try:
            return self.enum_class(raw)
        except ValueError:
            return raw

    def to_lexical(self, obj):
        if obj is None:
            return None
        return str(obj.value) if isinstance(obj, Enum) else str(obj)

    def to_wire(self, obj):
        if obj is None:
            return None
        return obj.value if isinstance(obj, Enum) else obj


PASSTHROUGH: Adapter = _Passthrough()

#: Bound by **type qname**, complex or simple (R5). Not by key name — binding
#: by name is what ``STRING_TYPED_KEYS`` had to do, and why it needed defensive
#: entries for keys that were not yet reachable.
ADAPTERS: dict[str, Adapter] = {
    # booleans — the UI contract (C5)
    "BoolType": _Bool(),
    # identifiers
    "UuidType": _UuidAdapter(),
    "TargetType": _UuidAdapter(),
    # the complex wrapper (R5)
    "CTimecodeType": _CTimecodeAdapter(),
    # integers
    "PercentType": _Int(),
    "LoopType": _Int(),
    "ChannelNumberType": _Int(),
    "ChannelValueType": _Int(),
    # floats
    "UnitFloat": _Float(),
    "PositiveUnitFloat": _Float(),
    # free text — never coerced, which is what retires STRING_TYPED_KEYS
    "NameStringType": _String(),
    "DescriptionStringType": _String(),
    "EmptyStringType": _String(),
    "TimecodeType": _String(),
    "FadeFunctionIdType": _String(),
    "DateType": _String(),
}


def _register_enums() -> None:
    """Bind the enum adapters to their Python classes.

    Imported lazily inside the function because ``cuemsutils.cues`` imports
    this package back; doing it at module scope is a cycle.
    """
    from ..cues.FadeCue import FadeCurveType

    ADAPTERS["FadeCurveType"] = _EnumAdapter(FadeCurveType)
    # The remaining five enum types (``PostGoType``, ``ActionType``,
    # ``FadeTypeType``, ``FadeModeType``, ``FadeFunctionIdType``) have **no**
    # Python enum class today — they are plain strings in the object model, and
    # the schema's enumeration is what constrains them. They get a leniently
    # decoding adapter with no class, which is a passthrough in practice.
    # Giving them real enums would change the object model, which feature 004
    # does not do.
    for name in ("PostGoType", "ActionType", "FadeTypeType", "FadeModeType"):
        ADAPTERS.setdefault(name, _EnumAdapter(None))


_register_enums()


def adapter_for(xsd_type: str | None) -> Adapter:
    """The adapter bound to ``xsd_type``, or the passthrough.

    Unbound types fall through rather than raising: registry *totality* is
    about complex types (FR-007, C7), while a simple type with no bespoke
    codec is correctly served by ``xmlschema``'s own decoding.
    """
    if xsd_type is None:
        return PASSTHROUGH
    return ADAPTERS.get(xsd_type, PASSTHROUGH)
