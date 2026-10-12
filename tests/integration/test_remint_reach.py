# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029 — the reach: any filename, optional mappings, trashed projects (FR-011, FR-012).

Each of the three is a way a real library differs from the one a developer
builds, and each would fail silently rather than loudly:

* a script under a name neither repository hardcodes would simply not be
  rewritten, and its outputs would resolve to nothing at the next show;
* a project with no ``mappings.xml`` would make a reach that required one skip
  the project **including its script**;
* ``trash/`` holds projects an operator can restore, which would come back
  carrying identities that no longer exist.
"""

from __future__ import annotations

import pytest

from cuemsutils.tools import remint
from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, state_dir


@pytest.mark.parametrize("script_name", [
    "script.xml",                       # cuems-engine's hardcoded name
    "cue_script.xml",                   # CuemsProjectManager's documented name
    "whatever-the-operator-called-it.xml",
])
def test_a_script_under_any_filename_is_rewritten(tmp_path, script_name):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], script_name=script_name)
    state = state_dir(tmp_path)

    code, out = run_remint(cluster, state)

    assert code == 0, out
    text = cluster.script_path("project_0").read_text()
    assert SHAPES["uuid1"] not in text
    table = remint.SubstitutionTable.load(remint.table_path(state))
    assert f"{table.entries[SHAPES['uuid1']]}_0" in text


def test_a_project_without_its_own_mappings_is_still_rewritten(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"],
                            with_project_mappings=False)
    state = state_dir(tmp_path)

    code, out = run_remint(cluster, state)

    assert code == 0, out
    assert SHAPES["uuid1"] not in cluster.script_path("project_0").read_text()


def test_trashed_projects_are_rewritten(tmp_path):
    """A trashed project can be restored. One restored after the migration
    would carry identities that no longer exist anywhere."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3,
                            trashed_projects=2)
    state = state_dir(tmp_path)

    code, out = run_remint(cluster, state)

    assert code == 0, out
    for name in ("project_0", "project_1"):
        assert SHAPES["uuid1"] not in cluster.script_path(name, trashed=True).read_text()
        assert SHAPES["uuid1"] not in cluster.mappings_path(name, trashed=True).read_text()


def test_a_file_that_is_neither_a_script_nor_mappings_is_left_alone(tmp_path):
    """§10.7 leaves open whether any *other* file in a project directory embeds
    an output name. Root-element identification answers that per file, and the
    answer for an unrelated document is "not mine to rewrite"."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    stray = cluster.project_dir("project_0") / "operator-notes.xml"
    stray.write_text(f"<notes><about>{SHAPES['uuid1']}</about></notes>", encoding="utf-8")

    run_remint(cluster, state_dir(tmp_path))

    assert SHAPES["uuid1"] in stray.read_text()
