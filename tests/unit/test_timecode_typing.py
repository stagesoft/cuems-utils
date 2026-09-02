"""One type and one machinery for every time value (T005, T006) — SC-001, SC-002.

Feature 008, ITEM A. Before this feature, ``Media.duration`` was the seventh
time-carrying element and the only one typed plain ``cms:TimecodeType`` — a
restricted string — rather than the complex ``cms:CTimecodeType`` every other
one uses. FR-002/FR-003 promote it, so afterward there is exactly one type and
one machinery for all seven.
"""

from __future__ import annotations

import re

import pytest

from cuemsutils.cues.CuemsScript import CuemsScript
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.xml.documents import get_pkg_schema
from cuemsutils.xml.schema import get_schema
from tests.support.corpus import by_relpath


@pytest.fixture
def script():
    """``fade_showcase.xml`` — the one corpus document carrying both a
    ``Media.duration`` and a ``FadeCue.duration`` (T006)."""
    return CuemsScript.load(by_relpath("cuems-utils/fade_showcase.xml").path)


#: Declarations, not resolved occurrences. ``content.iter_elements()`` resolves
#: ``xs:extension`` chains, so a base element (``CueType.offset``) would be
#: counted once per subclass that inherits it — the wrong question for "how
#: many elements are declared this type" (SC-001). Reading the declaration
#: text directly answers the right one.
_ELEMENT_TYPE_RE = re.compile(
    r'<xs:element\s+name="([A-Za-z_]+)"[^>]*\btype="cms:([A-Za-z]+)"'
)


def _declared_element_types(schema_name: str) -> list[tuple[str, str]]:
    """``(element name, type local name)`` for every ``<xs:element>`` with a
    ``cms:`` type, in source order, read from the ``.xsd`` text itself."""
    with open(get_pkg_schema(schema_name), encoding="utf-8") as handle:
        text = handle.read()
    return [(name, typ) for name, typ in _ELEMENT_TYPE_RE.findall(text)]


def test_exactly_seven_elements_are_typed_ctimecodetype():
    """SC-001 — seven, no more, no fewer, across all six schemas.

    Only ``script.xsd`` declares ``CTimecodeType`` at all (it is a
    schema-local complex type, not shared — see
    ``coercion.AmbiguousBindingError``'s docstring on why registries are per
    schema). So "across all six schemas" reduces to "in script.xsd", and that
    is itself part of what this test pins: a future schema gaining its own
    ``CTimecodeType`` would be exactly the kind of duplicate-by-a-different-name
    F1 exists to catch.
    """
    ctimecode_fields = [
        (name, typ) for name, typ in _declared_element_types("script") if typ == "CTimecodeType"
    ]
    assert len(ctimecode_fields) == 7, ctimecode_fields

    for schema_name in ("settings", "network_map", "project_mappings", "project_settings", "outputs"):
        schema = get_schema(schema_name)
        assert "CTimecodeType" not in schema.types, (
            f"{schema_name}.xsd declares its own CTimecodeType"
        )


def test_zero_time_carrying_elements_are_typed_otherwise():
    """The other half of SC-001: nothing time-carrying escaped the promotion.

    ``Media.duration`` was the one exception (bare ``TimecodeType``,
    ``script.xsd:182`` before T013). No element anywhere in ``script.xsd`` may
    still be declared that bare lexical type — the one legitimate remaining
    use of ``TimecodeType`` is as the *inner* type of ``CTimecodeType``'s own
    ``<CTimecode>`` child (T010), named explicitly rather than swept in.
    """
    offenders = [
        (name, typ) for name, typ in _declared_element_types("script")
        if typ == "TimecodeType" and name != "CTimecode"
    ]
    assert offenders == [], (
        f"time-carrying element(s) still typed a bare timecode string: {offenders}"
    )


def test_media_duration_and_fadecue_duration_are_the_same_object_type(script):
    """SC-002 — indistinguishable in storage, loaded from a real document."""
    media_durations = [
        cue.media.duration
        for cue in script.cuelist.contents
        if hasattr(cue, "media") and cue.media.get("duration") is not None
    ]
    fade_durations = [
        cue.duration
        for cue in script.cuelist.contents
        if type(cue).__name__ == "FadeCue" and cue.get("duration") is not None
    ]
    assert media_durations, "fixture carries no Media.duration to compare"
    assert fade_durations, "fixture carries no FadeCue.duration to compare"

    for value in (*media_durations, *fade_durations):
        assert type(value) is CTimecode

    assert type(media_durations[0]) is type(fade_durations[0])
