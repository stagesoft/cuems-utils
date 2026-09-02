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

    return {
        "AudioCue": build_audio_cue,
        "VideoCue": build_video_cue,
        "DmxCue": build_dmx_cue,
        "ActionCue": build_action_cue,
        "FadeCue": build_fade_cue,
    }


def _assert_every_choice_member_has_a_builder(builders: dict) -> tuple[str, ...]:
    """The concrete cue element names ``CueListContentsType`` offers, minus
    the recursive ``CueList`` container — and a loud failure if the schema
    ever names one this module has no builder for, rather than a silently
    incomplete example (mirrors
    ``test_generated_example_covers_every_cue_subclass``'s intent, now
    enforced at generation time too)."""
    choice = derive(TypeKey("script", "CueListContentsType"))
    leaf_names = tuple(f.name for f in choice.fields if f.name != "CueList")
    missing = [name for name in leaf_names if name not in builders]
    if missing:
        raise RuntimeError(
            f"CueListContentsType offers {missing} with no example builder in "
            f"descriptor._script_cue_builders — add one"
        )
    return leaf_names


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
    cues = [builders[name]() for name in leaf_names]

    script = CuemsScript({
        "name": "Example Script",
        "description": "Descriptor-generated example (feature 008, ITEM D)",
        "CueList": CueList({"contents": cues}),
    })
    script["id"] = new_uuid()
    script["CueList"]["id"] = new_uuid()
    script.ui_properties = {"warning": 0}
    return script


#: (bound class name, field name) -> an illustrative value, transcribed from
#: the retired hand-maintained settings template (T078). Every ``settings``/
#: ``NodeConfType``/player-section field is ``Unset`` at the model layer
#: (config/settings.py's own docstring: "every field defaults to Unset"), so
#: — unlike the show schema — there is no descriptor-derived default to fall
#: back on anywhere in this tree; a value has to come from somewhere, and
#: this table is that somewhere. What *is* descriptor-driven is completeness:
#: ``generate_settings_example`` raises if a field this table does not name
#: is required, rather than silently emitting an incomplete document — this
#: is what "remove the hand-maintenance clause" (FR-034) actually rests on,
#: since a schema change now breaks the build here instead of drifting out of
#: sync with a second, hand-edited file.
_SETTINGS_EXAMPLE_VALUES = {
    ("SettingsType", "conf_path"): "/etc/cuems",
    ("SettingsType", "library_path"): "/opt/cuems_library",
    ("SettingsType", "tmp_path"): "/tmp/cuems",
    ("SettingsType", "database_name"): "project-manager.db",
    ("SettingsType", "show_lock_file"): "show.lock",
    ("SettingsType", "editor_url"): "editor.local",
    ("SettingsType", "controller_url"): "controller.local",
    ("SettingsType", "templates_path"): "/usr/share/cuems",
    ("SettingsType", "controller_interfaces_template"): "interfaces.controller",
    ("SettingsType", "node_interfaces_template"): "interfaces.node",
    ("SettingsType", "controller_lock_file"): "controller.lock",
    ("NodeConfType", "uuid"): "00000000-0000-0000-0000-000000000000",
    ("NodeConfType", "mac"): "000000000000",
    ("NodeConfType", "osc_dest_host"): "localhost",
    ("NodeConfType", "oscquery_ws_port"): 9190,
    ("NodeConfType", "oscquery_osc_port"): 9191,
    ("NodeConfType", "websocket_port"): 9092,
    ("NodeConfType", "load_timeout"): 15000,
    ("NodeConfType", "nodeconf_timeout"): 5000,
    ("NodeConfType", "discovery_timeout"): 15000,
    ("NodeConfType", "mtc_port"): "Midi Through Port-0",
    ("NodeConfType", "osc_in_port_base"): 7000,
    ("NodeConfType", "nng_hub_port"): 9093,
    ("NodeConfType", "gradient_osc_port"): 7100,
    ("PlayerType", "path"): "/usr/bin/cuems-player",
    ("PlayerType", "args"): "",
    ("VideoPlayerType", "outputs"): 2,
    ("VideoPlayerType", "output_latency_ms"): "auto",
    ("AudioPlayerType", "audio_cards"): 1,
    ("AudioPlayerType", "output_latency_ms"): "auto",
    ("DmxPlayerType", "universes"): 1,
    ("DmxPlayerType", "output_latency_ms"): 35,
}


def _settings_example_value(class_name: str, field_name: str):
    """``derive()`` flattens ``xs:extension``, so a player subtype's field
    list already includes ``PlayerType``'s ``path``/``args`` (same
    flattening ``CueType`` gets from ``CommonPropertiesType``) — fall back to
    the base entry rather than duplicating it under every subtype."""
    for key in ((class_name, field_name), ("PlayerType", field_name)):
        if key in _SETTINGS_EXAMPLE_VALUES:
            return _SETTINGS_EXAMPLE_VALUES[key]
    raise RuntimeError(
        f"settings.xsd's {class_name}.{field_name} has no example value in "
        f"descriptor._SETTINGS_EXAMPLE_VALUES — add one"
    )


def _build_settings_section(class_name: str, model, field_names: tuple[str, ...]):
    return model({name: _settings_example_value(class_name, name) for name in field_names})


def generate_settings_example():
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

    def required_fields(key: TypeKey) -> tuple[str, ...]:
        """Required, **scalar** fields — complex children (``node``, the four
        player sections) are built and attached separately below."""
        spec = derive(key)
        return tuple(
            f.name for f in spec.fields
            if f.required and f.kind is FieldKind.ELEMENT and f.child is None
        )

    node = _build_settings_section(
        "NodeConfType", NodeConfType, required_fields(TypeKey("settings", "NodeConfType"))
    )
    node["videoplayer"] = _build_settings_section(
        "VideoPlayerType", VideoPlayerType, required_fields(TypeKey("settings", "VideoPlayerType"))
    )
    node["audioplayer"] = _build_settings_section(
        "AudioPlayerType", AudioPlayerType, required_fields(TypeKey("settings", "AudioPlayerType"))
    )
    node["audiomixer"] = _build_settings_section(
        "PlayerType", AudioMixerType, required_fields(TypeKey("settings", "PlayerType"))
    )
    node["dmxplayer"] = _build_settings_section(
        "DmxPlayerType", DmxPlayerType, required_fields(TypeKey("settings", "DmxPlayerType"))
    )

    settings_key = TypeKey("settings", "CuemsSettings/Settings", is_path=True)
    settings = _build_settings_section("SettingsType", SettingsType, required_fields(settings_key))
    settings["node"] = node
    return CuemsSettingsType({"Settings": settings})
