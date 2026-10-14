"""Foreign-controller scoping on ``NodeIndex`` — the read side and the removal.

Several CUEMS clusters share one LAN and every controller announces itself, so
an unscoped ``merge`` + ``set_controller_always_adopted`` adopts the *other*
clusters' controllers into this one's map. The rule (a node's cluster
controllers; a controller outside that set is foreign, ignored and removed) is
``cuems-nodeconf``'s shipped fix (``80ccc83``), moved here because the merge is
this library's (D22). Requested in
``../cuems-nodeconf/specs/upstream-reports/foreign-controller-scoping.md`` (§4
T1–T3); the orchestration through ``refresh`` is pinned in
``tests/integration/test_network_map_refresh.py``.

Nothing here saves, so the identities are readable labels rather than uuid4s.
"""

from __future__ import annotations

from cuemsutils.config.network_map import node
from cuemsutils.tools.NodeList import NodeIndex, NodeRole


def _node(uuid, mac, role=NodeRole.node, **kwargs):
    return node({"uuid": uuid, "mac": mac, "node_role": role, **kwargs})


def _index(*nodes):
    return NodeIndex({n["mac"]: n for n in nodes})


def _ours():
    return _node("u-master", "aa:master", NodeRole.controller, adopted=True)


def _foreign(uuid="u-foreign", mac="ff:foreign"):
    return _node(uuid, mac, NodeRole.controller, adopted=True, online=False)


# -- T1: cluster_controllers ---------------------------------------------------


def test_a_controllers_cluster_is_its_own_uuid_whatever_the_map_holds():
    index = _index(_ours(), _foreign())

    assert index.cluster_controllers(
        own_uuid="u-master", own_role=NodeRole.controller
    ) == frozenset({"u-master"})


def test_a_nodes_cluster_is_the_controller_its_map_records():
    index = _index(_ours(), _node("u-slave", "bb:slave"))

    assert index.cluster_controllers(
        own_uuid="u-slave", own_role=NodeRole.node
    ) == frozenset({"u-master"})


def test_a_fresh_nodes_cluster_is_empty():
    assert NodeIndex().cluster_controllers(
        own_uuid="u-slave", own_role=NodeRole.node
    ) == frozenset()


def test_a_controller_row_without_a_uuid_is_skipped():
    index = _index(_ours(), _node(None, "cc:nouuid", NodeRole.controller))

    assert index.cluster_controllers() == frozenset({"u-master"})


def test_cluster_controllers_is_read_only():
    index = _index(_ours(), _foreign())
    before = index.signature()

    index.cluster_controllers(own_uuid="u-slave", own_role=NodeRole.node)

    assert index.signature() == before


# -- T2: is_foreign_controller / foreign_controllers -----------------------------


def test_an_empty_cluster_makes_nothing_foreign():
    index = _index(_ours(), _foreign())

    assert index.foreign_controllers(frozenset()) == ()
    assert index.foreign_controllers(None) == ()


def test_a_node_role_row_is_never_foreign():
    stranger = _node("u-other", "dd:other")

    assert not NodeIndex.is_foreign_controller(stranger, frozenset({"u-master"}))


def test_foreign_controllers_returns_the_indexs_own_objects():
    foreign = _foreign()
    index = _index(_ours(), foreign, _node("u-slave", "bb:slave"))

    found = index.foreign_controllers(frozenset({"u-master"}))

    assert len(found) == 1
    assert found[0] is foreign


# -- T3: drop_foreign_controllers --------------------------------------------------


def test_a_saved_foreign_controller_is_removed_not_flipped():
    ours, foreign, slave = _ours(), _foreign(), _node("u-slave", "bb:slave")
    index = _index(ours, foreign, slave)

    removed = index.drop_foreign_controllers(frozenset({"u-master"}))

    assert removed == (foreign,) and removed[0] is foreign
    assert "ff:foreign" not in index
    assert index["aa:master"] is ours
    assert index["bb:slave"] is slave


def test_an_empty_cluster_removes_nothing():
    index = _index(_ours(), _foreign())

    assert index.drop_foreign_controllers(frozenset()) == ()
    assert set(index) == {"aa:master", "ff:foreign"}
