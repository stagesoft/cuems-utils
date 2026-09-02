"""``ActionType`` narrowed to 12 values, ``fade_in``/``fade_out`` gone (T058; FR-029a, SC-012a).

The schema and the ``fade_action_type`` T2 rule used to disagree: ``ActionType``
offered ``fade_in``/``fade_out`` to every action cue including ``FadeCueType``,
while the rule forbade them there. Deleting the two values (not renaming —
migration-guide.md's FR-007b/c reasoning) removes the disagreement rather than
resolving it in favour of one side.
"""

from __future__ import annotations

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import get_schema
from cuemsutils.xml.spec import TypeKey


def test_action_type_enumerates_exactly_twelve_values():
    values = get_schema("script").types["ActionType"].enumeration
    assert len(values) == 12
    assert "fade_in" not in values
    assert "fade_out" not in values
    assert "fade_action" in values


def test_the_descriptor_publishes_exactly_those_twelve_values():
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "ActionCueType"))
    field = next(f for f in type_descriptor.fields if f.name == "action_type")
    assert field.enum_values is not None
    assert len(field.enum_values) == 12
    assert "fade_in" not in field.enum_values
    assert "fade_out" not in field.enum_values
    assert set(field.enum_values) == set(
        get_schema("script").types["ActionType"].enumeration
    )
