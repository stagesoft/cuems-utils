"""Explicit XSD type → Python class bindings, one registry per schema (T042).

Replaces three implicit ``globals()`` name-manglings — the parser lookup, the
tag→class lookup and the builder lookup — each of which **misses silently**. The
measured consequences are in `generic-bindings.md`: ``mediaParser`` exists at
``Parsers.py:258`` and is never reached, because the lookup builds
``'Media' + 'Parser'`` = ``MediaParser`` while the class is spelled
``mediaParser``. Thirteen hits across the corpus, no error, no log line.

Two rules make that unrepeatable:

1. **Every complex type must be bound.** An unbound type raises at registry
   build time, naming it (FR-007, contract C7). That is the half ``globals()``
   could never do.
2. **Types that reach a generic today are bound explicitly to that same
   generic.** Completeness means *accounted for*, not *given a bespoke class* —
   promoting one to a real handler would change the output, which this feature
   forbids. `generic-bindings.md` is the measured list.

One registry per schema, mandatorily (research R4): ``script.xsd`` and
``outputs.xsd`` both declare ``{https://stagelab.coop/cuems/}OutputsType`` with
different content, so a shared registry would hand one schema the other's
binding. There is no public registration API (D11 + Q14) — nothing external
owns a model.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from .schema import SCHEMA_NAMES, SCHEMA_ROOTS, get_schema
from .spec import TypeKey

#: Marker for a type that is deliberately served by a generic container rather
#: than by a model class. Explicit so that "no bespoke class" is a *decision*
#: recorded in the table, not the absence of an entry.
GENERIC = "GENERIC"


@dataclass(frozen=True)
class Binding:
    """What a complex type maps to."""

    key: TypeKey
    model: type | str

    @property
    def is_generic(self) -> bool:
        return self.model is GENERIC or self.model == GENERIC


class SchemaRegistry:
    """Bindings for one schema."""

    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        self.root = SCHEMA_ROOTS[schema_name]
        self._by_type: dict[str, Binding] = {}
        self._by_path: dict[str, Binding] = {}

    def bind(self, type_name: str, model) -> SchemaRegistry:
        key = TypeKey(self.schema_name, type_name)
        self._by_type[type_name] = Binding(key, model)
        return self

    def bind_path(self, element_path: str, model) -> SchemaRegistry:
        """Bind an **anonymous** type by element path (research R3).

        ``CuemsProject`` and ``CuemsScript`` have no type qname to bind by —
        there is no ``CuemsScriptType`` in the schema, so the target design's
        illustrative ``SCRIPT.bind('CuemsScriptType', …)`` cannot work.
        """
        key = TypeKey(self.schema_name, element_path, is_path=True)
        self._by_path[element_path] = Binding(key, model)
        return self

    def binding_for(self, type_name: str) -> Binding | None:
        return self._by_type.get(type_name)

    def binding_for_path(self, element_path: str) -> Binding | None:
        return self._by_path.get(element_path)

    def model_for(self, type_name: str):
        binding = self.binding_for(type_name)
        return None if binding is None or binding.is_generic else binding.model

    @property
    def bound_type_names(self) -> frozenset[str]:
        return frozenset(self._by_type)

    def complex_type_names(self) -> frozenset[str]:
        schema = get_schema(self.schema_name)
        return frozenset(
            name for name, xsd_type in schema.types.items() if not xsd_type.is_simple()
        )

    def unbound_type_names(self) -> frozenset[str]:
        return self.complex_type_names() - self.bound_type_names

    def validate(self) -> None:
        """Raise if any complex type in the schema is unbound (FR-007, C7).

        Named types only. Anonymous types are bound by path and are reached
        through their parent, so they have no qname to be missing from here.
        """
        missing = sorted(self.unbound_type_names())
        if missing:
            raise RegistryIncompleteError(self.schema_name, missing)


class RegistryIncompleteError(RuntimeError):
    """A complex type has no binding.

    Raised at build time and naming the type, which is the entire point: the
    ``globals()`` lookups this replaces failed by *returning a generic*, so a
    missing handler looked exactly like a deliberate one.
    """

    def __init__(self, schema_name: str, missing: list[str]):
        self.schema_name = schema_name
        self.missing = missing
        super().__init__(
            f"{schema_name}.xsd has {len(missing)} unbound complex type(s): "
            f"{', '.join(missing)}. Every complex type must be bound — to a model "
            f"class, or explicitly to GENERIC if it is served by a generic "
            f"container today (FR-007; see specs/004-xml-serialization-core/"
            f"generic-bindings.md)."
        )


def _build_script_registry() -> SchemaRegistry:
    from ..cues.ActionCue import ActionCue
    from ..cues.AudioCue import AudioCue
    from ..cues.Cue import Cue, UI_properties
    from ..cues.CueList import CueList
    from ..cues.CuemsScript import CuemsScript
    from ..cues.CueOutput import AudioCueOutput, DmxCueOutput, VideoCueOutput
    from ..cues.DmxCue import DmxChannel, DmxCue, DmxScene, DmxUniverse
    from ..cues.FadeCue import FadeCue
    from ..cues.FadeProfile import FadeFunctionParameter, FadeProfile
    from ..cues.MediaCue import Media, MediaCue, Region
    from ..cues.VideoCue import VideoCue

    registry = SchemaRegistry("script")

    # Anonymous root types, bound by element path (R3).
    registry.bind_path("CuemsProject", GENERIC)
    registry.bind_path("CuemsProject/CuemsScript", CuemsScript)

    # Cue types.
    registry.bind("CueType", Cue)
    registry.bind("CueListType", CueList)
    registry.bind("AudioCueType", AudioCue)
    registry.bind("VideoCueType", VideoCue)
    registry.bind("DmxCueType", DmxCue)
    registry.bind("ActionCueType", ActionCue)
    registry.bind("FadeCueType", FadeCue)
    registry.bind("MediaCueType", MediaCue)

    # Media and regions.
    registry.bind("MediaType", Media)
    registry.bind("RegionType", Region)

    # Outputs. ``OutputsType`` here is *script.xsd's* — a different type from
    # the identically-named one in outputs.xsd, which is why registries are per
    # schema (R4).
    registry.bind("AudioCueOutputsType", AudioCueOutput)
    registry.bind("VideoCueOutputsType", VideoCueOutput)
    registry.bind("DmxCueOutputsType", DmxCueOutput)

    # DMX.
    registry.bind("DmxSceneType", DmxScene)
    registry.bind("DmxUniverseType", DmxUniverse)
    registry.bind("DmxChannelType", DmxChannel)

    # Fades.
    registry.bind("FadeProfileType", FadeProfile)
    registry.bind("FadeParameterType", FadeFunctionParameter)

    # Wildcard content (R6). ``UI_properties`` exists as a class and is *never*
    # reached today: the tag→class lookup searches for ``ui_properties`` while
    # the class is spelled ``UI_properties``, so all 20 hits fall through to
    # ``GenericDict``. Bound to GENERIC to preserve that; the discrepancy is
    # recorded for feature 005 rather than fixed here.
    registry.bind("UiPropertiesType", GENERIC)
    assert UI_properties is not None  # documents the class this does NOT bind

    # Explicit generics — measured, not assumed. Each of these reaches a
    # generic container today (see generic-bindings.md); binding it to a
    # bespoke class would change the output.
    for type_name in (
        "CommonPropertiesType",  # abstract base, never instantiated directly
        "CueListContentsType",  # the repeated-choice wrapper
        "CTimecodeType",  # handled by an adapter, not a model class (R5)
        "RegionsType",
        "OutputsType",
        "AudioChannelType",
        "AudioChannelsType",
        "CanvasRegionType",
        "Coordinates",
        "DmxUniverseContentsType",
        "FadeParametersType",
        "FadeProfilesWrapperType",
        "VideoCornersType",
        "VideoOutputGeometryType",
    ):
        registry.bind(type_name, GENERIC)

    return registry


def _build_config_registry(schema_name: str) -> SchemaRegistry:
    """Bindings for the five configuration schemas.

    **Every type is GENERIC**, and that is not laziness: configuration
    documents have no model classes at all today — ``Settings`` and its
    subclasses hand back raw dicts. Giving them classes is feature 006's job
    (data-model §6). Binding them explicitly is what lets C7 assert totality
    across all six schemas now rather than after that work lands.
    """
    registry = SchemaRegistry(schema_name)
    registry.bind_path(SCHEMA_ROOTS[schema_name], GENERIC)
    for type_name in registry.complex_type_names():
        registry.bind(type_name, GENERIC)
    return registry


@lru_cache(maxsize=None)
def get_registry(schema_name: str) -> SchemaRegistry:
    """The registry for one schema, built once and validated on build."""
    if schema_name not in SCHEMA_NAMES:
        raise KeyError(f"unknown schema {schema_name!r}")
    registry = (
        _build_script_registry()
        if schema_name == "script"
        else _build_config_registry(schema_name)
    )
    registry.validate()
    return registry


def all_registries() -> dict[str, SchemaRegistry]:
    return {name: get_registry(name) for name in SCHEMA_NAMES}


def clear_cache() -> None:
    get_registry.cache_clear()
