"""``CuemsNetworkMapType.refresh()`` (network_map.py:141-190) — ITEM C's
orchestration method. Its ingredients (``NodeIndex.merge``/
``set_controller_always_adopted``/``signature``) are characterized
individually in ``tests/contract/test_nodeindex_characterization.py``, but
nothing exercises the orchestration itself: merge → keep the controller
adopted → write only if the persisted fields actually changed.

**Identities updated by feature 012.** These used to be
``00000000-0000-0000-0000-00000000000N`` — neither converged uuid4s nor the
not-provisioned sentinel, which the narrowed ``cms:NodeUuidType`` now refuses.
They were arbitrary placeholders standing for "two distinct nodes", and they
still are; only their shape had to become one a network map may carry. Nothing
this file asserts is about the identities themselves.
"""

from __future__ import annotations

from cuemsutils.config.network_map import CuemsNetworkMapType, node
from cuemsutils.tools.NodeList import NodeIndex, NodeRole
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
        uuid="11111111-1111-4111-8111-111111111111", mac="controller", name="ctrl",
        node_role=NodeRole.controller, ip="10.0.0.1", adopted=True, online=True,
    )
    netmap = _map_with(existing_controller)
    target = tmp_path / "network_map.xml"

    discovered = {
        "controller": _node(
            uuid="11111111-1111-4111-8111-111111111111", mac="controller", name="ctrl",
            node_role=NodeRole.controller, ip="10.0.0.1",
        ),
        "bb:new": _node(uuid="22222222-2222-4222-8222-222222222222", mac="bb:new", name="fresh", ip="10.0.0.2"),
    }

    changed = netmap.refresh(discovered, str(target))

    assert changed is True
    assert target.exists()
    written_uuids = {n["node"]["uuid"] for n in netmap["node_list"]}
    assert written_uuids == {
        "11111111-1111-4111-8111-111111111111",
        "22222222-2222-4222-8222-222222222222",
    }


def test_refresh_returns_false_and_writes_nothing_when_nothing_changed(tmp_path):
    existing_controller = _node(
        uuid="11111111-1111-4111-8111-111111111111", mac="controller", name="ctrl",
        node_role=NodeRole.controller, ip="10.0.0.1", adopted=True, online=True,
    )
    netmap = _map_with(existing_controller)
    target = tmp_path / "network_map.xml"

    discovered = {
        "controller": _node(
            uuid="11111111-1111-4111-8111-111111111111", mac="controller", name="ctrl",
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
            uuid="11111111-1111-4111-8111-111111111111", mac="controller", name="ctrl",
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
            uuid="11111111-1111-4111-8111-111111111111", mac="controller", name="ctrl",
            node_role=NodeRole.controller, ip="10.0.0.1", role_id="r1",
        ),
    }

    netmap.refresh(discovered, str(target))

    reloaded = NetworkMap(str(target)).xml_dict
    assert reloaded["node_list"][0]["node"]["uuid"] == "11111111-1111-4111-8111-111111111111"
    assert reloaded["node_list"][0]["node"]["node_role"] is NodeRole.controller
    assert reloaded["node_list"][0]["node"]["adopted"] is True


# -- foreign-controller scoping ------------------------------------------------
#
# The four regression tests of ``cuems-nodeconf``'s shipped fix (``80ccc83``),
# translated to ``refresh(..., cluster=)`` — requested in
# ``../cuems-nodeconf/specs/upstream-reports/foreign-controller-scoping.md`` §4
# T4. The document's labels ``u-master``/``u-slave`` are uuid4s here because
# ``refresh`` saves, and ``cms:NodeUuidType`` refuses anything else.

U_MASTER = "11111111-1111-4111-8111-111111111111"
U_SLAVE = "22222222-2222-4222-8222-222222222222"
U_FOREIGN_A = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
U_FOREIGN_B = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def _controller(uuid, mac, **kwargs):
    return _node(uuid=uuid, mac=mac, name=mac, node_role=NodeRole.controller,
                 ip="10.0.0.1", **kwargs)


def _slave(**kwargs):
    return _node(uuid=U_SLAVE, mac="bb:slave", name="slave", ip="10.0.0.2", **kwargs)


def _uuids(netmap):
    return {item["node"]["uuid"] for item in netmap["node_list"]}


