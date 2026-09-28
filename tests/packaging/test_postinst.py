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
