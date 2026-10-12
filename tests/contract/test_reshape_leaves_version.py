# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T032 — a rewrite does not move ``doc_version`` (FR-020)."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from cuemsutils.xml.reshape_devices import main

_OLD = (
    Path(__file__).resolve().parents[1]
    / "data" / "corpus" / "pre-013" / "project_mappings.xml"
)


def test_the_marker_the_document_arrived_with_is_the_marker_it_leaves_with(tmp_path):
    target = tmp_path / "mappings.xml"
    shutil.copyfile(_OLD, target)
    tree = ET.parse(target)
    tree.getroot().set("doc_version", "7")
    tree.write(target, encoding="utf-8", xml_declaration=True)
    assert main([str(target)]) == 0
    assert ET.parse(target).getroot().get("doc_version") == "7"
