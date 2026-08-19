"""The one encode/decode engine (T045, T046).

Everything that used to be decided four times — once in ``XmlBuilder``, once in
``Parsers``, once in the hand-written ``__json__`` methods, once in the config
readers — is decided here, from the ``TypeSpec`` the schema produced.

Three things this engine does **not** do, each deliberately:

* **Decide order.** That is ``TypeSpec.order_keys`` and nowhere else (FR-001a).
* **Guess a type.** Types are declared; adapters convert them (FR-003).
* **Look a handler up by name.** The registry binds explicitly, and reports a
  missing binding instead of silently returning a generic (FR-007).
"""

from __future__ import annotations

from enum import Enum
from xml.etree.ElementTree import (
    Element,
    ElementTree,
    SubElement,
    register_namespace,
)

from ..helpers import as_cuemsdict
from ..log import Logger
from ..tools.Uuid import Uuid
from .adapters import PASSTHROUGH, adapter_for
from .registry import get_registry
from .spec import FieldKind, TypeSpec, derive, derive_path

#: Values written straight to element text rather than recursed into.
#:
#: ``Uuid`` belongs here despite being an object: it is a scalar in the schema
#: (``UuidType`` is an ``xs:string`` with a pattern) and the legacy builder
#: listed it in ``VALUE_TYPES`` for the same reason.
SCALARS = (str, bool, int, float, Enum, Uuid)


