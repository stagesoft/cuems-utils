import re
from decimal import Decimal

from ..helpers import CuemsDict

_UUID_PATTERN = r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}'
_ALIAS_RE = re.compile(rf'^{_UUID_PATTERN}_\d+$')
_CUSTOM_RE = re.compile(rf'^{_UUID_PATTERN}_custom_\d+$')

# Absorb float round-trip noise (xs:float round-trip can drift ~1e-7).
_CONTAINMENT_EPS = 1e-6

_REGION_KEYS = ('x', 'y', 'width', 'height')


def _classify_output_name(output_name: str) -> str:
    """Return 'alias' or 'custom' for a video output_name.

    Raises ValueError if the name matches neither shape.
    """
    if not isinstance(output_name, str):
        raise ValueError(f"output_name must be a string, got {type(output_name).__name__}")
    if _CUSTOM_RE.match(output_name):
        return 'custom'
    if _ALIAS_RE.match(output_name):
        return 'alias'
    raise ValueError(
        f"output_name {output_name!r} does not match alias '<uuid>_<int>' "
        f"or custom '<uuid>_custom_<int>' shape"
    )


def _validate_canvas_region(region) -> dict:
    """Normalise + validate a canvas_region dict.

    Coerces Decimal to float (defensive against xmlschema legacy paths).
    Returns a fresh dict with keys in canonical order.
    """
    if not isinstance(region, dict):
        raise ValueError(
            f"canvas_region must be a dict, got {type(region).__name__}"
        )
    missing = [k for k in _REGION_KEYS if k not in region]
    if missing:
        raise ValueError(f"canvas_region missing keys: {missing}")
    extras = [k for k in region if k not in _REGION_KEYS]
    if extras:
        raise ValueError(f"canvas_region has unexpected keys: {extras}")

    out = {}
    for k in _REGION_KEYS:
        v = region[k]
        if isinstance(v, Decimal):
            v = float(v)
        try:
            v = float(v)
        except (TypeError, ValueError):
            raise ValueError(f"canvas_region[{k!r}] must be numeric, got {v!r}")
        out[k] = v

    x, y, w, h = out['x'], out['y'], out['width'], out['height']
    if not (0.0 <= x <= 1.0):
        raise ValueError(f"canvas_region.x must be in [0, 1], got {x}")
    if not (0.0 <= y <= 1.0):
        raise ValueError(f"canvas_region.y must be in [0, 1], got {y}")
    if not (0.0 < w <= 1.0):
        raise ValueError(f"canvas_region.width must be in (0, 1], got {w}")
    if not (0.0 < h <= 1.0):
        raise ValueError(f"canvas_region.height must be in (0, 1], got {h}")
    if x + w > 1.0 + _CONTAINMENT_EPS:
        raise ValueError(f"canvas_region x+width must be <= 1, got {x + w}")
    if y + h > 1.0 + _CONTAINMENT_EPS:
        raise ValueError(f"canvas_region y+height must be <= 1, got {y + h}")

    return out


