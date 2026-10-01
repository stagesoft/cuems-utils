# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T021 — an old-shape mappings document names the migration (FR-027, SC-005)."""

from __future__ import annotations

from pathlib import Path

import pytest

from cuemsutils.errors import SchemaError
from cuemsutils.xml.settings import ProjectMappings

_DOCUMENT = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "pre-013" / "project_mappings.xml"
)


def test_an_old_shape_document_names_the_tool_and_the_path():
    with pytest.raises(SchemaError) as excinfo:
        ProjectMappings(str(_DOCUMENT))
    message = str(excinfo.value)
    assert message == (
        f"project_mappings document {_DOCUMENT} is in the pre-013 device shape "
        "(<audio>/<video>/<dmx> on <node>). Run `cuems-reshape-devices` to migrate it."
    )