class Mapper:
    """Encodes model objects to XML, driven by the derived specification."""

    def __init__(self, schema_name: str):
        self.schema_name = schema_name
        self.registry = get_registry(schema_name)

    # -- decode ------------------------------------------------------------

    def decode_document(self, source: dict):
        """Decode a read dict into model objects.

        The replacement for ``CuemsParser``'s tree of ``*Parser`` classes. Two
        things change and one does not:

        * scalars are converted by **adapters bound to the declared type**,
          not by ``str_to_value``'s guess-from-text (FR-003);
        * model classes come from the **registry**, not from ``globals()``
          name-mangling that misses silently (FR-007);
        * the object shapes are unchanged, including the ones that look
          accidental — see ``_decode_field``.
        """
        if not isinstance(source, dict) or not source:
            return source

        body_tag = next(iter(source))
        spec = _body_spec(self.schema_name, body_tag)
        return self.decode(source[body_tag], spec)

    def decode(self, value, spec: TypeSpec | None):
        """Decode one value against its type specification."""
        if value is None or spec is None:
            return value
        if not isinstance(value, dict):
            return value

        decoded = {}
        for key, raw in value.items():
            decoded[key] = self._decode_field(key, raw, spec)

        model = self._model_for_spec(spec)
        if model is None:
            return decoded
        return _instantiate(model, decoded)

    #: Types decoded **into the object model without recursing into them**:
    #: the bound class is constructed from the raw decoded dict, and whatever
    #: it contains stays as ``xmlschema`` produced it.
    #:
    #: This reproduces ``outputsParser``, which did ``self._class(dict_value)``
    #: on the whole output dict. The visible consequence is that ``channels``
    #: inside an ``AudioCueOutput`` keeps its ``{'channel': {...}}`` wrappers —
    #: decoding through them flattens the wrapper and the re-encoded document
    #: fails validation with ``Unexpected child with tag 'channel_num'``.
    OPAQUE_TYPES = frozenset(
        {
            "AudioCueOutputsType",
            "VideoCueOutputsType",
            "DmxCueOutputsType",
            # ``DmxCueParser`` did ``self._class(self.init_dict)`` on the whole
            # cue, so a DMX cue and its scene are built in one step and never
            # recursed into either.
            "DmxCueType",
        }
    )

    #: Types left **entirely undecoded**, as the raw list or dict.
    #:
    #: ``AudioChannelsType`` is the only member, and it is a real decision:
    #: ``channels`` inside an ``AudioCueOutput`` must keep its
    #: ``{'channel': {...}}`` wrappers, because decoding through them flattens
    #: the wrapper and the re-encoded document fails validation with
    #: ``Unexpected child with tag 'channel_num'``.
    #:
    #: ``RegionsType`` **was** here, and was not a decision: ``regions`` reached
    #: ``GenericParser`` with ``class_string='regions'``, whose lookup missed
    #: (the class is ``Region``, the tag is ``regions``) and fell back to a
    #: generic that returns its input untouched, so every region stayed a raw
    #: ``{'Region': {...}}`` wrapper with its timecodes as
    #: ``{'CTimecode': '...'}`` dicts. Feature 004 preserved that shape verbatim
    #: and recorded it as F19; feature 005 removes it (change 2). Regions now
    #: decode through ``RegionType``'s binding, which has existed and been
    #: unreachable all along.
    RAW_TYPES = frozenset({"AudioChannelsType"})

    def _decode_field(self, key: str, raw, spec: TypeSpec):
        field = spec.field(key)

        if field is None:
            # Undescribed: wildcard content, or the leaked schemaLocation.
            # Passed through untouched (FR-009).
            return raw

        # Adapters are consulted **before** complexity is considered, because
        # they bind complex types too (research R5). ``CTimecodeType`` is the
        # case: it is a complex type wrapping a ``<CTimecode>`` child, so
        # treating "has a child type" as "recurse into it" leaves every
        # timecode as a bare ``{'CTimecode': '...'}`` dict instead of a
        # ``CTimecode`` object.
        adapter = adapter_for(field.xsd_type)
        if adapter is not PASSTHROUGH:
            return adapter.decode(raw)

        if field.child is None:
            return raw

        if field.child.name in self.RAW_TYPES:
            return raw

        child_spec = derive(field.child)

        if isinstance(raw, list):
            return self._decode_repeated(raw, child_spec)

        if child_spec.wildcard:
            # Wildcard content — ``ui_properties`` is the only one. Its
            # *content* stays exactly as decoded (nothing about a wildcard's
            # children is derivable), but the container becomes the same
            # wrapper type the programmatic path produces (FR-008, T028).
            #
            # Routed through ``helpers.as_cuemsdict``, which is the recursive
            # wrapper ``Cue.set_ui_properties`` and
            # ``CuemsScript.set_ui_properties`` already use. Built and decoded
            # therefore agree **by construction** at every nesting depth,
            # rather than by two implementations that happen to match.
            return as_cuemsdict(raw) if isinstance(raw, dict) else raw

        if self._is_wrapper(child_spec):
            return self._decode_wrapper(raw, child_spec)

        return self.decode(raw, child_spec)

    def _decode_repeated(self, items: list, child_spec: TypeSpec):
        """A repeated block: ``[{Tag: {...}}, ...]`` in document order.

        Each wrapper key names the element, which is how an ``xs:choice`` of
        six cue types resolves to the right model class without a name-mangled
        lookup.
        """
        out = []
        for item in items:
            if not isinstance(item, dict) or len(item) != 1:
                out.append(item)
                continue
            tag, body = next(iter(item.items()))
            member = child_spec.field(tag)
            if member is None or member.child is None:
                out.append(item)
                continue
            out.append(self._decode_member(body, member))
        return out

    def _decode_member(self, body, member):
        """Decode one member of a repeated block, honouring ``OPAQUE_TYPES``."""
        if member.child.name in self.OPAQUE_TYPES:
            model = self._model_for_spec(derive(member.child))
            return model(body) if model is not None else body
        return self.decode(body, derive(member.child))

    @staticmethod
    def _is_wrapper(child_spec: TypeSpec) -> bool:
        """A type whose only job is to hold repeated children.

        ``RegionsType`` holds ``Region``, ``FadeProfilesWrapperType`` holds
        ``fade_profile``, ``OutputsType`` holds the three output types. The
        wrapper element exists in the XML but not in the object model, where
        the field holds the list directly.
        """
        elements = [f for f in child_spec.fields if f.kind is FieldKind.ELEMENT]
        return bool(elements) and all(f.repeated for f in elements)

    def _decode_wrapper(self, raw, child_spec: TypeSpec):
        if not isinstance(raw, dict):
            return raw
        out = []
        for tag, body in raw.items():
            member = child_spec.field(tag)
            if member is None or member.child is None:
                out.append({tag: body})
                continue
            items = body if isinstance(body, list) else [body]
            for item in items:
                out.append(self._decode_member(item, member))
        return out

    def _model_for_spec(self, spec: TypeSpec):
        binding = (
            self.registry.binding_for_path(spec.key.name)
            if spec.key.is_path
            else self.registry.binding_for(spec.key.name)
        )
        if binding is None or binding.is_generic:
            return None
        return binding.model

    # -- encode: wire ---------------------------------------------------

    def encode_wire(self, obj, spec: TypeSpec | None = None) -> dict:
        """Encode ``obj`` to a wire dict — a **direct** object walk (T008).

        The signature is pinned in data-model.md §6: the schema is bound at
        construction, and ``spec`` is an optional recursion parameter naming
        the type to project *within* that schema. Every call site in this
        feature omits it, so it is resolved from ``obj``'s class through the
        registry.

        Mirrors ``decode``/``_decode_field``, reusing the **same** ``Adapter``
        instances via ``Adapter.to_wire`` (rather than ``.decode``) so encode
        and decode cannot disagree by construction. The result matches
        ``schema.to_dict(build_document(obj))`` (the round-trip oracle, T004)
        without paying for the tree build or the re-decode.

        **The document body wraps; everything else is bare.** When ``spec``
        is omitted and ``obj``'s class is bound as the schema's document body
        (an anonymous root child, bound by *path* one level below the
        registry root — ``CuemsScript`` is script.xsd's), the result is
        ``{ClassName: {...fields}}``, matching ``read()``'s shape exactly
        (W1). A recursive call always passes an explicit ``spec`` and is
        never wrapped, matching ``decode``'s own field-level shape.
        """
        if spec is None:
            body_tag = self._body_tag_for(obj)
            spec = self._spec_for_model(type(obj))
            if spec is None:
                return obj
            value = self._encode_wire_value(obj, spec)
            return {body_tag: value} if body_tag is not None else value
        return self._encode_wire_value(obj, spec)

    def _body_tag_for(self, obj) -> str | None:
        """``obj``'s class name, if it is bound as this schema's document body.

        The document body is bound by *path*, one level below the registry
        root (``CuemsProject/CuemsScript`` for script.xsd) — the encode-side
        counterpart of ``_body_spec``'s ``body_tag`` extraction on decode.
        Every other binding (by qname, or nested deeper) is not a document
        body and stays bare.
        """
        class_name = type(obj).__name__
        binding = self.registry.binding_for_path(f"{self.registry.root}/{class_name}")
        if binding is not None and binding.model is type(obj):
            return class_name
        return None

    def _encode_wire_value(self, obj, spec: TypeSpec) -> dict:
        """The dict for one value against its type spec — mirrors ``decode``.

        A key whose field is **optional and empty** is left out entirely
        (matching the XML path's ``_omit`` and, empirically, what the
        converter's own dict never carries for an absent element) rather
        than emitted as ``null`` — reusing the same ``_omit`` the XML writer
        uses, so the two paths cannot disagree on which fields vanish.
        """
        keys = self._selected_keys(obj)
        ordered = spec.order_keys(keys)
        result = {}
        for key in ordered:
            value = obj[key]
            field = spec.field(key)
            if self._omit(field, value):
                continue
            result[key] = self._encode_wire_field(key, value, spec)
        return result

    def _encode_wire_field(self, key: str, value, spec: TypeSpec):
        """Mirrors ``_decode_field``, in the encode direction."""
        field = spec.field(key)

        if field is None:
            # Undescribed: wildcard content, or a leaked attribute. Passed
            # through untouched, matching decode's own passthrough (FR-009).
            return value

        adapter = adapter_for(field.xsd_type)
        if adapter is not PASSTHROUGH:
            return adapter.to_wire(value)

        if field.child is None:
            return value

        if value is None:
            # A required-but-empty complex field — ``<description />``,
            # ``<outputs />``. Every adapter already returns ``None`` for
            # ``None``; this is the passthrough types' equivalent, and it
            # must come before RAW_TYPES/list/wildcard, none of which is
            # meaningful on ``None``.
            return None

        if field.child.name in self.RAW_TYPES:
            # Never decoded into objects (T045/decode docstring); still raw.
            return value

        child_spec = derive(field.child)

        if isinstance(value, list):
            return self._encode_wire_repeated(value, child_spec)

        if child_spec.wildcard:
            return self._encode_wildcard_value(value)

        return self.encode_wire(value, child_spec)

    def _encode_wire_repeated(self, items: list, child_spec: TypeSpec) -> list:
        """A repeated block: object list -> ``[{Tag: {...}}, ...]`` (T009).

        The **only** repeated-content shape on the wire (verified against
        every corpus document's goldens): same-tag repetition (``Region``,
        ``fade_profile``, ``VideoCueOutput``) and mixed-tag choice (cue list
        contents) both decode — and therefore both re-encode — to a flat list
        of single-key ``{Tag: body}`` dicts. There is no second, wrapper-dict
        shape to reproduce on this side: decode's ``_decode_wrapper`` exists
        for a raw shape this converter's output never actually takes for the
        types it names, which is why encode has no corresponding branch.
        """
        out = []
        for item in items:
            if isinstance(item, SCALARS) or not hasattr(item, "keys"):
                out.append(item)
                continue
            tag = self._tag_for_item(item, child_spec)
            member = child_spec.field(tag)
            item_spec = (
                derive(member.child)
                if member is not None and member.child
                else self._spec_for_model(type(item))
            )
            body = (
                self._encode_wire_value(item, item_spec)
                if item_spec is not None
                else dict(item.items())
            )
            out.append({tag: body})
        return out

    def _encode_wildcard_value(self, value):
        """Wildcard (``ui_properties``) content — scalars become **strings**.

        The mirror of ``as_cuemsdict`` (decode's wildcard fallback, FR-009):
        nothing about a wildcard's children is derivable, so nothing here is
        typed either. A value built programmatically as a real Python type
        (``0``, ``None``) is stringified to match what decode would have
        produced from the equivalent XML text node.
        """
        if isinstance(value, dict):
            return {k: self._encode_wildcard_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._encode_wildcard_value(v) for v in value]
        return str(value)

    # -- encode: xml ------------------------------------------------------

    def encode_xml(self, obj, spec: TypeSpec | None, parent: Element, tag: str) -> Element:
        """Emit ``obj`` as ``<tag>`` under ``parent``.

        ``spec`` may be ``None`` for content the schema does not describe —
        wildcard subtrees — in which case the documented fallback applies
        (FR-009): preserve insertion order, pass scalars through untyped.
        """
        element = SubElement(parent, tag)
        self._fill(element, obj, spec)
        return element

    def _fill(self, element: Element, obj, spec: TypeSpec | None) -> None:
        if obj is None:
            return
        if isinstance(obj, SCALARS):
            element.text = self._lexical(obj, None)
            return
        if isinstance(obj, (list, tuple)):
            for item in obj:
                self._fill_list_item(element, item, spec)
            return
        if not hasattr(obj, "keys"):
            # A value object that is neither scalar nor mapping — ``CTimecode``
            # is the only one. It emits as a child named for its class
            # (``<CTimecode>00:00:00.000</CTimecode>``), which is the wrapper
            # ``CTimecodeType`` declares as a complex type (research R5), not a
            # quirk of the old builder.
            SubElement(element, type(obj).__name__).text = str(obj)
            return

        keys = self._selected_keys(obj)
        ordered = spec.order_keys(keys) if spec is not None else keys

        for key in ordered:
            if key == "DmxScene":
                self._emit_dmx_scene(element, key, obj, spec)
                continue
            self._emit_field(element, key, obj[key], spec)

    def _emit_dmx_scene(self, element: Element, key: str, cue, spec) -> None:
        """Emit a DMX scene, failing **loudly** if it cannot be written (FR-023).

        Feature 004 preserved a swallow-and-continue path here: a scene that
        failed to serialize produced no elements and no error, so the show saved
        cleanly with the scene missing from it. That compatibility object
        carried ``REMOVAL_TARGET = "005"``, and this is its removal (change 7).

        The engine already propagated the underlying exception — what it did not
        do was say *which* scene. A ``RuntimeError`` surfacing from somewhere
        inside a 24 KB document is not actionable, so the scene is identified by
        its ``id``, or by its zero-based index in the cue's scene contents when
        it has none, and the originating cue is named.

        Scoped to DMX scenes deliberately. An ambient ``except Exception`` in
        the general emit path would catch unrelated failures and make every
        other error class disappear too — which is the defect being removed,
        widened rather than fixed.
        """
        value = cue[key]
        scenes = value if isinstance(value, (list, tuple)) else [value]
        for index, scene in enumerate(scenes):
            try:
                self._emit_field(element, key, scene, spec)
            except Exception as exc:
                raise DmxSceneWriteError(scene, index, cue) from exc

    def _selected_keys(self, obj) -> list:
        """Which of ``obj``'s keys are emitted — **the model's rule** (FR-015).

        The engine asks the object rather than deriving the answer from
        ``spec.fields``. Two rules that agree only because a coherence test says
        so is the failure mode this feature exists to remove; asking means they
        cannot disagree in the first place.

        Three cases, and the last two are why this is not simply a filter:

        * a **model object** with declared fields — filtered to them, with every
          other key dropped and logged (FR-015a);
        * a **model object with no declared field set** — ``Media``, ``Region``
          and the three ``CueOutput`` subclasses, until T026/T027 give them one
          — passes everything through, exactly as today;
        * anything **without** ``declared_fields`` at all, or a bare
          ``CuemsDict`` whose set is empty: plain dicts, lists, and wildcard
          ``ui_properties`` subtrees. These pass through untouched. Filtering a
          wildcard subtree by a declared-field rule would delete real editor
          state for every cue in every project — it is declared *nowhere*, which
          is the whole point of a wildcard.
        """
        declared = getattr(obj, "declared_fields", None)
        if declared is None:
            return list(obj.keys())

        fields = declared()
        if not fields:
            return list(obj.keys())

        known = fields if len(fields) < 8 else set(fields)
        selected = []
        for key in obj.keys():
            if key in known:
                selected.append(key)
            else:
                # One record per dropped key per object, at DEBUG, naming the
                # class and the key and **never the value** (FR-015a). Silent
                # loss is how data disappears without a trace; an error would
                # break objects that construct fine today.
                Logger.debug(
                    f"{type(obj).__name__}: dropping undeclared key {key!r}"
                )
        return selected

    #: List items whose class name is one of these carry **no wrapper element**:
    #: their keys become children of the enclosing element directly. A parsed
    #: ``regions`` is ``[{'Region': {...}}]``, and the wrapper name would be
    #: ``dict`` — ``<regions><dict><Region>`` instead of ``<regions><Region>``.
    #: The legacy builder special-cased the same two names for the same reason.
    TRANSPARENT_LIST_ITEMS = ("dict", "CuemsDict")

    def _fill_list_item(self, element: Element, item, spec: TypeSpec | None) -> None:
        if isinstance(item, SCALARS):
            SubElement(element, type(item).__name__).text = self._lexical(item, None)
            return

        if type(item).__name__ in self.TRANSPARENT_LIST_ITEMS:
            self._fill(element, item, spec)
            return

        tag = self._tag_for_item(item, spec)
        field = spec.field(tag) if spec is not None else None
        child_spec = (
            derive(field.child)
            if field is not None and field.child
            else self._spec_for_model(type(item))
        )
        self.encode_xml(item, child_spec, element, tag)

    @staticmethod
    def _tag_for_item(item, spec: TypeSpec | None) -> str:
        """The element name for a list member — **from the schema**.

        The Python class name is only a fallback, and using it unconditionally
        is wrong: ``FadeProfile`` objects live in elements the schema calls
        ``fade_profile``, and ``FadeFunctionParameter`` objects in ones it calls
        ``parameter``. The legacy builder got this right by hardcoding both
        names in ``FadeProfileXmlBuilder``; here the names come from the
        content model, so a third such type needs no new code.

        Two cases, in order:

        * the class name **is** one of the declared children — cue types in a
          cue list, output types in ``outputs`` — so use it, which is what
          picks the right branch of an ``xs:choice``;
        * the content model declares exactly **one** child element, so there is
          nothing to choose and the declared name wins over the class name.
        """
        class_name = type(item).__name__
        if spec is None:
            return class_name

        candidates = [f.name for f in spec.fields if f.kind is FieldKind.ELEMENT]
        if class_name in candidates:
            return class_name
        if len(candidates) == 1:
            return candidates[0]
        return class_name

    def _emit_field(self, element: Element, key: str, value, spec: TypeSpec | None) -> None:
        field = spec.field(key) if spec is not None else None

        if field is not None and field.kind is FieldKind.ATTRIBUTE:
            if value is not None:
                element.set(key, self._lexical(value, field.xsd_type))
            return

        if self._omit(field, value):
            # Optional and unset: absent, not empty. The legacy builder reached
            # the same result for ``fade_profiles`` with two hardcoded branches
            # — ``if key == 'fade_profiles': continue`` and a later ``if fps:``
            # — which is the same rule expressed for one field at a time. Here
            # it comes from ``minOccurs="0"``, so it holds for every optional
            # element in every schema without anyone naming them.
            return

        if value is None:
            if field is None:
                # Undescribed content — a wildcard subtree (R6), where the
                # schema states nothing about the child at all. The documented
                # fallback is to pass values through untyped (FR-009), and
                # untyped means ``str(None)``: ``<warning>None</warning>``.
                #
                # It reads like a bug, and it is one. It is also what
                # ``ui_properties`` contains in every document written to date,
                # so changing it here would rewrite editor state for every cue
                # in every project. Deferred with the rest of the wildcard
                # handling.
                SubElement(element, str(key)).text = str(value)
                return
            # Described and required but unset: an empty element,
            # ``<description />``.
            SubElement(element, str(key))
            return

        if isinstance(value, SCALARS):
            SubElement(element, str(key)).text = self._lexical(
                value, field.xsd_type if field else None
            )
            return

        child = SubElement(element, str(key))
        child_spec = derive(field.child) if field is not None and field.child else None

        if isinstance(value, (list, tuple)):
            for item in value:
                self._fill_list_item(child, item, child_spec)
            return

        self._fill(child, value, child_spec)

    @staticmethod
    def _omit(field, value) -> bool:
        """Whether an optional field with no value is left out entirely.

        Emptiness rather than ``is None``, because an unset repeated field
        arrives as ``[]``: ``fade_profiles`` on a cue that has none decodes to
        an empty list, and ``<fade_profiles />`` is not what the corpus
        contains. Fields the schema declares required are never omitted, even
        when empty — that is the difference between "absent" and "present and
        empty", and both appear in real documents.
        """
        if field is None or field.required:
            return False
        return value is None or value == [] or value == {}

    def _lexical(self, value, xsd_type: str | None) -> str:
        text = adapter_for(xsd_type).to_lexical(value)
        return "" if text is None else text

    def _spec_for_model(self, model: type) -> TypeSpec | None:
        """The spec bound to a Python class, if the registry knows one.

        Delegates to the registry (T004a), which caches the model→spec map. This
        was an O(bindings) scan re-run for **every list item** on the encode
        path; the registry answers it once. ``coercion.adapter_table`` asks the
        same question, and one resolver is the point — two would be a second
        source of truth for which spec describes a class.
        """
        return self.registry.spec_for_model(model)


