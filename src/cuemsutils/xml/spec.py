"""Derived field specifications: ``FieldSpec`` and ``TypeSpec`` (T038, T039).

One ordered, typed description per complex type, derived from the XSD at load
time. This is the "single source of truth" the feature is named for: field
order, field type and cardinality all come from here, and nothing else in the
engine is allowed to decide them.

Derivation is **lazy and memoised** (research R8). ``CueListType`` contains
``CueListContentsType`` which contains ``CueListType`` — a genuine cycle, so
eager recursion does not terminate. A ``FieldSpec`` therefore holds a *reference*
to its child type, resolved on demand. The same memo is what bounds derivation
count by the number of distinct types (56 across all six schemas) rather than by
the number of objects, which is SC-PERF-002.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

from xmlschema.validators import XsdAnyElement

from .schema import get_schema, root_element


class FieldKind(Enum):
    ELEMENT = "element"
    ATTRIBUTE = "attribute"
    WILDCARD = "wildcard"


class ModelGroup(Enum):
    SEQUENCE = "sequence"
    CHOICE = "choice"
    ALL = "all"


@dataclass(frozen=True)
class TypeKey:
    """How a complex type is named.

    Either a type qname or, for the anonymous root types, an element path
    (research R3 — there is no ``CuemsScriptType``). Carries the schema name
    because two schemas declare different types under the same qname (R4), so a
    key without it is ambiguous in exactly the place it matters most.
    """

    schema: str
    name: str
    is_path: bool = False

    def __str__(self) -> str:
        return f"{self.schema}:{'/' if self.is_path else ''}{self.name}"


@dataclass(frozen=True)
class FieldSpec:
    """One element or attribute of one complex type."""

    name: str
    xsd_type: str | None
    required: bool
    repeated: bool
    order: int
    kind: FieldKind
    child: TypeKey | None = None
    #: ``(class value, type)`` in schema order. Empty when the element has no
    #: conditional type. A tuple of pairs, not a dict: this dataclass is frozen
    #: and hashed, and :func:`derive` is ``lru_cache``d (data-model §5.1).
    alternatives: tuple[tuple[str, TypeKey], ...] = ()

    @property
    def is_wildcard(self) -> bool:
        return self.kind is FieldKind.WILDCARD


@dataclass(frozen=True)
class TypeSpec:
    """The ordered field set for one complex type."""

    key: TypeKey
    fields: tuple[FieldSpec, ...]
    model_group: ModelGroup | None
    wildcard: bool
    mixed: bool
    attributes: tuple[str, ...] = field(default_factory=tuple)

    @property
    def ordered(self) -> bool:
        """Whether the schema imposes an order on this type's children.

        ``xs:all`` says explicitly that it does not. Everything else does.
        """
        return self.model_group is not ModelGroup.ALL

    @property
    def field_names(self) -> tuple[str, ...]:
        return tuple(f.name for f in self.fields)

    def field(self, name: str) -> FieldSpec | None:
        for spec in self.fields:
            if spec.name == name:
                return spec
        return None

    def order_keys(self, keys) -> list:
        """Apply FR-001's two-branch ordering rule to ``keys``.

        This is the **only** place in the engine that decides element order, and
        it branches on the content model — never on a type name, never on a
        hardcoded field list (FR-001a, FR-002).

        * **Ordered** models (``xs:sequence``, ``xs:choice``) emit in schema
          declaration order. Authoritative.
        * **Order-free** models (``xs:all``) emit in **arrival order**: the
          schema states no order is imposed, so there is none to honour, and
          preserving the order the fields came in is what reproduces today's
          bytes.

        Keys with no matching field keep their arrival order and sort last —
        wildcard content and the leaked ``schemaLocation`` both land here, and
        dropping them would silently lose data.

        On the ``xs:all`` branch (FR-001b, corrected 2026-08-11): an earlier
        draft specified a **sorted-key** tie-break, on the evidence of
        library-written files whose roots happen to be alphabetical. Measured
        against the full corpus, today's builder iterates the object's items and
        so preserves insertion order; two of the four captured ``CuemsScript``
        roots are *not* sorted. Sorting would rewrite the root element of every
        hand-authored script — the very regression the rule was written to
        prevent.
        """
        keys = list(keys)
        if not self.ordered:
            return keys

        position = {spec.name: spec.order for spec in self.fields}
        known = [k for k in keys if k in position]
        unknown = [k for k in keys if k not in position]
        known.sort(key=lambda k: position[k])
        return known + unknown


#: E2: ``XsdAlternative.path`` is the test text. Nothing else is read.
_CLASS_TEST = re.compile(r"^@class='([^']+)'$")


def class_alternatives(element, schema_name: str) -> tuple[tuple[str, TypeKey], ...]:
    """Conditional ``(class value, type)`` pairs, in schema order.

    The unconditional alternative is not one of them — it is the fallback
    :func:`fallback_alternative` returns. A test that is not exactly
    ``@class='VALUE'`` is a derivation error, not a skipped alternative.
    """
    pairs = []
    for alt in getattr(element, "alternatives", None) or ():
        path = getattr(alt, "path", None)
        if path is None:
            continue
        text = path if isinstance(path, str) else str(path)
        match = _CLASS_TEST.fullmatch(text)
        if match is None:
            raise ValueError(
                f"derivation error: alternative test {text!r} is not exactly @class='VALUE'"
            )
        key = _type_key(schema_name, alt.type)
        if key is None:
            raise ValueError(
                f"derivation error: alternative for class {match.group(1)!r} "
                "has no named complex type"
            )
        pairs.append((match.group(1), key))
    return tuple(pairs)


def fallback_alternative(element, schema_name: str) -> TypeKey | None:
    """The unconditional alternative's type, or ``None`` when there is none.

    ``xmlschema`` requires every alternative type to derive from the element's
    declared type. ``VideoDeviceType`` does not derive from ``DeviceType``, so
    the element's declared type is a class-only base and this function is the
    type an unknown class actually validates as. With no alternatives it
    returns ``None`` and the declared type stays ``FieldSpec.child``.
    """
    chosen = None
    for alt in getattr(element, "alternatives", None) or ():
        if getattr(alt, "path", None) is None:
            chosen = _type_key(schema_name, alt.type)
    return chosen


def _type_key(schema_name: str, xsd_type) -> TypeKey | None:
    """A key for ``xsd_type``, or ``None`` if it is simple."""
    if xsd_type is None or xsd_type.is_simple():
        return None
    if xsd_type.local_name:
        return TypeKey(schema_name, xsd_type.local_name)
    return None


def _model_group(xsd_type) -> ModelGroup | None:
    content = getattr(xsd_type, "content", None)
    model = getattr(content, "model", None)
    return ModelGroup(model) if model else None


def _derive_fields(schema_name: str, xsd_type) -> tuple[tuple[FieldSpec, ...], bool]:
    content = getattr(xsd_type, "content", None)
    if content is None:
        return (), False

    fields: list[FieldSpec] = []
    has_wildcard = False
    for index, element in enumerate(content.iter_elements()):
        if isinstance(element, XsdAnyElement):
            # Nothing about a wildcard's children is derivable — no name, no
            # type, no cardinality (research R6). ``UiPropertiesType`` is the
            # only one, and its content takes the documented fallback (FR-009).
            has_wildcard = True
            fields.append(
                FieldSpec(
                    name="",
                    xsd_type=None,
                    required=False,
                    repeated=True,
                    order=index,
                    kind=FieldKind.WILDCARD,
                )
            )
            continue

        alternatives = class_alternatives(element, schema_name)
        fallback = fallback_alternative(element, schema_name)
        fields.append(
            FieldSpec(
                name=element.local_name,
                xsd_type=element.type.local_name if element.type is not None else None,
                required=element.min_occurs > 0,
                # ``is_single()``, not ``max_occurs != 1``. Repetition usually
                # lives on the enclosing model group rather than on the element:
                # ``CueListContentsType`` is an ``xs:choice`` with
                # ``maxOccurs="unbounded"`` whose members are each declared
                # ``1..1``, so ``max_occurs`` says "single" for every cue type
                # in every cue list. ``is_single()`` accounts for the group,
                # and it is what the current converter keys off when deciding
                # the repeated-element shape (FR-014).
                repeated=not element.is_single(),
                order=index,
                kind=FieldKind.ELEMENT,
                child=fallback if fallback is not None else _type_key(schema_name, element.type),
                alternatives=alternatives,
            )
        )
    return tuple(fields), has_wildcard


#: Attributes the object model does not own (feature 008, ITEM E, research R1).
#:
#: A list of two, each with its reason, rather than a special case buried in a
#: conditional:
#:
#: * ``doc_version`` — the document-version marker (FR-048a). It is declared
#:   in all six schemas as of this feature, so unlike ``schemaLocation`` below
#:   it **would** otherwise be derived like any other attribute: a
#:   ``FieldSpec`` on the type, a coherence-check expectation, a wire key. It
#:   is a document property, not a domain field — written by
#:   ``mapper.build_document`` beside ``xsi:schemaLocation`` and read by a
#:   pre-validation probe (``xml/versioning.py``, research R2) — and it must
#:   stay invisible to the object model, so it is excluded here rather than
#:   bound.
#: * ``schemaLocation`` — the ``xsi:`` namespaced attribute every document
#:   carries. Listed for symmetry ("the attributes the model does not own" is
#:   a list of two, not one) even though it needs no active filtering here:
#:   it is never a *declared* attribute of a complex type (it lives in the
#:   ``xsi:`` namespace, not this schema's), so ``xsd_type.attributes`` never
#:   enumerates it in the first place. It leaks into the decoded dict through
#:   a different path (mapper.py, spec.py's undescribed-content handling).
ATTRIBUTES_THE_MODEL_DOES_NOT_OWN = frozenset({"doc_version", "schemaLocation"})


def _derive_attributes(schema_name: str, xsd_type, start: int) -> tuple[FieldSpec, ...]:
    """Attributes, recorded separately from elements (research R7).

    Declared attributes come in three kinds (feature 013, research R4):

    * ``universe_num`` on ``DmxUniverseType``, which also declares an element
      of the same name. With the converter's ``attr_prefix=''`` the decoded
      key is ambiguous between the two. That ambiguity is pre-existing and
      preserved, not resolved: fixing it would be a wire change (FR-010, R7).
    * ``doc_version`` on every root type, excluded deliberately — see
      :data:`ATTRIBUTES_THE_MODEL_DOES_NOT_OWN`. ``schemaLocation`` is listed
      there for symmetry and is never a declared attribute of a complex type,
      so ``xsd_type.attributes`` does not enumerate it.
    * ``class``, the device-class discriminator. It is a dict key named
      ``class``. No Python ``@property`` takes that name, and it is not added
      to :data:`ATTRIBUTES_THE_MODEL_DOES_NOT_OWN`: it is domain data and it
      round-trips.

    ``UiPropertiesType``'s ``anyAttribute`` is a wildcard (``name is None``),
    not a named declaration, and the loop below skips it.
    """
    declared = getattr(xsd_type, "attributes", None) or {}
    specs = []
    for offset, (name, attribute) in enumerate(declared.items()):
        if name is None:  # the anyAttribute wildcard
            continue
        if name in ATTRIBUTES_THE_MODEL_DOES_NOT_OWN:
            continue
        specs.append(
            FieldSpec(
                name=name,
                xsd_type=(
                    attribute.type.local_name if attribute.type is not None else None
                ),
                required=getattr(attribute, "use", "optional") == "required",
                repeated=False,
                order=start + offset,
                kind=FieldKind.ATTRIBUTE,
            )
        )
    return tuple(specs)


@lru_cache(maxsize=None)
def derive(key: TypeKey) -> TypeSpec:
    """The ordered field set for one complex type, memoised on ``key``.

    The memo is not an optimisation bolted on afterwards — it is what makes
    derivation terminate at all on cyclic content models, and what bounds the
    derivation count for SC-PERF-002.
    """
    schema = get_schema(key.schema)
    xsd_type = _resolve(key, schema)

    element_fields, has_wildcard = _derive_fields(key.schema, xsd_type)
    attribute_fields = _derive_attributes(key.schema, xsd_type, len(element_fields))

    return TypeSpec(
        key=key,
        fields=element_fields + attribute_fields,
        model_group=_model_group(xsd_type),
        wildcard=has_wildcard,
        mixed=bool(getattr(xsd_type, "mixed", False)),
        attributes=tuple(spec.name for spec in attribute_fields),
    )


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


def derive_named(schema_name: str, type_name: str) -> TypeSpec:
    return derive(TypeKey(schema_name, type_name))


def derive_path(schema_name: str, element_path: str) -> TypeSpec:
    return derive(TypeKey(schema_name, element_path, is_path=True))


def derive_root(schema_name: str) -> TypeSpec:
    """The spec for a schema's root element type, which is always anonymous."""
    return derive_path(schema_name, root_element(schema_name).local_name)


def derivation_count() -> int:
    """How many distinct types have been derived. Used by SC-PERF-002."""
    return derive.cache_info().currsize


def clear_cache() -> None:
    derive.cache_clear()
