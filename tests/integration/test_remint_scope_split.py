# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029c — the scope split (FR-011a, FR-019c, contracts/cli-remint.md).

The two reaches are not the same operation run twice. Configuration documents
are **per node**: every node rewrites its own, from the table the controller
handed it. The library is **controller-authoritative**: rewritten once, on the
controller, and carried to the nodes by the project deployer's existing
replication (research R11).

The three things that follow, and each is a distinct failure if got wrong:

* a plain node that rewrote its library replica would be N nodes independently
  rewriting replicas of one authoritative tree, with ``--delete`` replication
  running against them;
* a plain node that **minted its own table** would give itself an identity the
  rest of the cluster has never heard of — the divergence §10.3 warns about;
* a table whose controller is the map's controller is **accepted**, which is
  the normal case everywhere but one, and refusing it would refuse the table's
  whole purpose.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, snapshot, state_dir


def _plain_node(tmp_path):
    """A cluster directory that *is* node 1 — not the controller."""
    return build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=1)


def _handed_table(tmp_path):
    table = remint.build_table(
        [SHAPES["uuid1"], SHAPES["uuid5"]],
        controller=SHAPES["uuid1"],           # the map's controller row
        scope=remint.CONFIGURATION,
    )
    path = tmp_path / "handed-over.json"
    table.save(path)
    return path


def test_a_plain_node_with_a_table_rewrites_only_its_configuration(tmp_path):
    cluster = _plain_node(tmp_path)
    state = state_dir(tmp_path)
    library_before = snapshot(cluster.library)

    code, out = run_remint(cluster, state,
                           extra=["--table", str(_handed_table(tmp_path))])

    assert code == 0, out
    assert SHAPES["uuid5"] not in (cluster.conf / "settings.xml").read_text()
    assert snapshot(cluster.library) == library_before, \
        "a plain node rewrote its library replica"


def test_a_plain_node_says_why_its_library_is_untouched(tmp_path):
    """An operator who saw the library unchanged and was told nothing would
    reasonably conclude the run had failed."""
    cluster = _plain_node(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path),
                           extra=["--table", str(_handed_table(tmp_path))])
    assert "not the controller" in out
    assert "replication" in out


def test_a_plain_node_without_a_table_refuses_rather_than_minting(tmp_path):
    cluster = _plain_node(tmp_path)
    state = state_dir(tmp_path)
    before = snapshot(cluster.conf)

    code, out = run_remint(cluster, state)

    assert code == 1
    assert "not the controller and no substitution table" in out
    assert not remint.table_path(state).is_file()
    assert snapshot(cluster.conf) == before


def test_the_refusal_names_the_flag_that_is_the_way_forward(tmp_path):
    """``--table`` is how a plain node proceeds, not an override. A refusal
    that did not say so reads as a dead end."""
    cluster = _plain_node(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert "--table" in out


def test_a_table_whose_controller_is_the_maps_controller_is_accepted(tmp_path):
    """The normal case everywhere but one. Stated as its own test because an
    earlier draft of the design had the refusal backwards and would have
    refused exactly this."""
    cluster = _plain_node(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path),
                           extra=["--table", str(_handed_table(tmp_path))])
    assert code == 0, out


def test_the_controller_rewrites_both(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=0)
    state = state_dir(tmp_path)

    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert remint.SubstitutionTable.load(remint.table_path(state)).scope == remint.BOTH
    assert SHAPES["uuid1"] not in cluster.script_path("project_0").read_text()


def test_the_completion_record_names_the_scope(tmp_path):
    cluster = _plain_node(tmp_path)
    state = state_dir(tmp_path)
    handed = _handed_table(tmp_path)
    run_remint(cluster, state, extra=["--table", str(handed)])

    table = remint.SubstitutionTable.load(handed)
    new = table.entries[SHAPES["uuid5"]]
    record = remint.CompletionRecord.load(remint.completion_record_path(state, new))
    assert record.scope == remint.CONFIGURATION
