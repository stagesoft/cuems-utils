"""``NodeIndex.merge`` copies an announced field only if the schema accepts it.

D12 of ``specs/planning/tpm-ek-fingerprint.md``. Before it, ``merge`` copied
every announced value, so one node announcing one invalid value left that value
in the controller's in-memory map, and every later ``save`` of the whole map
failed until the node announced a valid one again.
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from cuemsutils.config.network_map import node
from cuemsutils.helpers import Unset
from cuemsutils.tools.ConfigManager import ConfigManager
from cuemsutils.tools.NodeList import NodeIndex, NodeRole
from tests.support.cuems_logs import capture

UUID_A = "6f0c8a52-3d1e-4b7a-9c2f-0a1b2c3d4e5f"
UUID_B = "9b2e4d61-7a3c-4f8e-8d1b-5e6f7a8b9c0d"
NODELIST = "cuemsutils.tools.NodeList"
DATA = Path(__file__).resolve().parents[1] / "data"


def _node(**overrides):
    fields = {
        "uuid": UUID_A, "mac": "aabbccddeeff", "name": "stage-left",
        "node_role": NodeRole.node, "ip": "10.0.0.2", "adopted": False, "online": True,
    }
    fields.update(overrides)
    return node(fields)


def _index(**overrides):
    return NodeIndex({"aabbccddeeff": _node(**overrides)})


# -- (b) an existing node keeps its value when the announced one is invalid ----


def test_an_invalid_value_is_dropped_and_the_stored_one_kept(caplog):
    capture(caplog, NODELIST)
    index = _index()

    index.merge({"x": _node(ip="", name="renamed")})

    merged = index["aabbccddeeff"]
    assert merged["ip"] == "10.0.0.2"
    assert merged["name"] == "renamed", "a valid field beside the invalid one must still be copied"
    assert any("invalid ip" in r.getMessage() and "keeping '10.0.0.2'" in r.getMessage()
               for r in caplog.records)


def test_a_valid_optional_field_is_copied():
    index = _index()

    index.merge({"x": _node(alias="downstage")})

    assert index["aabbccddeeff"]["alias"] == "downstage"


def test_an_invalid_optional_field_is_not_added():
    index = _index()

    index.merge({"x": _node(alias="   ")})

    assert "alias" not in index["aabbccddeeff"]


# -- (a) an undeclared key never reaches the map, even from a plain dict -------


def test_an_undeclared_key_from_a_plain_dict_is_not_copied():
    index = _index()
    announced = dict(_node())
    announced["bogus"] = "x"

    index.merge({"x": announced})

    assert "bogus" not in index["aabbccddeeff"]


# -- (c) a new node needs every required field, valid ---------------------------


@pytest.mark.parametrize("field, value", [("uuid", "not-a-uuid"), ("ip", ""), ("ip", None)])
def test_a_new_node_with_an_invalid_required_field_is_not_added(caplog, field, value):
    capture(caplog, NODELIST)
    index = NodeIndex()

    index.merge({"x": _node(**{field: value})})

    assert len(index) == 0
    assert any("not added to the network map" in r.getMessage() and field in r.getMessage()
               for r in caplog.records)


def test_a_new_node_keeps_its_valid_fields_and_loses_an_invalid_optional_one():
    index = NodeIndex()
    announced = _node(alias="   ")

    index.merge({"x": announced})

    added = index["aabbccddeeff"]
    assert added is announced, "a new node is still inserted as the discovered object"
    assert "alias" not in added
    assert added["ip"] == "10.0.0.2"


# -- (d) the existing discovery rules are unchanged -----------------------------


def test_mac_adopted_and_online_are_not_taken_from_discovery():
    index = _index(adopted=True, online=False)

    index.merge({"x": _node(mac="112233445566", adopted=False, online=False)})

    merged = index["aabbccddeeff"]
    assert merged["mac"] == "aabbccddeeff"
    assert merged["adopted"] is True
    assert merged["online"] is True


# -- (e) a field that is not announced is left alone ----------------------------


@pytest.mark.parametrize("absent", [None, Unset])
def test_an_unannounced_field_keeps_its_stored_value(absent):
    index = _index(alias="downstage")

    index.merge({"x": _node(alias=absent)})

    assert index["aabbccddeeff"]["alias"] == "downstage"


def test_a_field_missing_from_the_announcement_keeps_its_stored_value():
    index = _index(alias="downstage")
    announced = _node()
    announced.pop("alias", None)

    index.merge({"x": announced})

    assert index["aabbccddeeff"]["alias"] == "downstage"


# -- the defect itself, through the daemon's path ------------------------------


def test_one_invalid_announcement_no_longer_blocks_the_map(tmp_path):
    for name in ("network_map.xml", "settings.xml", "default_mappings.xml", "project_mappings.xml"):
        shutil.copy(DATA / name, tmp_path / name)
    network_map = ConfigManager(config_dir=str(tmp_path)).network_map
    target = tmp_path / "network_map.xml"
    existing = network_map["node_list"][0]["node"]

    poisoned = node(dict(existing))
    poisoned["ip"] = ""
    network_map.refresh({"x": poisoned}, str(target))

    newcomer = _node(uuid=UUID_B, mac="0a0b0c0d0e0f", name="newcomer", ip="10.0.0.9")
    assert network_map.refresh({"x": node(dict(existing)), "y": newcomer}, str(target)) is True
    saved = [item["node"] for item in ConfigManager(config_dir=str(tmp_path)).network_map["node_list"]]
    assert UUID_B in {str(n["uuid"]) for n in saved}
    assert existing["ip"] != ""
