# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029e — the completion record, and the roll-call (FR-017a, SC-002b, §2.3).

What makes "the cluster is converged" a **countable** claim rather than an
impression. The controller's run exiting cleanly says nothing at all about any
other node — it never touched them — so a migration confirmed by watching the
controller finish is a migration confirmed by watching the wrong thing.

The operator holds one record per node, keys them by identity, and compares the
set against the network map's rows. A row with no record is a node the
migration did not reach, and is reported as **incomplete** rather than inferred
to be fine.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, state_dir


def _record_for(cluster, state, index=0):
    table = remint.SubstitutionTable.load(remint.table_path(state))
    new = table.entries[cluster.nodes[index].uuid]
    return remint.CompletionRecord.load(remint.completion_record_path(state, new))


def test_a_run_leaves_a_record_naming_the_table_scope_paths_and_results(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    code, out = run_remint(cluster, state)
    assert code == 0, out

    table = remint.SubstitutionTable.load(remint.table_path(state))
    record = _record_for(cluster, state)
    assert record.table_digest == table.digest()
    assert record.table_path == str(remint.table_path(state))
    assert record.scope == remint.BOTH
    assert record.rewritten
    assert record.verification["zero_old_tokens"] is True
    assert record.finished


def test_the_record_is_keyed_by_the_nodes_new_identity(tmp_path):
    """Its **new** one (§2.3). Keying on the old one would make the record
    unfindable from the map the moment the map was rewritten."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)
    table = remint.SubstitutionTable.load(remint.table_path(state))
    new = table.entries[cluster.nodes[0].uuid]

    assert remint.completion_record_path(state, new).is_file()
    assert not remint.completion_record_path(state, cluster.nodes[0].uuid).is_file()


def test_two_nodes_records_assemble_into_a_complete_roll_call(tmp_path):
    """The controller and one plain node, each running on its own directory,
    both applying the table the controller built."""
    controller = build_cluster(tmp_path / "controller", shapes=["uuid1", "uuid5"],
                               self_index=0)
    state_c = state_dir(tmp_path / "controller")
    assert run_remint(controller, state_c)[0] == 0

    table_path = remint.table_path(state_c)
    plain = build_cluster(tmp_path / "plain", shapes=["uuid1", "uuid5"], self_index=1)
    state_p = state_dir(tmp_path / "plain")
    assert run_remint(plain, state_p, extra=["--table", str(table_path)])[0] == 0

    records = [
        remint.CompletionRecord.load(p)
        for state in (state_c, state_p)
        for p in (state / remint.STATE_SUBDIR).glob("completion-*.json")
    ]
    complete, missing, unexpected = remint.roll_call(
        records, controller.conf / "network_map.xml"
    )
    assert complete, f"missing={missing}"
    assert missing == () and unexpected == ()


def test_a_three_node_map_with_two_records_is_reported_incomplete(tmp_path):
    """Not "converged". The whole reason the roll-call exists."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5", "uuid4"])
    state = state_dir(tmp_path)
    assert run_remint(cluster, state)[0] == 0

    records = [
        remint.CompletionRecord.load(p)
        for p in (state / remint.STATE_SUBDIR).glob("completion-*.json")
    ]
    assert len(records) == 1
    complete, missing, _unexpected = remint.roll_call(
        records, cluster.conf / "network_map.xml"
    )
    assert not complete
    assert len(missing) == 2


def test_a_run_that_found_nothing_to_do_still_leaves_a_record(tmp_path):
    """A converged node with no record is indistinguishable from one the
    migration never reached — and the roll-call counts records, not rewrites."""
    cluster = build_cluster(tmp_path, shapes=["uuid4", "uuid4b"])
    state = state_dir(tmp_path)
    code, out = run_remint(cluster, state)

    assert code == 0 and "already converged" in out
    record = remint.CompletionRecord.load(
        remint.completion_record_path(state, cluster.nodes[0].uuid)
    )
    assert record.rewritten == []
    assert record.verification["zero_old_tokens"] is True


def test_the_run_says_out_loud_that_one_record_is_not_a_cluster(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert "one completion record exists per row" in out
    assert "says nothing about the others" in out
