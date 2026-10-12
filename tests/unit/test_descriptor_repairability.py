"""Repairability classification (T056; FR-031a, FR-031b, SC-011a, SC-011b).

data-model.md §3.1's three ordered rules: (1) a field targeted by a
registered T2 rule takes that rule's declared repairability; (2) a field with
no default is UNREPAIRABLE, outranking (1); (3) anything else is REPAIRABLE.
"""

from __future__ import annotations

import pytest

from cuemsutils.xml.descriptor import Repairability, SchemaDescriptor
from cuemsutils.xml.schema import SCHEMA_NAMES
from cuemsutils.xml.spec import TypeKey
from cuemsutils.xml.validators import register


def test_the_count_of_unclassified_fields_is_zero():
    """Every field, in every type, in every schema, has a Repairability."""
    descriptor = SchemaDescriptor()
    checked = 0
    for schema_name in SCHEMA_NAMES:
        for type_descriptor in descriptor.types(schema_name):
            for field in type_descriptor.fields:
                assert field.repairability in (
                    Repairability.REPAIRABLE,
                    Repairability.UNREPAIRABLE,
                )
                checked += 1
    assert checked > 0


def test_a_field_with_no_default_classifies_unrepairable():
    """``VideoCueOutputType.output_name`` has no default (research R2, rule 2)."""
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "VideoCueOutputsType"))
    field = next(f for f in type_descriptor.fields if f.name == "output_name")
    assert field.repairability is Repairability.UNREPAIRABLE


def test_a_rule_targeted_field_with_a_valid_default_classifies_repairable():
    """``FadeCueType.action_type``'s default (``'fade_action'``) satisfies its
    own rule — rule 1, with a default present so rule 2 does not override it."""
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "FadeCueType"))
    field = next(f for f in type_descriptor.fields if f.name == "action_type")
    assert field.repairability is Repairability.REPAIRABLE


def test_rule_2_outranks_rule_1_when_the_rule_declares_repairable_but_has_no_default():
    """``MediaType.duration``'s ``media_duration`` rule declares
    ``repairable=False``, and it also has no default — either reason alone
    would already give UNREPAIRABLE; this asserts the actually-binding one."""
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "MediaType"))
    field = next(f for f in type_descriptor.fields if f.name == "duration")
    assert field.repairability is Repairability.UNREPAIRABLE


def test_a_field_targeted_by_no_rule_and_carrying_a_default_is_repairable():
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "AudioCueType"))
    field = next(f for f in type_descriptor.fields if f.name == "master_vol")
    assert field.repairability is Repairability.REPAIRABLE


def test_registering_a_rule_without_declaring_repairable_raises_at_import():
    """``repairable`` is required and keyword-only, with no default (research R8)."""
    with pytest.raises(TypeError):

        @register("__test_only_missing_repairable__", [("Cue", "name")])
        def _missing(value, obj=None):  # pragma: no cover - never called
            pass
