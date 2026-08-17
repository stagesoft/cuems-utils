"""Stray keys: one rule, dropped and logged — contract C10, FR-015a (T013).

**Must FAIL on pre-005 code**: the root leaks undeclared keys into both
projections while cues filter them silently. That is two rules for one
question, and the difference is invisible until a stray key reaches a consumer.

The chosen outcome is **dropped, but logged** (clarification 2026-08-12, option
B). Silent loss is how data disappears without a trace; raising would break
objects that construct fine today. So exactly one DEBUG record per dropped key
per object, naming the class and the key and **never the value** — a document
dropping the same key on five cues emits five records and zero extra INFO.

The third case here is the one most likely to be got wrong in implementation:
``ui_properties`` is **wildcard** content, declared nowhere, and filtering it by
the declared-field rule would delete real editor state for every cue in every
project.
"""

from __future__ import annotations

import json
import logging
import warnings

import pytest

from cuemsutils.cues.AudioCue import AudioCue
from cuemsutils.cues.CuemsScript import CuemsScript
from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, by_relpath

SCRIPT_DOC = next(d for d in DOCUMENTS if d.schema == "script")
COMPLEX = "cuems-engine/projects/complex_test/script.xml"

STRAY = "not_a_declared_field"
STRAY_VALUE = "leaked-value-that-must-not-appear"


def xml_of(obj) -> str:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return rt.write_bytes(SCRIPT_DOC, obj).decode()


def json_of(obj):
    return json.loads(json.dumps(obj))


@pytest.fixture
def script_with_a_stray_key():
    obj = rt.read_objects(by_relpath(COMPLEX))
    dict.__setitem__(obj, STRAY, STRAY_VALUE)
    return obj


@pytest.fixture
def cue_with_a_stray_key():
    obj = rt.read_objects(by_relpath(COMPLEX))
    cue = obj["CueList"]["contents"][0]
    dict.__setitem__(cue, STRAY, STRAY_VALUE)
    return obj, cue


# --- the root: today's leak ------------------------------------------------


def test_a_stray_key_on_the_root_is_absent_from_the_xml(script_with_a_stray_key):
    """FR-019 row 6 — the root filters to declared fields, as cues already do."""
    assert STRAY not in xml_of(script_with_a_stray_key)
    assert STRAY_VALUE not in xml_of(script_with_a_stray_key)


def test_a_stray_key_on_the_root_is_absent_from_the_json(script_with_a_stray_key):
    payload = json_of(script_with_a_stray_key)
    assert STRAY not in payload


def test_a_stray_key_on_the_root_does_not_reach_items(script_with_a_stray_key):
    assert STRAY not in dict(script_with_a_stray_key.items())


# --- a cue: today's behaviour, which must not change -----------------------


def test_a_stray_key_on_a_cue_is_absent_from_both_projections(cue_with_a_stray_key):
    """Already true today. Asserted so the unification does not lose it."""
    obj, _ = cue_with_a_stray_key
    assert STRAY not in xml_of(obj)
    assert STRAY not in json.dumps(json_of(obj))


def test_the_root_and_a_cue_produce_the_same_outcome(
    script_with_a_stray_key, cue_with_a_stray_key
):
    """SC-004 — one rule, one outcome, whichever object carries the key."""
    root_obj = script_with_a_stray_key
    cue_obj, _ = cue_with_a_stray_key
    assert (STRAY in xml_of(root_obj)) == (STRAY in xml_of(cue_obj))
    assert (STRAY in json.dumps(json_of(root_obj))) == (
        STRAY in json.dumps(json_of(cue_obj))
    )


# --- the log record --------------------------------------------------------


def test_dropping_a_key_emits_exactly_one_debug_record_naming_class_and_key(
    script_with_a_stray_key, caplog
):
    """FR-015a — one record per dropped key per object, value never included."""
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        xml_of(script_with_a_stray_key)

    matching = [r for r in caplog.records if STRAY in r.getMessage()]
    assert len(matching) == 1, (
        f"{len(matching)} records mention the dropped key, expected 1:\n  "
        + "\n  ".join(r.getMessage() for r in matching)
    )
    record = matching[0]
    assert record.levelno == logging.DEBUG
    assert "CuemsScript" in record.getMessage()
    assert STRAY_VALUE not in record.getMessage(), "the log record leaked the value"


def test_the_same_key_on_many_cues_emits_one_record_each(caplog):
    """The arithmetic FR-015a states: N objects dropping a key -> N records."""
    obj = rt.read_objects(by_relpath(COMPLEX))
    cues = obj["CueList"]["contents"]
    for cue in cues:
        dict.__setitem__(cue, STRAY, STRAY_VALUE)

    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        xml_of(obj)

    matching = [r for r in caplog.records if STRAY in r.getMessage()]
    assert len(matching) == len(cues)
    assert all(r.levelno == logging.DEBUG for r in matching)


def test_dropping_keys_adds_no_info_records(script_with_a_stray_key, caplog):
    """004's INFO budget is untouched — that is what keeps it intact."""
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        xml_of(script_with_a_stray_key)

    info = [r for r in caplog.records if r.levelno >= logging.INFO]
    assert not [r for r in info if STRAY in r.getMessage()]


# --- the exemption that must hold -----------------------------------------


def test_wildcard_ui_properties_content_is_not_filtered():
    """``ui_properties`` is wildcard content — declared nowhere, kept entirely.

    Filtering it by the declared-field rule would delete real editor state for
    every cue in every project. This is the single most damaging way to get
    T019 wrong, and the goldens would catch it only as a byte diff.
    """
    obj = rt.read_objects(by_relpath(COMPLEX))
    cue = obj["CueList"]["contents"][0]
    ui = cue.get("ui_properties")
    assert ui, "the fixture document has no ui_properties to protect"

    ui["a_brand_new_editor_key"] = "kept"
    rendered = xml_of(obj)
    assert "a_brand_new_editor_key" in rendered
    assert "kept" in rendered


def test_declared_fields_are_not_dropped():
    """The obvious inverse, which a too-aggressive filter would break."""
    obj = rt.read_objects(by_relpath(COMPLEX))
    rendered = xml_of(obj)
    for field in ("name", "description", "created", "modified"):
        assert f"<{field}>" in rendered or f"<{field} />" in rendered


def test_a_built_object_filters_the_same_way():
    """The rule is the model's, so it holds off the decode path too."""
    cue = AudioCue({"name": "probe"})
    dict.__setitem__(cue, STRAY, STRAY_VALUE)
    assert STRAY not in dict(cue.items())

    script = CuemsScript({"name": "probe"})
    dict.__setitem__(script, STRAY, STRAY_VALUE)
    assert STRAY not in dict(script.items())
