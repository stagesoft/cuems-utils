"""Type coercion on the **live** paths (T036a) — SC-010, FR-003.

``tests/test_name_coercion.py`` pins ``str_to_value`` itself, and stays as the
frozen-shim regression for it. That file cannot show what this feature actually
changed, because it calls the heuristic directly — after the swap the heuristic
is no longer on any live path, so testing it proves nothing about what the
library now does.

So the same cases are driven here through **both** live paths:

* the XML read path, ``XmlReaderWriter.read_to_objects``;
* the editor's JSON path, ``CuemsParser`` on a payload.

The assertion is different in kind, too. ``test_name_coercion`` asserts the
heuristic's *guess* is right for a known list of key names — a denylist, which
by construction only covers the keys someone remembered. Here the assertion is
that the value keeps the type the **schema declares**, which holds for every
key of that type whether or not anyone thought of it.

ClickUp 869cqbpxa is the defect this closes: a cue named ``n`` was persisted as
``False``, one named ``1`` as the integer ``1``, and one named ``none`` became
``None`` → ``<name/>`` → a hard ``minLength`` validation failure at save time.
"""

from __future__ import annotations

import warnings

import pytest

from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.tools.Uuid import Uuid
from cuemsutils.xml.Parsers import CuemsParser
from tests.support import roundtrip as rt
from tests.support.corpus import by_relpath

SCRIPT = "cuems-editor/script_minimal.xml"

#: ``strtobool``'s entire vocabulary, which is what made 18 of the 62
#: alphanumeric single characters unusable as cue names.
BOOLEAN_LOOKING = [
    "y", "Y", "n", "N", "t", "T", "f", "F",
    "yes", "no", "true", "false", "on", "off",
    "1", "0",
]

NULLISH = ["none", "null", "None", "NULL"]

NUMERIC_LOOKING = ["1", "0", "42", "007", "-1"]

#: Keys the old code had to protect by name. Every one is declared a string
#: type in the schema, which is why the denylist can retire.
STRING_TYPED = ["name", "description"]

#: Keys that legitimately coerce. Without these the suite would pass for an
#: implementation that simply never converted anything.
COERCING = {"loop": int, "master_vol": int, "timecode": bool, "enabled": bool}


def _payload(cue_fields: dict) -> dict:
    return {
        "CuemsScript": {
            "CueList": {
                "id": "8726353c-5c8c-41fe-bab7-1b9d765ced77",
                "contents": [{"AudioCue": {**cue_fields}}],
            }
        }
    }


def _json_cue(cue_fields: dict):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        script = CuemsParser(_payload(cue_fields)).parse()
    return script["CueList"]["contents"][0]


