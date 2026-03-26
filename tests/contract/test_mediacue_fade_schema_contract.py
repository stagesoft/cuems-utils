"""Contract tests: script.xsd vs MediaCue fade_profile payloads."""

import copy

import pytest

from cuemsutils.cues.FadeProfile import FadeFunctionParameter, FadeProfile
from cuemsutils.xml.XmlBuilder import XmlBuilder
from cuemsutils.xml.XmlReaderWriter import get_pkg_schema
from tests.test_xml import create_dummy_script

NS = '{https://stagelab.coop/cuems/}'


def _fade_script_tree():
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
        )
    ]
    return XmlBuilder(
        script,
        {'cms': 'https://stagelab.coop/cuems/'},
        get_pkg_schema('script'),
        xml_root_tag='CuemsProject',
    ).build()


def _schema():
    from xmlschema import XMLSchema11

    return XMLSchema11(get_pkg_schema('script'))


def test_valid_fade_preset_passes_schema():
    tree = _fade_script_tree()
    _schema().validate(tree)


def test_valid_parametric_with_parameters_passes_schema():
    script, _ = create_dummy_script()
    ac = script.cuelist.contents[2]
    ac.fade_profiles = [
        FadeProfile(
            {
                'type': 'out',
                'mode': 'parametric',
                'function_id': 'bezier',
                'parameters': [
                    FadeFunctionParameter(
                        {'parameter_name': 'p1', 'parameter_value': 0.25}
                    ),
                    FadeFunctionParameter(
                        {'parameter_name': 'p2', 'parameter_value': 0.75}
                    ),
                ],
            }
        )
    ]
    tree = XmlBuilder(
        script,
        {'cms': 'https://stagelab.coop/cuems/'},
        get_pkg_schema('script'),
        xml_root_tag='CuemsProject',
    ).build()
    _schema().validate(tree)


def _iter_fade_wrappers(root):
    for el in root.iter():
        if el.tag == 'fade_profiles' or el.tag.endswith('}fade_profiles'):
            yield el


def _find_fade_profiles(wrap):
    found = wrap.findall('fade_profile')
    if found:
        return found
    return wrap.findall(NS + 'fade_profile')


def _fp_find(fp, name: str):
    el = fp.find(name)
    if el is not None:
        return el
    return fp.find(NS + name)


def test_missing_type_element_fails_schema():
    tree = copy.deepcopy(_fade_script_tree())
    root = tree.getroot()
    for wrap in _iter_fade_wrappers(root):
        for fp in list(_find_fade_profiles(wrap)):
            for ch in list(fp):
                if ch.tag == 'type' or ch.tag == NS + 'type':
                    fp.remove(ch)
    with pytest.raises(Exception):  # XMLSchemaValidationError
        _schema().validate(tree)


def test_invalid_mode_fails_schema():
    tree = copy.deepcopy(_fade_script_tree())
    root = tree.getroot()
    for wrap in _iter_fade_wrappers(root):
        for fp in _find_fade_profiles(wrap):
            mode_el = _fp_find(fp, 'mode')
            if mode_el is not None and mode_el.text == 'preset':
                mode_el.text = 'not_a_mode'
                break
        break
    with pytest.raises(Exception):
        _schema().validate(tree)


def test_empty_function_id_fails_schema():
    tree = copy.deepcopy(_fade_script_tree())
    root = tree.getroot()
    for wrap in _iter_fade_wrappers(root):
        for fp in _find_fade_profiles(wrap):
            fid = _fp_find(fp, 'function_id')
            if fid is not None:
                fid.text = ''
    with pytest.raises(Exception):
        _schema().validate(tree)


def test_legacy_script_without_fade_passes_schema():
    script, _ = create_dummy_script()
    tree = XmlBuilder(
        script,
        {'cms': 'https://stagelab.coop/cuems/'},
        get_pkg_schema('script'),
        xml_root_tag='CuemsProject',
    ).build()
    _schema().validate(tree)
