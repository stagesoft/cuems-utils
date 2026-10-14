"""The D14 chain for ``network_map`` (T039, FR-025).

    xml -> object -> json -> object -> xml

Unlike the show path's chain (``test_d14_chain.py``, ``CuemsParser``-based —
``network_map`` has no such rebuilder), the "json -> object" leg goes through
the same machinery a document does: ``to_wire()``'s output is exactly the
shape ``Mapper.decode_config`` (with ``network_map``'s adapter table opted
in) already knows how to consume — ``_EnumAdapter.decode``/``_Bool.decode``
both accept the lexical string form ``to_wire()`` produces. Asserting that
round trip *is* the claim: the wire projection and the decode input are the
same shape, not two shapes that happen to agree today.
"""

from __future__ import annotations

import json
import warnings

import pytest

from cuemsutils.tools.NodeList import NodeIndex, NodeRole
from cuemsutils.xml.mapper import Mapper, read_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT

CASES = [
    "tests/data/network_map.xml",
    "tests/data/corpus/cuems-utils/network_map.xml",
    "tests/data/corpus/cuems-engine/network_map.xml",
]


def _decoded(path: str):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        netmap = NetworkMap(str(REPO_ROOT / path))
    raw = read_config_document(netmap.schema_object, str(REPO_ROOT / path))
    return Mapper("network_map").decode_config(raw)


@pytest.mark.parametrize("path", CASES)
def test_xml_to_object_to_json_to_object_to_xml(path, tmp_path):
    # xml -> object
    obj = _decoded(path)
    original_role = obj["node_list"][0]["node"]["node_role"]
    assert isinstance(original_role, NodeRole)

    # object -> json
    wire = obj.to_wire()
    assert wire["node_list"][0]["node"]["node_role"] == original_role.value
    payload = json.dumps(wire)

    # json -> object
    reloaded_raw = json.loads(payload)
    reloaded = Mapper("network_map").decode_config(reloaded_raw)
    assert isinstance(reloaded["node_list"][0]["node"]["node_role"], NodeRole)
    assert reloaded["node_list"][0]["node"]["node_role"] == original_role

    # object -> xml
    out = tmp_path / "chain.xml"
    reloaded.save(str(out))
    written = out.read_text()
    assert f"<node_role>{original_role.value}</node_role>" in written
    assert "<node_type>" not in written


# -- G4, T046: a label persists through a save, an IP change, an adopt and an
# un-adopt --------------------------------------------------------------------


def test_a_labelled_index_saves_a_document_carrying_the_label(tmp_path):
    document = _decoded("tests/data/network_map.xml")
    index = NodeIndex({i["node"]["mac"]: i["node"] for i in document["node_list"]})
    target = list(index.values())[0]

    assert index.set_alias(target["uuid"], "stage-left") is True

    out = tmp_path / "labelled.xml"
    document.save(str(out))

    assert "<alias>stage-left</alias>" in out.read_text()


def test_a_label_survives_an_ip_change_an_adopt_and_an_unadopt(tmp_path):
    document = _decoded("tests/data/network_map.xml")
    index = NodeIndex({i["node"]["mac"]: i["node"] for i in document["node_list"]})
    target = next(n for n in index.values() if n.get("node_role") is not NodeRole.controller)
    target["online"] = True

    index.set_alias(target["uuid"], "stage-left")

    # An IP change, via discovery merge.
    discovered = {target["mac"]: {
        k: v for k, v in target.items()
        if k in ("uuid", "mac", "name", "node_role", "ip", "adopted", "online")
    }}
    discovered[target["mac"]]["ip"] = "10.10.10.10"
    index.merge(discovered)
    assert target["alias"] == "stage-left"

    # An adopt.
    assert index.adopt(target["uuid"]) is True
    assert target["alias"] == "stage-left"

    # An un-adopt.
    assert index.unadopt(target["uuid"]) is True
    assert target["alias"] == "stage-left"

    out = tmp_path / "survived.xml"
    document.save(str(out))
    assert "<alias>stage-left</alias>" in out.read_text()
