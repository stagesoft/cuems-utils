"""``ActionType`` has exactly eleven values (T058; FR-029a, SC-012a; feature 017 FR-024).

The schema and the ``fade_action_type`` T2 rule used to disagree: ``ActionType``
offered ``fade_in``/``fade_out`` to every action cue including ``FadeCueType``,
while the rule forbade them there. Deleting the two values (not renaming —
migration-guide.md's FR-007b/c reasoning) removes the disagreement rather than
resolving it in favour of one side. That gave twelve values.

Feature 017 moves the count twice, and both moves are asserted **by name**, not
only by count:

- **+ ``stop_project``**, the release line's rc17 project-scope action (the
  authored end of an unattended show; it takes no target, A-1);
- **− ``pause_project``, − ``resume_project``**, retired (Q13): project
  pause/resume is deferred, and ``specs/planning/project-pause-resume-deferred.md``
  is the handover.

The purpose is unchanged: no retired value may come back unnoticed.
"""

from __future__ import annotations

from cuemsutils.xml.descriptor import SchemaDescriptor
from cuemsutils.xml.schema import get_schema
from cuemsutils.xml.spec import TypeKey


ELEVEN = {
    "play", "pause", "stop", "load", "unload", "enable", "disable",
    "fade_action", "wait", "go_to", "stop_project",
}

#: Values that were deliberately removed and must not return unnoticed.
RETIRED = {"fade_in", "fade_out", "pause_project", "resume_project"}


def test_action_type_enumerates_exactly_eleven_values():
    values = get_schema("script").types["ActionType"].enumeration
    assert set(values) == ELEVEN
    assert len(values) == 11
    assert not RETIRED & set(values)


def test_the_descriptor_publishes_exactly_those_eleven_values():
    """The frontend reads this list (015 G3): ``stop_project`` in is the wire half of its
    STOP chips, and the two retired values out is what it must stop offering."""
    descriptor = SchemaDescriptor()
    type_descriptor = descriptor.describe(TypeKey("script", "ActionCueType"))
    field = next(f for f in type_descriptor.fields if f.name == "action_type")
    assert field.enum_values is not None
    assert set(field.enum_values) == ELEVEN
    assert len(field.enum_values) == 11
    assert not RETIRED & set(field.enum_values)
    assert set(field.enum_values) == set(
        get_schema("script").types["ActionType"].enumeration
    )
