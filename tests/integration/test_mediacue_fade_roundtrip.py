"""Integration: MediaCue fade profiles round-trip through XML."""

import pytest

from cuemsutils.cues.FadeProfile import FadeFunctionParameter, FadeProfile
from cuemsutils.create_script import create_script, validate_template
from cuemsutils.helpers import new_datetime, new_uuid
from cuemsutils.xml.XmlReaderWriter import XmlReaderWriter

from tests.test_xml import create_dummy_script


@pytest.fixture
def tmp_script_path(tmp_path):
    return str(tmp_path / 'fade_roundtrip.xml')


def test_mediacue_fade_profiles_roundtrip(tmp_script_path):
    script, _ = create_dummy_script()
    ac = script.cuelist.contents[2]
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'in',
                'mode': 'preset',
                'function_id': 'linear_in_out',
                'parameters': None,
            }
        ),
        FadeProfile(
            {
                'type': 'out',
                'mode': 'parametric',
                'function_id': 'bezier',
                'parameters': [
                    FadeFunctionParameter(
                        {'parameter_name': 'p1', 'parameter_value': 0.25}
                    )
                ],
            }
        ),
    ]

    writer = XmlReaderWriter(schema_name='script', xmlfile=tmp_script_path)
    writer.write_from_object(script)

    reader = XmlReaderWriter(schema_name='script', xmlfile=tmp_script_path)
    loaded = reader.read_to_objects()
    ac2 = loaded.cuelist.contents[2]
    assert ac2.fade_profiles is not None
    assert len(ac2.fade_profiles) == 2
    assert ac2.get_fade_profile('in').function_id == 'linear_in_out'
    assert ac2.get_fade_profile('out').mode == 'parametric'
    assert ac2.get_fade_profile('out').parameters[0].parameter_name == 'p1'
    assert ac2.get_fade_profile('out').parameters[0].parameter_value == pytest.approx(
        0.25
    )


def test_legacy_mediacue_without_fade_loads(tmp_script_path):
    script, _ = create_dummy_script()
    writer = XmlReaderWriter(schema_name='script', xmlfile=tmp_script_path)
    writer.write_from_object(script)
    reader = XmlReaderWriter(schema_name='script', xmlfile=tmp_script_path)
    loaded = reader.read_to_objects()
    ac = loaded.cuelist.contents[2]
    assert ac.fade_profiles is None


def test_create_script_template_validates_with_schema():
    """Mirror create_script validation window (ids and dates set)."""
    script = create_script()
    now = new_datetime()
    script.created = now
    script.modified = now
    script['id'] = new_uuid()
    script['CueList']['id'] = new_uuid()
    for i in range(len(script.cuelist.contents)):
        script.cuelist.contents[i]['id'] = new_uuid()
    script['ui_properties'] = {'warning': 0}
    validate_template(script)
