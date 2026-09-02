"""The schema descriptor (ITEM D, T062-T065) — data-model.md §3.

Reuses ``spec.derive()`` for structure — names, types, cardinality, order —
and adds what ``derive`` does not carry, from three sources that are not the
schema (research R3):

* ``enum_values`` — read from the resolved simple type's ``xs:enumeration``
  facets, **per schema** (research R4): the six schemas share one namespace
  with no imports between them, so a QName like ``BoolType`` is declared more
  than once, and resolving it without the schema name would silently pick one
  at random.
* ``default`` — the bound model class's accumulated ``declared_defaults()``,
  reached through the registry binding (research R5). A type with no bound
  model (``GENERIC``) has no defaults, which is a real answer, not a gap.
* ``repairability`` — derived from the registered T2 rule surface (research
  R8), per the three ordered rules in data-model.md §3.1.

This is a **separate module from ``spec.py``**, not an extension of
``FieldSpec`` (research R3): ``FieldSpec`` is on the hot path (``lru_cache``d,
consulted on every decode and encode) and answers "what shape is this
document"; the descriptor is consulted only when generating a template or
repairing a field, and answers "what may a user put here, and what does it
default to" — a question two of whose three inputs are not the schema at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from ..helpers import Unset
from .registry import all_registries, get_registry
from .schema import SCHEMA_NAMES, get_schema
from .spec import FieldKind, TypeKey, derive


class Repairability(Enum):
    REPAIRABLE = "repairable"
    UNREPAIRABLE = "unrepairable"


@dataclass(frozen=True)
class FieldDescriptor:
    """One field, structure plus what the descriptor adds to it."""

    name: str
    xsd_type: str | None
    required: bool
    repeated: bool
    order: int
    kind: FieldKind
    enum_values: tuple[str, ...] | None
    default: Any
    repairability: Repairability


@dataclass(frozen=True)
class TypeDescriptor:
    """The described field set for one complex type, declared order."""

    key: TypeKey
    fields: tuple[FieldDescriptor, ...]


class RepairabilityTargetError(RuntimeError):
    """A rule's ``(class_name, field_name)`` target resolved to no field.

    Raised rather than dropped (data-model.md §3.1): a target that resolves
    to nothing is a stale rule or a renamed field, and silently dropping it
    would leave the field classified by rules 2/3 and quietly widen what
    counts as repairable.
    """

    def __init__(self, rule_name: str, class_name: str, field_name: str):
        self.rule_name = rule_name
        self.class_name = class_name
        self.field_name = field_name
        super().__init__(
            f"rule {rule_name!r} targets ({class_name!r}, {field_name!r}), "
            f"which is bound to no XSD type in any of the six schemas"
        )


def _enum_values(schema_name: str, xsd_type_name: str | None) -> tuple[str, ...] | None:
    """The ``xs:enumeration`` facets for ``xsd_type_name``, in ``schema_name``.

    Resolved **per schema** (research R4) — never by a bare type name, since
    the same QName (``BoolType``) is declared independently in three of the
    six schemas. Handles the one union enumeration in the bundle
    (``AutoOrIntLatencyMsType``): a union's ``.enumeration`` is ``None`` on
    the union itself, and the facet lives on one of its member types.
    """
    if xsd_type_name is None:
        return None
    schema = get_schema(schema_name)
    simple_type = schema.types.get(xsd_type_name)
    if simple_type is None or not simple_type.is_simple():
        return None

    values = simple_type.enumeration
    if values:
        return tuple(values)

    member_types = getattr(simple_type, "member_types", None)
    if not member_types:
        return None
    merged: list[str] = []
    for member in member_types:
        for value in getattr(member, "enumeration", None) or ():
            if value not in merged:
                merged.append(value)
    return tuple(merged) if merged else None


def _defaults_for(key: TypeKey) -> dict[str, Any]:
    """The bound model class's accumulated defaults for ``key`` (research R5).

    ``{}`` for a ``GENERIC``-bound or unbound type — every field then reports
    ``Unset``, which is the real answer, not a gap.
    """
    registry = get_registry(key.schema)
    binding = (
        registry.binding_for_path(key.name)
        if key.is_path
        else registry.binding_for(key.name)
    )
    if binding is None or binding.is_generic or not isinstance(binding.model, type):
        return {}
    return dict(binding.model.declared_defaults())


_repairability_cache: dict[tuple[TypeKey, str], bool] | None = None


def _class_type_keys() -> dict[str, tuple[TypeKey, ...]]:
    """``model.__name__ -> every TypeKey that class is bound to``, all six schemas.

    A rule targets a **model class name**; ``TypeDescriptor.key`` carries the
    **XSD type name** (data-model.md §3.1) — this is the join between the two
    name spaces. A class bound to more than one XSD type (across schemas or
    within one) appears under every key it is bound to, which is the correct
    reading: the rule fires on the object, whichever type produced it.
    """
    mapping: dict[str, list[TypeKey]] = {}
    for registry in all_registries().values():
        for binding in registry.bindings():
            if not isinstance(binding.model, type):
                continue
            mapping.setdefault(binding.model.__name__, []).append(binding.key)
    return {name: tuple(keys) for name, keys in mapping.items()}


def _repairability_map() -> dict[tuple[TypeKey, str], bool]:
    """``(TypeKey, field_name) -> the targeting rule's declared repairable``.

    Built once and cached: it is a global join over every registered rule and
    every schema's bindings, not a per-schema or per-type computation.
    """
    global _repairability_cache
    if _repairability_cache is None:
        from .validators import RULES

        class_keys = _class_type_keys()
        mapping: dict[tuple[TypeKey, str], bool] = {}
        for rule in RULES.values():
            for class_name, field_name in rule.applies_to:
                keys = class_keys.get(class_name, ())
                if not keys:
                    raise RepairabilityTargetError(rule.name, class_name, field_name)
                for key in keys:
                    mapping[(key, field_name)] = rule.repairable
        _repairability_cache = mapping
    return _repairability_cache


def _repairability(key: TypeKey, field_name: str, default: Any) -> Repairability:
    """data-model.md §3.1's three ordered rules, rule 2 outranking rule 1."""
    if default is Unset:
        return Repairability.UNREPAIRABLE
    declared = _repairability_map().get((key, field_name))
    if declared is not None:
        return Repairability.REPAIRABLE if declared else Repairability.UNREPAIRABLE
    return Repairability.REPAIRABLE


