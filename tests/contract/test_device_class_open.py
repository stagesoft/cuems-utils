# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T017 — a class the library has never named validates and decodes (FR-004)."""

from __future__ import annotations

from pathlib import Path

from cuemsutils.xml.settings import ProjectMappings

_REPO = Path(__file__).resolve().parents[2]
_UUID = "0367f391-ebf4-48b2-9f26-000000000001"

_DOCUMENT = f"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">
  <number_of_nodes>1</number_of_nodes>
  <defaults>
    <default class="audio" direction="output">out</default>
  </defaults>
  <nodes><node>
    <uuid>{_UUID}</uuid>
    <mac>2cf05d21cca3</mac>
    <devices>
      <device class="audio">
        <outputs><output><id>0</id><name>a</name>
          <mappings><mapped_to>a</mapped_to></mappings>
        </output></outputs>
      </device>
      <device class="lighting">
        <outputs><output><id>0</id><name>lamp</name>
          <mappings><mapped_to>lamp</mapped_to></mappings>
        </output></outputs>
      </device>
    </devices>
  </node></nodes>
  <new_nodes></new_nodes>
</cms:CuemsProjectMappings>
"""


def test_a_lighting_device_validates_and_decodes(tmp_path):
    path = tmp_path / "mappings.xml"
    path.write_text(_DOCUMENT, encoding="utf-8")
    loaded = ProjectMappings(str(path))
    devices = loaded.processed["nodes"][0]["node"]["devices"]
    by_class = {item["device"]["class"]: item["device"] for item in devices}
    assert set(by_class) == {"audio", "lighting"}
    assert type(by_class["lighting"]).__name__ == "DeviceType"


def test_the_library_source_does_not_name_lighting():
    """A class the library has never named. Prose that says "lighting control"
    is not a name; a string or identifier whose value is exactly ``lighting`` is."""
    import ast

    hits = []
    for path in (_REPO / "src" / "cuemsutils").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and node.value == "lighting":
                hits.append(path.relative_to(_REPO).as_posix())
                break
            if isinstance(node, ast.Name) and node.id == "lighting":
                hits.append(path.relative_to(_REPO).as_posix())
                break
    for path in (_REPO / "src" / "cuemsutils").rglob("*.xsd"):
        if 'class="lighting"' in path.read_text(encoding="utf-8") or ">lighting<" in path.read_text(encoding="utf-8"):
            hits.append(path.relative_to(_REPO).as_posix())
    assert hits == []