def _by_uuid(netmap, uuid):
    return next(i["node"] for i in netmap["node_list"] if i["node"]["uuid"] == uuid)


def test_scoped_refresh_on_a_controller_ignores_foreign_controllers(tmp_path):
    netmap = _map_with(_controller(U_MASTER, "aa:master", adopted=True, online=True))
    discovered = {
        "aa:master": _controller(U_MASTER, "aa:master"),
        "bb:slave": _slave(),
        "fa:one": _controller(U_FOREIGN_A, "fa:one"),
        "fb:two": _controller(U_FOREIGN_B, "fb:two"),
    }

    netmap.refresh(discovered, str(tmp_path / "nm.xml"), cluster=frozenset({U_MASTER}))

    assert _uuids(netmap) == {U_MASTER, U_SLAVE}
    assert _by_uuid(netmap, U_MASTER)["adopted"] is True
    assert _by_uuid(netmap, U_SLAVE)["adopted"] is False


def test_scoped_refresh_removes_a_foreign_controller_saved_earlier(tmp_path):
    netmap = _map_with(
        _controller(U_MASTER, "aa:master", adopted=True, online=True),
        _controller(U_FOREIGN_A, "fa:one", adopted=True, online=True),
    )
    target = tmp_path / "nm.xml"

    changed = netmap.refresh(
        {"aa:master": _controller(U_MASTER, "aa:master")},
        str(target), cluster=frozenset({U_MASTER}),
    )

    assert changed is True
    written = target.read_text()
    assert U_MASTER in written
    assert U_FOREIGN_A not in written


def test_scoped_refresh_on_a_node_keeps_its_recorded_controller(tmp_path):
    netmap = _map_with(
        _controller(U_MASTER, "aa:master", adopted=True, online=False),
        _slave(online=True),
    )
    index = NodeIndex({i["node"]["mac"]: i["node"] for i in netmap["node_list"]})
    cluster = index.cluster_controllers(own_uuid=U_SLAVE, own_role=NodeRole.node)
    discovered = {
        "aa:master": _controller(U_MASTER, "aa:master"),
        "bb:slave": _slave(),
        "fa:one": _controller(U_FOREIGN_A, "fa:one"),
    }

    netmap.refresh(discovered, str(tmp_path / "nm.xml"), cluster=cluster)

    assert _uuids(netmap) == {U_MASTER, U_SLAVE}
    assert _by_uuid(netmap, U_MASTER)["online"] is True


def test_scoped_refresh_on_a_fresh_node_accepts_the_first_controller(tmp_path):
    netmap = _map_with()
    cluster = NodeIndex().cluster_controllers(own_uuid=U_SLAVE, own_role=NodeRole.node)
    assert cluster == frozenset()

    changed = netmap.refresh(
        {"aa:master": _controller(U_MASTER, "aa:master")},
        str(tmp_path / "nm.xml"), cluster=cluster,
    )

    assert changed is True
    assert _uuids(netmap) == {U_MASTER}
    assert _by_uuid(netmap, U_MASTER)["adopted"] is True


def test_unscoped_refresh_still_adopts_every_controller(tmp_path):
    """Today's behaviour, stated by a test: no ``cluster``, no scoping."""
    netmap = _map_with()
    discovered = {
        "aa:master": _controller(U_MASTER, "aa:master"),
        "fa:one": _controller(U_FOREIGN_A, "fa:one"),
    }

    netmap.refresh(discovered, str(tmp_path / "nm.xml"))

    assert _uuids(netmap) == {U_MASTER, U_FOREIGN_A}
    assert all(item["node"]["adopted"] is True for item in netmap["node_list"])


def test_a_second_identical_scoped_refresh_writes_nothing(tmp_path):
    netmap = _map_with(
        _controller(U_MASTER, "aa:master", adopted=True, online=True),
        _controller(U_FOREIGN_A, "fa:one", adopted=True, online=True),
    )
    target = str(tmp_path / "nm.xml")
    cluster = frozenset({U_MASTER})

    def discovered():
        return {"aa:master": _controller(U_MASTER, "aa:master"),
                "fa:one": _controller(U_FOREIGN_A, "fa:one")}

    assert netmap.refresh(discovered(), target, cluster=cluster) is True
    assert netmap.refresh(discovered(), target, cluster=cluster) is False
