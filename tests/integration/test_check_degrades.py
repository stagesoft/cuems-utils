# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T013 — partial failure is reported, not fatal (FR-005, research R9).

Three ways the library can be out of reach — ``settings.xml`` absent,
unreadable, or present with no ``library_path`` — and in each the check
degrades to a configuration-only survey **that says so**. A survey that
silently covered less would be worse than one that failed: an operator would
read "no non-converged identities" and believe it.
"""

from __future__ import annotations

import json

from cuemsutils.tools import identity_check
from tests.support.cluster_fixture import build_cluster


def _check(cluster, tmp_path, library=None):
    return identity_check.check(
        cluster.conf, avahi_service=cluster.avahi, library=library
    )


def test_an_absent_settings_degrades_and_says_so(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "settings.xml").unlink()
    report = _check(cluster, tmp_path)
    assert report.library == ""
    assert any("absent" in note for note in report.notes)
    assert report.exit_code == 2


def test_an_unreadable_settings_degrades_and_says_so(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "settings.xml").write_text("<Settings><unclosed>", encoding="utf-8")
    report = _check(cluster, tmp_path)
    assert any("unreadable" in note for note in report.notes)
    assert report.exit_code == 2


def test_a_settings_with_no_library_path_degrades_and_says_so(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    text = (cluster.conf / "settings.xml").read_text()
    start = text.index("<library_path>")
    end = text.index("</library_path>") + len("</library_path>")
    (cluster.conf / "settings.xml").write_text(text[:start] + text[end:], encoding="utf-8")
    report = _check(cluster, tmp_path)
    assert any("library_path" in note for note in report.notes)
    # the configuration survey still happened
    assert report.occurrences


def test_the_degradation_appears_in_both_renderings(tmp_path):
    """An operator reads one and a tool reads the other; a survey that covered
    less must say so in whichever one is being read."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    (cluster.conf / "settings.xml").unlink()
    report = _check(cluster, tmp_path)
    assert "configuration directory only" in identity_check.render(report)
    assert json.loads(identity_check.render_json(report))["notes"]


def test_an_unrecognised_document_is_named_and_the_survey_continues(tmp_path):
    """A malformed script in one project must not cost the survey the other
    projects — the check is most needed on a tree that is already wrong."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"], projects=3)
    broken = cluster.project_dir("project_1") / "script.xml"
    broken.write_text("<cms:CuemsProject><unclosed>", encoding="utf-8")

    report = _check(cluster, tmp_path, library=cluster.library)

    assert any(str(broken) in note for note in report.notes)
    surveyed = {o.path for o in report.occurrences}
    assert any("project_0" in p for p in surveyed)
    assert any("project_2" in p for p in surveyed)


def test_a_library_path_pointing_nowhere_degrades(tmp_path):
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    report = _check(cluster, tmp_path, library=tmp_path / "does-not-exist")
    assert any("not a directory" in note for note in report.notes)
    assert report.occurrences, "the configuration survey still ran"
