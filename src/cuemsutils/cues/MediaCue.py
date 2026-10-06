import re
from typing import Tuple

from .Cue import Cue

from ..helpers import CuemsDict, ensure_items, format_timecode, Unset
from ..tools.CTimecode import CTimecode

REQ_ITEMS = {
    'Media': None,
    # The device-class discriminator (feature 013, axis D). Declared on this
    # class and on ``DmxCue`` because ``MediaCueType`` and ``DmxCueType`` are
    # the two types that extend ``CueClassType``; ``Cue``, ``CueList``,
    # ``ActionCue`` and ``FadeCue`` extend ``CueType`` and carry none
    # (FR-050a).
    #
    # ``Unset`` on the *base*: ``MediaCue`` is the unconditional alternative,
    # the type an unknown class validates as, so its class is whatever the
    # document carried. Each concrete subclass declares its own literal, which
    # is what makes ``AudioCue({...}).save()`` produce a valid document.
    'class': Unset,
    'outputs': None,
}
# ``fade_profiles`` moved to AudioCue and VideoCue (feature 004, T059).
#
# It was declared here, on the base, while ``script.xsd`` declares it on
# ``AudioCueType`` and ``VideoCueType`` — the two concrete types — and *not* on
# ``MediaCueType``. Nothing broke, because both subclasses inherited it and both
# schema types have it; the base class simply claimed a field its schema type
# does not define.
#
# Found by the coherence test (FR-020) on its first run, which is the drift
# class that test exists for: the Python declaration and the XSD were
# maintained in two files by hand, and the only thing that would ever have
# noticed was a document failing to validate at save time.

REGION_REQ_ITEMS = {
    'id': 0,
    'loop': 1,
    'in_time': None,
    'out_time': None
}

def _as_region(item) -> "Region":
    """One region, from any of the four shapes it is supplied in (FR-009).

    Unwraps the reader's ``{'Region': {...}}`` form before construction: that
    single-key wrapper is the element name the schema states, not a field, and
    building a ``Region`` from it directly would produce a region whose only
    key is ``Region``.
    """
    if isinstance(item, Region):
        return item
    if not isinstance(item, dict):
        raise ValueError(
            f"a region must be a mapping or a Region, got "
            f"{type(item).__name__}: {item!r}"
        )

    if len(item) == 1 and 'Region' in item:
        item = item['Region']
        if not isinstance(item, dict):
            raise ValueError(
                f"wrapped region content must be a mapping, got "
                f"{type(item).__name__}"
            )

    # A non-empty mapping sharing no key with the declared field set is not a
    # region in any of the four shapes — most likely a wrapper with the wrong
    # tag. ``Region``'s setter would skip every unknown key in silence and hand
    # back an empty region, which is the shape of failure FR-009a exists to
    # prevent. An empty mapping keeps its existing meaning ("defaults").
    if item and not set(item) & set(Region.declared_fields()):
        raise ValueError(
            f"region mapping declares none of "
            f"{list(Region.declared_fields())}: {sorted(item)}"
        )
    return Region(item)


#: ``cms:Md5Type``'s pattern, mirrored. Lowercase only, 32 characters —
#: the same shape and the same case rule as ``UuidType``.
_MD5_RE = re.compile(r"[a-f0-9]{32}")


class Region(CuemsDict):
    """A class representing a region within a media file."""

    #: Declared fields, in ``RegionType``'s schema order (T026).
    #:
    #: ``REGION_REQ_ITEMS`` existed before this feature and **nothing read it**:
    #: ``__init__`` used a local ``empty_keys = {"id": "0"}`` literal instead,
    #: so a region's declared field set was a dict that documented an intention
    #: no code carried out. Promoting it to the real declaration is what moves
    #: coherence coverage off 13/18.
    DECLARED_DEFAULTS = REGION_REQ_ITEMS

    def __init__(self, init_dict = None):
        """Initialize a Region.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values will be used.
        """
        if init_dict:
            self.setter(init_dict)
        # The declared field set, replacing a local ``empty_keys = {'id': '0'}``
        # literal that made a bare region the one object in the model whose
        # defaults lived inside its own ``__init__`` (T026).
        self._fill_declared_defaults()
    
    def get_id(self):
        """Get the region ID.
        
        Returns:
            str: The region's identifier.
        """
        return super().__getitem__('id')

    def set_id(self, id):
        """Set the region ID.
        
        Args:
            id: The new region identifier.
        """
        super().__setitem__('id', id)

    id = property(get_id, set_id)

    def get_loop(self):
        """Get the loop count for this region.
        
        Returns:
            int: The number of times the region should loop.
        """
        return super().__getitem__('loop')

    def set_loop(self, loop):
        """Set the loop count for this region.
        
        Args:
            loop (int): The number of times the region should loop.
        """
        super().__setitem__('loop', loop)

    loop = property(get_loop, set_loop)

    def get_in_time(self):
        """Get the in point of the region.
        
        Returns:
            CTimecode: The timecode where the region starts.
        """
        return super().__getitem__('in_time')

    def set_in_time(self, in_time):
        """Set the in point of the region.
        
        Args:
            in_time: The new in point timecode.
        """
        in_time = format_timecode(in_time)
        super().__setitem__('in_time', in_time)

    in_time = property(get_in_time, set_in_time)

    def get_out_time(self):
        """Get the out point of the region.
        
        Returns:
            CTimecode: The timecode where the region ends.
        """
        return super().__getitem__('out_time')

    def set_out_time(self, out_time):
        """Set the out point of the region.
        
        Args:
            out_time: The new out point timecode.
        """
        out_time = format_timecode(out_time)
        super().__setitem__('out_time', out_time)

    out_time = property(get_out_time, set_out_time)

