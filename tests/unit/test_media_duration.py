"""Tests for Media.duration validate-on-write and the tightened XSD.

Covers the object-model setter contract (canonicalise valid input, reject
garbage) and the schema change that makes ``<duration>`` a pattern-validated
``TimecodeType`` instead of an unconstrained ``xs:string``.
"""
import tempfile
from os import path

import pytest

from cuemsutils.cues import CuemsScript, CueList, AudioCue
from cuemsutils.cues.MediaCue import Media, Region
from cuemsutils.tools.CTimecode import CTimecode
from cuemsutils.xml import XmlReaderWriter


# ------------------------------------------------------------------ setter ---

def test_set_duration_canonicalises_valid_string():
    m = Media()
    m.duration = '00:00:53.840'
    assert m.duration == '00:00:53.840'
    assert isinstance(m.duration, str)


def test_set_duration_accepts_ctimecode():
    m = Media()
    m.duration = CTimecode('00:03:12.940')
    assert m.duration == '00:03:12.940'
    assert isinstance(m.duration, str)   # getter contract stays str


def test_set_duration_accepts_none():
    m = Media()
    m.duration = None
    assert m.duration is None


def test_set_duration_rejects_garbage_string():
    m = Media()
    with pytest.raises(ValueError):
        m.duration = 'not-a-timecode'


def test_set_duration_rejects_wrong_type():
    m = Media()
    with pytest.raises(TypeError):
        m.duration = 12345


def test_construction_routes_through_validating_setter():
    # dict construction goes through set_duration -> garbage raises
    with pytest.raises(ValueError):
        Media({'file_name': 'x.wav', 'id': '', 'duration': 'garbage',
               'regions': [Region({'id': 0, 'loop': 1,
                                    'in_time': None, 'out_time': None})]})


# --------------------------------------------------------------------- XSD ---

def _script_with_duration(duration):
    return CuemsScript({
        'CueList': CueList({'contents': [
            AudioCue({
                'master_vol': 66,
                'Media': Media({
                    'file_name': 'file.ext', 'id': '', 'duration': duration,
                    'regions': [Region({'id': 0, 'loop': 1,
                                        'in_time': None, 'out_time': None})],
                }),
            }),
        ]}),
        'ui_properties': {'icon': 'icon.png', 'color': '#000000'},
    })


def test_xsd_accepts_corrected_duration(tmp_path):
    script = _script_with_duration('00:00:53.840')
    f = str(tmp_path / 'ok.xml')
    XmlReaderWriter(schema_name='script', xmlfile=f).write_from_object(script)
    # strict read re-validates against the schema
    data = XmlReaderWriter(schema_name='script', xmlfile=f).read()
    assert data['CuemsScript']['CueList']['contents'][0]['AudioCue']['Media']['duration'] == '00:00:53.840'


def test_xsd_rejects_malformed_duration(tmp_path):
    # write a valid doc, then corrupt the duration text on disk
    script = _script_with_duration('00:00:01.000')
    f = str(tmp_path / 'bad.xml')
    XmlReaderWriter(schema_name='script', xmlfile=f).write_from_object(script)
    raw = open(f).read().replace('<duration>00:00:01.000</duration>',
                                 '<duration>banana</duration>')
    open(f, 'w').write(raw)
    with pytest.raises(Exception):   # XMLSchemaValidationError on strict read
        XmlReaderWriter(schema_name='script', xmlfile=f).read()
