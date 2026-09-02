"""Tests for Media.duration validate-on-write and the promoted XSD type.

Covers the object-model setter contract (canonicalise valid input, reject
garbage) and the schema change that makes ``<duration>`` a ``cms:CTimecodeType``
— the same complex type every other time-carrying element uses (feature 008,
FR-002/FR-003) — instead of the unconstrained plain-string ``TimecodeType`` it
used to be.
"""
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
    assert m.duration == CTimecode('00:00:53.840')
    assert isinstance(m.duration, CTimecode)


def test_set_duration_accepts_ctimecode():
    m = Media()
    m.duration = CTimecode('00:03:12.940')
    assert m.duration == CTimecode('00:03:12.940')
    assert isinstance(m.duration, CTimecode)


def test_set_duration_accepts_none():
    m = Media()
    m.duration = None
    assert m.duration is None


def test_set_duration_rejects_garbage_string():
    m = Media()
    with pytest.raises(ValueError):
        m.duration = 'not-a-timecode'


def test_set_duration_accepts_int_and_dict_like_every_other_timecode_field():
    """FR-002 — the exception (str/CTimecode/None only) is gone.

    ``Media.duration`` now goes through ``format_timecode``, exactly as
    ``FadeCue.duration`` and every other ``CTimecodeType`` field does, so it
    accepts everything that machinery accepts.
    """
    m = Media()
    m.duration = 5
    assert m.duration == CTimecode(start_seconds=5)

    m2 = Media()
    m2.duration = {'CTimecode': '00:00:10.000'}
    assert m2.duration == CTimecode('00:00:10.000')


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
    media = data['CuemsScript']['CueList']['contents'][0]['AudioCue']['Media']
    assert media['duration'] == {'CTimecode': '00:00:53.840'}


def test_xsd_rejects_malformed_duration(tmp_path):
    # write a valid doc, then corrupt the duration text on disk
    script = _script_with_duration('00:00:01.000')
    f = str(tmp_path / 'bad.xml')
    XmlReaderWriter(schema_name='script', xmlfile=f).write_from_object(script)
    with open(f) as handle:
        raw = handle.read().replace(
            '<duration><CTimecode>00:00:01.000</CTimecode></duration>',
            '<duration><CTimecode>banana</CTimecode></duration>',
        )
    with open(f, 'w') as handle:
        handle.write(raw)
    with pytest.raises(Exception):   # XMLSchemaValidationError on strict read
        XmlReaderWriter(schema_name='script', xmlfile=f).read()
