# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T018 — ``canvas_region`` belongs to ``video`` and to no other class (FR-003)."""

from __future__ import annotations

from cuemsutils.xml.schema import get_schema

_UUID = "0367f391-ebf4-48b2-9f26-000000000001"
_REGION = "<canvas_region><x>0</x><y>0</y><width>0.5</width><height>0.5</height></canvas_region>"


def _document(device_class: str, region: str) -> str:
    return f"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">
  <number_of_nodes>1</number_of_nodes>
  <defaults></defaults>
  <nodes><node>
    <uuid>{_UUID}</uuid>
    <mac>2cf05d21cca3</mac>
    <devices>
      <device class="{device_class}">
        <outputs><output><id>0</id><name>n</name>
          {region}
          <mappings><mapped_to>n</mapped_to></mappings>
        </output></outputs>
      </device>
    </devices>
  </node></nodes>
  <new_nodes></new_nodes>
</cms:CuemsProjectMappings>
"""


def test_canvas_region_on_video_is_accepted():
    schema = get_schema("project_mappings")
    assert schema.is_valid(_document("video", _REGION))


def test_canvas_region_on_another_class_is_rejected():
    schema = get_schema("project_mappings")
    assert not schema.is_valid(_document("lighting", _REGION))
    assert schema.is_valid(_document("lighting", ""))
