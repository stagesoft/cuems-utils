# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T012 — the widened exit classes and their precedence (FR-004, contracts/cli-check.md).

Class **1 widens**: it meant "a mirror disagrees with the source" and now also
means "an identity is not converged". Both mean *actionable, run the tool named
in ``fix``*, so the semantics hold; the ``verdict`` field is what distinguishes
them.

Precedence is unchanged and still **3 > 2 > 1**, which is asserted here rather
than assumed because the widening added a fourth thing that can set class 1 and
precedence is exactly what a fourth entrant can break.
"""

from __future__ import annotations

from cuemsutils.tools import identity_check
from tests.support.cluster_fixture import SHAPES, build_cluster


def _check(cluster, tmp_path, **kwargs):
    return identity_check.check(
        cluster.conf,
        avahi_service=kwargs.pop("avahi", cluster.avahi),
        library=kwargs.pop("library", cluster.library),
        **kwargs,
    )


def test_class_0_is_converged_provisioned_and_coherent(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid4", "uuid4b"])
    report = _check(cluster, tmp_path)
    assert report.exit_code == 0
    assert report.verdict == "coherent"
    assert report.fix == ""


def test_class_1_migration_needed(tmp_path):
    """The widening. Before this feature a uuid1 cluster reported class 0 —
    coherent, and unmigratable, with no way for an operator to learn either."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    report = _check(cluster, tmp_path)
    assert report.exit_code == 1
    assert report.verdict == "migration-needed"
    assert "--remint" in report.fix


def test_class_1_mirror_disagreement_keeps_its_shipped_verdict(tmp_path):
    """Principle III: every shipped verdict still means what it meant. A
    consumer keying on ``mismatch`` sees it for the same condition as before."""
    cluster = build_cluster(tmp_path, shapes=["uuid4", "uuid4b"])
    (cluster.conf / "network_map.xml").write_text(
        (cluster.conf / "network_map.xml").read_text().replace(
            SHAPES["uuid4"], "11111111-2222-4333-8444-555555555555"
        ),
        encoding="utf-8",
    )
    report = _check(cluster, tmp_path)
    assert report.exit_code == 1
    assert report.verdict == "mismatch"


def test_a_mirror_disagreement_outranks_migration_needed_within_class_1(tmp_path):
    """Both are class 1, and the shipped verdict wins the field — which is what
    "extended rather than replaced" means for a consumer that already keys on
    it. The migration is not hidden: it is named in ``fix`` and enumerated in
    the occurrences."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "network_map.xml").write_text(
        (cluster.conf / "network_map.xml").read_text().replace(
            SHAPES["uuid1"], "0367f391-ebf4-11b2-9f26-0000000000ff"
        ),
        encoding="utf-8",
    )
    report = _check(cluster, tmp_path)
    assert report.exit_code == 1
    assert report.verdict == "mismatch"
    assert "--remint" in report.fix


def test_class_2_absent_or_unreadable(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "network_map.xml").unlink()
    report = _check(cluster, tmp_path)
    assert report.exit_code == 2


def test_class_3_sentinel(tmp_path):
    cluster = build_cluster(tmp_path, identities=[SHAPES["sentinel"], SHAPES["uuid4"]])
    report = _check(cluster, tmp_path)
    assert report.exit_code == 3
    assert report.verdict == identity_check.NOT_PROVISIONED


def test_precedence_three_beats_two_beats_one(tmp_path):
    """A tree carrying all three conditions at once reports the highest."""
    cluster = build_cluster(tmp_path, identities=[SHAPES["sentinel"], SHAPES["uuid1"]])
    (cluster.conf / "network_map.xml").unlink()          # would be 2
    report = _check(cluster, tmp_path)
    assert report.exit_code == 3

    cluster = build_cluster(tmp_path / "two", shapes=["uuid1", "uuid5"])
    (cluster.conf / "default_mappings.xml").unlink()     # 2 over 1
    report = _check(cluster, tmp_path)
    assert report.exit_code == 2


def test_a_converged_cluster_with_no_library_is_still_class_0(tmp_path):
    """The degradation is a reported condition, not a failure (FR-005)."""
    cluster = build_cluster(tmp_path, shapes=["uuid4", "uuid4b"])
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=tmp_path / "gone"
    )
    assert report.exit_code == 0
    assert report.notes
