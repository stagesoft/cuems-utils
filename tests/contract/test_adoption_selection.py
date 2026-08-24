"""Contract C6 — adoption selection (T007, T080, T081).

``NetworkMap.get_nodes_by_adoption`` predates this feature and has always
taken ``adopted``/``online`` as the ``"True"``/``"False"`` strings
``cms:BoolType`` decodes to, converting them with ``strtobool``. Once R1 makes
``network_map`` run the adapter table, those two fields decode as real
``bool`` — and ``strtobool(True)`` raises ``AttributeError`` (``bool`` has no
``.lower()``), not the ``ValueError`` an unrecognised string would raise. That
is a silent interaction between two requirements of this feature (FR-011a
typing the fields, Assumption 8 keeping this method available), so it is
proven here **before** the typing lands (research R7) rather than assumed.

``partition_by_adoption`` (T082) is the non-mutating replacement this file
also covers (T080, T081): it returns bare node objects rather than
``{"node": ...}`` wrappers, and never writes back into the map it is given.
"""

from __future__ import annotations

import warnings

from cuemsutils.config.network_map import node
from cuemsutils.tools.NodeList import NodeRole
from cuemsutils.xml.settings import NetworkMap


def _network_map_dict(*, adopted, online):
    return {
        "node_list": [
            {
                "node": {
                    "uuid": "0367f391-ebf4-48b2-9f26-000000000001",
                    "mac": "2cf05d21cca3",
                    "name": "controller",
                    "node_type": "NodeType.master",
                    "ip": "192.168.1.10",
                    "adopted": adopted,
                    "online": online,
                }
            }
        ]
    }


def _get_nodes_by_adoption(*args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        return NetworkMap.get_nodes_by_adoption(*args, **kwargs)


def test_get_nodes_by_adoption_accepts_already_typed_booleans():
    """C6 / research R7 — must fail before T008, pass after.

    The one interaction this feature's typing creates: a caller that already
    holds ``bool`` values (as every caller will, once ``network_map`` runs the
    adapter table) must not crash the one config accessor that post-processes
    them.
    """
    network_map_dict = _network_map_dict(adopted=True, online=False)
    nodes, new_nodes = _get_nodes_by_adoption(network_map_dict)
    assert len(nodes) == 1
    assert new_nodes == []
    assert nodes[0]["node"]["adopted"] is True
    assert nodes[0]["node"]["online"] is False


def test_get_nodes_by_adoption_still_accepts_strings():
    """The pre-typing call shape must keep working — this method is retained
    (Assumption 8) until feature 008 migrates its caller."""
    network_map_dict = _network_map_dict(adopted="True", online="False")
    nodes, new_nodes = _get_nodes_by_adoption(network_map_dict)
    assert len(nodes) == 1
    assert nodes[0]["node"]["adopted"] is True
    assert nodes[0]["node"]["online"] is False


def test_get_nodes_by_adoption_partitions_unadopted_typed_booleans():
    network_map_dict = _network_map_dict(adopted=False, online=True)
    nodes, new_nodes = _get_nodes_by_adoption(network_map_dict)
    assert nodes == []
    assert len(new_nodes) == 1
    assert new_nodes[0]["node"]["adopted"] is False


def test_get_nodes_by_adoption_warns():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        NetworkMap.get_nodes_by_adoption(_network_map_dict(adopted=True, online=True))
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert any("partition_by_adoption" in str(w.message) for w in caught)


# -- T080, T081: partition_by_adoption ---------------------------------------


def _two_node_map(*, first_adopted, second_adopted):
    def _node(uuid, adopted):
        fields = {
            "uuid": uuid,
            "mac": "aabbccddeeff",
            "name": "n",
            "node_role": NodeRole.node,
            "ip": "1.2.3.4",
        }
        if adopted is not None:
            fields["adopted"] = adopted
        return {"node": node(**fields)}

    return {
        "node_list": [
            _node("0367f391-ebf4-48b2-9f26-000000000001", first_adopted),
            _node("0367f391-ebf4-48b2-9f26-000000000002", second_adopted),
        ]
    }


def test_partition_by_adoption_true_false_and_absent():
    """T081 — adopted True, False and absent (no key at all — Unset)."""
    network_map = _two_node_map(first_adopted=True, second_adopted=False)
    adopted, unadopted = NetworkMap.partition_by_adoption(network_map)
    assert [n["uuid"] for n in adopted] == ["0367f391-ebf4-48b2-9f26-000000000001"]
    assert [n["uuid"] for n in unadopted] == ["0367f391-ebf4-48b2-9f26-000000000002"]

    absent_map = _two_node_map(first_adopted=None, second_adopted=True)
    adopted2, unadopted2 = NetworkMap.partition_by_adoption(absent_map)
    assert [n["uuid"] for n in adopted2] == ["0367f391-ebf4-48b2-9f26-000000000002"]
    assert [n["uuid"] for n in unadopted2] == ["0367f391-ebf4-48b2-9f26-000000000001"]


def test_partition_by_adoption_returns_bare_node_objects_not_wrappers():
    network_map = _two_node_map(first_adopted=True, second_adopted=False)
    adopted, unadopted = NetworkMap.partition_by_adoption(network_map)
    assert isinstance(adopted[0], node)
    assert "node" not in adopted[0]  # not a {"node": ...} wrapper


def test_partition_by_adoption_does_not_mutate_its_input():
    """C6 — every node value equal, field by field, before and after."""
    network_map = _two_node_map(first_adopted=True, second_adopted=False)
    before = [dict(entry["node"]) for entry in network_map["node_list"]]

    NetworkMap.partition_by_adoption(network_map)

    after = [dict(entry["node"]) for entry in network_map["node_list"]]
    assert before == after
    # And the field types specifically — a mutating implementation would
    # have coerced adopted through _as_bool in place.
    for entry in network_map["node_list"]:
        assert isinstance(entry["node"]["adopted"], bool)


def test_partition_by_adoption_accepts_string_adopted_too():
    """Tolerant of the pre-typing string shape, exactly like the deprecated
    method — a caller migrating incrementally is not forced to also retype
    its own data."""
    network_map = {
        "node_list": [
            {
                "node": node(
                    uuid="0367f391-ebf4-48b2-9f26-000000000001",
                    mac="aabbccddeeff",
                    name="n",
                    node_role=NodeRole.node,
                    ip="1.2.3.4",
                    adopted="True",
                )
            }
        ]
    }
    adopted, unadopted = NetworkMap.partition_by_adoption(network_map)
    assert len(adopted) == 1
    assert unadopted == ()