def _instantiate(model: type, decoded: dict):
    """Build a decoded model object — now the model's own decode mode (T025).

    This used to construct an empty object and assign raw values with
    ``dict.__setitem__``, reproducing what the legacy parsers did. Feature 005
    replaces the *body* while keeping both properties that depended on it:

    **Key order** is still the source document's. ``from_decoded`` preserves
    arrival order and appends only omitted declared fields, because
    ``CuemsScript`` is an ``xs:all`` type whose emission order **is** arrival
    order. ``==`` cannot see the difference — dicts compare equal regardless of
    order — so the byte-identity goldens and contract C3 are what prove it.

    **Property setters still do not run.** The difference is that values are no
    longer left raw: they pass through the class's schema-derived adapter table,
    which coerces without validating. That distinction is the feature. The nil
    uuid ``00000000-0000-0000-0000-000000000000`` — three occurrences in
    ``tests/data/sample_script.json``, so real editor payloads carry it — stays
    accepted, because ``_UuidAdapter`` keeps an unparseable value as its raw
    string while ``Uuid.__init__`` would raise.

    Kept as a module-level function rather than inlined: it is the seam the
    repeated-member path deliberately does *not* use (see ``_decode_member``),
    and naming it keeps that asymmetry visible.
    """
    if hasattr(model, "from_decoded"):
        return model.from_decoded(decoded)

    # A bound class that is not a ``CuemsDict``. None exist today; falling back
    # rather than raising keeps a registry binding from becoming a crash.
    obj = model()
    for key, value in decoded.items():
        dict.__setitem__(obj, key, value)
    return obj


