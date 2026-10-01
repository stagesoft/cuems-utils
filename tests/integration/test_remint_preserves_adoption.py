# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T028 — adoption state is identical before and after (FR-018, SC-003).

Compared **keyed by MAC**, which is the whole content of the test. The identity
is the thing that changes, so a comparison keyed on it would be comparing two
different nodes and would report every adoption as preserved no matter what
happened. "Match by uuid, key by MAC" is the map's own practice, and this is
the one comparison where only the MAC survives the operation.

Losing an adoption is not a cosmetic fault: §9.5 establishes that a lost node
identity is now permanent, and an unadopted node is one the controller will not
dispatch to.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import (
    NodeSpec,
    build_cluster,
    mac_for,
    network_map_xml,
)
from tests.support.remint_harness import run_remint, state_dir


def test_adopted_and_online_are_identical_per_node(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    before = remint.adoption_state(cluster.conf / "network_map.xml")

    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert remint.adoption_state(cluster.conf / "network_map.xml") == before


def test_a_mixed_adoption_state_survives_unchanged(tmp_path):
    """The case that would pass trivially if every node were adopted."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    rows = [
        NodeSpec(cluster.nodes[0].uuid, mac_for(0), "controller", "n0", "10.0.0.1",
                 adopted="True", online="True"),
        NodeSpec(cluster.nodes[1].uuid, mac_for(1), "node", "n1", "10.0.0.2",
                 adopted="False", online="False"),
    ]
    (cluster.conf / "network_map.xml").write_text(network_map_xml(rows), encoding="utf-8")
    state = state_dir(tmp_path)

    before = remint.adoption_state(cluster.conf / "network_map.xml")
    assert before[mac_for(0)] == ("True", "True")
    assert before[mac_for(1)] == ("False", "False")

    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert remint.adoption_state(cluster.conf / "network_map.xml") == before


def test_the_verification_reports_adoption_as_checked(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)

    record = remint.CompletionRecord.load(
        remint.completion_record_path(state, _new_identity(cluster, state))
    )
    assert record.verification["adoption_unchanged"] is True


def _new_identity(cluster, state):
    table = remint.SubstitutionTable.load(remint.table_path(state))
    return table.entries[cluster.nodes[0].uuid]