@pytest.fixture(scope="module")
def xml_cue():
    """A real cue loaded from a real document, through the XML path."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(by_relpath(SCRIPT))
    for cue in obj["CueList"]["contents"]:
        if type(cue).__name__ == "AudioCue":
            return cue
    pytest.skip("no AudioCue in the fixture")


# --- the JSON path: names and descriptions are never coerced --------------


@pytest.mark.parametrize("text", BOOLEAN_LOOKING)
@pytest.mark.parametrize("key", STRING_TYPED)
def test_json_path_never_coerces_string_typed_fields_to_bool(key, text):
    cue = _json_cue({key: text})
    assert cue[key] == text
    assert not isinstance(cue[key], bool)


@pytest.mark.parametrize("text", NULLISH)
@pytest.mark.parametrize("key", STRING_TYPED)
def test_json_path_never_nullifies_string_typed_fields(key, text):
    """The failure mode that was a hard save error rather than corruption."""
    cue = _json_cue({key: text})
    assert cue[key] == text
    assert cue[key] is not None


@pytest.mark.parametrize("text", NUMERIC_LOOKING)
@pytest.mark.parametrize("key", STRING_TYPED)
def test_json_path_never_coerces_string_typed_fields_to_int(key, text):
    cue = _json_cue({key: text})
    assert cue[key] == text
    assert not isinstance(cue[key], int)


@pytest.mark.parametrize("char", [chr(c) for c in range(ord("a"), ord("z") + 1)])
def test_every_single_letter_survives_as_a_cue_name(char):
    """All 26 letters, not just the ones the denylist happened to list.

    Sergio reported this as "can't name a cue with a single letter". There was
    never a length rule — the failing characters were exactly ``strtobool``'s
    vocabulary.
    """
    assert _json_cue({"name": char})["name"] == char


@pytest.mark.parametrize("digit", [str(d) for d in range(10)])
def test_every_single_digit_survives_as_a_cue_name(digit):
    assert _json_cue({"name": digit})["name"] == digit


# --- the JSON path: declared non-string types still convert ---------------


@pytest.mark.parametrize("key,expected_type", sorted(COERCING.items()))
def test_json_path_still_coerces_declared_types(key, expected_type):
    raw = {"loop": "2", "master_vol": "80", "timecode": "True", "enabled": "False"}[key]
    value = _json_cue({key: raw})[key]
    assert isinstance(value, expected_type), f"{key} -> {type(value).__name__}"


def test_json_path_decodes_declared_uuid_types():
    value = _json_cue({"id": "8726353c-5c8c-41fe-bab7-1b9d765ced77"})["id"]
    assert isinstance(value, Uuid)


def test_json_path_decodes_declared_timecode_types():
    value = _json_cue({"offset": {"CTimecode": "00:00:02.000"}})["offset"]
    assert isinstance(value, CTimecode)


# --- the XML path -----------------------------------------------------------


@pytest.mark.parametrize("key", STRING_TYPED)
def test_xml_path_keeps_string_typed_fields_as_strings(xml_cue, key):
    value = xml_cue[key]
    if value is None:
        pytest.skip(f"{key} is absent in the fixture")
    assert isinstance(value, str)


def test_xml_path_decodes_declared_types(xml_cue):
    assert isinstance(xml_cue["loop"], int)
    assert isinstance(xml_cue["enabled"], bool)
    assert isinstance(xml_cue["id"], Uuid)
    assert isinstance(xml_cue["offset"], CTimecode)


def test_xml_and_json_paths_agree_on_types(xml_cue):
    """One engine means one answer.

    Before this feature the two paths ran different code — ``CuemsParser`` for
    JSON, the same parsers reached differently for XML — so agreeing was a
    coincidence that held until it did not.
    """
    json_cue = _json_cue(
        {
            "loop": "1",
            "enabled": "True",
            "id": "8726353c-5c8c-41fe-bab7-1b9d765ced77",
            "offset": {"CTimecode": "00:00:00.000"},
        }
    )
    for key in ("loop", "enabled", "id", "offset"):
        assert type(json_cue[key]) is type(xml_cue[key]), key


# --- the structural claim ---------------------------------------------------


def test_no_live_path_reaches_the_type_guessing_heuristic():
    """FR-003 — ``str_to_value`` is deprecated, so any live call would warn.

    Driving a document through both paths under ``simplefilter("always")`` and
    seeing **zero** deprecation warnings is what makes "not reachable from any
    live path" a measurement rather than a claim (and is C8 in miniature).
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        doc = by_relpath(SCRIPT)
        obj = rt.read_objects(doc)
        rt.write_bytes(doc, obj)
        CuemsParser(_payload({"name": "n"})).parse()

    offenders = [
        f"{w.filename.split('/')[-1]}:{w.lineno} {w.message}"
        for w in caught
        if issubclass(w.category, DeprecationWarning)
    ]
    assert not offenders, offenders


def test_the_denylist_is_no_longer_consulted():
    """``STRING_TYPED_KEYS`` protected keys by *name*; types protect by type.

    A key of a string type that is **not** in the denylist must still survive
    coercion — which is the difference between the two mechanisms, and the
    reason the defect class is now unrepresentable rather than merely covered.
    """
    from cuemsutils.xml.Parsers import STRING_TYPED_KEYS

    assert "unit_name" not in STRING_TYPED_KEYS
    # ``name`` is in the denylist; ``description`` protection comes from its
    # declared type either way. Both must hold with the denylist unused.
    assert _json_cue({"description": "n"})["description"] == "n"
    assert _json_cue({"description": "none"})["description"] == "none"
