# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T021 — the table exists on disk before the first document is written (FR-007).

The table is the operation's **only durable record**: its loss strands a partly
rewritten cluster with no way to learn which identity replaced which. So the
ordering is not a nicety — every write after the first is recoverable only
because this one happened before it.

Asserted by interception rather than by reading the source: a future refactor
that moved the persist below the loop would leave every other test in this
phase green.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import build_cluster
from tests.support.remint_harness import run_remint, state_dir


def test_the_table_is_on_disk_before_any_document_is_rewritten(tmp_path, monkeypatch):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    seen = {}

    real_apply = remint.apply_table

    def watching(table, documents, table_file=None):
        seen["table_on_disk_at_first_write"] = remint.table_path(state).is_file()
        return real_apply(table, documents, table_file=table_file)

    monkeypatch.setattr(remint, "apply_table", watching)
    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert seen["table_on_disk_at_first_write"] is True


def test_the_persisted_table_carries_what_recovery_needs(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)

    table = remint.SubstitutionTable.load(remint.table_path(state))
    assert table.entries, "a table with no mapping records nothing"
    assert table.controller == cluster.controller.uuid
    assert table.created
    assert table.scope == remint.BOTH
    assert table.applied, "applied is what makes the operation resumable"


def test_a_dry_run_writes_no_table_at_all(tmp_path):
    """FR-PERF-003: ``--dry-run`` surveys, estimates and reports, and writes
    nothing — **including no table**. A table left behind by a dry run would be
    loaded by the next real run, which is a write the operator did not ask for
    and did not confirm."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    before = {p for p in tmp_path.rglob("*") if p.is_file()}

    code, out = run_remint(cluster, state, extra=["--dry-run"])

    assert code == 0, out
    assert not remint.table_path(state).is_file()
    assert {p for p in tmp_path.rglob("*") if p.is_file()} == before
    assert "would substitute" in out
