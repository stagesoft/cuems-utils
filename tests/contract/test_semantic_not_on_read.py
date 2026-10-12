"""FR-037, FR-038 (feature 008, ITEM E) — **reading now becomes stricter**.

This file pinned the opposite standing principle through feature 006
(FR-026/SC-016 there): "reading never becomes stricter", decided by measuring
that none of the fourteen setter rules would reject a value the load path
actually produced. That measurement is superseded, not wrong for its time —
feature 008 makes the **deliberate, recorded** reversal (FR-038): the public
show load surface and every configuration accessor now run **both** tiers,
T1 and T2, on every read (FR-037). ``CuemsScript.load``'s own docstring
records the same reversal at its call site.

The reversal is not "run every rule against the read path and see what
breaks" — it composes with ITEM D's descriptor and ITEM E's repair-and-notify
(US7): a **repairable** violation loads anyway, silently corrected to the
descriptor's default; only an **unrepairable** one raises. This file's fixture
is deliberately the latter (``fade_duration_positive`` is declared
``repairable=False`` in ``xml/validators.py`` — "no value both satisfies
positive-and-non-zero and carries no meaning of its own" — so there is no
default to repair it to), which is what lets this module keep demonstrating a
document that "loads" under the old principle and now does not, rather than
needing a second fixture to cover the newly-added repair path (that path has
its own tests in ``tests/integration/test_repair.py``).
"""

from __future__ import annotations

import sys

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.errors import ValidationError
from tests.support import invalid_scripts as broken
from tests.support.corpus import loadable_script_documents
from tests.support.public_api import assert_no_xml_import

SCRIPT_DOCS = loadable_script_documents()
IDS = [d.relpath for d in SCRIPT_DOCS]


@pytest.fixture(scope="module")
def semantically_invalid_document(tmp_path_factory):
    """A document on disk that is structurally valid and semantically wrong,
    in a field the descriptor classifies **unrepairable**.

    **A zero-duration fade**, not an off-canvas region, and the choice is
    load-bearing. ``VideoCueOutputsType`` is an ``OPAQUE_TYPE``, so decoding
    an output calls ``VideoCueOutput.__init__`` — which runs the containment
    check itself, at construction, before ``super().__init__``. That
    constructor call is what pins two legacy corpus documents as
    ``to_objects: error`` (FR-024d, T074), so an off-canvas region is rejected
    *on read* for a different reason and cannot demonstrate anything about
    ITEM E's T2-on-load tier specifically.

    ``FadeCue.duration`` has no such constructor: the ``fade_duration_positive``
    rule lives in ``FadeCue.set_duration``, decode does not run setters, and
    ``script.xsd``'s ``CTimecodeType`` only constrains the lexical *shape* of a
    timecode, not its sign — ``00:00:00.000`` is a perfectly valid
    ``CTimecodeType`` value. So the document decodes without complaint and it
    is ITEM E's new T2-on-load tier that objects — which is precisely the
    behaviour FR-037/FR-038 add.

    (Feature 008, FR-007a: the original fixture used duplicate fade profile
    types, via ``fade_profile_caps``. That rule and the surface it validated
    are deleted; this is the same shape of case on a rule that survives.)

    Written by hand-editing the *tree*, because ``save()`` would refuse it.
    """
    from cuemsutils.xml.documents import build_tree, write_tree
    from tests.support.corpus import by_relpath

    script = CuemsScript.load(by_relpath("cuems-utils/fade_showcase.xml").path)
    from cuemsutils.cues.FadeCue import FadeCue
    from cuemsutils.tools.CTimecode import CTimecode

    cue = next(c for c in script.cuelist.contents if isinstance(c, FadeCue))
    # Zero, not ``None`` — ``fade_duration_positive`` treats ``None`` as
    # "not set yet" and only rejects a duration that parses to zero.
    dict.__setitem__(cue, "duration", CTimecode("00:00:00.000"))

    target = tmp_path_factory.mktemp("semantic") / "show.xml"
    write_tree(build_tree(script, "script"), target)
    return target


