"""The D5 thin converter (T043).

Replaces ``CMLCuemsConverter``, which was a **fork**: both ``element_decode``
and ``element_encode`` were copied wholesale from an older ``xmlschema`` and
then edited, so every upstream fix since has been silently declined — and the
copy reaches into ``xmlschema.validators.wildcards.Xsd11AnyElement``, a
non-public path, which is exactly the coupling D5 exists to remove (R11).

This subclass overrides **one method**, and within it rebuilds **one block** —
the content assembly. Everything else (namespace handling, attribute mapping,
simple content, text, ``preserve_root``) is delegated to ``super()`` and keeps
receiving upstream fixes. ``element_encode`` is not overridden at all; the fork
carried a copy of it that differed from upstream only by drift.

Only public API is imported.

## Why the content block cannot simply be upstream's

Three decisions differ from stock, and all three are visible in the payload
`cuems-editor` transmits verbatim to the Angular UI (F22, FR-014, contract C5).

1. **Repeated elements decode as an ordered list of single-key dicts** —
   ``[{"ActionCue": {...}}, {"AudioCue": {...}}]`` — not grouped by name as
   ``{"ActionCue": [...], "AudioCue": [...]}``. A cue list *interleaves* cue
   types and its order is the running order of the show; grouping discards it,
   and the key inside each wrapper is how the frontend knows what it is holding.

2. **Cardinality is read from the child alone**, ``xsd_child.is_single()``.
   Upstream also requires the enclosing group to be single. That is the wrong
   test here: ``AudioCueOutputsType`` is a non-single sequence whose three
   children are each ``1..1``, so upstream reports ``output_name``,
   ``output_vol`` and ``channels`` as repeated and shatters every audio output
   into a list.

3. **Wildcard children are assigned directly**, with no cardinality treatment
   at all. Nothing about ``UiPropertiesType``'s children is derivable — no
   name, no type, no cardinality (R6) — so upstream's normal logic turns
   ``<x>0</x>`` into ``{"x": ["0"]}``. ``ui_properties`` carries editor state
   for every cue in every project.
"""

from __future__ import annotations

from xmlschema import XMLSchemaConverter
from xmlschema.validators import XsdAnyElement

__all__ = ["CuemsConverter"]


class CuemsConverter(XMLSchemaConverter):
    """``XMLSchemaConverter`` with the CueMS content shape preserved.

    Defaults match the fork's, because they are what the corpus was decoded
    with: ``text_key='&'``, ``attr_prefix=''``, ``cdata_prefix=None``,
    ``strip_namespaces=True``. Callers override ``strip_namespaces`` per reader
    configuration (FR-013).
    """

    def __init__(
        self,
        namespaces=None,
        dict_class=None,
        list_class=None,
        etree_element_class=None,
        text_key="&",
        attr_prefix="",
        cdata_prefix=None,
        indent=4,
        strip_namespaces=True,
        preserve_root=False,
        force_dict=False,
        force_list=False,
        **kwargs,
    ):
        # ``xmlns_processing='none'`` reproduces the fork, which never emitted
        # ``xmlns:*`` keys. It carried a level-0 branch that would have, guarded
        # by ``and self`` — its own namespace map, initialised empty and never
        # populated — so the branch never ran. Upstream 3.4.3 collects xmlns
        # from the document and emits them, which would add three keys to the
        # root of every decoded document.
        kwargs.pop("xmlns_processing", None)
        super().__init__(
            namespaces=namespaces,
            dict_class=dict_class,
            list_class=list_class,
            etree_element_class=etree_element_class,
            text_key=text_key,
            attr_prefix=attr_prefix,
            cdata_prefix=cdata_prefix,
            indent=indent,
            strip_namespaces=strip_namespaces,
            preserve_root=preserve_root,
            force_dict=force_dict,
            force_list=force_list,
            xmlns_processing="none",
            **kwargs,
        )

    def element_decode(self, data, xsd_element, xsd_type=None, level=0):
        """Decode via ``super()``, then rebuild the content block.

        The simple-content and text paths return non-dict values and are left
        entirely to upstream — only an element with real content reaches the
        rebuild.
        """
        decoded = super().element_decode(data, xsd_element, xsd_type, level)

        xsd_type = xsd_type or xsd_element.type
        group = getattr(xsd_type, "model_group", None)
        if group is None or not data.content:
            return decoded
        if not isinstance(decoded, (dict, self.dict)):
            return decoded

        content = self._decode_content(data.content)
        if content is None:
            return decoded

        return self._with_attributes(content, decoded, data)

    def _decode_content(self, content):
        """Assemble decoded children under the three rules above.

        Note the shape switch: as soon as a repeated child appears, the result
        becomes a **list** rather than a dict, and every subsequent child is
        appended to it. That is what produces ``"contents": [{...}, {...}]``
        rather than a dict keyed by cue type.
        """
        result = self.dict()
        for name, value, xsd_child in self.map_content(content):
            if isinstance(xsd_child, XsdAnyElement):
                # Wildcard: assign directly, no cardinality treatment (R6).
                # Later duplicates overwrite earlier ones — with no declared
                # cardinality there is no basis for choosing otherwise, and
                # inventing one is the guessing this feature removes.
                if isinstance(result, list):
                    result.append({name: value})
                else:
                    result[name] = value
                continue

            repeated = xsd_child is not None and not xsd_child.is_single()

            if isinstance(result, list):
                result.append({name: value})
                continue

            if name not in result:
                if repeated:
                    result = self.list([{name: value}])
                else:
                    result[name] = value
                continue

            # A second occurrence of a name already present. Reached when the
            # schema declares an element single but the document repeats it —
            # invalid input that strict validation rejects before this point,
            # kept only so the shape stays defined.
            existing = result[name]
            if isinstance(existing, (dict, self.dict)):
                result[name] = self.list([existing, value])
            elif isinstance(existing, list):
                existing.append(value)
            else:
                result[name] = self.list([existing, value])

        return result if result or isinstance(result, list) else None

    def _with_attributes(self, content, decoded, data):
        """Attach attributes **after** the content keys.

        Upstream merges attributes into the result before walking content; the
        fork did it after. With ``attr_prefix=''`` the two are
        indistinguishable by key name, so the difference shows up only as key
        insertion order — which is inside the C2 guarantee, because the dict is
        compared as ``json.dumps`` output and consumers serialize it the same
        way (FR-011a).

        On real documents the attribute this moves is the leaked
        ``{…XMLSchema-instance}schemaLocation`` (F23).
        """
        if not data.attributes:
            return content

        attributes = [
            (name, value)
            for name, value in self.map_attributes(data.attributes)
        ]
        if isinstance(content, list):
            # A repeated block carries no room for attributes; upstream's
            # result is the only defined shape here. Does not occur in the six
            # schemas.
            return decoded

        for name, value in attributes:
            content[name] = value
        return content
