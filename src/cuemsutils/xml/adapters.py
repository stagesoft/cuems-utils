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
XML is text. Booleans used to be the case that matters, and the reason has
inverted: ``cms:BoolType`` was an ``xs:string`` enum of ``"True"``/``"False"``
and **both** directions emitted the strings. **Feature 014 retyped it to
``xs:boolean``** (deferred audit item X1), so the XML carries lowercase
``true``/``false`` and the wire carries a real JSON boolean. This docstring
used to warn that decoding them to JSON booleans "would break every consumer of
the payload at once (C5)" — which was true, and is why the change was made as
one coordinated ecosystem step with its consumers rather than as a tidy-up.
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


class _Bool(_Passthrough):
    """``xs:boolean`` — the standard type, as of feature 014 (X1).

    Python ``bool`` in the object model, **lowercase** ``true``/``false`` in
    the XML, and a real JSON boolean on the wire.

    **This used to be a bespoke ``cms:BoolType``**: an ``xs:string`` restricted
    to ``True``/``False``, the Python ``repr`` spelling. That made it the one
    type in the schema whose wire form was not its natural JSON form — every
    other type, from ints to the ``CTimecode`` wrapper, already projected
    natively — and it made the schema descriptor unable to tell a boolean from
    a two-value string enumeration, so a descriptor-driven form rendered a
    dropdown where a checkbox belongs. That was the argument that retired it;
    the deferral it closes is audit item **X1**.

    **The class survives the retype, and that is not a stylistic choice.**
    ``Mapper._lexical`` is the *only* producer of element text and attribute
    values on the write path, and ``write_tree`` serialises with stdlib
    ``ElementTree``, where ``Element.text`` **must** be a ``str`` — assigning a
    ``bool`` raises ``TypeError: cannot serialize``. Neither ``lxml`` nor
    ``xmlschema`` is in that chain; ``xmlschema`` validates the result and
    never encodes it. So without the ``to_lexical`` below, the inherited
    ``str(obj)`` would write ``True``, which ``xs:boolean`` rejects — and since
    :meth:`CuemsScript.save` validates *before* writing, the library would
    refuse to save any document containing a cue. Deleting this class does not
    corrupt files; it stops them being written at all.

    What moved, in one table:

    ======================  =========================  ========================
    method                  before X1                   after X1
    ======================  =========================  ========================
    ``decode``              strict, two literals        strict, four (plus
                                                        ``bool``); ``"True"``
                                                        now **refused**
    ``to_lexical``          inherited ``str(obj)``      **overridden**, lowercase
    ``to_wire``             overridden, a ``str``       **deleted**, inherits a
                                                        ``bool``
    ======================  =========================  ========================

    ``decode`` stays strict because :meth:`CuemsScript.from_json` has no
    document to validate against, so this adapter *is* that path's structural
    check. The accepted set is ``xs:boolean``'s whole lexical space and nothing
    else: ``true``, ``false``, ``1``, ``0``, and a Python ``bool`` from a JSON
    payload. ``"True"`` is the one spelling that moves from accepted to
    refused, which is why ``cuems-frontend``'s ``sequence.component.ts:997`` is
    coupled to this feature in both directions.

    One consequence worth knowing rather than discovering: ``<enabled>1</enabled>``
    is now schema-valid, so ``to_lexical ∘ decode`` is no longer the identity on
    *text* even though it remains the identity on values.
    """

    #: ``xs:boolean``'s complete lexical space. Not a convenience mapping — the
    #: set is closed, and anything outside it is an error rather than a guess.
    _LITERALS = {"true": True, "false": False, "1": True, "0": False}

    def decode(self, raw):
        if raw is None or isinstance(raw, bool):
            return raw
        try:
            return self._LITERALS[raw]
        except (KeyError, TypeError):
            raise ValueError(
                "xs:boolean accepts 'true', 'false', '1', '0' or a bool; "
                f"got {raw!r}"
            ) from None

    def to_lexical(self, obj):
        """The canonical lowercase form, or ``None`` for an absent optional.

        ``str(True)`` is ``'True'``, which ``xs:boolean`` rejects, so this
        override is the one thing standing between the object model and an
        unwritable document. See the class docstring.
        """
        if obj is None:
            return None
        return "true" if obj else "false"


class _Int(_Passthrough):
    """``PercentType``, ``LoopType``, ``ChannelNumberType``, ``ChannelValueType``."""

    def decode(self, raw):
        if raw is None or isinstance(raw, int):
            return raw
        return int(raw)


class _Float(_Passthrough):
    """``UnitFloat``, ``PositiveUnitFloat``."""

    def decode(self, raw):
        if raw is None or isinstance(raw, float):
            return raw
        return float(raw)


class _UuidAdapter(_Passthrough):
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

    def to_wire(self, obj):
        return self.to_lexical(obj)


class _CTimecodeAdapter(_Passthrough):
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
#: The XSD namespace, so a built-in type can be keyed by the same qualified
#: name ``xmlschema`` reports for it. Feature 014's ``xs:boolean`` is the first
#: built-in to need an adapter: every other bespoke type is a ``cms:`` one, and
#: the table was keyed on the local name alone.
_XSD = "{http://www.w3.org/2001/XMLSchema}"

ADAPTERS: dict[str, Adapter] = {
    # Booleans. ``xmlschema`` reports a built-in's ``type.name`` **qualified**
    # — ``{...XMLSchema}boolean`` — so that is the key that resolves, and the
    # bare ``"boolean"`` is kept beside it because ``FieldSpec.xsd_type``
    # carries the local name in places (the descriptor shows ``xsd_type``
    # unqualified). Both spellings reach the same instance; keying only one
    # was feature 014's sharpest self-inflicted bug: ``_Bool`` stopped being
    # reached at all, ``_Passthrough.to_lexical`` wrote ``str(False)`` ->
    # ``"False"``, and the schema then refused the document the library had
    # just written — 292 failures from a lookup that silently fell through.
    f"{_XSD}boolean": _Bool(),
    "boolean": _Bool(),
    # identifiers
    "UuidType": _UuidAdapter(),
    "TargetType": _UuidAdapter(),
    # feature 012 — the node identity's three names. ``NodeUuidType`` is the
    # one any element references; the two halves are bound as well so that a
    # future element naming one directly does not silently fall through to the
    # passthrough and start decoding an identity as text.
    #
    # Binding these is not optional housekeeping: ``network_map`` runs the
    # adapter table (research R1) and its node ``uuid`` used to be a
    # ``UuidType``. Retyping the element without binding the new name would
    # have retired feature 007's "uuid decodes to Uuid" without a word.
    "NodeUuidType": _UuidAdapter(),
    "ConvergedUuidType": _UuidAdapter(),
    "NotProvisionedUuidType": _UuidAdapter(),
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
    "DateType": _String(),
}


def _register_enums() -> None:
    """Bind the enum adapters to their Python classes.

    Imported lazily inside the function because ``cuemsutils.cues`` imports
    this package back; doing it at module scope is a cycle.
    """
    from ..cues.FadeCue import FadeCurveType
    from ..tools.NodeList import NodeRole

    ADAPTERS["FadeCurveType"] = _EnumAdapter(FadeCurveType)
    ADAPTERS["NodeRoleType"] = _EnumAdapter(NodeRole)
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