class Media(CuemsDict):
    """A class representing a media file with associated regions."""

    #: Self-wrapping JSON projection: ``{"Media": {...}}`` (T018).
    JSON_SELF_WRAPS = True

    #: Declared fields, in ``MediaType``'s schema order (T026).
    #:
    #: All four are required by the schema, so each takes ``Unset``: a ``Media``
    #: built bare must not start emitting four empty elements.
    #:
    #: ``duration`` is ``cms:CTimecodeType`` (feature 008, FR-002/FR-003) — the
    #: same type and the same ``format_timecode`` machinery every other
    #: time-carrying element uses. It used to be the plain-string
    #: ``TimecodeType``, the last of seven time values with its own storage
    #: exception; that exception is gone, and so is the three-branch dispatch
    #: it needed.
    DECLARED_DEFAULTS = {
        'file_name': Unset,
        'id': Unset,
        'duration': Unset,
        'regions': Unset,
        # Feature 014's media block. ``Unset`` for the same reason the four
        # above use it, and **not** for the reason that comment gives: those
        # four are required by the schema, these are ``minOccurs="0"``, and
        # ``Unset`` is what "declared but emits nothing when absent" *means*
        # (``helpers.py``'s ``Unset`` docstring, with ``canvas_region`` as the
        # precedent). Defaulting them to ``None`` would start emitting four
        # empty elements, which ``xs:positiveInteger`` rejects.
        'pixel_width': Unset,
        'pixel_height': Unset,
        'file_size': Unset,
        'file_md5': Unset,
    }
    
    def __init__(self, init_dict = None):
        """Initialize a Media object.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If provided, will be used to set initial properties.
        """
        if init_dict:
            self.setter(init_dict)
    
    def get_file_name(self):
        """Get the media file name.
        
        Returns:
            str: The name of the media file.
        """
        return super().__getitem__('file_name')

    def set_file_name(self, file_name):
        """Set the media file name.
        
        Args:
            file_name (str): The new media file name.
        """
        super().__setitem__('file_name', file_name)

    file_name = property(get_file_name, set_file_name)

    def get_id(self):
        """Get the UUID of the media file.
        
        Returns:
            str: The UUID of the media file.
        """
        return super().__getitem__('id')

    def set_id(self, id):
        """Set the UUID of the media file.
        
        Args:
            id (str): The new UUID of the media file.
        """
        super().__setitem__('id', self.coerce('id', id))

    id = property(get_id, set_id)

    def get_duration(self):
        """Get the duration of the media file.

        Returns:
            CTimecode | None: The duration of the media file.
        """
        return super().__getitem__('duration')

    def set_duration(self, duration):
        """Set the duration of the media file, validating on write.

        Collapsed to the same one-branch shape every other ``CTimecodeType``
        setter uses (feature 008, FR-004) — ``FadeCue.duration``'s pattern,
        now that ``Media.duration`` carries the same schema type. The stored
        value is a ``CTimecode`` object, not a string: the getter's contract
        changes accordingly (FR-002), which is the point of retyping the
        field rather than a side effect of it.

        Args:
            duration (str | CTimecode | int | float | dict | None):
                anything :func:`~cuemsutils.helpers.format_timecode` accepts.

        Raises:
            ValueError: If *duration* cannot be parsed as a timecode.
        """
        from ..xml.validators import enforce

        # The rule, by name (T073) — parses via the same ``format_timecode``
        # this setter then uses to store, so a value that fails here would
        # fail identically below (FR-005).
        enforce('media_duration', duration, self)
        if duration is None:
            super().__setitem__('duration', None)
            return
        super().__setitem__('duration', format_timecode(duration))

    duration = property(get_duration, set_duration)

    def get_regions(self):
        """Get the list of regions in the media file.
        
        Returns:
            list: The list of Region objects.
        """
        return super().__getitem__('regions')

    def set_regions(self, regions):
        """Set the list of regions in the media file, coercing every member.

        The previous body computed the coercion and **threw it away** (F12): it
        iterated ``for r in regions`` and rebound the *loop variable* rather
        than the list member, so ``Region(r)`` was constructed and discarded on
        every pass and the raw mapping stayed in the list. Combined with the
        decoder never reaching ``RegionType``'s binding (F19), that is why no
        region anywhere was ever a ``Region``.

        Four supply shapes reach here, all measured (FR-009):

        * a single mapping — one region, not wrapped in a list;
        * a list of mappings;
        * a list of already-typed ``Region`` objects — idempotent (FR-004);
        * the wrapped ``{'Region': {...}}`` form the reader produces, which is
          what every document and every editor payload carries today.

        Anything else **raises** (FR-009a). Passing an unrecognised shape
        through unchanged would leave a plain dictionary in ``regions`` — this
        very defect, silently restored — and no golden would catch it, because
        a shape that never round-trips never reaches a comparison.

        Args:
            regions: ``None``, a mapping, a ``Region``, or a list of either.

        Raises:
            ValueError: If a member matches none of the four supported shapes.
        """
        if regions is None:
            super().__setitem__('regions', None)
            return

        if isinstance(regions, (Region, dict)):
            regions = [regions]
        elif not isinstance(regions, list):
            raise ValueError(
                f"regions must be a mapping, a Region, or a list of either — "
                f"got {type(regions).__name__}"
            )

        super().__setitem__('regions', [_as_region(item) for item in regions])

    regions: list[Region] = property(get_regions, set_regions)

    # --- the media block (feature 014) ----------------------------------
    #
    # Four optional elements, measured once by whoever probes the file and read
    # thereafter, so the engine does not run ffprobe while holding the command
    # lock. Each needs **both** a ``DECLARED_DEFAULTS`` entry and a
    # ``set_<name>`` accessor: ``CuemsDict.setter`` resolves
    # ``getattr(self, f"set_{k}")`` and ``continue``s on ``AttributeError``, so
    # a field with one and not the other is dropped **in silence**.
    #
    # ``None`` removes the key rather than storing it. Absent means *unknown*,
    # and that is the only way to say so: the schema has no empty form, and 0
    # is not a value.

    def _set_positive_int(self, key, value):
        """Store a positive integer, or remove the key when *value* is ``None``.

        Shared by the three integers because the rule is one rule. Accepts an
        ``int`` or a string of digits and stores an ``int``; **no upper bound**,
        deliberately — ``file_size`` must hold a file past 100 GB, which is
        107,374,182,400 bytes and overflows a 32-bit int. Python's ``int`` is
        arbitrary-precision and ``xs:positiveInteger`` is unbounded, so the
        range is a property of the types rather than something to check.

        Raises:
            ValueError: *value* is not a positive integer. Raising here rather
                than letting the schema refuse it at save names the field and
                fails at the assignment that caused it.
        """
        if value is None:
            super().pop(key, None)
            return
        if isinstance(value, bool):
            # ``bool`` is an ``int`` subclass, so this would otherwise store
            # ``True`` as 1 — a plausible-looking pixel width.
            raise ValueError(f"{key} must be a positive integer, got a bool")
        if isinstance(value, int):
            coerced = value
        elif isinstance(value, str) and value.isdigit():
            coerced = int(value)
        else:
            # Deliberately **not** ``int(value)`` on anything else: that
            # truncates, so ``1.5`` would store 1 — a wrong value that looks
            # right, which is the defect class this whole feature exists to
            # remove (see ``_Bool.decode``, which used to make ``False`` out of
            # any string). A fractional pixel count or byte count is nonsense;
            # refusing it names the field at the assignment.
            raise ValueError(
                f"{key} must be a positive integer or a string of digits, "
                f"got {value!r}"
            )
        if coerced < 1:
            raise ValueError(
                f"{key} must be positive; absent means unknown and 0 is not a "
                f"value, so pass None to clear it rather than {coerced}"
            )
        super().__setitem__(key, coerced)

    def get_pixel_width(self):
        """The media's original width in pixels, or ``None`` if unknown.

        The media's **own** size as ``ffprobe`` reports it — not the layer's
        size on screen, which is ``CanvasRegionType``'s ``width``/``height`` as
        unit floats.
        """
        return super().get('pixel_width')

    def set_pixel_width(self, value):
        self._set_positive_int('pixel_width', value)

    pixel_width = property(get_pixel_width, set_pixel_width)

    def get_pixel_height(self):
        """The media's original height in pixels, or ``None`` if unknown."""
        return super().get('pixel_height')

    def set_pixel_height(self, value):
        self._set_positive_int('pixel_height', value)

    pixel_height = property(get_pixel_height, set_pixel_height)

    def get_file_size(self):
        """The file's size in bytes when it was measured, or ``None``."""
        return super().get('file_size')

    def set_file_size(self, value):
        self._set_positive_int('file_size', value)

    file_size = property(get_file_size, set_file_size)

    def get_file_md5(self):
        """The file's md5 when it was measured, or ``None`` if unknown."""
        return super().get('file_md5')

    def set_file_md5(self, value):
        """Store a 32-character lowercase md5, or remove the key for ``None``.

        **Nothing is normalised.** An uppercase digest raises rather than being
        lowercased, because the schema refuses it and silently "fixing" a value
        here would mean the object and the document disagree about what is
        valid. ``md5sum``, ``hashlib`` and ``ffmpeg`` all emit lowercase, so
        the strict form costs a caller nothing it was not already doing.

        The house precedent is what settles it rather than taste:
        :class:`~cuemsutils.tools.Uuid.Uuid` **raises** on an uppercase uuid
        instead of lowercasing it, and ``Md5Type`` was written to match
        ``UuidType`` facet for facet. The rc15 line's setter normalises instead
        (*"accepts 32 hex digits in any case, and stores them lowercase"*), so
        a caller that relied on the library lowercasing for it — the editor,
        which stores the md5 its client sent — must ``.lower()`` before
        assigning here. See
        ``specs/planning/stored-media-values-preimplementation.md``.

        Raises:
            ValueError: *value* is not 32 lowercase hexadecimal characters.
        """
        if value is None:
            super().pop('file_md5', None)
            return
        if not isinstance(value, str) or not _MD5_RE.fullmatch(value):
            raise ValueError(
                f"file_md5 must be 32 lowercase hexadecimal characters "
                f"(cms:Md5Type), got {value!r}"
            )
        super().__setitem__('file_md5', value)

    file_md5 = property(get_file_md5, set_file_md5)


