"""FR-026, SC-016 (T068) — **reading never becomes stricter**.

This is the feature's second required decision stop, and it was answered with
measurement rather than judgement: a corpus sweep, per rule, re-invoking each
value-rejecting setter against the values the load path actually produces
(``specs/006-public-object-api/corpus-sweep.md``).

The answer was split, and that split is why the tier runs where it does:

* of the fourteen setter rules, **none** would reject anything the library
  accepts today — six proven against real values, eight unproven for lack of a
  fade document in the corpus;
* the fifteenth — the uuid4 shape check — **would**, three times in one
  ordinary editor payload, on the nil ``Media.id`` the editor sends for media
  that has no id yet.

So T2 runs on ``save()`` and ``validate()`` **only**. A document that violates
a semantic rule loads; it fails when someone tries to persist it. That keeps
the read path exactly as permissive as it is today, which is what FR-025's
accept/reject parity requires, and it is why the uuid rule stayed a *coercion*
concern rather than joining the registry (T070).
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
    """A document on disk that is structurally valid and semantically wrong.

    **A zero-duration fade**, not an off-canvas region, and the choice is
    load-bearing. ``VideoCueOutputsType`` is an ``OPAQUE_TYPE``, so decoding
    an output calls ``VideoCueOutput.__init__`` — which runs the containment
    check itself, at construction, before ``super().__init__``. That
    constructor call is what pins two legacy corpus documents as
    ``to_objects: error`` (FR-024d, T074), so an off-canvas region is rejected
    *on read* and cannot demonstrate anything about the write tier.

    ``FadeCue.duration`` has no such constructor: the ``fade_duration_positive``
    rule lives in ``FadeCue.set_duration``, decode does not run setters, and
    ``script.xsd``'s ``CTimecodeType`` only constrains the lexical *shape* of a
    timecode, not its sign — ``00:00:00.000`` is a perfectly valid
    ``CTimecodeType`` value. So the document loads and only ``save()`` objects
    — which is precisely the behaviour FR-026 specifies.

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
    """The control: without it, "it loads" could mean "it is fine"."""
    assert CuemsScript.load(semantically_invalid_document).validate()


def test_a_semantically_invalid_document_loads(semantically_invalid_document):
    script = CuemsScript.load(semantically_invalid_document)
    assert script is not None
    assert script.cuelist.contents


def test_it_fails_only_on_save(semantically_invalid_document, tmp_path):
    script = CuemsScript.load(semantically_invalid_document)
    with pytest.raises(ValidationError):
        script.save(tmp_path / "out.xml")


def test_from_json_runs_no_semantic_rule(semantically_invalid_document):
    payload = CuemsScript.load(semantically_invalid_document).to_json()
    rebuilt = CuemsScript.from_json(payload)
    assert rebuilt is not None
    assert rebuilt.validate(), "the rebuilt script lost the violation, not the check"


def test_load_runs_zero_rules(monkeypatch, semantically_invalid_document):
    """Counted, not inferred.

    "It loaded, so no rule rejected it" is weaker than it looks: a rule that
    ran and *passed* would also load. Counting invocations distinguishes "the
    tier is off on read" from "the tier happened to agree".
    """
    from cuemsutils.xml import validators

    calls: list[str] = []
    original = validators.run_rules
    monkeypatch.setattr(
        validators, "run_rules", lambda obj: calls.append("run") or original(obj)
    )

    CuemsScript.load(semantically_invalid_document)
    assert calls == [], "load() invoked the semantic tier"


@pytest.mark.parametrize("doc", SCRIPT_DOCS, ids=IDS)
def test_every_corpus_document_still_loads(doc):
    """FR-025 over the corpus: reading is no stricter than it was."""
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
