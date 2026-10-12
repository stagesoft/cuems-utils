# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029a — every touched document validates, and a full load succeeds (FR-017, SC-002).

**Distinct from T027**, which proves only that no old token survives. A file
can be token-free and still unloadable: the substitution could have produced a
value the schema refuses, or corrupted the document on the way through, or left
``settings.xml`` naming an identity the map no longer has. "No old token" and
"this node still works" are two claims, and only one of them is what an
operator cares about on the morning after.
"""

from __future__ import annotations

from cuemsutils.tools import remint
from tests.support.cluster_fixture import build_cluster
from tests.support.remint_harness import run_remint, state_dir


def _table(state):
    return remint.SubstitutionTable.load(remint.table_path(state))


def test_every_touched_document_validates_against_its_schema(tmp_path):
    from cuemsutils.xml.schema import get_schema

    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    state = state_dir(tmp_path)
    code, out = run_remint(cluster, state)
    assert code == 0, out

    for path in _table(state).applied:
        from pathlib import Path

        name = Path(path).name
        schema = {"settings.xml": "settings", "network_map.xml": "network_map",
                  "default_mappings.xml": "project_mappings",
                  "mappings.xml": "project_mappings"}.get(name, "script")
        get_schema(schema).validate(path)


def test_a_full_load_succeeds_on_this_node(tmp_path):
    """Through ``ConfigManager`` — the validating load path, and the **one**
    place in this operation it is used. It runs only after the rewrite, because
    before it these documents are by construction the ones the schema refuses
    (FR-006a)."""
    from cuemsutils.tools.ConfigManager import ConfigManager

    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)

    manager = ConfigManager(config_dir=str(cluster.conf), load_all=False)
    manager.load_config()
    assert str(manager.node_uuid) == _table(state).entries[cluster.nodes[0].uuid]


def test_the_verification_records_all_four_checks(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    run_remint(cluster, state)

    new = _table(state).entries[cluster.nodes[0].uuid]
    record = remint.CompletionRecord.load(remint.completion_record_path(state, new))
    assert record.verification == {
        "zero_old_tokens": True, "documents_valid": True,
        "load_succeeds": True, "adoption_unchanged": True, "failures": [],
    }


def test_a_verification_failure_is_its_own_exit_class(tmp_path):
    """Exit 2, not 1. "We changed your cluster and cannot prove it is right" is
    not the same news as "we changed nothing", and an operator's next action
    differs completely between the two."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)

    # A document the rewrite cannot make valid: the identity is substituted,
    # and the document is still structurally wrong afterwards.
    (cluster.conf / "default_mappings.xml").write_text(
        '<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">'
        f"<nodes><node><uuid>{cluster.nodes[0].uuid}</uuid></node></nodes>"
        "</cms:CuemsProjectMappings>",
        encoding="utf-8",
    )

    code, out = run_remint(cluster, state)

    assert code == 2, out
    assert "VERIFICATION FAILED" in out
