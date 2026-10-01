# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T032 — backups are not rewritten (FR-015).

Both spellings this project makes: ``<name>.<timestamp>.bak``, which
``xml/convert_documents.py`` writes before every conversion, and ``.bak-<date>``,
which the migration procedure tells an operator to take.

Leaving them alone is correct and is also a **hazard the migration guide must
state**: restoring one after the re-mint reintroduces a stale identity, and
nothing at any layer would report it — the restored document is schema-valid,
and the identity it names simply no longer exists.
"""

from __future__ import annotations

from tests.support.cluster_fixture import SHAPES, build_cluster
from tests.support.remint_harness import run_remint, snapshot, state_dir


def test_conversion_and_operator_backups_are_both_left_alone(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    directory = cluster.project_dir("project_0")
    original = cluster.script_path("project_0").read_text()
    backups = [
        directory / "script.xml.20260930T120000.bak",
        directory / "script.xml.bak-20260930",
        directory / "script.xml~",
    ]
    for path in backups:
        path.write_text(original, encoding="utf-8")
    before = {str(p): snapshot(directory)[str(p)] for p in backups}

    code, out = run_remint(cluster, state_dir(tmp_path))

    assert code == 0, out
    after = snapshot(directory)
    for path in backups:
        assert after[str(path)] == before[str(path)]
        assert SHAPES["uuid1"] in path.read_text(), \
            "a backup was rewritten, which defeats the purpose of having taken it"


def test_a_backup_of_a_configuration_document_is_left_alone(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    backup = cluster.conf / "network_map.xml.bak-20260930"
    backup.write_text((cluster.conf / "network_map.xml").read_text(), encoding="utf-8")

    run_remint(cluster, state_dir(tmp_path))

    assert SHAPES["uuid1"] in backup.read_text()