def test_the_fixture_really_is_semantically_invalid(semantically_invalid_document):
    """The control: without it, "load() raises" could mean "the file is
    unreadable", not "the T2 tier caught something real". Bypasses
    ``load()``'s new strictness on purpose, via the tree-building path
    ``validate()`` itself uses, so this assertion does not depend on the
    behaviour under test."""
    from cuemsutils.xml.documents import read_document

    script = CuemsScript._decode(read_document("script", semantically_invalid_document))
    assert script.validate()


def test_an_unrepairable_semantically_invalid_document_raises_on_load(
    semantically_invalid_document,
):
    """The reversal's headline case (FR-037, FR-038, FR-044): a document that
    used to load and only fail on ``save()`` now fails at ``load()``, because
    the violated field has no descriptor default to repair it to."""
    with pytest.raises(ValidationError):
        CuemsScript.load(semantically_invalid_document)


def test_it_fails_on_load_and_would_still_fail_on_save(
    semantically_invalid_document, tmp_path
):
    """``save()``'s own T2 check is unchanged by this feature — it would
    still refuse the object, if a caller ever got one to call it on by
    bypassing ``load()``."""
    with pytest.raises(ValidationError):
        CuemsScript.load(semantically_invalid_document)

    from cuemsutils.xml.documents import read_document

    script = CuemsScript._decode(read_document("script", semantically_invalid_document))
    with pytest.raises(ValidationError):
        script.save(tmp_path / "out.xml")


def test_from_json_runs_no_semantic_rule(semantically_invalid_document):
    """``from_json`` is **not** part of FR-037's reversal (contracts §2 names
    only ``load``/``load_with_report``) — the editor's ingestion path keeps
    its existing, decode-time-only posture, unchanged by this feature."""
    from cuemsutils.xml.documents import read_document

    script = CuemsScript._decode(read_document("script", semantically_invalid_document))
    payload = script.to_json()
    rebuilt = CuemsScript.from_json(payload)
    assert rebuilt is not None
    assert rebuilt.validate(), "the rebuilt script lost the violation, not the check"


def test_load_now_runs_the_tier(monkeypatch, semantically_invalid_document):
    """Counted, not inferred — the reversal's other half.

    Feature 006 counted invocations to prove the tier was **off**; feature 008
    counts them to prove it is now **on**. ``load()``'s repair path
    (``xml.validators.repair``) walks T2 findings directly rather than calling
    ``run_rules`` (which stays reserved for ``validate()``/``save()``'s
    collect-everything and stop-at-first postures), so this counts calls to
    the shared primitive both go through: ``_iter_t2_findings``.
    """
    from cuemsutils.xml import validators

    calls: list[str] = []
    original = validators._iter_t2_findings

    def _counted(obj):
        calls.append("run")
        return original(obj)

    monkeypatch.setattr(validators, "_iter_t2_findings", _counted)

    with pytest.raises(ValidationError):
        CuemsScript.load(semantically_invalid_document)
    assert calls == ["run"], "load() did not invoke the semantic tier"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_every_corpus_document_still_loads(doc):
    """No corpus document regresses under the new strictness — every one of
    them is either clean or repairable, none carries this fixture's
    unrepairable shape."""
    assert CuemsScript.load(doc.path) is not None


def test_validate_does_run_the_tier():
    """The other half. A tier that never runs anywhere would pass every test
    above and be worthless."""
    report = broken.semantically_invalid().validate()
    assert [v for v in report if v.tier == "T2"]


def test_the_module_under_test_names_only_the_document_helper():
    """The fixture reaches into ``xml.documents`` to write a file ``save()``
    would refuse. Stated rather than swept, because it is the one import here
    that is not the public surface."""
    from tests.support.public_api import imported_modules

    named = {
        n
        for n in imported_modules(sys.modules[__name__])
        if n.startswith("cuemsutils.xml")
    }
    roots = {
        ".".join(name.split(".")[:3])
        for name in named
        if name.count(".") >= 2
    }
    assert roots <= {
        "cuemsutils.xml.validators",
        "cuemsutils.xml.documents",
    }, roots


def test_the_public_leg_names_nothing_from_the_xml_package():
    import tests.contract.test_projection_does_not_validate as public_leg

    assert_no_xml_import(public_leg)
