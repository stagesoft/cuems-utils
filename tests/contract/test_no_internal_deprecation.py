"""Contract C8 (T062) — no internal caller of a deprecated symbol.

This is what keeps the softened wording of FR-002 and FR-003 honest. The old
ordering hack and the type-guessing heuristic still **exist**, frozen in
``XmlBuilder.py`` and ``Parsers.py`` for external callers until feature 007
removes them. "Not reachable from any live path" is therefore a claim about
what the library does, not about what its source contains — and every one of
those symbols warns on call, so running the whole corpus through the public
entry points and counting warnings measures exactly that claim.

``CuemsParser`` is included on purpose. It is a **supported** entry point, not
a deprecated one (Assumption 3a, FR-026d), and it is `cuems-editor`'s primary
JSON → object path — so it must stay silent here. Exercising it is exercising
the library's own path: ``XmlReaderWriter.write_from_dict`` and
``read_to_objects`` both call it.
"""

from __future__ import annotations

import json
import warnings

import pytest

from cuemsutils.xml.Parsers import CuemsParser
from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT

OUTCOMES = json.loads((GOLDEN_ROOT / "outcomes.json").read_text())


def _deprecations(fn):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        fn()
    return [
        f"{w.filename.split('/')[-1]}:{w.lineno} {w.message}"
        for w in caught
        if issubclass(w.category, DeprecationWarning)
    ]


def _run_full_corpus_through_public_entry_points():
    for doc in DOCUMENTS:
        record = OUTCOMES[doc.relpath]
        if not record["read"]["ok"]:
            continue
        rt.read_dict(doc)
        if doc.config_class:
            rt.read_config_dict(doc)
        if not record["to_objects"]["ok"]:
            continue
        obj = rt.read_objects(doc)
        if record.get("write", {}).get("ok"):
            rt.write_bytes(doc, obj)


@pytest.fixture(scope="module")
def corpus_deprecations():
    """The full corpus run **once** per module.

    Five assertions below read the same measurement. Re-running the whole
    corpus for each would cost about six seconds and tell us nothing five
    times.
    """
    return _deprecations(_run_full_corpus_through_public_entry_points)


def test_the_whole_corpus_emits_no_deprecation_warning(corpus_deprecations):
    assert corpus_deprecations == []


def test_the_generated_document_path_emits_none():
    def run():
        doc = next(d for d in DOCUMENTS if d.schema == "script")
        rt.write_bytes(doc, rt.build_generated_script())

    assert _deprecations(run) == []


def test_the_editor_json_path_emits_none():
    """``CuemsParser`` is supported and must stay silent (FR-026d).

    A warning here would fail C8 by design — which is why the migration map
    names it as the one symbol in ``Parsers.py`` that is not deprecated.
    """

    def run():
        doc = next(d for d in DOCUMENTS if d.schema == "script")
        obj = rt.read_objects(doc)
        CuemsParser({"CuemsScript": json.loads(json.dumps(obj))}).parse()

    assert _deprecations(run) == []


def test_write_from_dict_emits_none(tmp_path):
    """The other library-internal ``CuemsParser`` caller."""
    from cuemsutils.xml.xml_reader_writer import XmlReaderWriter

    doc = next(d for d in DOCUMENTS if d.schema == "script")
    payload = json.loads(json.dumps(rt.read_objects(doc)))

    def run():
        writer = XmlReaderWriter(
            schema_name="script", xmlfile=str(tmp_path / "out.xml")
        )
        writer.write_from_dict({"CuemsScript": payload})

    assert _deprecations(run) == []


def test_the_frozen_symbols_would_have_warned_if_reached():
    """The control, without which the assertions above prove nothing.

    A suite that emits zero deprecation warnings because the *warnings* are
    broken looks identical to one that emits zero because nothing deprecated
    is reached. Calling a frozen symbol directly distinguishes the two.
    """
    from cuemsutils.xml.Parsers import GenericDict

    assert _deprecations(GenericDict)


@pytest.mark.parametrize(
    "symbol",
    ["str_to_value", "GenericParser", "GenericDict"],
    ids=["type-guessing heuristic", "generic parser", "generic dict"],
)
def test_named_frozen_symbols_still_exist_but_are_unreached(symbol, corpus_deprecations):
    """FR-002/FR-003 — they survive as shims, and nothing live touches them.

    Asserting existence *and* silence together is the point: either half alone
    is satisfiable by deleting the symbol, which would break the consumers the
    shims exist for.
    """
    import cuemsutils.xml.Parsers as parsers

    assert hasattr(parsers, symbol) or hasattr(parsers.CuemsParser, symbol)
    assert corpus_deprecations == []


def test_the_ordering_hack_is_unreached(corpus_deprecations):
    """FR-002 — the ``master_vol``/``opacity`` branch still exists, frozen.

    It lives in ``MediaCueXmlBuilder.build``, whose class is deprecated, so
    reaching it during a write would show up as a deprecation warning from
    ``XmlBuilder.py``. T036 separately asserts the branch does not exist in any
    live engine module.
    """
    offenders = [line for line in corpus_deprecations if "XmlBuilder" in line]
    assert not offenders
