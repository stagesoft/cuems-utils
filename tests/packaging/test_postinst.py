# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""``debian/cuems-utils.postinst`` at script level (feature 011): every branch
of FR-015–FR-019, run against temp directories through the path overrides and
under a simulated ``set -e`` autoscript stanza (research R21)."""

from __future__ import annotations

from pathlib import Path

from tests.packaging.conftest import REPO_ROOT

SCHEMAS = ("settings", "network_map", "project_mappings", "project_settings", "script", "hardware_outputs")
DOCUMENTS = ("settings.xml", "network_map.xml", "default_mappings.xml")


def _seed_pristine(share: Path) -> None:
    for name in DOCUMENTS:
        (share / "defaults" / name).write_bytes(f"<pristine {name}/>".encode())


# -- US1 (T016) -----------------------------------------------------------------


def test_schemas_are_installed_always(dirs, run_maintainer_script):
    dirs.etc.mkdir()
    (dirs.etc / "network_map.xsd").write_bytes(b"<stale/>")
    _seed_pristine(dirs.share)

    result = run_maintainer_script("postinst", "configure", dirs.env())

    assert result.returncode == 0, result.stderr
    for name in SCHEMAS:
        installed = dirs.etc / f"{name}.xsd"
        assert installed.read_bytes() == (REPO_ROOT / "src/cuemsutils/xml/schemas" / f"{name}.xsd").read_bytes()
        assert installed.stat().st_mode & 0o777 == 0o644


def test_postinst_exits_zero_even_when_share_is_missing(dirs, run_maintainer_script):
    """FR-015 in its bluntest form: nothing to install must not fail the stack."""
    env = dirs.env()
    env["CUEMS_SHARE"] = str(dirs.share / "does-not-exist")
    result = run_maintainer_script("postinst", "configure", env)
    assert result.returncode == 0, result.stderr
    assert "WARNING" in result.stderr


# -- US2 (T028) -----------------------------------------------------------------


def test_documents_installed_only_when_absent(dirs, run_maintainer_script):
    """Per file, only where absent; a present file is never touched; the overlay
    is never read. CUEMS_INIT_NODE is EMPTY here so the tool step is skipped —
    this test must not depend on US3's block."""
    dirs.etc.mkdir()
    _seed_pristine(dirs.share)
    present = {
        "settings.xml": b"<real identity/>",
        "network_map.xml": b"<node_list/>",  # a cuems-common stub is "present"
    }
    for name, content in present.items():
        (dirs.etc / name).write_bytes(content)
    (dirs.etc / "defaults.d").mkdir()
    (dirs.etc / "defaults.d" / "00-broken.toml").write_text("this is = = not toml")

    result = run_maintainer_script("postinst", "configure", dirs.env())

    assert result.returncode == 0, result.stderr
    for name, content in present.items():
        assert (dirs.etc / name).read_bytes() == content, f"{name} was modified"
    assert (dirs.etc / "default_mappings.xml").read_bytes() == b"<pristine default_mappings.xml/>"
    assert (dirs.etc / "default_mappings.xml").stat().st_mode & 0o777 == 0o644
    assert "NOT PROVISIONED" in result.stderr


def test_a_sentinel_document_is_left_alone(dirs, run_maintainer_script):
    dirs.etc.mkdir()
    _seed_pristine(dirs.share)
    sentinel = b"<settings><uuid>00000000-0000-0000-0000-000000000000</uuid></settings>"
    (dirs.etc / "settings.xml").write_bytes(sentinel)
    result = run_maintainer_script("postinst", "configure", dirs.env())
    assert result.returncode == 0
    assert (dirs.etc / "settings.xml").read_bytes() == sentinel
