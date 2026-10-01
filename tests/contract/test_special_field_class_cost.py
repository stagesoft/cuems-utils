# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T067 — a special field costs one alternative and one type, in one schema (FR-005)."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_SCHEMAS = _REPO / "src" / "cuemsutils" / "xml" / "schemas"
_NS = {"xs": "http://www.w3.org/2001/XMLSchema"}


def test_video_costs_one_alternative_and_one_type():
    tree = ET.parse(_SCHEMAS / "project_mappings.xsd")
    conditional = [
        alt for alt in tree.iterfind(".//xs:alternative", _NS)
        if alt.get("test")
    ]
    assert len(conditional) == 1
    assert conditional[0].get("test") == "@class='video'"
    assert conditional[0].get("type") == "cms:VideoDeviceType"
    declared = tree.findall(".//xs:complexType[@name='VideoDeviceType']", _NS)
    assert len(declared) == 1

    elsewhere = []
    for path in _SCHEMAS.glob("*.xsd"):
        if path.name == "project_mappings.xsd":
            continue
        text = path.read_text(encoding="utf-8")
        # settings.xsd's alternatives select player types (axis C). A second
        # VideoDeviceType would be a second selection of the video device.
        if "VideoDeviceType" in text:
            elsewhere.append(path.name)
    assert elsewhere == []


def test_no_python_table_selects_the_video_type():
    """The alternative is the selection. A dict or tuple that maps the class
    word ``video`` onto ``VideoDeviceType`` would be a second one."""
    root = _REPO / "src" / "cuemsutils"
    hits = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "VideoDeviceType" not in text:
            continue
        # The derivation comment names the constraint. The binding lives in
        # the registry and the model. Neither is a second selection table.
        if path.name in {"registry.py", "mappings.py", "spec.py"}:
            continue
        hits.append(path.relative_to(_REPO).as_posix())
    assert hits == []
