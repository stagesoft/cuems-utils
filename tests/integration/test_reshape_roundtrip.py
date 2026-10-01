# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T030 — a reshaped mappings document decodes equal to the new-shape corpus."""

from __future__ import annotations

import shutil
from pathlib import Path

from cuemsutils.xml.reshape_devices import main
from cuemsutils.xml.settings import ProjectMappings
from tests.support.roundtrip import as_plain

_OLD = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "project_mappings.xml"
_NEW = Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils" / "project_mappings.xml"


def _domain(path: Path) -> dict:
    loaded = as_plain(ProjectMappings(str(path)).processed)
    loaded.pop("schemaLocation", None)
    return loaded


_OLD_SETTINGS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "pre-013" / "settings.xml"
_NEW_SETTINGS = Path(__file__).resolve().parents[1] / "data" / "corpus" / "cuems-utils" / "settings.xml"


def test_reshaped_settings_match_the_new_shape_document(tmp_path):
    from cuemsutils.xml.settings import Settings

    target = tmp_path / "settings.xml"
    shutil.copyfile(_OLD_SETTINGS, target)
    assert main([str(target)]) == 0

    def domain(path: Path) -> dict:
        loaded = as_plain(Settings(str(path)).processed)
        loaded.pop("schemaLocation", None)
        return loaded

    assert domain(target) == domain(_NEW_SETTINGS)


def test_reshaped_values_match_the_new_shape_document(tmp_path):
    target = tmp_path / "project_mappings.xml"
    shutil.copyfile(_OLD, target)
    assert main([str(target)]) == 0
    assert _domain(target) == _domain(_NEW)
