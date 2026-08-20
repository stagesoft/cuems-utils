"""Contract C0 (T021) — what ``from_json`` accepts, and how it refuses.

Three input forms, exhaustively (contracts §C0): a JSON **string**, UTF-8
**bytes**, and an already-decoded **``Mapping``**. ``bytes`` is not a
convenience — FR-036c makes accepting UTF-8 bytes, and *rejecting* other codecs
rather than guessing, part of the encoding contract.

Two refusal modes, and keeping them apart is the requirement:

``IngestError``
    the payload is **not a script at all** — an array, a scalar, a mapping
    whose root nothing recognises, bytes that are not UTF-8. The message names
    what was expected, rather than surfacing a ``KeyError`` from inside the
    machinery.

``SchemaError``
    the payload **is** a script and fails the structural check (FR-023a). On
    this path there is no XML document to hand the schema, so T1 *is* the
    decode-time check: every key resolved against a declared field, every value
    accepted by its adapter.

Undeclared keys are neither: they are dropped and **logged**, one record per
key naming the class and the key — feature 005's behaviour, unchanged.
"""

from __future__ import annotations

import json
import logging
import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import IngestError, SchemaError
from tests.support import invalid_scripts as broken
from tests.support.public_api import assert_no_xml_import


@pytest.fixture(scope="module")
def payload() -> dict:
    return broken.valid_script().to_wire()


def test_a_decoded_mapping_is_accepted(payload):
    assert isinstance(CuemsScript.from_json(payload), CuemsScript)


def test_a_json_string_is_accepted(payload):
    assert isinstance(CuemsScript.from_json(json.dumps(payload)), CuemsScript)


def test_utf8_bytes_are_accepted(payload):
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    assert isinstance(CuemsScript.from_json(raw), CuemsScript)


def test_the_three_forms_produce_equal_objects(payload):
    text = json.dumps(payload, ensure_ascii=False)
    from_mapping = CuemsScript.from_json(payload)
    from_str = CuemsScript.from_json(text)
    from_bytes = CuemsScript.from_json(text.encode("utf-8"))
    assert from_str == from_mapping
    assert from_bytes == from_mapping


def test_a_bare_body_without_the_root_wrapper_is_accepted(payload):
    """The editor sends both shapes; neither is the odd one out."""
    body = payload["CuemsScript"]
    assert CuemsScript.from_json(body) == CuemsScript.from_json(payload)


@pytest.mark.parametrize(
    "bad",
    [
        pytest.param("[1, 2, 3]", id="json-array"),
        pytest.param("42", id="json-scalar"),
        pytest.param('"a string"', id="json-string-scalar"),
        pytest.param("null", id="json-null"),
        pytest.param('{"NotAScript": {"a": 1}}', id="unrecognised-root"),
        pytest.param("{}", id="empty-mapping"),
        pytest.param("not json at all", id="malformed-json"),
    ],
)
def test_a_payload_that_is_not_a_script_raises_ingest_error(bad):
    with pytest.raises(IngestError):
        CuemsScript.from_json(bad)


def test_the_ingest_message_names_what_was_expected():
    with pytest.raises(IngestError) as caught:
        CuemsScript.from_json("[1, 2, 3]")
    assert "CuemsScript" in str(caught.value)


def test_non_utf8_bytes_are_refused_rather_than_guessed():
    """FR-036c: no codec sniffing. Latin-1 bytes are an error, not a fallback."""
    latin1 = '{"CuemsScript": {"name": "Cançó"}}'.encode("latin-1")
    with pytest.raises(IngestError):
        CuemsScript.from_json(latin1)


def test_a_value_its_adapter_rejects_raises_schema_error(payload):
    """FR-023a — distinct from ``IngestError``: this *is* a script."""
    broken_payload = json.loads(json.dumps(payload))
    broken_payload["CuemsScript"]["CueList"]["loop"] = "not-an-integer"

    with pytest.raises(SchemaError):
        CuemsScript.from_json(broken_payload)


def test_schema_error_and_ingest_error_are_catchable_apart(payload):
    with pytest.raises(IngestError):
        try:
            CuemsScript.from_json("[1, 2, 3]")
        except SchemaError:  # pragma: no cover - would mean the types collapsed
            pytest.fail("a non-script payload was reported as a schema failure")


def test_undeclared_keys_are_dropped_and_logged(payload, caplog):
    """Dropped at the declared-field boundary, and named when it happens.

    The drop is the model's rule, so it takes effect where the declared field
    set is consulted — ``items()`` and the projection — rather than by deleting
    the key on the way in. What the requirement is actually about is that the
    key never reaches a consumer **and** that its disappearance leaves a
    record: silent loss is how data vanishes without a trace.
    """
    payload = json.loads(json.dumps(payload))
    payload["CuemsScript"]["not_a_field"] = "dropped"

    with caplog.at_level(logging.DEBUG):
        script = CuemsScript.from_json(payload)
        wire = script.to_wire()

    assert "not_a_field" not in dict(script.items())
    assert "not_a_field" not in wire["CuemsScript"]
    records = [r.getMessage() for r in caplog.records if "not_a_field" in r.getMessage()]
    assert records, "an undeclared key was dropped without a record naming it"
    assert any("CuemsScript" in message for message in records), records


def test_the_module_under_test_names_nothing_from_the_xml_package():
    assert_no_xml_import(sys.modules[__name__])
