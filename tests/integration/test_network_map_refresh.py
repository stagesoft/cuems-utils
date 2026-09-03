"""``CuemsNetworkMapType.refresh()`` (network_map.py:141-190) — ITEM C's
orchestration method. Its ingredients (``NodeIndex.merge``/
``set_controller_always_adopted``/``signature``) are characterized
individually in ``tests/contract/test_nodeindex_characterization.py``, but
nothing exercises the orchestration itself: merge → keep the controller
adopted → write only if the persisted fields actually changed.
"""

from __future__ import annotations

from cuemsutils.config.network_map import CuemsNetworkMapType, node
from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.xml.settings import NetworkMap


def _node(**kwargs):
    defaults = {
        "uuid": None, "mac": None, "name": None, "node_role": NodeRole.node,
        "ip": None, "adopted": False, "online": False,
    }
    defaults.update(kwargs)
    return node(defaults)


def _map_with(*nodes):
    return CuemsNetworkMapType({"node_list": [{"node": n} for n in nodes]})


def test_refresh_writes_and_returns_true_when_a_new_node_is_discovered(tmp_path):
    existing_controller = _node(
        uuid="00000000-0000-0000-0000-000000000001", mac="controller", name="ctrl",
        node_role=NodeRole.controller, ip="10.0.0.1", adopted=True, online=True,
    )
    netmap = _map_with(existing_controller)
    target = tmp_path / "network_map.xml"

    discovered = {
        "controller": _node(
            uuid="00000000-0000-0000-0000-000000000001", mac="controller", name="ctrl",
            node_role=NodeRole.controller, ip="10.0.0.1",
        ),
        "bb:new": _node(uuid="00000000-0000-0000-0000-000000000002", mac="bb:new", name="fresh", ip="10.0.0.2"),
    }

    changed = netmap.refresh(discovered, str(target))

    assert changed is True
    assert target.exists()
    written_uuids = {n["node"]["uuid"] for n in netmap["node_list"]}
    assert written_uuids == {
        "00000000-0000-0000-0000-000000000001",
        "00000000-0000-0000-0000-000000000002",
    }


def test_refresh_returns_false_and_writes_nothing_when_nothing_changed(tmp_path):
    existing_controller = _node(
        uuid="00000000-0000-0000-0000-000000000001", mac="controller", name="ctrl",
        node_role=NodeRole.controller, ip="10.0.0.1", adopted=True, online=True,
    )
    netmap = _map_with(existing_controller)
    target = tmp_path / "network_map.xml"

    discovered = {
        "controller": _node(
            uuid="00000000-0000-0000-0000-000000000001", mac="controller", name="ctrl",
            node_role=NodeRole.controller, ip="10.0.0.1",
        ),
    }

    changed = netmap.refresh(discovered, str(target))

    assert changed is False
    assert not target.exists()


def test_refresh_keeps_the_controller_adopted_even_on_a_first_discovery(tmp_path):
    """``set_controller_always_adopted`` runs after ``merge``, so a
    freshly-discovered controller (which ``merge`` alone would leave
    ``adopted=False``, per the "genuinely new" branch) ends up adopted anyway
    — the property the docstring's "not ported" note contrasts with the
    first-run behaviour that *isn't* reproduced here."""
    netmap = _map_with()
    target = tmp_path / "network_map.xml"

    discovered = {
        "controller": _node(
            uuid="00000000-0000-0000-0000-000000000001", mac="controller", name="ctrl",
            node_role=NodeRole.controller, ip="10.0.0.1",
        ),
    }

    changed = netmap.refresh(discovered, str(target))

    assert changed is True
    written = netmap["node_list"][0]["node"]
    assert written["node_role"] is NodeRole.controller
    assert written["adopted"] is True


def test_refresh_persists_a_document_the_write_path_can_reload(tmp_path):
    netmap = _map_with()
    target = tmp_path / "network_map.xml"
    discovered = {
        "controller": _node(
            uuid="00000000-0000-0000-0000-000000000001", mac="controller", name="ctrl",
            node_role=NodeRole.controller, ip="10.0.0.1", role_id="r1",
        ),
    }

    netmap.refresh(discovered, str(target))

    reloaded = NetworkMap(str(target)).xml_dict
    assert reloaded["node_list"][0]["node"]["uuid"] == "00000000-0000-0000-0000-000000000001"
    assert reloaded["node_list"][0]["node"]["node_role"] is NodeRole.controller
    assert reloaded["node_list"][0]["node"]["adopted"] is True
