"""Contract C7 — no handler is resolved through a module namespace (T040, T046a).

FR-026d's break was exactly this: ``cuems-nodeconf``'s ``NodeXmlBuilders.py``
injected ``nodeXmlBuilder``/``node_listXmlBuilder``/``nodeParser``/
``node_listParser`` into ``cuemsutils.xml.XmlBuilder``/``Parsers`` module
namespaces via ``setattr``, and the old builder's ``get_builder_class``
consulted ``globals()[class_name]`` to find them. The registry-based engine
(``xml/registry.py``, ``xml/mapper.py``) never does that lookup — a class is
found by an explicit schema-scoped table, never by module attribute — so an
injection has no effect on the real read/write chain any more. This asserts
that structurally, not just "it still works today".
"""

from __future__ import annotations

import warnings

import cuemsutils.xml.XmlBuilder as xml_builder_module
import cuemsutils.xml.Parsers as parsers_module
from cuemsutils.xml.mapper import Mapper, read_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT

NETWORK_MAP_PATH = REPO_ROOT / "tests" / "data" / "network_map.xml"


def _decoded():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        netmap = NetworkMap(str(NETWORK_MAP_PATH))
    raw = read_config_document(netmap.schema_object, str(NETWORK_MAP_PATH))
    return Mapper("network_map").decode_config(raw)


def test_injecting_into_xmlbuilder_module_namespace_has_no_effect_on_the_write_chain(
    tmp_path,
):
    baseline = tmp_path / "baseline.xml"
    _decoded().save(str(baseline))
    baseline_text = baseline.read_text()

    called = []

    class _FakeInjectedBuilder:
        def __init__(self, *args, **kwargs):
            called.append((args, kwargs))

        def build(self):
            called.append("build")
            return None

    # Exactly the shape cuems-nodeconf's NodeXmlBuilders.py used to inject
    # (setattr(XmlBuilderModule, 'nodeXmlBuilder', ...), FR-026d).
    xml_builder_module.nodeXmlBuilder = _FakeInjectedBuilder
    xml_builder_module.node_listXmlBuilder = _FakeInjectedBuilder
    try:
        injected = tmp_path / "injected.xml"
        _decoded().save(str(injected))
        assert injected.read_text() == baseline_text
        assert called == [], "the injected class was consulted"
    finally:
        del xml_builder_module.nodeXmlBuilder
        del xml_builder_module.node_listXmlBuilder


def test_injecting_into_parsers_module_namespace_has_no_effect_on_the_read_chain():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        baseline_netmap = NetworkMap(str(NETWORK_MAP_PATH))
    baseline_raw = read_config_document(baseline_netmap.schema_object, str(NETWORK_MAP_PATH))
    baseline = Mapper("network_map").decode_config(baseline_raw)

    called = []

    class _FakeInjectedParser:
        def __init__(self, *args, **kwargs):
            called.append((args, kwargs))

        def parse(self):
            called.append("parse")
            return {}

    parsers_module.nodeParser = _FakeInjectedParser
    parsers_module.node_listParser = _FakeInjectedParser
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            netmap = NetworkMap(str(NETWORK_MAP_PATH))
        raw = read_config_document(netmap.schema_object, str(NETWORK_MAP_PATH))
        decoded = Mapper("network_map").decode_config(raw)
        assert decoded == baseline
        assert called == [], "the injected class was consulted"
    finally:
        del parsers_module.nodeParser
        del parsers_module.node_listParser


# -- T046a: no public registration API ---------------------------------------


def test_no_public_api_registers_an_external_builder_or_parser():
    """FR-017 — a distinct claim from the two tests above: not only does an
    injection have no effect, there is no *supported* way to register one."""
    import cuemsutils
    import cuemsutils.xml as xml_package
    from cuemsutils.xml import registry as registry_module

    # The package's own public surface names no registration entry point.
    forbidden_substrings = ("register", "inject")
    public_names = [n for n in dir(cuemsutils) if not n.startswith("_")]
    offenders = [
        n for n in public_names if any(s in n.lower() for s in forbidden_substrings)
    ]
    assert offenders == []

    assert xml_package.__all__ == []

    # The registry itself exposes no "add a binding from outside" method —
    # SchemaRegistry.bind/bind_path exist, but are never called except by the
    # module-private _build_*_registry functions this file cannot reach
    # without importing the private module directly.
    public_registry_names = [n for n in dir(registry_module) if not n.startswith("_")]
    assert "register" not in [n.lower() for n in public_registry_names]
