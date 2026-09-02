"""The fade-profile surface is deleted outright (T012) — FR-007a.

Three types, one element, two model classes, five semantic rules — the whole
surface, not renamed and not left half-present. Session (d)'s decision
(``spec.md``): deletion over rename, because a ``FadeProfile`` cannot expand
into the ``FadeCue`` its eventual replacement needs, so keeping the shape
under a better name would ship something already known to be wrong.
"""

from __future__ import annotations

from cuemsutils.xml.documents import get_pkg_schema
from cuemsutils.xml.registry import all_registries


def _schema_text() -> str:
    with open(get_pkg_schema("script"), encoding="utf-8") as handle:
        return handle.read()


def test_the_three_types_and_the_element_are_absent_from_script_xsd():
    text = _schema_text()
    for name in ("FadeProfileType", "FadeProfilesWrapperType", "FadeParameterType"):
        assert f'name="{name}"' not in text, f"{name} still declared in script.xsd"
    assert 'name="fade_profiles"' not in text


def test_fadeprofile_and_fadefunctionparameter_no_longer_import():
    import importlib

    import pytest as _pytest

    with _pytest.raises(ModuleNotFoundError):
        importlib.import_module("cuemsutils.cues.FadeProfile")


def test_the_five_fade_profile_rules_are_unregistered():
    from cuemsutils.xml.validators import RULES

    retired = (
        "fade_profile_type",
        "fade_profile_mode",
        "fade_profile_parameters",
        "fade_profile_parameter_value",
        "fade_profile_caps",
    )
    still_present = [name for name in retired if name in RULES]
    assert still_present == []


def test_registry_coherence_still_holds():
    for schema_name, registry in all_registries().items():
        registry.validate()


def test_media_cue_and_subclasses_carry_no_fade_profiles_field():
    from cuemsutils.cues.AudioCue import AudioCue
    from cuemsutils.cues.MediaCue import MediaCue
    from cuemsutils.cues.VideoCue import VideoCue

    for cls in (MediaCue, AudioCue, VideoCue):
        assert "fade_profiles" not in cls.declared_fields()
        assert not hasattr(cls, "get_fade_profile")
