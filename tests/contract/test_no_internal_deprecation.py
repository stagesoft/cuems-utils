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


def test_the_editor_json_path_is_now_a_deprecated_entry_point():
    """``CuemsParser`` was the one supported symbol in ``Parsers.py``; it is
    now the **sixth retired entry point** (contract C3, T061).

    Until feature 006 this test asserted the opposite — silence — and it was
    right to: ``CuemsParser`` was not a retired path but the engine's
    delegating facade, and the *library itself* called it from
    ``write_from_dict`` and ``read_to_objects``. Deprecating it then would have
    failed C8 on the library's own traffic.

    T061a moved both internal callers to ``Mapper.decode_document`` first, so
    C8 is **satisfied** rather than amended: nothing internal reaches it, and
    the shim can finally say so to the five ``cuems-editor`` call sites that
    do.

    The warning lives at ``cuemsutils.xml.CuemsParser``, where consumers import
    it. The class in ``Parsers.py`` is undecorated, so ``xml/__init__.py``'s
    own import of it stays silent.
    """
    import cuemsutils.xml as xml_package

    doc = next(d for d in DOCUMENTS if d.schema == "script")
    payload = {"CuemsScript": json.loads(json.dumps(rt.read_objects(doc)))}

    def run():
        xml_package.CuemsParser(payload).parse()

    records = _deprecations(run)
    assert records, "the retired entry point no longer warns"
    assert any("from_json" in record for record in records), records


def test_the_undecorated_class_is_what_the_library_would_have_imported():
    """The other half: importing ``Parsers.CuemsParser`` is silent.

    A warning on the class itself would fire for ``xml/__init__.py``'s own
    import — deprecating the shim's own source — which is the mistake the
    module-level note in ``Parsers.py`` exists to prevent.
    """

    def run():
        doc = next(d for d in DOCUMENTS if d.schema == "script")
        CuemsParser({"CuemsScript": json.loads(json.dumps(rt.read_objects(doc)))})

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
    ["str_to_value", "GenericDict", "STRING_TYPED_KEYS"],
    ids=["type-guessing heuristic", "generic dict", "the denylist"],
)
def test_named_frozen_symbols_still_exist_but_are_unreached(symbol, corpus_deprecations):
    """FR-002/FR-003 — they survive as shims, and nothing live touches them.

    Asserting existence *and* silence together is the point: either half alone
    is satisfiable by deleting the symbol, which would break the consumers the
    shims exist for.

    ``GenericParser`` **left this list in feature 006** and is gone, with the
    other fifteen frozen ``*Parser`` classes (T063). Their unreachability was
    measured under coverage before deletion — ``legacy-coverage.md`` — and
    ``CuemsParser.parse()``'s own docstring named this feature as the one that
    would remove them.

    Three symbols survive, each for a reason rather than by omission:
    ``str_to_value`` and ``STRING_TYPED_KEYS`` are the retired heuristic and
    the denylist that held its damage back, read by ``test_name_coercion`` to
    assert the defect class is unrepresentable rather than merely unreached;
    ``GenericDict`` is imported by ``XmlBuilder.py``, so deleting it would
    break that frozen shim's *import*, not just its behaviour.
    """
    import cuemsutils.xml.Parsers as parsers

    assert hasattr(parsers, symbol) or hasattr(parsers.CuemsParser, symbol)
    assert corpus_deprecations == []


def test_the_deleted_parser_tree_is_actually_gone():
    """T063, stated positively so "unreached" cannot quietly mean "still there".

    Naming them individually rather than counting: a count would pass if one
    were reintroduced while another was deleted.
    """
    import cuemsutils.xml.Parsers as parsers

    for name in (
        "CuemsScriptParser",
        "CueListParser",
        "GenericParser",
        "GenericSubObjectParser",
        "CTimecodeParser",
        "mediaParser",
        "outputsParser",
        "CuemsNodeDictParser",
        "AudioCueOutputParser",
        "VideoCueOutputParser",
        "DmxCueOutputParser",
        "DmxCueParser",
        "fade_profilesParser",
        "fade_profileParser",
        "NoneTypeParser",
    ):
        assert not hasattr(parsers, name), f"{name} survived T063"


def test_the_ordering_hack_is_unreached(corpus_deprecations):
    """FR-002 — the ``master_vol``/``opacity`` branch is gone outright now.

    It used to live in ``MediaCueXmlBuilder.build``, frozen behind the
    deprecated ``XmlBuilder`` class, so reaching it during a write would have
    shown up as a deprecation warning from ``XmlBuilder.py``. Feature 008
    (FR-007a) deletes the branch and the ``FadeProfileXmlBuilder`` it called,
    rather than leaving them frozen-but-unreachable like the rest of that
    module — there is nothing left for either to build. This assertion is
    kept as a regression guard: the corpus must still emit no such warning.
    """
    offenders = [line for line in corpus_deprecations if "XmlBuilder" in line]
    assert not offenders
