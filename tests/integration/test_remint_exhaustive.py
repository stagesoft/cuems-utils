# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T027 — no old token survives anywhere (FR-016, SC-001).

A recursive search over the configuration directory **and the whole library**,
not over the documents the run happened to touch. The difference is the point:
a reach that missed a file would report success over exactly the set it looked
at, and this test looks at the set it did not.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import build_cluster
from tests.support.remint_harness import all_text, run_remint, state_dir


def test_no_old_token_survives_in_the_configuration_or_the_library(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=4,
                            trashed_projects=2)
    state = state_dir(tmp_path)
    code, out = run_remint(cluster, state)
    assert code == 0, out

    table = remint.SubstitutionTable.load(remint.table_path(state))
    haystack = all_text(cluster.conf) + all_text(cluster.library)
    for old in table.entries:
        assert old not in haystack, f"{old} survives somewhere under the cluster"


def test_every_new_token_is_actually_present(tmp_path):
    """The other half, and it is not implied: a run that deleted every
    occurrence rather than replacing it would pass the assertion above."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    state = state_dir(tmp_path)
    run_remint(cluster, state)

    table = remint.SubstitutionTable.load(remint.table_path(state))
    haystack = all_text(cluster.conf) + all_text(cluster.library)
    for new in table.entries.values():
        assert new in haystack


def test_the_count_of_occurrences_is_preserved(tmp_path):
    """One old occurrence becomes exactly one new occurrence. Neither dropped
    nor duplicated — a chained substitution would show up here as a count that
    moved."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    state = state_dir(tmp_path)
    before = all_text(cluster.conf) + all_text(cluster.library)

    run_remint(cluster, state)

    table = remint.SubstitutionTable.load(remint.table_path(state))
    after = all_text(cluster.conf) + all_text(cluster.library)
    for old, new in table.entries.items():
        assert after.count(new) == before.count(old)
