"""S1 (US6), T073-T075/T077 — the identity collision as data, in two
layers (research R4, contract C5).

The internal rule stays a ``ValueError`` (T076, extended in
``test_node_uuid_unique_rule.py``); the public accessor promotes it to
``NodeIdentityCollisionError(ValidationError)`` with the file path
attached and ``violation`` populated.
"""

from __future__ import annotations

import pytest

from cuemsutils.errors import NodeIdentityCollisionError, ValidationError
from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.settings import NetworkMap
from tests.support.cluster_fixture import SHAPES, NodeSpec, mac_for, network_map_xml


def _write(tmp_path, *identities):
    rows = [
        NodeSpec(uuid, mac_for(i), "controller" if i == 0 else "node", f"n{i}",
                 f"10.0.0.{i + 1}")
        for i, uuid in enumerate(identities)
    ]
    path = tmp_path / "network_map.xml"
    path.write_text(network_map_xml(rows), encoding="utf-8")
    return path


def test_a_colliding_map_raises_a_nameable_type_carrying_structured_data(tmp_path):
    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"])

    with pytest.raises(NodeIdentityCollisionError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")

    exc = raised.value
    assert SHAPES["uuid4"] in exc.collisions
    macs = exc.collisions[SHAPES["uuid4"]]
    assert mac_for(0) in macs and mac_for(1) in macs
    assert exc.file == str(path)
    assert exc.violation.location == (SHAPES["uuid4"], "uuid")


def test_the_new_type_is_exported_and_documented():
    """FR-065a — a type a consumer cannot import is a type it cannot
    catch."""
    from cuemsutils import errors

    assert "NodeIdentityCollisionError" in errors.__all__
    assert errors.NodeIdentityCollisionError is NodeIdentityCollisionError
    assert issubclass(NodeIdentityCollisionError, ValidationError)


def test_the_operator_facing_message_is_unchanged(tmp_path):
    """FR-063/FR-UX-002 — the remedy sentence and the command it names
    survive the structuring unchanged."""
    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"])

    with pytest.raises(NodeIdentityCollisionError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")

    message = str(raised.value)
    assert "node identities are not unique" in message
    assert "cuems-init-node --remint" in message
    assert mac_for(0) in message and mac_for(1) in message


def test_message_shape_recognition_still_answers(tmp_path):
    """FR-064 — any caller still matching on message shape keeps
    answering."""
    from cuemsutils.errors import node_identity_collision_message

    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"])
    with pytest.raises(NodeIdentityCollisionError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")

    assert node_identity_collision_message(str(path), raised.value) is not None


def test_two_distinct_collisions_are_distinguishable_without_reparsing(tmp_path):
    """FR-062 — a consumer can log once per distinct identity, reading
    ``.collisions`` rather than re-parsing the prose."""
    rows = [
        NodeSpec(SHAPES["uuid4"], mac_for(0), "controller", "n0", "10.0.0.1"),
        NodeSpec(SHAPES["uuid4"], mac_for(1), "node", "n1", "10.0.0.2"),
        NodeSpec(SHAPES["uuid4b"], mac_for(2), "node", "n2", "10.0.0.3"),
        NodeSpec(SHAPES["uuid4b"], mac_for(3), "node", "n3", "10.0.0.4"),
    ]
    path = tmp_path / "network_map.xml"
    path.write_text(network_map_xml(rows), encoding="utf-8")

    with pytest.raises(NodeIdentityCollisionError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")

    exc = raised.value
    assert set(exc.collisions) == {SHAPES["uuid4"], SHAPES["uuid4b"]}
    assert len(exc.collisions[SHAPES["uuid4"]]) == 2
    assert len(exc.collisions[SHAPES["uuid4b"]]) == 2