class MediaCue(Cue):
    """Base class for media-related cues (audio and video).
    
    This class extends Cue to provide common functionality for media playback,
    including media file handling and output routing.
    """

    #: Declared fields and their defaults for this class alone;
    #: :meth:`CuemsDict.declared_defaults` accumulates the chain.
    DECLARED_DEFAULTS = REQ_ITEMS
    
    def __init__(self, init_dict = None):
        """Initialize a MediaCue.
        
        Args:
            init_dict (dict, optional): Dictionary containing initialization values.
                If not provided, default values from REQ_ITEMS will be used.
        """
        if not init_dict:
            init_dict = REQ_ITEMS
        else:
            init_dict = ensure_items(init_dict, REQ_ITEMS)
        super().__init__(init_dict)

    def get_Media(self):
        """Get the media object associated with this cue.
        
        Returns:
            Media: The media object containing file and region information.
        """
        return super().__getitem__('Media')

    def set_Media(self, value):
        """Set the media object for this cue.
        
        Args:
            value (Media or dict): The media object or dictionary to create one.
        """
        if not isinstance(value, Media):
            value = Media(value)
        super().__setitem__('Media', value)

    media: Media = property(get_Media, set_Media)

    def get_outputs(self):
        """Get the output routing configuration.
        
        Returns:
            list: The list of output configurations.
        """
        return super().__getitem__('outputs')

    def set_outputs(self, outputs):
        """Set the output routing configuration.
        
        Args:
            outputs (list): The list of output configurations.
        """
        super().__setitem__('outputs', outputs)

    outputs = property(get_outputs, set_outputs)

    def get_all_output_names(self) -> list[Tuple[str, str]]:
        """Get all output names splitted into node and output ids for the media cue.
        Returns:
            list: The list of output names.
        """
        # DEV: To allow proper mapping, we need to split the output name into node and output ids.
        # Additional logic in case mapping is developed and generalized output names (without node id) are used.
        # e.g: [(None,'generalized_output_id'), ('node_uuid','output_id'), ...]
        return [(output['output_name'][:36], output['output_name'][37:]) for output in self.outputs]

    def localize_cue(self, node_id: str) -> None:
        """Localize the cue outputs to the given node UUID.

        Sets the _local attribute to True if any of the cue outputs are local to the given node UUID, False otherwise.

        Args:
            node_id: The ID of the node to localize the cue to.
        """
        self._local = any(x[0] == node_id for x in self.get_all_output_names())
        