class DmxSceneWriteError(RuntimeError):
    """A DMX scene could not be serialized, and the write fails (FR-023).

    Replaces feature 004's ``DmxSceneCompatibility`` — a named swallow-and-log
    that reproduced ``DmxSceneXmlBuilder``'s ``except Exception`` so a show with
    a bad DMX scene kept saving, minus the scene. It carried
    ``REMOVAL_TARGET = "005"``; this is that removal (change 7).

    The consumer-visible consequence: a write that used to succeed and quietly
    drop a scene now raises. No valid document is affected.

    Carries **identifiers only, never the object repr** (FR-033): show content
    does not belong in an error string any more than in a log record.
    """

    def __init__(self, scene, index: int, cue):
        self.scene = scene
        self.index = index
        self.cue = cue

        scene_id = None
        if hasattr(scene, "get"):
            try:
                scene_id = scene.get("id")
            except Exception:  # noqa: BLE001 - a broken scene must still name itself
                scene_id = None
        where = f"id={scene_id!r}" if scene_id is not None else f"index {index}"

        cue_id = cue.get("id") if hasattr(cue, "get") else None
        cue_name = f"{type(cue).__name__}"
        if cue_id is not None:
            cue_name += f" id={cue_id!r}"

        super().__init__(
            f"DmxScene ({where}) in {cue_name} could not be serialized. The "
            f"write was aborted rather than producing a document with the "
            f"scene silently absent."
        )


