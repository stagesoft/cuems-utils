"""Contract C7 (T049a, repaired by feature 007) — the declared break, closed.

**What this file asserted through feature 006.** ``cuems-nodeconf`` registered
its node handlers by writing into this library's private module namespaces
(``NodeXmlBuilders.py:105-111``)::

    XmlBuilderModule.nodeXmlBuilder = nodeXmlBuilder
    ParsersModule.nodeParser        = nodeParser

``CuemsParser.get_parser_class`` and ``XmlBuilder.get_builder_class`` resolved
handlers through ``globals()`` of their own module, so an injected name was
found. Feature 004's engine routes every path through the explicit registry
instead, so an injected name is never consulted — a **silent** break: the
imports still resolve, the assignments still execute, nothing raises. Feature
004 declared it (FR-026d) rather than pretending it away.

**What repairs it, and what stays broken by design.** Two halves, from
research R11:

1. The registry binding half was already done — feature 006 bound
   ``NodeType`` -> ``node`` and ``NodeDictType`` -> ``node_list``.
2. **The write path half is this feature.** Before ``CuemsNetworkMapType.save``
   existed, network_map had *no* first-party writer at all — an injected
   handler having no effect was moot, because nothing serialized nodes
   either way. Now it does: FR-026d's break — "an injection is silently
   ignored" — is provable because there is finally a working write path for
   it to be silently ignored *by*.

So this file's assertions flip from "prove nothing writes nodes, injected or
not" to "prove nodes write correctly, and an injection changes nothing about
it". The record that the break was declared and dated survives in this
docstring; the tests below prove it closed.
"""

from __future__ import annotations

import warnings

import cuemsutils.xml.Parsers as ParsersModule
import cuemsutils.xml.XmlBuilder as XmlBuilderModule
from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.xml.mapper import Mapper, read_config_document
from cuemsutils.xml.registry import get_registry
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT

NETWORK_MAP_PATH = REPO_ROOT / "tests" / "data" / "network_map.xml"


class _InjectedNodeXmlBuilder:
    """Stands in for ``cuems-nodeconf``'s real ``nodeXmlBuilder`` injection."""

    was_used = False

    def __init__(self, *args, **kwargs):
        type(self).was_used = True

    def build(self):
        return None


class _InjectedNodeParser:
    """Stands in for ``cuems-nodeconf``'s real ``nodeParser`` injection."""

    was_used = False

    def __init__(self, *args, **kwargs):
        type(self).was_used = True

    def parse(self):
        return {"injected": True}


def _decoded():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        netmap = NetworkMap(str(NETWORK_MAP_PATH))
    raw = read_config_document(netmap.schema_object, str(NETWORK_MAP_PATH))
    return Mapper("network_map").decode_config(raw)


def test_the_registry_resolves_node_and_node_list():
    """The half that was already true — feature 006's bindings, restated as
    the foundation the write path (this feature) is built on."""
    from cuemsutils.config.network_map import node, node_list

    registry = get_registry("network_map")
    assert registry.model_for("NodeType") is node
    assert registry.model_for("NodeDictType") is node_list


def test_the_write_path_now_exists_and_works(tmp_path):
    """The half that was missing until this feature: node serialization
    through the registry, at all."""
    obj = _decoded()
    out = tmp_path / "out.xml"
    obj.save(str(out))

    written = out.read_text()
    assert "<node_role>controller</node_role>" in written
    assert obj["node_list"][0]["node"]["node_role"] is NodeRole.controller  # unmutated


def test_injecting_nodexmlbuilder_has_no_effect_on_the_write(tmp_path, monkeypatch):
    """The break, reproduced against the now-working write path (FR-026d)."""
    _InjectedNodeXmlBuilder.was_used = False
    monkeypatch.setattr(
        XmlBuilderModule, "nodeXmlBuilder", _InjectedNodeXmlBuilder, raising=False
    )

    baseline = tmp_path / "baseline.xml"
    _decoded().save(str(baseline))

    injected_out = tmp_path / "injected.xml"
    _decoded().save(str(injected_out))

    assert _InjectedNodeXmlBuilder.was_used is False
    assert injected_out.read_text() == baseline.read_text()


def test_injecting_nodeparser_has_no_effect_on_the_read(monkeypatch):
    _InjectedNodeParser.was_used = False
    monkeypatch.setattr(ParsersModule, "nodeParser", _InjectedNodeParser, raising=False)

    obj = _decoded()

    assert _InjectedNodeParser.was_used is False
    assert obj["node_list"][0]["node"]["node_role"] is NodeRole.controller


def test_the_injection_still_imports_and_assigns_without_error(monkeypatch):
    """What does **not** break, stated first — the imports still resolve and
    the assignment still executes; only its effect is gone."""
    monkeypatch.setattr(
        XmlBuilderModule, "nodeXmlBuilder", _InjectedNodeXmlBuilder, raising=False
    )
    monkeypatch.setattr(ParsersModule, "nodeParser", _InjectedNodeParser, raising=False)
    assert XmlBuilderModule.nodeXmlBuilder is _InjectedNodeXmlBuilder
    assert ParsersModule.nodeParser is _InjectedNodeParser


def test_no_public_registration_hook_replaces_it():
    """The break is not softened by a new injection point (D11 + Q14, FR-017).

    A consumer needing one uses the public registry — there is no half-API
    that would have to be supported forever.
    """
    import cuemsutils.xml.registry as registry_module

    for name in ("register", "register_binding", "bind", "add_binding"):
        assert not hasattr(registry_module, name)


def test_cuemsnodedict_xmlbuilder_no_longer_exists():
    """FR-018 — the dead stub this feature deletes."""
    assert not hasattr(XmlBuilderModule, "CuemsNodeDictXmlBuilder")


def test_cuemsnodedict_parser_still_absent():
    """Its prior removal (feature 006) stays asserted, so this file remains
    the one place both halves of C7's claim are checked together."""
    assert not hasattr(ParsersModule, "CuemsNodeDictParser")
