# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T011 — every occurrence classified, with where it was (FR-001, FR-002, SC-005).

SC-005's classification half: point the check at a tree containing a uuid1, a
uuid5, a uuid4 and the sentinel, and **every** occurrence comes back with its
document, its location within it, its value and its class — including the ones
embedded in compound strings, which are the occurrences a structural tool
cannot see and which are therefore the ones worth proving are seen.
"""

from __future__ import annotations

import json

from cuemsutils.tools import identity_check, ids
from tests.support.cluster_fixture import SHAPES, build_cluster


def _report(tmp_path, **kwargs):
    cluster = build_cluster(tmp_path, **kwargs)
    return cluster, identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )


def test_every_occurrence_carries_path_location_value_and_class(tmp_path):
    _cluster, report = _report(tmp_path, shapes=["uuid1", "uuid4"])
    assert report.occurrences
    for occurrence in report.occurrences:
        assert occurrence.path
        assert occurrence.location
        assert occurrence.value
        assert occurrence.classification in ids.CLASSES
        assert isinstance(occurrence.embedded, bool)


def test_a_mixed_tree_reports_each_class_it_contains(tmp_path):
    """One node per shape, so the report has to tell four things apart at once."""
    cluster = build_cluster(
        tmp_path,
        identities=[SHAPES["uuid1"], SHAPES["uuid5"], SHAPES["uuid4"], SHAPES["sentinel"]],
    )
    report = identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=cluster.library
    )
    by_value = {o.value: o.classification for o in report.occurrences}
    assert by_value[SHAPES["uuid1"]] == ids.NOT_CONVERGED
    assert by_value[SHAPES["uuid5"]] == ids.NOT_CONVERGED
    assert by_value[SHAPES["uuid4"]] == ids.CONVERGED
    assert by_value[SHAPES["sentinel"]] == ids.NOT_PROVISIONED_CLASS


def test_occurrences_embedded_in_compound_strings_are_reported_as_embedded(tmp_path):
    """The distinction that makes a structural rewrite wrong (design §10.2).
    An operator reading the report should be able to see how much of the work
    is invisible to a naive tool."""
    cluster, report = _report(tmp_path, shapes=["uuid1", "uuid5"])
    embedded = [o for o in report.occurrences if o.embedded]
    assert embedded, "the fixture's compound output names were not reported"
    assert {o.location for o in embedded} == {"output_name"}
    assert all(o.context.endswith(("_0", "_custom_1")) for o in embedded)


def test_bare_element_occurrences_are_reported_as_not_embedded(tmp_path):
    cluster, report = _report(tmp_path, shapes=["uuid1", "uuid5"])
    bare = [o for o in report.occurrences if not o.embedded]
    assert {o.location for o in bare} >= {"uuid"}


def test_occurrences_name_both_the_configuration_and_the_library(tmp_path):
    cluster, report = _report(tmp_path, shapes=["uuid1", "uuid5"])
    paths = {o.path for o in report.occurrences}
    assert any(str(cluster.conf) in p for p in paths)
    assert any(str(cluster.library) in p for p in paths)
    assert any("trash" in p for p in paths), "trashed projects are in reach (research R7)"


def test_nothing_scanned_is_left_unaccounted_for(tmp_path):
    """SC-005's "100%" made checkable: the per-class counts cover every token
    the survey saw, whether or not the occurrence list carries it."""
    _cluster, report = _report(tmp_path, shapes=["uuid1", "uuid5"])
    assert sum(report.counts.values()) == report.scanned
    assert set(report.counts) <= set(ids.CLASSES)
    assert report.scanned >= len(report.occurrences)


def test_the_json_output_carries_the_extended_occurrence_shape(tmp_path):
    """T018's shape, asserted where an operator or a tool actually reads it."""
    _cluster, report = _report(tmp_path, shapes=["uuid1", "uuid5"])
    payload = json.loads(identity_check.render_json(report))
    assert payload["occurrences"]
    first = payload["occurrences"][0]
    assert set(first) >= {"path", "location", "value", "classification", "embedded"}
    assert payload["counts"] and payload["scanned"]


def test_the_human_rendering_names_the_classes_and_the_embedded_count(tmp_path):
    _cluster, report = _report(tmp_path, shapes=["uuid1", "uuid5"])
    text = identity_check.render(report)
    assert ids.NOT_CONVERGED in text
    assert "embedded" in text
