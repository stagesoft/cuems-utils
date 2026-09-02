"""Model-layer defaults, and ``Unset`` distinguishing "no default" from "defaults to None"
(T055, T057; FR-030, FR-031, SC-012, E19).
"""

from __future__ import annotations

from cuemsutils.helpers import Unset
from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.spec import TypeKey


def _field(descriptor, schema, type_name, field_name):
    type_descriptor = descriptor.describe(TypeKey(schema, type_name))
    return next(f for f in type_descriptor.fields if f.name == field_name)


def test_a_field_with_a_declared_default_carries_its_value():
    descriptor = SchemaDescriptor()
    field = _field(descriptor, "script", "AudioCueType", "master_vol")
    assert field.default == 100
    assert field.default is not Unset


def test_a_field_declared_unset_carries_the_unset_sentinel():
    descriptor = SchemaDescriptor()
    field = _field(descriptor, "script", "MediaType", "duration")
    assert field.default is Unset


def test_a_field_declared_none_is_distinguishable_from_unset():
    """``DmxUniverseType.dmx_channels`` defaults to ``None`` — a real value,
    not an absence — and the descriptor must not conflate the two (FR-031)."""
    descriptor = SchemaDescriptor()
    field = _field(descriptor, "script", "DmxUniverseType", "dmx_channels")
    assert field.default is None
    assert field.default is not Unset


def test_a_generic_bound_type_has_no_defaults():
    """``GENERIC``-bound types have no model class, so no defaults (research R5)."""
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "CTimecodeType"))
    assert type_descriptor.fields
    assert all(f.default is Unset for f in type_descriptor.fields)


# --- T057 / SC-012 / E19: the two frontend template values, from the descriptor alone ---


def test_the_example_audio_cues_master_vol_is_answerable_from_the_descriptor():
    field = _field(SchemaDescriptor(), "script", "AudioCueType", "master_vol")
    assert field.default == 100


def test_the_example_dmx_cues_dmx_channels_is_answerable_from_the_descriptor():
    field = _field(SchemaDescriptor(), "script", "DmxUniverseType", "dmx_channels")
    assert field.default is None