class CueOutput(CuemsDict):
    """Base class for cue output configurations.

    This class provides the basic structure for configuring how cues are output
    to different types of devices or systems.
    """

    def __init__(self, init_dict=None):
        """Initialize a CueOutput.

        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            super().__init__(init_dict)

    def __json__(self):
        """Convert the output configuration to a JSON-compatible dictionary.

        Returns:
            dict: A dictionary representation of the output configuration.
        """
        return {type(self).__name__: dict(self.items())}


class AudioCueOutput(CueOutput):
    """Output configuration for audio cues.

    Free-form output_name; no canvas/region concerns. Left unvalidated by design
    — audio channels use domain-specific names (e.g. 'system:playback_1').
    """
    pass


class VideoCueOutput(CueOutput):
    """Output configuration for video cues.

    Two modes distinguished by ``output_name`` shape:

    * Alias (``<node_uuid>_<int>``): references a monitor-resolved entry from
      project_mappings. ``canvas_region`` must be absent.
    * Custom (``<node_uuid>_custom_<int>``): per-cue custom region on this
      node's canvas. ``canvas_region`` is required and carries normalized
      floats in ``[0, 1]``.

    Note: this is the per-cue canvas_region — the authoritative placement
    of a cue's output on the node's virtual canvas at playback time.
    The UI-template canvas_region in ``project_mappings.xsd``
    ``VideoPutType`` is a separate concept (a default rectangle offered
    by the editor when authoring a custom cue); it is neither a
    physical display-layout directive nor a substitute for this field.
    """

    def __init__(self, init_dict=None):
        """Initialize a VideoCueOutput.

        Raises:
            ValueError: On malformed ``output_name``, wrong ``canvas_region``
                presence for the detected mode, or invalid region shape/values.
        """
        self._initialized = False
        if init_dict is None:
            super().__init__()
            self._initialized = True
            return

        init_dict = dict(init_dict)
        output_name = init_dict.get('output_name')
        kind = _classify_output_name(output_name)

        canvas_region = init_dict.get('canvas_region')
        if kind == 'alias' and canvas_region is not None:
            raise ValueError(
                f"canvas_region must be absent for alias output_name "
                f"{output_name!r}"
            )
        if kind == 'custom' and canvas_region is None:
            raise ValueError(
                f"canvas_region is required for custom output_name "
                f"{output_name!r}"
            )
        if canvas_region is not None:
            init_dict['canvas_region'] = _validate_canvas_region(canvas_region)

        super().__init__(init_dict)
        self._initialized = True

    def get_output_name(self) -> str:
        return super().__getitem__('output_name')

    def set_output_name(self, output_name: str) -> None:
        kind = _classify_output_name(output_name)
        if getattr(self, '_initialized', False):
            has_region = 'canvas_region' in self
            if kind == 'alias' and has_region:
                raise ValueError(
                    f"cannot change output_name to alias {output_name!r} "
                    f"while canvas_region is set"
                )
            if kind == 'custom' and not has_region:
                raise ValueError(
                    f"cannot change output_name to custom {output_name!r} "
                    f"without setting canvas_region first"
                )
        super().__setitem__('output_name', output_name)

    output_name = property(get_output_name, set_output_name)

    def get_canvas_region(self):
        return super().__getitem__('canvas_region') if 'canvas_region' in self else None

    def set_canvas_region(self, canvas_region) -> None:
        if canvas_region is None:
            if getattr(self, '_initialized', False):
                output_name = super().__getitem__('output_name')
                if _classify_output_name(output_name) == 'custom':
                    raise ValueError(
                        f"canvas_region cannot be cleared on custom output "
                        f"{output_name!r}"
                    )
            if 'canvas_region' in self:
                super().__delitem__('canvas_region')
            return

        validated = _validate_canvas_region(canvas_region)
        if getattr(self, '_initialized', False):
            output_name = super().__getitem__('output_name')
            if _classify_output_name(output_name) == 'alias':
                raise ValueError(
                    f"canvas_region cannot be set on alias output "
                    f"{output_name!r}"
                )
        super().__setitem__('canvas_region', validated)

    canvas_region = property(get_canvas_region, set_canvas_region)

    def items(self):
        """Return items in XSD element order: output_name, output_geometry, canvas_region.

        canvas_region is emitted only when present.
        """
        ordered = {}
        for key in ('output_name', 'output_geometry'):
            if key in self:
                ordered[key] = super().__getitem__(key)
        if 'canvas_region' in self:
            ordered['canvas_region'] = super().__getitem__('canvas_region')
        for key, value in super().items():
            if key not in ordered:
                ordered[key] = value
        return ordered.items()


class DmxCueOutput(CueOutput):
    """Output configuration for DMX cues.

    Free-form output_name; left unvalidated by design.
    """
    pass
