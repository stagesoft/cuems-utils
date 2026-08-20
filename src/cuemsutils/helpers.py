"""Set of helper functions for the cuemsutils package."""

from os import access, mkdir, path, R_OK, W_OK
from datetime import datetime
from typing import Any
from collections.abc import ItemsView, KeysView
from xml.etree.ElementTree import Element, SubElement

from .tools.CTimecode import CTimecode
from .tools.Uuid import Uuid

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class _UnsetType:
    """The type of :data:`Unset`. Singleton, falsy, and self-describing."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "Unset"


#: A declared field with **no** default: the key stays *absent* rather than
#: present-and-empty.
#:
#: It exists because "one defaulting protocol" must not become "every field is
#: always present". Six classes gain a defaults declaration in this feature
#: (``Cue``, ``CuemsScript``, ``Media`` and the three ``CueOutput`` subclasses),
#: and several of their fields are optional in the schema — ``canvas_region`` is
#: the clearest case. Defaulting those to ``None`` would start emitting elements
#: the documents never contained, and the goldens would move. ``Unset`` is how a
#: field is declared *without* being materialised.
#:
#: Distinct from ``None``, which is a real value here: ``description`` defaults
#: to ``None`` and emits as ``<description />``.
Unset = _UnsetType()

#: Accumulated declarations, keyed on the **exact** class — same reasoning as
#: ``coercion._TABLES``: an attribute would be inherited through the MRO and a
#: subclass would silently answer with its parent's field set.
_DECLARED_DEFAULTS: dict[type, dict[str, Any]] = {}

#: Accumulated ``RUNTIME_FIELDS`` declarations, keyed on the exact class — the
#: same reasoning as ``_DECLARED_DEFAULTS`` (T010, data-model.md §4).
_RUNTIME_FIELDS: dict[type, dict[str, Any]] = {}


class CuemsDict(dict):
    """Custom dictionary class to handle cuemsutils specific items."""

    #: This class's **own** declared fields and their defaults. Subclasses
    #: declare only what they add; :meth:`declared_defaults` accumulates the
    #: chain. Left empty on the base — ``CuemsDict`` declares no fields.
    DECLARED_DEFAULTS: dict[str, Any] = {}

    #: Whether this class's JSON projection wraps itself in its own class name:
    #: ``{"AudioCue": {...}}`` rather than a bare ``{...}``.
    #:
    #: **Declared, replacing a heuristic.** ``CuemsScript.__json__`` used to
    #: detect a wrapped child by testing ``k.lower() != k`` — inferring a
    #: structural fact from the *casing of a key name*, which is true today only
    #: because the one wrapped child on the root happens to be spelled
    #: ``CueList``. A declared field named ``Media`` or a schema that lowercased
    #: that element would each have broken it silently.
    #:
    #: ``False`` on the base **deliberately**: a bare ``CuemsDict`` is what
    #: wildcard ``ui_properties`` content decodes to, and self-wrapping it would
    #: turn every cue's editor state into ``{"CuemsDict": {...}}`` in the
    #: payload. The six model classes that self-wrap say so explicitly.
    JSON_SELF_WRAPS: bool = False

    #: This class's **own** non-persisted runtime attributes and their
    #: defaults (T010, data-model.md §4). Subclasses declare only what they
    #: add or override; :meth:`runtime_fields` accumulates the chain exactly
    #: as :meth:`declared_defaults` does. A default that is *callable* is a
    #: **factory**, called fresh per object — required for ``CTimecode``
    #: defaults, so two cues never share one instance. Left empty on the
    #: base: ``CuemsDict`` itself carries no runtime state.
    RUNTIME_FIELDS: dict[str, Any] = {}

    def build(self, parent: Element):
        build_xml_dict(self, parent)

    def _fill_declared_defaults(self) -> None:
        """Insert any declared field this object does not yet carry (FR-017).

        The one defaulting protocol, applied at the end of construction. Six
        classes returned a completely **empty** object from bare construction
        before this feature — ``Cue``, ``CuemsScript``, ``Media`` and the three
        ``CueOutput`` subclasses — while thirteen returned full defaults. Same
        question, two answers, depending on which class you happened to ask.

        Written with ``dict.__setitem__`` rather than through ``setter``,
        deliberately: several setters *swallow* a ``None`` instead of storing
        it (``DmxUniverse.set_dmx_channels`` is one), so routing defaults
        through them would leave the field absent and the protocol would be
        "one rule, except where a setter disagrees".

        Fields declared :data:`Unset` are skipped — declared, but not
        materialised. That is what keeps six newly-defaulted classes from
        emitting elements their documents never contained, which the goldens
        are the gate on.
        """
        for key, default in type(self).declared_defaults().items():
            if key in self or default is Unset:
                continue
            dict.__setitem__(self, key, default() if callable(default) else default)

    def coerce(self, key: str, value):
        """Run ``key``'s adapter over ``value`` — the setters' entry point.

        The same table ``from_decoded`` uses, so a value assigned through a
        property and the same value arriving from a document end up identically
        typed (FR-001, FR-002). A field with no adapter is returned untouched.

        This is what lets ``None`` **clear** a uuid field. ``Uuid.__init__``
        mints a fresh uuid4 for any falsy argument, so ``script.id = None``
        assigned a new random id; ``_UuidAdapter.decode`` returns ``None`` for
        ``None`` and ``""``. Generating an id stays the job of the ``new_uuid``
        default, which runs at defaulting time rather than at assignment time
        (research R7, FR-019 row 3).

        It also preserves the nil-UUID leniency: the adapter keeps an
        unparseable value as its raw string rather than raising, which is how
        ``00000000-…`` stays acceptable where ``Uuid()`` would reject it.
        """
        adapter = type(self).coercion_table().get(key)
        return value if adapter is None else adapter.decode(value)

    @classmethod
    def from_decoded(cls, mapping: dict):
        """Build an instance from a decoded document — the **decode mode**.

        The second of two construction modes, and the reason there are two is
        **key order**, not coercion:

        ``cls(init_dict)``
            programmatic. Routes through ``ensure_items``, which applies
            declared defaults and sorts keys alphabetically. Unchanged.

        ``cls.from_decoded(mapping)``
            decode. Preserves the **source document's** key order, appending
            only the declared fields the document omitted.

        Routing decode through the sorting constructor would re-sort the root
        element of every hand-authored script on the next save, because
        ``CuemsScript`` is an ``xs:all`` type whose emission order *is* arrival
        order. Two of the four captured script roots are not alphabetical, so
        this is measured rather than hypothetical (research R10, contract C3).

        One coercion path, two orderings. Both modes run the *same* adapter
        table, which is what makes a decoded object and a built one the same
        object (FR-001, FR-007).

        Property setters are **not** invoked here, and that is deliberate: the
        decode path's accept/reject outcomes are pinned per document in both
        directions (FR-006/FR-006a), and routing every field through its setter
        would give fourteen inventoried value-rejecting rules new reach. The
        repeated-member path keeps calling the constructor for exactly the same
        reason — see ``Mapper._decode_member``.
        """
        obj = cls.__new__(cls)
        dict.__init__(obj)
        obj._init_runtime()

        table = cls.coercion_table()
        for key, value in mapping.items():
            adapter = table.get(key)
            dict.__setitem__(
                obj, key, value if adapter is None else adapter.decode(value)
            )

        # Declared fields the document omitted, appended after the arrival keys
        # so that ordering stays the document's. ``Unset`` means "declared but
        # not materialised" — the key stays absent rather than present-and-empty,
        # which is what stops six newly-defaulted classes from emitting elements
        # their documents never contained.
        for key, default in cls.declared_defaults().items():
            if key in obj or default is Unset:
                continue
            dict.__setitem__(obj, key, default() if callable(default) else default)

        return obj

    def items(self):
        """The declared fields of this object, in declaration order.

        **The single definition** (FR-014). Ten classes overrode this before,
        each layering its own ``REQ_ITEMS`` and two of them additionally
        hand-ordering their output — an ordering job that belongs to the
        mapper's ``TypeSpec``, which derives it from the schema.

        Built on ``extract_items`` rather than a new helper: ``Cue.items()`` was
        its only production caller, and orphaning it would drag
        ``tests/test_helpers.py`` into this feature's diff for no reason.

        A class with **no** declared field set falls through to ``dict.items()``
        unchanged. That is not a loophole — it is what keeps wildcard containers
        (``ui_properties`` subtrees) and plain dicts passing everything through.
        They have no declared fields, and filtering them would delete real
        editor state.

        Keys present on the object but not declared are **omitted**. They are
        reported once each by the serialization engine, which is the layer that
        can name the document position; see ``Mapper._selected_keys``.

        **Order is the declaration's**, which reproduces what the ten overrides
        produced by chaining ``super().items()``. Two consumers depend on it and
        neither is obvious:

        * the frozen legacy ``XmlBuilder`` iterates ``items()`` directly, and
          the schema's sequence is not alphabetical — an ``ActionCue`` emitting
          ``action_target`` first fails validation;
        * ``VideoCueOutput``'s hand-ordered override existed precisely to put
          ``canvas_region`` after ``output_geometry``.

        The script root is the one place arrival order matters instead, because
        it is an ``xs:all`` type. That belongs to its payload projection rather
        than here — see ``CuemsScript.__json__``.
        """
        declared = self.declared_fields()
        if not declared:
            return super().items()
        return extract_items(super().items(), [k for k in declared if k in self])

    def _init_runtime(self) -> None:
        """Initialize this object's non-persisted instance attributes.

        Cue objects carry state that is **not** part of the document: playback
        handles, timecode marks, arm state, locality flags. It is initialized in
        ``__init__`` today, which means a decoded object gets it only because
        decode happens to call the constructor. Feature 005 replaces that
        constructor call, so the guarantee has to become explicit or it is lost
        silently — and a cue reaching the engine without ``_go_thread`` fails at
        *playback*, not at load, which is the worst possible place to find out
        (FR-004a, contract C12).

        **The single inherited implementation** (T010, SC-014): driven by
        :attr:`RUNTIME_FIELDS`/:meth:`runtime_fields` rather than by a
        per-class override. No subclass defines this method any more — it
        sets exactly the attributes the declaration names, with no additions.

        **This hook must never touch ``_initialized``.** That flag is not an
        inert runtime attribute: it gates value-rejecting rules in three classes
        — ``ActionCue.set_action_target``, ``FadeCue.set_action_type`` and
        ``VideoCueOutput``'s ``set_output_name`` / ``set_canvas_region`` — each
        of which deliberately holds it ``False`` *while populating* so those
        rules stay off the load path. Setting it true before population would
        give fourteen inventoried setters new reach on decode, which FR-006b
        forbids, and the resulting failure is **arrival-order dependent** (a
        ``custom`` ``output_name`` arriving before ``canvas_region`` raises,
        the reverse order does not), so the corpus would catch it only by luck.
        The flag stays owned by the three classes that use it, and it is
        deliberately absent from ``RUNTIME_FIELDS`` everywhere.
        """
        for name, default in type(self).runtime_fields().items():
            setattr(self, name, default() if callable(default) else default)

    @classmethod
    def declared_defaults(cls) -> dict[str, Any]:
        """This class's declared fields and defaults, accumulated across the MRO.

        **Declared, not inferred.** The coherence test used to recover this by
        reading each ``__init__``'s *source* and regex-matching ``REQ_ITEMS``
        names — which worked, but meant the field set existed only as a
        convention that a test happened to be able to reconstruct. Two
        consumers reconstructing the same convention independently is the
        failure mode this feature removes, so the classes now say it and both
        consumers ask (T007).

        Accumulated because a subclass declares only what it *adds*:
        ``AudioCue`` declares ``master_vol``, and the thirteen common
        properties come from ``Cue``. Reading one class's dict alone reports
        thirteen spurious missing fields.

        **Order is load-bearing**, so it is defined rather than incidental:
        base-class fields first, each class's own in declaration order,
        duplicates keeping their first position. That reproduces the order the
        ten hand-written ``items()`` overrides produced by chaining
        ``super().items()`` — and ``items()`` feeds ``__json__``, so the order
        here is the key order of the editor's JSON payload.

        The returned dict is the cached one. Do not mutate it.
        """
        cached = _DECLARED_DEFAULTS.get(cls)
        if cached is None:
            merged: dict[str, Any] = {}
            for klass in reversed(cls.__mro__):
                own = klass.__dict__.get("DECLARED_DEFAULTS")
                if own:
                    merged.update(own)
            cached = _DECLARED_DEFAULTS[cls] = merged
        return cached

    @classmethod
    def runtime_fields(cls) -> dict[str, Any]:
        """This class's declared runtime attributes, accumulated across the
        MRO exactly as :meth:`declared_defaults` accumulates document fields
        (T010, data-model.md §4). Base-class fields first, each class's own
        additions or overrides layered on top — so ``VideoCue`` can replace
        ``Cue``'s plain ``CTimecode`` factory for ``_start_mtc``/``_end_mtc``
        with a 25fps one, exactly as it does today.

        The returned dict is the cached one. Do not mutate it.
        """
        cached = _RUNTIME_FIELDS.get(cls)
        if cached is None:
            merged: dict[str, Any] = {}
            for klass in reversed(cls.__mro__):
                own = klass.__dict__.get("RUNTIME_FIELDS")
                if own:
                    merged.update(own)
            cached = _RUNTIME_FIELDS[cls] = merged
        return cached

    @classmethod
    def declared_fields(cls) -> tuple[str, ...]:
        """The names of this class's declared fields, in declaration order.

        The single declared-field rule (FR-014, FR-015): ``items()`` filters by
        it, the serialization engine selects by it, and defaulting fills it. A
        field declared with :data:`Unset` still appears here — it is declared,
        it simply has no default to insert.
        """
        return tuple(cls.declared_defaults())

    @classmethod
    def coercion_table(cls) -> dict[str, Any]:
        """The ``{field name: Adapter}`` table for this class (T004b).

        **Declared, not inferred** — the object answers for its own types, the
        same way it answers for its own declared fields. The alternative was a
        resolver called only from ``xml/``, which would keep ``cues/`` free of
        any schema concept; it was rejected because then the *programmatic*
        construction path cannot reach its own adapters, and coercion stops
        being one path — which is the entire feature. Two rules that agree only
        because a test says so is the failure mode 005 exists to remove.

        Takes no schema argument, because every model class is bound in exactly
        one registry today. ``coercion.adapter_table`` raises if that stops
        being true rather than picking a winner; feature 006 is where it stops
        being true.
        """
        from .coercion import adapter_table

        return adapter_table(cls)


    # -- projection (T026) -------------------------------------------------
    #
    # On the **base**, not on ``CuemsScript``, and that placement is the
    # requirement rather than a convenience: "one projection implementation"
    # (SC-017) is a claim about code, so the config models bind to this body in
    # US3 rather than relocating or duplicating it. ``CuemsScript.to_wire()``
    # and a config object's differ only in which ``Mapper`` they resolve.
    #
    # The counted consequence: **every** ``CuemsDict`` subclass — every cue
    # class, not only ``CuemsScript`` — now exposes ``to_wire()``/``to_json()``
    # publicly. Intended and free (a cue projecting itself is meaningful), and
    # recorded in the enumerated API-surface diff rather than discovered when
    # the golden fails.

    def to_wire(self) -> dict:
        """The schema-faithful projection of this object.

        For a document body (``CuemsScript``) the result is wrapped in its own
        element name — ``{"CuemsScript": {...}}`` — matching the shape
        ``cuems-editor`` transmits verbatim to the UI on ``project_load``.
        Everything else projects bare.

        **It does not validate** (FR-005a). A projection is not a validation
        gate; ``save()`` is the gate. Projecting a half-built or semantically
        invalid object yields a **partial payload**, not an exception — a
        caller wanting a guarantee calls ``validate()`` first. The reason is
        measured rather than stylistic: running T1 here would cost roughly the
        15.49 ms the direct projection exists to avoid, against a 5 ms budget
        on the system's hottest path.

        Returns:
            dict: JSON-safe, ordered as the wire contract states.

        Raises:
            Nothing on a malformed or incomplete object — see above. Errors
            from a genuinely broken registry binding propagate unchanged.
        """
        from .coercion import schema_for
        from .xml.mapper import Mapper, encode_wildcard

        schema_name = schema_for(type(self))
        if schema_name is None:
            # An unbound class: a bare ``CuemsDict``, which is what wildcard
            # ``ui_properties`` content decodes to. Nothing about a wildcard's
            # children is derivable, so it projects through the same untyped
            # fallback the mapper applies when it meets one inside a document
            # — rather than through a schema it has none of.
            return encode_wildcard(self)
        return Mapper(schema_name).encode_wire(self)

    def to_json(self) -> str:
        """``to_wire()``, serialized — with the form **pinned**, not defaulted.

        Separators, ``ensure_ascii`` and key ordering each change the bytes,
        and this output is compared for equality across a repository boundary,
        so none of the three is left to a ``json.dumps`` default that a future
        stdlib release could move (FR-005b):

        ``separators=(", ", ": ")``
            what consumers produce today; changing it would alter every
            recorded payload.
        ``ensure_ascii=False``
            emits real UTF-8 rather than ``\\uXXXX`` escapes, so ``Cançó``
            stays ``Cançó``. Both settings round-trip losslessly — this is a
            readability and payload-size choice, on a transport (a WebSocket
            text frame) that is UTF-8 by definition.
        ``sort_keys=False``
            key order comes from ``to_wire()`` and is part of the wire
            contract. Sorting here would reorder the payload the UI receives.

        Defined in terms of ``to_wire()`` so the two cannot diverge, and like
        it, **does not validate**.

        Returns:
            str: UTF-8 JSON text.

        Raises:
            Nothing on a malformed or incomplete object — see ``to_wire()``.
        """
        import json

        return json.dumps(
            self.to_wire(),
            separators=(", ", ": "),
            ensure_ascii=False,
            sort_keys=False,
        )

    def __json__(self):
        """The ``json.dumps`` hook — **derived**, not hand-written (T035).

        Eight classes carried a hand-written body before this feature, each
        assembling the payload its own way, and the two the UI actually
        receives disagreed on every boolean (F21). All eight are gone: seven
        deleted outright and ``CuemsScript``'s reduced to unwrapping the
        document body, which projects nothing itself.

        Nothing below the top level consults this hook any more, and that is
        the point: ``to_wire()`` returns plain dicts, lists and scalars all the
        way down, so there is exactly one traversal of the object graph and
        exactly one place that decides what a value looks like on the wire.

        ``JSON_SELF_WRAPS`` still decides whether an object *dumped on its own*
        names itself — ``{"AudioCue": {...}}`` — because that wrapper is how
        the editor knows which cue type it is holding.
        """
        wire = self.to_wire()
        return {type(self).__name__: wire} if self.JSON_SELF_WRAPS else wire

    # -- identity (T029) ---------------------------------------------------

    def __eq__(self, other) -> bool:
        """Equality over **declared fields only** (FR-028b).

        Two scripts that differ only in accumulated playback state are equal,
        which is what makes ``load(save(x)) == load(x)`` hold. It **widens**
        ``Cue.__eq__``, which compared by ``id`` alone — enumerated behaviour
        change 5: two cues sharing an id and differing in every other field
        used to compare equal.

        A class with **no** declared field set falls through to ``dict``
        equality unchanged. That is not a loophole: wildcard containers and
        plain dicts have no declared fields, and comparing them by an empty set
        would make every one of them equal to every other.
        """
        if not type(self).declared_fields():
            return dict.__eq__(self, other)
        if type(other) is not type(self):
            return False
        return dict(self.items()) == dict(other.items())

    def __ne__(self, other) -> bool:
        result = self.__eq__(other)
        return result if result is NotImplemented else not result

    #: ``dict`` is unhashable and so is a bare ``CuemsDict``; ``Cue`` restates
    #: ``__hash__`` as ``hash(self.id)`` and **must keep doing so**. Defining
    #: ``__eq__`` without restating ``__hash__`` sets it to ``None``, which is
    #: invisible in review, produces no failure in any test that does not
    #: itself hash a cue, and surfaces as a ``TypeError`` in a consumer
    #: repository (FR-028d).
    __hash__ = None  # type: ignore[assignment]

    def __copy__(self):
        """A shallow copy with **fresh** runtime state (FR-028c).

        A copied cue that shares its parent's ``_go_thread`` is a cue that
        stops the wrong playback. Declared fields are shared, as a shallow copy
        means; runtime state never is.
        """
        clone = type(self).__new__(type(self))
        dict.__init__(clone)
        clone._init_runtime()
        for key, value in dict.items(self):
            dict.__setitem__(clone, key, value)
        return clone

    def __deepcopy__(self, memo):
        """A deep copy with fresh runtime state — the same rule, deeper."""
        from copy import deepcopy

        clone = type(self).__new__(type(self))
        memo[id(self)] = clone
        dict.__init__(clone)
        clone._init_runtime()
        for key, value in dict.items(self):
            dict.__setitem__(clone, key, deepcopy(value, memo))
        return clone

    def setter(self, settings: dict):
        """Set the object properties from a dictionary.
        
        Args:
            settings (dict): Dictionary containing property values to set.
            
        Raises:
            AttributeError: If settings is not a dictionary.
        """
        if not isinstance(settings, dict):
            raise AttributeError(f"Invalid type {type(settings)}. Expected dict.")
        for k, v in settings.items():
            # Resolve first, call **outside** the guard (F17, change 4).
            #
            # The lookup and the call used to share one
            # ``except AttributeError: pass``, which cannot tell "this class has
            # no setter for that key" — routine, and correctly skipped — from
            # "the setter ran and broke". The second swallowed the error *and*
            # dropped the field, so a defect in any setter that touched a
            # missing attribute produced a silently absent value rather than a
            # failure. Objects still constructed, which is why it could hide
            # indefinitely.
            #
            # Only ``AttributeError`` changes meaning here. Every other
            # exception type already propagated, because the guard never caught
            # them.
            try:
                setter = getattr(self, f"set_{k}")
            except AttributeError:
                continue
            setter(v)

def as_cuemsdict(x: dict) -> CuemsDict | None:
    if not x:
        return None
    out = CuemsDict({})
    for k,v in x.items():
        if isinstance(v, dict):
            out.update({k: as_cuemsdict(v)})
        else:
            out.update({k: v})
    return out

def build_xml_dict(x, parent: Element) -> None:
    """Build an xml element from a dictionary"""
    if not isinstance(x, dict):
        raise AttributeError(f"Invalid type {type(x)}. Expected dict.")
    if not isinstance(parent, Element):
        raise AttributeError(f"Invalid type {type(parent)}. Expected ElementTree.")
    for k, v in x.items():
        if isinstance(v, list):
            for item in v:
                if hasattr(item, 'build'):
                    item.build(parent)
                else:
                    SubElement(parent, k).text = str(item)
        elif hasattr(v, 'build'):
            s = SubElement(parent, k)
            v.build(s)
        else:
            SubElement(parent, k).text = str(v)

def check_path(x: str, dir_only: bool = False) -> bool:
    """Check if a path is valid. Raise an error if not."""
    x = path.realpath(x)
    if dir_only:
        dir_ok = _check_dir(path.dirname(x))
        return dir_ok
    if not path.exists(x):
        raise FileNotFoundError(f"Path {x} does not exist")
    if not _readable(x) or not _writable(x):
        raise PermissionError(f"Path {x} is not readable or writable")
    return True

def ensure_items(x: dict, requiered: dict) -> dict:
    """Ensure that all the items are present in a dictionary

    Args:
        x (dict): The dictionary to check
        requiered (dict): The items (key-value pairs) to check for

    Works on a **copy**. Every cue ``__init__`` follows the pattern
    ``if not init_dict: init_dict = REQ_ITEMS`` and then hands that straight
    here, so mutating the argument wrote the parent class's fields into the
    subclass's module-level ``REQ_ITEMS`` — permanently, process-wide, from a
    single bare ``AudioCue()``. Callers have always used the return value, so
    copying changes nothing for them.
    """
    x = dict(x)
    for k,v in requiered.items():
        if k not in x.keys():
            if v == None:
                x[k] = None
            elif callable(v):
                x[k] = v()
            else:
                x[k] = v

    ## Order the dictionary
    x = {k: x[k] for k in sorted(x.keys())}
    
    return x

def extract_items(x, keys: list[str] | KeysView[str]) -> ItemsView[str, Any]:
    """Extract list of keys and values from a dictionary
    
    Args:
        x (items): The dictionary items to extract from
        keys (list): The keys to extract
    """
    d = dict(x)
    return {k: d[k] for k in keys}.items()

def format_timecode(value):
        if not value or value == '':
            return CTimecode()
        elif isinstance(value, CTimecode):
            return value
        elif isinstance(value, (int, float)):
            return CTimecode(start_seconds=value)
        elif isinstance(value, str):
            return CTimecode(value)
        elif isinstance(value, dict):
            dict_timecode = value.pop('CTimecode', None)
            if dict_timecode is None:
                return CTimecode()
            elif isinstance(dict_timecode, int):
                return CTimecode(start_seconds = dict_timecode)
            else:
                return CTimecode(dict_timecode)
        else:
            raise ValueError(f'Invalid timecode value type {type(value)}')

def mkdir_recursive(folder: str) -> None:
    """
    Creates a directory recursively.

    Args:
        folder (str): The folder to be created.
    """
    if path.exists(folder):
        return
    if not path.exists(path.dirname(folder)):
        mkdir_recursive(path.dirname(folder))
    mkdir(folder)

def new_datetime():
    """Generate a new datetime string."""
    return datetime.now().strftime(DATETIME_FORMAT)

def new_uuid():
    """Generate a new Uuid class instance."""
    return Uuid()

def strtobool(val: str) -> bool:
    """Convert a string value representation of truth to true (1) or false (0).

        True values are y, yes, t, true, on and 1.
        False values are n, no, f, false, off and 0.
        Raises ValueError if val is anything else.
    """ 
    if val.lower() in ['y', 'yes', 't', 'true', 'on', '1']:
        return True
    elif val.lower() in ['n', 'no', 'f', 'false', 'off', '0']:
        return False
    else:
        raise ValueError(f'Invalid truth value {val}')

def unique_values_to_list(x: dict) -> list:
    """Convert a dictionary to a sorted list of its unique values.
    
    Args:
        x (dict): The dictionary to convert
    """
    return sorted(list(set(x.values())))

def _check_dir(x: str) -> bool:
    """Check if a path is a directory. Raise an error if not."""
    if not path.isdir(x):
        raise NotADirectoryError(f"Directory {x} does not exist")
    if not _readable(x):
        raise PermissionError(f"Directory {x} is not readable")
    if not _writable(x):
        raise PermissionError(f"Directory {x} is not writable")
    return True

def _readable(path: str) -> bool:
    """Check if a path is readable."""
    return access(path, R_OK)

def _writable(path: str) -> bool:
    """Check if a path is writable."""
    return access(path, W_OK) 
