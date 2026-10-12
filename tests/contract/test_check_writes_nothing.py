# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T010 — the check writes nothing, ever (feature 012, FR-003, SC-005).

The guarantee that makes this the one part of the feature safe to put on a
field machine before the re-mint's reach has been confirmed on hardware. It is
asserted over **content hashes and modification times together**: a rewrite
that restored times would pass a hash-only check on a file it had truncated and
rewritten identically, and a time-only check would miss a same-second rewrite.

The directory is compared as a *set* too, so a file created or deleted fails
here rather than passing because every surviving file happened to match.
"""

from __future__ import annotations

import hashlib
import os

import pytest

from cuemsutils.tools import identity_check
from tests.support.cluster_fixture import build_cluster


def _state(root):
    """Every path under ``root``, with its hash and modification time."""
    out = {}
    for base, _dirs, files in os.walk(root):
        for name in files:
            path = os.path.join(base, name)
            stat = os.stat(path)
            with open(path, "rb") as handle:
                digest = hashlib.sha256(handle.read()).hexdigest()
            out[path] = (digest, stat.st_mtime_ns, stat.st_size)
    return out


@pytest.mark.parametrize("shapes", [
    ["uuid4", "uuid4b"],          # already converged
    ["uuid1", "uuid5"],           # migration needed
    ["sentinel", "uuid4"],        # never provisioned
])
def test_the_check_creates_modifies_moves_and_deletes_nothing(tmp_path, shapes):
    cluster = build_cluster(tmp_path, shapes=shapes)
    before = _state(cluster.root)

    identity_check.check(cluster.conf, avahi_service=cluster.avahi)

    after = _state(cluster.root)
    assert set(after) == set(before), "the check created or removed a file"
    assert after == before, "the check changed a file's content or modification time"


def test_no_backup_appears(tmp_path):
    """FR-003's second half. A "harmless" backup is still a write, and on a
    node whose documents the schema refuses it is a write nobody asked for."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    before = {p for p in cluster.root.rglob("*") if p.is_file()}

    identity_check.check(cluster.conf, avahi_service=cluster.avahi)

    after = {p for p in cluster.root.rglob("*") if p.is_file()}
    assert after == before
    assert not [p for p in after if ".bak" in p.name or p.name.endswith("~")]


def test_the_library_survey_writes_nothing_either(tmp_path):
    """The library is where the check gained reach this feature, so it is where
    a write would newly be possible (FR-011, FR-003)."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    before = _state(cluster.library)

    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )

    assert report.occurrences, "the survey reached nothing, so it proves nothing"
    assert _state(cluster.library) == before
