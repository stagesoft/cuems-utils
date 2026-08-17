"""Logging budget (T061) — SC-014, FR-033, FR-034.

The one intentional, non-breaking behaviour difference in this feature. XML
bytes and the read dict are byte-identical; log output is explicitly outside
that guarantee (FR-032), and it changes in two ways.

**INFO scales with files touched, not with content.** It is declared at the
level of XML file access — read, write, validate. Element construction, object
building and per-cue work sit at DEBUG or below. A 1000-cue script is one file
and produces a single-digit number of INFO records; before, the builder emitted
two INFO lines per cue and per nested dict.

**No record carries a field value or an object repr.** That is a privacy
property as much as a tidiness one: the old records put cue names, media file
paths and whole node-mapping dicts into the system log. Show content does not
belong there.
"""

from __future__ import annotations

import logging
import warnings

import pytest

from tests.support import roundtrip as rt
from tests.support.corpus import by_relpath

SCRIPT = "cuems-editor/script_minimal.xml"
COMPLEX = "cuems-engine/projects/complex_test/script.xml"

#: Values that appear in the corpus and must never reach a log record.
FIELD_VALUES = (
    "sposa_non_mi_conosci",  # a media file name
    "Test Main Script",  # a script name
    "Main cuelist desc",  # a description
    "system:playback_1",  # an output routing name
)


def _records(caplog, level=logging.INFO):
    return [r for r in caplog.records if r.levelno >= level]


def test_reading_a_document_emits_a_single_digit_number_of_info_records(caplog):
    doc = by_relpath(SCRIPT)
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rt.read_objects(doc)
    assert len(_records(caplog)) < 10


def test_writing_a_document_emits_a_single_digit_number_of_info_records(caplog):
    doc = by_relpath(SCRIPT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(doc)
    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        rt.write_bytes(doc, obj)
    assert len(_records(caplog)) < 10


def test_info_count_does_not_grow_with_cue_count(caplog):
    """The property, stated as a comparison rather than a threshold.

    ``complex_test/script.xml`` holds many more cues than
    ``script_minimal.xml``. If INFO scaled with content the two counts would
    differ; a fixed budget could be met by a large constant and would not
    catch per-cue logging creeping back in.
    """
    counts = {}
    for relpath in (SCRIPT, COMPLEX):
        caplog.clear()
        with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
            warnings.simplefilter("ignore")
            doc = by_relpath(relpath)
            rt.write_bytes(doc, rt.read_objects(doc))
        counts[relpath] = len(_records(caplog))
    assert counts[SCRIPT] == counts[COMPLEX], counts


def test_a_thousand_cue_script_stays_in_single_digits(caplog):
    """SC-014 at the scale the requirement names."""
    from cuemsutils.cues.ActionCue import ActionCue

    doc = by_relpath(SCRIPT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(doc)
        contents = obj["CueList"]["contents"]
        template = next(c for c in contents if type(c) is ActionCue)
        for _ in range(1000):
            contents.append(template)

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        rt.write_bytes(doc, obj)
    assert len(_records(caplog)) < 10


@pytest.mark.parametrize("relpath", [SCRIPT, COMPLEX])
def test_no_record_at_any_level_carries_a_field_value(caplog, relpath):
    """FR-033 — identifiers only, never values.

    Checked at **DEBUG**, not just INFO: dropping show content to a lower
    level still writes it to a log file whenever debug logging is on, which is
    exactly when an operator is capturing output to send somewhere.
    """
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = by_relpath(relpath)
        rt.write_bytes(doc, rt.read_objects(doc))

    engine_records = [
        r for r in caplog.records if r.name.startswith("cuemsutils.xml")
    ]
    for record in engine_records:
        text = record.getMessage()
        for value in FIELD_VALUES:
            assert value not in text, f"{record.name}: {text[:160]}"


@pytest.mark.parametrize("relpath", [SCRIPT, COMPLEX])
def test_no_record_carries_an_object_repr(caplog, relpath):
    """A dict or object repr in a message is a field-value leak by another name.

    ``process_network_mappings`` used to log the entire mappings dict at INFO —
    every node's uuid, name, ip and output routing — once per project load.
    """
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        doc = by_relpath(relpath)
        rt.write_bytes(doc, rt.read_objects(doc))

    for record in caplog.records:
        if not record.name.startswith("cuemsutils.xml"):
            continue
        text = record.getMessage()
        assert "{'" not in text, f"dict repr in {record.name}: {text[:160]}"
        assert " object at 0x" not in text


def test_internally_built_elements_emit_nothing_above_debug(caplog):
    """Building a document in memory touches no file, so it logs no INFO."""
    from xml.etree.ElementTree import Element

    from cuemsutils.xml.mapper import Mapper
    from cuemsutils.xml.spec import derive_path

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(by_relpath(SCRIPT))

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        Mapper("script").encode_xml(
            obj,
            derive_path("script", "CuemsProject/CuemsScript"),
            Element("root"),
            "CuemsScript",
        )
    assert _records(caplog) == []


def test_read_and_write_log_at_the_same_level(caplog):
    """FR-034 — consistent between directions.

    They were not before: the write path logged INFO per cue while the read
    path was silent, so the same document produced wildly different output
    depending on which way it was going.
    """
    doc = by_relpath(SCRIPT)
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(doc)
    read_count = len(_records(caplog))

    caplog.clear()
    with caplog.at_level(logging.DEBUG):
        rt.write_bytes(doc, obj)
    write_count = len(_records(caplog))

    assert abs(read_count - write_count) <= 2, (read_count, write_count)


# --- feature 005 addition (T020, FR-015a) ---------------------------------
#
# Additive only: no assertion above changes. The drop-and-log record for
# undeclared keys must not be able to push the budget the rest of this file
# defends.

STRAY = "not_a_declared_field"


def test_dropped_keys_emit_debug_records_and_no_info_records(caplog):
    """The arithmetic FR-015a states, asserted as arithmetic.

    A document dropping the same key on N objects emits **N DEBUG records and
    zero additional INFO records**. That is what keeps 004's budget — INFO
    scales with files touched, not with content — intact while adding a
    per-object record.
    """
    doc = by_relpath(COMPLEX)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(doc)

    cues = obj["CueList"]["contents"]
    for cue in cues:
        dict.__setitem__(cue, STRAY, "value-that-must-not-be-logged")

    caplog.clear()
    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rt.write_bytes(doc, obj)

    dropped = [r for r in caplog.records if STRAY in r.getMessage()]
    assert len(dropped) == len(cues), (
        f"{len(dropped)} drop records for {len(cues)} objects carrying the key"
    )
    assert all(r.levelno == logging.DEBUG for r in dropped)

    # The INFO budget is untouched: no drop record is INFO or above.
    assert not [r for r in dropped if r.levelno >= logging.INFO]
    assert len(_records(caplog)) < 10


def test_a_drop_record_never_carries_the_value(caplog):
    """FR-015a and FR-033 — the class and the key, never the content.

    Show content does not belong in a system log, and a dropped key's *value*
    is show content by definition.
    """
    doc = by_relpath(COMPLEX)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(doc)

    secret = "sposa_non_mi_conosci_secret_payload"
    dict.__setitem__(obj, STRAY, secret)

    with caplog.at_level(logging.DEBUG), warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rt.write_bytes(doc, obj)

    dropped = [r for r in caplog.records if STRAY in r.getMessage()]
    assert len(dropped) == 1
    assert "CuemsScript" in dropped[0].getMessage()
    assert secret not in dropped[0].getMessage()
