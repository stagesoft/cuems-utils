"""Contract C11 (T049a) — the one declared breaking change, pinned.

Every other contract in this feature asserts that something did **not** change.
This one asserts that something **did**, and that it changed exactly as
declared (FR-026d, SC-017).

``cuems-nodeconf`` registers its node handlers by writing into this library's
private module namespaces (`NodeXmlBuilders.py:105-111`)::

    XmlBuilderModule.nodeXmlBuilder = nodeXmlBuilder
    ParsersModule.nodeParser        = nodeParser

``CuemsParser.get_parser_class`` and ``XmlBuilder.get_builder_class`` resolved
handlers through ``globals()`` of their own module, so an injected name was
found. Every path now routes through the explicit registry, and an injected
name is never consulted.

**Why this needs a test rather than a release note.** Nothing raises. The
imports still resolve, the assignments still execute, and the node simply
serializes through a generic instead of through ``nodeXmlBuilder``. A break
that is loud gets noticed; this one is silent, which is exactly why it is
asserted.

No shim can preserve it: honouring an injected name means keeping the implicit
lookup FR-007 exists to delete. **The `cuems-nodeconf` fix is carried by
feature 007** — see `specs/004-xml-serialization-core/migration-map.md` §3.
"""

from __future__ import annotations

import warnings

import pytest

import cuemsutils.xml.Parsers as ParsersModule
import cuemsutils.xml.XmlBuilder as XmlBuilderModule
from cuemsutils.xml.registry import get_registry
from tests.support import roundtrip as rt
from tests.support.corpus import by_relpath

SCRIPT = "cuems-editor/script_minimal.xml"


class _InjectedParser:
    """Stands in for `cuems-nodeconf`'s ``nodeParser``.

    Records whether it was consulted, which is the only observable this break
    has.
    """

    was_used = False

    def __init__(self, init_dict=None, class_string=None, **kwargs):
        type(self).was_used = True
        self.init_dict = init_dict

    def parse(self):
        return {"injected": True}


class _InjectedBuilder:
    was_used = False

    def __init__(self, _object=None, xml_tree=None, **kwargs):
        type(self).was_used = True

    def build(self):
        return None


@pytest.fixture
def injected(monkeypatch):
    """Reproduce the nodeconf injection, and undo it afterwards."""
    _InjectedParser.was_used = False
    _InjectedBuilder.was_used = False
    monkeypatch.setattr(
        ParsersModule, "AudioCueParser", _InjectedParser, raising=False
    )
    monkeypatch.setattr(
        XmlBuilderModule, "AudioCueXmlBuilder", _InjectedBuilder, raising=False
    )
    yield
    _InjectedParser.was_used = False
    _InjectedBuilder.was_used = False


def test_the_injection_still_imports_and_assigns_without_error(injected):
    """What does **not** break, stated first.

    The consumer's module still imports, and its four assignments still
    execute. Only their effect is gone — which is the entire reason this
    contract exists.
    """
    assert ParsersModule.AudioCueParser is _InjectedParser
    assert XmlBuilderModule.AudioCueXmlBuilder is _InjectedBuilder


def test_injected_parser_is_not_consulted_on_decode(injected):
    doc = by_relpath(SCRIPT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rt.read_objects(doc)
    assert _InjectedParser.was_used is False


def test_injected_builder_is_not_consulted_on_encode(injected):
    doc = by_relpath(SCRIPT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        rt.write_bytes(doc, rt.read_objects(doc))
    assert _InjectedBuilder.was_used is False


def test_the_registry_resolves_the_type_instead(injected):
    """The positive half: something else did the work, and it is the registry.

    Without this, "the injection was not used" would also pass if nothing had
    been serialized at all.
    """
    from cuemsutils.cues.AudioCue import AudioCue

    assert get_registry("script").model_for("AudioCueType") is AudioCue

    doc = by_relpath(SCRIPT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        obj = rt.read_objects(doc)

    cues = obj["CueList"]["contents"]
    assert any(type(cue) is AudioCue for cue in cues)
    assert not any(isinstance(cue, dict) and cue.get("injected") for cue in cues)


def test_output_is_unaffected_by_the_injection(injected):
    """The break costs nothing in output terms.

    A consumer that injects a handler gets the registry's result, which for
    every type the library itself knows is the same bytes it would produce
    anyway. What is lost is the ability to override — and that is the declared
    change.
    """
    doc = by_relpath(SCRIPT)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        produced = rt.write_bytes(doc, rt.read_objects(doc))
    assert produced == rt.golden_bytes(f"xml/{doc.slug}.xml")


def test_no_public_registration_hook_replaces_it():
    """The break is not softened by a new injection point.

    D11 + Q14: nothing external owns a model in this feature. A consumer
    needing one waits for the public registry in feature 006 — offering a
    half-API here would have to be supported forever.
    """
    import cuemsutils.xml.registry as registry_module

    for name in ("register", "register_binding", "bind", "add_binding"):
        assert not hasattr(registry_module, name)