def root_spec(schema_name: str) -> TypeSpec:
    return derive_path(schema_name, get_registry(schema_name).root)


SCHEMA_INSTANCE_URI = "http://www.w3.org/2001/XMLSchema-instance"

#: Reader configuration **B** (FR-013), used by the four configuration classes.
#: Kept here, next to the engine, so that "the two configurations" is a pair of
#: named things rather than a set of keyword arguments repeated at call sites.
CONFIG_READER_OPTIONS = {
    "validation": "strict",
    "dict_class": dict,
    "list_class": list,
    "strip_namespaces": True,
    "attr_prefix": "",
}


def read_config_document(schema_object, xmlfile):
    """Decode a configuration document under reader configuration B.

    Returns a raw dict: configuration documents have no model classes, so
    every type in the five configuration schemas is bound to ``GENERIC``
    (registry.py). That is a recorded decision rather than an omission —
    feature 006 introduces the objects.
    """
    Logger.info(f"Reading configuration document {xmlfile}")  # file access (FR-033)
    return schema_object.to_dict(xmlfile, **CONFIG_READER_OPTIONS)


def build_document(
    project_object,
    *,
    schema_name: str,
    namespace: dict,
    xsd_path: str,
    xml_root_tag: str,
) -> ElementTree:
    """Build a complete document tree from a model object.

    The write path's single entry point, replacing ``XmlBuilder.build``. The
    root element, its namespace registration and the ``xsi:schemaLocation``
    attribute are reproduced exactly — including the fact that ``xsd_path`` is
    the writing machine's **absolute** path, which is a defect (F24) whose fix
    is deferred to feature 006 because changing it changes every document's
    root.
    """
    namespace_uri = next(iter(namespace.values()))
    register_namespace(next(iter(namespace)), namespace_uri)

    root = Element(f"{{{namespace_uri}}}{xml_root_tag}")
    root.attrib = {
        f"{{{SCHEMA_INSTANCE_URI}}}schemaLocation": f"{namespace_uri} {xsd_path}"
    }

    mapper = Mapper(schema_name)
    body_tag = type(project_object).__name__
    spec = _body_spec(schema_name, body_tag)
    mapper.encode_xml(project_object, spec, root, body_tag)

    # Element construction and per-cue work stay below INFO (FR-033): this is
    # one record per document built, not one per cue.
    Logger.debug(f"Built {schema_name} document root <{xml_root_tag}>")
    return ElementTree(root)


def _body_spec(schema_name: str, body_tag: str) -> TypeSpec | None:
    """The spec for a document body named ``body_tag``.

    Two resolutions, in order.

    **By element path under the root**, because the root types are anonymous —
    there is no ``CuemsScriptType`` to look up (research R3).

    **By model class name**, for a body that is not a whole document. Callers
    hand ``CuemsParser`` a bare cue — ``{"AudioCue": {...}}`` — and expect an
    ``AudioCue`` back; the legacy ``get_class(class_string)`` served that by
    finding the class in module globals. Here the same lookup runs against the
    registry, so it reports nothing rather than silently returning a generic.
    """
    registry = get_registry(schema_name)
    try:
        return derive_path(schema_name, f"{registry.root}/{body_tag}")
    except (KeyError, StopIteration):
        pass

    for type_name in registry.bound_type_names:
        model = registry.model_for(type_name)
        if model is not None and model.__name__ == body_tag:
            return derive(registry.binding_for(type_name).key)
    return None
