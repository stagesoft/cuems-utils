# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T014 — the check runs on documents the tightened schema refuses (FR-001a).

FR-001a is satisfied **by design** — stdlib XML only, never the validating load
path — rather than by a dedicated test. This is the test that observes the
design holding, which is a different job: it does not make the property true, it
notices when the property stops being true.

Two ways it could stop. A future edit could route the check through
``ConfigManager`` for convenience, which would work on every developer's
already-converged machine and fail on exactly the node an operator runs it on.
Or the version probe could start refusing a document whose marker predates the
library. Both are covered below.
"""

from __future__ import annotations

import sys

from cuemsutils.tools import identity_check, ids
from tests.support.cluster_fixture import (
    SHAPES,
    build_cluster,
    network_map_xml,
    project_mappings_xml,
)


def test_a_uuid1_cluster_surveys_cleanly(tmp_path):
    """Every identity in this tree is one the narrowed ``NodeUuidType``
    refuses. It is also the only tree the migration exists for."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )
    assert report.exit_code == 1
    assert report.counts.get(ids.NOT_CONVERGED, 0) > 0


def test_a_map_with_two_rows_sharing_an_identity_still_surveys(tmp_path):
    """FR-019a makes this map raise ``ValidationError`` for every reader once
    the rule lands. The check must still read it: a collision is a thing an
    operator needs *told about*, and a diagnostic that refuses the broken case
    is no diagnostic."""
    cluster = build_cluster(tmp_path, identities=[SHAPES["uuid1"], SHAPES["uuid1"]])
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )
    assert report.occurrences
    assert report.exit_code in (1, 2)


def test_a_document_marked_newer_than_this_library_still_surveys(tmp_path):
    """The version probe raises for the load path, by design (FR-052). The
    check does not go through it, so a document from a future library is still
    classifiable — and telling an operator "your map is from a newer release"
    is more use than a traceback."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "network_map.xml").write_text(
        network_map_xml(cluster.nodes, version=99), encoding="utf-8"
    )
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )
    assert any(str(cluster.conf / "network_map.xml") == o.path for o in report.occurrences)


def test_a_structurally_invalid_but_well_formed_document_still_surveys(tmp_path):
    """Missing required elements, wrong order, an element the schema does not
    declare — none of it stops a scan that never consults a schema."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "default_mappings.xml").write_text(
        '<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">'
        f"<invented/><nodes><node><uuid>{SHAPES['uuid1']}</uuid></node></nodes>"
        "</cms:CuemsProjectMappings>",
        encoding="utf-8",
    )
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )
    assert any("default_mappings.xml" in o.path for o in report.occurrences)


def test_the_check_never_imports_the_validating_load_path(tmp_path):
    """The design property itself, observed rather than argued.

    ``cuemsutils.xml.settings`` and ``cuemsutils.tools.ConfigManager`` are the
    validating readers. A check that needed either would have imported it by
    the time the report came back.
    """
    for module in ("cuemsutils.xml.settings", "cuemsutils.tools.ConfigManager"):
        sys.modules.pop(module, None)

    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )

    assert "cuemsutils.xml.settings" not in sys.modules
    assert "cuemsutils.tools.ConfigManager" not in sys.modules


def test_a_project_mappings_the_narrowed_schema_refuses_is_surveyed(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    path = cluster.mappings_path("project_0")
    path.write_text(project_mappings_xml(cluster.nodes, version=2), encoding="utf-8")
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )
    assert any(str(path) == o.path for o in report.occurrences)
