"""T091 — the by-reference chain that keeps a consumer's adopt race unreachable.

``cuems-nodeconf`` writes ``network_map.xml`` from two threads: its worker loop
merges discovery and rewrites the map every 30 s or on a debounced Avahi event,
while ``adopt_node``/``unadopt_node`` mutate and save from the comms thread. It
holds **no lock** across either path, and an earlier branch
(``feat/nodelist-modify-hardening``, ``b53ee5f``) added one on the grounds that
a concurrent adopt could be lost.

Measured 2026-09-25, it is not: 60 trials running both paths concurrently lose
zero adoptions. The reason is not synchronisation but **aliasing** — node
dictionaries are passed by reference from the document, through the index, into
``merge`` and back, so an ``adopted`` flag set on the index is *already* visible
in the document being serialised. There is no private copy for the write to be
lost into.

Two of the four links in that chain live in this package, and **nothing stated
them**. These tests do, because the property is a consequence of the no-copies
design rather than a documented guarantee: a ``dict(n)`` added anywhere here for
tidiness would reopen a consumer's concurrency window, and both suites would
stay green. See
``specs/010-consumer-migration/nodeconf-map-write-divergence.md`` §4 for the
measurement and §7 for the task split; the other two links (the consumer's
``_index_from_document`` and ``_network_map_document``) are pinned in
``cuems-nodeconf`` by T093.

Each test here fails against a defensive-copy implementation of the link it
covers. The four mutation runs proving that are recorded in
``specs/010-consumer-migration/baseline.md``.
"""

from __future__ import annotations

import warnings

from cuemsutils.tools.NodeList import NodeIndex, NodeRole
from cuemsutils.xml.mapper import Mapper, read_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.corpus import REPO_ROOT


