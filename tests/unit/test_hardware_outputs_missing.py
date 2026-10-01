# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T026 — a missing class is empty, a present one is filled, a typo is an error."""

from __future__ import annotations

from cuemsutils.tools.ConfigManager import (
    HardwareOutputs,
    _each_device,
    _hw_name,
    _port_groups,
    _unwrap_put,
)
from cuemsutils.xml.settings import ProjectMappings

_UUID = "0367f391-ebf4-48b2-9f26-000000000001"
_DOCUMENT = f"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">
  <number_of_nodes>1</number_of_nodes>
  <defaults></defaults>
  <nodes><node>
    <uuid>{_UUID}</uuid>
    <mac>2cf05d21cca3</mac>
    <devices>
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


def _fill(node) -> HardwareOutputs:
    found = HardwareOutputs()
    for device in _each_device(node):
        section = device["class"]
        for direction in ("inputs", "outputs"):
            bucket = found.setdefault(f"{section}_{direction}", [])
            for ports in _port_groups(device.get(direction)):
                for port in ports:
                    bucket.append(_hw_name(_unwrap_put(port)))
    return found


def test_a_missing_well_formed_key_is_empty_and_get_does_not_invent_it():
    found = HardwareOutputs()
    assert found["fog_outputs"] == []
    assert found.get("fog_outputs") is None


def test_a_typo_stays_a_key_error():
    found = HardwareOutputs()
    try:
        found["audio_output"]
    except KeyError:
        return
    raise AssertionError("a typo answered")


def test_a_lighting_device_is_filled(tmp_path):
    path = tmp_path / "mappings.xml"
    path.write_text(_DOCUMENT, encoding="utf-8")
    node = ProjectMappings(str(path)).processed["nodes"][0]["node"]
    found = _fill(node)
    assert found["lighting_outputs"] == ["lamp"]
    assert found["lighting_inputs"] == []
    assert found.get("fog_outputs") is None
