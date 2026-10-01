# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T019 — two devices of one class are rejected by the schema alone (FR-013).

The library load path is not imported. The rejection is ``XMLSchema11.is_valid``.
"""

from __future__ import annotations

from pathlib import Path

from xmlschema import XMLSchema11

_XSD = Path(__file__).resolve().parents[2] / "src" / "cuemsutils" / "xml" / "schemas" / "project_mappings.xsd"
_UUID = "0367f391-ebf4-48b2-9f26-000000000001"


def _document(devices: str, defaults: str) -> str:
    return f"""<?xml version='1.0' encoding='utf-8'?>
<cms:CuemsProjectMappings xmlns:cms="https://stagelab.coop/cuems/">
  <number_of_nodes>1</number_of_nodes>
  <defaults>
    {defaults}
  </defaults>
  <nodes><node>
    <uuid>{_UUID}</uuid>
    <mac>2cf05d21cca3</mac>
    <devices>
      {devices}
    </devices>
  </node></nodes>
  <new_nodes></new_nodes>
</cms:CuemsProjectMappings>
"""


_OK_DEFAULTS = (
    '<default class="audio" direction="input"></default>'
    '<default class="audio" direction="output">a</default>'
)
_DUP_DEFAULTS = (
    '<default class="audio" direction="output">a</default>'
    '<default class="audio" direction="output">b</default>'
)


_ONE = """<device class="audio"><outputs><output><id>0</id><name>a</name>
  <mappings><mapped_to>a</mapped_to></mappings></output></outputs></device>"""
_TWO = _ONE + """<device class="audio"><outputs><output><id>1</id><name>b</name>
  <mappings><mapped_to>b</mapped_to></mappings></output></outputs></device>"""


def test_one_device_per_class_validates_and_a_duplicate_does_not():
    schema = XMLSchema11(str(_XSD))
    assert schema.is_valid(_document(_ONE, _OK_DEFAULTS))
    assert not schema.is_valid(_document(_TWO, _OK_DEFAULTS))


def test_a_duplicate_default_pair_does_not_validate():
    schema = XMLSchema11(str(_XSD))
    assert not schema.is_valid(_document(_ONE, _DUP_DEFAULTS))
