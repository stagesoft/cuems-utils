"""Contract C10 (T032) — upgrade tripwire on ``xmlschema``.

The entire design rests on one behaviour of `xmlschema==3.4.3`:
``content.iter_elements()`` resolves ``xs:extension`` chains in **schema
declaration order**, with type and cardinality attached. If an upgrade changed
that, element order would change silently — every script file on disk would be
rewritten on its next save, and nothing would raise.

So the premise is asserted directly against the library rather than only
through the goldens. A golden failure after an upgrade says "the output
changed"; this says *why*, which is the difference between a morning and a week.

`pyproject.toml` pins `xmlschema==3.4.3`. This test is what makes lifting that
pin a decision rather than an accident.
"""

from __future__ import annotations

import pytest
import xmlschema
from xmlschema import XMLSchema11

from cuemsutils.xml.schema import SCHEMA_NAMES, get_schema

#: Measured on 3.4.3 (research R1). Deliberately written out in full rather
#: than computed: a test that derives its expectation from the same call it is
#: checking cannot fail.
AUDIO_CUE_TYPE_ORDER = [
    # CommonPropertiesType, via xs:extension
    "autoload",
    "description",
    "enabled",
    "id",
    "loop",
    "name",
    "offset",
    "post_go",
    "postwait",
    "prewait",
    "target",
    "timecode",
    "ui_properties",
    # MediaCueType
    "Media",
    "outputs",
    # AudioCueType itself
    "master_vol",
    "fade_profiles",
]


def test_iter_elements_yields_the_measured_order():
    schema = get_schema("script")
    names = [e.local_name for e in schema.types["AudioCueType"].content.iter_elements()]
    assert names == AUDIO_CUE_TYPE_ORDER


def test_master_vol_precedes_fade_profiles():
    """The single constraint the hardcoded ordering hack exists to fake.

    ``XmlBuilder.MediaCueXmlBuilder.build`` special-cases ``master_vol`` (and
    ``opacity`` on video cues) to emit ``fade_profiles`` after it. FR-002
    deletes that branch, which is only safe because the schema already says so.
    """
    schema = get_schema("script")
    names = [e.local_name for e in schema.types["AudioCueType"].content.iter_elements()]
    assert names.index("master_vol") < names.index("fade_profiles")


def test_declaration_order_is_not_alphabetical():
    """If it were, the whole feature would be untestable.

    An alphabetically-ordered schema would make "derived from the schema" and
    "sorted by name" indistinguishable in the output, so no test could tell
    which one the engine was doing.
    """
    assert AUDIO_CUE_TYPE_ORDER != sorted(AUDIO_CUE_TYPE_ORDER)


def test_extension_chain_is_resolved_in_base_first_order():
    """Inherited fields come first, in the base type's own order.

    ``AudioCueType`` extends ``MediaCueType`` extends ``CommonPropertiesType``.
    If a future version emitted the derived type's own fields first, every cue
    element in every file would be reordered.
    """
    schema = get_schema("script")
    names = [e.local_name for e in schema.types["AudioCueType"].content.iter_elements()]
    common = [e.local_name for e in schema.types["CommonPropertiesType"].content.iter_elements()]
    assert names[: len(common)] == common


@pytest.mark.parametrize(
    "type_name,expected_model",
    [
        ("AudioCueType", "sequence"),
        ("DmxSceneType", "all"),
    ],
)
def test_content_model_discrimination(type_name, expected_model):
    """``content.model`` is what FR-001's two branches key off.

    Not a type name and not a hardcoded list — if this attribute changed
    meaning, the ordering rule would silently pick the wrong branch for the two
    order-free types.
    """
    assert get_schema("script").types[type_name].content.model == expected_model


def test_the_script_root_types_are_anonymous():
    """Research R3 — there is no ``CuemsScriptType``.

    The registry keys on element **path** for these two, so a future version
    that started naming anonymous types would change how they are looked up.
    """
    schema = get_schema("script")
    assert "CuemsScriptType" not in schema.types
    root = schema.elements["CuemsProject"]
    assert root.type.local_name is None
    script = next(iter(root.type.content.iter_elements()))
    assert script.local_name == "CuemsScript"
    assert script.type.local_name is None
    assert script.type.content.model == "all"


def test_cardinality_is_exposed():
    """``fade_profiles`` is the optional element the corpus actually exercises."""
    schema = get_schema("script")
    fields = {e.local_name: e for e in schema.types["AudioCueType"].content.iter_elements()}
    assert fields["fade_profiles"].min_occurs == 0
    assert fields["fade_profiles"].max_occurs == 1
    assert fields["master_vol"].min_occurs == 1


def test_pinned_version():
    """The pin is load-bearing, so it is asserted rather than trusted.

    Every assertion above was measured on this exact version. Changing the pin
    without re-measuring them is the failure mode this catches.
    """
    assert xmlschema.__version__ == "3.4.3"


@pytest.mark.parametrize("name", SCHEMA_NAMES)
def test_every_schema_loads_as_xsd_11(name):
    """XSD 1.1 is required — ``script.xsd`` uses ``xs:assert`` (X7)."""
    assert isinstance(get_schema(name), XMLSchema11)
