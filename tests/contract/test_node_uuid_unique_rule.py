# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T048 — node-identity uniqueness as a registered rule (FR-019a, SC-012, research R2).

Modelled on ``action_target_resolves``, the closest existing precedent in both
scope and repairability.

``document_scoped=True`` because a row cannot see its siblings, and uniqueness
is a question about all of them at once.

``repairable=False`` is **forced by the domain, not chosen for convenience**:
the library cannot know which of two colliding rows is the real node, so there
is no defensible default to repair *to*. Fabricating one would be worse than
refusing, because it would look resolved.

This is the feature's only change that turns a **successful read into an
exception**, and it reaches every repository that reads the map — which is why
FR-032a makes the second census column blocking.
"""

from __future__ import annotations

import pytest

from cuemsutils.errors import ValidationError
from cuemsutils.tools.ConfigBase import load_config_document
from cuemsutils.xml.settings import NetworkMap
from cuemsutils.xml.validators import RULES
from tests.support.cluster_fixture import SHAPES, NodeSpec, mac_for, network_map_xml

RULE = "node_uuid_unique"


def test_the_rule_is_registered_with_the_declared_scope_and_repairability():
    assert RULE in RULES
    rule = RULES[RULE]
    assert rule.document_scoped is True
    assert rule.repairable is False
    assert rule.applies_to == (("node", "uuid"),)


def _write(tmp_path, *identities):
    rows = [
        NodeSpec(uuid, mac_for(i), "controller" if i == 0 else "node", f"n{i}",
                 f"10.0.0.{i + 1}")
        for i, uuid in enumerate(identities)
    ]
    path = tmp_path / "network_map.xml"
    path.write_text(network_map_xml(rows), encoding="utf-8")
    return path


def test_a_colliding_map_raises_validation_error_naming_both_rows(tmp_path):
    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"])
    with pytest.raises(ValidationError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")
    message = str(raised.value)
    assert SHAPES["uuid4"] in message
    assert mac_for(0) in message and mac_for(1) in message


def test_the_message_names_the_repair_tool(tmp_path):
    """FR-024's reporting half, produced in the **validation error path**
    because no conversion exists to produce it (FR-023)."""
    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"])
    with pytest.raises(ValidationError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")
    assert "cuems-init-node" in str(raised.value)


def test_it_is_a_validation_error_and_not_the_generic_schema_error(tmp_path):
    """The distinction feature 008 established for ``project_mappings``: a
    caller can tell a **semantic** violation from a **structural** one the same
    way it can for a show document. Matched on the rule's own wording rather
    than by exception type, because ``xmlschema``'s own T1 errors are *also*
    ``ValueError`` subclasses."""
    from cuemsutils.errors import SchemaError

    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"])
    with pytest.raises(ValidationError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")
    assert not isinstance(raised.value, SchemaError)


def test_a_map_with_distinct_identities_loads(tmp_path):
    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4b"])
    document = load_config_document(NetworkMap, str(path), "network_map")
    assert len(document.get_dict()["node_list"]) == 2


def test_three_rows_sharing_one_identity_name_all_three(tmp_path):
    path = _write(tmp_path, SHAPES["uuid4"], SHAPES["uuid4"], SHAPES["uuid4"])
    with pytest.raises(ValidationError) as raised:
        load_config_document(NetworkMap, str(path), "network_map")
    message = str(raised.value)
    for i in range(3):
        assert mac_for(i) in message


def test_an_empty_map_is_not_a_collision(tmp_path):
    """``node_list`` is ``minOccurs="0"`` and an empty one decodes to a key
    present with value ``None`` — the shape ``cuems-common`` ships to every
    node."""
    path = tmp_path / "network_map.xml"
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<cms:CuemsNetworkMap xmlns:cms="https://stagelab.coop/cuems/" doc_version="2">'
        "<node_list /></cms:CuemsNetworkMap>\n",
        encoding="utf-8",
    )
    load_config_document(NetworkMap, str(path), "network_map")


def test_the_rule_is_not_repairable_so_nothing_substitutes_a_default(tmp_path):
    """A count violation has no single substitute value that would decide which
    duplicate to keep, and the library has no way to know which row is real. The
    flag is a statement about the repair *model*, not a gap in it."""
    assert RULES[RULE].repairable is False
