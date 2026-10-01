# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T023 — a second run substitutes nothing and changes zero bytes (FR-013, SC-004).

"Zero bytes in zero files" is stronger than "the same bytes": a re-serialising
implementation would produce identical content and a fresh modification time,
and under the replication in use (``rsync -rt``, no checksum — research R11)
that fresh time is a *change* as far as every node is concerned. So the
assertion is over content **and** modification time.

It is over the **documents**, not over the tool's state directory. The
completion record is meant to change on every run — it is this node's evidence
that it was reached, and a run that found nothing to do is still evidence
(FR-017a).
"""

from __future__ import annotations

from tests.support.cluster_fixture import build_cluster
from tests.support.remint_harness import documents_snapshot, run_remint, state_dir


def test_a_second_run_over_a_converged_cluster_changes_nothing(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)

    code, out = run_remint(cluster, state)
    assert code == 0, out

    after_first = documents_snapshot(cluster)
    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert documents_snapshot(cluster) == after_first


def test_an_already_converged_cluster_does_nothing_on_the_first_run(tmp_path):
    """The table is empty, so there is nothing to persist and nothing to write.
    This is FR-014 at cluster scale: a converged node is not rewritten to the
    same bytes, it is not rewritten."""
    cluster = build_cluster(tmp_path, shapes=["uuid4", "uuid4b"])
    state = state_dir(tmp_path)
    before = documents_snapshot(cluster)

    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert "already converged" in out
    assert documents_snapshot(cluster) == before


def test_a_third_run_is_still_a_no_op(tmp_path):
    """Idempotence is not a property of the second run in particular."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)
    after_first = documents_snapshot(cluster)
    run_remint(cluster, state)
    run_remint(cluster, state)
    assert documents_snapshot(cluster) == after_first
