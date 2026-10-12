# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T008 — ``_alternative_for`` selects the model, and the fallback is ``member.child``.

Both decode paths are here. The show path funnels through ``_decode_member``.
Configuration documents do not: ``_decode_config_item`` is their equivalent,
and a mappings device never reaches ``_decode_member``.
"""

from __future__ import annotations

from cuemsutils.config.mappings import DeviceType, VideoDeviceType
from cuemsutils.xml.mapper import Mapper
from cuemsutils.xml.spec import (
    FieldKind,
    FieldSpec,
    ModelGroup,
    TypeKey,
    TypeSpec,
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
        alternatives=(
            ("video", TypeKey("project_mappings", "VideoDeviceType")),
        ),
    )


def _devices() -> TypeSpec:
    return TypeSpec(
        key=TypeKey("project_mappings", "DevicesType"),
        fields=(_member(),),
        model_group=ModelGroup.SEQUENCE,
        wildcard=False,
        mixed=False,
    )


def test_a_matching_class_decodes_to_that_model():
    result = Mapper("project_mappings")._decode_member({"class": "video"}, _member())
    assert isinstance(result, VideoDeviceType)


def test_an_unknown_class_decodes_through_member_child():
    result = Mapper("project_mappings")._decode_member({"class": "lighting"}, _member())
    assert isinstance(result, DeviceType)
    assert not isinstance(result, VideoDeviceType)


def test_a_missing_class_decodes_through_member_child():
    result = Mapper("project_mappings")._decode_member({}, _member())
    assert isinstance(result, DeviceType)


def test_the_config_path_uses_the_same_dispatch():
    decoded = Mapper("project_mappings")._decode_config_item(
        {"device": {"class": "video"}}, _devices()
    )
    assert isinstance(decoded["device"], VideoDeviceType)
