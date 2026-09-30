# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029d — the re-mint runs on documents the tightened schema refuses (FR-006a).

**Not made redundant by US2 landing before US3.** The re-mint is what a
deployed cluster runs *after* upgrading to the narrowed library, so by the time
it runs, every document it exists to repair is invalid by definition. Ordering
the phases in this repository says nothing about the order of events on a node.

The collision abort is the sharper case. FR-019a refuses a colliding map **at
read time**, so the validating path cannot supply the two rows the abort
message has to name — the tool that reports the fault must be able to read the
document that has it. That is why stdlib XML is a requirement here and not a
technique.
"""

from __future__ import annotations

from cuemsutils.tools import library_reach, remint
from tests.support.cluster_fixture import SHAPES, build_cluster, mac_for
from tests.support.remint_harness import run_remint, state_dir


def test_the_survey_runs_over_a_uuid1_cluster(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    found = remint.survey(cluster.conf, library_reach.reach_library(cluster.library))
    assert set(found.node_identities) == {SHAPES["uuid1"], SHAPES["uuid5"]}
    assert found.needs_migration
    assert found.bytes_read > 0


def test_the_survey_runs_over_a_map_the_new_rule_refuses(tmp_path):
    """Two rows sharing an identity: a map that loads today (``NodeIndex.merge``
    collapsing the duplicate silently, M-l) and raises ``ValidationError`` for
    every reader once FR-019a's rule lands."""
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid1"], SHAPES["uuid1"]])
    found = remint.survey(cluster.conf, library_reach.reach_library(cluster.library))
    assert SHAPES["uuid1"] in found.node_identities


def test_the_collision_abort_names_both_rows_by_reading_the_refused_map(tmp_path):
    """It can only name them by having read the map — which is the point."""
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid1"], SHAPES["uuid1"]])
    found = remint.collisions(cluster.conf / "network_map.xml")
    assert len(found) == 1
    assert set(found[0].macs) == {mac_for(0), mac_for(1)}

    code, out = run_remint(cluster, state_dir(tmp_path))
    assert code == 1
    assert mac_for(0) in out and mac_for(1) in out


def test_a_structurally_invalid_document_does_not_stop_the_run(tmp_path):
    """Missing required elements are the *normal* state of a document mid
    migration. The rewrite does not care, and the verification reports
    afterwards rather than refusing beforehand."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    stray = cluster.project_dir("project_0") / "mappings.xml"
    stray.write_text(
        '<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">'
        f"<nodes><node><uuid>{SHAPES['uuid1']}</uuid></node></nodes>"
        "</cms:CuemsProjectMappings>",
        encoding="utf-8",
    )

    code, out = run_remint(cluster, state_dir(tmp_path))

    assert SHAPES["uuid1"] not in stray.read_text(), "the rewrite skipped an invalid document"
    assert code == 2, "and the verification said so afterwards"
    assert "does not validate" in out


def test_the_pre_write_paths_never_import_the_validating_reader(tmp_path):
    """The design property, observed. Everything up to the verify step reads
    with stdlib XML, so nothing in ``cuemsutils.xml.settings`` has been touched
    by the time the survey and the collision check are done."""
    import sys

    for module in ("cuemsutils.xml.settings", "cuemsutils.tools.ConfigManager"):
        sys.modules.pop(module, None)

    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    remint.survey(cluster.conf, library_reach.reach_library(cluster.library))
    remint.collisions(cluster.conf / "network_map.xml")

    assert "cuemsutils.xml.settings" not in sys.modules
    assert "cuemsutils.tools.ConfigManager" not in sys.modules
