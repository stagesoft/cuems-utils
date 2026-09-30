# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T025 — two nodes sharing an identity: abort, naming both, writing nothing (FR-019).

Why abort rather than resolve. Splitting a shared identity is **safe in the
configuration documents** — the MAC discriminates — and **unsafe in the
library**, where the compound ``<identity>_<output>`` prefix is the only record
of which node an output belongs to. No discriminator exists there, so a split
would silently reassign one node's entire output set (data-model §4.2).

The abort runs **after the survey and before the table is built**, which is
earlier than "before any write": an abort then costs not even a minted
identity.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import SHAPES, build_cluster, mac_for
from tests.support.remint_harness import documents_snapshot, run_remint, state_dir


def _colliding(tmp_path):
    return build_cluster(tmp_path, identities=[SHAPES["uuid1"], SHAPES["uuid1"]])


def test_the_run_aborts(tmp_path):
    cluster = _colliding(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert code == 1
    assert "share an identity" in out


def test_both_rows_are_named_with_their_macs(tmp_path):
    """The MAC is the only thing that tells the two rows apart, so an abort
    that named only the identity would leave the operator no way to act."""
    cluster = _colliding(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert f"mac={mac_for(0)}" in out
    assert f"mac={mac_for(1)}" in out
    assert SHAPES["uuid1"] in out


def test_every_script_referencing_the_token_is_named(tmp_path):
    """Because that is where the harm would be. An operator deciding which row
    is the real node needs to see which outputs are at stake."""
    cluster = _colliding(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert str(cluster.script_path("project_0")) in out
    assert str(cluster.script_path("project_1")) in out


def test_no_file_is_modified(tmp_path):
    cluster = _colliding(tmp_path)
    before = documents_snapshot(cluster)
    run_remint(cluster, state_dir(tmp_path))
    assert documents_snapshot(cluster) == before


def test_not_even_a_table_is_minted(tmp_path):
    """The abort is ordered before the table is built, not merely before the
    first write. A minted-but-unused table on disk would be loaded by the next
    run and applied without anyone deciding to."""
    cluster = _colliding(tmp_path)
    state = state_dir(tmp_path)
    run_remint(cluster, state)
    assert not remint.table_path(state).is_file()


def test_the_message_points_at_the_manual_procedure(tmp_path):
    """A cluster arriving with a collision is stopped by two requirements —
    the re-mint aborts (FR-019) and the library will not guess (FR-019a) — and
    released by neither. The way out is the guide's manual procedure, and it
    must be run **before** the narrowing, while the map still loads (FR-036b)."""
    cluster = _colliding(tmp_path)
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert "by hand" in out
    assert "while the map still loads" in out


def test_a_cluster_with_no_collision_does_not_abort(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    code, out = run_remint(cluster, state_dir(tmp_path))
    assert code == 0, out