class SchemaDescriptor:
    """One descriptor over all six schemas — data-model.md §3."""

    schemas: tuple[str, ...] = SCHEMA_NAMES

    def types(self, schema: str) -> tuple[TypeDescriptor, ...]:
        """Every complex type this schema declares, named and path-bound alike."""
        registry = get_registry(schema)
        keys = [
            TypeKey(schema, name) for name in sorted(registry.bound_type_names)
        ]
        keys += [
            TypeKey(schema, path, is_path=True)
            for path in sorted(registry.bound_path_names)
        ]
        return tuple(self.describe(key) for key in keys)

    def describe(self, key: TypeKey) -> TypeDescriptor:
        spec = derive(key)
        defaults = _defaults_for(key)
        fields = tuple(
            FieldDescriptor(
                name=field.name,
                xsd_type=field.xsd_type,
                required=field.required,
                repeated=field.repeated,
                order=field.order,
                kind=field.kind,
                enum_values=_enum_values(key.schema, field.xsd_type),
                default=defaults.get(field.name, Unset),
                repairability=_repairability(
                    key, field.name, defaults.get(field.name, Unset)
                ),
            )
            for field in spec.fields
        )
        return TypeDescriptor(key=key, fields=fields)


def clear_cache() -> None:
    global _repairability_cache
    _repairability_cache = None
