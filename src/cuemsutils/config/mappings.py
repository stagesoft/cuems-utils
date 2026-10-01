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

import re

from ..helpers import Unset
from .base import ConfigDict, save_document


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


class DeviceClassType(ConfigDict):
    """The class-only base every device alternative extends.

    ``class`` is a dict key. It is not a Python property.
    """

    DECLARED_DEFAULTS = {
        "class": Unset,
    }


class DeviceType(ConfigDict):
    """Audio, DMX, or any class with no special fields."""

    DECLARED_DEFAULTS = {
        "class": Unset,
        "outputs": Unset,
        "inputs": Unset,
    }


class VideoDeviceType(ConfigDict):
    DECLARED_DEFAULTS = {
        "class": Unset,
        "outputs": Unset,
        "inputs": Unset,
    }


class DevicesType(ConfigDict):
    """The ``<devices>`` container. The decoded field holds the repeated list."""

    DECLARED_DEFAULTS = {
        "device": Unset,
    }


class DefaultPortType(ConfigDict):
    """One default port. ``&`` is the converter's text key: the element text."""

    DECLARED_DEFAULTS = {
        "class": Unset,
        "direction": Unset,
        "&": Unset,
    }


class DefaultsType(ConfigDict):
    """The ``<defaults>`` container. The decoded field holds the repeated list."""

    DECLARED_DEFAULTS = {
        "default": Unset,
    }


def _devices_of(node) -> list:
    devices = dict.get(node, "devices")
    return devices if isinstance(devices, list) else []


def device_of_class(node, device_class: str):
    """The device whose ``class`` is ``device_class``, or ``None``.

    No class list. The document is the vocabulary (FR-012a).
    """
    for item in _devices_of(node):
        if not isinstance(item, dict):
            continue
        device = dict.get(item, "device")
        if isinstance(device, dict) and dict.get(device, "class") == device_class:
            return device
    return None


_DEFAULT_KEY = re.compile(r"^default_(.+)_(input|output)$")


def _legacy_default(root, device_class: str, direction: str):
    defaults = dict.get(root, "defaults")
    if not isinstance(defaults, list):
        raise KeyError(f"default_{device_class}_{direction}")
    for item in defaults:
        if not isinstance(item, dict):
            continue
        port = dict.get(item, "default")
        if (
            isinstance(port, dict)
            and dict.get(port, "class") == device_class
            and dict.get(port, "direction") == direction
        ):
            text = dict.get(port, "&")
            return "" if text in (None, Unset) else text
    raise KeyError(f"default_{device_class}_{direction}")


def _set_legacy_default(root, device_class: str, direction: str, value) -> None:
    defaults = dict.get(root, "defaults")
    if not isinstance(defaults, list):
        defaults = []
        dict.__setitem__(root, "defaults", defaults)
    for item in defaults:
        if not isinstance(item, dict):
            continue
        port = dict.get(item, "default")
        if (
            isinstance(port, dict)
            and dict.get(port, "class") == device_class
            and dict.get(port, "direction") == direction
        ):
            port["&"] = value
            return
    defaults.append({
        "default": DefaultPortType({
            "class": device_class,
            "direction": direction,
            "&": value,
        })
    })


class NodeMappingType(ConfigDict):
    """One node's device mappings — what ``ConfigManager.node_mappings`` holds.

    Distinct from ``network_map.xsd``'s ``NodeType``, which describes node
    *identity* rather than node *mappings*. Two schemas, two types, two
    classes; sharing one would be the F15 failure in miniature.

    **Named ``NodeMappingType``, not ``NodeType``** (rc16): both schemas used to
    declare ``NodeType`` in the same namespace with different content, which is
    the X14 pattern that ``tests/contract/test_schema_name_overlap.py`` exists
    to stop. ``network_map``'s keeps the plain name -- identity is the older and
    broader meaning -- and this one takes the narrower one it always had.
    """

    DECLARED_DEFAULTS = {
        "uuid": Unset,
        "mac": Unset,
        "devices": Unset,
    }

    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            device = device_of_class(self, key) if isinstance(key, str) else None
            if device is None:
                raise
            return device

    def get(self, key, default=None):
        # ``dict.get`` does not call ``__getitem__``. NodeEngine reads a class
        # with ``.get`` (FR-012a); a missing class stays the default.
        try:
            return self[key]
        except KeyError:
            return default


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
        "defaults": Unset,
        "nodes": Unset,
        "new_nodes": Unset,
    }

    def __getitem__(self, key):
        match = _DEFAULT_KEY.fullmatch(key) if isinstance(key, str) else None
        if match is not None and key not in self.keys():
            return _legacy_default(self, match.group(1), match.group(2))
        return super().__getitem__(key)

    def __setitem__(self, key, value):
        match = _DEFAULT_KEY.fullmatch(key) if isinstance(key, str) else None
        if match is not None and key not in self.keys():
            _set_legacy_default(self, match.group(1), match.group(2), value)
            return
        super().__setitem__(key, value)

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def save(self, path) -> None:
        """Validate (T1), then write atomically (feature 008, FR-013/FR-015/FR-017).

        Symmetric with the landed ``CuemsNetworkMapType.save`` — see
        ``config.base.save_document`` for the shared contract.

        Args:
            path (str | os.PathLike): where to write.

        Raises:
            SchemaError: the document does not match ``project_mappings.xsd``.
            OSError: propagated unwrapped.
        """
        save_document(self, "project_mappings", path)
