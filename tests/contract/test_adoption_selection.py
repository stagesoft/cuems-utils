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
"""

from __future__ import annotations

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


def test_get_nodes_by_adoption_accepts_already_typed_booleans():
    """C6 / research R7 — must fail before T008, pass after.

    The one interaction this feature's typing creates: a caller that already
    holds ``bool`` values (as every caller will, once ``network_map`` runs the
    adapter table) must not crash the one config accessor that post-processes
    them.
    """
    network_map_dict = _network_map_dict(adopted=True, online=False)
    nodes, new_nodes = NetworkMap.get_nodes_by_adoption(network_map_dict)
    assert len(nodes) == 1
    assert new_nodes == []
    assert nodes[0]["node"]["adopted"] is True
    assert nodes[0]["node"]["online"] is False


def test_get_nodes_by_adoption_still_accepts_strings():
    """The pre-typing call shape must keep working — this method is retained
    (Assumption 8) until feature 008 migrates its caller."""
    network_map_dict = _network_map_dict(adopted="True", online="False")
    nodes, new_nodes = NetworkMap.get_nodes_by_adoption(network_map_dict)
    assert len(nodes) == 1
    assert nodes[0]["node"]["adopted"] is True
    assert nodes[0]["node"]["online"] is False


def test_get_nodes_by_adoption_partitions_unadopted_typed_booleans():
    network_map_dict = _network_map_dict(adopted=False, online=True)
    nodes, new_nodes = NetworkMap.get_nodes_by_adoption(network_map_dict)
    assert nodes == []
    assert len(new_nodes) == 1
    assert new_nodes[0]["node"]["adopted"] is False
