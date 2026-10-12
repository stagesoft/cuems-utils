# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""T007 — ``FieldSpec.alternatives`` comes from the schema (rules 2–3).

The attribute path is ``XsdAlternative.path``, the string E2 recorded.
A test that is not exactly ``@class='VALUE'`` is a derivation error.
"""

from __future__ import annotations

import pytest
from xmlschema import XMLSchema11

from cuemsutils.xml.spec import (
    TypeKey,
    class_alternatives,
    derive_named,
    fallback_alternative,
)

_CONDITIONAL = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType><xs:sequence>
      <xs:element name="d" maxOccurs="unbounded" type="Base">
        <xs:alternative test="@class='audio'" type="Audio"/>
        <xs:alternative test="@class='video'" type="Video"/>
        <xs:alternative type="Device"/>
      </xs:element>
    </xs:sequence></xs:complexType>
  </xs:element>
  <xs:complexType name="Base">
    <xs:attribute name="class" type="xs:string" use="required"/>
  </xs:complexType>
  <xs:complexType name="Device">
    <xs:complexContent><xs:extension base="Base">
      <xs:sequence><xs:element name="a" type="xs:string"/></xs:sequence>
    </xs:extension></xs:complexContent>
  </xs:complexType>
  <xs:complexType name="Audio">
    <xs:complexContent><xs:extension base="Base">
      <xs:sequence><xs:element name="a" type="xs:string"/></xs:sequence>
    </xs:extension></xs:complexContent>
  </xs:complexType>
  <xs:complexType name="Video">
    <xs:complexContent><xs:extension base="Base">
      <xs:sequence><xs:element name="extra" type="xs:string"/></xs:sequence>
    </xs:extension></xs:complexContent>
  </xs:complexType>
</xs:schema>"""

_NOT_A_CLASS_TEST = """<?xml version="1.0"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
  <xs:element name="root">
    <xs:complexType><xs:sequence>
      <xs:element name="d" type="B">
        <xs:alternative test="@kind='video'" type="B"/>
        <xs:alternative type="B"/>
      </xs:element>
    </xs:sequence></xs:complexType>
  </xs:element>
  <xs:complexType name="B">
    <xs:attribute name="class" type="xs:string"/>
  </xs:complexType>
</xs:schema>"""


def _particle(text: str):
    schema = XMLSchema11(text)
    return schema.elements["root"].type.content[0]


def test_a_conditional_element_yields_pairs_in_schema_order():
    pairs = class_alternatives(_particle(_CONDITIONAL), "probe")
    assert pairs == (
        ("audio", TypeKey("probe", "Audio")),
        ("video", TypeKey("probe", "Video")),
    )


def test_the_unconditional_alternative_is_the_fallback_not_a_pair():
    element = _particle(_CONDITIONAL)
    assert fallback_alternative(element, "probe") == TypeKey("probe", "Device")
    assert all(value != "Device" for value, _key in class_alternatives(element, "probe"))


def test_an_unconditional_element_yields_nothing():
    spec = derive_named("project_mappings", "NodeMappingType")
    for field in spec.fields:
        assert field.alternatives == ()


def test_a_test_that_is_not_exactly_class_equals_value_is_a_derivation_error():
    element = _particle(_NOT_A_CLASS_TEST)
    with pytest.raises(ValueError, match="derivation error"):
        class_alternatives(element, "probe")
