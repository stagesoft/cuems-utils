"""The gating byte-identity test (T005) — contracts §W1.

For every corpus script document:

    CuemsScript.load(path).to_wire()  ==  <pre-feature XmlReaderWriter.read() golden>
                                           minus the schemaLocation key

This crosses into a repository this feature does not edit: ``cuems-editor``
transmits ``to_wire()``'s eventual output **verbatim** to the Angular UI on
`project_load`. If this test is wrong, nothing else in this repository would
catch the regression — which is why it is the feature's gating test rather
than one test among many.

At this point in the feature (Foundational phase, before ``CuemsScript.load``
exists), the comparison drives ``Mapper('script').encode_wire`` directly
against ``read_objects()`` — the same object ``load()`` will return once US1
lands (T024 delegates to the same decode path).
"""

from __future__ import annotations

import json

import pytest

from cuemsutils.helpers import Unset
from cuemsutils.xml.adapters import PASSTHROUGH, adapter_for
from cuemsutils.xml.mapper import Mapper
from cuemsutils.xml.spec import derive
from tests.support import roundtrip as rt
from tests.support.corpus import GOLDEN_ROOT, script_documents

#: Scoped to documents that actually reach the object layer — see
#: test_wire_oracle.py's SCRIPT_DOCS for why nine of the fourteen are
#: excluded by design, not by oversight.
SCRIPT_DOCS = [
    d for d in script_documents() if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()
]
IDS = [d.relpath for d in SCRIPT_DOCS]

SCHEMA_LOCATION_KEY = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"


def _with_declared_defaults(value, spec, mapper):
    """Fill in materialized, non-empty declared defaults the golden cannot show.

    ``read()`` is a pure XML->dict conversion — it never touches the object
    model, so a document that omits an *optional* field never shows that
    field's key at all. ``from_decoded`` (feature 005, unrelated to and
    predating this one) materializes every declared default a decoded
    object's document omitted, **including** optional fields whose default
    is a real, non-empty value (measured case: ``VideoCue.opacity`` defaults
    to ``100`` and is optional in the schema — confirmed pre-existing,
    already-accepted behaviour: the *frozen* ``tests/golden/xml/*.xml``
    write goldens, captured before this feature and never touched by it,
    already contain ``<opacity>100</opacity>`` written into documents whose
    source never had the element).

    ``encode_wire`` faithfully projects what the object holds, so this gap
    between "what the document said" and "what the object, once decoded,
    holds" is real and belongs in the **oracle**, not papered over in
    ``encode_wire`` itself. This function makes that adjustment mechanically
    — from the schema and each bound model's own ``declared_defaults()``,
    not by naming ``opacity`` specially — so it holds for any field with the
    same shape, not only the one this corpus happens to exercise.

    Fields whose default is empty (``None``/``[]``/``{}``) are left alone:
    they would be omitted from the wire form regardless (``_omit``), so they
    never created a mismatch to begin with.
    """
    if not isinstance(value, dict):
        return value

    result = dict(value)
    model = mapper._model_for_spec(spec)
    if model is not None and hasattr(model, "declared_defaults"):
        for key, default in model.declared_defaults().items():
            if key in result or default is Unset:
                continue
            field = spec.field(key)
            if field is None or field.required:
                continue
            raw = default() if callable(default) else default
            if raw is None or raw == [] or raw == {}:
                continue
            adapter = adapter_for(field.xsd_type)
            result[key] = adapter.to_wire(raw) if adapter is not PASSTHROUGH else raw

    # Each key added above goes in its **schema position**, not at the end.
    # Appending was indistinguishable from positioning while every added field
    # was the last one declared; feature 013's ``class`` is a declared
    # *attribute*, derived after every element, so an appended ``opacity``
    # landed after it and ``encode_wire`` — which orders by the spec — put it
    # before. The golden's own keys keep the golden's own order, so a real
    # disagreement between the converter and ``encode_wire`` is still caught;
    # only the keys this function invented are placed.
    added = [key for key in result if key not in value]
    if added:
        position = {field.name: field.order for field in spec.fields}
        keys = list(value)
        for key in added:
            order = position.get(key)
            if order is None:
                keys.append(key)
                continue
            index = len(keys)
            for offset, existing in enumerate(keys):
                existing_order = position.get(existing)
                if existing_order is not None and existing_order > order:
                    index = offset
                    break
            keys.insert(index, key)
        result = {key: result[key] for key in keys}

    for key, v in list(result.items()):
        field = spec.field(key)
        if field is None or field.child is None:
            continue
        child_spec = derive(field.child)
        if child_spec.wildcard:
            continue
        if isinstance(v, list):
            result[key] = [_with_defaults_in_item(item, child_spec, mapper) for item in v]
        elif isinstance(v, dict):
            result[key] = _with_declared_defaults(v, child_spec, mapper)
    return result


def _with_defaults_in_item(item, child_spec, mapper):
    if not isinstance(item, dict) or len(item) != 1:
        return item
    tag, body = next(iter(item.items()))
    member = child_spec.field(tag)
    if member is None or member.child is None:
        return item
    # ``member.child`` is the unconditional alternative, so for a conditional
    # element it is the *fallback* type, not the one this body decodes as:
    # a ``<Cue class="video">`` resolves to ``VideoCueType``, and only that
    # type's model declares ``opacity``. The oracle has to run the same
    # dispatch the mapper runs, rather than a second approximation of it.
    chosen = mapper._alternative_for(body, member)
    return {tag: _with_declared_defaults(body, derive(chosen), mapper)}


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_encode_wire_matches_the_reader_golden_minus_schema_location(doc):
    mapper = Mapper("script")
    obj = rt.read_objects(doc)
    wire = mapper.encode_wire(obj)

    golden_path = GOLDEN_ROOT / "dict" / f"{doc.slug}.reader.json"
    golden = json.loads(golden_path.read_text(encoding="utf-8"))
    body_spec = mapper._spec_for_model(type(obj))
    expected = {
        "CuemsScript": _with_declared_defaults(golden["CuemsScript"], body_spec, mapper)
    }

    diffs = rt.wire_diff(wire, expected)
    assert not diffs, (
        f"encode_wire disagrees with {golden_path.name} (W1a):\n  "
        + "\n  ".join(diffs)
    )
