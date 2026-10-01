# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T022 — resume, and the refusal stated in the right direction (FR-008, SC-006).

Two things, and the second is here because an earlier draft of the design had
it backwards.

**Resume** (data-model §2.2): an interrupted run leaves the table and its
``applied`` list on disk. A re-run *loads* the table rather than rebuilding it,
so no node receives a second new identity — which would be unrecoverable, since
the first new identity is by then already in half the library.

**The refusal** (data-model §2.2a): a table whose ``controller`` is not *this
node* is the **normal** case on every node but one. That is what distribution
means, and refusing it would refuse the table's whole purpose. The refusal is
on a table whose controller is not **the map's** controller — one minted by
something with no authority to mint it.
"""

from __future__ import annotations

import json

from cuemsutils.tools import remint
from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, state_dir


def _interrupt_after(count, monkeypatch):
    """Let ``apply_table`` rewrite ``count`` documents, then stop hard."""
    real = remint.apply_table

    def partial(table, documents, table_file=None):
        return real(table, list(documents)[:count], table_file=table_file)

    monkeypatch.setattr(remint, "apply_table", partial)


def test_a_re_run_loads_the_table_rather_than_rebuilding_it(tmp_path, monkeypatch):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)

    _interrupt_after(2, monkeypatch)
    run_remint(cluster, state)
    interrupted = remint.SubstitutionTable.load(remint.table_path(state))
    assert 0 < len(interrupted.applied) < 9

    monkeypatch.undo()
    code, out = run_remint(cluster, state, extra=["--resume"])

    assert code == 0, out
    resumed = remint.SubstitutionTable.load(remint.table_path(state))
    assert resumed.entries == interrupted.entries, "the table was rebuilt, not loaded"
    assert len(resumed.applied) > len(interrupted.applied)


def test_no_node_receives_a_second_new_identity(tmp_path, monkeypatch):
    """The failure this exists to prevent: half the library carrying identity
    A and the other half identity B, with the table naming only B."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)

    _interrupt_after(1, monkeypatch)
    run_remint(cluster, state)
    first = remint.SubstitutionTable.load(remint.table_path(state)).entries

    monkeypatch.undo()
    run_remint(cluster, state, extra=["--resume"])
    second = remint.SubstitutionTable.load(remint.table_path(state)).entries

    assert first == second
    text = "".join(p.read_text() for p in cluster.every_file())
    for old, new in second.items():
        assert old not in text
        assert new in text


def test_applied_paths_are_not_rewritten_twice(tmp_path, monkeypatch):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    _interrupt_after(2, monkeypatch)
    run_remint(cluster, state)

    done = list(remint.SubstitutionTable.load(remint.table_path(state)).applied)
    stamps = {p: (cluster.root / p).stat().st_mtime_ns for p in []}
    stamps = {p: __import__("os").stat(p).st_mtime_ns for p in done}

    monkeypatch.undo()
    run_remint(cluster, state, extra=["--resume"])

    for path, before in stamps.items():
        assert __import__("os").stat(path).st_mtime_ns == before, (
            f"{path} was rewritten a second time despite being in applied"
        )


def test_a_table_built_by_another_node_is_accepted(tmp_path):
    """**Not a refusal.** This is the normal case on every node but one: the
    controller built the table, the operator copied it here, and this node
    applies it to its own configuration."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=1)
    state = state_dir(tmp_path)
    table = remint.build_table(
        [SHAPES["uuid1"], SHAPES["uuid5"]], controller=SHAPES["uuid1"],
        scope=remint.CONFIGURATION,
    )
    handed = tmp_path / "from-the-controller.json"
    table.save(handed)

    code, out = run_remint(cluster, state, extra=["--table", str(handed)])

    assert code == 0, out
    assert SHAPES["uuid5"] not in (cluster.conf / "settings.xml").read_text()


def test_a_table_built_by_something_that_is_not_the_controller_is_refused(tmp_path):
    """The refusal, in the direction data-model §2.2a states it. This table's
    ``controller`` names a node that is not the map's controller, so it was
    minted by something with no authority to mint it."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], self_index=1)
    state = state_dir(tmp_path)
    rogue = remint.build_table(
        [SHAPES["uuid1"], SHAPES["uuid5"]], controller=SHAPES["uuid5"],
        scope=remint.CONFIGURATION,
    )
    handed = tmp_path / "rogue.json"
    rogue.save(handed)

    code, out = run_remint(cluster, state, extra=["--table", str(handed)])

    assert code == 1
    assert "no authority" in out
    assert SHAPES["uuid1"] in (cluster.conf / "network_map.xml").read_text(), \
        "a refused run wrote something"


def test_the_table_on_disk_is_never_silently_rebuilt(tmp_path):
    """Without ``--resume`` either. Rebuilding over an existing table is how a
    node gets a second identity, and there is no case where ignoring the
    operation's only durable record is the right thing to do."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)
    first = json.loads(remint.table_path(state).read_text())["entries"]

    run_remint(cluster, state)
    assert json.loads(remint.table_path(state).read_text())["entries"] == first
