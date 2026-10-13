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

from dataclasses import dataclass, field
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
    instance: dict | list = field(default_factory=dict)
    """A constructible, **wire-shaped and saveable** instance of this type
    (G3, contracts/public-surface.md C3). A ``dict`` for most types; a
    **bare list** for the few pure wrapper containers — ``OutputsType``,
    ``NodeDictType``, ``AudioChannelsType`` and the like — whose own content
    model is exactly one repeated field, which is what they collapse to
    once embedded and therefore what they are when queried standalone too.

    **Produced by construction, not by a second implementation.** The value
    is built fully populated, then projected through the same
    ``Mapper.encode_wire`` that ``to_wire()`` uses (research R2) — so a
    repeated complex field nests as a list of singly-keyed objects, a
    document-body type carries the wrapper the wire carries, and a later
    change to the wire shape moves this instance with it automatically.
    This **reverses** this class's earlier recorded position (FR-026): an
    instance built from model defaults alone could not be schema-valid for
    64 required-with-no-default scalar fields across 19 types in the show
    schema; G3 closes that gap with a seed derived from each field's
    declared XSD type (contracts/seeding-rules.md) — never from the
    field's name, and never promoted into ``FieldDescriptor.default`` or
    the repairability classification, both of which stay exactly as they
    were (FR-026a).

    **Complete.** Every declared non-wildcard field is present, required
    and optional alike, so nothing is "optional and empty" and the
    projection has nothing to omit (research R3 decision 3) — the one
    deliberate divergence from projecting a real sparse object, in the
    direction of being more useful.

    **A repeated complex field carries one exemplar**, not an empty list —
    unchanged from this class's original reason: a caller cloning element
    ``[0]`` of an example's outputs needs something to clone.

    **Callable defaults are still not invoked** (FR-027) — two reasons, and
    the first is decisive: ``derive`` is cached, so calling ``new_uuid()``
    once would freeze a single "fresh" identifier and hand the same one to
    every caller thereafter. Second, this object is served over a
    websocket to the UI, and a function is not serialisable. The callable
    itself remains visible on ``FieldDescriptor.default`` for a caller that
    wants to invoke it.

    **Every root instance saves through this library's own write path
    unmodified** (FR-023, FR-024, SC-005) — the property the retired
    position above could not offer, and the one four of
    ``cuems-editor``'s seven gate xfails assert directly.
    """


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
    six schemas.

    **A union reports a closed choice set only when every member is an
    enumeration** (S2, FR-066/FR-068, contract C6). A union's own
    ``.enumeration`` is ``None`` — the facet lives on its member types — and
    a union with at least one non-enumerated member (``NodeUuidType``'s
    pattern-restricted ``ConvergedUuidType`` member,
    ``AutoOrIntLatencyMsType``'s numeric ``IntLatencyMsType`` member) is
    **not itself closed**: narrowing to only the enumerated members' values
    would silently drop every other valid value. Five measured sites
    (data-model.md §4) stopped reporting a one-value choice set for exactly
    this reason — two identity fields' sentinel and three latency fields'
    ``auto``.
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
        member_values = getattr(member, "enumeration", None)
        if not member_values:
            return None
        for value in member_values:
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


#: Rule 8 — XSD built-ins in use, table-seeded (contracts/seeding-rules.md).
#: ``0`` would not validate for ``positiveInteger``, which is the one entry
#: that is not simply "the zero of its kind".
_BUILTIN_SEEDS: dict[str, Any] = {
    "boolean": False,
    "string": "",
    "positiveInteger": 1,
    "nonNegativeInteger": 0,
    "integer": 0,
    "float": 0.0,
    "byte": 0,
}

#: Rule 7 — the pattern table (contracts/seeding-rules.md). A regular
#: expression cannot be inverted, and no runtime dependency generates a
#: matching string; this is the irreducible residue, keyed by type and
#: guarded by completeness/validity contract tests.
_PATTERN_SEEDS: dict[str, Any] = {
    "UuidType": "00000000-0000-4000-8000-000000000000",
    "TargetType": "",
    "Md5Type": "0" * 32,
    "TimecodeType": "00:00:00.000",
    "NonEmptyString": "x",
}


def _facet(simple_type, local_name: str):
    facets = getattr(simple_type, "facets", None) or {}
    for key, facet in facets.items():
        if facet is not None and key.rsplit("}", 1)[-1] == local_name:
            return facet
    return None


def _facet_value(simple_type, local_name: str) -> Any:
    """A facet's declared bound (``minInclusive``/``minLength``/…). Not for
    ``pattern``, whose facet carries no single ``.value`` — presence alone
    is what rule 6 needs, checked with :func:`_facet` directly."""
    facet = _facet(simple_type, local_name)
    return facet.value if facet is not None else None


def _scalarize(value: Any) -> Any:
    """A facet's bound value, made lexical/wire-safe. A numeric facet
    (``PercentType``'s ``minInclusive``) already hands back a plain
    ``int``/``float``; a date-typed one (``DateType``) hands back an
    ``elementpath`` ``DateTime``, which is not JSON-serialisable and would
    write as an empty string if passed to the XML writer raw — its lexical
    form is what both paths actually need."""
    if value is None or isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


def _seed_for_facets(simple_type) -> Any:
    """Rules 3–6 over ``simple_type``'s own facets, plus rule 7's table —
    contracts/seeding-rules.md. Never reached for an enumeration or a
    union; the caller (:func:`_seed_for`) handles rules 1, 2 and 8."""
    min_inclusive = _facet_value(simple_type, "minInclusive")
    if min_inclusive is not None:
        return _scalarize(min_inclusive)  # rule 3

    min_exclusive = _facet_value(simple_type, "minExclusive")
    max_inclusive = _facet_value(simple_type, "maxInclusive")
    if min_exclusive is not None and max_inclusive is not None:
        return _scalarize(max_inclusive)  # rule 4
    if max_inclusive is not None:
        return 0  # rule 5

    min_length = _facet_value(simple_type, "minLength")
    pattern = _facet(simple_type, "pattern")
    if pattern is None and min_length is not None:
        return "" if min_length == 0 else "x"  # rule 6

    name = simple_type.name.rsplit("}", 1)[-1] if simple_type.name else None
    return _PATTERN_SEEDS.get(name)  # rule 7


def _seed_for_type_object(simple_type) -> Any:
    """Like :func:`_seed_for`, but given the simple-type xmlschema object
    directly rather than resolving one by name through ``schema.types``.
    Used only by :func:`_inline_named_type_seed` below, where there is no
    locally-declared type to look up by name — the content is anonymous
    *and* built-in (``xs:string``).
    """
    if simple_type is None or not simple_type.is_simple():
        return None
    if simple_type.enumeration:
        return simple_type.enumeration[0]
    member_types = getattr(simple_type, "member_types", None)
    if member_types:
        for member in member_types:
            if getattr(member, "enumeration", None):
                return member.enumeration[0]
        return _seed_for_type_object(member_types[0])
    seeded = _seed_for_facets(simple_type)
    if seeded is not None:
        return seeded
    return _BUILTIN_SEEDS.get(getattr(simple_type, "local_name", None))


def _inline_named_type_seed(key: TypeKey, field_spec) -> dict | list | None:
    """The one measured exception research R1 found and left unresolved:
    an anonymous complex child declared inside a **named** (non-path)
    type — ``PutType.mappings`` is the one site in the six schemas. R1's
    path-based resolution needs the *enclosing* type to be path-reachable
    (``CuemsProject/CuemsScript``); a named type like ``PutType`` is not,
    so there is no ``TypeKey`` to resolve this field's child by at all —
    "left raw, which is what the recorded config goldens carry."

    Walked directly off the XSD element, bypassing ``FieldSpec``/
    ``TypeKey`` entirely — the one place in this module that does, because
    there is no other way to reach it. Returns ``None`` when the shape
    does not match (a simple-content field, or more than one child),
    rather than guessing.
    """
    schema = get_schema(key.schema)
    xsd_type = schema.types.get(key.name)
    content = getattr(xsd_type, "content", None)
    if content is None or not hasattr(content, "iter_elements"):
        return None
    element = next((e for e in content.iter_elements() if e.name == field_spec.name), None)
    if element is None or element.type is None or element.type.is_simple():
        return None
    inner_content = getattr(element.type, "content", None)
    if inner_content is None or not hasattr(inner_content, "iter_elements"):
        return None
    inner_fields = list(inner_content.iter_elements())
    if len(inner_fields) != 1:
        return None
    inner = inner_fields[0]
    seed = _seed_for_type_object(inner.type)
    repeated = inner.occurs[1] is None or inner.occurs[1] > 1
    return [{inner.name: seed}] if repeated else {inner.name: seed}


def _seed_for(schema_name: str, xsd_type_name: str | None) -> Any:
    """A value satisfying ``xsd_type_name``'s declared facets — the closed,
    eight-rule contract in contracts/seeding-rules.md (FR-025, FR-026b,
    FR-028), never derived from the field's name. Resolved **per schema**
    (research R4), matching :func:`_enum_values`.

    Precedence is the caller's: this is consulted only where the bound
    model's own declared default is ``Unset`` or callable (data-model.md §3,
    "The seed, as a derived value").
    """
    if xsd_type_name is None:
        return None
    schema = get_schema(schema_name)
    simple_type = schema.types.get(xsd_type_name)
    if simple_type is None or not simple_type.is_simple():
        return _BUILTIN_SEEDS.get(xsd_type_name)  # rule 8

    if simple_type.enumeration:
        return simple_type.enumeration[0]  # rule 1

    member_types = getattr(simple_type, "member_types", None)
    if member_types:  # rule 2 — a union
        for member in member_types:
            if getattr(member, "enumeration", None):
                return member.enumeration[0]
        return _seed_for_facets(member_types[0])

    return _seed_for_facets(simple_type)


def _model_for(key: TypeKey) -> type | None:
    """The bound Python model class for ``key``, or ``None`` for a
    ``GENERIC`` or unbound type (reuses :func:`_defaults_for`'s own
    resolution, research R5)."""
    registry = get_registry(key.schema)
    binding = (
        registry.binding_for_path(key.name) if key.is_path else registry.binding_for(key.name)
    )
    if binding is None or binding.is_generic or not isinstance(binding.model, type):
        return None
    return binding.model


def _is_wrapper_shape(key: TypeKey) -> bool:
    """Every declared field is repeated — the pure structural-container
    shape (``OutputsType``, ``NodeDictType``, ``AudioChannelsType``, the
    multi-member choice ``CueListContentsType``) that the decoder collapses
    away whenever it is *embedded*: config decode preserves its one or more
    repeated children as a flat, pre-tagged list directly on the embedding
    field, never as a nested dict holding this type's own field (measured
    against real corpus documents — ``node_list``, ``players``, ``outputs``
    all decode this way; research R2's general pattern, not three special
    cases).
    """
    fields = [f for f in derive(key).fields if not f.is_wildcard]
    return bool(fields) and all(f.repeated for f in fields)


def _chosen_child(field_spec) -> tuple[Any, TypeKey | None]:
    """The exemplar to build for a repeated field: the first declared
    alternative if any (``AudioCueOutputsType`` for ``CueOutput``,
    ``VideoPlayerType`` for ``player``, …) — deterministic and reproducible,
    and a better exemplar than the unconditional fallback, which exists for
    an *unmatched* class — else the field's own declared child."""
    if field_spec.alternatives:
        return field_spec.alternatives[0]
    return None, field_spec.child


def _build_value_for(key: TypeKey, seen: frozenset) -> dict:
    """The raw, fully-populated, decoded-shape value for ``key`` — every
    declared non-wildcard field present, required and optional alike
    (research R3 decision 3).

    ``seen`` bounds cycles by branch, as the retired ``_instance_for`` did —
    a type reached twice down two different branches expands both times; a
    revisit on the same branch yields ``{}``.
    """
    if key in seen:
        return {}
    spec = derive(key)
    branch = seen | {key}
    defaults = _defaults_for(key)

    instance: dict = {}
    for field_spec in spec.fields:
        if field_spec.is_wildcard:
            continue
        if field_spec.repeated:
            instance[field_spec.name] = _build_repeated_direct(key.schema, field_spec, branch)
        else:
            instance[field_spec.name] = _build_single(key, field_spec, defaults, branch)
    return instance


def _build_repeated_direct(schema_name: str, field_spec, branch: frozenset) -> list:
    """One exemplar of a repeated field declared **directly** on the type
    being built (no intermediate wrapper collapsing into it) — tagged as it
    would actually decode on its own: the chosen item's own class/element
    name, never the field's own name (measured:
    ``project_settings``' ``setting`` decodes to a bare list of real
    ``SettingType`` instances and so tags as ``SettingType``, where
    ``network_map``'s ``node`` happens to tag as ``node`` only because the
    bound model class is itself named that)."""
    class_value, chosen_key = _chosen_child(field_spec)
    if chosen_key is None:
        # A repeated *scalar* field — measured: one site, hardware_outputs.
        return [_seed_for(schema_name, field_spec.xsd_type)]

    if _is_wrapper_shape(chosen_key):
        # The chosen child is itself a pure container sharing one type
        # between two *differently-named* repeated fields — measured:
        # ``DeviceType.outputs`` and ``.inputs`` both declare their child as
        # ``PutGroupType``, which carries both ``output`` and ``input``.
        # Resolving to ``PutGroupType`` directly would reuse the same ports
        # for both directions; the field this one actually means is
        # ``PutGroupType``'s own inner field matching this field's name.
        inner = _select_wrapper_field(chosen_key, field_spec.name)
        return [_build_repeated_wrapped(schema_name, inner, branch)]

    body = _build_value_for(chosen_key, branch)
    if class_value is not None and "class" in body:
        body["class"] = class_value

    model = _model_for(chosen_key)
    if model is not None:
        # The tag ``encode_wire`` would derive for this item is its own
        # bound class's name, resolved by ``Mapper._tag_for_item`` from the
        # item's **runtime type** — measured: ``project_settings``' real
        # decoded ``setting`` items are bare ``SettingType`` instances, and
        # ``settings``' real decoded ``player`` items are bare
        # ``VideoPlayerType`` instances, neither pre-wrapped. A plain dict
        # here would resolve to the class name ``"dict"`` instead, so the
        # item must be the real model, unwrapped, for that resolution to
        # run at all.
        return [model(body)]
    return [{field_spec.name: body}]


def _select_wrapper_field(wrapper_key: TypeKey, outer_name: str):
    """Which of a wrapper-shaped type's (possibly several) inner fields a
    repeated outer field sharing that type actually means — by name match,
    tolerating the plural/singular spelling (``outputs``/``output``), the
    one measured divergence. Falls back to the first field when there is
    exactly one, or no match is found."""
    wrapper_fields = [f for f in derive(wrapper_key).fields if not f.is_wildcard]
    for f in wrapper_fields:
        if f.name in (outer_name, outer_name.rstrip("s")):
            return f
    return wrapper_fields[0]


def _build_repeated_wrapped(schema_name: str, field_spec, branch: frozenset) -> list:
    """One exemplar of a field declared on a **wrapper container type**
    that is being collapsed into (:func:`_is_wrapper_shape`) — pre-tagged
    with the field's **own** declared name (``CueOutput``/``node``/
    ``player``/``channel``/…), which is what config decode already
    preserves and what ``encode_wire``'s repeated-field handling recognises
    as an already-tagged member (research R2)."""
    class_value, chosen_key = _chosen_child(field_spec)
    if chosen_key is None:
        return [_seed_for(schema_name, field_spec.xsd_type)]

    body = _build_value_for(chosen_key, branch)
    if class_value is not None and "class" in body:
        body["class"] = class_value
    return [{field_spec.name: body}]


def _build_wrapper_collapse(wrapper_key: TypeKey, branch: frozenset) -> list:
    """The collapsed value for a wrapper-shaped type being embedded — one
    exemplar of its **first** declared field.

    A single-field container (``OutputsType``) has only one choice. A
    multi-member choice (``CueListContentsType``:
    ``Cue``/``ActionCue``/``FadeCue``/``CueList``) could in principle offer
    one exemplar per member, but ``ActionCue``/``FadeCue``'s
    ``action_target`` is a cross-reference T2 validates against the
    *document*'s own cues (feature 010's ``action_target_resolves``) — no
    seed can satisfy that generically, and populating them anyway would
    break FR-023's "every root instance saves unmodified" for the one
    schema that has this shape. The first member is deterministic,
    reproducible, and keeps every root saveable; see
    ``test_the_instance_carries_every_declared_field``'s own exemption for
    a type whose content model is a true choice rather than a sequence.
    """
    fields = [f for f in derive(wrapper_key).fields if not f.is_wildcard]
    return _build_repeated_wrapped(wrapper_key.schema, fields[0], branch)


def _build_single(key: TypeKey, field_spec, defaults: dict, branch: frozenset) -> Any:
    """One non-repeated field's value: a nested instance for a complex
    child (R1's anonymous-child case included), collapsing through a
    wrapper-shaped child (research R2), or a seeded scalar — model default
    first, then :func:`_seed_for` (data-model.md §3)."""
    if field_spec.name == "&":
        # The converter's own text key for a simple-content type
        # (``spec.py``'s ``_simple_content_text``) — ``DefaultPortType``'s
        # own text, not an element, so it carries neither a qname nor a
        # complex child to resolve by. Its real type is the
        # ``xs:simpleContent`` base, read directly off the XSD.
        schema = get_schema(key.schema)
        xsd_type = schema.types.get(key.name)
        base = getattr(xsd_type, "content", None)
        seed = _seed_for_type_object(base) if base is not None else None
        return seed if seed is not None else ""

    if field_spec.xsd_type == "CTimecodeType":
        # The one value object that is neither scalar nor mapping
        # (mapper.py's own note beside ``_fill``): ``encode_wire`` checks
        # ``adapter_for(field.xsd_type)`` **before** looking at
        # ``field.child`` at all, and the adapter expects a real
        # ``CTimecode``, not the nested ``{"CTimecode": …}`` dict recursing
        # into the complex child would build — which the adapter would
        # then stringify wholesale instead of converting.
        from ..tools.CTimecode import CTimecode

        return CTimecode("00:00:00.000")

    child_key = field_spec.child
    if child_key is None and field_spec.xsd_type is None and key.is_path:
        # R1: an anonymous single complex child (``CuemsSettings/Settings``,
        # ``CuemsProject/CuemsScript``) has no qname to key it by, so
        # ``field_spec.child`` is ``None``. Resolved by **path**, reusing the
        # guard conditions of ``Mapper._anonymous_child``/``_child_spec_for``
        # verbatim, rather than widening ``FieldSpec.child``'s own notion of
        # a leaf (27 consumers depend on it meaning "scalar").
        candidate = TypeKey(key.schema, f"{key.name}/{field_spec.name}", is_path=True)
        try:
            derive(candidate)
            child_key = candidate
        except (KeyError, StopIteration, AttributeError):
            child_key = None

    if child_key is not None:
        if _is_wrapper_shape(child_key):
            return _build_wrapper_collapse(child_key, branch)
        return _build_value_for(child_key, branch)

    default = defaults.get(field_spec.name, Unset)
    if default is Unset or callable(default):
        # Unset has no value to seed with; a callable must not be invoked
        # here (FR-027) — see TypeDescriptor.instance.
        if field_spec.xsd_type is None:
            # Not a scalar at all — the one measured exception (R1,
            # ``PutType.mappings``): an anonymous complex child inside a
            # *named* (non-path) type, which neither a qname nor R1's path
            # form can reach.
            inline = _inline_named_type_seed(key, field_spec)
            if inline is not None:
                return inline
        return _seed_for(key.schema, field_spec.xsd_type)
    return default


_wrap_index_cache: dict[str, dict[TypeKey, str]] = {}


def _wrap_index(schema_name: str) -> dict[TypeKey, tuple[str, Any]]:
    """``TypeKey -> (the field name that wraps it, its class value or
    None)``, for every type reachable only by **collapsing into a
    wrapper-shaped container** (research R2's general pattern — FR-021's
    ``CueOutput`` wrapper is one instance of it, not a special case). Such
    a type has no wire representation of its own; queried standalone, its
    instance is what it would be as one member of that field — class
    value included, so ``VideoPlayerType`` queried standalone still seeds
    ``class="video"`` rather than a generic string.

    Scoped to **non-repeated** fields whose own child collapses
    (:func:`_is_wrapper_shape`), mirroring :func:`_build_single` exactly —
    a repeated field declared *directly* on a type (``setting`` on the
    ``project_settings`` root) never collapses, and indexing it here would
    wrongly wrap that field's own item type too (measured:
    ``SettingType`` queried standalone is bare, never ``{"setting": …}``).
    """
    if schema_name not in _wrap_index_cache:
        index: dict[TypeKey, tuple[str, Any]] = {}
        registry = get_registry(schema_name)
        keys = [TypeKey(schema_name, n) for n in registry.bound_type_names]
        keys += [TypeKey(schema_name, n, is_path=True) for n in registry.bound_path_names]
        for key in keys:
            for field_spec in derive(key).fields:
                if field_spec.repeated or field_spec.child is None:
                    continue
                if not _is_wrapper_shape(field_spec.child):
                    continue
                wrapper_fields = [f for f in derive(field_spec.child).fields if not f.is_wildcard]
                inner = wrapper_fields[0]
                if inner.child is not None:
                    index.setdefault(inner.child, (inner.name, None))
                for class_value, alt_key in inner.alternatives:
                    index.setdefault(alt_key, (inner.name, class_value))
        _wrap_index_cache[schema_name] = index
    return _wrap_index_cache[schema_name]


def _instance_for(key: TypeKey) -> dict | list:
    """The descriptor's wire-shaped, saveable instance for ``key`` (G3,
    contracts/public-surface.md C3, FR-020..FR-027).

    Builds the raw, fully-populated value above, then projects it through
    the **same** encoder ``to_wire()`` uses (``Mapper.encode_wire``) — so
    the wrapping and the nesting are structural, not a second
    implementation the descriptor owns and could drift from (research R2).
    """
    from .mapper import Mapper

    if _model_for(key) is None and _is_wrapper_shape(key):
        # An **unbound** wrapper container (``OutputsType``,
        # ``AudioChannelsType``, ``CueListContentsType``, …) has no
        # standalone existence of its own — nothing in this library ever
        # constructs one — so queried directly it is what it would look
        # like embedded: the bare, pre-tagged list (measured: a *bound*
        # wrapper like ``NodeDictType`` has a real standalone
        # ``.to_wire()``, which stays on the normal path below and is
        # measurably different — a dict, not a list).
        # One exemplar **per declared field** — a multi-member choice
        # (``CueListContentsType``: ``Cue``/``ActionCue``/``FadeCue``/
        # ``CueList``) has more than one, and every one of them must
        # appear for FR-020's "every declared field present" to hold; a
        # single-field container (``OutputsType``) is the one-item case of
        # the same rule, not a different one.
        fields = [f for f in derive(key).fields if not f.is_wildcard]
        items = []
        for chosen_field in fields:
            class_value, chosen_key = _chosen_child(chosen_field)
            if chosen_key is None:
                items.append({chosen_field.name: _seed_for(key.schema, chosen_field.xsd_type)})
                continue
            body = _build_value_for(chosen_key, frozenset({key}))
            if class_value is not None and "class" in body:
                body["class"] = class_value
            projected_body = Mapper(key.schema).encode_wire(body, derive(chosen_key))
            items.append({chosen_field.name: projected_body})
        return items

    spec = derive(key)
    raw = _build_value_for(key, frozenset())

    wrap = _wrap_index(key.schema).get(key)
    if wrap is not None:
        wrapper_name, class_value = wrap
        if class_value is not None and "class" in raw:
            raw["class"] = class_value
    instance = Mapper(key.schema).encode_wire(raw, spec)

    if wrap is not None:
        instance = {wrapper_name: instance}
    return instance


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
        return TypeDescriptor(key=key, fields=fields, instance=_instance_for(key))


def clear_cache() -> None:
    global _repairability_cache
    _repairability_cache = None
    _wrap_index_cache.clear()


# --- example-document generation (T070, T078) -------------------------------
#
# Replaces the retired hand-written script-template function and the retired
# hand-maintained settings template file (data-model.md §3.2). Neither
# generator validates and then mutates its result on the way out — there is
# no ordering defect here to reproduce, because there is no blanking step to
# get wrong (FR-033).
#
# Structural completeness — *which* concrete cue types a script example
# carries — is descriptor-driven: read off the registry's
# ``CueListContentsType`` binding (the schema's own choice of concrete cue
# types) rather than a hand-maintained list, so a new cue type added to the
# schema is caught by ``_assert_every_choice_member_has_a_builder`` instead of
# silently missing from the example. What each cue type's *content* looks
# like is not schema-derivable — a media file, an output's geometry, a DMX
# channel are exactly what the schema cannot supply on its own — so those are
# small, explicit, hand-authored builders, one per concrete type.


def _script_cue_builders():
    """One builder per concrete cue type, keyed by the element name
    ``CueListContentsType``'s choice offers it under (research R3's choice
    reuse — see ``_repairability_map`` for the same join pattern)."""
    from ..cues.ActionCue import ActionCue
    from ..cues.AudioCue import AudioCue
    from ..cues.CueOutput import AudioCueOutput, DmxCueOutput, VideoCueOutput
    from ..cues.DmxCue import DmxChannel, DmxCue, DmxScene, DmxUniverse
    from ..cues.FadeCue import FadeCue, FadeCurveType
    from ..cues.MediaCue import Media, Region
    from ..cues.VideoCue import VideoCue
    from ..helpers import new_uuid

    target_uuid = str(new_uuid())

    def _media(file_name: str) -> Media:
        return Media({
            "file_name": file_name,
            "id": new_uuid(),
            "duration": "00:00:01.000",
            "regions": [Region({"id": 0, "loop": 1, "in_time": None, "out_time": None})],
        })

    def build_audio_cue():
        cue = AudioCue({"Media": _media("audio_example.wav"), "ui_properties": {"warning": None}})
        cue.outputs = [AudioCueOutput({
            "output_name": f"{target_uuid}_0",
            "output_vol": 100,
            "channels": [{"channel": {"channel_num": 0, "channel_vol": 100}}],
        })]
        return cue

    def build_video_cue():
        cue = VideoCue({"Media": _media("video_example.mp4"), "ui_properties": {"warning": None}})
        geometry = {
            "x_scale": 1, "y_scale": 1,
            "corners": {
                "top_left": {"x": 0, "y": 0},
                "top_right": {"x": 0, "y": 0},
                "bottom_left": {"x": 0, "y": 0},
                "bottom_right": {"x": 0, "y": 0},
            },
        }
        # Two outputs, not one: an alias (no canvas_region) and a custom
        # slot (canvas_region required) — both output_name shapes
        # output_name_shape/canvas_region_containment exist to distinguish,
        # and tests/support/invalid_scripts.py's custom_video_output() reads
        # the custom one back out to build a canvas-region T2 violation.
        cue.outputs = [
            VideoCueOutput({
                "output_name": f"{target_uuid}_0",
                "output_geometry": geometry,
            }),
            VideoCueOutput({
                "output_name": f"{target_uuid}_custom_0",
                "output_geometry": geometry,
                "canvas_region": {"x": 0.1, "y": 0.1, "width": 0.5, "height": 0.5},
            }),
        ]
        return cue

    def build_dmx_cue():
        cue = DmxCue({
            "fadein_time": 0.0,
            "fadeout_time": 0.0,
            "DmxScene": DmxScene({
                "id": 0,
                "DmxUniverse": DmxUniverse({
                    "universe_num": 0,
                    "dmx_channels": [DmxChannel({"channel": 0, "value": 0})],
                }),
            }),
            "ui_properties": {"warning": None},
        })
        cue.outputs = [DmxCueOutput({"output_name": target_uuid})]
        return cue

    def build_action_cue():
        return ActionCue({
            "action_target": target_uuid,
            "action_type": "play",
            "ui_properties": {"warning": 0},
        })

    def build_fade_cue():
        return FadeCue({
            "action_target": target_uuid,
            "curve_type": FadeCurveType.linear,
            "duration": "00:00:02.000",
            "target_value": 0,
            "ui_properties": {"warning": None},
        })

    # Keyed by **element name**, which since feature 013 is no longer the same
    # thing as "one key per cue class": ``Cue`` is one element whose class
    # selects the type, so its entry is a per-class table rather than a single
    # thunk. ``ActionCue`` and ``FadeCue`` keep their own elements and their
    # own single thunks (FR-050a).
    return {
        "Cue": {
            "audio": build_audio_cue,
            "video": build_video_cue,
            "dmx": build_dmx_cue,
        },
        "ActionCue": build_action_cue,
        "FadeCue": build_fade_cue,
    }


def _assert_every_choice_member_has_a_builder(builders: dict) -> tuple[str, ...]:
    """The concrete cue element names ``CueListContentsType`` offers, minus
    the recursive ``CueList`` container — and a loud failure if the schema
    ever names one this module has no builder for, rather than a silently
    incomplete example (mirrors
    ``test_generated_example_covers_every_cue_subclass``'s intent, now
    enforced at generation time too).

    Since feature 013 the check has a second half, and it is the half that
    keeps the loudness: a conditional member needs one builder **per class the
    schema names an alternative for**. Without it, adding a fourth
    ``xs:alternative`` to ``Cue`` would leave the example silently one cue
    short — the element name ``Cue`` would still have *an* entry, which is
    exactly the "silently incomplete example" this function exists to prevent.
    A class with no alternative needs no builder: it has no special fields, so
    it adds nothing an example could show.
    """
    choice = derive(TypeKey("script", "CueListContentsType"))
    leaf_names = tuple(f.name for f in choice.fields if f.name != "CueList")
    missing = [name for name in leaf_names if name not in builders]
    if missing:
        raise RuntimeError(
            f"CueListContentsType offers {missing} with no example builder in "
            f"descriptor._script_cue_builders — add one"
        )
    # ``member``, not ``field``: this module imports ``dataclasses.field`` at
    # the top, and a loop variable of that name shadows it.
    for member in choice.fields:
        if member.name == "CueList" or not member.alternatives:
            continue
        by_class = builders[member.name]
        absent = [value for value, _key in member.alternatives if value not in by_class]
        if absent:
            raise RuntimeError(
                f"{member.name} names an xs:alternative for {absent} with no "
                f"example builder in descriptor._script_cue_builders — add one"
            )
    return leaf_names


def _build_choice_members(builders: dict, leaf_names: tuple[str, ...]) -> list:
    """One object per element name, and per class where the element is
    conditional — in schema order, then alternative order."""
    choice = derive(TypeKey("script", "CueListContentsType"))
    cues = []
    for name in leaf_names:
        builder = builders[name]
        if isinstance(builder, dict):
            member = choice.field(name)
            cues.extend(builder[value]() for value, _key in member.alternatives)
            continue
        cues.append(builder())
    return cues


def generate_script_example():
    """A ``CuemsScript`` carrying one of every concrete cue type (T070).

    Replaces the retired hand-written script-template function. Output is
    not byte-identical to what that function produced — a fresh uuid4 per
    identifier, no id-blanking step — which FR-033 permits.
    """
    from ..cues.CueList import CueList
    from ..cues.CuemsScript import CuemsScript
    from ..helpers import new_uuid

    builders = _script_cue_builders()
    leaf_names = _assert_every_choice_member_has_a_builder(builders)
    cues = _build_choice_members(builders, leaf_names)

    # Point every action reference at a cue that is actually here (T015a).
    #
    # ``build_action_cue`` and ``build_fade_cue`` cannot do this themselves:
    # they run *before* the list exists, so the only id available to them was a
    # placeholder shared with a DMX output name. That placeholder resolved to
    # nothing, which made this example — the document D25 has consumers clone
    # in place of a hand-maintained template — one the library's own strict load
    # path rejects, and would have handed every new project an unloadable
    # reference.
    #
    # Undetectable until ``action_target_resolves`` existed, because nothing
    # checked that a *non-null* action target named a real cue.
    referent = next(
        (cue["id"] for cue in cues if "action_target" not in cue), cues[0]["id"]
    )
    for cue in cues:
        if "action_target" in cue:
            cue["action_target"] = referent

    script = CuemsScript({
        "name": "Example Script",
        "description": "Descriptor-generated example (feature 008, ITEM D)",
        "CueList": CueList({"contents": cues}),
    })
    script["id"] = new_uuid()
    script["CueList"]["id"] = new_uuid()
    script.ui_properties = {"warning": 0}
    return script


#: The seed values moved out of this module (feature 011, D7/D9): they are
#: data now — ``cuemsutils/defaults/system-defaults.toml``, loaded and checked by
#: ``xml/seed_values.py``, the one code path the build-time generator and
#: ``cuems-init-node`` share. Everything the old table's docstring said about
#: *why* the values are what they are (D15's correction by consumption, D16's
#: removed base-class fallback) travelled with the values as comments in that
#: file. What stays here is the structural guarantee: ``generate_settings_example``
#: still raises when a required field has no entry, whichever file the entries
#: came from.
from .seed_values import settings_value as _settings_example_value  # noqa: E402


def _build_settings_section(class_name: str, model, field_names: tuple[str, ...], tables=None):
    return model({name: _settings_example_value(class_name, name, tables) for name in field_names})


def generate_settings_example(tables=None):
    """A ``CuemsSettingsType`` reference instance (T078), replacing the
    retired hand-maintained settings template file.

    Field *names* come from the descriptor — every required field of
    ``SettingsType``/``NodeConfType`` and the four player sections — so a
    schema change that adds or removes a field is caught here rather than in
    a second file nothing enforces agreement with. Field *values* are the
    illustrative table above.
    """
    from ..config.settings import (
        AudioMixerType,
        AudioPlayerType,
        CuemsSettingsType,
        DmxPlayerType,
        NodeConfType,
        SettingsType,
        VideoPlayerType,
    )

    def scalar_fields(key: TypeKey, required_only: bool = True) -> tuple[str, ...]:
        """**Scalar** fields — complex children (``node``, the four player
        sections) are built and attached separately below.

        ``required_only=False`` widens to optional fields as well, which is
        D17: ``osc_port`` and the three ``output_latency_ms`` entries are
        declared ``minOccurs="0"``, so a required-only generator emitted none of
        them and their table entries were unreachable by construction. The two
        audited machines split on exactly this — one omits them, one writes them
        out — and an operator opening ``settings.xml`` should see every knob
        that exists rather than having to read engine source to learn that one
        does.

        Applied to the player sections only, because they are the only types
        with optional scalars: ``SettingsType``'s eleven fields and
        ``NodeConfType``'s thirteen are all required, and ``NodeConfType``'s
        only optional children are the player sections themselves, attached
        below by name.
        """
        spec = derive(key)
        return tuple(
            f.name for f in spec.fields
            if (f.required or not required_only)
            and f.kind is FieldKind.ELEMENT
            and f.child is None
        )

    def player_fields(type_name: str) -> tuple[str, ...]:
        return scalar_fields(TypeKey("settings", type_name), required_only=False)

    node = _build_settings_section(
        "NodeConfType", NodeConfType, scalar_fields(TypeKey("settings", "NodeConfType")), tables
    )
    def _player(type_name: str, model, device_class: str):
        built = _build_settings_section(type_name, model, player_fields(type_name), tables)
        built["class"] = device_class
        return {"player": built}

    # Three assignments, not a collection of class names (FR-010).
    node["players"] = [
        _player("VideoPlayerType", VideoPlayerType, "video"),
        _player("AudioPlayerType", AudioPlayerType, "audio"),
        _player("DmxPlayerType", DmxPlayerType, "dmx"),
    ]
    # ``AudioMixerType``, not ``PlayerType`` (D16-A). This section derived from
    # the abstract base under both the lookup name and the TypeKey, and worked
    # only because that extension is currently empty: adding a required field to
    # AudioMixerType produced no RuntimeError here — the documented
    # generation-time guarantee was simply silent — and failed later as a
    # SchemaError naming neither the values table nor the fix. One of the four
    # sections had a hole in FR-034's net; this closes it.
    node["audiomixer"] = _build_settings_section(
        "AudioMixerType", AudioMixerType, player_fields("AudioMixerType"), tables
    )

    settings_key = TypeKey("settings", "CuemsSettings/Settings", is_path=True)
    settings = _build_settings_section("SettingsType", SettingsType, scalar_fields(settings_key), tables)
    settings["node"] = node
    return CuemsSettingsType({"Settings": settings})
