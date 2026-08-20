"""Models for ``project_mappings.xsd`` (T046) — eleven types, plus the root.

This schema carries all three of F14's compensations and all of F15's shape
confusion, so it is where the derivation earns its keep. The five-level walk in
``ConfigManager.load_net_and_node_mappings`` existed because **nothing stated
the nesting**; it is stated here, once, and the walk goes (T051).

The nesting itself does not go and is not meant to: a node has devices, a
device has put-groups, a put-group has puts, a put has mappings. What goes is
rediscovering that by iteration at every level.

Two types appear in both this schema and ``script.xsd`` — ``CanvasRegionType``
and the ``UnitFloat``/``PositiveUnitFloat`` simple types it uses — and the XSD
says so in a comment. The **classes** are not shared: registries are per schema
(research R4), and a class bound in two of them makes
``coercion.adapter_table`` ambiguous by construction. ``script.xsd`` keeps
``CanvasRegionType`` ``GENERIC``; this one gets a model.
"""

from __future__ import annotations

from ..helpers import Unset
from .base import ConfigDict


class MappingsType(ConfigDict):
    """The anonymous ``<mappings>`` wrapper inside a put.

    One repeated child, ``mapped_to``. Named because ``PutType`` references it
    and the coherence check needs something to compare against; the walk that
    used to rediscover it is what T051 deletes.
    """

    DECLARED_DEFAULTS = {"mapped_to": Unset}


class PutType(ConfigDict):
    """One audio or DMX port: identity, label, and where it actually goes.

    ``name`` is a human-readable label; ``mappings[0].mapped_to`` is the real
    target — the JACK port for audio, the DRM connector for video. Consumers
    fall back to ``name`` for legacy entries that carry no mappings, and that
    fallback is *domain knowledge*, so it stays hand-written in
    ``ConfigManager`` rather than being expressed here.
    """

    DECLARED_DEFAULTS = {
        "id": Unset,
        "name": Unset,
        "mappings": Unset,
    }


class VideoPutType(ConfigDict):
    """A video port. ``PutType`` plus an optional ``canvas_region``.

    Not a subclass of :class:`PutType`, because the XSD does not make it one:
    ``VideoPutType`` is an independent ``xs:complexType`` that happens to
    repeat three of ``PutType``'s four fields. Inheriting would state a
    relationship the schema does not, which is the direction of drift this
    whole feature removes — and ``canvas_region``'s position in the sequence
    (before ``mappings``) is part of the derived order.

    **``canvas_region`` here is a UI-template hint**, easy to misread. It
    offers the editor's output picker a default starting rectangle for a named
    custom slot. It does *not* describe physical monitor layout (that comes
    from videocomposer's DRM detection) and it is *not* a per-cue output region
    — those live in ``script.xsd``'s ``VideoCueOutput.canvas_region``.
    """

    DECLARED_DEFAULTS = {
        "id": Unset,
        "name": Unset,
        "canvas_region": Unset,
        "mappings": Unset,
    }


class PutGroupType(ConfigDict):
    """An ``xs:choice`` of ``output`` or ``input``, each repeatable.

    Both are declared, because a choice's members are both *declarable* fields
    even though a given document carries one. ``Unset`` keeps the absent one
    absent rather than present-and-empty.
    """

    DECLARED_DEFAULTS = {
        "output": Unset,
        "input": Unset,
    }


class VideoPutGroupType(ConfigDict):
    DECLARED_DEFAULTS = {
        "output": Unset,
        "input": Unset,
    }


class DeviceType(ConfigDict):
    """Audio or DMX on one node: output groups and input groups."""

    DECLARED_DEFAULTS = {
        "outputs": Unset,
        "inputs": Unset,
    }


class VideoDeviceType(ConfigDict):
    DECLARED_DEFAULTS = {
        "outputs": Unset,
        "inputs": Unset,
    }


class NodeType(ConfigDict):
    """One node's device mappings — what ``ConfigManager.node_mappings`` holds.

    Distinct from ``network_map.xsd``'s ``NodeType``, which describes node
    *identity* rather than node *mappings*. Two schemas, two types, two
    classes; sharing one would be the F15 failure in miniature.
    """

    DECLARED_DEFAULTS = {
        "uuid": Unset,
        "mac": Unset,
        "audio": Unset,
        "video": Unset,
        "dmx": Unset,
    }


class NodesType(ConfigDict):
    DECLARED_DEFAULTS = {"node": Unset}


class NewNodesType(ConfigDict):
    DECLARED_DEFAULTS = {"node": Unset}


class CanvasRegionType(ConfigDict):
    """A normalized rectangle on the node's virtual canvas.

    Each component is constrained to ``[0, 1]`` by the schema (T1). That their
    **sums** must also be bounded is not expressible there and stays a T2 rule
    — ``check_canvas_region_containment`` — which is the boundary this feature
    keeps checkable: anything in ``xml/validators.py`` is a rule XSD *cannot*
    express.
    """

    DECLARED_DEFAULTS = {
        "x": Unset,
        "y": Unset,
        "width": Unset,
        "height": Unset,
    }


class MappedToType(ConfigDict):
    """Declared in the schema and referenced by no element.

    Modelled anyway, for the same reason as ``settings.xsd``'s
    ``CTimecodeType``: the registry requires a binding for every complex type
    (C7), and an exception list is worse than a class nobody instantiates.
    """

    DECLARED_DEFAULTS = {
        "uuid": Unset,
        "name": Unset,
    }


class CuemsProjectMappingsType(ConfigDict):
    """The document root — what ``ConfigManager.mappings`` holds.

    Bound by element path: the root type is anonymous (research R3).
    """

    DECLARED_DEFAULTS = {
        "number_of_nodes": Unset,
        "default_audio_input": Unset,
        "default_audio_output": Unset,
        "default_video_input": Unset,
        "default_video_output": Unset,
        "default_dmx_input": Unset,
        "default_dmx_output": Unset,
        "nodes": Unset,
        "new_nodes": Unset,
    }
