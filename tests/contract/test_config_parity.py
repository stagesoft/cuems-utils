"""Accessor parity for the configuration classes (T051).

``Settings``, ``NetworkMap``, ``ProjectMappings`` and ``ProjectSettings`` are
the four public classes that read configuration documents. Routing them through
the engine (T053) must not change a single value any of them returns.

Their public surface is asserted here rather than only through the dict
goldens, because a consumer calls ``get_node`` or ``get_dict`` — not
``xml_dict`` — and a refactor that kept the dict intact while breaking an
accessor would pass C2 and still break `cuems-engine` at startup.
"""

from __future__ import annotations

import json
import warnings

import pytest

from cuemsutils.xml import NetworkMap, ProjectMappings, ProjectSettings, Settings
from tests.support import roundtrip as rt
from tests.support.corpus import DOCUMENTS, GOLDEN_ROOT, documents

CONFIG_CLASSES = {
    "Settings": Settings,
    "NetworkMap": NetworkMap,
    "ProjectMappings": ProjectMappings,
    "ProjectSettings": ProjectSettings,
}

READABLE_CONFIG = [
    d
    for d in DOCUMENTS
    if d.config_class and (GOLDEN_ROOT / "dict" / f"{d.slug}.config.json").exists()
]
IDS = [d.relpath for d in READABLE_CONFIG]


def _load(doc):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return CONFIG_CLASSES[doc.config_class](str(doc.path))


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_xml_dict_matches_its_golden(doc):
    assert rt.json_dumps(_load(doc).xml_dict) == rt.golden_json(
        f"dict/{doc.slug}.config.json"
    )


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_get_dict_is_stable(doc):
    """``get_dict`` unwraps ``main_key``, which differs per class.

    ``Settings`` uses ``'Settings'``, ``ProjectSettings`` uses
    ``'CuemsProjectSettings'``, and the other two use ``''`` — meaning the
    whole document. Getting that wrong returns an empty dict rather than an
    error, so it is asserted rather than assumed.
    """
    obj = _load(doc)
    result = obj.get_dict()
    assert isinstance(result, dict)
    golden = json.loads(rt.golden_json(f"dict/{doc.slug}.config.json"))
    if obj.main_key == "":
        assert result == golden
    else:
        assert result == golden.get(obj.main_key, {}) or result == {
            obj.main_key: golden.get(obj.main_key)
        }


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_loaded_flag_is_set(doc):
    assert _load(doc).loaded is True


def test_network_map_get_node_returns_the_named_node():
    doc = next(d for d in documents(schema="network_map") if d.category == "cuems-utils")
    network = _load(doc)
    node_list = network.get_dict()["node_list"]
    uuid = node_list[0]["node"]["uuid"]
    assert network.get_node(uuid)["uuid"] == uuid


def test_network_map_get_node_raises_for_an_unknown_uuid():
    """The failure path, pinned with the success path.

    A lookup that silently returned ``None`` for a missing node would let a
    misconfigured cluster start up and fail much later.
    """
    doc = next(d for d in documents(schema="network_map") if d.category == "cuems-utils")
    with pytest.raises(ValueError, match="not found"):
        _load(doc).get_node("00000000-0000-4000-8000-000000000000")


def test_network_map_nodes_by_adoption_splits_and_coerces():
    """``online``/``adopted`` are ``"True"``/``"False"`` strings in the dict.

    ``get_nodes_by_adoption`` converts them with ``strtobool`` and partitions
    on the result — one of the few places a config accessor does more than
    look something up.
    """
    doc = next(d for d in documents(schema="network_map") if d.category == "cuems-utils")
    nodes, new_nodes = NetworkMap.get_nodes_by_adoption(_load(doc).get_dict())
    assert isinstance(nodes, list) and isinstance(new_nodes, list)
    for entry in nodes + new_nodes:
        assert isinstance(entry["node"]["online"], bool)
        assert isinstance(entry["node"]["adopted"], bool)


def test_project_mappings_processed_is_populated():
    doc = next(
        d
        for d in documents(schema="project_mappings")
        if d.relpath == "cuems-utils/project_mappings.xml"
    )
    mappings = _load(doc)
    assert mappings.processed
    assert "nodes" in mappings.processed


def test_project_mappings_get_node_returns_the_named_node():
    doc = next(
        d
        for d in documents(schema="project_mappings")
        if d.relpath == "cuems-utils/project_mappings.xml"
    )
    mappings = _load(doc)
    uuid = mappings.processed["nodes"][0]["node"]["uuid"]
    assert mappings.get_node(uuid)["uuid"] == uuid


@pytest.mark.parametrize("doc", READABLE_CONFIG, ids=IDS)
def test_reading_twice_gives_the_same_result(doc):
    """Idempotence at the accessor level.

    The schema cache is shared across instances, so a cache that leaked state
    between reads would show up here and nowhere else.
    """
    assert rt.json_dumps(_load(doc).xml_dict) == rt.json_dumps(_load(doc).xml_dict)


def test_every_config_class_is_covered():
    """The parametrisation must not quietly shrink to three classes."""
    covered = {d.config_class for d in READABLE_CONFIG}
    assert covered == set(CONFIG_CLASSES)
