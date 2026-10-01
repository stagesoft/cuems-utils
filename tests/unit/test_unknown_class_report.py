# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T010 — an unrecognised class is one INFO line (FR-014).

Not a ``LoadReport`` field. The line is the whole report.
"""

from __future__ import annotations

import logging

from cuemsutils.errors import LoadReport
from cuemsutils.xml.mapper import Mapper
from cuemsutils.xml.spec import FieldKind, FieldSpec, TypeKey

_LINE = (
    "project_mappings mappings.xml: /node/devices/device[@class='vidoe'] "
    "has no conditional type; decoded as DeviceType. "
    "Check the spelling — an unknown class is valid, and this line is the only report."
)


def _member() -> FieldSpec:
    return FieldSpec(
        name="device",
        xsd_type="DeviceType",
        required=False,
        repeated=True,
        order=0,
        kind=FieldKind.ELEMENT,
        child=TypeKey("project_mappings", "DeviceType"),
        alternatives=(("video", TypeKey("project_mappings", "VideoDeviceType")),),
    )


def _decode(caplog, body, *, document="mappings.xml"):
    caplog.clear()
    mapper = Mapper("project_mappings", document=document)
    with caplog.at_level(logging.INFO):
        mapper._decode_member(body, _member(), path=("node", "devices"))
    return [r.getMessage() for r in caplog.records if r.levelno == logging.INFO]


def test_an_unknown_class_logs_the_info_line(caplog):
    assert _LINE in _decode(caplog, {"class": "vidoe"})


def test_a_matched_class_logs_nothing(caplog):
    assert _decode(caplog, {"class": "video"}) == []


def test_a_missing_class_logs_nothing(caplog):
    assert _decode(caplog, {}) == []


def test_a_decode_without_a_file_says_so(caplog):
    messages = _decode(caplog, {"class": "vidoe"}, document=None)
    assert any("(no file path)" in message and "vidoe" in message for message in messages)


def test_load_report_gains_no_field():
    assert "class" not in LoadReport.__dataclass_fields__