def _decoded(path: str = "tests/data/network_map.xml"):
    """The document a consumer gets from ``ConfigManager.network_map``."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        netmap = NetworkMap(str(REPO_ROOT / path))
    raw = read_config_document(netmap.schema_object, str(REPO_ROOT / path))
    return Mapper("network_map").decode_config(raw)


def _index_over(document):
    """What ``cuems-nodeconf._index_from_document`` does — deliberately no copies."""
    return NodeIndex({i["node"]["mac"]: i["node"] for i in document["node_list"]})


def _an_adoptable_node(index):
    """An online, unadopted node — made so if the fixture has none."""
    for n in index.values():
        if n.get("online") and not n.get("adopted"):
            return n
    n = list(index.values())[-1]
    n["online"], n["adopted"] = True, False
    return n


def _a_non_controller(index):
    """A node ``unadopt`` will accept — it refuses the controller."""
    for n in index.values():
        if n.get("node_role") is not NodeRole.controller:
            return n
    raise AssertionError("fixture has no non-controller node")


# -- link 3: adopt/unadopt reach the caller's own object -----------------------


def test_adopt_mutates_the_node_object_the_caller_holds():
    """``adopt`` must write through the caller's reference, not rebind a copy.

    The identity assertion is the point: a value-only check
    (``index[mac]["adopted"] is True``) passes for a copy-and-replace
    implementation, and a copy is exactly what breaks the consumer.
    """
    document = _decoded()
    index = _index_over(document)
    victim = _an_adoptable_node(index)
    wrappers = document["node_list"]

    assert index.adopt(victim["uuid"]) is True

    assert victim["adopted"] is True, "adopt did not reach the caller's object"
    aliased = next(i["node"] for i in wrappers if i["node"]["uuid"] == victim["uuid"])
    assert aliased is victim, "the document no longer aliases the index's node"
    assert aliased["adopted"] is True


def test_unadopt_mutates_the_node_object_the_caller_holds():
    """The same guarantee on the way back down — see ``test_adopt_…`` for why."""
    document = _decoded()
    index = _index_over(document)
    victim = _a_non_controller(index)
    victim["adopted"] = True
    wrappers = document["node_list"]

    assert index.unadopt(victim["uuid"]) is True

    assert victim["adopted"] is False, "unadopt did not reach the caller's object"
    aliased = next(i["node"] for i in wrappers if i["node"]["uuid"] == victim["uuid"])
    assert aliased is victim, "the document no longer aliases the index's node"
    assert aliased["adopted"] is False


# -- link 4: merge refreshes in place ----------------------------------------


def test_merge_refreshes_discovery_fields_on_the_callers_objects():
    """``merge`` must update the existing node, not swap in a discovered one.

    Its own comment already says "Refresh mutable discovery fields in place" —
    for a different reason (not clobbering the real key with the discovered
    one). This pins the *aliasing* consequence, which nothing said.
    """
    document = _decoded()
    index = _index_over(document)
    target = list(index.values())[0]
    discovered = {target["mac"]: {**dict(target), "ip": "10.99.99.99"}}

    index.merge(discovered)

    assert index[target["mac"]] is target, "merge replaced the node object"
    assert target["ip"] == "10.99.99.99", "merge did not refresh in place"


# -- link 4: refresh reaches the document's own nodes -------------------------


def test_refresh_reaches_the_documents_own_node_objects(tmp_path):
    """``refresh`` builds its working index over the document's nodes.

    This is the link that carries the consumer's guarantee: if ``refresh``
    worked on copies, an adoption made concurrently on the caller's index would
    be invisible to the document being serialised, and the write would drop it.
    """
    document = _decoded()
    index = _index_over(document)
    target = list(index.values())[0]
    discovered = {target["mac"]: {**dict(target), "ip": "10.88.88.88"}}

    document.refresh(discovered, str(tmp_path / "out.xml"))

    assert target["ip"] == "10.88.88.88", (
        "refresh worked on copies: an adoption made concurrently on the index "
        "would be invisible to the document being serialised"
    )


# -- feature 011, T013: ensure inserts the caller's own object -------------------


def test_ensure_inserts_the_callers_object_by_reference():
    """``NodeIndex.ensure`` is the one primitive for "this node's row exists".

    ``cuems-init-node`` seeds the self-entry through it at provisioning and
    ``cuems-nodeconf``'s feature 003 seeds from ``settings.xml`` through the same
    call (research R7 item 7, decision D-R20-2). It must honour the aliasing
    contract every other link does: insert the **same object** the caller
    holds, so a later ``adopt`` on the index is visible through the caller's
    reference — a ``dict(node)`` copy here would fail this test.
    """
    document = _decoded()
    index = _index_over(document)
    fresh = {
        "uuid": "8c8f4d5e-3d5b-4b0a-9f5d-0a0a0a0a0a0a",
        "mac": "aabbccddeeff",
        "name": "unprovisioned",
        "node_role": NodeRole.firstrun,
        "ip": "0.0.0.0",
        "adopted": False,
        "online": True,  # what provisioning seeds; ``adopt`` refuses an offline node
    }
    before = {mac: dict(n) for mac, n in index.items()}

    assert index.ensure(fresh) is True
    assert index["aabbccddeeff"] is fresh, "ensure copied instead of inserting by reference"
    assert index.adopt(fresh["uuid"]) is True and fresh["adopted"] is True

    for mac, snapshot in before.items():
        assert dict(index[mac]) == snapshot, f"ensure touched another row ({mac})"


def test_ensure_is_a_no_op_when_the_uuid_is_already_present():
    """Match by uuid, never by key: a present node keeps its object and its flags."""
    document = _decoded()
    index = _index_over(document)
    existing = list(index.values())[0]
    existing["adopted"] = True
    duplicate = {**dict(existing), "mac": "000000000000", "name": "impostor"}

    assert index.ensure(duplicate) is False
    assert "000000000000" not in index, "ensure inserted a second row for a present uuid"
    assert index[existing["mac"]] is existing and existing["adopted"] is True
