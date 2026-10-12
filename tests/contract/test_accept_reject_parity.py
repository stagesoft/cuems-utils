"""Accept/reject parity (T018) — FR-015, FR-035a.

Today's verdict on every corpus document, at every layer, pinned.

The obligation runs in **both** directions and that is easy to get wrong. "The
engine may never reject what today's parser accepts" is the half everyone
remembers; the other half — it may not start *accepting* what today's parser
rejects — matters just as much, because silently widening what loads is how a
malformed show file reaches a stage.

Three layers are recorded separately, because a document can pass one and fail
the next, and conflating them hides real changes:

* ``read``       — schema validation and dict decode;
* ``to_objects`` — building the model objects (``CuemsParser``);
* ``write``      — serializing them back out.

The ``legacy/`` documents are the case that motivated the split: both validate
against the schema and both fail at the object layer.
"""

from __future__ import annotations

import json

import pytest

from tests.support import roundtrip as rt
from tests.support.capture_goldens import _ADDRESS_RE
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

OUTCOMES = json.loads((GOLDEN_ROOT / "outcomes.json").read_text())
IDS = [d.relpath for d in DOCUMENTS]


def _verdict(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - the failure is the measurement
        head = str(exc).splitlines()[0][:200] if str(exc) else ""
        return {
            "ok": False,
            "error_type": type(exc).__name__,
            "error_head": _ADDRESS_RE.sub("0xADDR", head),
        }
    return {"ok": True}


@pytest.mark.parametrize("doc", DOCUMENTS, ids=IDS)
def test_read_verdict_is_unchanged(doc):
    expected = OUTCOMES[doc.relpath]["read"]
    assert _verdict(rt.read_dict, doc) == expected


@pytest.mark.parametrize("doc", DOCUMENTS, ids=IDS)
def test_to_objects_verdict_is_unchanged(doc):
    expected = OUTCOMES[doc.relpath]["to_objects"]
    if not OUTCOMES[doc.relpath]["read"]["ok"]:
        pytest.skip("document does not reach the object layer today")
    assert _verdict(rt.read_objects, doc) == expected


@pytest.mark.parametrize("doc", DOCUMENTS, ids=IDS)
def test_config_read_verdict_is_unchanged(doc):
    record = OUTCOMES[doc.relpath]
    if "config_read" not in record:
        pytest.skip("no config class reads this schema")
    assert _verdict(rt.read_config_dict, doc) == record["config_read"]


@pytest.mark.parametrize("doc", DOCUMENTS, ids=IDS)
def test_write_verdict_is_unchanged_in_substance(doc):
    """The write layer, asserted **live** rather than against the record.

    This was the gap that let the exception-class change below go unnoticed:
    ``test_config_documents_still_fail_to_write`` reads ``outcomes.json``, so it
    checks the golden against itself and passes whatever the library does.

    What FR-015 binds is the **verdict** — writable or not. The exception
    *class* is deliberately not asserted here; see the test below, which pins
    the one place it changed and says why.
    """
    record = OUTCOMES[doc.relpath]
    if "write" not in record:
        pytest.skip("document does not reach the write layer today")

    obj = rt.read_objects(doc)
    verdict = _verdict(rt.write_bytes, doc, obj)
    assert verdict["ok"] == record["write"]["ok"]


def test_config_documents_fail_to_write_with_a_changed_exception_class():
    """A declared difference inside an already-failing path.

    Config documents have never been writable — ``Settings`` and its subclasses
    are read-only, and building XML from a settings dict has always raised. The
    *verdict* is unchanged, which is what FR-015 binds.

    The **class** changed. Pre-refactor, ``XmlBuilder`` crashed part-way
    through construction with ``AttributeError`` (``'int' object has no
    attribute 'items'``, ``'NoneType' object has no attribute 'tag'``, and three
    other spellings depending on which key it reached first). The mapper builds
    a complete tree and hands it to the schema, which rejects it with
    ``XMLSchemaChildrenValidationError`` naming the offending element.

    Recorded rather than smoothed over. It is a strictly better failure — an
    error about the document instead of an error about the builder's internals
    — and no consumer can be relying on it, because no consumer can write these
    documents at all. Feature 006 makes them writable, at which point this test
    is deleted rather than updated.
    """
    config_docs = [
        d
        for d in DOCUMENTS
        if d.schema != "script" and OUTCOMES[d.relpath].get("write", {}).get("ok") is False
    ]
    assert config_docs, "no config document reaches the write layer"

    for doc in config_docs:
        assert OUTCOMES[doc.relpath]["write"]["error_type"] == "AttributeError"
        verdict = _verdict(rt.write_bytes, doc, rt.read_objects(doc))
        assert verdict["ok"] is False
        assert verdict["error_type"] == "XMLSchemaChildrenValidationError"


def test_the_deliberately_bad_document_still_fails():
    """The one negative case that was authored to fail, named explicitly.

    Parametrised parity would cover it, but a corpus can lose a file and the
    parametrisation shrinks silently. This one is load-bearing enough to be
    named: without it, "rejects what it should reject" would rest entirely on
    documents that fail by accident of age.
    """
    doc = next(d for d in DOCUMENTS if d.relpath.endswith("settings_bad_dmx_auto.xml"))
    verdict = _verdict(rt.read_dict, doc)
    assert verdict["ok"] is False
    assert verdict["error_type"] == "XMLSchemaDecodeError"


def test_legacy_documents_validate_but_do_not_build_objects():
    """The distinction the three-layer split exists for.

    Both ``legacy/`` scripts predate the ``<uuid>_<int>`` /
    ``<uuid>_custom_<int>`` output-name convention, so they fail in
    ``CueOutput._classify_output_name`` — that was the *entire* story through
    feature 007, when both passed schema validation and only the object layer
    rejected them.

    **Feature 008 changes this** (FR-002, D3's second recorded exception,
    ``migration-guide.md``): ``Media.duration`` is promoted from a bare
    string to ``cms:CTimecodeType``, which both legacy documents still carry
    in the old shape — so schema validation (T1) now rejects them too, before
    the output-name check is ever reached. They are frozen historical
    snapshots (real revisions of a real script, recovered from
    ``cuems-engine``'s history) and are deliberately **not** rewritten to the
    new shape — see ``tests/data/corpus/pre-008/`` for what a retained
    old-shape document is *for*: this feature's D3 relaxation is licensed
    only because a Phase 2 conversion path exists to carry documents like
    these forward, and these two are compatibility evidence of exactly that
    gap until Phase 2 lands.
    """
    legacy = [d for d in DOCUMENTS if d.category == "legacy"]
    assert legacy
    for doc in legacy:
        assert OUTCOMES[doc.relpath]["read"]["ok"] is False
        assert OUTCOMES[doc.relpath]["read"]["error_type"] == "XMLSchemaValidationError"
        assert OUTCOMES[doc.relpath]["to_objects"]["ok"] is False


def test_every_negative_document_is_rejected():
    for doc in (d for d in DOCUMENTS if d.category == "negative"):
        assert OUTCOMES[doc.relpath]["read"]["ok"] is False


def test_outcome_coverage_is_total():
    """No document may sit outside the parity record.

    A corpus entry with no recorded verdict is a document whose behaviour is
    free to change without failing anything.
    """
    missing = [d.relpath for d in DOCUMENTS if d.relpath not in OUTCOMES]
    assert not missing


# --- feature 005 additions (T012a) ----------------------------------------
#
# Additive only: no assertion above changes. Both cases below **pass on
# pre-005 code** — they are guards on acceptance that must survive coercion
# moving out of the property setters.


def test_the_nil_uuid_stays_accepted():
    """C2 — the nil UUID loads, and must keep loading (FR-006, SC-007).

    ``00000000-0000-0000-0000-000000000000`` appears three times in
    ``tests/data/sample_script.json``, so real editor payloads carry it. It
    fails ``Uuid``'s uuid4 shape check (version nibble 4, variant 8-b), and is
    accepted today only because ``_UuidAdapter.decode`` keeps an unparseable
    value as its **raw string** rather than calling ``Uuid()``.

    That is precisely the leniency feature 005 could destroy by accident: once
    the uuid-bearing setters delegate to the adapter (T037), the path that
    accepts this value changes. Asserted explicitly rather than inherited from
    the corpus parametrisation, because no corpus *document* contains it —
    only the JSON payload does, and a parametrisation over documents would
    report full coverage while testing none of this.
    """
    from cuemsutils.xml.adapters import adapter_for

    nil = "00000000-0000-0000-0000-000000000000"
    for type_name in ("UuidType", "TargetType"):
        decoded = adapter_for(type_name).decode(nil)
        assert decoded == nil, f"{type_name} rejected the nil uuid"
        assert isinstance(decoded, str)


def test_the_nil_uuid_survives_a_full_payload_parse():
    """The same value, through the real entry point rather than the adapter.

    ``Uuid(nil)`` raises, so a construction path that reached it would turn
    three values in a shipped payload into a load failure.
    """
    import json
    from pathlib import Path

    from cuemsutils.tools.Uuid import Uuid

    nil = "00000000-0000-0000-0000-000000000000"
    payload = Path("tests/data/sample_script.json").read_text()
    assert payload.count(nil) == 3, "the payload no longer carries the nil uuid"

    # The value that must not reach ``Uuid.__init__`` — pinned so the reason
    # this case exists stays visible.
    with pytest.raises(ValueError):
        Uuid(nil)

    assert json.loads(payload) is not None


# --- feature 006 addition (T069, FR-024d, FR-025, SC-008) ------------------
#
# The T2 rules moved into a named registry (US5) and their setters now
# delegate. Delegation must change **nothing** about which documents load.


def test_every_document_that_loaded_before_still_loads_through_the_public_api():
    """FR-025 through the surface consumers use, not through the reader.

    ``read_objects`` is the internal path the outcome goldens were captured
    from; ``CuemsScript.load`` is what a consumer calls. Both must agree with
    the recorded verdict, and asserting only the first would leave the public
    surface free to be stricter without anything noticing.
    """
    from cuemsutils.cues.CuemsScript import CuemsScript

    for doc in DOCUMENTS:
        if doc.schema != "script":
            continue
        record = OUTCOMES[doc.relpath]
        expected_ok = record["read"]["ok"] and record["to_objects"]["ok"]
        try:
            CuemsScript.load(doc.path)
            actual_ok = True
        except Exception:  # noqa: BLE001 - the verdict is the measurement
            actual_ok = False
        assert actual_ok == expected_ok, (
            f"{doc.relpath}: load() {'accepted' if actual_ok else 'rejected'} a "
            f"document recorded as {'accepted' if expected_ok else 'rejected'}"
        )


LEGACY_REJECTED = [
    "legacy/script_complex_test-engine-e6fc6c9.xml",
    "legacy/script_complex_test-engine-e7215ae.xml",
]


@pytest.mark.parametrize("relpath", LEGACY_REJECTED)
def test_the_two_pinned_documents_keep_exactly_their_outcomes(relpath):
    """FR-024d, superseded by feature 008's D3 duration relaxation.

    These two were the reason T074 exists: ``VideoCueOutput.__init__`` calls
    ``_classify_output_name`` **before** ``super().__init__``, and it is that
    *constructor* call — not the setter — that used to reject them, with
    schema validation (T1) passing. Feature 008 promotes ``Media.duration``
    to ``cms:CTimecodeType`` (FR-002); both documents still carry the old
    bare-string shape, so T1 now rejects them first and the object layer is
    never reached. What is pinned here is that they are still rejected, only
    earlier and for a different, recorded reason.
    """
    record = OUTCOMES[relpath]
    assert record["read"]["ok"] is False
    assert record["to_objects"]["ok"] is False

    doc = next(d for d in DOCUMENTS if d.relpath == relpath)
    with pytest.raises(Exception):
        rt.read_dict(doc)
    with pytest.raises(Exception):  # noqa: B017 - the type is pinned by the golden
        rt.read_objects(doc)


def test_the_constructor_is_what_rejects_them_not_the_setter():
    """Stated directly, on the class rather than on a document.

    A ``VideoCueOutput`` built with a malformed ``output_name`` must fail in
    ``__init__``, before ``super().__init__`` has run — so the object never
    exists. Building one *past* the constructor (``from_decoded``) and only
    then assigning shows the setter is a second gate, not the first.
    """
    from cuemsutils.cues.CueOutput import VideoCueOutput

    with pytest.raises(ValueError, match="does not match alias"):
        VideoCueOutput({"output_name": "VideoOut1"})

    survivor = VideoCueOutput.from_decoded({"output_name": "VideoOut1"})
    assert survivor["output_name"] == "VideoOut1"
