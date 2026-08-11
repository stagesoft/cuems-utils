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

    Both ``legacy/`` scripts pass schema validation and fail in
    ``CueOutput._classify_output_name``: they predate the
    ``<uuid>_<int>`` / ``<uuid>_custom_<int>`` output-name convention. So they
    are compatibility evidence at the dict layer and *not* at the object layer,
    and saying "they load" without qualification would be wrong in a way that
    matters to FR-035a.
    """
    legacy = [d for d in DOCUMENTS if d.category == "legacy"]
    assert legacy
    for doc in legacy:
        assert OUTCOMES[doc.relpath]["read"]["ok"] is True
        assert OUTCOMES[doc.relpath]["to_objects"]["ok"] is False
        assert OUTCOMES[doc.relpath]["to_objects"]["error_type"] == "ValueError"


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
