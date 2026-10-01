# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T009 — library reach (feature 012, FR-011, FR-012, research R3/R7).

The assertion the whole design turns on: a script is found by its **root
element**, so the filename is irrelevant. ``script_file_name`` is an
editor-internal dict key that appears in no document this library reads
(research R3), so a reach keyed on a filename would silently skip a library
configured the other way — which is exactly what FR-012 forbids.
"""

from __future__ import annotations

from cuemsutils.tools import library_reach
from tests.support.cluster_fixture import build_cluster, script_xml


def _names(reach):
    return sorted(p.name for p in reach.documents)


def test_a_script_named_script_xml_is_found(tmp_path):
    cluster = build_cluster(tmp_path, script_name="script.xml")
    reach = library_reach.reach_library(cluster.library)
    assert "script.xml" in _names(reach)


def test_a_script_named_cue_script_xml_is_found(tmp_path):
    """The editor's other spelling (``CuemsProjectManager.py:38``)."""
    cluster = build_cluster(tmp_path, script_name="cue_script.xml")
    reach = library_reach.reach_library(cluster.library)
    assert "cue_script.xml" in _names(reach)


def test_a_script_named_neither_is_found(tmp_path):
    """The case that proves it is not a two-constant heuristic: a name neither
    repository uses is still found, because the root element is what decides."""
    cluster = build_cluster(tmp_path, script_name="whatever-the-operator-called-it.xml")
    reach = library_reach.reach_library(cluster.library)
    assert "whatever-the-operator-called-it.xml" in _names(reach)


def test_a_project_with_no_mappings_is_still_a_project(tmp_path):
    """``mappings.xml`` is optional per project — the §10.7 item research could
    not settle from code, mitigated by treating it as optional (research R10)."""
    cluster = build_cluster(tmp_path, with_project_mappings=False)
    reach = library_reach.reach_library(cluster.library)
    assert [p.name for p in reach.projects]
    assert all(p.mappings == () for p in reach.projects)
    assert all(p.scripts for p in reach.projects)


def test_a_non_script_xml_in_a_project_directory_is_not_selected(tmp_path):
    """§10.7 leaves open whether any *other* file in a project directory embeds
    an output name. Root-element identification answers that per file rather
    than assuming it either way — an unrelated document is skipped, recorded,
    and not rewritten."""
    cluster = build_cluster(tmp_path)
    stray = cluster.project_dir("project_0") / "notes.xml"
    stray.write_text("<notes><entry>nothing to see</entry></notes>", encoding="utf-8")
    reach = library_reach.reach_library(cluster.library)
    assert stray not in reach.documents
    assert stray in reach.skipped


def test_trash_projects_are_included(tmp_path):
    """``trash/`` mirrors ``projects/`` because ``ConfigBase`` creates it that
    way (research R7) — confirmed in code, not on one machine."""
    cluster = build_cluster(tmp_path, projects=2, trashed_projects=1)
    reach = library_reach.reach_library(cluster.library)
    trashed = [p for p in reach.projects if p.trashed]
    assert len(trashed) == 1
    assert all(p.documents for p in trashed)


def test_backups_are_skipped_not_reached(tmp_path):
    """FR-015. A backup *is* a valid document, so only its name distinguishes
    one — and rewriting it would defeat the purpose of having taken it."""
    cluster = build_cluster(tmp_path)
    directory = cluster.project_dir("project_0")
    made = [
        directory / "script.xml.20260930T120000.bak",
        directory / "script.xml.bak-20260930",
        directory / "script.xml~",
    ]
    for path in made:
        path.write_text(script_xml("backup", cluster.nodes), encoding="utf-8")
    reach = library_reach.reach_library(cluster.library)
    for path in made:
        assert path not in reach.documents
        assert path in reach.skipped


def test_library_path_comes_from_settings(tmp_path):
    cluster = build_cluster(tmp_path)
    value, why_not = library_reach.library_path_from_settings(cluster.conf / "settings.xml")
    assert value == str(cluster.library) and why_not == ""


def test_an_absent_settings_degrades_with_a_reason(tmp_path):
    value, why_not = library_reach.library_path_from_settings(tmp_path / "nothing.xml")
    assert value is None and "absent" in why_not


def test_an_unreadable_settings_degrades_with_a_reason(tmp_path):
    path = tmp_path / "settings.xml"
    path.write_text("<Settings><unclosed>", encoding="utf-8")
    value, why_not = library_reach.library_path_from_settings(path)
    assert value is None and "unreadable" in why_not


def test_a_settings_with_no_library_path_degrades_with_a_reason(tmp_path):
    path = tmp_path / "settings.xml"
    path.write_text("<Settings><tmp_path>/tmp</tmp_path></Settings>", encoding="utf-8")
    value, why_not = library_reach.library_path_from_settings(path)
    assert value is None and "no library_path" in why_not


def test_resolve_prefers_the_override(tmp_path):
    cluster = build_cluster(tmp_path)
    other = tmp_path / "elsewhere"
    (other / "projects").mkdir(parents=True)
    reach = library_reach.resolve(cluster.conf, library_override=other)
    assert reach.library_path == other and reach.projects == ()


def test_resolve_degrades_when_settings_cannot_supply_a_path(tmp_path):
    reach = library_reach.resolve(tmp_path)
    assert reach.library_path is None and reach.degraded


def test_the_reach_reads_a_document_the_schema_would_refuse(tmp_path):
    """The property the check and the re-mint both need (FR-001a, FR-006a): a
    library full of uuid1 identities is exactly what this has to enumerate."""
    cluster = build_cluster(tmp_path, shapes=["uuid1", "uuid5"])
    reach = library_reach.reach_library(cluster.library)
    # two live projects and one trashed, each with a script and a mappings
    assert len(reach.documents) == 6
    assert reach.unreadable == ()
