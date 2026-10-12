# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T026 — a node already carrying a uuid4 is untouched (FR-014).

Not "rewritten to the same bytes" — **untouched**. The distinction is not
cosmetic: the library reaches the nodes by a replication that compares size and
modification time with no checksum (research R11), so a file rewritten to
identical content still propagates as a change to every node in the cluster.
A migration that re-synced the entire library for nodes it did not touch is a
different and much larger operation than the one the guide describes.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, snapshot, state_dir


def test_a_converged_node_gets_no_table_entry(tmp_path):
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid4"], SHAPES["uuid1"]])
    state = state_dir(tmp_path)
    code, out = run_remint(cluster, state)
    assert code == 0, out

    table = remint.SubstitutionTable.load(remint.table_path(state))
    assert set(table.entries) == {SHAPES["uuid1"]}
    assert SHAPES["uuid4"] in (cluster.conf / "network_map.xml").read_text()


def test_a_file_mentioning_only_the_converged_node_is_not_rewritten(tmp_path):
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid4"], SHAPES["uuid1"]])
    state = state_dir(tmp_path)

    lone = cluster.project_dir("project_0") / "converged-only.xml"
    lone.write_text(
        '<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">'
        f"<nodes><node><uuid>{SHAPES['uuid4']}</uuid><mac>aabbccdd0000</mac></node></nodes>"
        "</cms:CuemsProjectMappings>",
        encoding="utf-8",
    )
    before = snapshot(lone.parent)[str(lone)]

    run_remint(cluster, state)

    assert snapshot(lone.parent)[str(lone)] == before


def test_the_converged_identity_survives_byte_identically(tmp_path):
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid4"], SHAPES["uuid1"]])
    run_remint(cluster, state_dir(tmp_path))
    text = "".join(p.read_text() for p in cluster.every_file())
    assert SHAPES["uuid4"] in text
    assert f"{SHAPES['uuid4']}_0" in text, "the converged node's compound outputs are untouched too"
