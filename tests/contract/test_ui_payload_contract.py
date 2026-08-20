"""Contract C5 (T017) — the UI payload is untouched.

The dict from C2 is what ``cuems-editor`` transmits **verbatim** to the Angular
UI on ``project_load``. No frontend change is required by this feature, and none
is permitted to become necessary.

Each assertion below is a shape the frontend reads directly. They look like
quirks, and two of them are; that is precisely why they need pinning, because a
quirk is what a rewrite tidies up first.
"""

from __future__ import annotations

import json

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

SCRIPT_DOCS = [
    d
    for d in DOCUMENTS
    if d.schema == "script" and (GOLDEN_ROOT / "dict" / f"{d.slug}.reader.json").exists()
]
IDS = [d.relpath for d in SCRIPT_DOCS]

BOOLEAN_FIELDS = ("autoload", "enabled", "timecode")


def _walk(node, path="", out=None):
    out = [] if out is None else out
    if isinstance(node, dict):
        for k, v in node.items():
            out.append((f"{path}/{k}", k, v))
            _walk(v, f"{path}/{k}", out)
    elif isinstance(node, list):
        for item in node:
            _walk(item, f"{path}[]", out)
    return out


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_booleans_are_the_strings_true_and_false(doc):
    """``cms:BoolType`` is an ``xs:string`` enum (X1), not ``xs:boolean``.

    So the payload carries ``"True"`` / ``"False"`` — capitalised Python
    spelling, as strings. Decoding them to real JSON booleans would be the
    single most natural "improvement" to make here and would break every
    consumer of the payload at once.
    """
    found = [
        (path, value)
        for path, key, value in _walk(rt.read_dict(doc))
        if key in BOOLEAN_FIELDS
    ]
    assert found, f"{doc.relpath} carries no boolean fields to check"
    for path, value in found:
        assert isinstance(value, str), f"{path} decoded to {type(value).__name__}"
        assert value in ("True", "False"), f"{path} == {value!r}"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_ctimecode_keeps_its_wrapper_shape(doc):
    """``{"CTimecode": "00:00:00.000"}`` — a dict, not a bare string.

    The wrapper is stated by the schema (``CTimecodeType`` is a complex type,
    research R5), not invented by the converter, and the UI unwraps it itself.
    """
    wrapped = [
        (path, value)
        for path, key, value in _walk(rt.read_dict(doc))
        if key in ("offset", "prewait", "postwait", "in_time", "out_time", "duration")
        and value is not None
    ]
    for path, value in wrapped:
        if isinstance(value, dict):
            assert set(value) == {"CTimecode"}, f"{path} == {value!r}"
            assert isinstance(value["CTimecode"], str)


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_ui_properties_scalars_stay_strings(doc):
    """``UiPropertiesType`` is a wildcard (R6): nothing about it is derivable.

    Its children have no declared type, so they pass through untyped and stay
    strings. A mapper that started guessing types here would change the payload
    for every cue in every project.
    """
    for path, key, value in _walk(rt.read_dict(doc)):
        if "/ui_properties/" not in f"{path}/":
            continue
        if isinstance(value, (dict, list, type(None))):
            continue
        assert isinstance(value, str), f"{path} decoded to {type(value).__name__}"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_repeated_elements_stay_lists_of_single_key_dicts(doc):
    """FR-014 / F22 — the repeated-element shape *is* the contract.

    ``contents``, ``outputs``, ``regions`` and friends decode as
    ``[{"AudioCue": {...}}, ...]`` rather than as a flat list of values. The
    key inside each wrapper is what tells the UI which cue type it is holding.
    """
    golden = json.loads(rt.golden_json(f"dict/{doc.slug}.reader.json"))
    for path, key, value in _walk(golden):
        if key not in ("contents", "outputs", "regions"):
            continue
        if not isinstance(value, list):
            continue
        for item in value:
            assert isinstance(item, dict), f"{path} holds a bare {type(item).__name__}"
            assert len(item) == 1, f"{path} item has keys {sorted(item)}"


# --- feature 006 addition (T034, W3, F22) ---------------------------------
#
# Everything above reads the *decoder's* output. The projection now produces
# the same shape from the object side, and that is a second implementation of
# one contract — so it gets its own assertion rather than being covered by
# transitivity through a golden comparison. A future change to the decode
# shape has to fail here, loudly, naming the shape.


def test_the_projection_reproduces_the_repeated_element_shape_exactly():
    """``to_wire()`` emits ``[{Tag: {...}}, ...]``, not a grouped dict.

    Stated as its own rule because the alternative is genuinely tempting:
    upstream ``xmlschema`` groups repeated children by name
    (``{"AudioCue": [...], "VideoCue": [...]}``), which is tidier and wrong
    here. A cue list **interleaves** cue types and its order is the running
    order of the show; grouping discards it. The key inside each wrapper is
    also how the frontend knows what it is holding.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    doc = next(
        d
        for d in SCRIPT_DOCS
        if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()
    )
    wire = CuemsScript.load(doc.path).to_wire()

    contents = wire["CuemsScript"]["CueList"]["contents"]
    assert isinstance(contents, list), type(contents).__name__
    assert contents, "the fixture carries no cues, so the shape is untested"
    for item in contents:
        assert isinstance(item, dict), f"bare {type(item).__name__} in contents"
        assert len(item) == 1, f"wrapper has keys {sorted(item)}"
        tag, body = next(iter(item.items()))
        assert tag.endswith("Cue") or tag == "CueList", tag
        assert isinstance(body, dict), f"{tag} body is {type(body).__name__}"


def test_the_projection_and_the_decoder_agree_on_that_shape():
    """One contract, two implementations — asserted against each other.

    ``rt.read_dict`` is the decoder and ``to_wire()`` is the projection. If
    they ever disagree about repeated content the UI sees one shape on
    ``project_load`` and another on ``initial_template``, which is the class of
    divergence this whole feature exists to close.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    doc = next(
        d
        for d in SCRIPT_DOCS
        if (GOLDEN_ROOT / "xml" / f"{d.slug}.xml").exists()
    )
    decoded = rt.read_dict(doc)["CuemsScript"]["CueList"]["contents"]
    projected = CuemsScript.load(doc.path).to_wire()["CuemsScript"]["CueList"]["contents"]

    assert [sorted(i) for i in decoded] == [sorted(i) for i in projected]


def test_no_script_document_decodes_a_python_bool():
    """The negative form of the boolean rule, across the whole corpus.

    Stated separately because the per-field check only inspects the three known
    boolean fields; this one would catch a *new* field decoding as ``bool``.
    """
    offenders = []
    for doc in SCRIPT_DOCS:
        for path, _key, value in _walk(rt.read_dict(doc)):
            if isinstance(value, bool):
                offenders.append(f"{doc.relpath}{path}")
    assert not offenders, f"JSON booleans in the UI payload: {offenders}"
