# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T029b — same size, later modification time (FR-011b, SC-002a, research R11).

The property the whole library reach silently depends on, pinned because it
holds by accident of implementation and could be "fixed" away.

The substitution replaces 36 characters with 36, so **every rewritten file is
exactly the size it was**. The library reaches the nodes by ``rsync -rt`` with
no checksum, whose quick check is size plus modification time — so the time is
the *only* signal it has that the file changed. A rewrite that preserved
modification times, which is an easy and well-intentioned thing to add, would
leave every node's replica stale indefinitely with no error at any layer; the
failure would surface much later as an output resolving to nothing.

``os.replace`` already does the right thing. The trap is adding
``shutil.copystat``.
"""

from __future__ import annotations

import os

from tests.support.cluster_fixture import build_cluster
from tests.support.remint_harness import run_remint, state_dir


def _stats(paths):
    return {str(p): (os.stat(p).st_size, os.stat(p).st_mtime_ns) for p in paths}


def test_every_rewritten_library_file_keeps_its_size_and_gains_a_later_time(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    state = state_dir(tmp_path)
    library_files = [p for p in cluster.library.rglob("*.xml")]
    before = _stats(library_files)

    code, out = run_remint(cluster, state)
    assert code == 0, out

    after = _stats(library_files)
    assert set(after) == set(before)
    for path, (size, mtime) in after.items():
        old_size, old_mtime = before[path]
        assert size == old_size, f"{path} changed size; the substitution is not length-preserving"
        assert mtime > old_mtime, (
            f"{path} kept its modification time. Under rsync -rt with no checksum that "
            "leaves every node's replica stale forever, with no error anywhere."
        )


def test_the_configuration_documents_keep_their_size_too(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    state = state_dir(tmp_path)
    documents = [cluster.conf / n for n in
                 ("settings.xml", "network_map.xml", "default_mappings.xml")]
    before = _stats(documents)

    run_remint(cluster, state)

    for path, (size, _mtime) in _stats(documents).items():
        assert size == before[path][0]


def test_a_file_that_was_not_rewritten_keeps_its_time(tmp_path):
    """The other direction: a fresh time on an untouched file would re-sync it
    to every node for nothing."""
    cluster = build_cluster(tmp_path, identities=[
        "6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40",   # converged
        "0367f391-ebf4-11b2-9f26-000000000001",   # uuid1
    ])
    state = state_dir(tmp_path)
    lone = cluster.project_dir("project_0") / "converged-only.xml"
    lone.write_text(
        '<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">'
        "<nodes><node><uuid>6f1d2c3b-4a5e-4f60-8a71-9b8c7d6e5f40</uuid>"
        "<mac>aabbccdd0000</mac></node></nodes></cms:CuemsProjectMappings>",
        encoding="utf-8",
    )
    before = _stats([lone])

    run_remint(cluster, state)

    assert _stats([lone]) == before
