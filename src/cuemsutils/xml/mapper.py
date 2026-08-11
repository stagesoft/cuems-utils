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
    #: ``regions`` reaches ``GenericParser`` with ``class_string='regions'``,
    #: whose ``get_class`` lookup misses (the class is ``Region``, the tag is
    #: ``regions``) and falls back to ``GenericDict``, which returns its input
    #: untouched. So every region stays a raw ``{'Region': {...}}`` wrapper
    #: inside ``Media``.
    #:
    #: That is a name-mangling miss, not a decision — but it is the shape in
    #: every document and every editor payload, so 004 preserves it and
    #: records it. Feature 005 owns the fix.
    RAW_TYPES = frozenset({"RegionsType", "AudioChannelsType"})

    def _decode_field(self, key: str, raw, spec: TypeSpec):
        field = spec.field(key)

        if field is None:
            # Undescribed: wildcard content, or the leaked schemaLocation.
            # Passed through untouched (FR-009) — which is also why
            # ``ui_properties`` stays a plain dict rather than becoming
            # ``UI_properties``. The class exists and has never been reached,
            # because the lookup searched for the lowercase tag; binding it now
            # would start running code that has never run.
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
            return raw

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

    # -- encode ------------------------------------------------------------

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

        keys = list(obj.keys())
        ordered = spec.order_keys(keys) if spec is not None else keys

        for key in ordered:
            self._emit_field(element, key, obj[key], spec)

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
        """The spec bound to a Python class, if the registry knows one."""
        for type_name in self.registry.bound_type_names:
            if self.registry.model_for(type_name) is model:
                return derive(self.registry.binding_for(type_name).key)
        return None


def _instantiate(model: type, decoded: dict):
    """Build a model object the way the legacy parsers did: empty, then assign.

    Two properties depend on this, and both are invisible until something far
    away breaks.

    **Key order.** Constructing from a dict routes through ``ensure_items`` and
    inserts keys in ``REQ_ITEMS`` order; assigning preserves the *source
    document's* order. ``==`` cannot see the difference — dicts compare equal
    regardless of order — but ``CuemsScript`` is an ``xs:all`` type whose
    emission order **is** arrival order (FR-001b), so constructing would
    rewrite the root element of every hand-authored script on save.

    **Property setters do not run.** ``dict.__setitem__`` bypasses them, which
    is what the parsers have always done. It matters because the setters
    validate: ``Media.set_id`` raises on the nil uuid
    ``00000000-0000-0000-0000-000000000000``, which appears three times in
    ``tests/data/sample_script.json`` and therefore in real editor payloads.
    Constructing from a dict would make the engine reject a document today's
    parser accepts — exactly what FR-015 forbids.

    Both are behaviours of the code being replaced rather than choices made
    here. The setters' validation is worth having; turning it on is a
    behaviour change, so it belongs to feature 005.
    """
    obj = model()
    for key, value in decoded.items():
        dict.__setitem__(obj, key, value)
    return obj


class DmxSceneCompatibility:
    """The one named compatibility behaviour (FR-015a, T046).

    ``DmxSceneXmlBuilder.build`` wraps its whole body in
    ``except Exception`` and logs instead of raising, so a DMX scene that fails
    to serialize produces **no elements and no error** — the surrounding
    document saves as if the scene were empty.

    That is a defect. It is also behaviour: a show with a bad DMX scene saves
    today, and making it fail instead is a behaviour change FR-015 forbids in
    this feature. So it is reproduced here **by name**, scoped to DMX scenes,
    and carrying its removal target — not as an ambient ``except Exception`` in
    the general path, which would swallow unrelated failures and quietly make
    every other error class disappear too.

    **Removal target: feature 005.**
    """

    REMOVAL_TARGET = "005"

    @staticmethod
    def guard(scene_label: str):
        return _SwallowAndLog(scene_label)


class _SwallowAndLog:
    def __init__(self, label: str):
        self.label = label
        self.failed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        if exc is None:
            return False
        self.failed = True
        # Identifier only, never the object repr — FR-033.
        Logger.error(
            f"Error building DmxScene {self.label}: {exc_type.__name__} "
            f"(preserved failure path, removal target: feature "
            f"{DmxSceneCompatibility.REMOVAL_TARGET})"
        )
        return True


def root_spec(schema_name: str) -> TypeSpec:
    return derive_path(schema_name, get_registry(schema_name).root)


SCHEMA_INSTANCE_URI = "http://www.w3.org/2001/XMLSchema-instance"


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

    Logger.info(f"Built {schema_name} document root <{xml_root_tag}>")
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
