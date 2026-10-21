# SPDX-FileCopyrightText: 2026 Stagelab Coop SCCL
# SPDX-License-Identifier: GPL-3.0-or-later
"""A field's published repairability does not depend on rule registration order (017 FR-023a).

The descriptor classifies every field as REPAIRABLE or UNREPAIRABLE from the T2 rules that
target it, and the frontend reads that classification (015 G3). It used to keep **the last
registered rule's** flag for each field. That was harmless while every field had rules that
agreed (measured 2026-10-21: only ``ActionCue.action_target`` had two, both unrepairable).

A-1 adds a repairable rule, ``project_action_takes_no_target``, on ``ActionCue.action_target``.
With last-wins, the field would have been published as repairable: false for every action type
except ``stop_project``. The map is now conservative: a field is repairable only if **every**
rule targeting it is.
"""
from cuemsutils.xml import descriptor as descriptor_module
from cuemsutils.xml import validators
from cuemsutils.xml.descriptor import Repairability, SchemaDescriptor
from cuemsutils.xml.spec import TypeKey


def test_action_target_is_published_unrepairable():
    type_descriptor = SchemaDescriptor().describe(TypeKey("script", "ActionCueType"))
    field = next(f for f in type_descriptor.fields if f.name == "action_target")
    assert field.repairability is Repairability.UNREPAIRABLE


def test_the_map_is_the_same_whatever_order_the_rules_are_registered_in(monkeypatch):
    monkeypatch.setattr(descriptor_module, "_repairability_cache", None)
    forward = dict(descriptor_module._repairability_map())

    monkeypatch.setattr(descriptor_module, "_repairability_cache", None)
    monkeypatch.setattr(validators, "RULES", dict(reversed(list(validators.RULES.items()))))
    backward = dict(descriptor_module._repairability_map())

    assert forward == backward
    # monkeypatch restores RULES and the cache, so later tests see the real map.
